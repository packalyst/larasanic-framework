"""
WebSocket Channels
Defines standard WebSocket message channels
"""
from enum import Enum


class WSChannel(Enum):
    """WebSocket message channels"""

    # General
    BROADCAST = "broadcast"
    NOTIFY = "notify"
    EVENTS = "events"

    # User-specific
    USER_MESSAGE = "user.message"
    USER_NOTIFICATION = "user.notification"

    # System
    SYSTEM_STATUS = "system.status"
    SYSTEM_UPDATE = "system.update"
