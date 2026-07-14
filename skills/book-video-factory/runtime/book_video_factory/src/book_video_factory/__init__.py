"""Reusable foundation for the local book-video factory."""

from .project import PROJECT_DIRECTORIES, initialize_project
from .voice import VoiceProfileError, build_generation_request
from .weread import WeReadClient, collect_book_source_pack

__all__ = [
    "PROJECT_DIRECTORIES",
    "VoiceProfileError",
    "WeReadClient",
    "build_generation_request",
    "collect_book_source_pack",
    "initialize_project",
]
