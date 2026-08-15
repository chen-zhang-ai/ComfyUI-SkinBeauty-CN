# Security Policy / 安全策略

## Supported versions

仅最新 GitHub Release 接收安全修复；旧版本用户应先升级。

## Private reporting

请通过 [GitHub Private Vulnerability Reporting](https://github.com/likun199679-bot/ComfyUI-SkinBeauty-CN/security/advisories/new) 报告路径穿越、任意文件读取、恶意工作流、下载完整性、依赖或其他安全问题。不要在公开 Issue 中发布利用细节、个人图片、Token 或本机路径。

请提供受影响版本、最小复现、影响和建议缓解方式。维护者会确认收到、评估范围，并在修复和发布协调后公开说明；无法复现时也会如实回复。本项目不承诺赏金。

核心路径无网络行为；只有用户明确选择模型下载模式才访问代码中固定的 HTTPS 主机。项目不会执行 pip，也不会收集遥测。
