#!/usr/bin/env python3
"""
Movify - YouTube Music to Spotify Playlist Migrator
Setup script for easy installation and configuration
"""

import os
import shutil
from pathlib import Path

def main():
    print("🎵 Movify Setup")
    print("=" * 50)
    
    # Check if config.py exists
    if os.path.exists("config.py"):
        print("✅ Configuration file already exists!")
        print("You can edit config.py to add your credentials and playlist URLs.")
    else:
        print("📝 Creating configuration file...")
        if os.path.exists("config_template.py"):
            shutil.copy("config_template.py", "config.py")
            print("✅ Created config.py from template")
            print("📝 Please edit config.py with your Spotify credentials and playlist URLs")
        else:
            print("❌ config_template.py not found!")
            return
    
    print("\n📋 Next steps:")
    print("1. Edit config.py with your Spotify API credentials")
    print("2. Add your YouTube Music playlist URLs to config.py")
    print("3. Run: python migrate_playlists.py")
    
    print("\n🔗 Get your Spotify API credentials from:")
    print("https://developer.spotify.com/dashboard")
    
    print("\n📖 For detailed instructions, see README.md")

if __name__ == "__main__":
    main()
