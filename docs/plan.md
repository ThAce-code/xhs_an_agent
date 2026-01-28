# MVP 扩展规划

## 里程碑 1：稳定性与可维护性（1–2 天）
- [x] 配置集中管理：新增 `src/config.py`（pydantic-settings 可用时启用），统一 `model/max_results/out_dir` 等；`main.py` 增加 `--days/--lang/--region`。
- [x] 模型兜底：增加 MiniMax 兜底（从 `.env` 读取 `MINIMAX_API_KEY`，默认模型 `MiniMax-M2.1`）；支持 `--list-models` 提示 Gemini 可用模型；请求失败自动降级。
- [x] 输出规范化：System prompt 约束输出 JSON（`why_hot/structure/ideas/sources`），解析失败再 fallback 到旧的分段/正则解析。
- [x] 测试补齐：为 `src/reporting.py` 的解析与导出加 `pytest`；增加“Gemini 分段输出（list parts）”回归用例（见 `tests/test_reporting.py`）。
- [x] 日志落盘：记录检索 query/URL、模型降级等信息到 `outputs/<run_id>/run.log`。

## 里程碑 2：数据质量与可追溯（2–4 天）
- [x] 检索策略升级：主题拆分多 query（`src/retrieval.py::generate_queries`）→ 结果去重（canonical URL）→ 评分排序（相关性/可信域名/时间/原始 score）。
- [x] 缓存：Tavily 结果按 `query+days+lang+region+max_results` 缓存到 sqlite（默认 `outputs/tavily_cache.sqlite`；见 `src/cache.py` + `src/tools.py`）。
- [x] 引用绑定：输出 schema 升级为 `text + cites:[sources.id]`，并导出到 Markdown/CSV/XLSX（见 `src/prompts.py` + `src/reporting.py`）。

## 里程碑 3：产品化输出（2–3 天）
- [x] 3.1 爆款仿写（文本版）：生成 3 个中篇草稿（400–600 字）+ 标题库/钩子/标签/CTA/合规提示，条目支持 `cites:[sources.id]`（见 `src/prompts.py`、`src/agent.py`、`src/reporting.py`、`main.py`；测试：`tests/test_reporting.py`）。
- [x] 3.1 封面导演（文本版，质感拍摄向）：输出 3 套可执行封面方案 + `image_prompt`，条目支持 `cites`（见 `src/prompts.py`、`src/agent.py`、`src/reporting.py`、`main.py`）。
- [x] 3.1 导出拆分（按文件）：每次运行在 `outputs/<run_id>/` 生成 `analysis.*`、`rewrite.*`、`cover.*`，并额外落盘 `analysis.json/rewrite.json/cover.json` + `*_raw.txt` 方便排查（见 `main.py`）。
- [x] 3.2 封面出图（可选，软失败不影响主流程）：支持 MiniMax `image-01`（默认）或 Google；成功则保存 `cover.png` + `cover_prompt.txt` + `cover_image.json`，失败写入 `cover_image_error.json` 并保留 `cover.md`（见：`src/image_gen.py`；改动：`main.py`、`src/config.py`、`.env.example`；CLI：`--cover-image/--cover-image-provider/--cover-image-model/--image-aspect`）。
- [x] 3.3 账号方向雷达（赛道扫描）：新增 `--analysis-mode radar/--radar`，输出 10 个候选赛道（人群/痛点/关键词/内容栏目/变现/难度/风险/7天计划）到 `radar.md/radar.csv/radar.xlsx`（见：`src/prompts.py`、`src/agent.py`、`src/reporting.py`、`main.py`；测试：`tests/test_reporting.py`）。

## 里程碑 4：Agent 架构升级（中期）
- [ ] LangGraph 工作流：`plan -> search -> extract -> synthesize -> verify -> format`，每步可测试/可观测。
- [ ] 自检与反事实：对关键结论二次检索验证，降低幻觉。
- [ ] 回归评测：准备 20 条典型问题 + 期望格式，接入 LangSmith 或本地评测脚本。

## 建议优先级（先做什么）
1. 输出结构化（JSON）+ 解析/导出稳定（降低“乱输出”成本）
2. 检索策略 + 缓存 + 引用绑定（提升质量与可追溯）
3. LangGraph 工作流（中期演进）



