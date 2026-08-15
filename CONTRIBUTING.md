# Contributing / 参与贡献

感谢改进项目。一般缺陷或建议请先搜索并提交 GitHub Issue；安全问题不要公开，按 `SECURITY.md` 处理。

1. 从 `main` 创建短生命周期分支，保持改动聚焦。
2. 不新增强制运行依赖，不添加自动 pip/install 脚本，不改动旧节点键值或正式输出尺寸。
3. 修改 UI 时同步 `locales/en`、`locales/zh`、节点文档和前端自定义文本。
4. 运行 `python -m unittest discover -s tests -v`、`python -m compileall`、JS/JSON 检查和 `python tools/build_release.py --verify-only`。
5. PR 说明行为变化、兼容性、测试环境、网络/依赖影响和第三方来源。提交信息建议使用 Conventional Commits。

By contributing, you agree that your contribution is released under this repository's MIT License and that you have the right to submit it. Do not add personal data, secrets, copyrighted media without permission, generated claims, or copied third-party source without compatible licensing and clear attribution.
