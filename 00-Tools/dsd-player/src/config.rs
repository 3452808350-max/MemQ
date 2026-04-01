//! Configuration management

use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

/// Application configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub general: GeneralConfig,
    pub library: LibraryConfig,
    pub playback: PlaybackConfig,
    pub audio: AudioConfig,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            general: GeneralConfig::default(),
            library: LibraryConfig::default(),
            playback: PlaybackConfig::default(),
            audio: AudioConfig::default(),
        }
    }
}

/// General configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeneralConfig {
    pub theme: String,
    pub language: String,
}

impl Default for GeneralConfig {
    fn default() -> Self {
        Self {
            theme: "dark".to_string(),
            language: "zh-CN".to_string(),
        }
    }
}

/// Library configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LibraryConfig {
    pub scan_paths: Vec<PathBuf>,
    pub auto_scan: bool,
}

impl Default for LibraryConfig {
    fn default() -> Self {
        Self {
            scan_paths: vec![
                dirs::music_dir().unwrap_or_else(|| PathBuf::from("~/Music")),
            ],
            auto_scan: true,
        }
    }
}

/// Playback configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlaybackConfig {
    pub default_mode: String,
    pub volume: f32,
    pub gapless: bool,
}

impl Default for PlaybackConfig {
    fn default() -> Self {
        Self {
            default_mode: "auto".to_string(),
            volume: 0.8,
            gapless: true,
        }
    }
}

/// Audio configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AudioConfig {
    pub output_device: String,
    pub buffer_size: u32,
}

impl Default for AudioConfig {
    fn default() -> Self {
        Self {
            output_device: "auto".to_string(),
            buffer_size: 4096,
        }
    }
}

impl Config {
    /// Load configuration from file
    pub fn load() -> Result<Self> {
        let config_path = get_config_path();
        
        if config_path.exists() {
            log::info!("Loading config from: {:?}", config_path);
            
            let content = std::fs::read_to_string(&config_path)?;
            let config: Config = toml::from_str(&content)?;
            
            Ok(config)
        } else {
            log::info!("Config file not found, using defaults");
            
            // Create default config
            let config = Config::default();
            config.save()?;
            
            Ok(config)
        }
    }

    /// Save configuration to file
    pub fn save(&self) -> Result<()> {
        let config_path = get_config_path();
        
        // Ensure directory exists
        if let Some(parent) = config_path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        
        let content = toml::to_string_pretty(self)?;
        std::fs::write(&config_path, content)?;
        
        log::info!("Config saved to: {:?}", config_path);
        
        Ok(())
    }
}

/// Get configuration file path
fn get_config_path() -> PathBuf {
    let config_dir = dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("~/.config"));
    
    config_dir.join("dsd-player").join("config.toml")
}
