# XHS Agent Desktop Application - Build Instructions

## 环境准备

### 1. 安装依赖

```bash
# 安装核心依赖
pip install -r requirements.txt

# 安装GUI依赖
pip install -r requirements-gui.txt

# 安装打包依赖
pip install -r requirements-build.txt
```

### 2. 配置API密钥

首次运行时，应用会提示配置API密钥。你也可以手动创建配置文件：

配置文件位置：`~/.xhs_agent/config.json`

## 开发模式运行

```bash
python gui_app.py
```

## 打包为可执行文件

### 方法1：使用打包脚本（推荐）

```bash
python build_exe.py
```

### 方法2：直接使用PyInstaller

```bash
pyinstaller --onefile --windowed --name=XHS_Agent gui_app.py
```

## 打包输出

打包完成后，可执行文件位于：
- Windows: `dist/XHS_Agent.exe`
- 文件大小：约200-250MB（单文件版本）

## 分发

将 `dist/XHS_Agent.exe` 文件分发给用户即可，无需Python环境。

## 注意事项

1. **首次启动较慢**：单文件版本首次启动需要解压，可能需要5-10秒
2. **防病毒软件**：某些防病毒软件可能误报，需要添加信任
3. **API密钥安全**：配置文件使用加密存储，但仍需妥善保管
4. **系统要求**：Windows 10/11，64位系统

## 故障排除

### 打包失败

1. 确保所有依赖已安装
2. 清理缓存：删除 `build/` 和 `dist/` 目录后重试
3. 检查Python版本：建议使用Python 3.10+

### 运行时错误

1. 检查API密钥配置是否正确
2. 查看日志文件：`~/.xhs_agent/` 目录下
3. 确保网络连接正常

## 开发分支

当前在 `feature/gui-desktop-app` 分支开发。

合并到main分支：
```bash
git checkout main
git merge feature/gui-desktop-app
```
