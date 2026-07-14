from __future__ import annotations

import hashlib
import csv
import json
import re
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from .manifests import artifact as manifest_artifact
from .manifests import safe_project_output, sha256_file, write_stage_manifest
from .scene_contract import V4_SCENE_LINE_CONTRACT


class ContentBridgeError(ValueError):
    pass


UNIT_TYPES = {
    "QST": "问题单元",
    "CON": "概念单元",
    "OPI": "观点单元",
    "CAS": "案例单元",
    "SOL": "方案单元",
}
UNIT_FIELDS = {
    "QST": ("question_text", "question_type", "user_stage", "applicable_topics"),
    "CON": ("concept_definition", "concept_function"),
    "OPI": ("core_claim", "claim_scope", "why_it_matters"),
    "CAS": ("case_subject", "case_summary", "case_process", "case_result"),
    "SOL": ("target_problem", "solution_summary", "action_steps", "expected_result"),
}
CLAIM_ORIGIN_FIELDS = {
    "OPI": {"core_claim"},
    "CAS": {"case_summary", "case_result"},
}
RELATIONSHIP_TYPES = {"回应", "解释", "证明", "冲突"}
CLAIM_STATUSES = {"draft", "reviewed", "approved", "rejected"}
CLAIM_TYPES = {"fact", "interpretation", "quotation", "recommendation"}
RISK_LEVELS = {"low", "medium", "high"}
EDITORIAL_NO_CLAIM_ROLES = {"hook", "reveal_cue"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID_RE = re.compile(r"^[A-Z][A-Z0-9-]{2,127}$")
UNIT_ID_RE = re.compile(r"^(QST|CON|OPI|CAS|SOL)-\d{8}-\d{3,}$")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContentBridgeError(f"{label} must be an object")
    return value


def _list(value: Any, label: str, *, nonempty: bool = False) -> list[Any]:
    if not isinstance(value, list) or (nonempty and not value):
        suffix = " and cannot be empty" if nonempty else ""
        raise ContentBridgeError(f"{label} must be an array{suffix}")
    return value


def _string(value: Any, label: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str) or (nonempty and not value.strip()):
        raise ContentBridgeError(f"{label} must be a non-empty string")
    return value


def _string_list(value: Any, label: str, *, nonempty: bool = False) -> list[str]:
    values = _list(value, label, nonempty=nonempty)
    for index, item in enumerate(values):
        _string(item, f"{label}[{index}]")
    return values


def _sha256(value: Any, label: str) -> str:
    text = _string(value, label)
    if not SHA256_RE.fullmatch(text):
        raise ContentBridgeError(f"{label} must be a lowercase SHA-256")
    return text


def _relative_path(value: Any, label: str) -> str:
    text = _string(value, label)
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts:
        raise ContentBridgeError(f"{label} must be an upstream-relative path")
    return text


def _unique_ids(objects: list[Any], label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for index, value in enumerate(objects):
        item = _mapping(value, f"{label}[{index}]")
        identifier = _string(item.get("id"), f"{label}[{index}].id")
        if identifier in result:
            raise ContentBridgeError(f"duplicate {label} id: {identifier}")
        result[identifier] = item
    return result


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def content_package_sha256(payload: dict[str, Any]) -> str:
    # Export time is operational metadata, not content identity. Excluding it
    # keeps repeat exports of the same audited snapshot semantically idempotent.
    normalized = json.loads(json.dumps(payload, ensure_ascii=False))
    source_system = normalized.get("source_system")
    if isinstance(source_system, dict):
        source_system.pop("exported_at", None)
    return hashlib.sha256(_canonical_bytes(normalized)).hexdigest()


def _frontmatter_scalar(value: str) -> Any:
    text = value.strip()
    if text == "[]":
        return []
    if text in {"true", "false"}:
        return text == "true"
    if re.fullmatch(r"[0-9]+", text):
        return int(text)
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    return text


def parse_dbs_content_unit(path: Path, root: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ContentBridgeError(f"cannot read content unit {path}: {error}") from error
    if not text.startswith("---\n"):
        raise ContentBridgeError(f"content unit has no YAML frontmatter: {path}")
    closing = text.find("\n---\n", 4)
    if closing < 0:
        raise ContentBridgeError(f"content unit frontmatter is not closed: {path}")
    frontmatter = text[4:closing]
    body = text[closing + 5 :].strip()
    payload: dict[str, Any] = {}
    current_key: str | None = None
    current_mapping: dict[str, Any] | None = None
    for line_number, line in enumerate(frontmatter.splitlines(), start=2):
        if not line.strip():
            continue
        if not line.startswith(" "):
            if ":" not in line:
                raise ContentBridgeError(f"unsupported frontmatter line {path}:{line_number}")
            key, raw_value = line.split(":", 1)
            current_key = key.strip()
            current_mapping = None
            payload[current_key] = _frontmatter_scalar(raw_value) if raw_value.strip() else []
            continue
        if line.startswith("  - ") and current_key:
            if not isinstance(payload.get(current_key), list):
                raise ContentBridgeError(f"frontmatter list conflicts with scalar {path}:{line_number}")
            raw_item = line[4:]
            if current_key == "relationships" and ":" in raw_item:
                key, raw_value = raw_item.split(":", 1)
                current_mapping = {key.strip(): _frontmatter_scalar(raw_value)}
                payload[current_key].append(current_mapping)
            else:
                current_mapping = None
                payload[current_key].append(_frontmatter_scalar(raw_item))
            continue
        if line.startswith("    ") and current_mapping is not None and ":" in line:
            key, raw_value = line.strip().split(":", 1)
            current_mapping[key.strip()] = _frontmatter_scalar(raw_value)
            continue
        raise ContentBridgeError(f"unsupported frontmatter indentation {path}:{line_number}")
    payload.update(
        {
            "upstream_path": path.resolve().relative_to(root.resolve()).as_posix(),
            "content_sha256": sha256_file(path),
            "body_markdown": body,
        }
    )
    return payload


def _markdown_section(markdown: str, heading: str) -> str:
    pattern = re.compile(
        rf"(?ms)^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)"
    )
    match = pattern.search(markdown)
    return match.group(1).strip() if match else ""


def _assembly_skeleton(markdown: str) -> dict[str, Any]:
    section = _markdown_section(markdown, "表达骨架")
    parts: dict[str, str] = {}
    matches = list(re.finditer(r"(?m)^### (.+?)\s*$", section))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        parts[match.group(1).strip()] = section[match.end() : end].strip()
    middle = [value for key, value in parts.items() if key.startswith("中段") and value]
    return {
        "opening": parts.get("开头", ""),
        "middle": middle,
        "closing": parts.get("结尾", ""),
    }


def _assembly_structure(markdown: str) -> list[str]:
    section = _markdown_section(markdown, "建议结构")
    result = []
    for line in section.splitlines():
        match = re.match(r"\s*\d+[.、]\s*(.+)", line)
        if match and match.group(1).strip():
            result.append(match.group(1).strip())
    return result


def export_dbs_content_package(
    content_root: Path,
    assembly_path: Path,
    output_path: Path,
) -> Path:
    root = content_root.expanduser().resolve()
    assembly = assembly_path.expanduser().resolve()
    output = output_path.expanduser().resolve()
    try:
        assembly.relative_to(root)
    except ValueError as error:
        raise ContentBridgeError("assembly path must be inside the dbs-content-system root") from error
    if not assembly.is_file():
        raise ContentBridgeError(f"assembly does not exist: {assembly}")
    assembly_markdown = assembly.read_text(encoding="utf-8")
    unit_root = root / "02-内容单元库"
    if not unit_root.is_dir():
        raise ContentBridgeError(f"content unit library is missing: {unit_root}")
    unit_index: dict[str, dict[str, Any]] = {}
    for path in sorted(unit_root.rglob("*.md")):
        unit = parse_dbs_content_unit(path, root)
        identifier = _string(unit.get("id"), f"content unit id in {path}")
        if identifier in unit_index:
            raise ContentBridgeError(f"duplicate upstream content unit id: {identifier}")
        unit_index[identifier] = unit

    linked_ids = []
    for raw_link in re.findall(r"\[\[([^\]|#]+)", assembly_markdown):
        basename = PurePosixPath(raw_link).name
        match = re.match(r"((?:QST|CON|OPI|CAS|SOL)-\d{8}-\d{3,})", basename)
        if match and match.group(1) not in linked_ids:
            linked_ids.append(match.group(1))
    if not linked_ids:
        raise ContentBridgeError("assembly contains no content-unit links")
    missing_linked = sorted(set(linked_ids) - set(unit_index))
    if missing_linked:
        raise ContentBridgeError(f"assembly links unknown content units: {missing_linked}")

    packaged_ids = set(linked_ids)
    queue = list(linked_ids)
    while queue:
        unit_id = queue.pop(0)
        for relationship in unit_index[unit_id].get("relationships", []):
            if not isinstance(relationship, dict):
                continue
            target = str(relationship.get("target", ""))
            if target and target not in unit_index:
                raise ContentBridgeError(f"content unit {unit_id} relationship targets unknown unit: {target}")
            if target and target not in packaged_ids:
                packaged_ids.add(target)
                queue.append(target)
    units = [unit_index[unit_id] for unit_id in sorted(packaged_ids)]

    registry_path = root / "03-处理状态/来源注册表.csv"
    if not registry_path.is_file():
        raise ContentBridgeError(f"source registry is missing: {registry_path}")
    with registry_path.open(encoding="utf-8-sig", newline="") as source:
        registry = {row.get("source_id", ""): row for row in csv.DictReader(source)}
    source_ids = sorted(
        {
            source_id
            for unit in units
            for source_id in _string_list(unit.get("source_documents"), f"content unit {unit['id']}.source_documents")
        }
    )
    source_documents = []
    source_root = root / "01-原始素材区"
    for source_id in source_ids:
        row = registry.get(source_id)
        if not row:
            raise ContentBridgeError(f"content unit references source absent from registry: {source_id}")
        raw_path = _string(row.get("path"), f"source registry path for {source_id}")
        relative = PurePosixPath(raw_path)
        source_path = root / relative if relative.parts[:1] == ("01-原始素材区",) else source_root / relative
        source_path = source_path.resolve()
        try:
            source_relative = source_path.relative_to(root).as_posix()
        except ValueError as error:
            raise ContentBridgeError(f"source registry path escapes content root: {raw_path}") from error
        if not source_path.is_file():
            raise ContentBridgeError(f"registered source file is missing: {source_path}")
        source_documents.append(
            {
                "id": source_id,
                "relative_path": source_relative,
                "source_type": _string(row.get("source_type"), f"source type for {source_id}"),
                "author": _string(row.get("author"), f"source author for {source_id}"),
                "upstream_status": _string(row.get("status"), f"source status for {source_id}"),
                "notes": str(row.get("notes") or ""),
                "content_sha256": sha256_file(source_path),
                "upstream_registry_path": registry_path.relative_to(root).as_posix(),
            }
        )

    selected = {prefix: [unit_id for unit_id in linked_ids if unit_id.startswith(prefix + "-")] for prefix in UNIT_TYPES}
    claims = []
    for opinion_id in selected["OPI"]:
        opinion = unit_index[opinion_id]
        related_cases = [
            unit["id"]
            for unit in units
            if unit["id"].startswith("CAS-")
            and any(
                relationship.get("type") == "证明" and relationship.get("target") == opinion_id
                for relationship in unit.get("relationships", [])
                if isinstance(relationship, dict)
            )
        ]
        reviewed = opinion.get("canonical") is True and opinion.get("status") in {
            "已核对",
            "已审核",
            "已完成",
            "可用",
        }
        claims.append(
            {
                "id": f"CLM:{opinion_id}:core_claim",
                "origin": {"content_unit_id": opinion_id, "field": "core_claim"},
                "claim_type": "interpretation",
                "text_zh": opinion.get("core_claim", ""),
                "text_en": "",
                "source_document_ids": list(opinion.get("source_documents", [])),
                "content_unit_ids": [opinion_id, *related_cases],
                "quote_refs": [],
                "status": "reviewed" if reviewed else "draft",
                "risk_level": "low",
            }
        )

    assembly_sha = sha256_file(assembly)
    identity = hashlib.sha256(
        _canonical_bytes(
            {
                "assembly": {
                    "path": assembly.relative_to(root).as_posix(),
                    "sha256": assembly_sha,
                    "selected_unit_ids": selected,
                },
                "content_units": units,
                "source_documents": source_documents,
                "claims": claims,
            }
        )
    ).hexdigest()
    title_match = re.search(r"(?m)^# 选题装配：(.+?)\s*$", assembly_markdown)
    title = title_match.group(1).strip() if title_match else assembly.stem
    package = {
        "schema_version": "1.0",
        "package_id": f"PKG-{identity[:24].upper()}",
        "source_system": {
            "name": "dbs-content-system",
            "snapshot_id": f"SNAP-{identity[:24].upper()}",
            "exported_at": _utc_now(),
        },
        "source_documents": source_documents,
        "content_units": units,
        "claims": claims,
        "assembly_brief": {
            "id": f"ASM-{identity[:24].upper()}",
            "title": title,
            "target_audience": _markdown_section(assembly_markdown, "目标受众"),
            "assembly_reason": _markdown_section(assembly_markdown, "装配理由"),
            "upstream_path": assembly.relative_to(root).as_posix(),
            "content_sha256": assembly_sha,
            "unit_ids": selected,
            "claim_ids": [claim["id"] for claim in claims],
            "suggested_structure": _assembly_structure(assembly_markdown),
            "expression_skeleton": _assembly_skeleton(assembly_markdown),
        },
    }
    validate_content_package(package)
    if output.exists():
        existing = _load_json(output, "existing content package")
        validate_content_package(existing)
        if content_package_sha256(existing) != content_package_sha256(package):
            raise ContentBridgeError(f"refusing to overwrite a different content package: {output}")
        return output
    _write_json_exclusive(output, package)
    return output


def _validate_source_documents(values: list[Any]) -> dict[str, dict[str, Any]]:
    documents = _unique_ids(values, "source_documents")
    for identifier, document in documents.items():
        if not identifier.startswith("SRC-") or identifier == "SRC-*":
            raise ContentBridgeError(f"invalid source document id: {identifier}")
        _relative_path(document.get("relative_path"), f"source document {identifier}.relative_path")
        _string(document.get("source_type"), f"source document {identifier}.source_type")
        _string(document.get("author"), f"source document {identifier}.author")
        _string(document.get("upstream_status"), f"source document {identifier}.upstream_status")
        _string(document.get("notes", ""), f"source document {identifier}.notes", nonempty=False)
        _sha256(document.get("content_sha256"), f"source document {identifier}.content_sha256")
        _relative_path(
            document.get("upstream_registry_path"),
            f"source document {identifier}.upstream_registry_path",
        )
    return documents


def _validate_content_units(
    values: list[Any], source_documents: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    units = _unique_ids(values, "content_units")
    for identifier, unit in units.items():
        match = UNIT_ID_RE.fullmatch(identifier)
        if not match:
            raise ContentBridgeError(f"invalid content unit id: {identifier}")
        prefix = match.group(1)
        if unit.get("type") != UNIT_TYPES[prefix]:
            raise ContentBridgeError(
                f"content unit {identifier} type must be {UNIT_TYPES[prefix]}"
            )
        _string(unit.get("title"), f"content unit {identifier}.title")
        source_ids = _string_list(
            unit.get("source_documents"),
            f"content unit {identifier}.source_documents",
            nonempty=True,
        )
        unknown_sources = sorted(set(source_ids) - set(source_documents))
        if unknown_sources:
            raise ContentBridgeError(
                f"content unit {identifier} references unknown source document: {unknown_sources}"
            )
        _string_list(unit.get("source_authors"), f"content unit {identifier}.source_authors", nonempty=True)
        _string_list(unit.get("themes"), f"content unit {identifier}.themes", nonempty=True)
        _string_list(unit.get("keywords"), f"content unit {identifier}.keywords", nonempty=True)
        _string(unit.get("status"), f"content unit {identifier}.status")
        if not isinstance(unit.get("canonical"), bool):
            raise ContentBridgeError(f"content unit {identifier}.canonical must be boolean")
        version = unit.get("version")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise ContentBridgeError(f"content unit {identifier}.version must be a positive integer")
        _string(unit.get("created_at"), f"content unit {identifier}.created_at")
        _string(unit.get("updated_at"), f"content unit {identifier}.updated_at")
        _relative_path(unit.get("upstream_path"), f"content unit {identifier}.upstream_path")
        _sha256(unit.get("content_sha256"), f"content unit {identifier}.content_sha256")
        _string(unit.get("body_markdown"), f"content unit {identifier}.body_markdown")
        for field in UNIT_FIELDS[prefix]:
            value = unit.get(field)
            if field in {"applicable_topics", "action_steps"}:
                _string_list(value, f"content unit {identifier}.{field}", nonempty=True)
            else:
                _string(value, f"content unit {identifier}.{field}")
        relationships = _list(
            unit.get("relationships"), f"content unit {identifier}.relationships"
        )
        for index, raw_relationship in enumerate(relationships):
            relationship = _mapping(
                raw_relationship,
                f"content unit {identifier}.relationships[{index}]",
            )
            relation_type = _string(
                relationship.get("type"),
                f"content unit {identifier}.relationships[{index}].type",
            )
            if relation_type not in RELATIONSHIP_TYPES:
                raise ContentBridgeError(
                    f"content unit {identifier} has unknown relationship type: {relation_type}"
                )
            target = _string(
                relationship.get("target"),
                f"content unit {identifier}.relationships[{index}].target",
            )
            if target not in units:
                raise ContentBridgeError(
                    f"content unit {identifier} relationship targets unknown unit: {target}"
                )
            _string(
                relationship.get("note", ""),
                f"content unit {identifier}.relationships[{index}].note",
                nonempty=False,
            )
    return units


def _validate_claims(
    values: list[Any],
    source_documents: dict[str, dict[str, Any]],
    content_units: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    claims = _unique_ids(values, "claims")
    for identifier, claim in claims.items():
        origin = _mapping(claim.get("origin"), f"claim {identifier}.origin")
        origin_id = _string(origin.get("content_unit_id"), f"claim {identifier}.origin.content_unit_id")
        field = _string(origin.get("field"), f"claim {identifier}.origin.field")
        if origin_id not in content_units:
            raise ContentBridgeError(f"claim {identifier} references unknown origin unit: {origin_id}")
        prefix = origin_id.split("-", 1)[0]
        if field not in CLAIM_ORIGIN_FIELDS.get(prefix, set()):
            raise ContentBridgeError(f"claim {identifier} uses unsupported origin field: {field}")
        expected_id = f"CLM:{origin_id}:{field}"
        if identifier != expected_id:
            raise ContentBridgeError(f"claim id must be deterministic: {expected_id}")
        claim_type = _string(claim.get("claim_type"), f"claim {identifier}.claim_type")
        if claim_type not in CLAIM_TYPES:
            raise ContentBridgeError(f"claim {identifier} has unknown claim_type: {claim_type}")
        text_zh = _string(claim.get("text_zh"), f"claim {identifier}.text_zh")
        if text_zh != str(content_units[origin_id][field]).strip():
            raise ContentBridgeError(f"claim {identifier}.text_zh diverges from its origin field")
        _string(claim.get("text_en", ""), f"claim {identifier}.text_en", nonempty=False)
        source_ids = _string_list(
            claim.get("source_document_ids"),
            f"claim {identifier}.source_document_ids",
            nonempty=True,
        )
        unknown_sources = sorted(set(source_ids) - set(source_documents))
        if unknown_sources:
            raise ContentBridgeError(
                f"claim {identifier} references unknown source document: {unknown_sources}"
            )
        unit_ids = _string_list(
            claim.get("content_unit_ids"),
            f"claim {identifier}.content_unit_ids",
            nonempty=True,
        )
        unknown_units = sorted(set(unit_ids) - set(content_units))
        if unknown_units:
            raise ContentBridgeError(f"claim {identifier} references unknown content unit: {unknown_units}")
        if origin_id not in unit_ids:
            raise ContentBridgeError(f"claim {identifier} must include its origin content unit")
        origin_sources = set(content_units[origin_id]["source_documents"])
        if not set(source_ids).issubset(origin_sources):
            raise ContentBridgeError(f"claim {identifier} source evidence diverges from its origin unit")
        for index, raw_quote in enumerate(_list(claim.get("quote_refs"), f"claim {identifier}.quote_refs")):
            quote = _mapping(raw_quote, f"claim {identifier}.quote_refs[{index}]")
            source_id = _string(
                quote.get("source_document_id"),
                f"claim {identifier}.quote_refs[{index}].source_document_id",
            )
            if source_id not in source_documents:
                raise ContentBridgeError(f"claim {identifier} quote references unknown source document: {source_id}")
            _string(quote.get("locator"), f"claim {identifier}.quote_refs[{index}].locator")
            _string(quote.get("excerpt", ""), f"claim {identifier}.quote_refs[{index}].excerpt", nonempty=False)
        status = _string(claim.get("status"), f"claim {identifier}.status")
        if status not in CLAIM_STATUSES:
            raise ContentBridgeError(f"claim {identifier} has unknown status: {status}")
        risk = _string(claim.get("risk_level"), f"claim {identifier}.risk_level")
        if risk not in RISK_LEVELS:
            raise ContentBridgeError(f"claim {identifier} has unknown risk_level: {risk}")
    return claims


def _validate_assembly(
    value: Any,
    content_units: dict[str, dict[str, Any]],
    claims: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    assembly = _mapping(value, "assembly_brief")
    identifier = _string(assembly.get("id"), "assembly_brief.id")
    if not identifier.startswith("ASM-"):
        raise ContentBridgeError("assembly_brief.id must start with ASM-")
    _string(assembly.get("title"), "assembly_brief.title")
    _string(assembly.get("target_audience"), "assembly_brief.target_audience")
    _string(assembly.get("assembly_reason"), "assembly_brief.assembly_reason")
    _relative_path(assembly.get("upstream_path"), "assembly_brief.upstream_path")
    _sha256(assembly.get("content_sha256"), "assembly_brief.content_sha256")
    buckets = _mapping(assembly.get("unit_ids"), "assembly_brief.unit_ids")
    production_eligible = True
    selected_units: set[str] = set()
    for prefix in UNIT_TYPES:
        bucket = _string_list(buckets.get(prefix), f"assembly_brief.unit_ids.{prefix}")
        if not bucket:
            production_eligible = False
        for unit_id in bucket:
            if unit_id not in content_units:
                raise ContentBridgeError(f"assembly {prefix} bucket references unknown unit: {unit_id}")
            if not unit_id.startswith(prefix + "-"):
                raise ContentBridgeError(f"assembly {prefix} bucket contains mismatched unit: {unit_id}")
            if not content_units[unit_id].get("canonical"):
                raise ContentBridgeError(f"assembly references non-canonical unit: {unit_id}")
            selected_units.add(unit_id)
    claim_ids = _string_list(assembly.get("claim_ids"), "assembly_brief.claim_ids")
    if not claim_ids:
        production_eligible = False
    for claim_id in claim_ids:
        if claim_id not in claims:
            raise ContentBridgeError(f"assembly references unknown claim: {claim_id}")
        claim = claims[claim_id]
        if claim.get("status") not in {"reviewed", "approved"}:
            production_eligible = False
        if not set(claim["content_unit_ids"]).intersection(selected_units):
            raise ContentBridgeError(f"assembly claim is disconnected from selected units: {claim_id}")
    _string_list(
        assembly.get("suggested_structure"),
        "assembly_brief.suggested_structure",
        nonempty=True,
    )
    skeleton = _mapping(assembly.get("expression_skeleton"), "assembly_brief.expression_skeleton")
    _string(skeleton.get("opening"), "assembly_brief.expression_skeleton.opening")
    _string_list(skeleton.get("middle"), "assembly_brief.expression_skeleton.middle", nonempty=True)
    _string(skeleton.get("closing"), "assembly_brief.expression_skeleton.closing")
    return assembly, production_eligible


def validate_content_package(payload: Any) -> dict[str, Any]:
    package = _mapping(payload, "content package")
    if package.get("schema_version") != "1.0":
        raise ContentBridgeError("unsupported content package schema_version")
    package_id = _string(package.get("package_id"), "content package.package_id")
    if not SAFE_ID_RE.fullmatch(package_id):
        raise ContentBridgeError("content package.package_id is not path-safe")
    source_system = _mapping(package.get("source_system"), "content package.source_system")
    if source_system.get("name") != "dbs-content-system":
        raise ContentBridgeError("content package.source_system.name must be dbs-content-system")
    _string(source_system.get("snapshot_id"), "content package.source_system.snapshot_id")
    _string(source_system.get("exported_at"), "content package.source_system.exported_at")
    source_documents = _validate_source_documents(
        _list(package.get("source_documents"), "content package.source_documents", nonempty=True)
    )
    content_units = _validate_content_units(
        _list(package.get("content_units"), "content package.content_units", nonempty=True),
        source_documents,
    )
    claims = _validate_claims(
        _list(package.get("claims"), "content package.claims"),
        source_documents,
        content_units,
    )
    assembly, production_eligible = _validate_assembly(
        package.get("assembly_brief"), content_units, claims
    )
    return {
        "schema_version": "1.0",
        "package_id": package_id,
        "package_sha256": content_package_sha256(package),
        "assembly_id": assembly["id"],
        "counts": {
            "source_documents": len(source_documents),
            "content_units": len(content_units),
            "claims": len(claims),
        },
        "production_eligible": production_eligible,
    }


def _load_json(path: Path, label: str) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContentBridgeError(f"cannot load {label} {resolved}: {error}") from error
    return _mapping(payload, label)


def _project_contract(project: Path) -> dict[str, Any]:
    path = project.resolve() / "project.json"
    return _load_json(path, "project contract")


def _project_mode(project: Path) -> str:
    contract = _project_contract(project)
    workflow = contract.get("workflow")
    if not isinstance(workflow, dict):
        return "single-book"
    return str(workflow.get("mode") or "single-book")


def _require_content_mode(project: Path) -> None:
    if _project_mode(project) != "content-system-backed":
        raise ContentBridgeError("content package import requires a content-system-backed project")


def _write_json_exclusive(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write("\n")
    return path


def _event_filename(event_time: str, event_id: str) -> str:
    return f"{event_time.replace(':', '-').replace('+', '_')}-{event_id}.json"


def _latest_event(project: Path, event_type: str) -> tuple[Path, dict[str, Any]] | None:
    directory = project.resolve() / "logs" / f"{event_type}_events"
    paths = sorted(directory.glob("*.json")) if directory.is_dir() else []
    if not paths:
        return None
    path = paths[-1]
    event = _load_json(path, f"{event_type} activation event")
    if event.get("schema_version") != "1.0" or event.get("project_id") != project.resolve().name:
        raise ContentBridgeError(f"invalid {event_type} activation event: {path}")
    return path, event


def _activate_import(project: Path, manifest_path: Path, package_sha256: str) -> Path | None:
    root = project.resolve()
    relative = _project_relative(root, manifest_path)
    manifest_sha = sha256_file(manifest_path)
    latest = _latest_event(root, "content_import")
    if latest and latest[1].get("manifest_path") == relative and latest[1].get("manifest_sha256") == manifest_sha:
        return None
    event_time = _utc_now()
    event_id = str(uuid.uuid4())
    path = safe_project_output(
        root,
        root / "logs/content_import_events" / _event_filename(event_time, event_id),
    )
    return _write_json_exclusive(
        path,
        {
            "schema_version": "1.0",
            "event_id": event_id,
            "project_id": root.name,
            "event_type": "content_import_activated",
            "activated_at": event_time,
            "package_sha256": package_sha256,
            "manifest_path": relative,
            "manifest_sha256": manifest_sha,
        },
    )


def _activate_traceability(project: Path, traceability_path: Path) -> Path | None:
    root = project.resolve()
    relative = _project_relative(root, traceability_path)
    trace_sha = sha256_file(traceability_path)
    latest = _latest_event(root, "traceability")
    if latest and latest[1].get("traceability_path") == relative and latest[1].get("traceability_sha256") == trace_sha:
        return None
    event_time = _utc_now()
    event_id = str(uuid.uuid4())
    path = safe_project_output(
        root,
        root / "logs/traceability_events" / _event_filename(event_time, event_id),
    )
    return _write_json_exclusive(
        path,
        {
            "schema_version": "1.0",
            "event_id": event_id,
            "project_id": root.name,
            "event_type": "traceability_activated",
            "activated_at": event_time,
            "traceability_path": relative,
            "traceability_sha256": trace_sha,
        },
    )


def _project_relative(project: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError as error:
        raise ContentBridgeError(f"path is outside project: {path}") from error


def _ensure_stage_manifest(
    project: Path,
    *,
    stage: str,
    release_id: str,
    release_profile_id: str,
    inputs: list[tuple[str, Path]],
    outputs: list[tuple[str, Path]],
    checks: list[dict[str, Any]],
    producer: str,
    manifest_id: str,
    recorded_at: str,
) -> Path:
    """Write or verify one deterministic stage manifest before activation."""
    root = project.resolve()
    try:
        path = write_stage_manifest(
            root,
            stage=stage,
            release_id=release_id,
            release_profile_id=release_profile_id,
            inputs=inputs,
            outputs=outputs,
            checks=checks,
            producer=producer,
            manifest_id=manifest_id,
            recorded_at=recorded_at,
        )
    except FileExistsError:
        matches = list((root / "manifests/stages" / stage).glob(f"*-{manifest_id}.json"))
        if len(matches) != 1:
            raise ContentBridgeError(
                f"cannot locate deterministic stage manifest {stage}/{manifest_id}"
            )
        path = matches[0]

    payload = _load_json(path, f"{stage} stage manifest")
    expected = {
        "schema_version": "1.0",
        "manifest_id": manifest_id,
        "project_id": root.name,
        "stage": stage,
        "release_id": release_id,
        "release_profile_id": release_profile_id,
        "producer": {"tool": producer},
        "recorded_at": recorded_at,
        "status": (
            "success"
            if all(
                item.get("result") == "pass"
                for item in checks
                if item.get("severity") == "error"
            )
            else "failed"
        ),
        "inputs": [manifest_artifact(root, role, path) for role, path in inputs],
        "outputs": [manifest_artifact(root, role, path) for role, path in outputs],
        "checks": checks,
        "approval_event_ids": [],
        "cost_event_ids": [],
    }
    if payload != expected:
        raise ContentBridgeError(f"deterministic stage manifest changed: {path}")
    return path


def _release_profile_id(project: Path) -> str:
    contract = _project_contract(project)
    workflow = contract.get("workflow") if isinstance(contract.get("workflow"), dict) else {}
    return str(workflow.get("release_profile_id", "book-v4-bilingual-3x4"))


def _ensure_content_import_stage(project: Path, imported: dict[str, Any]) -> Path:
    manifest = imported["manifest"]
    manifest_path = imported["manifest_path"]
    snapshot_path = imported["snapshot_path"]
    outputs = [
        manifest_path.parent / item["path"]
        for item in manifest["artifacts"]
        if item["path"] != "package.json"
    ]
    package_sha = imported["validation"]["package_sha256"]
    return _ensure_stage_manifest(
        project,
        stage="research.content_bridge",
        release_id=f"content-{imported['validation']['assembly_id'].lower()}",
        release_profile_id=_release_profile_id(project),
        inputs=[("content_package_snapshot", snapshot_path)],
        outputs=[("content_import_manifest", manifest_path)]
        + [("normalized_content_object", path) for path in outputs],
        checks=[
            {"id": "content_package_contract", "result": "pass", "severity": "error"},
            {
                "id": "production_eligible",
                "result": "pass" if imported["validation"]["production_eligible"] else "fail",
                "severity": "error",
            },
        ],
        producer="book-video-factory.content-bridge",
        manifest_id=f"content-{package_sha[:24]}",
        recorded_at=_string(manifest.get("imported_at"), "content import imported_at"),
    )


def import_content_package(project: Path, package_path: Path) -> Path:
    root = project.expanduser().resolve()
    _require_content_mode(root)
    source_path = package_path.expanduser().resolve()
    package = _load_json(source_path, "content package")
    validation = validate_content_package(package)
    target = (
        root
        / "01_research_资料搜集/content_system/imports"
        / validation["package_id"]
        / validation["package_sha256"]
    )
    safe_project_output(root, target)
    safe_project_output(root, root / "logs/content_import_events/.write-probe")
    safe_project_output(
        root,
        root / "manifests/stages/research.content_bridge/.write-probe",
    )
    manifest_path = target / "import_manifest.json"
    if target.exists():
        if not manifest_path.is_file():
            raise ContentBridgeError(f"incomplete immutable content import exists: {target}")
        imported = _validate_import_manifest(root, manifest_path)
        _ensure_content_import_stage(root, imported)
        _activate_import(root, manifest_path, validation["package_sha256"])
        return manifest_path

    target.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=".content-import-", dir=target.parent))
    try:
        snapshot = _write_json_exclusive(temp / "package.json", package)
        objects_dir = temp / "objects"
        source_objects = _write_json_exclusive(
            objects_dir / "source_documents.json",
            {"schema_version": "1.0", "objects": package["source_documents"]},
        )
        unit_objects = _write_json_exclusive(
            objects_dir / "content_units.json",
            {"schema_version": "1.0", "objects": package["content_units"]},
        )
        claim_objects = _write_json_exclusive(
            objects_dir / "claims.json",
            {"schema_version": "1.0", "objects": package["claims"]},
        )
        assembly_object = _write_json_exclusive(
            objects_dir / "assembly_brief.json",
            {"schema_version": "1.0", "object": package["assembly_brief"]},
        )
        object_paths = [snapshot, source_objects, unit_objects, claim_objects, assembly_object]
        import_manifest = {
            "schema_version": "1.0",
            "import_id": f"IMP-{validation['package_sha256'][:20].upper()}",
            "project_id": root.name,
            "package_id": validation["package_id"],
            "package_sha256": validation["package_sha256"],
            "assembly_id": validation["assembly_id"],
            "source_system": package["source_system"],
            "source_package_path": str(source_path),
            "source_package_file_sha256": sha256_file(source_path),
            "imported_at": _utc_now(),
            "production_eligible": validation["production_eligible"],
            "object_counts": validation["counts"],
            "artifacts": [
                {
                    "path": path.relative_to(temp).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for path in object_paths
            ],
        }
        _write_json_exclusive(temp / "import_manifest.json", import_manifest)
        temp.replace(target)
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise

    imported = _validate_import_manifest(root, manifest_path)
    _ensure_content_import_stage(root, imported)
    _activate_import(root, manifest_path, validation["package_sha256"])
    return manifest_path


def _validate_import_manifest(project: Path, manifest_path: Path) -> dict[str, Any]:
    root = project.resolve()
    manifest = _load_json(manifest_path, "content import manifest")
    if manifest.get("schema_version") != "1.0" or manifest.get("project_id") != root.name:
        raise ContentBridgeError("content import manifest does not belong to this project")
    artifacts = _list(manifest.get("artifacts"), "content import manifest.artifacts", nonempty=True)
    snapshot_path: Path | None = None
    for raw_artifact in artifacts:
        item = _mapping(raw_artifact, "content import artifact")
        relative = _relative_path(item.get("path"), "content import artifact.path")
        path = (manifest_path.parent / relative).resolve()
        try:
            path.relative_to(manifest_path.parent.resolve())
        except ValueError as error:
            raise ContentBridgeError("content import artifact escapes its immutable snapshot") from error
        if not path.is_file():
            raise ContentBridgeError(f"content import artifact is missing: {path}")
        if sha256_file(path) != item.get("sha256"):
            raise ContentBridgeError(f"content import artifact hash changed: {path}")
        if relative == "package.json":
            snapshot_path = path
    if snapshot_path is None:
        raise ContentBridgeError("content import manifest has no package snapshot")
    package = _load_json(snapshot_path, "content package snapshot")
    validation = validate_content_package(package)
    if validation["package_sha256"] != manifest.get("package_sha256"):
        raise ContentBridgeError("content import package hash changed")
    if validation["counts"] != manifest.get("object_counts"):
        raise ContentBridgeError("content import object counts changed")
    if validation["production_eligible"] != manifest.get("production_eligible"):
        raise ContentBridgeError("content import eligibility changed")
    return {
        "manifest": manifest,
        "manifest_path": manifest_path,
        "snapshot_path": snapshot_path,
        "package": package,
        "validation": validation,
    }


def _latest_import(project: Path) -> dict[str, Any]:
    root = project.resolve()
    activation = _latest_event(root, "content_import")
    if activation is None:
        raise ContentBridgeError("no activated content package import exists")
    event_path, event = activation
    path = _project_file(root, event.get("manifest_path"), "content import activation manifest_path")
    if sha256_file(path) != event.get("manifest_sha256"):
        raise ContentBridgeError(f"content import activation is stale: {event_path}")
    imported = _validate_import_manifest(root, path)
    if imported["validation"]["package_sha256"] != event.get("package_sha256"):
        raise ContentBridgeError("content import activation targets the wrong package hash")
    imported["activation_event_path"] = event_path
    return imported


def _project_file(project: Path, value: Any, label: str) -> Path:
    relative = _relative_path(value, label)
    root = project.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ContentBridgeError(f"{label} escapes the project") from error
    if not path.is_file():
        raise ContentBridgeError(f"{label} does not exist: {relative}")
    return path


def _scene_line_map(
    project: Path, scene_manifest: dict[str, Any]
) -> dict[str, tuple[str, ...]]:
    root = project.resolve()
    raw_assets = scene_manifest.get("assets", scene_manifest.get("scenes"))
    assets = _list(raw_assets, "scene manifest assets", nonempty=True)
    result: dict[str, tuple[str, ...]] = {}
    image_hashes: set[str] = set()
    for index, raw_asset in enumerate(assets):
        asset = _mapping(raw_asset, f"scene manifest assets[{index}]")
        scene_id = _string(asset.get("id"), f"scene manifest assets[{index}].id")
        if scene_id in result:
            raise ContentBridgeError(f"duplicate scene manifest id: {scene_id}")
        expected_file = f"03_images_生成图片/approved/v4/{scene_id}.png"
        asset_file = _relative_path(asset.get("file"), f"scene manifest {scene_id}.file")
        if asset_file != expected_file:
            raise ContentBridgeError(f"scene manifest file diverges for {scene_id}")
        image_path = _project_file(root, asset_file, f"scene manifest {scene_id}.file")
        expected_sha = _sha256(asset.get("sha256"), f"scene manifest {scene_id}.sha256")
        actual_sha = sha256_file(image_path)
        if actual_sha != expected_sha:
            raise ContentBridgeError(f"scene image hash changed: {scene_id}")
        if actual_sha in image_hashes:
            raise ContentBridgeError(f"scene images must be unique: {scene_id}")
        image_hashes.add(actual_sha)
        _string(asset.get("prompt"), f"scene manifest {scene_id}.prompt")
        _string(asset.get("generator"), f"scene manifest {scene_id}.generator")
        result[scene_id] = tuple(
            _string_list(asset.get("line_ids"), f"scene manifest {scene_id}.line_ids", nonempty=True)
        )
    expected = dict(V4_SCENE_LINE_CONTRACT)
    if result != expected:
        raise ContentBridgeError("scene manifest diverges from the renderer scene contract")
    return result


def _validate_traceability_payload(
    project: Path,
    payload: dict[str, Any],
    imported: dict[str, Any],
) -> dict[str, Any]:
    root = project.resolve()
    if payload.get("schema_version") != "1.0":
        raise ContentBridgeError("unsupported traceability schema_version")
    traceability_id = _string(payload.get("traceability_id"), "traceability.traceability_id")
    if not traceability_id.startswith("TRC-"):
        raise ContentBridgeError("traceability.traceability_id must start with TRC-")
    if payload.get("project_id") != root.name:
        raise ContentBridgeError("traceability project_id does not match the project")
    release_id = _string(payload.get("release_id"), "traceability.release_id")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", release_id):
        raise ContentBridgeError("traceability.release_id is not path-safe")
    package_sha = _sha256(
        payload.get("content_package_sha256"),
        "traceability.content_package_sha256",
    )
    if package_sha != imported["validation"]["package_sha256"]:
        raise ContentBridgeError("traceability does not target the latest imported content package")
    script_path = _project_file(project, payload.get("script_path"), "traceability.script_path")
    scene_path = _project_file(
        project,
        payload.get("scene_manifest_path"),
        "traceability.scene_manifest_path",
    )
    script = _load_json(script_path, "script")
    raw_lines = _list(script.get("lines"), "script.lines", nonempty=True)
    lines: dict[str, dict[str, Any]] = {}
    for index, raw_line in enumerate(raw_lines):
        line = _mapping(raw_line, f"script.lines[{index}]")
        line_id = _string(line.get("id"), f"script.lines[{index}].id")
        if line_id in lines:
            raise ContentBridgeError(f"duplicate script line id: {line_id}")
        lines[line_id] = line
    scene_manifest = _load_json(scene_path, "scene manifest")
    scene_map = _scene_line_map(root, scene_manifest)
    expected_line_scenes: dict[str, list[str]] = {}
    for scene_id, line_ids in scene_map.items():
        for line_id in line_ids:
            expected_line_scenes.setdefault(line_id, []).append(scene_id)
    if set(expected_line_scenes) != set(lines):
        raise ContentBridgeError("renderer scene contract does not cover every script line")

    package = imported["package"]
    claims = {item["id"]: item for item in package["claims"]}
    assembly_claims = set(package["assembly_brief"]["claim_ids"])
    raw_links = _list(payload.get("links"), "traceability.links", nonempty=True)
    links: dict[str, dict[str, Any]] = {}
    for index, raw_link in enumerate(raw_links):
        link = _mapping(raw_link, f"traceability.links[{index}]")
        line_id = _string(link.get("script_line_id"), f"traceability.links[{index}].script_line_id")
        if line_id in links:
            raise ContentBridgeError(f"duplicate traceability script line: {line_id}")
        if line_id not in lines:
            raise ContentBridgeError(f"traceability references unknown script line: {line_id}")
        mode = _string(link.get("evidence_mode"), f"traceability link {line_id}.evidence_mode")
        claim_ids = _string_list(link.get("claim_ids"), f"traceability link {line_id}.claim_ids")
        if mode == "claim_backed":
            if not claim_ids:
                raise ContentBridgeError(f"claim-backed script line has no claims: {line_id}")
            for claim_id in claim_ids:
                if claim_id not in claims:
                    raise ContentBridgeError(f"traceability references unknown claim: {claim_id}")
                if claim_id not in assembly_claims:
                    raise ContentBridgeError(f"traceability claim is outside the assembly: {claim_id}")
                if claims[claim_id].get("status") not in {"reviewed", "approved"}:
                    raise ContentBridgeError(f"traceability claim is not reviewed: {claim_id}")
        elif mode == "editorial_no_claim":
            if claim_ids:
                raise ContentBridgeError(f"editorial-no-claim line cannot include claims: {line_id}")
            role = str(lines[line_id].get("role", ""))
            if role not in EDITORIAL_NO_CLAIM_ROLES:
                raise ContentBridgeError(f"script role cannot bypass claim evidence: {line_id}")
            _string(link.get("editorial_note"), f"traceability link {line_id}.editorial_note")
        else:
            raise ContentBridgeError(f"unknown traceability evidence mode: {mode}")
        scene_ids = _string_list(
            link.get("scene_ids"), f"traceability link {line_id}.scene_ids", nonempty=True
        )
        if scene_ids != expected_line_scenes[line_id]:
            raise ContentBridgeError(f"traceability scene mapping diverges for script line: {line_id}")
        links[line_id] = link
    if set(links) != set(lines):
        raise ContentBridgeError("traceability links must cover every script line exactly once")
    return {
        "traceability_id": traceability_id,
        "release_id": release_id,
        "script_path": script_path,
        "scene_manifest_path": scene_path,
        "script_line_count": len(lines),
        "claim_backed_line_count": sum(
            1 for link in links.values() if link["evidence_mode"] == "claim_backed"
        ),
    }


def _ensure_traceability_stage(
    project: Path,
    imported: dict[str, Any],
    traceability_path: Path,
    validation: dict[str, Any],
) -> Path:
    payload = _load_json(traceability_path, "attached traceability map")
    script_path = validation["script_path"]
    scene_path = validation["scene_manifest_path"]
    return _ensure_stage_manifest(
        project,
        stage="script.traceability",
        release_id=validation["release_id"],
        release_profile_id=_release_profile_id(project),
        inputs=[
            ("content_package_snapshot", imported["snapshot_path"]),
            ("script", script_path),
            ("scene_manifest", scene_path),
        ],
        outputs=[("traceability_map", traceability_path)],
        checks=[
            {"id": "script_claim_scene_links", "result": "pass", "severity": "error"},
            {"id": "renderer_scene_contract", "result": "pass", "severity": "error"},
        ],
        producer="book-video-factory.traceability",
        manifest_id=f"trace-{traceability_path.stem[:24]}",
        recorded_at=_string(payload.get("attached_at"), "traceability attached_at"),
    )


def attach_traceability(project: Path, traceability_path: Path) -> Path:
    root = project.expanduser().resolve()
    _require_content_mode(root)
    imported = _latest_import(root)
    source_path = traceability_path.expanduser().resolve()
    draft = _load_json(source_path, "traceability map")
    validation = _validate_traceability_payload(root, draft, imported)
    script_path = validation["script_path"]
    scene_path = validation["scene_manifest_path"]
    trace_digest = hashlib.sha256(
        _canonical_bytes(
            {
                "draft": draft,
                "script_sha256": sha256_file(script_path),
                "scene_manifest_sha256": sha256_file(scene_path),
            }
        )
    ).hexdigest()
    output = (
        root
        / "02_story_script_故事脚本/traceability"
        / validation["release_id"]
        / f"{trace_digest}.json"
    )
    safe_project_output(root, output)
    safe_project_output(root, root / "logs/traceability_events/.write-probe")
    safe_project_output(
        root,
        root / "manifests/stages/script.traceability/.write-probe",
    )
    if output.exists():
        attached_validation = _validate_attached_traceability(root, output, imported)
        _ensure_traceability_stage(
            root,
            imported,
            output,
            attached_validation["validation"],
        )
        _activate_traceability(root, output)
        return output
    attached = dict(draft)
    attached.update(
        {
            "attached_at": _utc_now(),
            "source_map_sha256": hashlib.sha256(_canonical_bytes(draft)).hexdigest(),
            "script_sha256": sha256_file(script_path),
            "scene_manifest_sha256": sha256_file(scene_path),
            "validation_summary": {
                "script_line_count": validation["script_line_count"],
                "claim_backed_line_count": validation["claim_backed_line_count"],
                "scene_contract": "book-v4-scene-line-v1",
            },
        }
    )
    _write_json_exclusive(output, attached)
    attached_validation = _validate_attached_traceability(root, output, imported)
    _ensure_traceability_stage(
        root,
        imported,
        output,
        attached_validation["validation"],
    )
    _activate_traceability(root, output)
    return output


def _validate_attached_traceability(
    project: Path, path: Path, imported: dict[str, Any]
) -> dict[str, Any]:
    payload = _load_json(path, "attached traceability map")
    validation = _validate_traceability_payload(project, payload, imported)
    if sha256_file(validation["script_path"]) != payload.get("script_sha256"):
        raise ContentBridgeError("traceability script hash is stale")
    if sha256_file(validation["scene_manifest_path"]) != payload.get("scene_manifest_sha256"):
        raise ContentBridgeError("traceability scene manifest hash is stale")
    return {"payload": payload, "path": path, "validation": validation}


def content_system_status(project: Path) -> dict[str, Any]:
    root = project.expanduser().resolve()
    mode = _project_mode(root)
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "project_id": root.name,
        "mode": mode,
        "required": mode == "content-system-backed",
        "content_package_valid": False,
        "production_eligible": False,
        "traceability_valid": False,
        "linked_script_lines": 0,
        "errors": [],
    }
    if mode != "content-system-backed":
        return result
    try:
        imported = _latest_import(root)
    except ContentBridgeError as error:
        result["errors"].append(str(error))
        return result
    result.update(
        {
            "content_package_valid": True,
            "production_eligible": imported["validation"]["production_eligible"],
            "package_id": imported["validation"]["package_id"],
            "package_sha256": imported["validation"]["package_sha256"],
            "assembly_id": imported["validation"]["assembly_id"],
            "import_manifest": _project_relative(root, imported["manifest_path"]),
            "package_snapshot": _project_relative(root, imported["snapshot_path"]),
            "content_activation_event": (
                _project_relative(root, imported["activation_event_path"])
                if imported.get("activation_event_path")
                else None
            ),
        }
    )
    trace_activation = _latest_event(root, "traceability")
    if trace_activation is None:
        result["errors"].append("no activated traceability map exists")
        return result
    event_path, event = trace_activation
    try:
        trace_path = _project_file(
            root,
            event.get("traceability_path"),
            "traceability activation path",
        )
    except ContentBridgeError as error:
        result["errors"].append(str(error))
        return result
    if sha256_file(trace_path) != event.get("traceability_sha256"):
        result["errors"].append(f"traceability activation is stale: {event_path}")
        return result
    try:
        trace = _validate_attached_traceability(root, trace_path, imported)
    except ContentBridgeError as error:
        result["errors"].append(str(error))
        return result
    result.update(
        {
            "traceability_valid": True,
            "linked_script_lines": trace["validation"]["script_line_count"],
            "traceability_map": _project_relative(root, trace_path),
            "release_id": trace["validation"]["release_id"],
            "traceability_activation_event": (
                _project_relative(root, trace_activation[0])
            ),
        }
    )
    return result
