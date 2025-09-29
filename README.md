# JQS (Job Queue System) 安装包

这是一个轻量级的个人作业调度系统。此安装包旨在提供一个简单、无缝的“一键式”安装体验。

## 核心特性

- **命令无冲突**: 使用 `jqs` 作为主命令，避免与系统内置 `jobs` 命令冲突。
- **无 Root 安装**: 所有文件和配置均安装在用户主目录下，无需 `sudo` 权限。
- **一键式脚本**: 只需运行一个脚本即可完成所有安装、配置和后台服务启动。
- **自动环境检测**: 自动检测 `PATH` 环境变量，并为用户提供清晰的配置指引。

## 安装步骤

打开终端，进入 `installation_package` 目录，然后只需运行以下两个命令：

```bash
# 1. 赋予安装脚本执行权限
chmod +x install.sh

# 2. 运行一键式安装脚本
./install.sh
```

脚本会自动完成所有设置。安装成功后，您就可以在任何地方使用 `jqs` 命令了。

## 使用方法

- **查看作业队列**: `jqs q`
- **提交作业**: `jqs submit <your_script.sh>`
- **查看特定作业信息**: `jqs info <job_id>`
- **取消作业**: `jqs cancel <job_id>`
- **查看节点资源**: `jqs nodes`

## 包含的文件

- `install.sh` - **（新）** 一键式安装脚本
- `jqs` - **（新）** 主程序入口点 (原为 `jobs`)
- `setup.py` - 系统初始化脚本
- `project/` - 核心 Python 模块
- `jqs-scheduler-daemon.sh` - 启动调度器后台服务的脚本
- `stop-jqs-scheduler.sh` - 停止调度器服务的脚本
- `INSTALLATION_GUIDE_ZH.md` - 详细的中文技术和使用指南
- `test_job.sh` - 用于测试的示例作业脚本

## 系统配置

安装后，您可以根据系统资源编辑 `~/jqs/limits.json` 文件来调整可用的 CPU 核心数和内存大小。

```json
{
  "cores_total": 8,      // CPU 核心总数
  "mem_mb_total": 16384  // 内存总量 (MB)
}
```
