from typing import Union, List, Optional
from functools import reduce
import sys
from urllib.parse import urlparse, parse_qs
import re

import pandas as pd
from ytmusicapi import YTMusic


class YoutubeMusicSource:

    def __init__(self):
        try:
            # Initialize without authentication for public playlists
            self.ytmusic = YTMusic()
        except Exception as e:
            print("Cannot establish connection. Error: \n")
            print(e)
            sys.exit(1)

    def get_albums_library_df(self) -> pd.DataFrame:
        albums_response = self.ytmusic.get_library_albums(limit=10000)
        albums = pd.DataFrame(albums_response)
        albums["artists"] = self.parse_artists(albums["artists"])
        albums = albums.drop(["browseId", "thumbnails"], axis=1)
        return albums

    def get_playlists_library(self) -> pd.DataFrame:
        playlists = self._get_playlists_df()[["playlist_title", "playlist_id", "title", "artists", "duration"]]
        playlists["artists"] = self.parse_artists(playlists["artists"])
        return playlists

    def _get_playlists_df(self) -> pd.DataFrame:
        playlists_response = self.ytmusic.get_library_playlists(limit=30)

        dfs = []
        for playlist_obj in playlists_response:
            df = pd.DataFrame(self.ytmusic.get_playlist(playlist_obj["playlistId"])["tracks"])
            df.insert(0, "playlist_id", playlist_obj["playlistId"])
            df.insert(0, "playlist_title", playlist_obj["title"])
            dfs.append(df)

        return reduce(lambda a, b: a.append(b), dfs)

    @staticmethod
    def parse_artist(object_artists_json) -> List[str]:
        return [object_artist["name"] for object_artist in list(object_artists_json)]

    @staticmethod
    def parse_artists(artists_json, as_str=True) -> Union[list[str], list[list[str]]]:
        if as_str:
            return [str(YoutubeMusicSource.parse_artist(object_artists)) for object_artists in list(artists_json)]
        else:
            return [YoutubeMusicSource.parse_artist(object_artists) for object_artists in list(artists_json)]
    
    def get_playlist_from_url(self, url: str) -> pd.DataFrame:
        """Get playlist data from a YouTube Music URL"""
        # Extract playlist ID from URL
        if "list=" in url:
            playlist_id = url.split("list=")[1].split("&")[0]
        else:
            raise ValueError("Invalid playlist URL. Must contain 'list=' parameter")
        
        # Get playlist data
        playlist_data = self.ytmusic.get_playlist(playlist_id)
        
        # Convert to DataFrame
        tracks = playlist_data.get("tracks", [])
        if not tracks:
            return pd.DataFrame()
        
        df = pd.DataFrame(tracks)
        
        # Add playlist info
        df.insert(0, "playlist_title", playlist_data.get("title", "Unknown Playlist"))
        df.insert(0, "playlist_id", playlist_id)
        
        # Parse artists
        if "artists" in df.columns:
            df["artists"] = self.parse_artists(df["artists"])
        
        # Select relevant columns
        columns_to_keep = ["playlist_title", "playlist_id", "title", "artists", "duration"]
        available_columns = [col for col in columns_to_keep if col in df.columns]
        
        return df[available_columns]

    # ---------------------- NEW: Single-track helpers ----------------------
    def get_track_from_url(self, url: str, playlist_title: str = "Unknown Playlist") -> pd.DataFrame:
        """Return a single-track DataFrame with columns: playlist_title, title, artists, duration.
        Works with youtube.com/watch, music.youtube.com/watch, youtu.be links, and playlist index links.
        """
        try:
            # Handle playlist index links (e.g., ...&index=6)
            if "list=" in url and "index=" in url:
                # Extract playlist ID and index
                playlist_id = url.split("list=")[1].split("&")[0]
                index_match = re.search(r'index=(\d+)', url)
                if index_match:
                    index = int(index_match.group(1)) - 1  # Convert to 0-based index
                    try:
                        playlist_data = self.ytmusic.get_playlist(playlist_id)
                        tracks = playlist_data.get("tracks", [])
                        if tracks and 0 <= index < len(tracks):
                            track = tracks[index]
                            title = track.get("title", "Unknown Title")
                            artists_json = track.get("artists", [])
                            artists = self.parse_artists([artists_json]) if artists_json else "Unknown Artist"
                            duration = track.get("duration")
                            
                            df = pd.DataFrame([{
                                "playlist_title": playlist_title,
                                "title": title,
                                "artists": artists[0] if isinstance(artists, list) else artists,
                                "duration": duration
                            }])
                            return df
                    except Exception as e:
                        print(f"   - Failed to get playlist index {index} from {playlist_id}: {e}")
                        # Fall back to treating this as a regular video URL
                        print(f"   - Falling back to video extraction...")
                        pass

            # Handle regular video URLs (including failed playlist index URLs)
            video_id = self._extract_video_id_from_url(url)
            if not video_id:
                print(f"   - Could not extract video ID from URL: {url}")
                return pd.DataFrame()

            # Try multiple methods to get track info
            track_info = None
            
            # Method 1: Try get_watch_playlist (most reliable)
            try:
                watch_pl = self.ytmusic.get_watch_playlist(video_id)
                tracks = watch_pl.get("tracks", [])
                if tracks:
                    track = tracks[0]
                    title = track.get("title")
                    artists_json = track.get("artists", [])
                    artists = ", ".join([a.get("name", "") for a in artists_json if a.get("name")])
                    duration = track.get("duration")
                    if title and artists:
                        track_info = {"title": title, "artists": artists, "duration": duration}
            except Exception as e:
                pass

            # Method 2: Try get_song if first method failed
            if not track_info:
                try:
                    song = self.ytmusic.get_song(video_id)
                    video_details = song.get("videoDetails", {}) if isinstance(song, dict) else {}
                    title = video_details.get("title")
                    artists = video_details.get("author")  # Channel name as best-effort
                    length_seconds = video_details.get("lengthSeconds")
                    
                    if title and artists:
                        duration = None
                        if length_seconds:
                            try:
                                total = int(length_seconds)
                                minutes = total // 60
                                seconds = total % 60
                                duration = f"{minutes}:{seconds:02d}"
                            except Exception:
                                pass
                        track_info = {"title": title, "artists": artists, "duration": duration}
                except Exception as e:
                    print(f"   - Failed to get song info for {video_id}: {e}")

            # Return DataFrame if we got track info
            if track_info:
                df = pd.DataFrame([{
                    "playlist_title": playlist_title,
                    "title": track_info["title"],
                    "artists": track_info["artists"],
                    "duration": track_info["duration"]
                }])
                return df
            
            print(f"   - Could not extract track info from {url}")
            return pd.DataFrame()
            
        except Exception as e:
            print(f"   - Error processing {url}: {e}")
            return pd.DataFrame()

    @staticmethod
    def _extract_video_id_from_url(url: str) -> Optional[str]:
        """Extract the YouTube videoId (v) from youtube.com, music.youtube.com or youtu.be URLs."""
        try:
            parsed = urlparse(url)
            # youtu.be/VIDEOID
            if parsed.netloc.endswith("youtu.be"):
                path = parsed.path.lstrip("/")
                return path if path else None
            # youtube.com/watch?v=VIDEOID or music.youtube.com/watch?v=VIDEOID
            if parsed.path == "/watch":
                qs = parse_qs(parsed.query)
                v_list = qs.get("v", [])
                if v_list:
                    return v_list[0]
            return None
        except Exception:
            return None