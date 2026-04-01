//! DSD Player - A modern DSD music player for Linux
//! 
//! Features:
//! - Native DSD playback via PipeWire
//! - DSF/DFF/SACD ISO support
//! - Modern GTK4/libadwaita UI
//! - Music library management

mod app;
mod config;
mod player;
mod library;
mod ui;
mod models;

use anyhow::Result;
use std::path::PathBuf;

fn main() -> Result<()> {
    // Initialize logger
    env_logger::Builder::from_env(
        env_logger::Env::default().default_filter_or("info")
    ).init();

    log::info!("Starting DSD Player v{}", env!("CARGO_PKG_VERSION"));

    // Parse command line arguments
    let args = std::env::args().collect::<Vec<_>>();
    let music_dir = parse_args(&args);

    // Initialize configuration
    let config = config::Config::load()?;

    // Check PipeWire availability
    if !check_pipewire() {
        anyhow::bail!("PipeWire is not available. Please install PipeWire >= 0.3.50");
    }

    log::info!("PipeWire is available");

    // Create and run application
    let app = app::DsdApp::new(&config, music_dir)?;
    app.run();

    Ok(())
}

fn parse_args(args: &[String]) -> Option<PathBuf> {
    use std::env;
    
    let mut music_dir = None;
    
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--music-dir" | "-m" => {
                if i + 1 < args.len() {
                    music_dir = Some(PathBuf::from(&args[i + 1]));
                    i += 1;
                }
            }
            "--verbose" | "-v" => {
                env::set_var("RUST_LOG", "debug");
            }
            "--help" | "-h" => {
                print_help();
                std::process::exit(0);
            }
            "--version" => {
                println!("dsd-player {}", env!("CARGO_PKG_VERSION"));
                std::process::exit(0);
            }
            _ => {
                // Assume it's a music directory
                music_dir = Some(PathBuf::from(&args[i]));
            }
        }
        i += 1;
    }
    
    music_dir
}

fn print_help() {
    println!("DSD Player v{}", env!("CARGO_PKG_VERSION"));
    println!();
    println!("USAGE:");
    println!("    dsd-player [OPTIONS] [MUSIC_DIR]");
    println!();
    println!("OPTIONS:");
    println!("    -m, --music-dir <DIR>    Specify music directory");
    println!("    -v, --verbose            Enable verbose logging");
    println!("    -h, --help               Print help information");
    println!("    --version                Print version information");
    println!();
    println!("EXAMPLES:");
    println!("    dsd-player");
    println!("    dsd-player ~/Music/DSD");
    println!("    dsd-player -m ~/Music -v");
}

fn check_pipewire() -> bool {
    // Check if pw-play is available
    std::process::Command::new("pw-play")
        .arg("--version")
        .output()
        .map(|output| output.status.success())
        .unwrap_or(false)
}
