#!/bin/bash

# active.sh - 激活虚拟环境（正确的版本）

# 设置变量 - 虚拟环境实际在 .venv 目录中
VENV_DIR=".venv"
SCRIPT_DIR="$(pwd)"
VENV_PATH="$SCRIPT_DIR/kk_processor/$VENV_DIR"

echo "🔍 检查虚拟环境..."
echo "当前目录: $SCRIPT_DIR"
echo "虚拟环境路径: $VENV_PATH"

# 检查虚拟环境目录是否存在
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ 错误: 虚拟环境目录不存在: $VENV_PATH"
    echo "📁 kk_processor 目录内容:"
    ls -la kk_processor/
    exit 1
fi

# 显示虚拟环境结构
echo "📂 虚拟环境目录结构:"
ls -la "$VENV_PATH/" | head -10

# 检查激活脚本
if [ -f "$VENV_PATH/bin/activate" ]; then
    echo "✅ 找到激活脚本: $VENV_PATH/bin/activate"
    source "$VENV_PATH/bin/activate"
    echo "🎉 虚拟环境已激活: $VENV_DIR"
elif [ -f "$VENV_PATH/Scripts/activate" ]; then
    echo "✅ 找到激活脚本: $VENV_PATH/Scripts/activate"
    source "$VENV_PATH/Scripts/activate"
    echo "🎉 虚拟环境已激活: $VENV_DIR"
else
    echo "❌ 错误: 找不到激活脚本"
    echo "📂 虚拟环境目录内容:"
    ls -la "$VENV_PATH"
    exit 1
fi

# 验证激活
if [ -n "$VIRTUAL_ENV" ]; then
    echo ""
    echo "✅ 虚拟环境激活成功!"
    echo "📁 虚拟环境路径: $VIRTUAL_ENV"
    echo "🐍 Python 路径: $(which python)"
    echo "🔢 Python 版本: $(python --version 2>&1)"
    
    # 检查当前目录（应该在 kk_processor 中）
    echo "📂 工作目录: $(pwd)"
else
    echo "❌ 虚拟环境激活失败"
fi