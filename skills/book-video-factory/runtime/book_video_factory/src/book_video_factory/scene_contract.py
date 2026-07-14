from __future__ import annotations

from collections import OrderedDict


# This is the single V4 scene-to-script contract used by planning, rendering,
# manifests, and traceability validation. S03 is the generated background used
# by the real-cover composite for the V03 book reveal.
V4_SCENE_LINE_CONTRACT: "OrderedDict[str, tuple[str, ...]]" = OrderedDict(
    (
        ("S01", ("V01", "V02")),
        ("S02", ("V04",)),
        ("S03", ("V03",)),
        ("S04", ("V05", "V06")),
        ("S05", ("V07", "V08")),
        ("S06", ("V09",)),
        ("S07", ("V10",)),
        ("S08", ("V11",)),
        ("S09", ("V12",)),
        ("S10", ("V13",)),
        ("S11", ("V14",)),
        ("S12", ("V15",)),
    )
)


V4_TIMELINE_SCENES = (
    ("HOOK", "S01"),
    ("BOOK", "S03"),
    ("THESIS", "S02"),
    ("RELATION", "S04"),
    ("SUPPORT", "S05"),
    ("BOUNDARIES", "S06"),
    ("FIRST_STEP", "S07"),
    ("QUESTION", "S08"),
    ("SELF_CARE", "S09"),
    ("LOVE", "S10"),
    ("RAIN", "S11"),
    ("DAWN", "S12"),
)


def expected_line_to_scenes() -> dict[str, tuple[str, ...]]:
    result: dict[str, list[str]] = {}
    for scene_id, line_ids in V4_SCENE_LINE_CONTRACT.items():
        for line_id in line_ids:
            result.setdefault(line_id, []).append(scene_id)
    return {line_id: tuple(scene_ids) for line_id, scene_ids in result.items()}
