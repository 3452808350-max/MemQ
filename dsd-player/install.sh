#!/bin/bash
# DSD Player 自动安装脚本

set -e

echo "========================================"
echo "🎵 DSD Player 自动安装脚本"
echo "========================================"
echo ""

# 检查是否已安装 Rust
if command -v rustc &> /dev/null; then
    echo "✅ Rust 已安装：$(rustc --version)"
else
    echo "📦 安装 Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source $HOME/.cargo/env
    echo "✅ Rust 安装完成：$(rustc --version)"
fi

echo ""

# 检测系统
if [ -f /etc/debian_version ]; then
    echo "📦 检测到 Debian/Ubuntu 系统"
    echo "🔧 安装系统依赖..."
    sudo apt update
    sudo apt install -y \
        libgtk-4-dev \
        libadwaita-1-dev \
        libpipewire-0.3-dev \
        libtag1-dev \
        ffmpeg \
        pkg-config \
        cmake
elif [ -f /etc/fedora-release ]; then
    echo "📦 检测到 Fedora 系统"
    echo "🔧 安装系统依赖..."
    sudo dnf install -y \
        gtk4-devel \
        libadwaita-devel \
        pipewire-devel \
        taglib-devel \
        ffmpeg-devel \
        pkg-config
elif [ -f /etc/arch-release ]; then
    echo "📦 检测到 Arch Linux 系统"
    echo "🔧 安装系统依赖..."
    sudo pacman -S --noconfirm \
        gtk4 \
        libadwaita \
        pipewire \
        taglib \
        ffmpeg \
        pkg-config
else
    echo "⚠️  未检测到支持的系统，请手动安装依赖"
    echo "参考 BUILD.md 文档"
    exit 1
fi

echo ""
echo "✅ 所有依赖安装完成！"
echo ""
echo "========================================"
echo "🚀 开始编译 DSD Player"
echo "========================================"
echo ""

cd "$(dirname "$0")"

# Debug 编译
echo "🔧 编译 Debug 版本..."
cargo build

echo ""
echo "✅ Debug 编译完成！"
echo ""

# Release 编译
echo "🔧 编译 Release 版本..."
cargo build --release

echo ""
echo "✅ Release 编译完成！"
echo ""

# 显示文件信息
echo "========================================"
echo "📊 编译结果"
echo "========================================"
echo ""
ls -lh target/debug/dsd-player 2>/dev/null || true
ls -lh target/release/dsd-player 2>/dev/null || true
echo ""

# 运行测试
echo "========================================"
echo "🧪 运行测试"
echo "========================================"
echo ""
./target/release/dsd-player --version || true
echo ""

echo "========================================"
echo "🎉 安装完成！"
echo "========================================"
echo ""
echo "运行方式:"
echo "  Debug 版本：  cargo run"
echo "  Release 版本：./target/release/dsd-player"
echo "  指定目录：   ./target/release/dsd-player --music-dir ~/Music"
echo ""
