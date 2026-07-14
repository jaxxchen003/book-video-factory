from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from book_video_factory.content_bridge import (  # noqa: E402
    ContentBridgeError,
    attach_traceability,
    content_system_status,
    export_dbs_content_package,
    import_content_package,
    content_package_sha256,
    validate_content_package,
)
from book_video_factory.contracts import ReleaseProfile  # noqa: E402
from book_video_factory.gates import evaluate_workflow_state  # noqa: E402
from book_video_factory.manifests import record_approval  # noqa: E402
from book_video_factory.project import initialize_project  # noqa: E402
from book_video_factory.scene_contract import V4_SCENE_LINE_CONTRACT  # noqa: E402


def source_document() -> dict[str, object]:
    return {
        "id": "SRC-BOOK-001",
        "relative_path": "完整副本/样书.md",
        "source_type": "图书笔记",
        "author": "作者",
        "upstream_status": "已登记",
        "notes": "",
        "content_sha256": "a" * 64,
        "upstream_registry_path": "03-处理状态/来源注册表.csv",
    }


def unit(prefix: str, unit_type: str, **specific: object) -> dict[str, object]:
    identifier = f"{prefix}-20260714-001"
    payload: dict[str, object] = {
        "id": identifier,
        "type": unit_type,
        "title": f"{unit_type}标题",
        "source_documents": ["SRC-BOOK-001"],
        "source_authors": ["作者"],
        "themes": ["自我成长"],
        "keywords": ["边界"],
        "status": "已核对",
        "canonical": True,
        "version": 1,
        "created_at": "2026-07-14",
        "updated_at": "2026-07-14",
        "relationships": [],
        "upstream_path": f"02-内容单元库/{unit_type}/{identifier}.md",
        "content_sha256": {
            "QST": "1",
            "CON": "2",
            "OPI": "3",
            "CAS": "4",
            "SOL": "5",
        }[prefix]
        * 64,
        "body_markdown": "## 核心内容\n\n可独立理解的内容。",
    }
    payload.update(specific)
    return payload


def valid_package() -> dict[str, object]:
    units = [
        unit(
            "QST",
            "问题单元",
            question_text="为什么总在讨好别人？",
            question_type="认知问题",
            user_stage="起步期",
            applicable_topics=["关系边界"],
        ),
        unit(
            "CON",
            "概念单元",
            concept_definition="边界是对自己责任范围的识别。",
            concept_function="解释拒绝为何不是攻击。",
        ),
        unit(
            "OPI",
            "观点单元",
            core_claim="拒绝是在归还自己的选择权。",
            claim_scope="日常人际关系",
            why_it_matters="避免把过度让步误认为善良。",
        ),
        unit(
            "CAS",
            "案例单元",
            case_subject="临时请求",
            case_summary="先停两秒再回应。",
            case_process="说明当前不方便。",
            case_result="双方获得清晰预期。",
        ),
        unit(
            "SOL",
            "方案单元",
            target_problem="下意识答应",
            solution_summary="用暂停替代自动同意。",
            action_steps=["停两秒", "说明边界"],
            expected_result="保留选择空间。",
        ),
    ]
    opinion_id = "OPI-20260714-001"
    claim_id = f"CLM:{opinion_id}:core_claim"
    return {
        "schema_version": "1.0",
        "package_id": "PKG-20260714-BOUNDARY-001",
        "source_system": {
            "name": "dbs-content-system",
            "snapshot_id": "SNAP-20260714-001",
            "exported_at": "2026-07-14T00:00:00+00:00",
        },
        "source_documents": [source_document()],
        "content_units": units,
        "claims": [
            {
                "id": claim_id,
                "origin": {"content_unit_id": opinion_id, "field": "core_claim"},
                "claim_type": "interpretation",
                "text_zh": "拒绝是在归还自己的选择权。",
                "text_en": "A refusal returns choice to you.",
                "source_document_ids": ["SRC-BOOK-001"],
                "content_unit_ids": [opinion_id, "CAS-20260714-001"],
                "quote_refs": [],
                "status": "reviewed",
                "risk_level": "low",
            }
        ],
        "assembly_brief": {
            "id": "ASM-20260714-BOUNDARY-001",
            "title": "停止讨好，从暂停两秒开始",
            "target_audience": "习惯过度答应的人",
            "assembly_reason": "从问题、解释、判断、案例到行动形成完整闭环。",
            "upstream_path": "06-选题装配/20260714_边界_装配稿.md",
            "content_sha256": "b" * 64,
            "unit_ids": {
                "QST": ["QST-20260714-001"],
                "CON": ["CON-20260714-001"],
                "OPI": [opinion_id],
                "CAS": ["CAS-20260714-001"],
                "SOL": ["SOL-20260714-001"],
            },
            "claim_ids": [claim_id],
            "suggested_structure": ["痛点", "冲突", "展开", "案例", "方法", "收束"],
            "expression_skeleton": {
                "opening": "指出自动答应的代价。",
                "middle": ["解释边界", "给出案例", "提供动作"],
                "closing": "把选择权还给自己。",
            },
        },
    }


def write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def prepare_script_and_scenes(project: Path) -> tuple[Path, Path]:
    script = write_json(
        project / "02_story_script_故事脚本/script.v2.bilingual.json",
        {
            "schema_version": "2.0",
            "project_id": project.name,
            "lines": [
                {"id": f"V{index:02d}", "role": "line", "zh": f"第{index}句", "en": f"Line {index}"}
                for index in range(1, 16)
            ],
        },
    )
    assets = []
    for index, (scene_id, line_ids) in enumerate(V4_SCENE_LINE_CONTRACT.items(), start=1):
        image_path = project / f"03_images_生成图片/approved/v4/{scene_id}.png"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(f"scene-{index}".encode("utf-8"))
        assets.append(
            {
                "id": scene_id,
                "line_ids": list(line_ids),
                "file": f"03_images_生成图片/approved/v4/{scene_id}.png",
                "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                "prompt": f"Scene {index} prompt",
                "generator": "test-generator",
            }
        )
    scene_manifest = write_json(
        project / "03_images_生成图片/approved/v4/scene_manifest.json",
        {
            "schema_version": "2.0",
            "project_id": project.name,
            "assets": assets,
        },
    )
    return script, scene_manifest


def traceability_draft(project: Path, package_sha256: str) -> dict[str, object]:
    line_to_scenes: dict[str, list[str]] = {}
    for scene_id, line_ids in V4_SCENE_LINE_CONTRACT.items():
        for line_id in line_ids:
            line_to_scenes.setdefault(line_id, []).append(scene_id)
    claim_id = "CLM:OPI-20260714-001:core_claim"
    return {
        "schema_version": "1.0",
        "traceability_id": "TRC-20260714-001",
        "project_id": project.name,
        "release_id": "v1-r1",
        "content_package_sha256": package_sha256,
        "script_path": "02_story_script_故事脚本/script.v2.bilingual.json",
        "scene_manifest_path": "03_images_生成图片/approved/v4/scene_manifest.json",
        "links": [
            {
                "script_line_id": f"V{index:02d}",
                "evidence_mode": "claim_backed",
                "claim_ids": [claim_id],
                "scene_ids": line_to_scenes[f"V{index:02d}"],
            }
            for index in range(1, 16)
        ],
    }


class ContentPackageTests(unittest.TestCase):
    def test_valid_package_preserves_all_five_unit_types(self) -> None:
        result = validate_content_package(valid_package())
        self.assertEqual(result["counts"], {"source_documents": 1, "content_units": 5, "claims": 1})
        self.assertTrue(result["production_eligible"])

    def test_package_identity_ignores_export_timestamp(self) -> None:
        first = valid_package()
        second = copy.deepcopy(first)
        second["source_system"]["exported_at"] = "2026-07-15T00:00:00+00:00"  # type: ignore[index]
        self.assertEqual(content_package_sha256(first), content_package_sha256(second))

    def test_orphan_claim_source_is_rejected(self) -> None:
        payload = valid_package()
        payload["claims"][0]["source_document_ids"] = ["SRC-MISSING-001"]  # type: ignore[index]
        with self.assertRaisesRegex(ContentBridgeError, "unknown source document"):
            validate_content_package(payload)

    def test_unknown_relationship_type_is_rejected(self) -> None:
        payload = valid_package()
        payload["content_units"][1]["relationships"] = [  # type: ignore[index]
            {"type": "承接", "target": "QST-20260714-001", "note": "not contracted"}
        ]
        with self.assertRaisesRegex(ContentBridgeError, "unknown relationship type"):
            validate_content_package(payload)

    def test_assembly_bucket_mismatch_is_rejected(self) -> None:
        payload = valid_package()
        payload["assembly_brief"]["unit_ids"]["QST"] = ["OPI-20260714-001"]  # type: ignore[index]
        with self.assertRaisesRegex(ContentBridgeError, "QST bucket"):
            validate_content_package(payload)

    def test_export_dbs_serializes_registered_sources_units_and_assembly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "content-system"
            source = root / "01-原始素材区/图书/样书.md"
            source.parent.mkdir(parents=True)
            source.write_text("原始资料", encoding="utf-8")
            registry = root / "03-处理状态/来源注册表.csv"
            registry.parent.mkdir(parents=True)
            registry.write_text(
                "source_id,path,source_type,author,status,notes\n"
                "SRC-BOOK-001,图书/样书.md,图书笔记,作者,已登记,\n",
                encoding="utf-8",
            )
            package_fixture = valid_package()
            for unit_payload in package_fixture["content_units"]:  # type: ignore[index]
                unit_path = root / str(unit_payload["upstream_path"])
                unit_path.parent.mkdir(parents=True, exist_ok=True)
                common_keys = [
                    "id", "type", "title", "source_documents", "source_authors",
                    "themes", "keywords", "status", "canonical", "version",
                    "created_at", "updated_at",
                ]
                lines = ["---"]
                for key in common_keys:
                    value = unit_payload[key]
                    if isinstance(value, list):
                        lines.append(f"{key}:")
                        lines.extend(f"  - {item}" for item in value)
                    elif isinstance(value, bool):
                        lines.append(f"{key}: {'true' if value else 'false'}")
                    else:
                        lines.append(f"{key}: {value}")
                prefix = str(unit_payload["id"]).split("-", 1)[0]
                for key in {
                    "QST": ("question_text", "question_type", "user_stage", "applicable_topics"),
                    "CON": ("concept_definition", "concept_function"),
                    "OPI": ("core_claim", "claim_scope", "why_it_matters"),
                    "CAS": ("case_subject", "case_summary", "case_process", "case_result"),
                    "SOL": ("target_problem", "solution_summary", "action_steps", "expected_result"),
                }[prefix]:
                    value = unit_payload[key]
                    if isinstance(value, list):
                        lines.append(f"{key}:")
                        lines.extend(f"  - {item}" for item in value)
                    else:
                        lines.append(f"{key}: {value}")
                lines.extend(["relationships: []", "---", "", "## 核心内容", "", "可独立理解的内容。", ""])
                unit_path.write_text("\n".join(lines), encoding="utf-8")
            assembly = root / "06-选题装配/20260714_边界_装配稿.md"
            assembly.parent.mkdir(parents=True)
            assembly.write_text(
                "# 选题装配：停止讨好，从暂停两秒开始\n\n"
                "## 目标受众\n\n习惯过度答应的人\n\n"
                "## 装配理由\n\n从问题、解释、判断、案例到行动形成闭环。\n\n"
                "## 核心调用单元\n\n"
                "### 问题\n\n[[QST-20260714-001_问题]]\n\n"
                "### 概念\n\n[[CON-20260714-001_概念]]\n\n"
                "### 观点\n\n[[OPI-20260714-001_观点]]\n\n"
                "### 案例\n\n[[CAS-20260714-001_案例]]\n\n"
                "### 方案\n\n[[SOL-20260714-001_方案]]\n\n"
                "## 建议结构\n\n1. 痛点：自动答应\n2. 冲突：边界不是攻击\n3. 展开：解释选择权\n4. 案例：暂停两秒\n5. 方法：说明边界\n6. 收束：归还选择\n\n"
                "## 表达骨架\n\n### 开头\n\n指出自动答应的代价。\n\n"
                "### 中段 1\n\n解释边界。\n\n### 中段 2\n\n给出案例。\n\n"
                "### 结尾\n\n把选择权还给自己。\n",
                encoding="utf-8",
            )
            output = Path(temp) / "package.json"
            first = export_dbs_content_package(root, assembly, output)
            second = export_dbs_content_package(root, assembly, output)
            self.assertEqual(first, second)
            exported = json.loads(output.read_text(encoding="utf-8"))
            validation = validate_content_package(exported)
            self.assertTrue(validation["production_eligible"])
            self.assertEqual(exported["source_documents"][0]["relative_path"], "01-原始素材区/图书/样书.md")
            registry.write_text(
                "source_id,path,source_type,author,status,notes\n"
                "SRC-BOOK-001,图书/样书.md,图书笔记,作者,已登记,changed\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ContentBridgeError, "refusing to overwrite"):
                export_dbs_content_package(root, assembly, output)


class ImportAndTraceabilityTests(unittest.TestCase):
    def test_import_retry_repairs_stage_before_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = initialize_project(
                root / "warehouse", "backed", "样书", "作者", mode="content-system-backed"
            )
            package_path = write_json(root / "package.json", valid_package())
            with patch(
                "book_video_factory.content_bridge.write_stage_manifest",
                side_effect=RuntimeError("simulated stage write failure"),
            ):
                with self.assertRaisesRegex(RuntimeError, "simulated stage write failure"):
                    import_content_package(project, package_path)
            self.assertTrue(
                list(
                    (project / "01_research_资料搜集/content_system/imports").glob(
                        "*/*/import_manifest.json"
                    )
                )
            )
            self.assertFalse(list((project / "logs/content_import_events").glob("*.json")))

            manifest = import_content_package(project, package_path)
            self.assertTrue(manifest.is_file())
            self.assertEqual(
                len(list((project / "manifests/stages/research.content_bridge").glob("*.json"))),
                1,
            )
            self.assertEqual(len(list((project / "logs/content_import_events").glob("*.json"))), 1)

    def test_traceability_retry_repairs_stage_before_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = initialize_project(
                root / "warehouse", "backed", "样书", "作者", mode="content-system-backed"
            )
            package_path = write_json(root / "package.json", valid_package())
            manifest = import_content_package(project, package_path)
            package_sha = json.loads(manifest.read_text(encoding="utf-8"))["package_sha256"]
            prepare_script_and_scenes(project)
            trace_path = write_json(root / "trace.json", traceability_draft(project, package_sha))
            with patch(
                "book_video_factory.content_bridge.write_stage_manifest",
                side_effect=RuntimeError("simulated trace stage failure"),
            ):
                with self.assertRaisesRegex(RuntimeError, "simulated trace stage failure"):
                    attach_traceability(project, trace_path)
            self.assertTrue(
                list((project / "02_story_script_故事脚本/traceability").glob("*/*.json"))
            )
            self.assertFalse(list((project / "logs/traceability_events").glob("*.json")))

            attached = attach_traceability(project, trace_path)
            self.assertTrue(attached.is_file())
            self.assertEqual(
                len(list((project / "manifests/stages/script.traceability").glob("*.json"))),
                1,
            )
            self.assertEqual(len(list((project / "logs/traceability_events").glob("*.json"))), 1)

    def test_missing_content_activation_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = initialize_project(
                root / "warehouse", "backed", "样书", "作者", mode="content-system-backed"
            )
            package_path = write_json(root / "package.json", valid_package())
            import_content_package(project, package_path)
            for event in (project / "logs/content_import_events").glob("*.json"):
                event.unlink()
            status = content_system_status(project)
            self.assertFalse(status["content_package_valid"])
            self.assertIn("activated content package", " ".join(status["errors"]))

    def test_missing_traceability_activation_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = initialize_project(
                root / "warehouse", "backed", "样书", "作者", mode="content-system-backed"
            )
            package_path = write_json(root / "package.json", valid_package())
            manifest = import_content_package(project, package_path)
            package_sha = json.loads(manifest.read_text(encoding="utf-8"))["package_sha256"]
            prepare_script_and_scenes(project)
            trace_path = write_json(root / "trace.json", traceability_draft(project, package_sha))
            attach_traceability(project, trace_path)
            for event in (project / "logs/traceability_events").glob("*.json"):
                event.unlink()
            status = content_system_status(project)
            self.assertTrue(status["content_package_valid"])
            self.assertFalse(status["traceability_valid"])
            self.assertIn("activated traceability", " ".join(status["errors"]))

    def test_import_is_mode_guarded_immutable_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package_path = write_json(root / "package.json", valid_package())
            single = initialize_project(root / "warehouse", "single", "样书", "作者")
            with self.assertRaisesRegex(ContentBridgeError, "content-system-backed"):
                import_content_package(single, package_path)

            project = initialize_project(
                root / "warehouse", "backed", "样书", "作者", mode="content-system-backed"
            )
            first = import_content_package(project, package_path)
            second = import_content_package(project, package_path)
            self.assertEqual(first, second)
            first_payload = json.loads(first.read_text(encoding="utf-8"))
            self.assertEqual(first_payload["object_counts"]["content_units"], 5)

            changed = valid_package()
            changed["assembly_brief"]["assembly_reason"] = "新的装配理由。"  # type: ignore[index]
            write_json(package_path, changed)
            third = import_content_package(project, package_path)
            self.assertNotEqual(first.parent, third.parent)
            self.assertTrue(first.is_file())

    def test_import_rejects_project_output_symlink_before_external_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = initialize_project(
                root / "warehouse", "backed", "样书", "作者", mode="content-system-backed"
            )
            package_path = write_json(root / "package.json", valid_package())
            imports = project / "01_research_资料搜集/content_system/imports"
            outside = root / "outside-imports"
            outside.mkdir()
            shutil.rmtree(imports)
            imports.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                import_content_package(project, package_path)
            self.assertEqual(list(outside.iterdir()), [])

    def test_traceability_rejects_project_output_symlink_before_external_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = initialize_project(
                root / "warehouse", "backed", "样书", "作者", mode="content-system-backed"
            )
            package_path = write_json(root / "package.json", valid_package())
            manifest = import_content_package(project, package_path)
            package_sha = json.loads(manifest.read_text(encoding="utf-8"))["package_sha256"]
            prepare_script_and_scenes(project)
            trace_path = write_json(root / "trace.json", traceability_draft(project, package_sha))
            trace_directory = project / "02_story_script_故事脚本/traceability"
            outside = root / "outside-traceability"
            outside.mkdir()
            shutil.rmtree(trace_directory)
            trace_directory.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                attach_traceability(project, trace_path)
            self.assertEqual(list(outside.iterdir()), [])

    def test_traceability_covers_script_claims_and_renderer_scene_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = initialize_project(
                root / "warehouse", "backed", "样书", "作者", mode="content-system-backed"
            )
            package_path = write_json(root / "package.json", valid_package())
            manifest = import_content_package(project, package_path)
            package_sha = json.loads(manifest.read_text(encoding="utf-8"))["package_sha256"]
            prepare_script_and_scenes(project)
            trace_path = write_json(root / "trace.json", traceability_draft(project, package_sha))
            attached = attach_traceability(project, trace_path)
            self.assertTrue(attached.is_file())
            status = content_system_status(project)
            self.assertTrue(status["content_package_valid"])
            self.assertTrue(status["traceability_valid"])
            self.assertEqual(status["linked_script_lines"], 15)
            (project / "03_images_生成图片/approved/v4/S01.png").write_bytes(b"tampered")
            stale = content_system_status(project)
            self.assertFalse(stale["traceability_valid"])
            self.assertIn("hash", " ".join(stale["errors"]))

    def test_traceability_rejects_uncovered_script_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = initialize_project(
                root / "warehouse", "backed", "样书", "作者", mode="content-system-backed"
            )
            package_path = write_json(root / "package.json", valid_package())
            manifest = import_content_package(project, package_path)
            package_sha = json.loads(manifest.read_text(encoding="utf-8"))["package_sha256"]
            prepare_script_and_scenes(project)
            trace = traceability_draft(project, package_sha)
            trace["links"] = trace["links"][:-1]  # type: ignore[index]
            trace_path = write_json(root / "trace.json", trace)
            with self.assertRaisesRegex(ContentBridgeError, "cover every script line"):
                attach_traceability(project, trace_path)

    def test_traceability_rejects_scene_line_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = initialize_project(
                root / "warehouse", "backed", "样书", "作者", mode="content-system-backed"
            )
            package_path = write_json(root / "package.json", valid_package())
            manifest = import_content_package(project, package_path)
            package_sha = json.loads(manifest.read_text(encoding="utf-8"))["package_sha256"]
            _, scene_manifest = prepare_script_and_scenes(project)
            scene_payload = json.loads(scene_manifest.read_text(encoding="utf-8"))
            scene_payload["assets"][0]["line_ids"] = ["V04"]
            write_json(scene_manifest, scene_payload)
            trace_path = write_json(root / "trace.json", traceability_draft(project, package_sha))
            with self.assertRaisesRegex(ContentBridgeError, "renderer scene contract"):
                attach_traceability(project, trace_path)

    def test_content_backed_gate_requires_hash_bound_package_and_traceability(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = initialize_project(
                root / "warehouse", "backed", "样书", "作者", mode="content-system-backed"
            )
            topic = write_json(project / "00_topic_选题/topic.json", {"approved": True})
            package_path = write_json(root / "package.json", valid_package())
            import_manifest = import_content_package(project, package_path)
            imported = json.loads(import_manifest.read_text(encoding="utf-8"))
            package_snapshot = import_manifest.parent / "package.json"
            script, _ = prepare_script_and_scenes(project)
            write_json(project / "01_research_资料搜集/sources/cover/cover_manifest.json", {"ok": True})
            (project / "05_voice_人声/v3-b-locked-master.wav").write_bytes(b"voice")
            write_json(project / "05_voice_人声/asr-v3/v3-b-locked-master.json", {"segments": []})
            (project / "06_music_音乐/v4-calm-original-bgm.mp3").write_bytes(b"bgm")
            (project / "06_music_音乐/H2-用户确认原片高频音效层.wav").write_bytes(b"sfx")
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
                release_id="v1-r1",
                gate="source",
                decision="approved",
                reviewer="human",
                subjects=[package_snapshot],
            )
            record_approval(
                project,
                release_id="v1-r1",
                gate="script",
                decision="approved",
                reviewer="human",
                subjects=[script],
            )
            profile = ReleaseProfile.load(ROOT / "config/release_profiles/book-v4-bilingual-3x4.json")
            before = evaluate_workflow_state(project, profile)
            self.assertEqual(before["derived_state"], "script_reviewed")
            trace_path = write_json(
                root / "trace.json",
                traceability_draft(project, imported["package_sha256"]),
            )
            attached = attach_traceability(project, trace_path)
            before_trace_review = evaluate_workflow_state(project, profile)
            self.assertEqual(before_trace_review["derived_state"], "script_reviewed")
            record_approval(
                project,
                release_id="v1-r1",
                gate="traceability",
                decision="approved",
                reviewer="human",
                subjects=[attached],
            )
            after = evaluate_workflow_state(project, profile)
            self.assertEqual(after["derived_state"], "assets_ready")
            self.assertTrue(after["content_system"]["traceability_valid"])


if __name__ == "__main__":
    unittest.main()
