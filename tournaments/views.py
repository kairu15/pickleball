from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Count, Q, Sum, F, Prefetch
from django.views.decorators.http import require_POST

from dashboard.cache_utils import cache_anon_page, pages_cache_get_or_set, PAGES_CACHE_TIMEOUT
from datetime import datetime, timedelta

from accounts.decorators import admin_required, staff_or_admin_required, user_required
from courts.models import Court
from accounts.models import UserActivity
from dashboard.models import TournamentPageSettings, FeaturedTournament, TournamentAnnouncement, TournamentCategory
from notifications.email_utils import (
    send_tournament_registration_email,
    send_tournament_schedule_update_email,
    send_tournament_cancellation_email,
    send_tournament_results_email,
    send_tournament_match_reminder_email,
)
from .models import Tournament, Registration, Match, Team, Leaderboard, MatchNotification
from .forms import (
    TournamentForm, RegistrationForm, RegistrationReviewForm, 
    MatchScoreForm, MatchScheduleForm, BulkScheduleForm,
    TournamentStatusForm, TeamForm
)
from .utils import TournamentRandomizer, LeaderboardManager


# ==================== PUBLIC / PLAYER VIEWS ====================

@cache_anon_page(PAGES_CACHE_TIMEOUT, key_prefix='tournament_list')
def tournament_list(request):
    """List all active tournaments.
    Full-page cached for anonymous visitors; invalidated whenever a tournament,
    registration or tournament-CMS record changes. The registration_count is
    annotated to avoid N+1 COUNT queries per tournament card."""

    status_filter = request.GET.get('status', 'all')
    category_filter = request.GET.get('category', 'all')

    # Annotate registration_count so the template's per-card count is a single
    # SQL aggregate instead of a property COUNT query per tournament.
    tournaments = Tournament.objects.annotate(
        approved_registrations_count=Count('registrations', filter=Q(registrations__status='approved'))
    )
    
    if status_filter != 'all':
        tournaments = tournaments.filter(status=status_filter)
    if category_filter != 'all':
        tournaments = tournaments.filter(category=category_filter)
    
    # Separate into categories
    open_tournaments = tournaments.filter(status='registration_open')
    upcoming_tournaments = tournaments.filter(status='draft')
    active_tournaments = tournaments.filter(status='in_progress')
    completed_tournaments = tournaments.filter(status='completed')
    
    # CMS Data (cached; invalidated via dashboard.cache_signals)
    cms_settings = pages_cache_get_or_set('tournament_list_cms', lambda: TournamentPageSettings.objects.first())
    featured_tournaments = pages_cache_get_or_set('tournament_list_featured', lambda: list(
        FeaturedTournament.objects.filter(is_active=True)
        .prefetch_related(Prefetch(
            'tournament',
            queryset=Tournament.objects.annotate(
                approved_registrations_count=Count('registrations', filter=Q(registrations__status='approved'))
            ),
        ))
        .order_by('display_order')[:6]
    ))
    announcements = pages_cache_get_or_set('tournament_list_announcements', lambda: list(
        TournamentAnnouncement.objects.filter(is_active=True).order_by('display_order')
    ))
    categories = pages_cache_get_or_set('tournament_list_categories', lambda: list(
        TournamentCategory.objects.filter(is_active=True).order_by('display_order')
    ))
    
    context = {
        'open_tournaments': open_tournaments,
        'upcoming_tournaments': upcoming_tournaments,
        'active_tournaments': active_tournaments,
        'completed_tournaments': completed_tournaments,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'cms_settings': cms_settings,
        'featured_tournaments': featured_tournaments,
        'announcements': announcements,
        'categories': categories,
        'page_title': cms_settings.page_title if cms_settings and cms_settings.page_title else 'Tournaments',
    }
    
    # Use public template for non-authenticated users, dashboard template for authenticated
    if request.user.is_authenticated:
        return render(request, 'tournaments_public/tournament_list.html', context)
    else:
        return render(request, 'tournaments_public/tournament_list_public.html', context)


def tournament_detail(request, pk):
    """View tournament details"""
    tournament = get_object_or_404(Tournament, pk=pk)
    
    # Check if user is registered
    user_registration = None
    if request.user.is_authenticated:
        user_registration = Registration.objects.filter(
            tournament=tournament,
            user=request.user
        ).first()
    
    # Get approved registrations
    registrations = tournament.registrations.filter(status='approved').select_related('user')
    
    # Get matches if tournament has started
    matches = Match.objects.filter(tournament=tournament).order_by('round_name', 'match_number')
    
    # Get leaderboard
    leaderboard = Leaderboard.objects.filter(tournament=tournament).order_by('rank')[:20]
    
    # Get pending count for admin
    pending_count = tournament.registrations.filter(status='pending').count()
    
    context = {
        'tournament': tournament,
        'user_registration': user_registration,
        'registrations': registrations,
        'registration_count': registrations.count(),
        'pending_count': pending_count,
        'matches': matches,
        'leaderboard': leaderboard,
        'page_title': tournament.name
    }
    
    # Use public template for non-authenticated users, dashboard template for authenticated
    if request.user.is_authenticated:
        return render(request, 'tournaments_public/tournament_detail.html', context)
    else:
        return render(request, 'tournaments_public/tournament_view_public.html', context)


@login_required
@user_required
def tournament_register(request, pk):
    """Register for a tournament"""
    tournament = get_object_or_404(Tournament, pk=pk)
    
    # Check if registration is open
    if not tournament.is_registration_open:
        messages.error(request, 'Registration is not open for this tournament.')
        return redirect('tournament_detail', pk=pk)
    
    # Check if already registered
    existing = Registration.objects.filter(tournament=tournament, user=request.user).first()
    if existing:
        messages.info(request, 'You are already registered for this tournament.')
        return redirect('tournament_detail', pk=pk)
    
    # Check if tournament is full
    if tournament.registration_count >= tournament.max_participants:
        messages.error(request, 'This tournament is full.')
        return redirect('tournament_detail', pk=pk)
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            registration = form.save(commit=False)
            registration.tournament = tournament
            registration.user = request.user
            registration.status = 'pending'
            registration.save()
            
            # Log activity
            UserActivity.objects.create(
                user=request.user,
                action=f'Registered for tournament: {tournament.name}',
                details=f'Status: Pending, Category: {tournament.get_category_display()}'
            )
            
            messages.success(request, 'Registration submitted! Please wait for admin approval.')
            send_tournament_registration_email(request.user, tournament, 'pending')
            return redirect('tournament_detail', pk=pk)
    else:
        form = RegistrationForm()
    
    context = {
        'form': form,
        'tournament': tournament,
        'page_title': f'Register for {tournament.name}'
    }
    return render(request, 'tournaments_public/tournament_register.html', context)


@login_required
@user_required
def my_tournaments(request):
    """View user's tournament registrations"""
    registrations = Registration.objects.filter(
        user=request.user
    ).select_related('tournament').order_by('-registered_at')
    
    context = {
        'registrations': registrations,
        'page_title': 'My Tournaments'
    }
    return render(request, 'user/tournaments/my_tournaments.html', context)


@login_required
@user_required
def my_matches(request):
    """View user's upcoming and past matches"""
    # Singles matches
    singles_matches = Match.objects.filter(
        Q(player1=request.user) | Q(player2=request.user)
    ).select_related('tournament', 'court')
    
    # Doubles matches via team
    user_teams = Team.objects.filter(
        Q(player1=request.user) | Q(player2=request.user)
    ).values_list('id', flat=True)
    
    doubles_matches = Match.objects.filter(
        Q(team1__in=user_teams) | Q(team2__in=user_teams)
    ).select_related('tournament', 'court', 'team1', 'team2')
    
    # Combine and order
    all_matches = (singles_matches | doubles_matches).distinct().order_by('-scheduled_date', '-scheduled_time')
    
    upcoming = all_matches.filter(status__in=['scheduled', 'in_progress'])
    completed = all_matches.filter(status='completed')
    
    context = {
        'upcoming_matches': upcoming,
        'completed_matches': completed,
        'page_title': 'My Matches'
    }
    return render(request, 'user/tournaments/my_matches.html', context)


# ==================== ADMIN / STAFF VIEWS ====================

@login_required
@staff_or_admin_required
def admin_tournament_list(request):
    """Admin view for managing tournaments"""
    
    tournaments = Tournament.objects.all().order_by('-created_at')
    
    # Stats
    total_tournaments = tournaments.count()
    active_count = tournaments.filter(status__in=['registration_open', 'in_progress']).count()
    draft_count = tournaments.filter(status='draft').count()
    completed_count = tournaments.filter(status='completed').count()
    
    context = {
        'tournaments': tournaments,
        'total_tournaments': total_tournaments,
        'active_count': active_count,
        'draft_count': draft_count,
        'completed_count': completed_count,
        'page_title': 'Tournament Management'
    }
    return render(request, 'admin/tournaments/tournament_list.html', context)


@login_required
@staff_or_admin_required
def admin_tournament_create(request):
    """Create a new tournament"""
    
    if request.method == 'POST':
        form = TournamentForm(request.POST)
        if form.is_valid():
            tournament = form.save(commit=False)
            tournament.created_by = request.user
            tournament.save()
            
            UserActivity.objects.create(
                user=request.user,
                action=f'Created tournament: {tournament.name}',
                details=f'Category: {tournament.get_category_display()}, Format: {tournament.get_format_display()}'
            )
            
            messages.success(request, f'Tournament "{tournament.name}" created successfully!')
            return redirect('admin_tournament_list')
    else:
        form = TournamentForm()
    
    context = {
        'form': form,
        'page_title': 'Create Tournament'
    }
    return render(request, 'admin/tournaments/tournament_form.html', context)


@login_required
@staff_or_admin_required
def admin_tournament_edit(request, pk):
    """Edit an existing tournament"""
    
    tournament = get_object_or_404(Tournament.objects.all(), pk=pk)
    
    if request.method == 'POST':
        form = TournamentForm(request.POST, instance=tournament)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tournament updated successfully!')
            return redirect('admin_tournament_list')
    else:
        form = TournamentForm(instance=tournament)
    
    context = {
        'form': form,
        'tournament': tournament,
        'page_title': f'Edit {tournament.name}'
    }
    return render(request, 'admin/tournaments/tournament_form.html', context)


@login_required
@staff_or_admin_required
def admin_tournament_manage(request, pk):
    """Main management view for a tournament"""
    
    tournament = get_object_or_404(Tournament.objects.all(), pk=pk)
    
    # Get all registrations
    registrations = tournament.registrations.select_related('user').order_by('-registered_at')
    pending_regs = registrations.filter(status='pending')
    approved_regs = registrations.filter(status='approved')
    
    # Get matches
    matches = Match.objects.filter(tournament=tournament).order_by('match_number')
    
    # Get teams
    teams = tournament.teams.all()
    
    # Get leaderboard
    leaderboard = Leaderboard.objects.filter(tournament=tournament).order_by('rank')
    
    context = {
        'tournament': tournament,
        'registrations': registrations,
        'pending_count': pending_regs.count(),
        'approved_count': approved_regs.count(),
        'matches': matches,
        'teams': teams,
        'leaderboard': leaderboard,
        'page_title': f'Manage: {tournament.name}'
    }
    return render(request, 'admin/tournaments/tournament_manage.html', context)


@login_required
@staff_or_admin_required
def admin_registration_list(request, pk):
    """View and manage all registrations"""

    tournament = get_object_or_404(Tournament.objects.all(), pk=pk)
    status_filter = request.GET.get('status', 'all')

    all_registrations = tournament.registrations.select_related('user').order_by('-registered_at')
    registrations = all_registrations

    if status_filter != 'all':
        registrations = registrations.filter(status=status_filter)

    # Get counts for stats display
    pending_count = all_registrations.filter(status='pending').count()
    approved_count = all_registrations.filter(status='approved').count()
    rejected_count = all_registrations.filter(status='rejected').count()

    context = {
        'tournament': tournament,
        'registrations': registrations,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'page_title': f'Registrations - {tournament.name}'
    }
    return render(request, 'admin/tournaments/registration_list.html', context)


@login_required
@staff_or_admin_required
def admin_registration_review(request, pk, reg_id):
    """Review a single registration"""
    
    tournament = get_object_or_404(Tournament.objects.all(), pk=pk)
    registration = get_object_or_404(Registration, id=reg_id, tournament=tournament)
    
    if request.method == 'POST':
        form = RegistrationReviewForm(request.POST, instance=registration)
        if form.is_valid():
            reg = form.save(commit=False)
            reg.reviewed_at = timezone.now()
            reg.reviewed_by = request.user
            reg.save()
            
            # Send notification
            if reg.status == 'approved':
                MatchNotification.objects.create(
                    tournament=tournament,
                    user=reg.user,
                    notification_type='registration_approved',
                    message=f'Your registration for {tournament.name} has been approved!'
                )
                messages.success(request, f'Registration approved for {reg.user.username}.')
                send_tournament_registration_email(reg.user, tournament, 'approved')
            elif reg.status == 'rejected':
                MatchNotification.objects.create(
                    tournament=tournament,
                    user=reg.user,
                    notification_type='registration_rejected',
                    message=f'Your registration for {tournament.name} has been rejected.'
                )
                send_tournament_registration_email(reg.user, tournament, 'rejected')
                messages.info(request, f'Registration rejected for {reg.user.username}.')
            
            return redirect('admin_registration_list', pk=pk)
    else:
        form = RegistrationReviewForm(instance=registration)
    
    context = {
        'form': form,
        'tournament': tournament,
        'registration': registration,
        'page_title': f'Review Registration'
    }
    return render(request, 'admin/tournaments/registration_review.html', context)


@login_required
@staff_or_admin_required
@require_POST
def admin_bulk_approve(request, pk):
    """Bulk approve pending registrations"""
    
    tournament = get_object_or_404(Tournament.objects.all(), pk=pk)
    
    pending = tournament.registrations.filter(status='pending')
    count = pending.count()
    
    for reg in pending:
        reg.status = 'approved'
        reg.reviewed_at = timezone.now()
        reg.reviewed_by = request.user
        reg.save()
    
    messages.success(request, f'{count} registrations approved.')
    return redirect('admin_registration_list', pk=pk)


@login_required
@staff_or_admin_required
def admin_generate_matches(request, pk):
    """Generate matches using the randomizer"""
    
    tournament = get_object_or_404(Tournament.objects.all(), pk=pk)
    
    if not tournament.can_generate_matches():
        messages.error(request, 'Not enough approved participants to generate matches.')
        return redirect('admin_tournament_manage', pk=pk)
    
    if request.method == 'POST':
        # Clear existing matches if regenerating
        if 'regenerate' in request.POST:
            Match.objects.filter(tournament=tournament).delete()
            if tournament.category == 'doubles':
                Team.objects.filter(tournament=tournament, is_auto_assigned=True).delete()
        
        # Generate matches based on category
        if tournament.category == 'singles':
            matches = TournamentRandomizer.create_singles_matches(tournament)
        else:
            matches = TournamentRandomizer.create_doubles_matches(tournament)
        
        UserActivity.objects.create(
            user=request.user,
            action=f'Generated matches for tournament: {tournament.name}',
            details=f'Generated {len(matches)} matches'
        )
        
        messages.success(request, f'Successfully generated {len(matches)} matches!')
        return redirect('admin_match_list', pk=pk)
    
    approved_count = tournament.registrations.filter(status='approved').count()
    existing_matches = Match.objects.filter(tournament=tournament).count()
    
    context = {
        'tournament': tournament,
        'approved_count': approved_count,
        'existing_matches': existing_matches,
        'page_title': f'Generate Matches - {tournament.name}'
    }
    return render(request, 'admin/tournaments/generate_matches.html', context)


@login_required
@staff_or_admin_required
def admin_match_list(request, pk):
    """List and manage all matches"""

    tournament = get_object_or_404(Tournament.objects.all(), pk=pk)
    matches = Match.objects.filter(tournament=tournament).order_by('round_name', 'match_number')

    # Calculate status counts
    scheduled_count = matches.filter(status='scheduled').count()
    completed_count = matches.filter(status='completed').count()
    in_progress_count = matches.filter(status='in_progress').count()

    context = {
        'tournament': tournament,
        'matches': matches,
        'total_count': matches.count(),
        'scheduled_count': scheduled_count,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'page_title': f'Matches - {tournament.name}'
    }
    return render(request, 'admin/tournaments/match_list.html', context)


@login_required
@staff_or_admin_required
def admin_match_edit(request, pk, match_id):
    """Edit a match (scores and status)"""
    
    tournament = get_object_or_404(Tournament.objects.all(), pk=pk)
    match = get_object_or_404(Match, id=match_id, tournament=tournament)
    
    if request.method == 'POST':
        form = MatchScoreForm(request.POST, instance=match)
        if form.is_valid():
            updated_match = form.save()
            
            # Update leaderboard if match is completed
            if updated_match.status == 'completed' and updated_match.winner:
                updated_match.completed_at = timezone.now()
                updated_match.save()
                LeaderboardManager.update_leaderboard(updated_match)
                
                # Send notification
                participants = []
                if tournament.category == 'singles':
                    participants = [updated_match.player1, updated_match.player2]
                else:
                    if updated_match.team1:
                        participants.extend([updated_match.team1.player1, updated_match.team1.player2])
                    if updated_match.team2:
                        participants.extend([updated_match.team2.player1, updated_match.team2.player2])
                
                for participant in participants:
                    if participant:
                        MatchNotification.objects.create(
                            tournament=tournament,
                            user=participant,
                            match=updated_match,
                            notification_type='match_completed',
                            message=f'Match completed: {updated_match.get_player1_display()} vs {updated_match.get_player2_display()} - Winner: {updated_match.get_winner_display()}'
                        )
                        # Send match results email
                        send_tournament_results_email(participant, tournament, updated_match.get_winner_display() if updated_match.winner == participant else '')
                
                messages.success(request, 'Match updated and leaderboard recalculated!')
            else:
                messages.success(request, 'Match updated!')
            
            return redirect('admin_match_list', pk=pk)
    else:
        form = MatchScoreForm(instance=match)
    
    context = {
        'form': form,
        'tournament': tournament,
        'match': match,
        'page_title': f'Edit Match #{match.match_number}'
    }
    return render(request, 'admin/tournaments/match_form.html', context)


@login_required
@staff_or_admin_required
def admin_schedule_matches(request, pk):
    """Schedule matches with courts and times"""
    
    tournament = get_object_or_404(Tournament.objects.all(), pk=pk)
    
    # Get unscheduled matches
    unscheduled = Match.objects.filter(
        tournament=tournament,
        court__isnull=True
    ).order_by('match_number')
    
    if request.method == 'POST':
        form = BulkScheduleForm(request.POST)
        if form.is_valid():
            # Process bulk scheduling
            start_date = form.cleaned_data['start_date']
            start_time = form.cleaned_data['start_time']
            matches_per_day = form.cleaned_data['matches_per_day']
            duration = form.cleaned_data['match_duration']
            
            available_courts = list(Court.objects.filter(is_active=True))
            
            current_date = start_date
            current_time = datetime.combine(current_date, start_time)
            court_idx = 0
            matches_scheduled = 0
            
            for match in unscheduled:
                if matches_scheduled >= matches_per_day:
                    # Move to next day
                    current_date += timedelta(days=1)
                    current_time = datetime.combine(current_date, start_time)
                    matches_scheduled = 0
                    court_idx = 0
                
                if available_courts:
                    match.court = available_courts[court_idx % len(available_courts)]
                    match.scheduled_date = current_date
                    match.scheduled_time = current_time.time()
                    match.duration_minutes = duration
                    match.save()
                    
                    # Increment time for next match on same court
                    matches_scheduled += 1
                    
                    # Rotate through courts
                    if matches_scheduled % len(available_courts) == 0:
                        current_time += timedelta(minutes=duration)
                    
                    court_idx += 1
            
            # Send schedule update and match reminder emails to all approved participants
            for reg in tournament.registrations.filter(status='approved'):
                send_tournament_schedule_update_email(reg.user, tournament, f'{unscheduled.count()} matches have been scheduled.')
                # Send match reminders to players who have matches scheduled
                player_matches = Match.objects.filter(
                    tournament=tournament,
                    scheduled_date__isnull=False
                ).filter(
                    Q(player1=reg.user) | Q(player2=reg.user) |
                    Q(team1__player1=reg.user) | Q(team1__player2=reg.user) |
                    Q(team2__player1=reg.user) | Q(team2__player2=reg.user)
                )
                for match in player_matches:
                    send_tournament_match_reminder_email(reg.user, match)
            
            messages.success(request, f'Scheduled {unscheduled.count()} matches!')
            return redirect('admin_match_list', pk=pk)
    else:
        form = BulkScheduleForm()
    
    available_courts_count = Court.objects.filter(is_active=True).count()
    
    if available_courts_count == 0 and unscheduled.count() > 0:
        messages.warning(
            request,
            'No courts are available for scheduling matches. '
            'Please create at least one court before scheduling.'
        )
    
    context = {
        'form': form,
        'tournament': tournament,
        'unscheduled_count': unscheduled.count(),
        'available_courts_count': available_courts_count,
        'page_title': f'Schedule Matches - {tournament.name}'
    }
    return render(request, 'admin/tournaments/schedule_matches.html', context)


@login_required
@staff_or_admin_required
def admin_leaderboard(request, pk):
    """View and manage leaderboard"""
    
    tournament = get_object_or_404(Tournament.objects.all(), pk=pk)
    
    # Get standings
    standings = LeaderboardManager.get_standings(tournament)
    
    # Group by group name
    groups = {}
    for entry in standings:
        group = entry.group_name or 'General'
        if group not in groups:
            groups[group] = []
        groups[group].append(entry)
    
    context = {
        'tournament': tournament,
        'groups': groups,
        'standings': standings,
        'page_title': f'Leaderboard - {tournament.name}'
    }
    return render(request, 'admin/tournaments/leaderboard.html', context)


@login_required
@staff_or_admin_required
def admin_team_list(request, pk):
    """View and manage teams for doubles tournaments"""
    
    tournament = get_object_or_404(Tournament.objects.all(), pk=pk)
    teams = tournament.teams.all().select_related('player1', 'player2')
    
    context = {
        'tournament': tournament,
        'teams': teams,
        'page_title': f'Teams - {tournament.name}'
    }
    return render(request, 'admin/tournaments/team_list.html', context)


@login_required
@staff_or_admin_required
def admin_team_create(request, pk):
    """Create a new team"""
    
    tournament = get_object_or_404(Tournament.objects.all(), pk=pk)
    
    if request.method == 'POST':
        form = TeamForm(request.POST, tournament=tournament)
        if form.is_valid():
            team = form.save(commit=False)
            team.tournament = tournament
            team.save()
            
            messages.success(request, 'Team created successfully!')
            return redirect('admin_team_list', pk=pk)
    else:
        form = TeamForm(tournament=tournament)
    
    context = {
        'form': form,
        'tournament': tournament,
        'page_title': f'Create Team - {tournament.name}'
    }
    return render(request, 'admin/tournaments/team_form.html', context)


@login_required
@staff_or_admin_required
def admin_tournament_bracket(request, pk):
    """View tournament bracket (for elimination formats)"""
    
    tournament = get_object_or_404(Tournament.objects.all(), pk=pk)
    
    # Get matches organized by round
    matches_by_round = {}
    for round_name, _ in Match.ROUND_CHOICES:
        matches = Match.objects.filter(tournament=tournament, round_name=round_name).order_by('match_number')
        if matches.exists():
            matches_by_round[round_name] = matches
    
    context = {
        'tournament': tournament,
        'matches_by_round': matches_by_round,
        'page_title': f'Bracket - {tournament.name}'
    }
    return render(request, 'admin/tournaments/bracket.html', context)


@login_required
@staff_or_admin_required
def admin_change_status(request, pk):
    """Change tournament status"""
    
    tournament = get_object_or_404(Tournament.objects.all(), pk=pk)
    
    if request.method == 'POST':
        form = TournamentStatusForm(request.POST, instance=tournament)
        if form.is_valid():
            form.save()
            
            # Send notifications based on status change
            if tournament.status == 'in_progress':
                for reg in tournament.registrations.filter(status='approved'):
                    MatchNotification.objects.create(
                        tournament=tournament,
                        user=reg.user,
                        notification_type='tournament_start',
                        message=f'{tournament.name} has started! Check your matches.'
                    )
            elif tournament.status == 'completed':
                # Send tournament results to all approved registrations
                for reg in tournament.registrations.filter(status='approved'):
                    send_tournament_results_email(reg.user, tournament)
            elif tournament.status == 'cancelled':
                # Send cancellation to all registrations
                for reg in tournament.registrations.all():
                    send_tournament_cancellation_email(reg.user, tournament)
            
            messages.success(request, f'Tournament status updated to {tournament.get_status_display()}.')
            return redirect('admin_tournament_manage', pk=pk)
    else:
        form = TournamentStatusForm(instance=tournament)
    
    context = {
        'form': form,
        'tournament': tournament,
        'page_title': f'Change Status - {tournament.name}'
    }
    return render(request, 'admin/tournaments/change_status.html', context)


# ==================== API / AJAX VIEWS ====================

@login_required
def api_update_score(request, match_id):
    """AJAX endpoint for updating match scores"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    match = get_object_or_404(Match, id=match_id)
    
    if not request.user.is_admin() and not request.user.is_staff_user():
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        score1 = int(request.POST.get('score1', 0))
        score2 = int(request.POST.get('score2', 0))
        
        match.score1 = score1
        match.score2 = score2
        
        # Auto-determine winner
        if score1 > score2:
            match.winner = match.player1
            match.winner_team = match.team1
        elif score2 > score1:
            match.winner = match.player2
            match.winner_team = match.team2
        
        match.status = 'completed'
        match.completed_at = timezone.now()
        match.save()
        
        # Update leaderboard
        LeaderboardManager.update_leaderboard(match)
        
        return JsonResponse({
            'success': True,
            'winner': match.get_winner_display() if match.winner or match.winner_team else None
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
