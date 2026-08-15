#!/usr/bin/env python3
"""Insert the skin-beauty nodes into the supplied MiniMax H3 workflow.

The script is intentionally strict: it verifies the two expected original
links before rewriting them, so it cannot silently patch an unrelated graph.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Dict, List


SETTINGS_ID = 272
PROCESSOR_REF1_ID = 273
PROCESSOR_REF0_ID = 274
INFO_ID = 275


def widget_input(name: str, kind: str) -> Dict[str, Any]:
    return {"label": name, "name": name, "type": kind, "widget": {"name": name}, "link": None}


def settings_node() -> Dict[str, Any]:
    inputs = [widget_input("预设", "COMBO")]
    inputs.extend(widget_input(name, "FLOAT") for name in (
        "总强度", "美白", "冷暖", "红润", "匀肤", "暗部提亮", "高光保护",
        "饱和度", "平滑", "纹理保留", "肤色识别", "蒙版羽化",
    ))
    return {
        "id": SETTINGS_ID,
        "type": "SkinBeautySettingsCN",
        "pos": [-1515, 7200],
        "size": [420, 590],
        "flags": {},
        "order": 52,
        "mode": 0,
        "inputs": inputs,
        "outputs": [
            {"label": "美白参数", "name": "美白参数", "type": "SKIN_BEAUTY_CONFIG", "links": [646, 649]},
            {"label": "参数摘要", "name": "参数摘要", "type": "STRING", "links": []},
        ],
        "title": "共享美白参数｜低中高档＋手动微调",
        "properties": {"Node name for S&R": "SkinBeautySettingsCN"},
        "widgets_values": ["中档·自然冷白", 72, 52, 42, 8, 28, 18, 72, -8, 12, 88, 58, 12],
        "color": "#74546d",
        "bgcolor": "#2a2029",
    }


def processor_node(node_id: int, order: int, position: List[float], source_link: int, config_link: int,
                   output_link: int, title: str, mode: int, realtime_exact: bool) -> Dict[str, Any]:
    inputs = [
        {"label": "图像", "name": "图像", "type": "IMAGE", "link": source_link},
        {"label": "美白参数", "name": "美白参数", "type": "SKIN_BEAUTY_CONFIG", "link": config_link},
        widget_input("蒙版模式", "COMBO"),
        widget_input("语义蒙版", "COMBO"),
        widget_input("批处理", "COMBO"),
        widget_input("计算设备", "COMBO"),
        widget_input("生成节点预览", "BOOLEAN"),
        widget_input("实时精确预览", "BOOLEAN"),
        {"label": "外部遮罩", "name": "外部遮罩", "shape": 7, "type": "MASK", "link": None},
    ]
    return {
        "id": node_id,
        "type": "SkinBeautyProcessorCN",
        "pos": position,
        "size": [520, 900],
        "flags": {},
        "order": order,
        "mode": mode,
        "inputs": inputs,
        "outputs": [
            {"label": "美白图像", "name": "美白图像", "type": "IMAGE", "links": [output_link]},
            {"label": "肤色蒙版", "name": "肤色蒙版", "type": "MASK", "links": []},
            {"label": "预览图", "name": "预览图", "type": "IMAGE", "links": []},
            {"label": "处理报告", "name": "处理报告", "type": "STRING", "links": []},
        ],
        "title": title,
        "properties": {"Node name for S&R": "SkinBeautyProcessorCN"},
        "widgets_values": [
            "自动肤色（推荐）",
            "自动：已有模型则使用",
            "自动：逐张省显存",
            "自动",
            True,
            realtime_exact,
        ],
        "color": "#376574",
        "bgcolor": "#17262d",
    }


def info_node() -> Dict[str, Any]:
    return {
        "id": INFO_ID,
        "type": "MarkdownNote",
        "pos": [-2070, 7200],
        "size": [500, 780],
        "flags": {},
        "order": 55,
        "mode": 0,
        "inputs": [],
        "outputs": [],
        "title": "使用说明｜人物肤色美白＋左右滑动对比",
        "properties": {"Node name for S&R": "MarkdownNote"},
        "widgets_values": [
            "# 人物肤色美白｜使用说明\n\n"
            "## 推荐流程\n\n"
            "1. 在节点272选择低/中/高预设，再按需微调。\n"
            "2. 处理节点默认使用“自动：已有模型则使用”，恢复V1精准人物肤色识别。\n"
            "3. 调节节点272任意参数后，活动参考图会自动防抖刷新精确预览。\n"
            "4. “刷新精确预览（不跑视频）”用于手动强制刷新。\n"
            "5. 在大图中左右拖动竖线对比：左侧原图，右侧美白结果。\n\n"
            "## 参数作用\n\n"
            "- **总强度**：控制全部效果的混合比例。\n"
            "- **美白**：提高皮肤明度，不改变画布尺寸。\n"
            "- **冷暖**：正值减少黄感并偏冷；负值偏暖。\n"
            "- **红润**：补充自然血色，过高会偏红。\n"
            "- **匀肤**：均衡肤色明暗与局部色差。\n"
            "- **暗部提亮**：提亮皮肤阴影区域。\n"
            "- **高光保护**：避免额头、鼻梁等区域过曝。\n"
            "- **饱和度**：控制皮肤颜色浓淡。\n"
            "- **平滑**：轻度柔化肤质。\n"
            "- **纹理保留**：保留毛孔、绒毛与皮肤细节。\n"
            "- **肤色识别**：调节自动肤色蒙版覆盖范围。\n"
            "- **蒙版羽化**：柔化皮肤与非皮肤边界。\n\n"
            "## 质量与依赖\n\n"
            "- 送入节点186的“美白图像”始终保持原始宽高。\n"
            "- 节点内缩放仅用于屏幕显示，不压缩工作流图像。\n"
            "- “自动：已有模型则使用”已组合MediaPipe语义位置和内置肤色约束。\n"
            "- “MediaPipe：仅允许下载模型，不安装Python包”只下载校验模型；插件绝不安装 Python 包。\n"
            "- The MediaPipe download option downloads the verified model only and never installs Python packages.\n"
            "- 米色衣服/背景误选时，可接手工 MASK 并选“仅外部遮罩”。\n"
        ],
    }


def find_node(workflow: Dict[str, Any], node_id: int) -> Dict[str, Any]:
    try:
        return next(node for node in workflow["nodes"] if node["id"] == node_id)
    except StopIteration as exc:
        raise ValueError(f"工作流缺少预期节点 {node_id}") from exc


def find_link(workflow: Dict[str, Any], link_id: int) -> List[Any]:
    try:
        return next(link for link in workflow["links"] if link[0] == link_id)
    except StopIteration as exc:
        raise ValueError(f"工作流缺少预期连线 {link_id}") from exc


def inject(source: Dict[str, Any]) -> Dict[str, Any]:
    workflow = copy.deepcopy(source)
    if any(node.get("type") in {"SkinBeautySettingsCN", "SkinBeautyProcessorCN"} for node in workflow["nodes"]):
        raise ValueError("工作流已经包含 SkinBeauty-CN 节点，拒绝重复注入")

    link_582 = find_link(workflow, 582)
    link_550 = find_link(workflow, 550)
    if link_582[1:6] != [139, 0, 186, 3, "IMAGE"]:
        raise ValueError(f"连线 582 与预期不符: {link_582}")
    if link_550[1:6] != [137, 0, 186, 4, "IMAGE"]:
        raise ValueError(f"连线 550 与预期不符: {link_550}")

    node_186 = find_node(workflow, 186)
    source_139 = find_node(workflow, 139)
    source_137 = find_node(workflow, 137)
    if node_186["inputs"][3].get("link") != 582 or node_186["inputs"][4].get("link") != 550:
        raise ValueError("节点 186 的两路参考图输入与预期不符")

    # Reuse each original source link and redirect its target to a processor.
    link_582[3:5] = [PROCESSOR_REF1_ID, 0]
    link_550[3:5] = [PROCESSOR_REF0_ID, 0]
    node_186["inputs"][3]["link"] = 647
    node_186["inputs"][4]["link"] = 650

    # Node 139 was bypassed in the original.  Mirror its mode on the added
    # processor and preview so the unchanged workflow remains valid.
    ref1_mode = 4 if source_139.get("mode") == 4 else 0
    ref0_mode = 4 if source_137.get("mode") == 4 else 0
    workflow["nodes"].extend([
        settings_node(),
        processor_node(
            PROCESSOR_REF1_ID, 53, [-1040, 8170], 582, 646, 647,
            "参考图1美白｜送入186图像0（原分支为旁路）", ref1_mode, False,
        ),
        processor_node(
            PROCESSOR_REF0_ID, 54, [-1040, 7200], 550, 649, 650,
            "参考图0美白｜送入186图像1", ref0_mode, True,
        ),
        info_node(),
    ])

    workflow["links"].extend([
        [646, SETTINGS_ID, 0, PROCESSOR_REF1_ID, 1, "SKIN_BEAUTY_CONFIG"],
        [647, PROCESSOR_REF1_ID, 0, 186, 3, "IMAGE"],
        [649, SETTINGS_ID, 0, PROCESSOR_REF0_ID, 1, "SKIN_BEAUTY_CONFIG"],
        [650, PROCESSOR_REF0_ID, 0, 186, 4, "IMAGE"],
    ])
    workflow.setdefault("groups", []).append({
        "id": 11,
        "title": "新增｜参考图肤色美白＋节点内左右对比（节点139原旁路状态已保留）",
        "bounding": [-2120, 7135, 1670, 2010],
        "color": "#7d5473",
        "font_size": 24,
        "flags": {},
    })
    workflow["last_node_id"] = INFO_ID
    workflow["last_link_id"] = 651
    validate(workflow)
    return workflow


def validate(workflow: Dict[str, Any]) -> None:
    nodes = {node["id"]: node for node in workflow["nodes"]}
    if len(nodes) != len(workflow["nodes"]):
        raise ValueError("存在重复节点 ID")
    links = {link[0]: link for link in workflow["links"]}
    if len(links) != len(workflow["links"]):
        raise ValueError("存在重复连线 ID")
    for link_id, link in links.items():
        _, origin_id, origin_slot, target_id, target_slot, link_type = link
        if origin_id not in nodes or target_id not in nodes:
            raise ValueError(f"连线 {link_id} 指向不存在的节点")
        origin = nodes[origin_id]
        target = nodes[target_id]
        if origin_slot >= len(origin.get("outputs", [])) or target_slot >= len(target.get("inputs", [])):
            raise ValueError(f"连线 {link_id} 的插槽越界")
        if link_id not in (origin["outputs"][origin_slot].get("links") or []):
            raise ValueError(f"连线 {link_id} 未登记在源节点输出")
        if target["inputs"][target_slot].get("link") != link_id:
            raise ValueError(f"连线 {link_id} 未登记在目标节点输入")
        # Some pre-existing third-party nodes serialize equivalent wildcard
        # types differently.  Enforce exact types on the two redirected links
        # and every new SkinBeauty link without rewriting unrelated metadata.
        if link_id in {550, 582, 646, 647, 649, 650}:
            if origin["outputs"][origin_slot]["type"] != link_type or target["inputs"][target_slot]["type"] != link_type:
                raise ValueError(f"新增/改写连线 {link_id} 类型不一致")
    node_186 = nodes[186]
    if node_186["inputs"][3].get("link") != 647 or node_186["inputs"][4].get("link") != 650:
        raise ValueError("美白输出没有正确接入节点 186")
    if workflow["last_node_id"] < max(nodes):
        raise ValueError("last_node_id 小于最大节点 ID")
    if workflow["last_link_id"] < max(links):
        raise ValueError("last_link_id 小于最大连线 ID")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.input.open("r", encoding="utf-8") as handle:
        source = json.load(handle)
    result = inject(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"已写入 {args.output}：{len(result['nodes'])} 节点，{len(result['links'])} 连线")


if __name__ == "__main__":
    main()
