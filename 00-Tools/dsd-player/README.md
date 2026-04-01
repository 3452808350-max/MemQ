# DSD Player

> A modern DSD music player for Linux with PipeWire support

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Rust](https://img.shields.io/badge/rust-1.75+-blue.svg)](https://www.rust-lang.org)
[![GTK4](https://img.shields.io/badge/GTK4-4.12+-green.svg)](https://gtk.rs)

## Features

- 🎵 **Native DSD Support** - DSF/DFF/SACD ISO formats
- 🔊 **PipeWire Integration** - Low-latency audio playback
- 🎨 **Modern UI** - Apple Music-inspired GTK4/libadwaita design
- 📚 **Music Library** - Smart album/artist/playlist management
- 🔧 **Flexible Playback** - Native DSD / DoP / PCM conversion
- 🖥️ **Linux Native** - Optimized for Linux desktop

## Supported Formats

| Format | Extensions | Sample Rates |
|--------|------------|--------------|
| DSD Audio File | `.dsf` | DSD64/128/256/512 |
| DSD Interchange File | `.dff` | DSD64/128/256/512 |
| SACD ISO | `.iso` | DSD64 |
| WavPack DSD | `.wv` | DSD64/128 |

## Installation

### Build from Source

```bash
# Clone repository
git clone https://github.com/yourusername/dsd-player.git
cd dsd-player

# Build Release version
cargo build --release

# Install
sudo install -Dm755 target/release/dsd-player /usr/bin/dsd-player
sudo install -Dm644 data/dsd-player.desktop /usr/share/applications/dsd-player.desktop
```

### System Dependencies

```bash
# Debian/Ubuntu
sudo apt install \
    libgtk-4-dev \
    libadwaita-1-dev \
    libpipewire-0.3-dev \
    libtag1-dev \
    ffmpeg

# Fedora
sudo dnf install \
    gtk4-devel \
    libadwaita-devel \
    pipewire-devel \
    taglib-devel \
    ffmpeg

# Arch Linux
sudo pacman -S \
    gtk4 \
    libadwaita \
    pipewire \
    taglib \
    ffmpeg
```

## Usage

```bash
# Run directly
dsd-player

# Specify music directory
dsd-player --music-dir ~/Music/DSD

# Verbose mode
dsd-player -v
```

## Configuration

Config file location: `~/.config/dsd-player/config.toml`

```toml
[general]
theme = "dark"
language = "zh-CN"

[library]
scan_paths = ["~/Music", "~/Downloads/DSD"]
auto_scan = true

[playback]
default_mode = "auto"  # auto / native / dop / pcm
volume = 80
gapless = true

[audio]
output_device = "auto"
buffer_size = 4096
```

## Development Roadmap

### Phase 1: MVP (2 weeks)

- [x] Basic GTK4 UI framework
- [x] PipeWire audio integration
- [x] DSF/DFF file playback
- [x] Basic playback controls
- [x] Volume control

### Phase 2: Music Library (1 week)

- [ ] Library scanning
- [ ] Album/artist/song browser
- [ ] Metadata display
- [ ] SACD ISO support
- [ ] Cover art display

### Phase 3: Playback Features (1 week)

- [ ] Playlist management
- [ ] Play modes (shuffle/repeat)
- [ ] Gapless playback
- [ ] Search functionality
- [ ] Favorites

### Phase 4: Optimization (1 week)

- [ ] Settings panel
- [ ] DSD mode switching
- [ ] Audio device selection
- [ ] Theme switching (dark/light)
- [ ] Performance optimization

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ UI Layer (GTK4/libadwaita)                              │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │
│ │  Sidebar    │ │  Library    │ │  Now Playing        │ │
│ │  Navigation │ │  Browser    │ │  (Cover + Controls) │ │
│ └─────────────┘ └─────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│ Player Core (Rust)                                      │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐ │
│ │  Playlist   │ │  Metadata   │ │  Playback Engine    │ │
│ │  Manager    │ │  Parser     │ │  (PipeWire)         │ │
│ └─────────────┘ └─────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│ Audio Backend                                           │
│ PipeWire (pw-play / libpipewire)                        │
│           ↓ ↓                                           │
│ ┌──────────────┐ ┌──────────────┐                      │
│ │ Native DSD   │ │ DoP Mode     │                      │
│ │ (DSD_U32_BE) │ │ (PCM wrap)   │                      │
│ └──────────────┘ └──────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

## Technical Stack

- **Language**: Rust 2021 Edition
- **UI**: GTK4 + libadwaita
- **Audio**: PipeWire
- **Metadata**: lofty
- **Database**: rusqlite
- **Async**: tokio

## License

MIT License - See [LICENSE](LICENSE) file

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- [PipeWire](https://pipewire.org)
- [GTK4](https://gtk.rs)
- [libadwaita](https://gnome.pages.gitlab.gnome.org/libadwaita)

## Contact

- **Author**: K
- **Email**: kyj1145141@outlook.com

---

*Version: 0.1.0*
*Last Updated: 2026-03-06*
