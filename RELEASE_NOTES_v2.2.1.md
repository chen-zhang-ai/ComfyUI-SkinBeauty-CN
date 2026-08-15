# ComfyUI-SkinBeauty-CN v2.2.1

## 中文

面向人物参考图的自然肤色美白节点：偏黄/偏暖转冷白皮，优先保护背景、高光、纹理和正式输出分辨率。

### 本版亮点

- 开源加固：标准治理文件、安全边界、CI、可复现打包和公开安装验证流程。
- 中英文 UI、Canvas 控件、节点文档、README 和处理报告。
- 三套清理后的工作流：纯算法最小示例、自动语义最小示例、MiniMax H3 集成示例。
- 核心 `dependencies = []`，无根 requirements/install 脚本、无自动 pip、无 cv2。
- MediaPipe 模型下载改为固定 HTTPS 版本和 SHA256，带超时、大小上限、`.part`、加载校验与原子替换。
- 删除浏览器近似美白，自动/手动预览都使用同一后端真实算法。

### 安装与升级

可通过 ComfyUI Manager/Registry（发布后）、Git clone，或下载 `ComfyUI-SkinBeauty-CN_v2.2.1.zip`。升级请完整替换旧文件夹、重启 ComfyUI 并按 `Ctrl+F5`。节点 ID、Python 输入键、内部枚举值、输出顺序和 V1/V2.2 工作流保持兼容。

先尝试 `workflows/SkinBeauty_Minimal_Pure_Algorithm.json`；自动语义示例在缺少 MediaPipe 时也会回退运行。

### MediaPipe 风险提示

核心功能不需要 MediaPipe。**不需要时不要安装。** 手工安装可选包可能改变 ComfyUI 共享环境中的 NumPy/protobuf。插件从不执行 pip；明确下载模式只下载校验后的模型，不安装 Python 包。默认自动模式不下载。

### 校验

```powershell
Get-FileHash .\ComfyUI-SkinBeauty-CN_v2.2.1.zip -Algorithm SHA256
Get-Content .\SHA256SUMS.txt
```

已知限制包括米色背景/衣物误选、轻量语义模型漏选，以及精确预览源需能追溯到 `LoadImage`。请在 [Issues](https://github.com/likun199679-bot/ComfyUI-SkinBeauty-CN/issues) 报告普通问题。

## English

Natural person-skin correction for ComfyUI: shift yellow/warm skin toward a cooler white tone while protecting the background, highlights, texture, and full-resolution outputs.

### Highlights

- Open-source hardening with governance, security boundaries, CI, reproducible packaging, and public-install verification.
- English/Chinese UI, Canvas controls, node docs, READMEs, and reports.
- Three sanitized workflows: pure-algorithm minimal, auto-semantic minimal, and MiniMax H3 integration.
- Core `dependencies = []`: no root requirements/install script, runtime pip, or cv2.
- Fixed HTTPS MediaPipe model version and SHA256 with timeout, size limit, `.part`, load validation, and atomic replacement.
- Exact backend processing replaces the old approximate browser whitening preview.

### Install and upgrade

Install through ComfyUI Manager/Registry once published, Git clone, or `ComfyUI-SkinBeauty-CN_v2.2.1.zip`. Replace the old folder completely, restart ComfyUI, and press `Ctrl+F5`. Node IDs, Python keys, saved enum values, output order, and V1/V2.2 workflows remain compatible.

Start with `workflows/SkinBeauty_Minimal_Pure_Algorithm.json`. The auto-semantic example also works without MediaPipe by falling back.

### MediaPipe warning

MediaPipe is not required. **Do not install it unless needed.** Manual installation can alter NumPy/protobuf in the shared ComfyUI environment. The plugin never runs pip; explicit download mode downloads a verified model only and never installs Python packages. Default automatic mode never downloads.

### Verify

```bash
sha256sum ComfyUI-SkinBeauty-CN_v2.2.1.zip
cat SHA256SUMS.txt
```

Known limitations include beige-object false positives, lightweight semantic-model misses, and the `LoadImage` trace requirement for standalone exact preview. Report ordinary problems through [Issues](https://github.com/likun199679-bot/ComfyUI-SkinBeauty-CN/issues).
