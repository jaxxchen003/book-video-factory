from __future__ import annotations

import importlib.util
import json
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
    def test_workspace_and_project_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            bootstrap.bootstrap_workspace(workspace)
            project, _ = bootstrap.create_project(workspace, "example-book", "Example Book", "Example Author")
            original = (project / "project.json").read_text(encoding="utf-8")
            bootstrap.bootstrap_workspace(workspace)
            bootstrap.create_project(workspace, "example-book", "Changed", "Changed")
            self.assertEqual(original, (project / "project.json").read_text(encoding="utf-8"))
            template = json.loads((project / "02_story_script" / "script.v2.bilingual.template.json").read_text(encoding="utf-8"))
            self.assertEqual(len(template["lines"]), 15)
            self.assertTrue((project / "03_images" / "approved" / "v4").is_dir())

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
