"""
WebSocket consumer for live match scoring.

Players and referees connect to a match-specific channel.
Score updates are broadcast to all connected clients for that match.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class MatchScoreConsumer(AsyncWebsocketConsumer):
    """
    Live match scoring consumer.

    Connected clients receive real-time score updates for a specific match.
    Authorized users (players, referees) can submit score updates.
    """

    async def connect(self):
        """Authenticate and join the match-specific group."""
        self.user = self.scope.get('user')
        self.match_id = self.scope['url_route']['kwargs']['match_id']
        self.group_name = f'match_{self.match_id}'

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Verify the match exists and user has access
        match_data = await self._get_match()
        if not match_data:
            await self.close(code=4004)
            return

        # Store match info for authorization
        self.match_data = match_data

        # Join match group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Augment match data with authorization info
        match_data['is_player'] = await self._is_player()
        match_data['is_staff'] = self.user.is_staff_user()

        # Send current match state on connect
        await self.send(text_data=json.dumps(match_data))

    async def disconnect(self, close_code):
        """Leave the match group on disconnect."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle score updates from authorized users."""
        try:
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'update_score':
                if not await self._can_update_score():
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'You are not authorized to update this match score.',
                    }))
                    return

                team1_score = data.get('team1_score')
                team2_score = data.get('team2_score')
                status = data.get('status')

                success = await self._update_game_score(team1_score, team2_score, status)

                if success:
                    await self.channel_layer.group_send(
                        self.group_name,
                        {
                            'type': 'score_update',
                            'team1_score': team1_score,
                            'team2_score': team2_score,
                            'status': status,
                            'updated_by': self.user.username,
                        }
                    )
                else:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Failed to update match score.',
                    }))

            elif action == 'get_state':
                match_data = await self._get_match()
                if match_data:
                    match_data['is_player'] = await self._is_player()
                    match_data['is_staff'] = self.user.is_staff_user()
                    await self.send(text_data=json.dumps(match_data))

        except json.JSONDecodeError:
            pass

    async def score_update(self, event):
        """Receive score update broadcast and forward to WebSocket client."""
        await self.send(text_data=json.dumps({
            'type': 'score_update',
            'team1_score': event.get('team1_score'),
            'team2_score': event.get('team2_score'),
            'status': event.get('status'),
            'updated_by': event.get('updated_by'),
        }))

    @database_sync_to_async
    def _get_match(self):
        """Get match data from database."""
        try:
            from .models import Match, Game
            from accounts.models import User
            match = Match.objects.select_related(
                'team1_player1', 'team1_player2', 'team2_player1', 'team2_player2'
            ).prefetch_related('games').get(id=self.match_id)

            # Build player name helpers
            def _name(u):
                return u.get_full_name() or u.username if u else 'TBD'

            current_game = match.games.filter(ended_at__isnull=True).first()

            return {
                'type': 'match_state',
                'match_id': self.match_id,
                'match_name': match.match_name or '',
                'status': match.status,
                'format': match.format,
                'game_type': match.game_type,
                'scoring_format': match.scoring_format,
                'games_to_win': match.games_to_win,
                'points_per_game': match.points_per_game,
                'win_by_two': match.win_by_two,
                # Team 1
                'team1_player1_name': _name(match.team1_player1),
                'team1_player2_name': _name(match.team1_player2),
                'team1_player1_id': match.team1_player1_id,
                'team1_player2_id': match.team1_player2_id,
                'team1_wins': match.get_team1_score(),
                # Team 2
                'team2_player1_name': _name(match.team2_player1),
                'team2_player2_name': _name(match.team2_player2),
                'team2_player1_id': match.team2_player1_id,
                'team2_player2_id': match.team2_player2_id,
                'team2_wins': match.get_team2_score(),
                # Current game
                'current_game': {
                    'game_number': current_game.game_number if current_game else None,
                    'team1_score': current_game.team1_score if current_game else 0,
                    'team2_score': current_game.team2_score if current_game else 0,
                } if current_game else None,
                # Authorization flags (filled in by caller)
                'is_player': False,
                'is_staff': False,
            }
        except Exception:
            return None

    @database_sync_to_async
    def _is_player(self):
        """Check if the current user is one of the match players."""
        try:
            from .models import Match
            match = Match.objects.get(id=self.match_id)
            return self.user in [
                match.team1_player1, match.team1_player2,
                match.team2_player1, match.team2_player2
            ]
        except Exception:
            return False

    @database_sync_to_async
    def _can_update_score(self):
        """Check if the current user can update the score."""
        try:
            from .models import Match
            match = Match.objects.get(id=self.match_id)
            if self.user in [
                match.team1_player1, match.team1_player2,
                match.team2_player1, match.team2_player2
            ]:
                return match.status in ('ongoing', 'scheduled')
            if self.user.is_staff_user():
                return True
            return False
        except Exception:
            return False

    @database_sync_to_async
    def _update_game_score(self, team1_score, team2_score, status):
        """Update the current game score in the database."""
        try:
            from .models import Match, Game
            match = Match.objects.get(id=self.match_id)
            current_game = match.games.filter(ended_at__isnull=True).first()

            if current_game:
                if team1_score is not None:
                    current_game.team1_score = team1_score
                if team2_score is not None:
                    current_game.team2_score = team2_score
                current_game.save(update_fields=['team1_score', 'team2_score'])

            if status:
                match.status = status
                if status == 'completed':
                    match.ended_at = timezone.now()
                match.save(update_fields=['status', 'ended_at'])

            return True
        except Exception:
            return False
