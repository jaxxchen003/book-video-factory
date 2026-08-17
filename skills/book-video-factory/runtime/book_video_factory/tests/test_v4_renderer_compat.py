from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from book_video_factory.manifests import record_approval  # noqa: E402
from book_video_factory.renderer_contracts import (  # noqa: E402
    CommandResult,
    ContractPersistenceError,
    ContractValidationError,
    LegacyV4Renderer,
    PortableRef,
    RenderExecutionContext,
    RendererErrorCode,
    RenderStatus,
    RootResolver,
    collect_v4_release,
    map_v4_snapshot_to_request,
    render_request_from_dict,
    render_request_to_dict,
    request_id_from_hash,
    semantic_request_hash,
    validate_render_request,
    validate_request_hash,
    write_render_request,
)


RELEASE_ID = "release-v4-test"
CREATED_AT = "2026-08-01T00:00:00Z"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_wave(path: Path, duration_ticks: int = 10_000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(1)
        output.setframerate(1000)
        output.writeframes(b"\x80" * duration_ticks)


class V4Fixture:
    def __init__(self, base: Path, *, approval_release_id: str = RELEASE_ID) -> None:
        self.project = base / "synthetic-v4"
        self.project.mkdir(parents=True)
        _write_json(
            self.project / "project.json",
            {
                "schema_version": "1.0",
                "project_id": self.project.name,
                "book": {"title": "测试书", "author": "测试作者"},
                "workflow": {
                    "mode": "single-book",
                    "style_profile_id": "book-editorial-bilingual-v2",
                    "release_profile_id": "book-v4-bilingual-3x4",
                    "generation_lane": "local-renderer",
                },
            },
        )
        characters = list("甲乙丙丁戊己庚辛壬癸子丑寅卯辰")
        lines = [
            {"id": f"V{index:02d}", "role": "body", "zh": character, "en": f"line {index}"}
            for index, character in enumerate(characters, start=1)
        ]
        self.script = self.project / "02_story_script_故事脚本/script.v2.bilingual.json"
        _write_json(
            self.script,
            {
                "schema_version": "2.0",
                "version": "synthetic-v1",
                "project_id": self.project.name,
                "book": {"title": "测试书", "author": "测试作者"},
                "translation_status": "reviewed",
                "lines": lines,
            },
        )
        self.voice = self.project / "05_voice_人声/v3-b-locked-master.wav"
        _write_wave(self.voice)
        self.asr = self.project / "05_voice_人声/asr-v3/v3-b-locked-master.json"
        words = []
        for index, character in enumerate(characters):
            start = 0.2 + index * 0.5
            words.append({"word": character, "start": start, "end": start + 0.3})
        _write_json(self.asr, {"segments": [{"start": 0.0, "end": 7.5, "words": words}]})
        self.bgm = self.project / "06_music_音乐/v4-synthetic-original-bgm.mp3"
        self.bgm.parent.mkdir(parents=True, exist_ok=True)
        self.bgm.write_bytes(b"synthetic-bgm")
        self.sfx = self.project / "06_music_音乐/H2-用户确认原片高频音效层.wav"
        self.sfx.write_bytes(b"synthetic-h2")
        self.scenes: list[Path] = []
        for index in range(1, 13):
            path = self.project / f"03_images_生成图片/approved/v4/S{index:02d}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"png" + bytes([index]))
            self.scenes.append(path)
        self.cover = self.project / "01_research_资料搜集/sources/cover/cover.png"
        self.cover.parent.mkdir(parents=True, exist_ok=True)
        self.cover.write_bytes(b"synthetic-cover")
        self.cover_manifest = self.cover.parent / "cover_manifest.json"
        _write_json(
            self.cover_manifest,
            {
                "schema_version": "1.1",
                "local_file": self.cover.relative_to(self.project).as_posix(),
                "source_url": "https://example.invalid/cover.png",
                "rights_status": "cleared_for_public_release",
                "sha256": hashlib.sha256(self.cover.read_bytes()).hexdigest(),
            },
        )
        self.fonts: dict[str, Path] = {}
        for role in ("title", "chinese", "english"):
            path = base / "fonts" / f"{role}.ttf"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"font-{role}".encode())
            self.fonts[role] = path
        subjects = {
            "script": [self.script],
            "timing": [self.asr],
            "visual_rights": self.scenes,
            "cover_rights": [self.cover_manifest, self.cover],
            "bgm_rights": [self.bgm],
            "sfx_rights": [self.sfx],
            "voice_rights": [self.voice],
        }
        for gate, paths in subjects.items():
            record_approval(
                self.project,
                release_id=approval_release_id,
                gate=gate,
                decision="approved",
                reviewer="fixture-reviewer",
                subjects=paths,
                event_id=f"event-{gate}-{approval_release_id}",
                reviewed_at="2026-08-01T00:00:00+00:00",
            )

    def collect(self):
        return collect_v4_release(
            self.project,
            RELEASE_ID,
            runtime_root=ROOT,
            font_paths=self.fonts,
            created_at=CREATED_AT,
        )

    def map(self, bundle):
        resolver = RootResolver(bundle.root_bindings)
        snapshot_ref = PortableRef(
            "project", bundle.snapshot_path.relative_to(self.project).as_posix()
        )
        return map_v4_snapshot_to_request(
            bundle.snapshot,
            snapshot_ref,
            resolver,
            created_at=CREATED_AT,
        ), resolver


class FakeProbe:
    def __init__(self, request) -> None:
        self.request = request

    def probe(self, path: Path):
        spec = self.request.output_spec
        duration = int(spec["duration_ticks"])
        fps = spec["fps"]
        return {
            "duration_ticks": duration,
            "video": {
                "codec": spec["video"]["codec"],
                "width": spec["width"],
                "height": spec["height"],
                "fps": dict(fps),
                "pixel_format": spec["pixel_format"],
                "frame_count": max(1, duration * int(fps["numerator"]) // (1000 * int(fps["denominator"]))),
            },
            "audio": dict(spec["audio"]),
        }


class FakeRunner:
    def __init__(self, request, resolver: RootResolver, *, returncode: int = 0, create_output: bool = True, mutate_input: Path | None = None) -> None:
        self.request = request
        self.resolver = resolver
        self.returncode = returncode
        self.create_output = create_output
        self.mutate_input = mutate_input
        self.calls: list[tuple[list[str], Path, dict[str, str]]] = []

    def run(self, command, *, cwd: Path, env):
        self.calls.append((list(command), cwd, dict(env)))
        if self.mutate_input is not None:
            self.mutate_input.write_bytes(b"changed-after-preflight")
        if self.returncode == 0 and self.create_output:
            target = self.request.output["target"]
            output = self.resolver.resolve(PortableRef(str(target["root"]), str(target["path"])))
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(b"synthetic-mp4")
            extension = self.request.extensions["org.book-video-factory.legacy-v4"]
            for sidecar in extension["expected_sidecars"]:
                ref = sidecar["ref"]
                path = self.resolver.resolve(PortableRef(str(ref["root"]), str(ref["path"])))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"{}" if str(sidecar["media_type"]) == "application/json" else b"1\n")
        return CommandResult(self.returncode, stdout="fake stdout", stderr="fake stderr", elapsed_ms=7)


class V4CollectorMapperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.fixture = V4Fixture(Path(self.temp.name))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_snapshot_and_mapper_are_stable_and_continuous(self) -> None:
        first = self.fixture.collect()
        second = self.fixture.collect()
        self.assertEqual(first.snapshot.snapshot_hash, second.snapshot.snapshot_hash)
        self.assertEqual(first.snapshot_path, second.snapshot_path)
        request, resolver = self.fixture.map(first)
        remapped = map_v4_snapshot_to_request(
            first.snapshot,
            PortableRef("project", first.snapshot_path.relative_to(self.fixture.project).as_posix()),
            resolver,
            created_at="2026-08-02T00:00:00Z",
        )
        self.assertEqual(request.request_hash, remapped.request_hash)
        self.assertEqual(validate_render_request(request), ())
        self.assertEqual(validate_request_hash(request), ())
        self.assertIsNone(request.audio["final_mix_asset_id"])
        self.assertIn("audio_mixing", request.renderer.required_capabilities)
        segments = request.timeline["segments"]
        self.assertEqual(len(segments), 13)
        self.assertEqual(segments[0]["start_tick"], 0)
        self.assertTrue(all(left["end_tick"] == right["start_tick"] for left, right in zip(segments, segments[1:])))
        self.assertEqual(segments[-1]["end_tick"], request.timeline["duration_ticks"])
        self.assertNotIn("render_manifest.v4.json", first.snapshot.timeline_source["ref"]["path"])

    def test_missing_asset_fails_closed(self) -> None:
        self.fixture.bgm.unlink()
        with self.assertRaises(ContractValidationError) as caught:
            self.fixture.collect()
        self.assertEqual(caught.exception.issues[0].code, RendererErrorCode.RENDER_ASSET_MISSING)

    def test_duplicate_scene_bytes_fail_closed(self) -> None:
        self.fixture.scenes[1].write_bytes(self.fixture.scenes[0].read_bytes())
        with self.assertRaises(ContractValidationError) as caught:
            self.fixture.collect()
        self.assertEqual(caught.exception.issues[0].code, RendererErrorCode.RENDER_INPUT_INVALID)

    def test_cross_release_approvals_are_not_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = V4Fixture(Path(temp), approval_release_id="other-release")
            with self.assertRaises(ContractValidationError) as caught:
                fixture.collect()
        self.assertTrue(all(issue.code is RendererErrorCode.RENDER_GATE_BLOCKED for issue in caught.exception.issues))

    def test_stale_approval_subject_hash_is_blocked(self) -> None:
        self.fixture.asr.write_text("{}", encoding="utf-8")
        with self.assertRaises(ContractValidationError) as caught:
            self.fixture.collect()
        self.assertIn(caught.exception.issues[0].code, {RendererErrorCode.RENDER_CAPTION_INVALID, RendererErrorCode.RENDER_GATE_BLOCKED})

    def test_legacy_audio_exception_is_not_generic(self) -> None:
        bundle = self.fixture.collect()
        request, _ = self.fixture.map(bundle)
        payload = render_request_to_dict(request)
        payload["renderer"]["required_capabilities"].remove("audio_mixing")
        payload["request_hash"] = semantic_request_hash(payload)
        payload["request_id"] = request_id_from_hash(payload["request_hash"])
        issues = validate_render_request(render_request_from_dict(payload))
        self.assertIn(RendererErrorCode.RENDER_AUDIO_INVALID, {issue.code for issue in issues})

    def test_request_persistence_is_write_once(self) -> None:
        bundle = self.fixture.collect()
        request, _ = self.fixture.map(bundle)
        directory = self.fixture.project / "manifests/requests"
        path = write_render_request(request, directory)
        self.assertEqual(path, write_render_request(request, directory))
        path.write_bytes(b"tampered")
        with self.assertRaises(ContractPersistenceError):
            write_render_request(request, directory)

    def test_phase_3b_json_schemas_parse(self) -> None:
        for name in (
            "render-request-v1.schema.json",
            "render-result-v1.schema.json",
            "renderer-capabilities-v1.schema.json",
            "release-snapshot-v1.schema.json",
        ):
            self.assertIsInstance(json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8")), dict)


class LegacyV4FacadeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.fixture = V4Fixture(Path(self.temp.name))
        self.bundle = self.fixture.collect()
        self.request, self.resolver = self.fixture.map(self.bundle)
        self.attempts = self.fixture.project / "08_render_合成/attempts"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def context(self, attempt_id: str) -> RenderExecutionContext:
        return RenderExecutionContext(self.resolver, self.attempts, attempt_id, environment={})

    def test_success_collects_result_sidecars_probe_and_qc_handoff(self) -> None:
        runner = FakeRunner(self.request, self.resolver)
        renderer = LegacyV4Renderer(runner=runner, probe=FakeProbe(self.request), clock=lambda: CREATED_AT)
        result = renderer.render(self.request, self.context("attempt-success"))
        self.assertEqual(result.status, RenderStatus.SUCCEEDED)
        self.assertEqual(len(result.output), 1)
        self.assertEqual(len(result.sidecars), 7)
        self.assertEqual(result.qc_handoff["release_id"], RELEASE_ID)
        self.assertFalse(result.extensions["org.book-video-factory.legacy-v4"]["post_qc_invoked"])
        self.assertEqual(len(list((self.attempts / "attempt-success/events").glob("*.json"))), 3)
        self.assertTrue((self.attempts / "attempt-success/render-result-v1.json").is_file())
        self.assertEqual(runner.calls[0][0][-2:], ["--release-version", "v4"])
        for variable in ("BOOK_VIDEO_TITLE_FONT", "BOOK_VIDEO_CHINESE_FONT", "BOOK_VIDEO_ENGLISH_FONT"):
            self.assertIn(variable, runner.calls[0][2])

    def test_runner_failure_is_terminal_and_retry_uses_new_attempt(self) -> None:
        failed = LegacyV4Renderer(
            runner=FakeRunner(self.request, self.resolver, returncode=3),
            probe=FakeProbe(self.request),
            clock=lambda: CREATED_AT,
        ).render(self.request, self.context("attempt-failed"))
        self.assertEqual(failed.status, RenderStatus.FAILED)
        self.assertEqual(failed.primary_error_code, RendererErrorCode.RENDER_PROCESS_FAILED.value)
        succeeded = LegacyV4Renderer(
            runner=FakeRunner(self.request, self.resolver),
            probe=FakeProbe(self.request),
            clock=lambda: CREATED_AT,
        ).render(self.request, self.context("attempt-retry"))
        self.assertEqual(succeeded.status, RenderStatus.SUCCEEDED)
        self.assertNotEqual(failed.attempt_id, succeeded.attempt_id)

    def test_zero_exit_without_output_fails_collection(self) -> None:
        result = LegacyV4Renderer(
            runner=FakeRunner(self.request, self.resolver, create_output=False),
            probe=FakeProbe(self.request),
            clock=lambda: CREATED_AT,
        ).render(self.request, self.context("attempt-no-output"))
        self.assertEqual(result.status, RenderStatus.FAILED)
        self.assertEqual(result.primary_error_code, RendererErrorCode.RENDER_OUTPUT_MISSING.value)

    def test_input_mutation_after_runner_is_hash_mismatch(self) -> None:
        result = LegacyV4Renderer(
            runner=FakeRunner(self.request, self.resolver, mutate_input=self.fixture.script),
            probe=FakeProbe(self.request),
            clock=lambda: CREATED_AT,
        ).render(self.request, self.context("attempt-mutated"))
        self.assertEqual(result.status, RenderStatus.FAILED)
        self.assertEqual(result.primary_error_code, RendererErrorCode.RENDER_HASH_MISMATCH.value)

    def test_existing_output_blocks_before_runner(self) -> None:
        target = self.request.output["target"]
        path = self.resolver.resolve(PortableRef(str(target["root"]), str(target["path"])))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"existing")
        runner = FakeRunner(self.request, self.resolver)
        result = LegacyV4Renderer(runner=runner, probe=FakeProbe(self.request), clock=lambda: CREATED_AT).render(
            self.request, self.context("attempt-existing")
        )
        self.assertEqual(result.status, RenderStatus.FAILED)
        self.assertEqual(runner.calls, [])


if __name__ == "__main__":
    unittest.main()
