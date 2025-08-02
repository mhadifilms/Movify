# Movify - YouTube Music to Spotify Playlist Migrator

A Python tool that migrates YouTube Music playlists to Spotify using public/unlisted playlist URLs. No YouTube Music authentication required!

## Features

- 🎵 **Easy Migration**: Migrate YouTube Music playlists to Spotify with just URLs
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
```

### 5. Run the Migration
```bash
python migrate_playlists.py
```

## How It Works

1. **URL Processing**: Extracts playlist IDs from YouTube Music URLs
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
- Public playlists: `https://music.youtube.com/playlist?list=PLAYLIST_ID`
- Unlisted playlists: Same format, just needs to be accessible

## Configuration

### Spotify API Setup
1. **Client ID & Secret**: From Spotify Developer Dashboard
2. **User ID**: Your Spotify username (found in your profile)
3. **Redirect URI**: Must match what you set in the Spotify app

### Playlist URLs
Add your YouTube Music playlist URLs to the `PLAYLIST_URLS` list in `config.py`:
```python
PLAYLIST_URLS = [
    "https://music.youtube.com/playlist?list=YOUR_FIRST_PLAYLIST_ID",
    "https://music.youtube.com/playlist?list=YOUR_SECOND_PLAYLIST_ID",
    # Add more as needed
]
```

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

**Authentication errors**
- Make sure your Spotify Client ID and Secret are correct
- Check that the Redirect URI matches exactly
- Ensure your Spotify account is active

### Debug Mode
For detailed logging, you can modify the script to show more information about the matching process.

## File Structure

```
Movify/
├── movify/                    # Core library
│   ├── __init__.py
│   ├── SpotifyTarget.py      # Spotify API integration
│   └── YoutubeMusicSource.py # YouTube Music data fetching
├── config_template.py         # Configuration template
├── config.py                  # Your configuration (gitignored)
├── migrate_playlists.py       # Main migration script
├── requirements.txt           # Python dependencies
└── README.md                 # This file
```

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
