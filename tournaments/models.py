import random
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Tournament(models.Model):
    FORMAT_CHOICES = (
        ('round_robin', 'Round Robin'),
        ('single_elimination', 'Single Elimination'),
        ('double_elimination', 'Double Elimination'),
        ('mixed_doubles', 'Mixed Doubles'),
        ('king_queen', 'King/Queen of the Court'),
    )
    
    CATEGORY_CHOICES = (
        ('singles', 'Singles (1v1)'),
        ('doubles', 'Doubles (2v2)'),
        ('mixed_doubles', 'Mixed Doubles'),
    )
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('registration_open', 'Registration Open'),
        ('registration_closed', 'Registration Closed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    SKILL_LEVEL_CHOICES = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('all_levels', 'All Levels'),
    )
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES)
    skill_level = models.CharField(max_length=20, choices=SKILL_LEVEL_CHOICES, default='beginner')
    
    # Dates
    registration_start = models.DateTimeField()
    registration_end = models.DateTimeField()
    tournament_start = models.DateTimeField()
    tournament_end = models.DateTimeField(null=True, blank=True)
    
    # Settings
    max_participants = models.PositiveIntegerField(default=32)
    min_participants = models.PositiveIntegerField(default=4)
    players_per_group = models.PositiveIntegerField(default=4, help_text="For Round Robin groups")
    points_per_win = models.PositiveIntegerField(default=3)
    points_per_loss = models.PositiveIntegerField(default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Auto-assign teams for doubles
    auto_assign_teams = models.BooleanField(default=True, help_text="Auto-randomize teams for doubles")
    
    # Prize
    prize_pool = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, blank=True)
    
    # Created by
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_tournaments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tournaments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['tournament_start', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"
    
    @property
    def is_registration_open(self):
        return self.status == 'registration_open'
    
    @property
    def registration_count(self):
        return self.registrations.filter(status='approved').count()
    
    @property
    def pending_count(self):
        return self.registrations.filter(status='pending').count()
    
    def can_generate_matches(self):
        approved = self.registrations.filter(status='approved').count()
        return approved >= self.min_participants


class Team(models.Model):
    """For doubles tournaments - teams of 2 players"""
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='teams')
    name = models.CharField(max_length=100, blank=True, null=True)
    player1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teams_as_player1')
    player2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teams_as_player2', null=True, blank=True)
    seed = models.PositiveIntegerField(null=True, blank=True)
    is_auto_assigned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tournament_teams'
        ordering = ['seed', 'name']
    
    def __str__(self):
        if self.name:
            return self.name
        if self.player2:
            return f"{self.player1.username} & {self.player2.username}"
        return f"{self.player1.username} (Solo)"
    
    def get_display_name(self):
        return self.name or self.__str__()


class Registration(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    )
    
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('prefer_not_say', 'Prefer not to say'),
    )
    
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tournament_registrations')
    
    # Registration details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    skill_level = models.CharField(max_length=20, choices=Tournament.SKILL_LEVEL_CHOICES, default='beginner')
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, null=True)
    
    # For doubles - if user brings a partner
    partner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='partner_registrations')
    partner_name = models.CharField(max_length=100, blank=True, null=True, help_text="External partner name if not a system user")
    
    # Assigned team after approval
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='registrations')
    
    # Admin notes
    admin_notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    registered_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_registrations')
    
    class Meta:
        db_table = 'tournament_registrations'
        unique_together = ['tournament', 'user']
        ordering = ['-registered_at']
        indexes = [
            models.Index(fields=['tournament', 'status']),
            models.Index(fields=['user', '-registered_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.tournament.name} ({self.status})"


class Match(models.Model):
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    )
    
    ROUND_CHOICES = (
        ('group_stage', 'Group Stage'),
        ('round_of_32', 'Round of 32'),
        ('round_of_16', 'Round of 16'),
        ('quarter_final', 'Quarter Final'),
        ('semi_final', 'Semi Final'),
        ('final', 'Final'),
        ('third_place', '3rd Place Match'),
        ('winners_bracket', 'Winners Bracket'),
        ('losers_bracket', 'Losers Bracket'),
        ('qualifier', 'Qualifier'),
    )
    
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='matches')
    
    # For Singles
    player1 = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='matches_as_player1')
    player2 = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='matches_as_player2')
    
    # For Doubles
    team1 = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True, related_name='matches_as_team1')
    team2 = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True, related_name='matches_as_team2')
    
    # Match details
    round_name = models.CharField(max_length=20, choices=ROUND_CHOICES, default='group_stage')
    group_name = models.CharField(max_length=10, blank=True, null=True, help_text="e.g., A, B, C for round robin groups")
    match_number = models.PositiveIntegerField(default=1)
    
    # Scores
    score1 = models.PositiveIntegerField(default=0)
    score2 = models.PositiveIntegerField(default=0)
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_matches')
    winner_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_matches')
    
    # Scheduling
    court = models.ForeignKey('courts.Court', on_delete=models.SET_NULL, null=True, blank=True, related_name='tournament_matches')
    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_time = models.TimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=60)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Bracket positioning (for elimination tournaments)
    bracket_position = models.PositiveIntegerField(null=True, blank=True)
    next_match = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='previous_matches')
    is_winners_bracket = models.BooleanField(default=True)  # For double elimination
    
    # Additional data
    notes = models.TextField(blank=True, null=True)
    umpire = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='umpired_matches')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'tournament_matches'
        ordering = ['tournament', 'scheduled_date', 'scheduled_time', 'match_number']
        indexes = [
            models.Index(fields=['tournament', 'status']),
            models.Index(fields=['scheduled_date', 'status']),
            models.Index(fields=['court', 'scheduled_date']),
        ]
    
    def __str__(self):
        if self.tournament.category == 'singles' and self.player1 and self.player2:
            return f"{self.player1.username} vs {self.player2.username} - {self.tournament.name}"
        elif self.team1 and self.team2:
            return f"{self.team1.get_display_name()} vs {self.team2.get_display_name()} - {self.tournament.name}"
        return f"Match {self.match_number} - {self.tournament.name}"
    
    def get_player1_display(self):
        if self.tournament.category == 'singles':
            return self.player1.get_full_name() or self.player1.username if self.player1 else "TBD"
        return self.team1.get_display_name() if self.team1 else "TBD"
    
    def get_player2_display(self):
        if self.tournament.category == 'singles':
            return self.player2.get_full_name() or self.player2.username if self.player2 else "TBD"
        return self.team2.get_display_name() if self.team2 else "TBD"
    
    def get_winner_display(self):
        if self.tournament.category == 'singles':
            return self.winner.get_full_name() or self.winner.username if self.winner else None
        return self.winner_team.get_display_name() if self.winner_team else None


class Leaderboard(models.Model):
    """Tracks standings for round robin tournaments"""
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='leaderboard_entries')
    
    # For Singles
    player = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='leaderboard_entries')
    
    # For Doubles
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True, related_name='leaderboard_entries')
    
    # Stats
    group_name = models.CharField(max_length=10, blank=True, null=True)
    matches_played = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    points_for = models.PositiveIntegerField(default=0)
    points_against = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=0)
    
    # Rank
    rank = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'tournament_leaderboard'
        ordering = ['tournament', 'group_name', '-points', '-wins', 'rank']
    
    def __str__(self):
        name = self.player.username if self.player else self.team.get_display_name() if self.team else "Unknown"
        return f"{name} - {self.tournament.name} ({self.points} pts)"
    
    @property
    def point_differential(self):
        return self.points_for - self.points_against


class MatchNotification(models.Model):
    """Notifications for tournament participants"""
    NOTIFICATION_TYPES = (
        ('registration_approved', 'Registration Approved'),
        ('registration_rejected', 'Registration Rejected'),
        ('match_scheduled', 'Match Scheduled'),
        ('match_reminder', 'Match Reminder'),
        ('match_completed', 'Match Completed'),
        ('tournament_start', 'Tournament Starting'),
        ('tournament_complete', 'Tournament Complete'),
        ('round_complete', 'Round Complete'),
    )
    
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='notifications')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tournament_notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    match = models.ForeignKey(Match, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tournament_notifications'
        ordering = ['-created_at']


class CourtRotation(models.Model):
    """For King/Queen of the Court format"""
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='court_rotations')
    court = models.ForeignKey('courts.Court', on_delete=models.CASCADE)
    
    # Current occupants
    current_players = models.ManyToManyField(User, blank=True, related_name='current_court_rotations')
    current_teams = models.ManyToManyField(Team, blank=True, related_name='current_court_rotations')
    
    # Rotation level (higher = champions court)
    level = models.PositiveIntegerField(default=1)
    
    # Stats
    matches_played = models.PositiveIntegerField(default=0)
    champions_count = models.PositiveIntegerField(default=0)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'court_rotations'
        ordering = ['tournament', '-level']
