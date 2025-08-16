# Spotify API Configuration
# Get these from https://developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID = "your_spotify_client_id_here"
SPOTIFY_CLIENT_SECRET = "your_spotify_client_secret_here"
SPOTIFY_USER_ID = "your_spotify_username_here"
SPOTIFY_REDIRECT_URI = "https://mysite.com/callback"

# YouTube Music Playlist URLs
# Add your unlisted playlist URLs here
PLAYLIST_URLS = [
    "https://music.youtube.com/playlist?list=YOUR_PLAYLIST_ID_1",
    "https://music.youtube.com/playlist?list=YOUR_PLAYLIST_ID_2",
    # Add more URLs as needed
]

# Individual YouTube Video URLs
# Add individual YouTube video URLs here
INDIVIDUAL_VIDEO_URLS = [
    "https://www.youtube.com/watch?v=Fwgg8r8cznI",
    "https://youtu.be/TA0ZeWxDG6M",
]


# Format 2: Dictionary with playlist titles as keys
PLAYLISTS_TEXT = {
    "cinematic music": [
        "https://www.youtube.com/watch?v=Fwgg8r8cznI",
        "https://www.youtube.com/watch?v=TA0ZeWxDG6M",
    ],
    "another playlist": [
        "https://www.youtube.com/watch?v=7XPlOi1-hmM",
    ]
} 