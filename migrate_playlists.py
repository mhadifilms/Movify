from movify.SpotifyTarget import SpotifyTarget
from movify.YoutubeMusicSource import YoutubeMusicSource
from config import (
    SPOTIFY_CLIENT_ID, 
    SPOTIFY_CLIENT_SECRET, 
    SPOTIFY_USER_ID, 
    SPOTIFY_REDIRECT_URI, 
    PLAYLIST_URLS
)

sp = SpotifyTarget(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
yt = YoutubeMusicSource()

playlist_urls = PLAYLIST_URLS

if not playlist_urls:
    print("❌ Please add your playlist URLs to the playlist_urls list above!")
    print("Format: https://music.youtube.com/playlist?list=YOUR_PLAYLIST_ID")
    exit(1)

print("🎵 Migrating playlists from URLs...")

for i, url in enumerate(playlist_urls):
    print(f"\n📋 Processing playlist {i+1}/{len(playlist_urls)}: {url}")
    
    try:
        # Get playlist data
        pl_lib = yt.get_playlist_from_url(url)
        
        if pl_lib.empty:
            print(f"❌ No tracks found in playlist {i+1}")
            continue
            
        print(f"✅ Found {len(pl_lib)} tracks in playlist")
        
        # Get Spotify song IDs
        print("🔍 Looking up songs on Spotify...")
        sp_ids = sp.get_spotify_song_ids(pl_lib)
        pl_lib.insert(0, "spotify_id", sp_ids)
        
        # Add to Spotify library
        print("📤 Adding to Spotify library...")
        sp.add_playlists_to_library(pl_lib, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, SPOTIFY_USER_ID)
        
        print(f"✅ Completed playlist {i+1}")
        
    except Exception as e:
        print(f"❌ Error processing playlist {i+1}: {e}")

print("\n🎉 All playlists processed!") 