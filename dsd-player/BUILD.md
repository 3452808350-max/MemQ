# DSD Player 编译指南

> **创建时间**: 2026-03-06  
> **状态**: ⚠️ 需要安装依赖

---

## 📦 系统依赖

### Debian/Ubuntu

```bash
# 安装 Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 安装系统依赖
sudo apt update
sudo apt install -y \
    libgtk-4-dev \
    libadwaita-1-dev \
    libpipewire-0.3-dev \
    libtag1-dev \
    ffmpeg \
    pkg-config \
    cmake
```

### Fedora

```bash
# 安装 Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 安装系统依赖
sudo dnf install \
    gtk4-devel \
    libadwaita-devel \
    pipewire-devel \
    taglib-devel \
    ffmpeg-devel \
    pkg-config
```

### Arch Linux

```bash
# 安装 Rust
sudo pacman -S rust cargo

# 安装系统依赖
sudo pacman -S \
    gtk4 \
    libadwaita \
    pipewire \
    taglib \
    ffmpeg \
    pkg-config
```

---

## 🚀 编译步骤

### 1. 进入项目目录

```bash
cd /home/kyj/.openclaw/workspace/dsd-player
```

### 2. 编译 Debug 版本

```bash
cargo build
```

### 3. 编译 Release 版本

```bash
cargo build --release
```

### 4. 运行程序

```bash
# Debug 版本
cargo run

# Release 版本
./target/release/dsd-player
```

### 5. 指定音乐目录

```bash
./target/release/dsd-player --music-dir ~/Music/DSD
```

---

## 🧪 测试

### 运行测试

```bash
cargo test
```

### 检查代码

```bash
cargo check
```

### 格式化代码

```bash
cargo fmt
```

### 代码审查

```bash
cargo clippy
```

---

## ⚠️ 常见问题

### 问题 1: 找不到 GTK4

**错误**:
```
error: failed to run custom build command for `gtk4-sys`
```

**解决**:
```bash
# Debian/Ubuntu
sudo apt install libgtk-4-dev

# Fedora
sudo dnf install gtk4-devel

# Arch
sudo pacman -S gtk4
```

---

### 问题 2: 找不到 PipeWire

**错误**:
```
error: failed to run custom build command for `pipewire`
```

**解决**:
```bash
# Debian/Ubuntu
sudo apt install libpipewire-0.3-dev

# Fedora
sudo dnf install pipewire-devel

# Arch
sudo pacman -S pipewire
```

---

### 问题 3: Rust 版本过旧

**错误**:
```
error[E0658]: this is not valid Rust
```

**解决**:
```bash
rustup update stable
rustup default stable
```

---

### 问题 4: 编译时间过长

**解决**:
```bash
# 使用更多并行编译
export CARGO_BUILD_JOBS=8

# 或者使用更快的链接器
sudo apt install lld
echo '[target.x86_64-unknown-linux-gnu]' >> ~/.cargo/config.toml
echo 'linker = "lld"' >> ~/.cargo/config.toml
```

---

## 📊 编译时间预估

| 系统 | CPU | 内存 | Debug | Release |
|------|-----|------|-------|---------|
| **i5-8 代** | 4 核 | 16GB | ~5 分钟 | ~15 分钟 |
| **i7-10 代** | 8 核 | 32GB | ~3 分钟 | ~10 分钟 |
| **Ryzen 7** | 8 核 | 32GB | ~2 分钟 | ~8 分钟 |

---

## 🎯 下一步

编译成功后：

1. **运行程序**
   ```bash
   cargo run
   ```

2. **测试功能**
   - GTK4 界面显示
   - PipeWire 音频播放
   - 配置文件加载

3. **继续开发**
   - Phase 2: 音乐库
   - Phase 3: 播放功能
   - Phase 4: 优化

---

## 📝 当前状态

| 组件 | 状态 | 说明 |
|------|------|------|
| **Rust** | ❌ 未安装 | 需要安装 |
| **GTK4** | ❌ 未安装 | 需要安装 |
| **libadwaita** | ❌ 未安装 | 需要安装 |
| **PipeWire** | ❌ 未安装 | 需要安装 |
| **项目代码** | ✅ 完成 | 等待编译 |

---

*指南版本：1.0*  
*最后更新：2026-03-06*  
*状态：⚠️ 等待安装依赖*
