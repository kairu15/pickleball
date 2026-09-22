"""
WebSocket consumer for real-time notifications.

Each authenticated user connects to their own notification channel.
When a notification is created for them, it's pushed instantly via WebSocket.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Real-time notification consumer.
    
    Users connect to ws/notifications/ and receive notifications
    pushed to their user-specific group.
    """

    async def connect(self):
        """Authenticate the user and add them to their notification group."""
        self.user = self.scope.get('user')
        
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return
        
        # Create a unique group name for this user
        self.group_name = f'notifications_{self.user.id}'
        
        # Join the user's notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial unread count
        unread_count = await self._get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count,
        }))

    async def disconnect(self, close_code):
        """Leave the notification group on disconnect."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming messages from WebSocket (e.g., mark as read)."""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'mark_read':
                notification_id = data.get('notification_id')
                if notification_id:
                    await self._mark_notification_read(notification_id)
                    unread_count = await self._get_unread_count()
                    await self.send(text_data=json.dumps({
                        'type': 'unread_count',
                        'count': unread_count,
                    }))
            elif action == 'mark_all_read':
                await self._mark_all_read()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': 0,
                }))
            elif action == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
        except json.JSONDecodeError:
            pass

    async def send_notification(self, event):
        """
        Called when a notification is pushed to the group.
        Sends the notification data to the WebSocket client.
        """
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'id': event.get('id'),
            'title': event.get('title', ''),
            'message': event.get('message', ''),
            'notification_type': event.get('notification_type', 'info'),
            'category': event.get('category', 'system'),
            'priority': event.get('priority', 'normal'),
            'action_url': event.get('action_url', ''),
            'action_text': event.get('action_text', 'View Details'),
            'created_at': event.get('created_at', ''),
            'unread_count': event.get('unread_count', 0),
        }))

    @database_sync_to_async
    def _get_unread_count(self):
        """Get the unread notification count for the current user."""
        from .models import Notification
        return Notification.objects.filter(
            user=self.user, is_read=False, is_deleted=False
        ).count()

    @database_sync_to_async
    def _mark_notification_read(self, notification_id):
        """Mark a single notification as read."""
        from .models import Notification
        try:
            notification = Notification.objects.get(
                id=notification_id, user=self.user
            )
            notification.mark_as_read()
        except Notification.DoesNotExist:
            pass

    @database_sync_to_async
    def _mark_all_read(self):
        """Mark all notifications as read for the current user."""
        from .models import Notification
        Notification.objects.filter(
            user=self.user, is_read=False, is_deleted=False
        ).update(is_read=True)
