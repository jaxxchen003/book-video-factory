from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from book_video_factory.project import PROJECT_DIRECTORIES, initialize_project  # noqa: E402
from book_video_factory.style_profiles import StyleProfileError  # noqa: E402
from book_video_factory.audio import splice_asr_timestamps  # noqa: E402
from book_video_factory.voice import build_generation_request  # noqa: E402
from book_video_factory.weread import (  # noqa: E402
    collect_book_source_pack,
    normalize_source_pack,
    select_book,
)
from book_video_factory.freesound import (  # noqa: E402
    FreesoundError,
    license_details,
    normalize_candidates,
    write_candidate_manifest,
)


class ProjectTests(unittest.TestCase):
    def test_initialization_creates_contract_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            warehouse = Path(temp) / "warehouse"
            project = initialize_project(warehouse, "sample", "样书", "作者")
            for relative in PROJECT_DIRECTORIES:
                self.assertTrue((project / relative).is_dir())
            first = json.loads((project / "project.json").read_text(encoding="utf-8"))
            initialize_project(warehouse, "sample", "被覆盖", "另一作者")
            second = json.loads((project / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(first, second)
            self.assertEqual(first["workflow"]["mode"], "single-book")
            self.assertEqual(
                first["workflow"]["release_profile_id"],
                "book-v4-bilingual-3x4",
            )
            self.assertEqual(
                first["workflow"]["style_profile_id"],
                "book-editorial-bilingual-v2",
            )
            self.assertEqual(first["workflow"]["generation_lane"], "local-renderer")
            self.assertTrue((project / "manifests/stages").is_dir())
            self.assertTrue((project / "logs/approval_events").is_dir())

    def test_vox_style_requires_explicit_lane_and_maps_release_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            warehouse = Path(temp) / "warehouse"
            with self.assertRaisesRegex(StyleProfileError, "explicit generation lane"):
                initialize_project(
                    warehouse,
                    "missing-lane",
                    "样书",
                    "作者",
                    style_profile_id="paper-collage-explainer-v1",
                )
            project = initialize_project(
                warehouse,
                "vox-sample",
                "样书",
                "作者",
                style_profile_id="paper-collage-explainer-v1",
                generation_lane="google-flow",
            )
            payload = json.loads(
                (project / "project.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                payload["workflow"]["style_profile_id"],
                "paper-collage-explainer-v1",
            )
            self.assertEqual(
                payload["workflow"]["style_display_name"],
                "VOX风格图书视频",
            )
            self.assertEqual(
                payload["workflow"]["release_profile_id"],
                "book-vox-vertical-9x16-v1",
            )
            self.assertEqual(payload["workflow"]["generation_lane"], "google-flow")
            with self.assertRaisesRegex(ValueError, "does not support workflow mode"):
                initialize_project(
                    warehouse,
                    "vox-content-backed",
                    "样书",
                    "作者",
                    mode="content-system-backed",
                    style_profile_id="paper-collage-explainer-v1",
                    generation_lane="google-flow",
                )

    def test_style_rejects_incompatible_release_profile_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "incompatible override"):
                initialize_project(
                    Path(temp),
                    "vox-mismatch",
                    "样书",
                    "作者",
                    release_profile_id="book-v4-bilingual-3x4",
                    style_profile_id="paper-collage-explainer-v1",
                    generation_lane="google-flow",
                )


class WeReadTests(unittest.TestCase):
    def test_select_book_prefers_exact_author(self) -> None:
        search = {
            "results": [
                {
                    "books": [
                        {"bookInfo": {"bookId": "1", "title": "兜底", "author": "甲"}},
                        {"bookInfo": {"bookId": "2", "title": "兜底", "author": "晴山"}},
                    ]
                }
            ]
        }
        selected = select_book(search, "兜底", "晴山")
        self.assertEqual(selected["bookInfo"]["bookId"], "2")

    def test_normalized_pack_keeps_source_types_separate(self) -> None:
        selected = {"bookInfo": {"bookId": "b1", "title": "兜底", "author": "晴山"}}
        info = {"bookId": "b1", "title": "兜底", "author": "晴山"}
        chapters = {"chapters": [{"chapterUid": 7, "title": "第一章"}]}
        highlights = {
            "items": [
                {
                    "chapterUid": 7,
                    "range": "1-9",
                    "markText": "短划线",
                    "totalCount": 12,
                }
            ]
        }
        reviews = {
            "reviews": [
                {
                    "review": {
                        "review": {"reviewId": "r1", "content": "公开点评", "star": 80}
                    }
                }
            ]
        }
        pack = normalize_source_pack(selected, info, chapters, highlights, reviews)
        self.assertEqual(pack["popular_highlights"][0]["source_type"], "popular_highlight")
        self.assertEqual(pack["public_reviews"][0]["source_type"], "public_review")
        self.assertTrue(pack["editorial_rules"]["do_not_treat_reviews_as_book_facts"])

    def test_collection_writes_raw_normalized_and_project_state(self) -> None:
        responses = {
            "/store/search": {
                "results": [
                    {
                        "books": [
                            {
                                "bookInfo": {
                                    "bookId": "b1",
                                    "title": "兜底",
                                    "author": "晴山",
                                }
                            }
                        ]
                    }
                ]
            },
            "/book/info": {"bookId": "b1", "title": "兜底", "author": "晴山"},
            "/book/chapterinfo": {"chapters": []},
            "/book/bestbookmarks": {"items": []},
            "/review/list": {"reviews": []},
        }

        class FakeClient:
            def call(self, api_name: str, **params: object) -> dict[str, object]:
                return responses[api_name]

        with tempfile.TemporaryDirectory() as temp:
            project = initialize_project(Path(temp), "sample", "兜底", "晴山")
            collect_book_source_pack(
                project, "兜底", "晴山", client=FakeClient()  # type: ignore[arg-type]
            )
            normalized = project / "01_research_资料搜集" / "normalized"
            self.assertTrue((normalized / "book_source_pack.json").is_file())
            self.assertTrue((normalized / "collection_manifest.json").is_file())
            manifest = json.loads((project / "project.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "research_collected")
            self.assertEqual(manifest["research"]["book_id"], "b1")


class VoiceProfileTests(unittest.TestCase):
    def test_ultimate_clone_always_passes_selected_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reference = root / "reference.wav"
            reference.write_bytes(b"test-audio")
            profile_path = root / "profile.json"
            profile = {
                "mode": "ultimate_clone",
                "generation": {"cfg_value": 2.0, "inference_timesteps": 10},
                "clone": {
                    "reference_audio": "reference.wav",
                    "prompt_audio": "reference.wav",
                    "prompt_text": "固定音色的准确提示文本。",
                },
            }
            request = build_generation_request(profile, profile_path, "新的旁白。")
            self.assertEqual(request["text"], "新的旁白。")
            self.assertEqual(request["reference_wav_path"], str(reference.resolve()))
            self.assertEqual(request["prompt_wav_path"], str(reference.resolve()))
            self.assertEqual(request["prompt_text"], "固定音色的准确提示文本。")

    def test_voice_design_does_not_claim_a_reference_identity(self) -> None:
        profile = {
            "mode": "voice_design",
            "control": "温暖女声",
            "generation": {"cfg_value": 2.0, "inference_timesteps": 10},
        }
        request = build_generation_request(profile, Path("profile.json"), "测试。")
        self.assertEqual(request["text"], "(温暖女声)测试。")
        self.assertNotIn("reference_wav_path", request)


class AudioEditTests(unittest.TestCase):
    def test_splice_trims_crossing_word_and_moves_following_speech(self) -> None:
        asr = {
            "segments": [
                {
                    "start": 3.24,
                    "end": 6.0,
                    "words": [
                        {"word": "自", "start": 4.2, "end": 4.52},
                        {"word": "晴", "start": 4.52, "end": 5.14},
                    ],
                },
                {
                    "start": 6.0,
                    "end": 7.0,
                    "words": [{"word": "真", "start": 6.0, "end": 6.8}],
                },
            ]
        }

        shifted = splice_asr_timestamps(
            asr, cut_start=4.48, cut_end=4.52, inserted_silence=1.04
        )

        first_words = shifted["segments"][0]["words"]
        self.assertEqual(first_words[0]["end"], 4.48)
        self.assertEqual(first_words[1]["start"], 5.52)
        self.assertEqual(shifted["segments"][1]["start"], 7.0)
        self.assertEqual(asr["segments"][0]["words"][1]["start"], 4.52)


class FreesoundPolicyTests(unittest.TestCase):
    def test_license_allowlist_rejects_noncommercial_and_unknown(self) -> None:
        self.assertEqual(
            license_details("http://creativecommons.org/publicdomain/zero/1.0/")["code"],
            "CC0-1.0",
        )
        self.assertEqual(license_details("Attribution")["code"], "CC-BY-4.0")
        self.assertIsNone(
            license_details("https://creativecommons.org/licenses/by-nc/4.0/")
        )
        self.assertIsNone(license_details("royalty-free"))

    def test_candidate_normalization_keeps_only_previewable_allowlist_entries(self) -> None:
        results = [
            {
                "id": 1,
                "name": "Eligible",
                "username": "creator",
                "license": "Creative Commons 0",
                "duration": 72,
                "url": "https://freesound.org/people/creator/sounds/1/",
                "previews": {"preview-hq-mp3": "https://example.test/1.mp3"},
            },
            {
                "id": 2,
                "name": "NC must fail",
                "username": "creator",
                "license": "Attribution NonCommercial",
                "duration": 72,
                "previews": {"preview-hq-mp3": "https://example.test/2.mp3"},
            },
            {
                "id": 3,
                "name": "Too short",
                "username": "creator",
                "license": "Attribution",
                "duration": 15,
                "previews": {"preview-hq-mp3": "https://example.test/3.mp3"},
            },
        ]
        candidates, rejected = normalize_candidates(
            results, intent="calm piano", min_duration=55, max_duration=180, limit=10
        )
        self.assertEqual([candidate["sound_id"] for candidate in candidates], [1])
        self.assertEqual(rejected, 2)
        self.assertIn("CC0", candidates[0]["required_attribution"])

    def test_candidate_limit_must_be_positive(self) -> None:
        with self.assertRaises(FreesoundError):
            normalize_candidates([], intent="calm piano", min_duration=55, max_duration=180, limit=0)

    def test_candidate_manifest_is_noncommercial_until_operator_records_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = initialize_project(Path(temp), "sample", "样书", "作者")
            output = write_candidate_manifest(
                project,
                intent="calm piano",
                search_query="cinematic ambient piano",
                raw_payload={"count": 1},
                candidates=[],
                rejected_count=0,
                min_duration=55,
                max_duration=180,
            )
            manifest = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(
                manifest["provider_api_authorization"]["commercial_use_authorized"]
            )
            self.assertEqual(
                manifest["provider_api_authorization"]["status"],
                "noncommercial_preview_only",
            )
            self.assertEqual(manifest["search_query"], "cinematic ambient piano")


if __name__ == "__main__":
    unittest.main()
