#!/bin/bash
# 微信公众号AI写作助手 - 一键安装脚本

set -e

echo "=================================="
echo "  微信公众号AI写作助手 - 安装向导"
echo "=================================="
echo ""

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到Python3"
    echo "请先安装Python 3.8或更高版本"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ 检测到Python版本: $PYTHON_VERSION"

# 询问安装位置
echo ""
echo "请选择安装位置："
echo "  1) 当前目录"
echo "  2) ~/.local/openclaw-wechat-publisher"
echo "  3) 自定义路径"
read -p "选择 [1-3]: " choice

case $choice in
    1)
        INSTALL_DIR="./openclaw-wechat-publisher"
        ;;
    2)
        INSTALL_DIR="$HOME/.local/openclaw-wechat-publisher"
        ;;
    3)
        read -p "请输入安装路径: " INSTALL_DIR
        ;;
    *)
        echo "无效选择，使用当前目录"
        INSTALL_DIR="./openclaw-wechat-publisher"
        ;;
esac

echo ""
echo "安装位置: $INSTALL_DIR"

# 询问访问令牌
echo ""
echo "⚠️  这是一个私有仓库，需要访问令牌"
read -p "请输入Gitee访问令牌（或按Enter跳过）: " TOKEN

# 构造克隆URL
if [ -z "$TOKEN" ]; then
    CLONE_URL="https://gitee.com/woipanda/openclaw-wechat-publisher.git"
    echo "⚠️  未提供令牌，如果克隆失败请重新运行并提供令牌"
else
    CLONE_URL="https://$TOKEN@gitee.com/woipanda/openclaw-wechat-publisher.git"
fi

# 克隆仓库
echo ""
echo "正在克隆仓库..."
if [ -d "$INSTALL_DIR" ]; then
    echo "⚠️  目录已存在，跳过克隆"
    cd "$INSTALL_DIR"
else
    git clone "$CLONE_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 安装依赖
echo ""
echo "正在安装Python依赖..."
pip3 install -r requirements.txt

# 运行配置向导
echo ""
echo "✓ 安装完成！"
echo ""
read -p "是否现在运行配置向导？(Y/n): " run_setup

if [ "$run_setup" != "n" ] && [ "$run_setup" != "N" ]; then
    python3 setup.py
fi

echo ""
echo "=================================="
echo "  安装完成！"
echo "=================================="
echo ""
echo "使用方法："
echo "  cd $INSTALL_DIR"
echo "  python3 skill.py \"你的文章主题\""
echo ""
echo "重新配置："
echo "  python3 setup.py"
echo ""
