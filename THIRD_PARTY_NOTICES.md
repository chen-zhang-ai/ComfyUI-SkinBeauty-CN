# Third-party notices / 第三方声明

本仓库的运行时 Python 依赖列表为空；ComfyUI 提供的 PyTorch 和宿主 API 不随本项目分发。

## Optional MediaPipe integration

项目可调用用户环境中已有的 [Google MediaPipe](https://github.com/google-ai-edge/mediapipe) Image Segmenter，并可在用户明确选择时下载公开的 Selfie Multiclass 模型。MediaPipe 项目使用 Apache-2.0；模型仍受提供方适用条款约束。本仓库不包含 MediaPipe 代码、wheel 或模型，也不代表 Google 背书。

## Design references, not runtime dependencies

- [ComfyUI ImageCompare](https://docs.comfy.org/built-in-nodes/ImageCompare)：参考同画布前后比较的通用交互。
- [rgthree-comfy Image Comparer](https://github.com/rgthree/rgthree-comfy)（MIT）：参考成熟的节点内比较体验。

本项目 Canvas 比较器为独立实现，没有复制上述实现，也没有 npm/Python 运行时依赖。MiniMax 集成示例本身包含一个 `rgthree-comfy` 的 Fast Groups Bypasser 节点；这属于示例工作流的第三方依赖，不是本项目比较器的依赖。

## Public technical foundations

肤色概率、sRGB/XYZ/CIELAB 转换、局部平均、遮罩羽化、颜色混合、语义分割和滑动比较属于公开的标准或常规图像处理技术。具体工程组合、参数模型、安全边界、测试和 UI 实现见 `docs/ALGORITHM_AND_ORIGINALITY.md`。

第三方 MiniMax 集成工作流的节点包归属见 `workflows/DEPENDENCIES.md`。用户必须分别遵守相应项目的许可证和模型/服务条款。
