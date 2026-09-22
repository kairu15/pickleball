"""
WebSocket consumer for live court availability.

Connected clients receive real-time updates when court availability changes
(e.g., new reservations, cancellations, maintenance status changes).
"""
import json
from datetime import date, datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class CourtAvailabilityConsumer(AsyncWebsocketConsumer):
    """
    Real-time court availability consumer.
    
    Users connect to ws/courts/availability/ and receive updates when
    court availability changes anywhere in the system.
    """

    async def connect(self):
        """Authenticate and join the system-wide court availability group."""
        self.user = self.scope.get('user')
        self.group_name = 'courts_availability'

        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        # Join the court availability group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial court availability data
        courts = await self._get_courts_availability()
        await self.send(text_data=json.dumps({
            'type': 'courts_availability',
            'courts': courts,
            'date': date.today().isoformat(),
        }))

    async def disconnect(self, close_code):
        """Leave the court availability group on disconnect."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming messages (e.g., request refresh)."""
        try:
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'refresh':
                # Send updated court availability
                courts = await self._get_courts_availability()
                await self.send(text_data=json.dumps({
                    'type': 'courts_availability',
                    'courts': courts,
                    'date': date.today().isoformat(),
                }))
            elif action == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))

        except json.JSONDecodeError:
            pass

    async def court_availability_update(self, event):
        """
        Called when court availability changes.
        Sends the update to all connected clients.
        """
        await self.send(text_data=json.dumps({
            'type': 'court_update',
            'court_id': event.get('court_id'),
            'court_name': event.get('court_name'),
            'is_available': event.get('is_available', True),
            'status': event.get('status', 'available'),
            'next_available_slot': event.get('next_available_slot'),
            'timestamp': datetime.now().isoformat(),
        }))

    @database_sync_to_async
    def _get_courts_availability(self):
        """Get current availability for all active courts in the system."""
        try:
            from courts.models import Court
            from reservations.models import Reservation
            today = date.today()
            
            courts_data = []
            courts = Court.objects.filter(
                is_active=True
            ).order_by('name')

            for court in courts:
                # Check if there are any active reservations for today
                active_reservations = Reservation.objects.filter(
                    court=court,
                    date=today,
                    status__in=['pending', 'confirmed']
                ).count()

                courts_data.append({
                    'id': court.id,
                    'name': court.name,
                    'court_type': court.court_type if hasattr(court, 'court_type') else 'standard',
                    'is_available': court.is_available if hasattr(court, 'is_available') else True,
                    'status': court.status if hasattr(court, 'status') else 'active',
                    'active_reservations_today': active_reservations,
                })

            return courts_data
        except Exception:
            return []
