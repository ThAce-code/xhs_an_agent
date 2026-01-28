# Project Specification: Xiaohongshu Traffic Analysis Agent (LangChain)

## 1. 项目概述 (Project Overview)
构建一个基于 **LangChain** 的自动化 Agent，旨在挖掘“小红书”平台的流量热点。该 Agent 不通过直接爬虫实现，而是采用 **ReAct 架构**，利用搜索引擎工具（Search Tools）获取第三方数据报告，并由 LLM 进行汇总分析，输出具备可执行性的爆款选题建议。

## 2. 技术栈 (Tech Stack)
* **Language:** Python 3.10+
* **Framework:** LangChain (v0.1+), LangChain Community
* **LLM Provider:** Google Gemini (via `langchain-google-genai`)
    * *Model:* `gemini-2.0-pro` (速度快、免费额度高、适合处理长文本)
* **Search Tool:** Tavily Search API (via `langchain-community`)
    * *Reason:* 专为 AI 优化，可直接提取网页正文内容，无需二次爬取。
* **Environment Management:** `python-dotenv`

## 3. 项目目录结构 (Directory Structure)
采用模块化设计（类似嵌入式开发的 HAL 库与应用层分离），确保高内聚低耦合。

```text
xiaohongshu_agent/
├── .env                  # 存放 API Keys (GOOGLE_API_KEY, TAVILY_API_KEY)
├── .gitignore            # 忽略 .env, __pycache__, venv
├── main.py               # [Entry Point] 程序入口，负责环境加载和启动 Agent
├── requirements.txt      # 依赖列表
└── src/
    ├── __init__.py
    ├── agent.py          # [Core Logic] 组装 LLM、Tools 和 Prompt，构建 AgentExecutor
    ├── tools.py          # [Drivers] 定义和配置搜索工具 (Tavily) 及中间件
    └── prompts.py        # [Constants] 存放 System Prompt 和 Prompt Templates

```

## 4. 模块详细规范 (Module Specifications)

### A. Configuration (`.env`)

必须包含以下环境变量：

```ini
GOOGLE_API_KEY=your_gemini_key
TAVILY_API_KEY=your_tavily_key

```

### B. Tools Layer (`src/tools.py`)

* **功能：** 初始化 `TavilySearchResults`。
* **配置：**
* `max_results=5` (每次搜索读取前5个结果)。


* **中间件 (Middleware)：**
* 应用 `.with_retry(stop_after_attempt=2)` 以防止网络波动导致的请求失败。



### C. Logic Layer (`src/prompts.py`)

* **System Prompt 核心指令：**
* 角色：小红书流量数据分析师。
* 任务：搜索第三方平台（千瓜、新榜等）的最新报告。
* 约束：严禁编造数据，必须基于 Search Tool 的返回结果。
* 输出格式：包含【热门赛道】、【爆款关键词】、【可模仿选题】、【数据来源】。



### D. Agent Layer (`src/agent.py`)

* **LLM 初始化：** 使用 `ChatGoogleGenerativeAI`，设置 `temperature=0` (保证分析客观性)。
* **Agent 类型：** 使用 `create_tool_calling_agent` (针对 Gemini 的 Function Calling 能力优化)。
* **Executor：** 使用 `AgentExecutor`，开启 `verbose=True` 以便于调试观察思考过程。

### E. Entry Point (`main.py`)

* 负责调用 `load_dotenv()`。
* 实例化 Agent。
* 提供一个测试 Query（例如：“分析本周大学生副业赛道的流量趋势”）。

## 5. 依赖包 (Requirements)

```text
langchain
langchain-community
langchain-google-genai
tavily-python
python-dotenv

```

## 6. 开发目标 (Action Items)

请根据上述规范，初始化项目文件结构，并编写核心代码。优先实现 `src/tools.py` 和 `src/agent.py` 的基础连通性。

