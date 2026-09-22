import random
from typing import List, Tuple, Optional
from django.db import transaction
from django.utils import timezone
from accounts.models import User
from .models import Tournament, Registration, Team, Match, Leaderboard


class TournamentRandomizer:
    """Handles random player and team assignments"""
    
    @staticmethod
    def shuffle_players(players: List) -> List:
        """Shuffle players randomly"""
        shuffled = players.copy()
        random.shuffle(shuffled)
        return shuffled
    
    @staticmethod
    def create_singles_matches(tournament: Tournament) -> List[Match]:
        """
        Create random matches for singles tournament
        Supports: Round Robin, Single Elimination, Double Elimination
        """
        approved_regs = list(tournament.registrations.filter(status='approved').select_related('user'))
        players = [reg.user for reg in approved_regs]
        shuffled_players = TournamentRandomizer.shuffle_players(players)
        
        matches = []
        
        if tournament.format == 'round_robin':
            matches = TournamentRandomizer._create_round_robin_singles(tournament, shuffled_players)
        elif tournament.format == 'single_elimination':
            matches = TournamentRandomizer._create_single_elimination_singles(tournament, shuffled_players)
        elif tournament.format == 'double_elimination':
            matches = TournamentRandomizer._create_double_elimination_singles(tournament, shuffled_players)
        elif tournament.format == 'king_queen':
            matches = TournamentRandomizer._create_king_queen_singles(tournament, shuffled_players)
            
        return matches
    
    @staticmethod
    def _create_round_robin_singles(tournament: Tournament, players: List[User]) -> List[Match]:
        """Create round robin matches where everyone plays everyone"""
        matches = []
        match_num = 1
        
        # Create groups if needed
        group_size = tournament.players_per_group
        groups = [players[i:i + group_size] for i in range(0, len(players), group_size)]
        
        for group_idx, group in enumerate(groups):
            group_name = chr(65 + group_idx)  # A, B, C...
            
            # Everyone plays everyone in the group
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    match = Match.objects.create(
                        tournament=tournament,
                        player1=group[i],
                        player2=group[j],
                        round_name='group_stage',
                        group_name=group_name,
                        match_number=match_num,
                        status='scheduled'
                    )
                    matches.append(match)
                    match_num += 1
        
        return matches
    
    @staticmethod
    def _create_single_elimination_singles(tournament: Tournament, players: List[User]) -> List[Match]:
        """Create single elimination bracket"""
        matches = []
        num_players = len(players)
        
        # Calculate bracket size (next power of 2)
        bracket_size = 1
        while bracket_size < num_players:
            bracket_size *= 2
        
        # Create byes for extra slots
        byes = bracket_size - num_players
        player_with_byes = players[:byes] if byes > 0 else []
        players_without_byes = players[byes:] if byes > 0 else players
        
        # Create first round matches
        match_num = 1
        first_round_matches = []
        
        for i in range(0, len(players_without_byes), 2):
            if i + 1 < len(players_without_byes):
                match = Match.objects.create(
                    tournament=tournament,
                    player1=players_without_byes[i],
                    player2=players_without_byes[i + 1],
                    round_name='round_of_32' if bracket_size >= 32 else 'round_of_16',
                    match_number=match_num,
                    status='scheduled',
                    bracket_position=match_num
                )
                first_round_matches.append(match)
                match_num += 1
        
        # Create subsequent rounds
        current_round = first_round_matches
        round_names = ['round_of_16', 'quarter_final', 'semi_final', 'final']
        round_idx = 0
        
        while len(current_round) > 1:
            next_round = []
            next_round_name = round_names[min(round_idx, len(round_names) - 1)]
            
            for i in range(0, len(current_round), 2):
                match = Match.objects.create(
                    tournament=tournament,
                    round_name=next_round_name,
                    match_number=match_num,
                    status='scheduled'
                )
                
                # Link previous matches
                if i < len(current_round):
                    current_round[i].next_match = match
                    current_round[i].save()
                if i + 1 < len(current_round):
                    current_round[i + 1].next_match = match
                    current_round[i + 1].save()
                
                next_round.append(match)
                match_num += 1
            
            current_round = next_round
            round_idx += 1
        
        matches = list(Match.objects.filter(tournament=tournament))
        return matches
    
    @staticmethod
    def _create_double_elimination_singles(tournament: Tournament, players: List[User]) -> List[Match]:
        """Create double elimination bracket (winners and losers bracket)"""
        # First create winners bracket like single elimination
        matches = TournamentRandomizer._create_single_elimination_singles(tournament, players)
        
        # Mark as winners bracket
        for match in matches:
            match.is_winners_bracket = True
            match.save()
        
        # Note: Losers bracket matches not yet implemented.
        # This is more complex - losers drop to losers bracket.
        # Future enhancement: create losers bracket after winners bracket matches complete.
        
        return matches
    
    @staticmethod
    def _create_king_queen_singles(tournament: Tournament, players: List[User]) -> List[Match]:
        """Create rotation-based matches for King/Queen of the Court"""
        # Initial random pairings
        shuffled = TournamentRandomizer.shuffle_players(players)
        matches = []
        
        # Create initial matches
        for i in range(0, len(shuffled), 2):
            if i + 1 < len(shuffled):
                match = Match.objects.create(
                    tournament=tournament,
                    player1=shuffled[i],
                    player2=shuffled[i + 1],
                    round_name='qualifier',
                    match_number=(i // 2) + 1,
                    status='scheduled'
                )
                matches.append(match)
        
        return matches
    
    @staticmethod
    def create_doubles_matches(tournament: Tournament) -> List[Match]:
        """Create matches for doubles tournaments with auto-team assignment"""
        approved_regs = list(tournament.registrations.filter(status='approved').select_related('user'))
        
        if tournament.auto_assign_teams:
            # Randomly pair players into teams
            teams = TournamentRandomizer._create_random_teams(tournament, approved_regs)
        else:
            # Use pre-registered teams
            teams = list(tournament.teams.all())
        
        # Shuffle teams for random matchups
        shuffled_teams = TournamentRandomizer.shuffle_players(teams)
        
        matches = []
        
        if tournament.format == 'round_robin':
            matches = TournamentRandomizer._create_round_robin_doubles(tournament, shuffled_teams)
        elif tournament.format in ['single_elimination', 'double_elimination']:
            matches = TournamentRandomizer._create_elimination_doubles(tournament, shuffled_teams)
        
        return matches
    
    @staticmethod
    def _create_random_teams(tournament: Tournament, registrations: List[Registration]) -> List[Team]:
        """Create random teams from individual registrations"""
        players = [reg.user for reg in registrations]
        shuffled = TournamentRandomizer.shuffle_players(players)
        teams = []
        
        # Check for mixed doubles
        if tournament.category == 'mixed_doubles':
            return TournamentRandomizer._create_mixed_teams(tournament, registrations)
        
        # Random pairing
        for i in range(0, len(shuffled), 2):
            if i + 1 < len(shuffled):
                team = Team.objects.create(
                    tournament=tournament,
                    player1=shuffled[i],
                    player2=shuffled[i + 1],
                    is_auto_assigned=True
                )
                teams.append(team)
                
                # Update registrations with team
                Registration.objects.filter(
                    tournament=tournament, 
                    user__in=[shuffled[i], shuffled[i + 1]]
                ).update(team=team)
        
        return teams
    
    @staticmethod
    def _create_mixed_teams(tournament: Tournament, registrations: List[Registration]) -> List[Team]:
        """Create mixed gender teams - one male, one female"""
        # Separate by gender
        males = [reg for reg in registrations if reg.gender == 'male']
        females = [reg for reg in registrations if reg.gender == 'female']
        
        # Shuffle both lists
        random.shuffle(males)
        random.shuffle(females)
        
        teams = []
        min_pairs = min(len(males), len(females))
        
        for i in range(min_pairs):
            team = Team.objects.create(
                tournament=tournament,
                player1=males[i].user,
                player2=females[i].user,
                is_auto_assigned=True
            )
            teams.append(team)
            
            # Update registrations
            males[i].team = team
            males[i].save()
            females[i].team = team
            females[i].save()
        
        # Handle remaining players (single gender)
        remaining = males[min_pairs:] + females[min_pairs:]
        for i in range(0, len(remaining), 2):
            if i + 1 < len(remaining):
                team = Team.objects.create(
                    tournament=tournament,
                    player1=remaining[i].user,
                    player2=remaining[i + 1].user,
                    is_auto_assigned=True
                )
                teams.append(team)
                remaining[i].team = team
                remaining[i].save()
                remaining[i + 1].team = team
                remaining[i + 1].save()
        
        return teams
    
    @staticmethod
    def _create_round_robin_doubles(tournament: Tournament, teams: List[Team]) -> List[Match]:
        """Create round robin matches for doubles"""
        matches = []
        match_num = 1
        
        group_size = tournament.players_per_group
        groups = [teams[i:i + group_size] for i in range(0, len(teams), group_size)]
        
        for group_idx, group in enumerate(groups):
            group_name = chr(65 + group_idx)
            
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    match = Match.objects.create(
                        tournament=tournament,
                        team1=group[i],
                        team2=group[j],
                        round_name='group_stage',
                        group_name=group_name,
                        match_number=match_num,
                        status='scheduled'
                    )
                    matches.append(match)
                    match_num += 1
        
        return matches
    
    @staticmethod
    def _create_elimination_doubles(tournament: Tournament, teams: List[Team]) -> List[Match]:
        """Create elimination bracket for doubles"""
        matches = []
        num_teams = len(teams)
        
        bracket_size = 1
        while bracket_size < num_teams:
            bracket_size *= 2
        
        byes = bracket_size - num_teams
        teams_with_byes = teams[:byes] if byes > 0 else []
        teams_without_byes = teams[byes:] if byes > 0 else teams
        
        match_num = 1
        
        # First round
        for i in range(0, len(teams_without_byes), 2):
            if i + 1 < len(teams_without_byes):
                match = Match.objects.create(
                    tournament=tournament,
                    team1=teams_without_byes[i],
                    team2=teams_without_byes[i + 1],
                    round_name='round_of_32' if bracket_size >= 32 else 'round_of_16',
                    match_number=match_num,
                    status='scheduled'
                )
                matches.append(match)
                match_num += 1
        
        return matches


class LeaderboardManager:
    """Manages leaderboard updates and calculations"""
    
    @staticmethod
    def update_leaderboard(match: Match):
        """Update leaderboard after a match is completed"""
        if match.status != 'completed':
            return
        
        tournament = match.tournament
        
        if tournament.category == 'singles':
            LeaderboardManager._update_singles_leaderboard(match)
        else:
            LeaderboardManager._update_doubles_leaderboard(match)
    
    @staticmethod
    def _update_singles_leaderboard(match: Match):
        """Update leaderboard for singles match"""
        tournament = match.tournament
        
        # Update player 1
        entry1, _ = Leaderboard.objects.get_or_create(
            tournament=tournament,
            player=match.player1,
            defaults={'group_name': match.group_name}
        )
        
        # Update player 2
        entry2, _ = Leaderboard.objects.get_or_create(
            tournament=tournament,
            player=match.player2,
            defaults={'group_name': match.group_name}
        )
        
        # Update stats
        entry1.matches_played += 1
        entry2.matches_played += 1
        
        entry1.points_for += match.score1
        entry1.points_against += match.score2
        entry2.points_for += match.score2
        entry2.points_against += match.score1
        
        if match.winner == match.player1:
            entry1.wins += 1
            entry1.points += tournament.points_per_win
            entry2.losses += 1
            entry2.points += tournament.points_per_loss
        elif match.winner == match.player2:
            entry2.wins += 1
            entry2.points += tournament.points_per_win
            entry1.losses += 1
            entry1.points += tournament.points_per_loss
        else:
            # Draw
            entry1.draws += 1
            entry2.draws += 1
        
        entry1.save()
        entry2.save()
        
        # Recalculate ranks within each group
        LeaderboardManager._recalculate_ranks(tournament, match.group_name)
    
    @staticmethod
    def _update_doubles_leaderboard(match: Match):
        """Update leaderboard for doubles match"""
        tournament = match.tournament
        
        entry1, _ = Leaderboard.objects.get_or_create(
            tournament=tournament,
            team=match.team1,
            defaults={'group_name': match.group_name}
        )
        
        entry2, _ = Leaderboard.objects.get_or_create(
            tournament=tournament,
            team=match.team2,
            defaults={'group_name': match.group_name}
        )
        
        entry1.matches_played += 1
        entry2.matches_played += 1
        
        entry1.points_for += match.score1
        entry1.points_against += match.score2
        entry2.points_for += match.score2
        entry2.points_against += match.score1
        
        if match.winner_team == match.team1:
            entry1.wins += 1
            entry1.points += tournament.points_per_win
            entry2.losses += 1
            entry2.points += tournament.points_per_loss
        elif match.winner_team == match.team2:
            entry2.wins += 1
            entry2.points += tournament.points_per_win
            entry1.losses += 1
            entry1.points += tournament.points_per_loss
        else:
            entry1.draws += 1
            entry2.draws += 1
        
        entry1.save()
        entry2.save()
        
        LeaderboardManager._recalculate_ranks(tournament, match.group_name)
    
    @staticmethod
    def _recalculate_ranks(tournament: Tournament, group_name: str = None):
        """Recalculate ranks for all entries in a group"""
        entries = Leaderboard.objects.filter(tournament=tournament)
        if group_name:
            entries = entries.filter(group_name=group_name)
        
        # Sort by points, then wins, then point differential
        entries = entries.order_by('-points', '-wins', '-matches_played')
        
        for idx, entry in enumerate(entries, 1):
            entry.rank = idx
            entry.save()
    
    @staticmethod
    def get_standings(tournament: Tournament, group_name: str = None):
        """Get current standings for a tournament"""
        entries = Leaderboard.objects.filter(tournament=tournament)
        if group_name:
            entries = entries.filter(group_name=group_name)
        return entries.order_by('rank')
    
    @staticmethod
    def get_top_players(tournament: Tournament, n: int = 4):
        """Get top N players from each group"""
        standings = LeaderboardManager.get_standings(tournament)
        return standings[:n]
