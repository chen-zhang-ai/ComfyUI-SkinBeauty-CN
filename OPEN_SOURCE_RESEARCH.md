# 开源方案核查（2026-08-14）

## 结论

在本次核查到的主流公开仓库中，没有发现一个现成 ComfyUI 节点能同时满足：全身＋面部皮肤识别、黄皮转冷白皮、低/中/高预设、细分滑杆、同尺寸多图批次、不排队视频即可实时预览、低依赖。现有方案各自只覆盖其中一部分，因此本节点包采用独立核心，并把 MediaPipe 作为可选增强，而不是强制安装多个大型节点包。

## 可直接使用的 ComfyUI 项目

| 项目 | 可用节点/能力 | 优点 | 与本需求的差距 |
|---|---|---|---|
| [ComfyUI LayerStyle](https://github.com/chflame163/ComfyUI_LayerStyle) / [Advance](https://github.com/chflame163/ComfyUI_LayerStyle_Advance) | `PersonMaskUltraV2`、`ColorTemperature`、`LAB`、`BrightnessContrastV2`、`Sharp & Soft` | 人物皮肤蒙版和传统调色很全，社区规模大，可拼出冷白皮流程 | 需要多个节点；Advance 依赖较多；VITMatte 在 2K 以上显存开销大；没有一体化美白预设与本需求的预览面板 |
| [a-person-mask-generator](https://github.com/djbielejeski/a-person-mask-generator) | 面部皮肤、身体皮肤、头发、服装等 MediaPipe 蒙版 | MIT、轻量、直接支持 ComfyUI，是很实用的皮肤区域来源 | 只生成蒙版，不负责美白、修肤或冷暖；需安装 MediaPipe |
| [ComfyUI-JH-PixelPro](https://github.com/jetthuangai/ComfyUI-JH-PixelPro) | Edge-Aware Skin Smoother、ColorLab、Skin Tone Tri-Region、Face Beauty Blend | GPU 张量处理、测试和专业修肤思路完整，是现成项目里最接近专业人像后期的一套 | 项目较新；需要 Kornia、MediaPipe、OpenCV、SciPy；要组合多节点，仍不是“全身皮肤冷白一键节点” |
| [ComfyUI-Portrait-Maker](https://github.com/THtianhao/ComfyUI-Portrait-Maker) | FaceSkin、Skin Retouching、Portrait Enhancement、Makeup Transfer | 有直接的皮肤修饰和人像增强模型 | 首次启动下载多模型且文档注明无哈希校验；主要聚焦脸部；Windows 依赖仍有已知问题；不适合追求少依赖的稳定前置节点 |
| [ComfyUI-Curve](https://github.com/aiaiaikkk/ComfyUI-Curve) | HSL、曲线、色阶、Color Grading、前端实时弹窗 | 实时交互界面优秀，支持遮罩与红/橙肤色通道，适合手工调色 | 没有自动皮肤语义识别，也没有面向“冷白皮”的一体化参数模型 |
| [ComfyUI_PortraitTools](https://github.com/billwuhao/ComfyUI_PortraitTools) | Photo Enhancement：亮度、饱和度、锐化、磨皮 | 上手简单，依赖列表不长 | 更像基础增强；没有明确的全身皮肤蒙版和冷白肤色控制；人脸检测还需要模型 |

## 适合继续改造成节点的底层项目

| 项目 | 适合程度 | 建议 |
|---|---|---|
| [Google MediaPipe Image Segmenter](https://ai.google.dev/edge/mediapipe/solutions/vision/image_segmenter) | 高 | SelfieMulticlass 直接给出 body-skin 与 face-skin，256×256 模型轻量，最适合做自动皮肤位置先验。本插件已做成可选适配器。 |
| [yakhyo/face-parsing](https://github.com/yakhyo/face-parsing) | 高（脸部） | MIT，提供 43MB ResNet18 的 PT/ONNX 权重，适合未来增加眼、唇、眉、脸皮肤精细排除；但不覆盖全身裸露皮肤。 |
| [zllrunning/face-parsing.PyTorch](https://github.com/zllrunning/face-parsing.PyTorch) | 中高（脸部） | 社区使用广、MIT，可用于高精度脸部解析；代码较老，接入前应封装权重下载、设备和批次逻辑。 |
| [pixpark/GPUPixel](https://github.com/pixpark/gpupixel) | 中（独立实时引擎） | Apache-2.0，C++/OpenGL 实时美白、磨皮与人脸特效思路成熟；若做独立桌面美颜很合适，但给 ComfyUI Python 节点增加本地编译和 OpenGL 上下文，维护成本过高。 |
| [RetouchFormer](https://github.com/Davidcoach/RetouchFormer_AAAI_24) | 中低 | 对痘印/瑕疵修复有研究价值，但权重来自网盘、环境偏旧，仓库未明确显示许可证，而且目标不是肤色冷白；不适合直接打包进低依赖节点。 |
| [axidex/face-retouching](https://github.com/axidex/face-retouching) | 低 | 包含动态平滑、羽化、纹理恢复等完整思路，但为 GPL C++/OpenCV/dlib/子模块构建，社区采用很少；适合研究，不适合直接嵌入本插件。 |

## 本插件实际采用的取舍

1. **基础路径零额外依赖**：使用 ComfyUI 已有的 PyTorch，实现 YCbCr 自适应肤色概率、CIELAB 提亮/去黄加蓝、局部匀肤、高光保护和纹理保留。
2. **语义模型可选**：环境已有 MediaPipe 与模型时，融合 face-skin/body-skin；任何导入或推理失败都会回退，不影响工作流运行。
3. **外部 MASK 是最高精度路径**：可接 LayerStyle、a-person-mask-generator、BiSeNet 或手工蒙版。
4. **统一精确预览**：浏览器不再做可能误导的近似全图美白；自动防抖和手动刷新都通过独立安全路由调用后端真实算法，不会触发节点 186 和整条视频队列。
5. **不同尺寸分路，同尺寸可批次**：符合 ComfyUI `IMAGE` 的批次语义，也避免 3K–5K 多图并行时不必要的显存峰值。

## V2.2 左右对比界面参考

| 项目 | 许可/状态 | 采用方式 |
|---|---|---|
| [ComfyUI 官方 ImageCompare](https://docs.comfy.org/built-in-nodes/ImageCompare) | ComfyUI 官方功能 | 参考“同一画布叠放两图＋可拖动分隔线”的交互模型；未复制官方源码。 |
| [rgthree-comfy Image Comparer](https://github.com/rgthree/rgthree-comfy) | MIT | 参考其成熟的节点内对比体验；未引入 rgthree 包、依赖或运行时。 |

V2.2 比较器由本项目用原生 Canvas 独立实现，不增加 npm/Python 包。它像rgthree一样在节点级 `onMouseMove` 追踪悬停位置，采用“占用节点剩余高度＋1px细分隔线”结构，去除文字标签和大圆形手柄；原图与结果只在画布内按比例显示，传给节点186的 `IMAGE` 张量和第三个 `IMAGE` 输出均保持原始宽高。
