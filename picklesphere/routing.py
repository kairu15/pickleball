"""
WebSocket URL routing for PickleSphere.

Maps WebSocket paths to their respective consumers across apps.
"""
from django.urls import re_path

from notifications.consumers import NotificationConsumer
from scoring.consumers import MatchScoreConsumer
from courts.consumers import CourtAvailabilityConsumer

websocket_urlpatterns = [
    # Live notifications - user-specific channel
    re_path(r'^/ws/notifications/$', NotificationConsumer.as_asgi()),
    
    # Live match scoring - match-specific channel
    re_path(r'^/ws/match/(?P<match_id>\d+)/score/$', MatchScoreConsumer.as_asgi()),
    
    # Live court availability - system-wide channel
    re_path(r'^/ws/courts/availability/$', CourtAvailabilityConsumer.as_asgi()),
]
