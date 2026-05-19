"""agent-launch — draft platform-native release announcements.

Python port of @p-vbordei/agent-launch.
"""

from agent_launch.config import (
    HnPlatform,
    LaunchConfig,
    LaunchConfigError,
    LinkedinPlatform,
    MastodonPlatform,
    Platform,
    Project,
    RedditPlatform,
    XPlatform,
    load_launch_config,
)
from agent_launch.context import ContextError, GatheredContext, gather_context
from agent_launch.draft import DraftResult, draft_one
from agent_launch.platforms import PlatformTemplate, list_platforms, load_platform_template

__version__ = "0.1.0"

__all__ = [
    "ContextError",
    "DraftResult",
    "GatheredContext",
    "HnPlatform",
    "LaunchConfig",
    "LaunchConfigError",
    "LinkedinPlatform",
    "MastodonPlatform",
    "Platform",
    "PlatformTemplate",
    "Project",
    "RedditPlatform",
    "XPlatform",
    "draft_one",
    "gather_context",
    "list_platforms",
    "load_launch_config",
    "load_platform_template",
]
