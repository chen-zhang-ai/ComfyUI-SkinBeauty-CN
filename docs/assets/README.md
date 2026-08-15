# Media provenance and sanitization / 素材来源与清理

项目所有者于 2026-08-15 确认：本目录 4 张展示图和用于生成 Release 视频的 2 段源视频均由其制作、生成，或已取得公开发布权，并授权用于本项目。

- `presets.png`：完整预设列表。
- `before.png`：对比线靠右时的节点截图，原图占比更高。
- `after.png`：对比线靠左时的节点截图，处理结果占比更高。
- `before-after-comparison.png`：参数面板与节点内左右比较器。
- Release 资产 `skinbeauty-video-comparison.mp4`：两段授权源视频各取前三秒，等比例缩放后静音并排编码；左右运动并非逐帧锁定。

4 张 PNG 均重新解码为 RGB 并写为新 PNG；检查结果为无 EXIF、无文本块、无源 DPI/软件信息。Release 视频重新编码为 H.264/YUV420p、1080×968、24 fps、3 秒、无音频；容器只保留 MP4 所需的结构性 brand/language/handler/vendor 字段。扫描确认不存在 `workflow`、`prompt`、绝对路径、API key、Token、Cookie、encoder 或 creation time 标签。

The owner confirmed publication rights on 2026-08-15. Every PNG was decoded to RGB and written as a new metadata-free file. The silent three-second H.264 comparison is derived from the two authorized clips; its motion is not frame-locked. Post-encoding inspection found no workflow, prompt, absolute path, secret, encoder, or creation-time metadata.
