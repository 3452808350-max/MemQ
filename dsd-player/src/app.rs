//! DSD Player application

use crate::config::Config;
use crate::player::{DsdPlayer, Player};
use crate::ui::MainWindow;
use anyhow::Result;
use std::path::PathBuf;
use gtk4::prelude::*;
use adw::Application;

/// Main application struct
pub struct DsdApp {
    app: Application,
    config: Config,
    player: DsdPlayer,
    music_dir: Option<PathBuf>,
}

impl DsdApp {
    /// Create new application
    pub fn new(config: &Config, music_dir: Option<PathBuf>) -> Result<Self> {
        log::info!("Creating DSD application");
        
        let app = Application::builder()
            .application_id("com.dsd.player")
            .build();
        
        let player = DsdPlayer::new()?;
        
        Ok(Self {
            app,
            config: config.clone(),
            player,
            music_dir,
        })
    }

    /// Run application
    pub fn run(self) {
        log::info!("Running application");
        
        let music_dir = self.music_dir.clone();
        let config = self.config.clone();
        
        self.app.connect_startup(move |app| {
            log::debug!("Application startup");
            
            // Setup CSS
            setup_css(app);
        });
        
        self.app.connect_activate(move |app| {
            log::debug!("Application activate");
            
            // Create main window
            let window = MainWindow::new(app, &config);
            
            // Load music library if directory specified
            if let Some(ref dir) = music_dir {
                window.load_music_dir(dir);
            }
            
            window.present();
        });
        
        // Run application
        self.app.run();
    }
}

/// Setup application CSS
fn setup_css(app: &Application) {
    // Load custom CSS
    let css_provider = gtk4::CssProvider::new();
    
    // Load default theme
    let css = r#"
        .sidebar {
            background: #1a1a1a;
        }
        
        .album-cover {
            border-radius: 8px;
        }
        
        .player-bar {
            background: #252526;
            padding: 8px;
        }
        
        .track-title {
            font-weight: bold;
            font-size: 14px;
        }
        
        .track-artist {
            color: #a1a1a1;
            font-size: 12px;
        }
    "#;
    
    css_provider.load_from_string(css);
    
    gtk4::StyleContext::add_provider_for_display(
        &gtk4::Display::default().unwrap(),
        &css_provider,
        gtk4::STYLE_PROVIDER_PRIORITY_APPLICATION,
    );
}
