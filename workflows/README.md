# 示例工作流 / Example workflows

- `SkinBeauty_Minimal_Pure_Algorithm.json`：只使用 ComfyUI 内置节点和本项目节点；无需 MediaPipe 或模型，适合首次安装验证。
- `SkinBeauty_Minimal_Auto_Semantic.json`：默认“自动：已有模型则使用”；没有 MediaPipe 或模型时安全回退到纯 PyTorch 肤色蒙版，且不会联网下载。
- `MiniMax_H3_SkinBeauty_Integration.json`：从 V2.2 原工作流清理而来，保留节点 272/273/274/186 的接线和原 bypass 状态。它依赖多个第三方节点包，详见 `DEPENDENCIES.md`。

打开工作流后，在 `LoadImage` 中选择自己的图片。正式 `IMAGE` 输出始终保持原始宽高；节点内对比图只是显示用途。

The two minimal workflows need only ComfyUI built-ins and this project. The MiniMax integration workflow preserves the V2.2 reference-image wiring but requires the third-party packs listed in `DEPENDENCIES.md`.

