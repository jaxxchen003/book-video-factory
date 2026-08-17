"""Stable string enums for Renderer Contract v1."""

from __future__ import annotations

from enum import Enum


class StableStringEnum(str, Enum):
    """Enum whose persisted value is its stable lowercase contract token."""

    def __str__(self) -> str:
        return self.value


class RenderMode(StableStringEnum):
    PREVIEW = "preview"
    FINAL = "final"


class RenderStatus(StableStringEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class RendererCapability(StableStringEnum):
    STILL_IMAGES = "still_images"
    LAYERED_IMAGES = "layered_images"
    VIDEO_CLIPS = "video_clips"
    CAPTIONS = "captions"
    WORD_HIGHLIGHT = "word_highlight"
    CAMERA_MOTION = "camera_motion"
    VECTOR_OVERLAYS = "vector_overlays"
    AUDIO_PLAYBACK = "audio_playback"
    AUDIO_MIXING = "audio_mixing"
    WAVEFORM = "waveform"
    TRANSITIONS = "transitions"
    PREVIEW = "preview"
    DETERMINISTIC_RENDER = "deterministic_render"


class RendererErrorCode(StableStringEnum):
    RENDER_INPUT_INVALID = "RENDER_INPUT_INVALID"
    RENDER_ASSET_MISSING = "RENDER_ASSET_MISSING"
    RENDER_HASH_MISMATCH = "RENDER_HASH_MISMATCH"
    RENDER_CAPABILITY_UNSUPPORTED = "RENDER_CAPABILITY_UNSUPPORTED"
    RENDER_GATE_BLOCKED = "RENDER_GATE_BLOCKED"
    RENDER_RIGHTS_BLOCKED = "RENDER_RIGHTS_BLOCKED"
    RENDER_TIMELINE_INVALID = "RENDER_TIMELINE_INVALID"
    RENDER_AUDIO_INVALID = "RENDER_AUDIO_INVALID"
    RENDER_CAPTION_INVALID = "RENDER_CAPTION_INVALID"
    RENDER_FONT_UNAVAILABLE = "RENDER_FONT_UNAVAILABLE"
    RENDER_PROCESS_FAILED = "RENDER_PROCESS_FAILED"
    RENDER_OUTPUT_MISSING = "RENDER_OUTPUT_MISSING"
    RENDER_PROBE_FAILED = "RENDER_PROBE_FAILED"
    RENDER_CANCELLED = "RENDER_CANCELLED"


class TimelineAssetKind(StableStringEnum):
    STILL = "still"
    SEQUENCE = "sequence"
    VIDEO = "video"
    HOLD = "hold"
    SOLID = "solid"


class CaptionTimingLevel(StableStringEnum):
    PHRASE = "phrase"
    SENTENCE = "sentence"
    WORD = "word"


class PathRootKind(StableStringEnum):
    WORKSPACE = "workspace"
    PROJECT = "project"
    RELEASE = "release"
    ARTIFACT = "artifact"
    OUTPUT = "output"
    RUNTIME = "runtime"
    FONT_RESOURCES = "font_resources"
