# Maintenance guardrails

- 核心安装必须保持 `dependencies = []`；禁止根目录 `requirements.txt`、`install.py`、`uninstall.py` 和运行时 pip。
- 禁止自动修改共享 Torch/CUDA/NumPy/protobuf/OpenCV/MediaPipe 环境；可选依赖只能放在 `extras/` 并由用户明确决定。
- `SkinBeautySettingsCN`、`SkinBeautyProcessorCN`、中文 Python 输入键、枚举真实值和输出顺序属于旧工作流兼容协议，不得在 patch/minor 中改名。
- 正式 `IMAGE` 输出必须保持输入分辨率；屏幕缩略图不能进入下游。
- 英文与中文 `locales`、Canvas 文本、节点文档和 README 必须同步修改。
- 模型下载必须保持固定 HTTPS 主机、固定版本、SHA256、超时、大小限制、`.part`、加载校验和原子替换；默认自动模式不得下载。
- 发布前必须运行全量测试、安全/路径/secret 扫描、JS/JSON/compile 检查、Release ZIP 冷验证和 `pip check` 前后对比。
- 不提交人物展示素材，除非已确认公开权利并清除隐私 metadata；原始视频只作为 Release 资产。
