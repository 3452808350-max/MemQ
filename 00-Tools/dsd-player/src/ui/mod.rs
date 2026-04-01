//! UI module

use crate::config::Config;
use gtk4::prelude::*;
use adw::{Application, ApplicationWindow};
use std::path::Path;

/// Main application window
pub struct MainWindow {
    window: ApplicationWindow,
    config: Config,
}

impl MainWindow {
    /// Create new main window
    pub fn new(app: &Application, config: &Config) -> Self {
        log::debug!("Creating main window");
        
        let window = ApplicationWindow::builder()
            .application(app)
            .title("DSD Player")
            .default_width(1200)
            .default_height(800)
            .build();
        
        // Create UI layout
        let ui = create_ui(config);
        window.set_child(Some(&ui));
        
        Self {
            window,
            config: config.clone(),
        }
    }

    /// Present window
    pub fn present(&self) {
        self.window.present();
    }

    /// Load music directory
    pub fn load_music_dir(&self, dir: &Path) {
        log::info!("Loading music directory: {:?}", dir);
        
        // TODO: Implement music library scanning
        // TODO: Update UI with scanned tracks
    }
}

/// Create main UI layout
fn create_ui(config: &Config) -> gtk4::Widget {
    // Main vertical box
    let main_box = gtk4::Box::builder()
        .orientation(gtk4::Orientation::Vertical)
        .build();

    // Header bar
    let header = create_header();
    main_box.append(&header);

    // Content area (sidebar + main view)
    let content = create_content_area(config);
    main_box.append(&content);

    // Player bar
    let player_bar = create_player_bar();
    main_box.append(&player_bar);

    main_box.upcast()
}

/// Create header bar
fn create_header() -> adw::HeaderBar {
    let header = adw::HeaderBar::builder()
        .show_title(true)
        .title_widget(&gtk4::Label::new(Some("🎵 DSD Player")))
        .build();

    // Add search button
    let search_button = gtk4::Button::builder()
        .icon_name("system-search-symbolic")
        .tooltip_text("Search")
        .build();
    
    header.pack_start(&search_button);

    header
}

/// Create content area (sidebar + main view)
fn create_content_area(config: &Config) -> gtk4::Widget {
    let paned = gtk4::Paned::builder()
        .orientation(gtk4::Orientation::Horizontal)
        .position(250)
        .build();

    // Sidebar
    let sidebar = create_sidebar(config);
    paned.set_start_child(Some(&sidebar));

    // Main view
    let main_view = create_main_view();
    paned.set_end_child(Some(&main_view));

    paned.upcast()
}

/// Create sidebar
fn create_sidebar(config: &Config) -> gtk4::Widget {
    let sidebar = gtk4::Box::builder()
        .orientation(gtk4::Orientation::Vertical)
        .css_name("sidebar")
        .build();

    // Navigation list
    let nav_list = gtk4::ListBox::new();
    
    let items = vec![
        ("🏠", "Home"),
        ("📚", "Library"),
        ("💿", "Albums"),
        ("🎙️", "Artists"),
        ("🎼", "Songs"),
        ("⭐", "Favorites"),
        ("🕐", "Recently Played"),
        ("🔧", "Settings"),
    ];

    for (icon, label) in items {
        let row = adw::ActionRow::builder()
            .title(label)
            .build();
        
        nav_list.append(&row);
    }

    sidebar.append(&nav_list);

    sidebar.upcast()
}

/// Create main view
fn create_main_view() -> gtk4::Widget {
    let scrolled = gtk4::ScrolledWindow::builder()
        .hscrollbar_policy(gtk4::PolicyType::Never)
        .build();

    // Grid layout for albums
    let grid = gtk4::FlowBox::builder()
        .homogeneous(true)
        .column_spacing(20)
        .row_spacing(20)
        .min_children_per_line(4)
        .max_children_per_line(8)
        .build();

    // Add sample album covers
    for i in 1..=12 {
        let album = create_album_card(&format!("Album {}", i), &format!("Artist {}", i));
        grid.append(&album);
    }

    scrolled.set_child(Some(&grid));
    scrolled.upcast()
}

/// Create album card
fn create_album_card(title: &str, artist: &str) -> gtk4::Widget {
    let box_widget = gtk4::Box::builder()
        .orientation(gtk4::Orientation::Vertical)
        .spacing(8)
        .build();

    // Album cover placeholder
    let cover = gtk4::Box::builder()
        .width_request(180)
        .height_request(180)
        .css_name("album-cover")
        .build();
    
    cover.add_css_class("card");

    // Album info
    let title_label = gtk4::Label::builder()
        .label(title)
        .wrap(true)
        .build();
    
    title_label.add_css_class("track-title");

    let artist_label = gtk4::Label::builder()
        .label(artist)
        .wrap(true)
        .build();
    
    artist_label.add_css_class("track-artist");

    box_widget.append(&cover);
    box_widget.append(&title_label);
    box_widget.append(&artist_label);

    box_widget.upcast()
}

/// Create player bar
fn create_player_bar() -> gtk4::Widget {
    let bar = gtk4::Box::builder()
        .orientation(gtk4::Orientation::Horizontal)
        .css_name("player-bar")
        .spacing(12)
        .build();

    // Album art (small)
    let album_art = gtk4::Box::builder()
        .width_request(48)
        .height_request(48)
        .css_name("album-cover")
        .build();
    
    bar.append(&album_art);

    // Track info
    let track_info = gtk4::Box::builder()
        .orientation(gtk4::Orientation::Vertical)
        .build();
    
    let title = gtk4::Label::builder()
        .label("Album Title - Track Title")
        .halign(gtk4::Align::Start)
        .build();
    
    title.add_css_class("track-title");

    let artist = gtk4::Label::builder()
        .label("Artist Name")
        .halign(gtk4::Align::Start)
        .build();
    
    artist.add_css_class("track-artist");

    track_info.append(&title);
    track_info.append(&artist);
    bar.append(&track_info);

    // Playback controls
    let controls = gtk4::Box::builder()
        .orientation(gtk4::Orientation::Horizontal)
        .spacing(8)
        .build();

    let prev_btn = gtk4::Button::builder()
        .icon_name("media-skip-backward-symbolic")
        .build();
    
    let play_btn = gtk4::Button::builder()
        .icon_name("media-playback-start-symbolic")
        .build();
    
    let next_btn = gtk4::Button::builder()
        .icon_name("media-skip-forward-symbolic")
        .build();

    controls.append(&prev_btn);
    controls.append(&play_btn);
    controls.append(&next_btn);

    bar.append(&controls);

    // Progress bar
    let progress = gtk4::Scale::builder()
        .orientation(gtk4::Orientation::Horizontal)
        .hexpand(true)
        .build();
    
    bar.append(&progress);

    // Volume control
    let volume = gtk4::Scale::builder()
        .orientation(gtk4::Orientation::Horizontal)
        .width_request(100)
        .build();
    
    bar.append(&volume);

    bar.upcast()
}
