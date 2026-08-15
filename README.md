# ComfyUI-SkinBeauty-CN

[English](README_EN.md) · [更新记录](CHANGELOG.md) · [安全策略](SECURITY.md) · [问题反馈](https://github.com/chen-zhang-ai/ComfyUI-SkinBeauty-CN/issues)

人物肤色美白节点：把偏黄、偏暖的人脸与身体皮肤自然调整为冷白皮，同时尽量保护背景、服装、高光和真实皮肤纹理。

## 功能与优势

- 基础路径只使用 ComfyUI 已有的 PyTorch，`dependencies = []`，不自动安装、升级或卸载任何包。
- 自适应肤色蒙版优先处理皮肤区域，避免整张图一起变白；外部 `MASK` 是最高精度路径。
- CIELAB 明度/黄蓝/红绿联合调色，带暗部提亮、高光保护、匀肤、平滑和纹理保留。
- 原分辨率精确预览使用 ComfyUI 官方局部执行，只提交当前处理节点及 IMAGE、参数、外部 MASK 的必要祖先；下游图像/视频生成、编码和保存节点不会进入精确预览的局部执行范围。节点内用 1px 细线拖动比较前后效果。
- 正式 `IMAGE` 与第三个预览 `IMAGE` 均保持原始宽高；只有屏幕临时 PNG 会缩放。
- 支持同尺寸多图批次、逐张省显存、整批并行、CPU/GPU 和自动 OOM 回退。
- 官方 `locales/zh`、`locales/en` 与自定义 Canvas 控件均支持中英文界面。
- 可选 MediaPipe 人脸/身体皮肤语义先验；缺少包、模型或推理失败都会安全回退。

相较多个调色、蒙版和预览节点拼接，本项目把共享参数、统一蒙版、精确预览和最终输出放在两个节点内，减少依赖和工作流噪声，也避免预览算法与正式输出不一致。

## 界面与效果展示

![完整预设列表](docs/assets/presets.png)

![参数面板与节点内精确对比](docs/assets/before-after-comparison.png)

| 对比线靠右：原图占比更高 | 对比线靠左：处理结果占比更高 |
|---|---|
| ![节点内处理前观察](docs/assets/before.png) | ![节点内处理后观察](docs/assets/after.png) |

展示素材由项目所有者制作或取得公开授权；截图显示的自定义参数仅用于功能演示，实际效果会随输入、光线与蒙版而变化。两段授权视频已合成为静音并排短片，左右运动并非逐帧锁定，不用于夸大算法效果：[下载视频对比](https://github.com/chen-zhang-ai/ComfyUI-SkinBeauty-CN/releases/download/v2.2.1/skinbeauty-video-comparison.mp4)。图片和视频均已重新编码并扫描，未保留 workflow、prompt、本机路径或软件 metadata，详见 [`docs/assets/README.md`](docs/assets/README.md)。

## 节点、预设与参数

`人物肤色美白｜参数面板` 可连接多个处理节点。预设：`关闭`、`低档·自然提亮`、`中档·自然冷白`、`高档·通透冷白`、`冷白皮`、`粉润白`、`奶油白`，选择后仍可微调。

完整参数：预设、总强度、美白、冷暖、红润、匀肤、暗部提亮、高光保护、饱和度、平滑、纹理保留、肤色识别、蒙版羽化。

`人物肤色美白｜处理＋预览` 输入 `IMAGE`、共享参数和可选 `MASK`，输出美白图像、肤色蒙版、同尺寸预览图和中英双语报告。蒙版模式包括自动肤色、外部遮罩优先、仅外部遮罩和全图调色；语义模式、批处理模式与计算设备均可显式选择。

精确预览与正式处理共享同一完整分辨率结果；节点画布仅进行显示缩放，不改变下游 `IMAGE`。自动刷新采用 650ms 防抖、single-flight 和请求序列控制，快速拖动时只保留最新待执行请求并丢弃过期显示结果。任意上游生成的外部 `MASK` 会随必要祖先子图进入同一次正式处理路径；“仅外部遮罩”未连接 MASK 时会明确报错，不会回退自动肤色。

## 安装

### ComfyUI Manager / Registry

Registry 发布完成后，在 Manager 中搜索 `skin-beauty-cn` 或 `ComfyUI-SkinBeauty-CN`。若当前尚未出现，请使用下面两种方式之一，不要安装同名未知来源包。

### Git clone

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/chen-zhang-ai/ComfyUI-SkinBeauty-CN.git
```

### Release ZIP

从 [Releases](https://github.com/chen-zhang-ai/ComfyUI-SkinBeauty-CN/releases) 下载 `ComfyUI-SkinBeauty-CN_v2.2.2.zip`，解压后确认目录为：

```text
ComfyUI/custom_nodes/ComfyUI-SkinBeauty-CN/__init__.py
```

重启 ComfyUI，并在浏览器按 `Ctrl+F5`。核心功能不需要运行任何 `pip install`。

## 更新与卸载

更新时备份自定义修改，用新 Release 文件夹完整替换旧文件夹，重启 ComfyUI 并 `Ctrl+F5`；不要只覆盖 Python 而遗留旧 JS。v2.2.2 保留节点 class ID、输入键、枚举真实值和输出顺序，旧 V1/V2.2 工作流可继续加载。

卸载时关闭 ComfyUI，删除 `custom_nodes/ComfyUI-SkinBeauty-CN` 后重启。模型若已由用户主动下载，位于 `ComfyUI/models/mediapipe/selfie_multiclass_256x256.tflite`，是否保留由用户决定；插件没有卸载脚本，也不会修改共享 Python 环境。

## 最小与集成工作流

```text
LoadImage ──> 人物肤色美白｜处理＋预览 ──> PreviewImage / 下游
参数面板 ────────────────> 处理＋预览（可连接多个）
```

- [`SkinBeauty_Minimal_Pure_Algorithm.json`](workflows/SkinBeauty_Minimal_Pure_Algorithm.json)：零额外依赖，适合安装验证。
- [`SkinBeauty_Minimal_Auto_Semantic.json`](workflows/SkinBeauty_Minimal_Auto_Semantic.json)：有本地语义能力则使用，否则无网络回退。

## 放在工作流哪里？常见使用场景

本项目处理 ComfyUI `IMAGE` 张量，不是模型权重，不直接处理 `LATENT`，也不直接读取或修改 MP4 文件。

### 1. 视频生成前的参考图肤色校正

```text
参考图 / LoadImage → 人物肤色美白 → 图生视频 / 参考图视频 / 角色一致性视频节点
```

适合在耗时的视频生成前先校正人物肤色，通过精确预览确认后再运行视频，避免成片后才发现肤色不满意。本节点不压缩、缩放或重新编码参考图，正式 `IMAGE` 输出保持输入分辨率。

### 2. 图像生成模型后的最终调色

```text
图像生成模型 → VAE Decode / IMAGE → 人物肤色美白 → PreviewImage / SaveImage
```

可作为文生图、图生图、换装、修复或扩图流程的最后肤色调色步骤，在保存前统一冷暖、亮度、红润度和肤色质感。它不是生成模型，不改变模型权重或提示词；必须接在已得到 `IMAGE` 的位置，不能直接连接 `LATENT`。

### 3. 放大或细节修复后的最终肤色统一

```text
图像生成 → 放大 / Face Detailer / 细节修复 → 人物肤色美白 → SaveImage
```

如果放大或细节修复会重新绘制面部，通常在其后做最终肤色统一。如果视频模型需要已校正的参考图，也可以先处理，再由下游按模型要求缩放；本项目本身不额外压缩图片。

### 4. 多张角色参考图肤色统一

```text
多个 LoadImage → 多个人物肤色处理节点 → 共享一个参数面板 → 多参考图生成模型
```

同一参数面板可连接多个处理节点。不同尺寸图片应分别使用处理节点；同尺寸图片也可组成 `IMAGE` batch。默认逐张模式更省显存。

### 5. 外部 MASK 精确局部调色

```text
IMAGE + 人工确认的人物皮肤 MASK → 人物肤色美白 → Preview / Save / 下游模型
```

外部 `MASK` 是米色衣物、墙面或复杂背景场景的最高精度路径。只调节人物皮肤时优先使用经过检查的 MASK：“外部遮罩优先”会在有 MASK 时使用它、缺少时回到自动肤色；“仅外部遮罩”则要求必须连接 MASK，缺失时明确报错。

### 6. 视频帧批次后期调色

```text
视频解码为 IMAGE 帧批次 → 人物肤色美白 → 视频合成 / 编码节点
```

本节点不能直接读取或输出 MP4，必须由其他节点把视频解码成符合 ComfyUI batch 规则的同尺寸 `IMAGE` 帧；重新编码和压缩也由视频节点负责。逐帧颜色算法可能出现轻微时间波动，请先用短片测试再处理正式视频；本项目未实现、也不宣传专门的视频时序一致性算法。

### 7. 摄影、人像精修和非生成式调色

```text
LoadImage → 人物肤色美白 → PreviewImage / SaveImage
```

普通照片可用于黄暖肤色转自然冷白、轻度提亮和统一肤色。本项目不是换脸或磨皮重绘工具，也不用于医疗判断或治疗。

## 黄皮转冷白皮起点

先选“中档·自然冷白”。偏黄明显可把冷暖调到 45–65；只需提亮时，美白 35–55、冷暖 15–35；皮肤高光已亮时，高光保护 75–90；保留毛孔可让平滑不高于 15、纹理保留 88–96。米色衣服或墙面误选时，先降低肤色识别；正式成片建议连接经过人工检查的皮肤 `MASK`。

## 多图、性能与显存

一个 ComfyUI `IMAGE` 原生支持同尺寸批次；不同尺寸图片请分别连接处理节点并共享参数面板。默认“自动：逐张省显存”适合 3K–5K 参考图。整批并行只适用于少量同尺寸图且显存充足。自动设备遇到 CUDA OOM 时会先从整批改为逐张，再回退 CPU；显式选择 GPU 时不会悄悄改用 CPU。

## 可选 MediaPipe：请先读风险

核心人物肤色处理不需要 MediaPipe，项目仍是 `dependencies = []`。未安装包、未放置模型或语义推理失败时，节点会安全使用纯 PyTorch 肤色算法；这不是插件安装失败。MediaPipe 仅提供人脸/身体皮肤的位置先验，不需要 CUDA 或 NVIDIA 显卡，模型可在 CPU 上执行。

### 环境范围与证据等级

[Google MediaPipe Python Setup](https://developers.google.com/edge/mediapipe/solutions/setup_python) 的通用基础要求是 Python 3.9+、pip 20.3+ 和 64 位 Windows、Linux 或 macOS 桌面环境。本项目的范围更窄：只声明 Python 3.10、3.11、3.12，不声明 Python 3.9 或 3.13 支持。不要把 Google 的通用要求理解成本项目对所有组合都做过实测；只有当前 Windows 实机组合属于“实测通过”。

固定 `mediapipe==0.10.21` 的 [PyPI wheel](https://pypi.org/project/mediapipe/0.10.21/) 覆盖本项目 Python 3.10–3.12 范围内的 Windows 64 位、macOS 11+（x86_64 或对应的 universal2 wheel）和 Linux x86_64（manylinux_2_28）。这是可安装包范围，不等于每个平台都经过本项目实测；不要宣传 ARM Linux 或 Raspberry Pi 已测试支持。只有当当前 pip 低于 20.3 且用户明确决定安装 MediaPipe 时，才应自行评估是否升级 pip。

| 证据等级 | 环境或检查 | 结论 |
|---|---|---|
| 实测通过 / Verified | Windows 11 64-bit、Python 3.12.10、MediaPipe 0.10.21、RTX 5090、`selfie_multiclass_256x256.tflite` | `ImageSegmenter` 可导入、模型可加载，人脸皮肤与身体皮肤语义蒙版已通过本项目实际运行验证 |
| CI 或 Mock 测试 / CI or mocked | Python 3.10–3.12 CI、缺包/缺模型/下载/哈希/推理失败回退 | 覆盖静态、契约、打包与模拟故障；不等于所有实体系统上的 MediaPipe 推理 |
| 理论候选 / Candidate only | 0.10.13 作为项目整体 Python 3.10–3.12 的候选兼容下限 | 仅有 wheel 与所需 Tasks API 的理论依据，尚未端到端验证 |
| 未验证 / Unverified | 其他 MediaPipe、操作系统、Python 和硬件组合 | 可能可用，但本项目不作保证 |

### MediaPipe 版本说明

| MediaPipe 版本 | Python 安装包情况 | 项目验证状态 | 建议 |
|---|---|---|---|
| [0.10.5](https://pypi.org/project/mediapipe/0.10.5/) | PyPI 有 Python 3.10/3.11 的部分主流平台 wheel | 未进行本项目端到端实测 / Unverified | 仅作为较早版本参考，不建议普通用户安装 |
| [0.10.13](https://pypi.org/project/mediapipe/0.10.13/)–0.10.20 | 0.10.13 开始可找到 Python 3.12 主流平台 wheel；具体平台覆盖随版本变化 | 未进行完整模型、蒙版和 ComfyUI 集成实测 / Candidate only | 可能可用，但不能保证 |
| [0.10.21](https://pypi.org/project/mediapipe/0.10.21/) | 覆盖本项目 Python 3.10–3.12 范围 | 当前唯一端到端实测通过版本 / Verified | 正式推荐版本 |
| 高于 0.10.21 | 新版本可能有不同的包结构、依赖或 API 实现 | 未验证 / Unverified | 不建议为了本节点主动升级 |

对本项目声明的 Python 3.10–3.12 **整体范围**，0.10.13 只能称为“候选兼容下限”：它表示存在相应 wheel 且可能具备所需 Tasks API，不表示已经测试通过。Python 3.10/3.11 能安装更早版本，也不能把它们变成正式支持版本。当前运行代码不会强制检查版本必须等于 0.10.21；其他版本若能提供所需 API、加载模型并返回正确结果，可能可以使用，但仍属未验证。

`mediapipe==0.10.21` 是唯一实测推荐版本，不是 TFLite 模型规定的最低版本，模型文件本身也没有绑定该 Python 包版本。在完成 0.10.13、0.10.15、0.10.18、0.10.20、0.10.21 的真实环境矩阵测试前，不会把可选依赖改成 `mediapipe>=0.10.13,<0.10.22`，也不会宣传 0.10.13 已受支持。

### 安装风险与只读检查

**不需要语义蒙版时不要安装 MediaPipe。** `mediapipe==0.10.21` 的 PyPI 元数据要求 `numpy<2`、`protobuf>=4.25.3,<5`、`opencv-contrib-python`，还可能安装或改变 JAX、jaxlib、matplotlib、sentencepiece、sounddevice、flatbuffers 和其他间接依赖。多个 OpenCV 发行包——`opencv-python`、`opencv-python-headless`、`opencv-contrib-python`、`opencv-contrib-python-headless`——都可能提供 `cv2`，共存时可能影响其他节点。

先确认哪个 Python 真正启动 ComfyUI；不要误用系统 Python。下面命令只读检查导入和当前依赖状态，成功导入不代表模型推理已经验证。将 `<COMFYUI_PYTHON>` 替换成实际解释器：

```text
<COMFYUI_PYTHON> -c "import sys; print(sys.version)"
<COMFYUI_PYTHON> -m pip show mediapipe
<COMFYUI_PYTHON> -c "import mediapipe as mp; print(mp.__version__); print(mp.tasks.vision.ImageSegmenter)"
<COMFYUI_PYTHON> -m pip check
```

Windows Portable 在 ComfyUI 根目录可按实际目录使用：

```powershell
.\python_embeded\python.exe -c "import sys; print(sys.version)"
.\python_embeded\python.exe -m pip show mediapipe
.\python_embeded\python.exe -c "import mediapipe as mp; print(mp.__version__); print(mp.tasks.vision.ImageSegmenter)"
.\python_embeded\python.exe -m pip check
```

> **环境变更警告：以下是可选的手工安装命令，不是所有用户都应执行的一键步骤。** 先备份环境或使用可恢复的独立 ComfyUI，再审查 pip 计划中的 NumPy、protobuf、OpenCV 等变化。

```text
<COMFYUI_PYTHON> -m pip install -r custom_nodes/ComfyUI-SkinBeauty-CN/extras/requirements-mediapipe.txt
```

本插件和 Manager 都不会自动运行 pip，也不提供自动清理/修复 OpenCV、自动卸载冲突依赖或 `--no-deps` 强制安装。不要为了本节点升级一个已经可用的共享环境；若自行安装，完成后建议再次运行 `<COMFYUI_PYTHON> -m pip check`。安装失败不会阻止插件加载，语义路径会回退纯算法。

### MediaPipe 模型手动下载与放置

“安装 MediaPipe Python 包”和“下载 TFLite 模型”是两个独立条件：包安装成功不表示模型已下载，模型存在也不会安装 Python 包。仓库不分发 MediaPipe wheel 或 TFLite 模型。

- 文件名：`selfie_multiclass_256x256.tflite`
- Google 官方下载：[selfie_multiclass_256x256.tflite](https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/1/selfie_multiclass_256x256.tflite)
- 文件大小：`16,371,837 bytes`
- SHA256：`c6748b1253a99067ef71f7e26ca71096cd449baefa8f101900ea23016507e0e0`
- 最终路径：`ComfyUI/models/mediapipe/selfie_multiclass_256x256.tflite`

`mediapipe` 文件夹不存在时可手工创建；最终路径不要再多套一层同名目录。使用语义蒙版必须同时满足：

1. ComfyUI 当前 Python 能成功 `import mediapipe`；
2. 模型存在且 SHA256 正确；
3. 当前版本能成功创建 `ImageSegmenter`；
4. 推理返回 [Selfie Multiclass 模型规定的六个分类蒙版](https://developers.google.com/edge/mediapipe/solutions/vision/image_segmenter)；
5. 身体皮肤使用索引 2，面部皮肤使用索引 3。

Windows PowerShell 校验：

```powershell
Get-FileHash "ComfyUI\models\mediapipe\selfie_multiclass_256x256.tflite" -Algorithm SHA256
```

Linux（或已安装 coreutils 的 macOS）校验：

```bash
sha256sum "ComfyUI/models/mediapipe/selfie_multiclass_256x256.tflite"
```

macOS 也可使用系统命令：

```bash
shasum -a 256 "ComfyUI/models/mediapipe/selfie_multiclass_256x256.tflite"
```

默认“自动：已有模型则使用”绝不联网下载。只有用户明确选择“MediaPipe：仅允许下载模型，不安装Python包”时，才会从固定 HTTPS 地址下载模型；它不会安装 Python 包。下载器设有 60 秒超时、32 MiB 上限、`.part` 临时文件、SHA256 与加载校验和原子替换。包缺失、模型缺失、哈希错误、下载或推理失败时都会安全回退纯算法，并给出不含本机路径的报告。

放置完成后重启 ComfyUI，浏览器按 `Ctrl+F5`，节点选择“自动：已有模型则使用”，再查看“处理报告”确认实际使用了 MediaPipe 语义蒙版还是纯算法回退。模型来自 Google MediaPipe，并受提供方适用条款约束；本仓库不分发该模型，也不代表 Google 为本项目背书。

## 隐私与网络行为

基础模式、自动模式和本地模型推理全部在本机运行，无遥测、无统计上报。只有明确模型下载模式会访问 `https://storage.googleapis.com/mediapipe-models/`。v2.2.2 已移除读取文件的独立预览端点；精确预览通过 ComfyUI 正式队列传递内存张量，临时 PNG 不写入 workflow、prompt、本机路径或软件 metadata，并以原子替换避免半文件。

## 已知限制

- 纯颜色肤色判断可能误选米色墙、木材、皮革或衣物；外部皮肤 `MASK` 是最高精度路径。
- 不同光源、色彩管理和相机白平衡会改变同一参数的观感，预设是起点而非统一审美标准。
- MediaPipe 轻量模型分辨率有限，遮挡、极端姿态或远景小人物可能漏选。
- 本项目是可控的色调与质感处理，不是生成式换脸，也不会重绘五官或自动修复痘印。
- ComfyUI 的全局队列仍按顺序执行；若已有长任务运行，精确预览会等待，但插件不会并发堆积预览请求或中断其他任务。

## 兼容性与验证

| 证据等级 | 环境 | v2.2.2 状态 |
|---|---|---|
| 实测通过 / Verified | Windows 11 64-bit / Python 3.12.10 / Torch 2.9.1+cu130 / RTX 5090 | 本机核心、CPU/GPU 对照与 MediaPipe 0.10.21 实际推理通过 |
| CI 或 Mock 测试 / CI or mocked | Windows + Ubuntu / Python 3.10、3.11、3.12 | GitHub Actions 静态、JSON、工作流、安全与包结构矩阵；以公开 CI 结果为准 |
| CI 或 Mock 测试 / CI or mocked | Ubuntu / Python 3.12 / CPU Torch | GitHub Actions 算法回归；不代表 MediaPipe 实机验证 |
| CI 或 Mock 测试 / CI or mocked | 无 MediaPipe、无模型、下载/哈希/推理失败 | 契约与 mock 回退覆盖；不虚报为每种实体环境实测 |

## 故障排查

- 节点不出现：确认没有多套嵌套目录，查看启动日志，然后重启；本项目没有根 `requirements.txt` 或 `install.py`。
- 中文/英文按钮未更新：确认 ComfyUI 的 Locale 设置，再按 `Ctrl+F5` 清理旧前端缓存。
- MediaPipe 回退：查看双语处理报告；默认无模型时回退是预期行为，不代表核心节点故障。
- 精确预览连接错误：确认处理节点同时连接 `IMAGE` 和参数面板；外部遮罩模式还要确认 MASK 祖先可在当前工作流中执行。
- OOM：改为逐张、缩小同时处理的批次，或选择 CPU；不要通过随意改装 Torch 解决本节点问题。

## 技术归属、许可与参与

核心 PyTorch 调色、批处理、OOM 回退、局部执行预览编排和 Canvas 比较器为本项目独立实现或工程化组合。YCbCr、sRGB/XYZ/CIELAB、常规模糊/蒙版、语义分割和左右滑动比较都是公开通用技术概念；项目不声称发明这些方法，也未复制或运行时依赖 rgthree。详见 [`ALGORITHM_AND_ORIGINALITY.md`](docs/ALGORITHM_AND_ORIGINALITY.md)、[`ARCHITECTURE.md`](docs/ARCHITECTURE.md) 与 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

本项目采用 [MIT License](LICENSE)。安全问题请按 [SECURITY.md](SECURITY.md) 私下报告；一般问题使用 GitHub Issues，贡献流程见 [CONTRIBUTING.md](CONTRIBUTING.md)，支持边界见 [SUPPORT.md](SUPPORT.md)。版本遵循 SemVer；兼容性修复进入 patch，新功能进入 minor，破坏性协议变化只进入 major。
