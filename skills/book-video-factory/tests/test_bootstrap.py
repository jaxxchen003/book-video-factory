from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bootstrap = load_script("bootstrap_workspace")
run_cost = load_script("run_cost")


class BootstrapTests(unittest.TestCase):
    def test_bundled_doctor_planning_profile_is_runnable(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/doctor.py"),
                "--profile",
                "planning",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["profile"], "planning")

    def test_workspace_and_project_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            bootstrap.bootstrap_workspace(workspace)
            project, _ = bootstrap.create_project(workspace, "example-book", "Example Book", "Example Author")
            original = (project / "project.json").read_text(encoding="utf-8")
            bootstrap.bootstrap_workspace(workspace)
            bootstrap.create_project(workspace, "example-book", "Changed", "Changed")
            self.assertEqual(original, (project / "project.json").read_text(encoding="utf-8"))
            template = json.loads((project / "02_story_script_故事脚本" / "script.v2.bilingual.template.json").read_text(encoding="utf-8"))
            self.assertEqual(len(template["lines"]), 15)
            self.assertTrue((project / "03_images_生成图片" / "approved" / "v4").is_dir())
            self.assertTrue((workspace / "book_video_factory/scripts/workflow.py").is_file())
            self.assertTrue((workspace / "book_video_factory/scripts/content_bridge.py").is_file())
            self.assertFalse(any((workspace / "book_video_factory").rglob("*.pyc")))
            self.assertTrue((workspace / "book_video_factory/config/release_profiles/book-v4-bilingual-3x4.json").is_file())
            workflow = json.loads(original)["workflow"]
            self.assertEqual(
                workflow["state_source"],
                "derived_gate_evaluator",
            )
            self.assertEqual(workflow["style_profile_id"], "book-editorial-bilingual-v2")
            self.assertEqual(workflow["generation_lane"], "local-renderer")

    def test_vox_style_requires_lane_and_is_initialized_separately(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            bootstrap.bootstrap_workspace(workspace)
            with self.assertRaisesRegex(ValueError, "requires --generation-lane"):
                bootstrap.create_project(
                    workspace,
                    "vox-missing-lane",
                    "Example Book",
                    "Example Author",
                    style_profile_id="paper-collage-explainer-v1",
                )
            project, _ = bootstrap.create_project(
                workspace,
                "vox-example",
                "Example Book",
                "Example Author",
                style_profile_id="paper-collage-explainer-v1",
                generation_lane="google-flow",
            )
            workflow = json.loads(
                (project / "project.json").read_text(encoding="utf-8")
            )["workflow"]
            self.assertEqual(workflow["style_profile_id"], "paper-collage-explainer-v1")
            self.assertEqual(workflow["style_display_name"], "VOX风格图书视频")
            self.assertEqual(workflow["release_profile_id"], "book-vox-vertical-9x16-v1")
            self.assertEqual(workflow["generation_lane"], "google-flow")
            self.assertTrue((project / "03_images_生成图片/collage-broll").is_dir())
            with self.assertRaisesRegex(ValueError, "does not support workflow mode"):
                bootstrap.create_project(
                    workspace,
                    "vox-content-backed",
                    "Example Book",
                    "Example Author",
                    mode="content-system-backed",
                    style_profile_id="paper-collage-explainer-v1",
                    generation_lane="google-flow",
                )

    def test_content_system_mode_is_available_from_clean_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            bootstrap.bootstrap_workspace(workspace)
            project, _ = bootstrap.create_project(
                workspace,
                "content-backed",
                "Example Book",
                "Example Author",
                "content-system-backed",
            )
            payload = json.loads((project / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["workflow"]["mode"], "content-system-backed")
            self.assertTrue((project / "01_research_资料搜集/content_system/imports").is_dir())
            self.assertTrue((project / "02_story_script_故事脚本/traceability").is_dir())

    def test_existing_project_rejects_conflicting_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            bootstrap.bootstrap_workspace(workspace)
            bootstrap.create_project(
                workspace,
                "content-backed",
                "Example Book",
                "Example Author",
                "content-system-backed",
            )
            with self.assertRaisesRegex(ValueError, "already uses workflow mode"):
                bootstrap.create_project(
                    workspace,
                    "content-backed",
                    "Example Book",
                    "Example Author",
                    "single-book",
                )

    def test_existing_project_rejects_style_release_profile_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            bootstrap.bootstrap_workspace(workspace)
            project, _ = bootstrap.create_project(
                workspace,
                "vox-example",
                "Example Book",
                "Example Author",
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
            with self.assertRaisesRegex(ValueError, "release profile"):
                bootstrap.create_project(
                    workspace,
                    "vox-example",
                    "Example Book",
                    "Example Author",
                    style_profile_id="paper-collage-explainer-v1",
                    generation_lane="google-flow",
                )

    def test_slug_rejects_unsafe_values(self) -> None:
        with self.assertRaises(Exception):
            bootstrap.valid_slug("../unsafe")


class LedgerTests(unittest.TestCase):
    def test_unknown_tokens_are_rendered_as_dash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            warehouse = Path(temporary) / "book_video_warehouse"
            run_cost.append_event(
                warehouse,
                {"project_slug": "example-book", "images_generated": 12, "music_jobs": 1, "voice_seconds": 42, "render_seconds": 50, "retries": 0},
            )
            events = run_cost.read_events(warehouse)
            self.assertEqual(run_cost.token_value(events, "codex_input_tokens"), "—")
            self.assertEqual(run_cost.aggregate(events)["images_generated"], 12)


if __name__ == "__main__":
    unittest.main()
