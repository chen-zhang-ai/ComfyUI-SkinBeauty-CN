# MiniMax 集成工作流依赖 / Integration dependencies

两个 `SkinBeauty_Minimal_*` 工作流只依赖 ComfyUI 内置节点和本项目。`MiniMax_H3_SkinBeauty_Integration.json` 还包含下列第三方节点；缺失节点并不表示本项目安装失败。

| 工作流节点来源 | 证据与说明 |
|---|---|
| ComfyUI core | `LoadImage`、`PreviewImage`、MiniMax H3 核心节点等 |
| `comfyui-easy-use` | 工作流节点元数据中的 `cnr_id` |
| `ComfyUI-MiniMaxH3_LatentUpscaler` | 元数据 `aux_id: Tr1dae/ComfyUI-MiniMaxH3_LatentUpscaler` |
| `comfyui-kjnodes` | 多个图像范围/尺寸辅助节点的 `cnr_id` |
| `comfyui-videohelpersuite` | 视频载入、合并与音频相关节点 |
| `ComfyUI-SolAttn_triton` | 元数据 `aux_id: kijai/ComfyUI-SolAttn_triton` |
| `rgthree-comfy` | 集成工作流中的 Fast Groups Bypasser；本项目自己的左右比较器不依赖 rgthree |
| `comfyui-minimax-h3-turbo` | MiniMax H3 Turbo 相关节点 |

`MarkdownNote`、`MiniMaxH3IntegerSizeController` 以及少量历史节点的元数据未提供唯一、可靠的 Registry 标识；请以 ComfyUI Manager 的“Install Missing Custom Nodes”结果和工作流作者所用环境为准。个别第三方视频节点将 `widgets_values` 保存为对象而不是数组，这是其原始序列化格式，清理时未擅自改写。

The integration graph intentionally keeps third-party widget serialization and its original reference routing. Some legacy nodes do not expose an unambiguous Registry identifier; use ComfyUI Manager's missing-node report for those items.
