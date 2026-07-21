from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from book_video_factory.contracts import ContractError, ReleaseProfile  # noqa: E402
from book_video_factory.gates import approval_is_current, evaluate_workflow_state  # noqa: E402
from book_video_factory.manifests import (  # noqa: E402
    record_approval,
    write_stage_manifest,
)
from book_video_factory.project import initialize_project  # noqa: E402
from book_video_factory.style_profiles import (  # noqa: E402
    StyleProfile,
    StyleProfileError,
    load_style_profile,
    project_workflow,
)


class ReleaseProfileTests(unittest.TestCase):
    def test_contract_schemas_are_valid_json(self) -> None:
        for path in sorted((ROOT / "schemas").glob("*.schema.json")):
            with self.subTest(path=path.name):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_v4_profile_is_valid(self) -> None:
        profile = ReleaseProfile.load(
            ROOT / "config/release_profiles/book-v4-bilingual-3x4.json"
        )
        self.assertEqual(profile.profile_id, "book-v4-bilingual-3x4")
        self.assertEqual(profile.title_max_width, 608)

    def test_vox_release_and_both_style_profiles_are_valid(self) -> None:
        vox_release = ReleaseProfile.load(
            ROOT / "config/release_profiles/book-vox-vertical-9x16-v1.json"
        )
        self.assertEqual(vox_release.renderer, "external_clip_timeline_v1")
        self.assertEqual(
            vox_release.asset_manifest,
            "03_images_生成图片/collage-broll/video-assets-v1.json",
        )
        original = load_style_profile("book-editorial-bilingual-v2")
        vox = load_style_profile("paper-collage-explainer-v1")
        self.assertIsInstance(original, StyleProfile)
        self.assertEqual(original.release_profile_id, "book-v4-bilingual-3x4")
        self.assertEqual(vox.display_name_zh, "VOX风格图书视频")
        self.assertEqual(vox.release_profile_id, "book-vox-vertical-9x16-v1")

    def test_invalid_title_safe_box_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "profile.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "profile_id": "bad",
                        "renderer": "build_batch_video_v3",
                        "canvas": {"width": 720, "height": 960, "fps": 30},
                        "script": {"language_mode": "bilingual", "line_count": 15},
                        "visual": {"scene_count": 12, "scene_format": "png"},
                        "typography": {
                            "title_safe_margin_x_px": 56,
                            "title_max_width_px": 700,
                            "title_max_lines": 2,
                            "title_max_font_size_px": 70,
                            "title_min_font_size_px": 34,
                        },
                        "video": {"codec": "h264"},
                        "audio": {"codec": "aac"},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ContractError):
                ReleaseProfile.load(path)


class ManifestTests(unittest.TestCase):
    def test_stage_manifest_is_immutable_and_hashes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            source = project / "input.txt"
            output = project / "output.txt"
            source.write_text("source", encoding="utf-8")
            output.write_text("output", encoding="utf-8")
            first = write_stage_manifest(
                project,
                stage="render",
                release_id="v1-r1",
                release_profile_id="book-v4-bilingual-3x4",
                inputs=[("script", source)],
                outputs=[("local_master", output)],
                checks=[{"id": "smoke", "result": "pass", "severity": "error"}],
                manifest_id="fixed-id",
                recorded_at="2026-07-14T00:00:00+00:00",
            )
            payload = json.loads(first.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["inputs"][0]["sha256"]), 64)
            with self.assertRaises(FileExistsError):
                write_stage_manifest(
                    project,
                    stage="render",
                    release_id="v1-r1",
                    release_profile_id="book-v4-bilingual-3x4",
                    inputs=[("script", source)],
                    outputs=[("local_master", output)],
                    checks=[],
                    manifest_id="fixed-id",
                    recorded_at="2026-07-14T00:00:00+00:00",
                )

    def test_approval_becomes_stale_when_subject_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            script = project / "script.json"
            script.write_text('{"version": 1}', encoding="utf-8")
            event_path = record_approval(
                project,
                release_id="v1-r1",
                gate="script",
                decision="approved",
                reviewer="human-reviewer",
                subjects=[script],
                event_id="approval-1",
                reviewed_at="2026-07-14T00:00:00+00:00",
            )
            event = json.loads(event_path.read_text(encoding="utf-8"))
            self.assertTrue(approval_is_current(project, event))
            script.write_text('{"version": 2}', encoding="utf-8")
            self.assertFalse(approval_is_current(project, event))

    def test_stage_manifest_rejects_symlinked_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "project"
            project.mkdir()
            source = project / "input.txt"
            output = project / "output.txt"
            source.write_text("source", encoding="utf-8")
            output.write_text("output", encoding="utf-8")
            outside = root / "outside"
            outside.mkdir()
            manifests = project / "manifests"
            manifests.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                write_stage_manifest(
                    project,
                    stage="render",
                    release_id="v1-r1",
                    release_profile_id="book-v4-bilingual-3x4",
                    inputs=[("script", source)],
                    outputs=[("master", output)],
                    checks=[],
                )
            self.assertEqual(list(outside.iterdir()), [])


class GateTests(unittest.TestCase):
    def test_vox_project_uses_its_own_release_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = initialize_project(
                Path(temp),
                "vox-sample",
                "样书",
                "作者",
                style_profile_id="paper-collage-explainer-v1",
                generation_lane="gemini-api",
            )
            profile = ReleaseProfile.load(
                ROOT / "config/release_profiles/book-vox-vertical-9x16-v1.json"
            )
            result = evaluate_workflow_state(project, profile)
            self.assertEqual(result["derived_state"], "draft")
            self.assertEqual(result["style_profile_id"], "paper-collage-explainer-v1")
            self.assertEqual(result["style_display_name"], "VOX风格图书视频")
            self.assertTrue(result["release_profile_aligned"])

            legacy = ReleaseProfile.load(
                ROOT / "config/release_profiles/book-v4-bilingual-3x4.json"
            )
            mismatch = evaluate_workflow_state(project, legacy)
            self.assertEqual(mismatch["derived_state"], "invalid")
            self.assertFalse(mismatch["release_profile_aligned"])

    def test_project_workflow_rejects_recorded_style_release_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = initialize_project(
                Path(temp),
                "vox-sample",
                "样书",
                "作者",
                style_profile_id="paper-collage-explainer-v1",
                generation_lane="google-flow",
            )
            contract_path = project / "project.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["workflow"]["release_profile_id"] = "book-v4-bilingual-3x4"
            contract_path.write_text(
                json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(StyleProfileError, "incompatible profile"):
                project_workflow(project)

    def test_same_timestamp_gate_decisions_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = initialize_project(Path(temp), "sample", "样书", "作者")
            topic = project / "00_topic_选题/topic.json"
            topic.write_text('{"approved": true}', encoding="utf-8")
            timestamp = "2026-07-14T00:00:00+00:00"
            record_approval(
                project,
                release_id="v1-r1",
                gate="topic",
                decision="approved",
                reviewer="human",
                subjects=[topic],
                event_id="approval-a",
                reviewed_at=timestamp,
            )
            record_approval(
                project,
                release_id="v1-r1",
                gate="topic",
                decision="revoked",
                reviewer="human",
                subjects=[topic],
                event_id="approval-b",
                reviewed_at=timestamp,
            )
            profile = ReleaseProfile.load(
                ROOT / "config/release_profiles/book-v4-bilingual-3x4.json"
            )
            result = evaluate_workflow_state(project, profile, release_id="v1-r1")
            self.assertEqual(result["derived_state"], "draft")
            self.assertNotIn("topic", result["current_approval_gates"])

    def test_release_scope_never_combines_approvals_from_two_releases(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = initialize_project(Path(temp), "sample", "样书", "作者")
            topic = project / "00_topic_选题/topic.json"
            script = project / "02_story_script_故事脚本/script.v2.bilingual.json"
            topic.write_text('{"approved": true}', encoding="utf-8")
            script.write_text('{"lines": []}', encoding="utf-8")
            record_approval(
                project,
                release_id="v1-r1",
                gate="topic",
                decision="approved",
                reviewer="human",
                subjects=[topic],
            )
            record_approval(
                project,
                release_id="v2-r1",
                gate="script",
                decision="approved",
                reviewer="human",
                subjects=[script],
            )
            profile = ReleaseProfile.load(
                ROOT / "config/release_profiles/book-v4-bilingual-3x4.json"
            )
            ambiguous = evaluate_workflow_state(project, profile)
            self.assertIsNone(ambiguous["release_id"])
            self.assertFalse(ambiguous["release_scope_valid"])
            self.assertEqual(ambiguous["derived_state"], "invalid")
            old_release = evaluate_workflow_state(project, profile, release_id="v1-r1")
            self.assertEqual(old_release["derived_state"], "topic_approved")
            self.assertEqual(old_release["current_approval_gates"], ["topic"])

    def test_qc_report_must_match_active_release(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = initialize_project(Path(temp), "sample", "样书", "作者")
            qc = project / "09_qc_质检/v4_release_gate.json"
            qc.write_text(
                json.dumps({"release_id": "v1-r1", "local_master_status": "pass"}),
                encoding="utf-8",
            )
            profile = ReleaseProfile.load(
                ROOT / "config/release_profiles/book-v4-bilingual-3x4.json"
            )
            self.assertTrue(
                evaluate_workflow_state(project, profile, release_id="v1-r1")["qc_passed"]
            )
            self.assertFalse(
                evaluate_workflow_state(project, profile, release_id="v2-r1")["qc_passed"]
            )

    def test_project_status_cannot_bypass_derived_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = initialize_project(Path(temp), "sample", "样书", "作者")
            project_json = project / "project.json"
            payload = json.loads(project_json.read_text(encoding="utf-8"))
            payload["status"] = "ready_to_publish"
            project_json.write_text(json.dumps(payload), encoding="utf-8")
            result = evaluate_workflow_state(
                project,
                ReleaseProfile.load(
                    ROOT / "config/release_profiles/book-v4-bilingual-3x4.json"
                ),
            )
            self.assertEqual(result["derived_state"], "draft")
            self.assertFalse(result["ready_to_publish"])


if __name__ == "__main__":
    unittest.main()
