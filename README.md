# ComfyUI-SkinBeauty-CN

[English](README_EN.md) · [更新记录](CHANGELOG.md) · [安全策略](SECURITY.md) · [问题反馈](https://github.com/likun199679-bot/ComfyUI-SkinBeauty-CN/issues)

人物肤色美白节点：把偏黄、偏暖的人脸与身体皮肤自然调整为冷白皮，同时尽量保护背景、服装、高光和真实皮肤纹理。

## 功能与优势

- 基础路径只使用 ComfyUI 已有的 PyTorch，`dependencies = []`，不自动安装、升级或卸载任何包。
- 自适应肤色蒙版优先处理皮肤区域，避免整张图一起变白；外部 `MASK` 是最高精度路径。
- CIELAB 明度/黄蓝/红绿联合调色，带暗部提亮、高光保护、匀肤、平滑和纹理保留。
- 自动精确预览直接调用同一后端算法，不触发整条视频工作流；节点内用 1px 细线拖动比较前后效果。
- 正式 `IMAGE` 与第三个预览 `IMAGE` 均保持原始宽高；只有屏幕临时 PNG 会缩放。
- 支持同尺寸多图批次、逐张省显存、整批并行、CPU/GPU 和自动 OOM 回退。
- 官方 `locales/zh`、`locales/en` 与自定义 Canvas 控件均支持中英文界面。
- 可选 MediaPipe 人脸/身体皮肤语义先验；缺少包、模型或推理失败都会安全回退。

相较多个调色、蒙版和预览节点拼接，本项目把共享参数、统一蒙版、精确预览和最终输出放在两个节点内，减少依赖和工作流噪声，也避免预览算法与正式输出不一致。

## 节点、预设与参数

`人物肤色美白｜参数面板` 可连接多个处理节点。预设：`关闭`、`低档·自然提亮`、`中档·自然冷白`、`高档·通透冷白`、`冷白皮`、`粉润白`、`奶油白`，选择后仍可微调。

完整参数：预设、总强度、美白、冷暖、红润、匀肤、暗部提亮、高光保护、饱和度、平滑、纹理保留、肤色识别、蒙版羽化。

`人物肤色美白｜处理＋预览` 输入 `IMAGE`、共享参数和可选 `MASK`，输出美白图像、肤色蒙版、同尺寸预览图和中英双语报告。蒙版模式包括自动肤色、外部遮罩优先、仅外部遮罩和全图调色；语义模式、批处理模式与计算设备均可显式选择。

## 安装

### ComfyUI Manager / Registry

Registry 发布完成后，在 Manager 中搜索 `skin-beauty-cn` 或 `ComfyUI-SkinBeauty-CN`。若当前尚未出现，请使用下面两种方式之一，不要安装同名未知来源包。

### Git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/likun199679-bot/ComfyUI-SkinBeauty-CN.git
```

### Release ZIP

从 [Releases](https://github.com/likun199679-bot/ComfyUI-SkinBeauty-CN/releases) 下载 `ComfyUI-SkinBeauty-CN_v2.2.1.zip`，解压后确认目录为：

```text
ComfyUI/custom_nodes/ComfyUI-SkinBeauty-CN/__init__.py
```

重启 ComfyUI，并在浏览器按 `Ctrl+F5`。核心功能不需要运行任何 `pip install`。

## 更新与卸载

更新时备份自定义修改，用新 Release 文件夹完整替换旧文件夹，重启 ComfyUI 并 `Ctrl+F5`；不要只覆盖 Python 而遗留旧 JS。v2.2.1 保留节点 class ID、输入键、枚举真实值和输出顺序，旧 V1/V2.2 工作流可继续加载。

卸载时关闭 ComfyUI，删除 `custom_nodes/ComfyUI-SkinBeauty-CN` 后重启。模型若已由用户主动下载，位于 `ComfyUI/models/mediapipe/selfie_multiclass_256x256.tflite`，是否保留由用户决定；插件没有卸载脚本，也不会修改共享 Python 环境。

## 最小与集成工作流

```text
LoadImage ──> 人物肤色美白｜处理＋预览 ──> PreviewImage / 下游
参数面板 ────────────────> 处理＋预览（可连接多个）
```

- [`SkinBeauty_Minimal_Pure_Algorithm.json`](workflows/SkinBeauty_Minimal_Pure_Algorithm.json)：零额外依赖，适合安装验证。
- [`SkinBeauty_Minimal_Auto_Semantic.json`](workflows/SkinBeauty_Minimal_Auto_Semantic.json)：有本地语义能力则使用，否则无网络回退。
- [`MiniMax_H3_SkinBeauty_Integration.json`](workflows/MiniMax_H3_SkinBeauty_Integration.json)：保留 V2.2 的两路参考图与 bypass 状态；其第三方依赖见 [`DEPENDENCIES.md`](workflows/DEPENDENCIES.md)。

## 黄皮转冷白皮起点

先选“中档·自然冷白”。偏黄明显可把冷暖调到 45–65；只需提亮时，美白 35–55、冷暖 15–35；皮肤高光已亮时，高光保护 75–90；保留毛孔可让平滑不高于 15、纹理保留 88–96。米色衣服或墙面误选时，先降低肤色识别；正式成片建议连接经过人工检查的皮肤 `MASK`。

## 多图、性能与显存

一个 ComfyUI `IMAGE` 原生支持同尺寸批次；不同尺寸图片请分别连接处理节点并共享参数面板。默认“自动：逐张省显存”适合 3K–5K 参考图。整批并行只适用于少量同尺寸图且显存充足。自动设备遇到 CUDA OOM 时会先从整批改为逐张，再回退 CPU；显式选择 GPU 时不会悄悄改用 CPU。

## 可选 MediaPipe：请先读风险

**不需要语义分割时不要安装 MediaPipe。** ComfyUI 是共享 Python 环境，手工安装 MediaPipe 可能改变 NumPy、protobuf 等依赖，并可能由 MediaPipe 自身拉入 OpenCV 发行包，影响其他节点。本项目不会替你执行 pip，也不直接导入或依赖 `cv2`。可选清单仅放在 `extras/requirements-mediapipe.txt`，请在可恢复的独立环境中自行评估：

```bash
python -m pip install -r extras/requirements-mediapipe.txt
```

默认“自动：已有模型则使用”绝不下载；只有用户明确选择 UI 中的“MediaPipe：仅允许下载模型，不安装Python包”时，才从固定 HTTPS 主机下载固定版本模型。下载具有 60 秒超时、32 MiB 上限、`.part` 临时文件、SHA256 校验、加载校验和原子替换。它只下载模型，绝不安装 Python 包。离线时可手工把已核验模型放入 `ComfyUI/models/mediapipe/`。任何失败都会回退纯算法并给出不含本机路径的报告。

## 隐私与网络行为

基础模式、自动模式和本地模型推理全部在本机运行，无遥测、无统计上报。只有明确模型下载模式会访问 `https://storage.googleapis.com/mediapipe-models/`。精确预览端点只接受 ComfyUI `input` 目录中的上传图片，拒绝路径穿越和 output/任意文件读取。

## 已知限制

- 纯颜色肤色判断可能误选米色墙、木材、皮革或衣物；外部皮肤 `MASK` 是最高精度路径。
- 不同光源、色彩管理和相机白平衡会改变同一参数的观感，预设是起点而非统一审美标准。
- MediaPipe 轻量模型分辨率有限，遮挡、极端姿态或远景小人物可能漏选。
- 本项目是可控的色调与质感处理，不是生成式换脸，也不会重绘五官或自动修复痘印。
- 独立精确预览当前要求输入能追溯到 `LoadImage`；即使无法预览，正式节点仍可处理任意 `IMAGE`。

## 兼容性与验证

| 环境 | v2.2.1 状态 |
|---|---|
| Windows 11 / Python 3.12.10 / Torch 2.9.1+cu130 / RTX 5090 | 本机核心、CPU/GPU 对照、MediaPipe 0.10.21 实测 |
| Windows + Ubuntu / Python 3.10、3.11、3.12 | 已配置 GitHub Actions 静态、JSON、工作流、安全与包结构矩阵；以公开 CI 运行结果为准 |
| Ubuntu / Python 3.12 / CPU Torch | 已配置 GitHub Actions 算法回归；以公开 CI 运行结果为准 |
| 无 MediaPipe、无模型、下载/哈希/推理失败 | 契约与 mock 回退测试；不虚报为每种实体环境实测 |

## 故障排查

- 节点不出现：确认没有多套嵌套目录，查看启动日志，然后重启；本项目没有根 `requirements.txt` 或 `install.py`。
- 中文/英文按钮未更新：确认 ComfyUI 的 Locale 设置，再按 `Ctrl+F5` 清理旧前端缓存。
- MediaPipe 回退：查看双语处理报告；默认无模型时回退是预期行为，不代表核心节点故障。
- 精确预览无源图：确保处理节点的 `IMAGE` 能追溯到 `LoadImage`；正式队列输出不受影响。
- OOM：改为逐张、缩小同时处理的批次，或选择 CPU；不要通过随意改装 Torch 解决本节点问题。

## 技术归属、许可与参与

核心 PyTorch 调色、批处理、回退策略、安全预览端点和 Canvas 比较器为本项目独立实现或工程化组合。YCbCr、sRGB/XYZ/CIELAB、常规模糊/蒙版、语义分割和左右滑动比较都是公开通用技术概念；项目不声称发明这些方法，也未复制或运行时依赖 rgthree。详见 [`ALGORITHM_AND_ORIGINALITY.md`](docs/ALGORITHM_AND_ORIGINALITY.md)、[`ARCHITECTURE.md`](docs/ARCHITECTURE.md) 与 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

本项目采用 [MIT License](LICENSE)。安全问题请按 [SECURITY.md](SECURITY.md) 私下报告；一般问题使用 GitHub Issues，贡献流程见 [CONTRIBUTING.md](CONTRIBUTING.md)，支持边界见 [SUPPORT.md](SUPPORT.md)。版本遵循 SemVer；兼容性修复进入 patch，新功能进入 minor，破坏性协议变化只进入 major。
