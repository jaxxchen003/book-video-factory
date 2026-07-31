from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
REPOSITORY = ROOT.parents[3]
EXAMPLES = REPOSITORY / "docs" / "phase-2" / "schemas"
sys.path.insert(0, str(SRC))

from book_video_factory.renderer_contracts import (  # noqa: E402
    ArtifactBinding,
    CanonicalizationError,
    CaptionTimingLevel,
    ContractValidationError,
    PathRootKind,
    PortablePathError,
    PortableRef,
    RenderMode,
    RendererCapability,
    RendererErrorCode,
    RenderStatus,
    RootResolver,
    SnapshotWriteError,
    TimelineAssetKind,
    canonical_json_bytes,
    canonical_json_text,
    canonical_sha256,
    capabilities_from_dict,
    capabilities_to_dict,
    compare_capabilities,
    create_release_snapshot,
    normalize_portable_path,
    release_snapshot_from_dict,
    release_snapshot_to_dict,
    render_request_from_dict,
    render_request_to_dict,
    render_result_from_dict,
    render_result_to_dict,
    request_id_from_hash,
    semantic_request_hash,
    snapshot_filename,
    validate_capabilities,
    validate_release_snapshot,
    validate_render_request,
    validate_render_result,
    validate_request_filesystem,
    validate_request_capabilities,
    validate_request_hash,
    validate_snapshot_hash,
    write_release_snapshot,
)


def load_example(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def valid_request_payload() -> dict:
    payload = load_example("render-request-v1.example.json")
    digest = semantic_request_hash(payload)
    payload["request_hash"] = digest
    payload["request_id"] = request_id_from_hash(digest)
    return payload


def source_binding(name: str, hash_char: str = "b") -> dict:
    return {
        "id": name,
        "version": "1.0",
        "ref": {"root": "project", "path": f"manifests/{name}.json"},
        "sha256": hash_char * 64,
    }


def make_snapshot(*, created_at: str = "2026-07-31T12:00:00Z", metadata: dict | None = None):
    artifact = ArtifactBinding(
        asset_id="asset-1",
        role="approved_script",
        ref=PortableRef("project", "approved/script.json"),
        bytes=10,
        sha256="a" * 64,
        media_type="application/json",
        source_manifest_artifact_id="source-asset-1",
        rights_ref="rights-script",
    )
    return create_release_snapshot(
        project_id="project-1",
        release_id="release-1",
        created_at=created_at,
        profile=source_binding("profile", "b"),
        artifacts=(artifact,),
        timeline_source=source_binding("timeline", "c"),
        audio_source=source_binding("audio", "d"),
        caption_source=source_binding("captions", "e"),
        rights={
            "status": "allowed",
            "policy_version": "1.0",
            "snapshot_ref": {"root": "project", "path": "manifests/rights.json"},
            "snapshot_sha256": "f" * 64,
        },
        approvals={
            "status": "approved",
            "event_ids": ["approval-1"],
            "snapshot_sha256": "1" * 64,
        },
        release_gates={
            "status": "passed",
            "gate_ids": ["script"],
            "policy_version": "1.0",
        },
        source_manifests=(source_binding("project", "2"),),
        metadata=metadata or {"created_by": "unit-test", "notes": "synthetic"},
    )


class SchemaAndModelTests(unittest.TestCase):
    def test_all_four_formal_schemas_parse_as_draft_2020_12(self) -> None:
        names = {
            "render-request-v1.schema.json",
            "render-result-v1.schema.json",
            "renderer-capabilities-v1.schema.json",
            "release-snapshot-v1.schema.json",
        }
        for name in names:
            with self.subTest(name=name):
                payload = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
                self.assertEqual(payload["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertTrue(payload["$id"])
                self.assertTrue(payload["title"])
                self.assertTrue(payload["description"])
                self.assertIn("required", payload)
                self.assertFalse(payload["additionalProperties"])

    def test_required_enums_have_stable_values(self) -> None:
        self.assertEqual(RenderMode.FINAL.value, "final")
        self.assertEqual(RenderStatus.BLOCKED.value, "blocked")
        self.assertEqual(RendererCapability.AUDIO_PLAYBACK.value, "audio_playback")
        self.assertEqual(RendererErrorCode.RENDER_HASH_MISMATCH.value, "RENDER_HASH_MISMATCH")
        self.assertEqual(TimelineAssetKind.SEQUENCE.value, "sequence")
        self.assertEqual(CaptionTimingLevel.WORD.value, "word")
        self.assertEqual(PathRootKind.OUTPUT.value, "output")

    def test_render_request_is_frozen(self) -> None:
        request = render_request_from_dict(valid_request_payload())
        with self.assertRaises(FrozenInstanceError):
            request.request_id = "changed"  # type: ignore[misc]

    def test_nested_mapping_is_immutable(self) -> None:
        request = render_request_from_dict(valid_request_payload())
        with self.assertRaises(TypeError):
            request.output_spec["width"] = 1  # type: ignore[index]

    def test_semantic_identity_properties_map_frozen_phase_2_shape(self) -> None:
        request = render_request_from_dict(valid_request_payload())
        self.assertEqual(request.project_id, "example-project")
        self.assertEqual(request.release_id, "release-001")
        self.assertEqual(request.release_snapshot_hash, "b" * 64)


class SerializationTests(unittest.TestCase):
    def test_request_round_trip_is_exact(self) -> None:
        payload = load_example("render-request-v1.example.json")
        self.assertEqual(render_request_to_dict(render_request_from_dict(payload)), payload)

    def test_result_round_trip_is_exact(self) -> None:
        payload = load_example("render-result-v1.example.json")
        self.assertEqual(render_result_to_dict(render_result_from_dict(payload)), payload)

    def test_capabilities_round_trip_is_exact(self) -> None:
        payload = load_example("renderer-capabilities-v1.example.json")
        self.assertEqual(capabilities_to_dict(capabilities_from_dict(payload)), payload)

    def test_release_snapshot_round_trip_is_exact(self) -> None:
        snapshot = make_snapshot()
        payload = release_snapshot_to_dict(snapshot)
        self.assertEqual(release_snapshot_to_dict(release_snapshot_from_dict(payload)), payload)

    def test_missing_request_field_returns_structured_error(self) -> None:
        payload = valid_request_payload()
        payload.pop("audio")
        with self.assertRaises(ContractValidationError) as caught:
            render_request_from_dict(payload)
        self.assertEqual(caught.exception.issues[0].code, RendererErrorCode.RENDER_INPUT_INVALID)
        self.assertIn("$.audio", {issue.field for issue in caught.exception.issues})

    def test_unknown_request_field_is_rejected(self) -> None:
        payload = valid_request_payload()
        payload["typo_field"] = True
        with self.assertRaises(ContractValidationError):
            render_request_from_dict(payload)

    def test_unknown_capability_is_rejected_during_deserialization(self) -> None:
        payload = load_example("renderer-capabilities-v1.example.json")
        payload["capabilities"]["magic_pixels"] = copy.deepcopy(payload["capabilities"]["still_images"])
        with self.assertRaises(ContractValidationError):
            capabilities_from_dict(payload)

    def test_unicode_paths_survive_round_trip(self) -> None:
        payload = valid_request_payload()
        payload["project"]["manifest_ref"]["path"] = "项目/清单.json"
        self.assertEqual(
            render_request_to_dict(render_request_from_dict(payload))["project"]["manifest_ref"]["path"],
            "项目/清单.json",
        )


class PortablePathTests(unittest.TestCase):
    def test_backslashes_are_normalized(self) -> None:
        self.assertEqual(normalize_portable_path(r"assets\audio\voice.wav"), "assets/audio/voice.wav")

    def test_unicode_relative_path_is_allowed(self) -> None:
        self.assertEqual(normalize_portable_path("资产/人声.wav"), "资产/人声.wav")

    def test_posix_absolute_path_is_rejected(self) -> None:
        with self.assertRaises(PortablePathError):
            normalize_portable_path("/" + "etc/passwd")

    def test_windows_drive_path_is_rejected(self) -> None:
        with self.assertRaises(PortablePathError):
            normalize_portable_path("C" + ":" + chr(92) + "assets" + chr(92) + "voice.wav")

    def test_unc_path_is_rejected(self) -> None:
        with self.assertRaises(PortablePathError):
            normalize_portable_path(chr(92) * 2 + "server" + chr(92) + "share" + chr(92) + "voice.wav")

    def test_parent_traversal_is_rejected(self) -> None:
        with self.assertRaises(PortablePathError):
            normalize_portable_path("assets/../../voice.wav")

    def test_empty_segment_is_rejected(self) -> None:
        with self.assertRaises(PortablePathError):
            normalize_portable_path("assets//voice.wav")

    def test_nul_is_rejected(self) -> None:
        with self.assertRaises(PortablePathError):
            normalize_portable_path("assets/voice\x00.wav")

    def test_root_resolver_resolves_existing_unicode_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "资产" / "人声.wav"
            target.parent.mkdir()
            target.write_bytes(b"voice")
            resolver = RootResolver({"project": root})
            self.assertEqual(resolver.resolve(PortableRef("project", "资产/人声.wav"), require_exists=True), target.resolve())

    def test_undeclared_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            resolver = RootResolver({"project": Path(temp)})
            with self.assertRaises(PortablePathError):
                resolver.resolve(PortableRef("runtime", "config.json"))

    def test_output_on_read_only_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            resolver = RootResolver({"runtime": Path(temp)})
            with self.assertRaises(PortablePathError):
                resolver.resolve_output(PortableRef("runtime", "result.json"))

    def test_symlink_escape_is_rejected_or_explicitly_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / "root"
            outside = base / "outside"
            root.mkdir()
            outside.mkdir()
            link = root / "escape"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"symlink privilege unavailable: {error}")
            resolver = RootResolver({"project": root})
            with self.assertRaises(PortablePathError):
                resolver.resolve(PortableRef("project", "escape/file.json"))


class CanonicalJsonTests(unittest.TestCase):
    def test_key_order_is_canonical(self) -> None:
        self.assertEqual(canonical_json_text({"b": 1, "a": "中"}), '{"a":"中","b":1}')

    def test_utf8_has_no_bom_or_trailing_newline(self) -> None:
        encoded = canonical_json_bytes({"text": "中文"})
        self.assertFalse(encoded.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(encoded.endswith(b"\n"))
        self.assertIn("中文".encode("utf-8"), encoded)

    def test_golden_sha_is_stable(self) -> None:
        self.assertEqual(canonical_sha256({"b": 1, "a": "中"}), "d8158d9a7acf211407d1309876015fc6e69f13b7dd8126a571e429ddce565911")

    def test_enum_path_and_tuple_normalize(self) -> None:
        self.assertEqual(
            canonical_json_text({"mode": RenderMode.FINAL, "path": PurePosixPath("a/b"), "values": (1, 2)}),
            '{"mode":"final","path":"a/b","values":[1,2]}',
        )

    def test_all_floats_are_rejected(self) -> None:
        for value in (1.5, math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaises(CanonicalizationError):
                canonical_json_text({"value": value})

    def test_request_identity_metadata_and_runtime_fields_do_not_change_hash(self) -> None:
        payload = {"semantic": {"value": 1}, "request_id": "one", "request_hash": "a" * 64, "metadata": {"created_at": "one"}}
        baseline = semantic_request_hash(payload)
        payload.update({"request_id": "two", "request_hash": "b" * 64, "metadata": {"created_at": "two"}, "attempt_id": "attempt", "temp_dir": "tmp", "logs": ["x"], "pid": 42, "root_bindings": {"project": "runtime-project-root"}})
        self.assertEqual(semantic_request_hash(payload), baseline)

    def test_semantic_change_changes_request_hash(self) -> None:
        payload = valid_request_payload()
        baseline = semantic_request_hash(payload)
        payload["output"]["target"]["path"] = "08_render_合成/final/other.mp4"
        self.assertNotEqual(semantic_request_hash(payload), baseline)

    def test_request_id_is_derived_from_hash(self) -> None:
        self.assertEqual(request_id_from_hash("a" * 64), "rrq_" + "a" * 24)


class RequestValidationTests(unittest.TestCase):
    def issue_codes(self, payload: dict) -> set[RendererErrorCode]:
        return {issue.code for issue in validate_render_request(render_request_from_dict(payload))}

    def test_phase_2_request_example_passes_semantic_validation(self) -> None:
        request = render_request_from_dict(load_example("render-request-v1.example.json"))
        self.assertEqual(validate_render_request(request), ())

    def test_valid_derived_request_hash_passes_integrity_layer(self) -> None:
        request = render_request_from_dict(valid_request_payload())
        self.assertEqual(validate_request_hash(request), ())

    def test_placeholder_example_hash_is_detected_only_by_integrity_layer(self) -> None:
        request = render_request_from_dict(load_example("render-request-v1.example.json"))
        self.assertEqual(validate_request_hash(request)[0].code, RendererErrorCode.RENDER_HASH_MISMATCH)

    def test_timeline_gap_is_rejected(self) -> None:
        payload = valid_request_payload()
        payload["timeline"]["segments"][1]["start_tick"] += 1
        self.assertIn(RendererErrorCode.RENDER_TIMELINE_INVALID, self.issue_codes(payload))

    def test_first_hold_segment_is_rejected(self) -> None:
        payload = valid_request_payload()
        payload["timeline"]["segments"][0]["visual"] = {"kind": "hold", "asset_ids": [], "motion": "none"}
        self.assertIn(RendererErrorCode.RENDER_TIMELINE_INVALID, self.issue_codes(payload))

    def test_unknown_visual_asset_is_rejected(self) -> None:
        payload = valid_request_payload()
        payload["timeline"]["segments"][0]["visual"]["asset_ids"] = ["missing"]
        self.assertIn(RendererErrorCode.RENDER_ASSET_MISSING, self.issue_codes(payload))

    def test_missing_final_mix_is_rejected(self) -> None:
        payload = valid_request_payload()
        payload["audio"]["final_mix_asset_id"] = "missing"
        self.assertIn(RendererErrorCode.RENDER_AUDIO_INVALID, self.issue_codes(payload))

    def test_caption_word_outside_cue_is_rejected(self) -> None:
        payload = valid_request_payload()
        payload["captions"]["tracks"][0]["cues"][0]["words"][0]["end_tick"] = 6000
        self.assertIn(RendererErrorCode.RENDER_CAPTION_INVALID, self.issue_codes(payload))

    def test_missing_caption_font_fails_closed(self) -> None:
        payload = valid_request_payload()
        payload["captions"]["tracks"][0]["style"]["font_asset_id"] = "missing-font"
        self.assertIn(RendererErrorCode.RENDER_FONT_UNAVAILABLE, self.issue_codes(payload))

    def test_rights_blocked_fails_closed(self) -> None:
        payload = valid_request_payload()
        payload["rights"]["status"] = "blocked"
        self.assertIn(RendererErrorCode.RENDER_RIGHTS_BLOCKED, self.issue_codes(payload))

    def test_required_gate_without_events_fails_closed(self) -> None:
        payload = valid_request_payload()
        payload["approvals"]["satisfied_event_ids"] = []
        self.assertIn(RendererErrorCode.RENDER_GATE_BLOCKED, self.issue_codes(payload))

    def test_unknown_extension_namespace_is_rejected(self) -> None:
        payload = valid_request_payload()
        payload["extensions"] = {"not-reverse-dns": {"schema_version": "1.0"}}
        self.assertIn(RendererErrorCode.RENDER_INPUT_INVALID, self.issue_codes(payload))

    def test_unknown_nested_timeline_field_is_rejected(self) -> None:
        payload = valid_request_payload()
        payload["timeline"]["segments"][0]["renderer_hint"] = "ignore-me"
        self.assertIn(RendererErrorCode.RENDER_TIMELINE_INVALID, self.issue_codes(payload))

    def test_multiple_errors_have_stable_order(self) -> None:
        payload = valid_request_payload()
        payload["rights"]["status"] = "blocked"
        payload["timeline"]["segments"][1]["start_tick"] += 1
        request = render_request_from_dict(payload)
        first = validate_render_request(request)
        second = validate_render_request(request)
        self.assertEqual(first, second)

    def test_request_filesystem_accepts_matching_files(self) -> None:
        payload = valid_request_payload()
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            for asset in payload["assets"]:
                path = project.joinpath(*asset["ref"]["path"].split("/"))
                path.parent.mkdir(parents=True, exist_ok=True)
                content = asset["asset_id"].encode("utf-8")
                path.write_bytes(content)
                asset["bytes"] = len(content)
                asset["sha256"] = hashlib.sha256(content).hexdigest()
            request = render_request_from_dict(payload)
            self.assertEqual(validate_request_filesystem(request, RootResolver({"project": project})), ())

    def test_request_filesystem_detects_hash_mismatch(self) -> None:
        payload = valid_request_payload()
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            for asset in payload["assets"]:
                path = project.joinpath(*asset["ref"]["path"].split("/"))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"actual")
                asset["bytes"] = 6
                asset["sha256"] = "0" * 64
            issues = validate_request_filesystem(render_request_from_dict(payload), RootResolver({"project": project}))
            self.assertIn(RendererErrorCode.RENDER_HASH_MISMATCH, {item.code for item in issues})


class CapabilityAndResultTests(unittest.TestCase):
    def setUp(self) -> None:
        self.capabilities = capabilities_from_dict(load_example("renderer-capabilities-v1.example.json"))

    def test_capability_document_is_valid(self) -> None:
        self.assertEqual(validate_capabilities(self.capabilities), ())

    def test_supported_capability_comparison_is_pure_and_empty(self) -> None:
        self.assertEqual(compare_capabilities((RendererCapability.STILL_IMAGES,), self.capabilities), ())

    def test_request_capability_and_extension_negotiation_passes(self) -> None:
        request = render_request_from_dict(valid_request_payload())
        self.assertEqual(validate_request_capabilities(request, self.capabilities), ())

    def test_undeclared_extension_version_is_blocked(self) -> None:
        payload = valid_request_payload()
        payload["extensions"]["org.book-video-factory.example"]["schema_version"] = "2.0"
        issues = validate_request_capabilities(render_request_from_dict(payload), self.capabilities)
        self.assertEqual(issues[0].code, RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED)

    def test_unsupported_capability_is_blocked(self) -> None:
        issues = compare_capabilities((RendererCapability.VIDEO_CLIPS,), self.capabilities)
        self.assertEqual(issues[0].code, RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED)

    def test_unknown_required_capability_is_not_silently_accepted(self) -> None:
        issues = compare_capabilities(("telepathy",), self.capabilities)
        self.assertEqual(issues[0].code, RendererErrorCode.RENDER_CAPABILITY_UNSUPPORTED)

    def test_phase_2_result_example_is_valid(self) -> None:
        result = render_result_from_dict(load_example("render-result-v1.example.json"))
        self.assertEqual(validate_render_result(result), ())

    def test_succeeded_without_output_is_rejected(self) -> None:
        payload = load_example("render-result-v1.example.json")
        payload["output"] = []
        payload["output_hashes"].pop("local-master")
        issues = validate_render_result(render_result_from_dict(payload))
        self.assertIn(RendererErrorCode.RENDER_OUTPUT_MISSING, {item.code for item in issues})

    def test_failed_without_structured_error_is_rejected(self) -> None:
        payload = load_example("render-result-v1.example.json")
        payload.update({"status": "failed", "output": [], "sidecars": [], "output_hashes": {}, "media_probe": None, "qc_handoff": None})
        issues = validate_render_result(render_result_from_dict(payload))
        self.assertIn(RendererErrorCode.RENDER_INPUT_INVALID, {item.code for item in issues})

    def test_running_cannot_register_terminal_output(self) -> None:
        payload = load_example("render-result-v1.example.json")
        payload.update({"status": "running", "finished_at": None})
        issues = validate_render_result(render_result_from_dict(payload))
        self.assertIn(RendererErrorCode.RENDER_INPUT_INVALID, {item.code for item in issues})

    def test_output_hash_index_mismatch_is_rejected(self) -> None:
        payload = load_example("render-result-v1.example.json")
        payload["output_hashes"]["local-master"] = "0" * 64
        issues = validate_render_result(render_result_from_dict(payload))
        self.assertIn(RendererErrorCode.RENDER_HASH_MISMATCH, {item.code for item in issues})


class ReleaseSnapshotTests(unittest.TestCase):
    def test_snapshot_hash_and_id_are_derived_and_valid(self) -> None:
        snapshot = make_snapshot()
        self.assertEqual(validate_release_snapshot(snapshot), ())
        self.assertEqual(validate_snapshot_hash(snapshot), ())
        self.assertEqual(snapshot.snapshot_id, "rsn_" + snapshot.snapshot_hash[:24])

    def test_created_at_and_metadata_do_not_change_snapshot_hash(self) -> None:
        first = make_snapshot(created_at="2026-07-31T12:00:00Z", metadata={"notes": "one"})
        second = make_snapshot(created_at="2026-08-01T12:00:00Z", metadata={"notes": "two"})
        self.assertEqual(first.snapshot_hash, second.snapshot_hash)

    def test_asset_hash_changes_snapshot_hash(self) -> None:
        first = make_snapshot()
        payload = release_snapshot_to_dict(first)
        payload["artifacts"][0]["sha256"] = "9" * 64
        payload["artifact_hashes"]["asset-1"] = "9" * 64
        payload["snapshot_hash"] = "0" * 64
        changed = release_snapshot_from_dict(payload)
        self.assertNotEqual(validate_snapshot_hash(changed), ())

    def test_blocked_rights_prevent_snapshot_creation(self) -> None:
        with self.assertRaises(ContractValidationError):
            create_release_snapshot(
                project_id="p", release_id="r", created_at="2026-07-31T12:00:00Z",
                profile=source_binding("profile"),
                artifacts=(ArtifactBinding("a", "approved", PortableRef("project", "a"), 1, "a" * 64, "text/plain", "source-a", "rights-a"),),
                timeline_source=source_binding("timeline"), audio_source=source_binding("audio"), caption_source=source_binding("caption"),
                rights={"status": "blocked", "policy_version": "1.0", "snapshot_ref": {"root": "project", "path": "rights.json"}, "snapshot_sha256": "b" * 64},
                approvals={"status": "approved", "event_ids": ["e"], "snapshot_sha256": "c" * 64},
                release_gates={"status": "passed", "gate_ids": ["g"], "policy_version": "1.0"},
                source_manifests=(source_binding("project"),),
            )

    def test_write_once_is_idempotent_for_same_hash_and_bytes(self) -> None:
        snapshot = make_snapshot()
        with tempfile.TemporaryDirectory() as temp:
            first = write_release_snapshot(snapshot, Path(temp))
            second = write_release_snapshot(snapshot, Path(temp))
            self.assertEqual(first, second)
            self.assertEqual(first.read_bytes(), canonical_json_bytes(release_snapshot_to_dict(snapshot)))

    def test_same_snapshot_path_with_different_bytes_fails(self) -> None:
        snapshot = make_snapshot()
        with tempfile.TemporaryDirectory() as temp:
            path = write_release_snapshot(snapshot, Path(temp))
            path.write_bytes(b"tampered")
            with self.assertRaises(SnapshotWriteError):
                write_release_snapshot(snapshot, Path(temp))

    def test_snapshot_write_has_no_bom_newline_or_temp_residue(self) -> None:
        snapshot = make_snapshot()
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            path = write_release_snapshot(snapshot, directory)
            data = path.read_bytes()
            self.assertFalse(data.startswith(b"\xef\xbb\xbf"))
            self.assertFalse(data.endswith(b"\n"))
            self.assertEqual(list(directory.glob("*.tmp")), [])

    def test_snapshot_writer_does_not_modify_stage_manifest(self) -> None:
        snapshot = make_snapshot()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage = root / "stage-manifest.json"
            stage.write_bytes(b'{"immutable":true}')
            before = stage.read_bytes()
            write_release_snapshot(snapshot, root / "snapshots")
            self.assertEqual(stage.read_bytes(), before)

    def test_snapshot_filename_is_content_addressed(self) -> None:
        snapshot = make_snapshot()
        self.assertEqual(snapshot_filename(snapshot), f"release-snapshot-v1-{snapshot.snapshot_hash}.json")


if __name__ == "__main__":
    unittest.main()
