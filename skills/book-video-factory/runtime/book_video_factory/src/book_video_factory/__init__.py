"""Reusable foundation for the local book-video factory."""

from .project import PROJECT_DIRECTORIES, initialize_project
from .content_bridge import (
    ContentBridgeError,
    attach_traceability,
    content_system_status,
    export_dbs_content_package,
    import_content_package,
    validate_content_package,
)
from .voice import VoiceProfileError, build_generation_request
from .weread import WeReadClient, collect_book_source_pack
from .style_profiles import (
    DEFAULT_STYLE_PROFILE_ID,
    StyleProfile,
    StyleProfileError,
    available_style_profile_ids,
    load_style_profile,
)

__all__ = [
    "PROJECT_DIRECTORIES",
    "ContentBridgeError",
    "DEFAULT_STYLE_PROFILE_ID",
    "StyleProfile",
    "StyleProfileError",
    "VoiceProfileError",
    "WeReadClient",
    "build_generation_request",
    "attach_traceability",
    "available_style_profile_ids",
    "collect_book_source_pack",
    "content_system_status",
    "export_dbs_content_package",
    "import_content_package",
    "initialize_project",
    "load_style_profile",
    "validate_content_package",
]
