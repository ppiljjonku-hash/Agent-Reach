# -*- coding: utf-8 -*-
"""
Channel registry — every platform exposed by `agent-reach <channel> <action>`.
"""

from typing import List, Optional

from .base import Channel
from .reddit import RedditChannel
from .twitter import TwitterChannel
from .youtube import YouTubeChannel

ALL_CHANNELS: List[Channel] = [
    TwitterChannel(),
    YouTubeChannel(),
    RedditChannel(),
]


def get_channel(name: str) -> Optional[Channel]:
    """Get a channel by name."""
    for ch in ALL_CHANNELS:
        if ch.name == name:
            return ch
    return None


def get_all_channels() -> List[Channel]:
    """Get all registered channels."""
    return ALL_CHANNELS


__all__ = [
    "Channel",
    "ALL_CHANNELS",
    "get_channel",
    "get_all_channels",
]
