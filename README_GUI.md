# XHS Agent - 小红书流量分析助手（桌面版）

## 功能特性

### ✨ 核心功能
- **热点分析**：分析小红书流量热点，提供爆款选题建议
- **账号雷达**：推荐10个适合的账号方向和变现路径
- **爆款仿写**：生成3篇可直接发布的小红书文案
- **封面设计**：提供3套专业的封面拍摄方案

### 🎨 GUI特性
- **现代化界面**：基于CustomTkinter的简洁现代设计
- **配置管理**：图形化API密钥和参数配置
- **历史记录**：自动保存分析历史，支持搜索和查看
- **实时进度**：显示分析进度和当前步骤
- **结果预览**：多标签页展示分析、仿写、封面结果
- **一键导出**：支持JSON格式导出

## 快速开始

### 方式1：使用可执行文件（推荐）

1. 下载 `XHS_Agent.exe`
2. 双击运行
3. 首次运行时配置API密钥
4. 开始使用

### 方式2：从源码运行

```bash
# 1. 克隆仓库
git clone <repository-url>
cd xhs_an_agent

# 2. 切换到GUI分支
git checkout feature/gui-desktop-app

# 3. 安装依赖
pip install -r requirements.txt
pip install -r requirements-gui.txt

# 4. 运行应用
python gui_app.py
```

## 使用说明

### 1. 配置API密钥

首次运行时，点击右上角"设置"按钮，配置以下API密钥：

- **Google API Key**（必需）：用于Gemini模型
- **Tavily API Key**（必需）：用于搜索功能
- **MiniMax API Key**（可选）：备用模型

### 2. 开始分析

1. 在输入框中输入你的问题，例如："最近有什么美食热点"
2. 选择分析模式：
   - **热点分析**：分析具体话题的流量趋势
   - **账号雷达**：获取账号方向建议
3. 勾选需要的功能：
   - ☑ 生成仿写
   - ☑ 生成封面
   - ☐ 生成封面图片
4. 点击"开始分析"

### 3. 查看结果

分析完成后，结果会显示在下方的标签页中：
- **分析**：热点分析报告
- **仿写**：爆款文案草稿
- **封面**：封面设计方案
- **来源**：信息来源列表

### 4. 历史记录

点击"历史记录"按钮可以：
- 查看所有历史分析
- 搜索特定记录
- 重新查看历史结果
- 删除不需要的记录

## 配置说明

### API密钥获取

1. **Google Gemini API**
   - 访问：https://makersuite.google.com/app/apikey
   - 创建API密钥

2. **Tavily Search API**
   - 访问：https://tavily.com
   - 注册并获取API密钥

3. **MiniMax API**（可选）
   - 访问：https://www.minimaxi.com
   - 注册并获取API密钥

### 高级设置

在"设置"对话框中可以配置：

- **模型配置**：选择使用的模型和温度参数
- **搜索参数**：调整搜索结果数量、查询数等
- **输出设置**：配置输出目录和图片生成提供商

## 技术架构

### 核心技术栈
- **GUI框架**：CustomTkinter
- **LLM框架**：LangChain
- **主模型**：Google Gemini 2.5 Flash
- **备用模型**：MiniMax M2.1
- **搜索工具**：Tavily Search API
- **数据库**：SQLite（历史记录）
- **加密**：Cryptography（API密钥加密存储）

### 项目结构
```
xhs_an_agent/
├── gui_app.py              # GUI应用入口
├── main.py                 # CLI应用入口（原版）
├── src/
│   ├── core/               # 核心业务逻辑
│   │   ├── config_manager.py
│   │   ├── task_manager.py
│   │   └── history_manager.py
│   ├── gui/                # GUI组件
│   │   ├── main_window.py
│   │   ├── settings_dialog.py
│   │   ├── history_panel.py
│   │   └── result_viewer.py
│   └── [原有模块]
└── dist/                   # 打包输出
    └── XHS_Agent.exe
```

## 打包说明

如需自行打包，请参考 [BUILD.md](BUILD.md)

## 常见问题

### Q: 首次启动很慢？
A: 单文件版本首次启动需要解压，约需5-10秒，这是正常现象。

### Q: 防病毒软件报警？
A: PyInstaller打包的程序可能被误报，请添加信任。

### Q: API密钥安全吗？
A: API密钥使用Fernet加密存储在本地配置文件中，但仍需妥善保管配置文件。

### Q: 如何更新？
A: 下载新版本的.exe文件替换旧版本即可，配置文件会保留。

### Q: 支持Mac/Linux吗？
A: 当前主要支持Windows，Mac/Linux需要从源码运行。

## 开发计划

- [ ] 批量处理功能
- [ ] 结果Markdown渲染
- [ ] 数据可视化图表
- [ ] 模板管理功能
- [ ] 自动更新功能
- [ ] 多语言支持

## 许可证

[添加许可证信息]

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

[添加联系方式]
