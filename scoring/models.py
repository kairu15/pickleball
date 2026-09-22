from django.db import models
from accounts.models import User
from reservations.models import Reservation


class Match(models.Model):
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    FORMAT_CHOICES = (
        ('singles', 'Singles'),
        ('doubles', 'Doubles'),
        ('mixed_doubles', 'Mixed Doubles'),
    )

    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='match')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')

    # Match details
    match_name = models.CharField(max_length=100, blank=True, null=True)
    team1_player1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team1_matches_as_p1', null=True, blank=True)
    team1_player2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team1_matches_as_p2', null=True, blank=True)
    team2_player1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team2_matches_as_p1', null=True, blank=True)
    team2_player2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team2_matches_as_p2', null=True, blank=True)

    # Match format
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='singles')
    game_type = models.CharField(max_length=20, default='friendly')
    scoring_format = models.CharField(max_length=20, default='11')
    games_to_win = models.IntegerField(default=2)  # best of 3
    points_per_game = models.IntegerField(default=11)  # 11 points win
    win_by_two = models.BooleanField(default=True)
    
    # Team names (optional display labels)
    team1_name = models.CharField(max_length=100, blank=True, null=True)
    team2_name = models.CharField(max_length=100, blank=True, null=True)

    # Match result
    winner_team = models.IntegerField(null=True, blank=True)  # 1 or 2
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'matches'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['reservation']),
        ]
    
    def __str__(self):
        return f"Match #{self.id} - {self.reservation.court.name}"
    
    def get_team1_score(self):
        games = self.games.all()
        wins = sum(1 for game in games if game.winner == 1)
        return wins
    
    def get_team2_score(self):
        games = self.games.all()
        wins = sum(1 for game in games if game.winner == 2)
        return wins
    
    def is_complete(self):
        team1_wins = self.get_team1_score()
        team2_wins = self.get_team2_score()
        return team1_wins >= self.games_to_win or team2_wins >= self.games_to_win


class Game(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='games')
    game_number = models.PositiveIntegerField()
    
    team1_score = models.PositiveIntegerField(default=0)
    team2_score = models.PositiveIntegerField(default=0)
    
    winner = models.IntegerField(null=True, blank=True)  # 1 or 2
    
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'games'
        ordering = ['game_number']
        unique_together = ['match', 'game_number']
    
    def __str__(self):
        return f"Game {self.game_number} - Match #{self.match.id}"


class ScorePoint(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='points')
    team = models.IntegerField(choices=[(1, 'Team 1'), (2, 'Team 2')])
    point_number = models.PositiveIntegerField()
    server = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Position info for pickleball scoring
    server_position = models.IntegerField(default=1)  # 1 or 2 (serving position)
    side_out = models.BooleanField(default=False)  # if this was a side out
    
    scored_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'score_points'
        ordering = ['point_number']


class PlayerStats(models.Model):
    player = models.OneToOneField(User, on_delete=models.CASCADE, related_name='stats')
    
    total_matches = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    
    total_games_played = models.PositiveIntegerField(default=0)
    games_won = models.PositiveIntegerField(default=0)
    
    total_points_scored = models.PositiveIntegerField(default=0)
    total_points_conceded = models.PositiveIntegerField(default=0)
    
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    last_match_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'player_stats'
        indexes = [
            models.Index(fields=['-wins', '-total_matches']),
        ]
    
    def __str__(self):
        return f"{self.player.username} Stats"
    
    def calculate_win_rate(self):
        if self.total_matches > 0:
            self.win_rate = (self.wins / self.total_matches) * 100
        else:
            self.win_rate = 0


class GuestPlayer(models.Model):
    """
    Stores guest player information for matches where the player
    does not have a registered account.
    """
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='guest_players')
    team = models.IntegerField(choices=[(1, 'Team 1'), (2, 'Team 2')])
    player_number = models.IntegerField(choices=[(1, 'Player 1'), (2, 'Player 2')], default=1)
    full_name = models.CharField(max_length=100)
    nickname = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'guest_players'
        verbose_name = 'Guest Player'
        verbose_name_plural = 'Guest Players'

    def __str__(self):
        return f"Guest: {self.full_name} (Match #{self.match_id}, Team {self.team})"

    def get_display_name(self):
        if self.nickname:
            return f"{self.full_name} ({self.nickname})"
        return self.full_name




class MatchSettings(models.Model):
    FORMAT_CHOICES = (
        ('singles', 'Singles'),
        ('doubles', 'Doubles'),
        ('mixed_doubles', 'Mixed Doubles'),
    )

    GAME_TYPE_CHOICES = (
        ('friendly', 'Friendly'),
        ('ranked', 'Ranked'),
        ('practice', 'Practice'),
    )

    SCORING_FORMAT_CHOICES = (
        ('11', '11 Points (Standard)'),
        ('15', '15 Points (Extended)'),
        ('21', '21 Points (Extended)'),
        ('best_of_3', 'Best of 3 Games'),
    )

    name = models.CharField(max_length=100, default="Default Match Settings")
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='singles')
    game_type = models.CharField(max_length=20, choices=GAME_TYPE_CHOICES, default='friendly')
    scoring_format = models.CharField(max_length=20, choices=SCORING_FORMAT_CHOICES, default='11')
    games_to_win = models.IntegerField(default=2)
    points_per_game = models.IntegerField(default=11)
    win_by_two = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'match_settings'
    
    def __str__(self):
        return self.name
