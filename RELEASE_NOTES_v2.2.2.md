# ComfyUI-SkinBeauty-CN v2.2.2

## 中文

### P0 修复

- 精确预览不再读取 `LoadImage` 文件或先缩到 1600px 处理。
- 预览使用 ComfyUI 官方局部执行，运行处理节点和 IMAGE、参数、任意外部 MASK 的必要祖先；节点 186、视频生成、编码和保存下游不会进入预览 prompt。
- 正式处理与精确预览共用 `run_skin_beauty`：输入张量、原始分辨率、外部/语义蒙版、参数、批处理、设备选择、OOM 回退与结果张量同源。
- 完整分辨率结果生成后，内部终点才把第一张图缩放为最长边不超过 1600 的无 metadata 临时 PNG。三个正式 IMAGE 输出的批次、宽高、Alpha 与额外通道不变。
- 自动预览采用 650ms 防抖、single-flight、最新请求替换与过期结果丢弃。

### 安全与发布链

- 已移除独立文件读取预览路由；临时 PNG 使用原子替换，失败不会留下半文件或覆盖已知正常结果。
- GitHub Actions 固定到执行时核验的完整 commit SHA；GitHub Release 与 Registry 发布均必须先通过同一个完整 Quality Gate。
- 仓库已迁移到 `chen-zhang-ai` 组织；v2.2.1 的公开提交、Tag、Release 和资产未改写。
- 核心仍为 `dependencies = []`，没有根 `requirements.txt`、安装脚本或自动 pip。MediaPipe 始终可选，显式模式也只下载经 SHA256 验证的模型。

### 安装与升级

可下载 `ComfyUI-SkinBeauty-CN_v2.2.2.zip` 或执行：

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/chen-zhang-ai/ComfyUI-SkinBeauty-CN.git
```

升级时请完整替换旧插件目录、重启 ComfyUI，并在浏览器按 `Ctrl+F5`。节点 class ID、Python 输入键、内部枚举值、输出顺序和 V1/V2.2 工作流保持兼容。

Registry/Manager 条目只会在真实 PublisherId、发布密钥和公共冷安装验证完成后公布；在此之前不要安装同名未知来源包。

### 校验

```powershell
Get-FileHash .\ComfyUI-SkinBeauty-CN_v2.2.2.zip -Algorithm SHA256
```

与 `SHA256SUMS.txt` 对照。普通问题请提交到 [Issues](https://github.com/chen-zhang-ai/ComfyUI-SkinBeauty-CN/issues)；安全问题请按 [SECURITY.md](SECURITY.md) 私下报告。

## English

### P0 fix

- Exact preview no longer reads a `LoadImage` file or processes a source pre-scaled to 1600 px.
- It uses ComfyUI's official partial execution and runs only the processor plus required IMAGE, settings, and arbitrary external-MASK ancestors. Node 186 and downstream video generation, encoding, and save nodes are absent from the preview prompt.
- Formal execution and exact preview share `run_skin_beauty`, including the input tensor, source resolution, external/semantic mask, settings, batch mode, device selection, OOM fallback, and result tensor.
- Only after the full-resolution result exists does the internal sink encode the first batch item as a metadata-free display PNG capped at 1600 px. All three formal IMAGE outputs preserve batch, dimensions, alpha, and extra channels.
- Automatic preview uses a 650 ms debounce, single-flight execution, latest-request replacement, and stale-result rejection.

### Security and release chain

- The standalone file-reading preview route is removed. Temporary PNGs use atomic replacement so failures leave no partial file and do not overwrite a known-good result.
- Every GitHub Action is pinned to a verified full commit SHA. GitHub Release and Registry publishing both depend on the same complete Quality Gate.
- The repository moved to the `chen-zhang-ai` organization without rewriting the public v2.2.1 commits, tag, release, or assets.
- The core remains `dependencies = []`, with no root requirements file, installer, or automatic pip. MediaPipe stays optional; its explicit mode downloads only a SHA256-verified model.

### Install and upgrade

Download `ComfyUI-SkinBeauty-CN_v2.2.2.zip` or run:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/chen-zhang-ai/ComfyUI-SkinBeauty-CN.git
```

For upgrades, replace the complete plug-in folder, restart ComfyUI, and press `Ctrl+F5`. Node class IDs, Python input keys, stored enum values, output order, and V1/V2.2 workflows remain compatible.

The Registry/Manager entry will be announced only after a real PublisherId, secure publishing key, and public cold-install verification are complete. Until then, do not install an unrelated similarly named package.

### Verify

```bash
sha256sum ComfyUI-SkinBeauty-CN_v2.2.2.zip
```

Compare it with `SHA256SUMS.txt`. Use [Issues](https://github.com/chen-zhang-ai/ComfyUI-SkinBeauty-CN/issues) for ordinary problems and [SECURITY.md](SECURITY.md) for private vulnerability reports.
