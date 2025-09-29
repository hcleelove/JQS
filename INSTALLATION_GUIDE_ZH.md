# 作业调度系统 (JQS) 安装指南

## 概述
这是一个轻量级的个人作业调度系统，使用基于文件的状态管理和 systemd 来执行带有资源限制的作业。

## 系统要求
- Linux 系统 (支持 systemd)
- Python 3.6+
- systemd-run 命令 (systemd 的一部分)
- 至少 1GB 可用磁盘空间用于作业存储

## 安装步骤

### 1. 复制项目文件
将以下文件复制到目标计算机：
- jqs (主程序)
- project/ 目录 (包含所有 Python 模块)
- setup.py (初始化脚本)

### 2. 初始化系统
运行设置脚本来初始化数据目录：

```bash
python3 setup.py
```

这将创建：
- `~/jqs/` 目录，包含子目录：`queue/`, `running/`, `finished/`, `locks/`
- 配置文件：`limits.json`, `usage.json`, `jobid_counter`

### 3. 使主程序可执行
```bash
chmod +x jobs
```

### 4. 安装到系统路径（可选）
要从任何地方使用 `jobs` 命令，请将其复制到 PATH 中的目录：

```bash
# 复制到 PATH 中的 bin 目录
cp jobs ~/bin/          # 如果 ~/bin 在您的 PATH 中
# 或者
sudo cp jobs /usr/local/bin/
```

## 配置

系统使用 `~/jqs/` 中的以下配置文件：

- `limits.json`：系统资源限制（默认：16 核心，64GB 内存）
- `usage.json`：当前资源使用情况（由系统自动管理）
- `jobid_counter`：自动递增的作业 ID 计数器

您可以编辑 `limits.json` 以反映您系统的实际资源：

```json
{
  "cores_total": 8,
  "mem_mb_total": 16384
}
```

## 启动调度器服务

### 方法 1：使用提供的脚本启动后台服务
```bash
# 启动调度器后台服务
./jqs-scheduler-daemon.sh

# 停止调度器服务
./stop-jqs-scheduler.sh
```

### 方法 2：使用 systemd 设置为系统服务（推荐）
创建 `/etc/systemd/system/jqs-scheduler.service` 文件：

```bash
sudo tee /etc/systemd/system/jqs-scheduler.service > /dev/null <<EOF
[Unit]
Description=Job Queue System Scheduler
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=/home/$(whoami)/qwen/subjobs
ExecStart=/usr/bin/python3 /home/$(whoami)/qwen/subjobs/jobs scheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

启用并启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable jqs-scheduler.service
sudo systemctl start jqs-scheduler.service
```

## 使用方法

在使用系统之前，确保调度器正在运行。您可以：
- 运行 `python3 jobs scheduler` 使调度器持续运行
- 或使用以上方法设置为系统服务

### 提交作业
创建一个包含 #JS 指令的脚本文件并提交：

```bash
# 示例：test_job.sh
#!/bin/bash
#JS name="my_test_job" cores=2 mem_mb=2048 stdout="output.log" stderr="error.log"

echo "Starting my test job..."
sleep 10
echo "Job completed!"
```

提交作业：
```bash
python3 jobs submit test_job.sh
```

### 作业脚本指令
您可以在脚本头部使用 #JS 指令指定作业需求：
- `name="job_name"`：作业名称
- `cores=2`：所需 CPU 核心数
- `mem_mb=2048`：所需内存（MB）
- `stdout="output.log"`：stdout 文件路径
- `stderr="error.log"`：stderr 文件路径
- `workdir="/path/to/workdir"`：工作目录
- `time_limit="01:00:00"`：时间限制（HH:MM:SS 格式）

### 查看作业状态
列出所有作业：
```bash
python3 jobs q
```

查看详细的作业信息：
```bash
python3 jobs info <jobid>
```

### 取消作业
取消待处理或正在运行的作业：
```bash
python3 jobs cancel <jobid>
```

### 系统资源
查看系统资源使用情况：
```bash
python3 jobs nodes
```

## 故障排除

- 确保 systemd-run 在您的系统上可用
- 检查 `~/jqs/` 目录结构是否存在
- 确保您的脚本具有执行权限
- 验证资源需求不超过系统限制
- 确保调度器正在运行以处理提交的作业

## 目录结构说明

- `~/jqs/queue/`：等待调度的作业
- `~/jqs/running/`：当前正在运行的作业
- `~/jqs/finished/`：已完成/已取消的作业
- `~/jqs/locks/`：用于并发控制的锁文件

## 许可证
MIT 许可证