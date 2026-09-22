import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Value
from django.db.models.functions import Concat
from django.utils import timezone
from django.http import JsonResponse
from accounts.decorators import admin_required, staff_or_admin_required, user_required
from accounts.models import User
from .models import Match, Game, ScorePoint, PlayerStats, MatchSettings, GuestPlayer
from .forms import MatchSetupForm, ScoreUpdateForm, MatchSettingsForm
from reservations.models import Reservation
from notifications.models import Notification


@login_required
def match_list_view(request):
    if request.user.is_normal_user():
        # Show matches where user is a player
        matches = Match.objects.filter(
            Q(team1_player1=request.user) |
            Q(team1_player2=request.user) |
            Q(team2_player1=request.user) |
            Q(team2_player2=request.user) |
            Q(reservation__user=request.user)
        ).order_by('-created_at')
    else:
        matches = Match.objects.all().order_by('-created_at')
    
    return render(request, 'scoring/match_list.html', {'matches': matches})


@login_required
def match_detail_view(request, match_id):
    match = get_object_or_404(Match.objects.all(), id=match_id)
    
    return render(request, 'scoring/match_detail.html', {'match': match})


@login_required
@staff_or_admin_required
def start_match_view(request, reservation_id):
    
    reservation = get_object_or_404(Reservation.objects.all(), id=reservation_id)
    
    # Check if match already exists
    try:
        match = Match.objects.get(reservation=reservation)
        return redirect('match_live', match_id=match.id)
    except Match.DoesNotExist:
        pass
    
    # Check if user can override reservation settings (org staff or admin)
    can_override = request.user.is_staff_user() or request.user.is_admin()

    # Get eligible users (active users with 'user' role, scoped to org if applicable)
    eligible_users = User.objects.filter(is_active=True, employment_status='active', role='user').order_by('username')

    if request.method == 'POST':
        form = MatchSetupForm(request.POST)
        form.fields['team1_player1'].queryset = eligible_users
        form.fields['team1_player2'].queryset = eligible_users
        form.fields['team2_player1'].queryset = eligible_users
        form.fields['team2_player2'].queryset = eligible_users

        if form.is_valid():
            match = form.save(commit=False)
            match.reservation = reservation
            match.match_name = reservation.match_name
            match.status = 'ongoing'
            match.started_at = timezone.now()

            # Assign team 1 players
            team1_p1 = form.cleaned_data.get('team1_player1')
            team1_p2 = form.cleaned_data.get('team1_player2')
            match.team1_player1 = team1_p1 or reservation.user
            match.team1_player2 = team1_p2 if form.cleaned_data.get('format') in ('doubles', 'mixed_doubles') else None

            # Assign team 2 players
            match.team2_player1 = form.cleaned_data.get('team2_player1')
            match.team2_player2 = form.cleaned_data.get('team2_player2') if form.cleaned_data.get('format') in ('doubles', 'mixed_doubles') else None

            # Override lock check
            if not can_override:
                match.format = reservation.match_format
                match.game_type = reservation.game_type
                match.scoring_format = reservation.scoring_format
                match.games_to_win = reservation.games_to_win
                match.points_per_game = reservation.points_per_game
                match.win_by_two = reservation.win_by_two

            # Save team names
            match.team1_name = form.cleaned_data.get('team1_name', '')
            match.team2_name = form.cleaned_data.get('team2_name', '')

            match.save()

            # Handle guest players
            guest_fields = {
                ('guest_team1_p1', 1, 1),
                ('guest_team1_p2', 1, 2),
                ('guest_team2_p1', 2, 1),
                ('guest_team2_p2', 2, 2),
            }
            is_doubles = match.format in ('doubles', 'mixed_doubles')
            for field_name, team, player_num in guest_fields:
                guest_name = form.cleaned_data.get(field_name, '')
                if guest_name:
                    # Check if this slot should have a guest (not filled by registered user)
                    if (team == 1 and player_num == 1 and match.team1_player1):
                        continue
                    if (team == 1 and player_num == 2 and (match.team1_player2 or not is_doubles)):
                        continue
                    if (team == 2 and player_num == 1 and match.team2_player1):
                        continue
                    if (team == 2 and player_num == 2 and (match.team2_player2 or not is_doubles)):
                        continue
                    GuestPlayer.objects.create(
                        match=match,
                        team=team,
                        player_number=player_num,
                        full_name=guest_name,
                    )

            # Create first game
            Game.objects.create(
                match=match,
                game_number=1,
                started_at=timezone.now()
            )

            # Update reservation status
            reservation.status = 'completed'
            reservation.save()

            # Notify players
            Notification.objects.create(
                user=reservation.user,
                message=f"Your match has started on {reservation.court.name}!"
            )

            messages.success(request, 'Match started successfully!')
            return redirect('match_live', match_id=match.id)
    else:
        # Auto-populate from reservation's player fields if available
        initial = {
            'format': reservation.match_format,
            'game_type': reservation.game_type,
            'scoring_format': reservation.scoring_format,
            'games_to_win': reservation.games_to_win,
            'points_per_game': reservation.points_per_game,
            'win_by_two': reservation.win_by_two,
            'team1_player1': reservation.user,
        }
        # Set team 1 player 2 (doubles teammate)
        if reservation.team1_player2:
            initial['team1_player2'] = reservation.team1_player2
        # Set team 2 player 1 (opponent) from reservation
        if reservation.team2_player1:
            initial['team2_player1'] = reservation.team2_player1
        # Set team 2 player 2 (doubles teammate)
        if reservation.team2_player2:
            initial['team2_player2'] = reservation.team2_player2
        # Set team names
        initial['team1_name'] = reservation.team1_name or 'Home Team'
        initial['team2_name'] = reservation.team2_name or 'Opponent'
        
        form = MatchSetupForm(initial=initial)
        form.fields['team1_player1'].queryset = eligible_users
        form.fields['team1_player2'].queryset = eligible_users
        form.fields['team2_player1'].queryset = eligible_users
        form.fields['team2_player2'].queryset = eligible_users

    # Parse guest players data from reservation for pre-population
    guest_data_list = []
    if reservation.guest_players_data:
        try:
            parsed = json.loads(reservation.guest_players_data)
            if isinstance(parsed, list):
                guest_data_list = parsed
        except (json.JSONDecodeError, TypeError):
            pass

    return render(request, 'scoring/start_match.html', {
        'form': form,
        'reservation': reservation,
        'can_override': can_override,
        'eligible_users': eligible_users,
        'guest_data_list': guest_data_list,
    })


@login_required
def match_live_view(request, match_id):
    match = get_object_or_404(Match.objects.all(), id=match_id)
    
    # Get current game
    current_game = match.games.filter(ended_at__isnull=True).first()
    if not current_game:
        # All games complete, get the last one
        current_game = match.games.order_by('-game_number').first()
    
    completed_games = match.games.filter(ended_at__isnull=False)
    
    # Build player display data for template
    def player_name(registered_player, team, player_number):
        """Get display name for a player slot."""
        if registered_player:
            return registered_player.get_full_name() or registered_player.username
        guest = match.guest_players.filter(team=team, player_number=player_number).first()
        if guest:
            return guest.get_display_name()
        return 'TBD'
    
    def player_initial(registered_player, team, player_number):
        """Get initial for a player slot."""
        name = player_name(registered_player, team, player_number)
        if name and name != 'TBD':
            return name[0].upper()
        return '?'
    
    context = {
        'match': match,
        'current_game': current_game,
        'completed_games': completed_games,
        't1_p1_name': player_name(match.team1_player1, 1, 1),
        't1_p1_initial': player_initial(match.team1_player1, 1, 1),
        't1_p2_name': player_name(match.team1_player2, 1, 2),
        't1_p2_initial': player_initial(match.team1_player2, 1, 2),
        't2_p1_name': player_name(match.team2_player1, 2, 1),
        't2_p1_initial': player_initial(match.team2_player1, 2, 1),
        't2_p2_name': player_name(match.team2_player2, 2, 2),
        't2_p2_initial': player_initial(match.team2_player2, 2, 2),
    }
    
    return render(request, 'scoring/match_live.html', context)


@login_required
def update_score_view(request, game_id):
    if not request.user.is_staff_user():
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    game = get_object_or_404(Game.objects.all(), id=game_id)
    
    if request.method == 'POST':
        team = request.POST.get('team')
        action = request.POST.get('action')  # 'add' or 'subtract'
        
        if action == 'add':
            if team == '1':
                game.team1_score += 1
            else:
                game.team2_score += 1
            
            # Log the point (total points so far in the game)
            total_points = game.team1_score + game.team2_score
            ScorePoint.objects.create(
                game=game,
                team=int(team),
                point_number=total_points
            )
            
        elif action == 'subtract':
            if team == '1' and game.team1_score > 0:
                game.team1_score -= 1
            elif team == '2' and game.team2_score > 0:
                game.team2_score -= 1
        
        game.save()
        
        # Check if game is won
        match = game.match
        win_by_two = 2 if match.win_by_two else 0
        points_to_win = match.points_per_game
        
        if (game.team1_score >= points_to_win and 
            game.team1_score >= game.team2_score + win_by_two):
            game.winner = 1
            game.ended_at = timezone.now()
            game.save()
            
        elif (game.team2_score >= points_to_win and 
              game.team2_score >= game.team1_score + win_by_two):
            game.winner = 2
            game.ended_at = timezone.now()
            game.save()
        
        # Check if match is complete
        team1_wins = sum(1 for g in match.games.all() if g.winner == 1)
        team2_wins = sum(1 for g in match.games.all() if g.winner == 2)
        
        if team1_wins >= match.games_to_win:
            match.winner_team = 1
            match.status = 'completed'
            match.ended_at = timezone.now()
            match.save()
            update_player_stats(match)
        elif team2_wins >= match.games_to_win:
            match.winner_team = 2
            match.status = 'completed'
            match.ended_at = timezone.now()
            match.save()
            update_player_stats(match)
        elif game.winner and not match.games.filter(ended_at__isnull=True).count() >= match.games_to_win * 2 - 1:
            # Create next game if match isn't over
            next_game_num = match.games.count() + 1
            if next_game_num <= match.games_to_win * 2 - 1:
                Game.objects.create(
                    match=match,
                    game_number=next_game_num,
                    started_at=timezone.now()
                )
        
        return redirect('match_live', match_id=match.id)
    
    return redirect('match_live', match_id=game.match.id)


@login_required
@user_required
def player_stats_view(request):
    try:
        stats = request.user.stats
    except PlayerStats.DoesNotExist:
        stats = PlayerStats.objects.create(player=request.user)
    
    # Get match history
    matches = Match.objects.filter(
        Q(team1_player1=request.user) |
        Q(team1_player2=request.user) |
        Q(team2_player1=request.user) |
        Q(team2_player2=request.user)
    ).order_by('-created_at')[:10]
    
    return render(request, 'scoring/player_stats.html', {
        'stats': stats,
        'matches': matches
    })


@login_required
def leaderboard_view(request):
    stats_qs = PlayerStats.objects.filter(total_matches__gt=0)
    stats = stats_qs.order_by('-win_rate', '-total_matches')[:50]
    
    return render(request, 'scoring/leaderboard.html', {
        'stats': stats
    })


def update_player_stats(match):
    """Update player statistics after a match is completed"""
    players = [
        match.team1_player1,
        match.team1_player2,
        match.team2_player1,
        match.team2_player2
    ]
    
    for player in players:
        if not player:
            continue
        
        try:
            stats = player.stats
        except PlayerStats.DoesNotExist:
            stats = PlayerStats.objects.create(player=player)
        
        stats.total_matches += 1
        stats.total_games_played += match.games.count()
        
        # Determine if player was on winning team
        on_team1 = player in [match.team1_player1, match.team1_player2]
        won = (on_team1 and match.winner_team == 1) or (not on_team1 and match.winner_team == 2)
        
        if won:
            stats.wins += 1
        else:
            stats.losses += 1
        
        # Count games won
        for game in match.games.all():
            if game.winner:
                if (on_team1 and game.winner == 1) or (not on_team1 and game.winner == 2):
                    stats.games_won += 1
        
        # Points
        for game in match.games.all():
            if on_team1:
                stats.total_points_scored += game.team1_score
                stats.total_points_conceded += game.team2_score
            else:
                stats.total_points_scored += game.team2_score
                stats.total_points_conceded += game.team1_score
        
        stats.calculate_win_rate()
        stats.last_match_at = match.ended_at
        stats.save()


@login_required
def search_users_api(request):
    """API endpoint for searching users for player assignment.
    Supports searching by: username, first_name, middle_name, last_name,
    full name (*), email, staff_id, and player ID (numeric pk).

    (*) Full name matching uses CONCAT(first_name, ' ', last_name)
        so queries like "John Smith" match the combined full name.
    """
    q = request.GET.get('q', '').strip()
    exclude_ids = request.GET.get('exclude_ids', '')
    reservation_id = request.GET.get('reservation_id', '')
    
    # Only show active users with the 'user' role (exclude staff/admins)
    users = User.objects.filter(is_active=True, employment_status='active', role='user')
    
    if q:
        # Annotate concatenated full name for searching by "Full Name"
        users = users.annotate(
            _full_name=Concat('first_name', Value(' '), 'last_name')
        )
        
        # Build search filter covering all requested fields
        name_filter = (
            Q(username__icontains=q) |
            Q(_full_name__icontains=q) |
            Q(first_name__icontains=q) |
            Q(middle_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(staff_id__icontains=q)
        )
        
        # Also search by numeric player ID if query is a number
        try:
            q_int = int(q)
            name_filter |= Q(id=q_int)
        except ValueError:
            pass
        
        users = users.filter(name_filter)
    
    if exclude_ids:
        try:
            ids = [int(x) for x in exclude_ids.split(',') if x.strip()]
            users = users.exclude(id__in=ids)
        except (ValueError, TypeError):
            pass
    
    users = users.order_by('username')[:20]
    
    results = []
    for u in users:
        profile_pic_url = None
        if u.profile_picture:
            try:
                profile_pic_url = u.profile_picture.url
            except Exception:
                pass
        results.append({
            'id': u.id,
            'username': u.username,
            'full_name': u.get_full_name() or u.username,
            'email': u.email,
            'profile_picture': profile_pic_url,
            'skill_level': u.get_skill_level_display() if u.skill_level else None,
        })
    
    return JsonResponse({'users': results})


def match_score_api(request, match_id):
    """API endpoint for getting live match score"""
    match = get_object_or_404(Match.objects.all(), id=match_id)
    current_game = match.games.filter(ended_at__isnull=True).first()
    
    data = {
        'match_id': match.id,
        'status': match.status,
        'team1_wins': match.get_team1_score(),
        'team2_wins': match.get_team2_score(),
        'current_game': {
            'game_number': current_game.game_number if current_game else None,
            'team1_score': current_game.team1_score if current_game else 0,
            'team2_score': current_game.team2_score if current_game else 0,
        } if current_game else None
    }
    
    return JsonResponse(data)


@login_required
@admin_required
def match_settings_list_view(request):
    
    settings = MatchSettings.objects.all().order_by('-is_active', '-created_at')
    
    return render(request, 'admin/match_settings/match_settings_list.html', {'settings': settings})


@login_required
@admin_required
def match_settings_create_view(request):
    
    if request.method == 'POST':
        form = MatchSettingsForm(request.POST)
        if form.is_valid():
            settings = form.save()
            messages.success(request, 'Match settings created successfully.')
            return redirect('match_settings_list')
    else:
        form = MatchSettingsForm()
    
    return render(request, 'admin/match_settings/match_settings_form.html', {'form': form, 'edit_mode': False})


@login_required
@admin_required
def match_settings_edit_view(request, settings_id):
    
    settings = get_object_or_404(MatchSettings.objects.all(), id=settings_id)
    
    if request.method == 'POST':
        form = MatchSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Match settings updated successfully.')
            return redirect('match_settings_list')
    else:
        form = MatchSettingsForm(instance=settings)
    
    return render(request, 'admin/match_settings/match_settings_form.html', {'form': form, 'settings': settings, 'edit_mode': True})


@login_required
@admin_required
def match_settings_delete_view(request, settings_id):
    
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('match_settings_list')
    
    settings = get_object_or_404(MatchSettings.objects.all(), id=settings_id)
    settings.delete()
    messages.success(request, 'Match settings deleted successfully.')
    return redirect('match_settings_list')
