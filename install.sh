#!/bin/sh
# JQS (Job Queue System) 一键安装脚本 (v2.1)

set -e

# --- 配置 ---
APP_DIR="$HOME/.jqs_app"
BIN_DIR="$HOME/.local/bin"

echo "🚀 开始安装作业调度系统 (JQS)..."

# 检查 Python 3 (POSIX 兼容方式)
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ 错误: 系统中未找到 python3。请先安装 Python 3.6+."
    exit 1
fi

# 1. 初始化 JQS 数据目录
echo "[1/5] 正在初始化 JQS 数据目录 (~/jqs)..."
python3 setup.py > /dev/null

# 2. 创建应用程序目录并复制文件
echo "[2/5] 正在将应用程序文件安装到 $APP_DIR ..."
mkdir -p "$APP_DIR"
cp -r jqs project jqs-scheduler-daemon.sh stop-jqs-scheduler.sh "$APP_DIR/"
chmod +x "$APP_DIR/jqs" "$APP_DIR/jqs-scheduler-daemon.sh" "$APP_DIR/stop-jqs-scheduler.sh"
echo "✅ 应用程序文件已成功安装."

# 3. 创建符号链接
echo "[3/5] 正在将 jqs 命令链接到 $BIN_DIR ..."
mkdir -p "$BIN_DIR"
ln -sf "$APP_DIR/jqs" "$BIN_DIR/jqs"
echo "✅ 命令链接已成功创建."

# 4. 检查 PATH 环境变量 (POSIX 兼容方式)
echo "[4/5] 正在检查 PATH 环境变量..."
case ":$PATH:" in
  *":$BIN_DIR:"*) 
    echo "✅ PATH 环境变量配置正确."
    ;;
  *)
    echo "⚠️ 注意: 您的 PATH 环境变量中未包含 $BIN_DIR。"
    echo "   请将以下命令添加到您的 shell 配置文件 (如 ~/.bashrc 或 ~/.zshrc) 中:"
    echo 
    echo "   export PATH=\"$BIN_DIR:\$PATH\""
    echo 
    echo "   添加后，请重新启动您的终端，或运行 'source ~/.bashrc' (或 ~/.zshrc) 来使更改生效。"
    ;;
esac

# 5. 启动后台调度服务
echo "[5/5] 正在启动 JQS 后台调度服务..."
cd "$APP_DIR"
./jqs-scheduler-daemon.sh

echo
echo "🎉 恭喜！JQS 安装和配置已全部完成！"
echo
echo "您现在可以随时随地使用 'jqs' 命令了 (可能需要重启终端才能找到命令)。"
echo "- 查看作业状态: jqs q"
echo "- 提交一个作业: jqs submit <您的脚本>"
