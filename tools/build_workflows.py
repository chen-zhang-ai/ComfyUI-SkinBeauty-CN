#!/usr/bin/env python3
"""Sanitize the V2.2 integration workflow and build two minimal examples."""

from __future__ import annotations

import copy
import json
import ntpath
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / "workflows"
INTEGRATION = WORKFLOW_DIR / "MiniMax_H3_SkinBeauty_Integration.json"
PURE = WORKFLOW_DIR / "SkinBeauty_Minimal_Pure_Algorithm.json"
AUTO = WORKFLOW_DIR / "SkinBeauty_Minimal_Auto_Semantic.json"

WINDOWS_ABSOLUTE = re.compile(r"(?i)(?<![a-z])[a-z]:[\\/](?![\\/])")
UNIX_ABSOLUTE = re.compile(r"(?:^|[\s\"'])/(?:home|Users)/")
SECRET_KEY = re.compile(r"(?i)(api.?key|access.?token|password|bearer|authorization|cookie)")


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def node_by_id(workflow: dict[str, Any], node_id: int) -> dict[str, Any]:
    return next(node for node in workflow["nodes"] if node["id"] == node_id)


def sanitize(value: Any, path: str = "$") -> tuple[Any, list[str]]:
    actions: list[str] = []
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            item_path = f"{path}.{key}"
            lowered = key.lower()
            if lowered == "fullpath" or SECRET_KEY.search(key):
                actions.append(f"removed {item_path}")
                continue
            if isinstance(item, str) and (WINDOWS_ABSOLUTE.search(item) or UNIX_ABSOLUTE.search(item)):
                if lowered in {"url", "cos_url"}:
                    cleaned[key] = ""
                    actions.append(f"cleared {item_path}")
                else:
                    cleaned[key] = ntpath.basename(item.replace("/", "\\"))
                    actions.append(f"reduced {item_path} to a basename")
                continue
            cleaned_item, nested = sanitize(item, item_path)
            cleaned[key] = cleaned_item
            actions.extend(nested)
        return cleaned, actions
    if isinstance(value, list):
        cleaned_list = []
        for index, item in enumerate(value):
            cleaned_item, nested = sanitize(item, f"{path}[{index}]")
            cleaned_list.append(cleaned_item)
            actions.extend(nested)
        return cleaned_list, actions
    if isinstance(value, str) and (WINDOWS_ABSOLUTE.search(value) or UNIX_ABSOLUTE.search(value)):
        actions.append(f"reduced {path} to a basename")
        return ntpath.basename(value.replace("/", "\\")), actions
    return value, actions


def validate_graph(workflow: dict[str, Any], strict_types: bool = True) -> None:
    nodes = {node["id"]: node for node in workflow["nodes"]}
    links = {link[0]: link for link in workflow["links"]}
    if len(nodes) != len(workflow["nodes"]):
        raise ValueError("duplicate node id")
    if len(links) != len(workflow["links"]):
        raise ValueError("duplicate link id")
    for link_id, link in links.items():
        _, source_id, source_slot, target_id, target_slot, link_type = link
        source = nodes[source_id]
        target = nodes[target_id]
        if source_slot >= len(source.get("outputs", [])) or target_slot >= len(target.get("inputs", [])):
            raise ValueError(f"link {link_id} has an out-of-range slot")
        if link_id not in (source["outputs"][source_slot].get("links") or []):
            raise ValueError(f"link {link_id} is not registered at its source")
        if target["inputs"][target_slot].get("link") != link_id:
            raise ValueError(f"link {link_id} is not registered at its target")
        source_type = source["outputs"][source_slot].get("type")
        target_type = target["inputs"][target_slot].get("type")
        if strict_types and (source_type != link_type or target_type != link_type):
            raise ValueError(f"link {link_id} has inconsistent types")


def validate_integration(workflow: dict[str, Any]) -> None:
    # Preserve unrelated third-party wildcard serialization.  Exact types are
    # enforced below for every link added or redirected by this project.
    validate_graph(workflow, strict_types=False)
    nodes = {node["id"]: node for node in workflow["nodes"]}
    links = {link[0]: link for link in workflow["links"]}
    if nodes[186]["inputs"][3].get("link") != 647 or nodes[186]["inputs"][4].get("link") != 650:
        raise ValueError("node 186 reference inputs changed")
    if links[647][1:6] != [273, 0, 186, 3, "IMAGE"]:
        raise ValueError("reference image 1 was swapped")
    if links[650][1:6] != [274, 0, 186, 4, "IMAGE"]:
        raise ValueError("reference image 0 was swapped")
    if links[582][1:6] != [139, 0, 273, 0, "IMAGE"] or links[550][1:6] != [137, 0, 274, 0, "IMAGE"]:
        raise ValueError("upstream reference sources changed")
    for link_id in (550, 582, 646, 647, 649, 650):
        _, source_id, source_slot, target_id, target_slot, link_type = links[link_id]
        if nodes[source_id]["outputs"][source_slot]["type"] != link_type:
            raise ValueError(f"link {link_id} source type changed")
        if nodes[target_id]["inputs"][target_slot]["type"] != link_type:
            raise ValueError(f"link {link_id} target type changed")
    if (nodes[139]["mode"], nodes[273]["mode"], nodes[137]["mode"], nodes[274]["mode"]) != (4, 4, 0, 0):
        raise ValueError("original bypass state changed")


def refresh_embedded_help(workflow: dict[str, Any]) -> None:
    """Clarify the model-only download boundary without changing saved enums."""

    note = node_by_id(workflow, 275)
    help_text = note["widgets_values"][0]
    marker = "- 本插件不会安装 OpenCV、MediaPipe 或其他新增依赖；已有MediaPipe时直接使用。"
    replacement = (
        "- “MediaPipe：仅允许下载模型，不安装Python包”仅下载固定哈希的模型文件；"
        "本插件不会安装 OpenCV、MediaPipe 或其他 Python 包。\n"
        "- The MediaPipe download option downloads the verified model only and never installs Python packages."
    )
    if marker in help_text:
        help_text = help_text.replace(marker, replacement)
    note["widgets_values"][0] = help_text


def load_image_node() -> dict[str, Any]:
    return {
        "id": 1,
        "type": "LoadImage",
        "pos": [60, 220],
        "size": [320, 310],
        "flags": {},
        "order": 0,
        "mode": 0,
        "inputs": [
            {"name": "image", "type": "COMBO", "widget": {"name": "image"}, "link": None},
            {"name": "upload", "type": "IMAGEUPLOAD", "widget": {"name": "upload"}, "link": None},
        ],
        "outputs": [
            {"name": "IMAGE", "type": "IMAGE", "links": [1]},
            {"name": "MASK", "type": "MASK", "links": None},
        ],
        "properties": {"Node name for S&R": "LoadImage"},
        "widgets_values": ["example.png", "image"],
    }


def preview_node() -> dict[str, Any]:
    return {
        "id": 4,
        "type": "PreviewImage",
        "pos": [1420, 260],
        "size": [360, 320],
        "flags": {},
        "order": 3,
        "mode": 0,
        "inputs": [{"name": "images", "type": "IMAGE", "link": 3}],
        "outputs": [],
        "properties": {"Node name for S&R": "PreviewImage"},
        "widgets_values": [],
    }


def minimal_workflow(integration: dict[str, Any], semantic_mode: str) -> dict[str, Any]:
    settings = copy.deepcopy(node_by_id(integration, 272))
    settings.update({"id": 2, "pos": [430, 40], "order": 1, "mode": 0})
    settings["title"] = "Skin Beauty Settings / 人物肤色美白参数"
    settings["outputs"][0]["links"] = [2]
    settings["outputs"][1]["links"] = []

    processor = copy.deepcopy(node_by_id(integration, 274))
    processor.update({"id": 3, "pos": [880, 80], "order": 2, "mode": 0})
    processor["title"] = "Skin Beauty Process + Preview / 处理＋预览"
    processor["inputs"][0]["link"] = 1
    processor["inputs"][1]["link"] = 2
    processor["widgets_values"][1] = semantic_mode
    processor["widgets_values"][5] = True
    processor["outputs"][0]["links"] = [3]
    for output in processor["outputs"][1:]:
        output["links"] = []

    workflow = {
        "last_node_id": 4,
        "last_link_id": 3,
        "nodes": [load_image_node(), settings, processor, preview_node()],
        "links": [
            [1, 1, 0, 3, 0, "IMAGE"],
            [2, 2, 0, 3, 1, "SKIN_BEAUTY_CONFIG"],
            [3, 3, 0, 4, 0, "IMAGE"],
        ],
        "groups": [],
        "config": {},
        "extra": {"workflowRendererVersion": "LG"},
        "version": integration.get("version", 0.4),
    }
    validate_graph(workflow)
    return workflow


def assert_clean(workflow: dict[str, Any]) -> None:
    serialized = json.dumps(workflow, ensure_ascii=False)
    if WINDOWS_ABSOLUTE.search(serialized) or UNIX_ABSOLUTE.search(serialized):
        raise ValueError("absolute path remains in workflow")
    if '"fullpath"' in serialized.lower():
        raise ValueError("fullpath remains in workflow")


def main() -> None:
    integration = load(INTEGRATION)
    integration, actions = sanitize(integration)
    refresh_embedded_help(integration)
    validate_integration(integration)
    assert_clean(integration)
    dump(INTEGRATION, integration)

    pure = minimal_workflow(integration, "纯算法：零依赖")
    auto = minimal_workflow(integration, "自动：已有模型则使用")
    assert_clean(pure)
    assert_clean(auto)
    dump(PURE, pure)
    dump(AUTO, auto)

    print(f"sanitized {INTEGRATION.name}: {len(actions)} action(s)")
    for action in actions:
        print(action)
    print(f"wrote {PURE.name} and {AUTO.name}")


if __name__ == "__main__":
    main()
