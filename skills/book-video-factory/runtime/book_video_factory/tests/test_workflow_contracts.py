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


class GateTests(unittest.TestCase):
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
