from django.contrib import admin
from .models import Match, Game, ScorePoint, PlayerStats, MatchSettings


class GameInline(admin.TabularInline):
    model = Game
    extra = 0


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['id', 'reservation', 'status', 'format', 'started_at', 'ended_at']
    list_filter = ['status', 'format']
    search_fields = ['reservation__user__username', 'reservation__court__name']
    inlines = [GameInline]


@admin.register(PlayerStats)
class PlayerStatsAdmin(admin.ModelAdmin):
    list_display = ['player', 'total_matches', 'wins', 'losses', 'win_rate']
    search_fields = ['player__username']


@admin.register(MatchSettings)
class MatchSettingsAdmin(admin.ModelAdmin):
    list_display = ['name', 'format', 'games_to_win', 'points_per_game', 'win_by_two', 'is_active']
    list_editable = ['is_active']
