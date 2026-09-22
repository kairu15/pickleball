from django.contrib import admin
from django.utils import timezone
from .models import Tournament, Registration, Match, Team, Leaderboard, MatchNotification, CourtRotation


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'format', 'skill_level', 'status', 'registration_count', 'tournament_start']
    list_filter = ['status', 'category', 'format', 'skill_level', 'created_at']
    search_fields = ['name', 'description']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'format', 'skill_level')
        }),
        ('Dates', {
            'fields': ('registration_start', 'registration_end', 'tournament_start', 'tournament_end')
        }),
        ('Settings', {
            'fields': ('max_participants', 'min_participants', 'players_per_group', 
                      'points_per_win', 'points_per_loss', 'auto_assign_teams')
        }),
        ('Status & Prize', {
            'fields': ('status', 'prize_pool', 'created_by')
        }),
    )


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ['user', 'tournament', 'status', 'skill_level', 'registered_at', 'reviewed_by']
    list_filter = ['status', 'skill_level', 'tournament', 'registered_at']
    search_fields = ['user__username', 'user__email', 'tournament__name']
    date_hierarchy = 'registered_at'
    raw_id_fields = ['user', 'partner', 'reviewed_by']
    
    actions = ['approve_registrations', 'reject_registrations']
    
    def approve_registrations(self, request, queryset):
        queryset.update(status='approved', reviewed_at=timezone.now(), reviewed_by=request.user)
        self.message_user(request, f'{queryset.count()} registrations approved.')
    approve_registrations.short_description = 'Approve selected registrations'
    
    def reject_registrations(self, request, queryset):
        queryset.update(status='rejected', reviewed_at=timezone.now(), reviewed_by=request.user)
        self.message_user(request, f'{queryset.count()} registrations rejected.')
    reject_registrations.short_description = 'Reject selected registrations'


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['tournament', 'match_number', 'get_players', 'round_name', 'score1', 'score2', 
                    'get_winner', 'status', 'scheduled_date', 'court']
    list_filter = ['status', 'round_name', 'tournament', 'scheduled_date']
    search_fields = ['tournament__name', 'player1__username', 'player2__username']
    date_hierarchy = 'scheduled_date'
    raw_id_fields = ['player1', 'player2', 'team1', 'team2', 'winner', 'winner_team', 'court', 'umpire']
    
    def get_players(self, obj):
        if obj.tournament.category == 'singles':
            return f"{obj.player1} vs {obj.player2}" if obj.player1 and obj.player2 else "TBD"
        return f"{obj.team1} vs {obj.team2}" if obj.team1 and obj.team2 else "TBD"
    get_players.short_description = 'Matchup'
    
    def get_winner(self, obj):
        if obj.tournament.category == 'singles':
            return obj.winner
        return obj.winner_team
    get_winner.short_description = 'Winner'


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'tournament', 'player1', 'player2', 'seed', 'is_auto_assigned']
    list_filter = ['tournament', 'is_auto_assigned']
    search_fields = ['name', 'player1__username', 'player2__username']
    raw_id_fields = ['player1', 'player2']


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ['tournament', 'get_name', 'group_name', 'rank', 'matches_played', 'wins', 'losses', 'points']
    list_filter = ['tournament', 'group_name']
    search_fields = ['player__username', 'team__name']
    ordering = ['tournament', 'group_name', 'rank']
    
    def get_name(self, obj):
        if obj.player:
            return obj.player.username
        return obj.team.get_display_name() if obj.team else "Unknown"
    get_name.short_description = 'Player/Team'


@admin.register(MatchNotification)
class MatchNotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'tournament', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'message']
    date_hierarchy = 'created_at'


@admin.register(CourtRotation)
class CourtRotationAdmin(admin.ModelAdmin):
    list_display = ['tournament', 'court', 'level', 'matches_played']
    list_filter = ['tournament', 'level']
