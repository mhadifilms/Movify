# Movify - YouTube Music to Spotify Playlist Migrator

A Python tool that migrates YouTube Music playlists and individual videos to Spotify, seamlessly matching songs and adding them to your Spotify library. No YouTube Music authentication required.

## Features

- 🎵 **Easy Migration**: Migrate YouTube Music playlists to Spotify with just URLs
- 🎬 **Individual Videos**: Support for individual YouTube video URLs
- 📝 **Text-based Playlists**: Create playlists from text files or inline text
- 🔍 **Smart Matching**: Advanced song matching algorithm that handles remixes, live versions, and featured artists
- 📋 **Batch Processing**: Process multiple playlists at once
- 🛡️ **Secure**: No YouTube Music credentials needed - works with public/unlisted playlists
- ⚡ **Fast**: Optimized for speed and accuracy

## Quick Start

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd Movify
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Spotify API
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Add `https://mysite.com/callback` as the Redirect URI
4. Copy your Client ID and Client Secret

### 4. Configure the Tool
1. Copy `config_template.py` to `config.py` (to keep your credentials private)
2. Edit `config.py` with your Spotify credentials:

**You can use any combination of these input methods - the tool will process all of them together!**
```python
SPOTIFY_CLIENT_ID = "your_client_id_here"
SPOTIFY_CLIENT_SECRET = "your_client_secret_here"
SPOTIFY_USER_ID = "your_spotify_username_here"
SPOTIFY_REDIRECT_URI = "https://mysite.com/callback"

# Add your YouTube Music playlist URLs here
PLAYLIST_URLS = [
    "https://music.youtube.com/playlist?list=YOUR_PLAYLIST_ID",
    # Add more URLs as needed
]

# Individual YouTube video/playlist links organized into custom playlists
INDIVIDUAL_LINKS = {
    "My Custom Playlist": [
        "https://www.youtube.com/watch?v=VIDEO_ID_1",
        "https://www.youtube.com/watch?v=VIDEO_ID_2",
    ],
    "Another Playlist": [
        "https://music.youtube.com/playlist?list=PLAYLIST_ID",  # Can mix playlists too!
        "https://www.youtube.com/watch?v=VIDEO_ID_3",
    ]
}
```

**The tool will automatically process all three input types if they're defined:**
- `PLAYLIST_URLS`: YouTube Music playlists (original functionality)
- `INDIVIDUAL_LINKS`: Individual videos organized into custom playlists
- Text files: Use `--from-text` argument for external playlist files

### 5. Run the Migration
```bash
# Use configuration from config.py
python migrate_playlists.py

# Or use a text file
python migrate_playlists.py --from-text /path/to/your/playlists.txt
```

## How It Works

1. **URL Processing**: Extracts playlist IDs or video IDs from YouTube URLs
2. **Data Fetching**: Retrieves track information from YouTube Music
3. **Smart Matching**: Uses advanced algorithms to match songs on Spotify
4. **Library Addition**: Adds matched songs to your Spotify library

## Advanced Features

### Song Matching Algorithm
The tool uses a sophisticated matching system that:
- Prioritizes exact title matches
- Handles remixes and live versions intelligently
- Manages featured artists correctly
- Infers correct artists from titles when metadata is wrong
- Penalizes remixes/mashups to prefer original versions

### Supported URL Formats
- **Playlists**: `https://music.youtube.com/playlist?list=PLAYLIST_ID`
- **Individual Videos**: 
  - `https://www.youtube.com/watch?v=VIDEO_ID`
  - `https://youtu.be/VIDEO_ID`
  - `https://youtube.com/watch?v=VIDEO_ID`
- **Mixed Content**: You can mix playlists and individual videos in the same input

## Troubleshooting

### Common Issues

**"No match found" for songs**
- The song might not be available on Spotify
- Try checking the song title/artist spelling
- Some songs may be region-restricted

**"Error processing playlist"**
- Check that the playlist URL is correct and accessible
- Ensure the playlist is public or unlisted
- Verify your Spotify credentials are correct

**"Error processing video"**
- Check that the video URL is correct and accessible
- Ensure the video is public or unlisted
- Some videos may be age-restricted or unavailable

**Authentication errors**
- Make sure your Spotify Client ID and Secret are correct
- Check that the Redirect URI matches exactly
- Ensure your Spotify account is active

## Dependencies

- `spotipy`: Spotify API client
- `ytmusicapi`: YouTube Music API client
- `pandas`: Data manipulation
- `numpy`: Numerical operations

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License.

## Support

If you encounter any issues, please check the troubleshooting section above or open an issue on GitHub.