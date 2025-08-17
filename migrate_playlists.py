import argparse
import os
import re
import pandas as pd

from movify.SpotifyTarget import SpotifyTarget
from movify.YoutubeMusicSource import YoutubeMusicSource
from config import (
    SPOTIFY_CLIENT_ID,
    SPOTIFY_CLIENT_SECRET,
    SPOTIFY_USER_ID,
    SPOTIFY_REDIRECT_URI,
    PLAYLIST_URLS,
)

# INDIVIDUAL_LINKS is optional - import it if it exists
try:
    from config import INDIVIDUAL_LINKS
except ImportError:
    INDIVIDUAL_LINKS = None


def parse_text_playlists_file(path: str) -> list[tuple[str, list[str]]]:
    """
    Parse a text file containing sections that start with a line beginning with '#',
    followed by one or more YouTube/YouTube Music links. Blank lines are ignored.

    Example:
    # sample playlist
    https://youtube.com/link1
    https://music.youtube.com/link2

    Returns a list of (playlist_title, urls) tuples.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    header_pattern = re.compile(r"^\s*#\s*(.+?)\s*$")
    url_pattern = re.compile(r"^(?:https?://)?(?:(?:[a-zA-Z0-9.-]+\.)?youtube\.com/|youtu\.be/)", re.IGNORECASE)

    playlists: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_urls: list[str] = []

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            header_match = header_pattern.match(line)
            if header_match:
                # Commit previous section
                if current_title and current_urls:
                    playlists.append((current_title, current_urls))
                current_title = header_match.group(1)
                current_urls = []
                continue

            # URL line
            if url_pattern.search(line):
                normalized = line if line.startswith("http") else ("https://" + line)
                current_urls.append(normalized)

    # Commit last section
    if current_title and current_urls:
        playlists.append((current_title, current_urls))

    return playlists


def parse_text_playlists_text(content: str) -> list[tuple[str, list[str]]]:
    """Parse in-memory text into (playlist_title, urls) tuples. Same format as file parser."""
    header_pattern = re.compile(r"^\s*#\s*(.+?)\s*$")
    url_pattern = re.compile(r"^(?:https?://)?(?:(?:[a-zA-Z0-9.-]+\.)?youtube\.com/|youtu\.be/)", re.IGNORECASE)

    playlists: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_urls: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        header_match = header_pattern.match(line)
        if header_match:
            if current_title and current_urls:
                playlists.append((current_title, current_urls))
            current_title = header_match.group(1)
            current_urls = []
            continue

        if url_pattern.search(line):
            normalized = line if line.startswith("http") else ("https://" + line)
            current_urls.append(normalized)

    if current_title and current_urls:
        playlists.append((current_title, current_urls))

    return playlists


def clean_url_for_individual_track(url: str) -> str:
    """Clean a URL by removing &list= and everything after it.
    This ensures individual video URLs work even if they contain playlist parameters.
    """
    if "&list=" in url:
        return url.split("&list=")[0]
    return url


def main():
    parser = argparse.ArgumentParser(description="Migrate YouTube/YouTube Music links into Spotify playlists")
    parser.add_argument(
        "--from-text",
        dest="from_text",
        help="Path to a text file with sections '# Title' followed by YouTube links",
    )
    args = parser.parse_args()

    sp = SpotifyTarget(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
    yt = YoutubeMusicSource()

    final_df_list: list[pd.DataFrame] = []

    # Process text file if provided
    if args.from_text:
        # Parse the text file into sections of (playlist_title, urls)
        sections = parse_text_playlists_file(args.from_text)
        if not sections:
            print("❌ No playlists found in the provided text file.")
            return

        print("🎵 Building playlists from text file...")
        for idx, (title, urls) in enumerate(sections, start=1):
            print(f"\n📋 Processing section {idx}/{len(sections)}: {title} ({len(urls)} links)")
            per_section_tracks: list[pd.DataFrame] = []
            for url in urls:
                try:
                    if "list=" in url and ("/playlist" in url or "/watch" not in url):
                        # Playlist URL
                        pl_df = yt.get_playlist_from_url(url)
                        if not pl_df.empty:
                            pl_df = pl_df.copy()
                            pl_df["playlist_title"] = title
                            per_section_tracks.append(pl_df)
                    else:
                        # Single track URL
                        t_df = yt.get_track_from_url(url, playlist_title=title)
                        if not t_df.empty:
                            per_section_tracks.append(t_df)
                except Exception as e:
                    print(f"   - Skipping URL due to error: {url} -> {e}")

            if per_section_tracks:
                section_df = pd.concat(per_section_tracks, ignore_index=True, sort=False)
                final_df_list.append(section_df)
                print(f"   ✅ Added {len(section_df)} tracks to '{title}'")
            else:
                print(f"   ❌ No tracks found for '{title}'")

    # Process INDIVIDUAL_LINKS if defined (can be string or dict)
    if isinstance(INDIVIDUAL_LINKS, str) and INDIVIDUAL_LINKS.strip():
        sections = parse_text_playlists_text(INDIVIDUAL_LINKS)
        if sections:
            print("🎵 Building playlists from INDIVIDUAL_LINKS in config.py...")
            for idx, (title, urls) in enumerate(sections, start=1):
                print(f"\n📋 Processing section {idx}/{len(sections)}: {title} ({len(urls)} links)")
                per_section_tracks: list[pd.DataFrame] = []
                for url in urls:
                    try:
                        # Clean the URL for individual track processing
                        cleaned_url = clean_url_for_individual_track(url)
                        if "list=" in cleaned_url and ("/playlist" in cleaned_url or "/watch" not in cleaned_url):
                            pl_df = yt.get_playlist_from_url(cleaned_url)
                            if not pl_df.empty:
                                pl_df = pl_df.copy()
                                pl_df["playlist_title"] = title
                                per_section_tracks.append(pl_df)
                        else:
                            t_df = yt.get_track_from_url(cleaned_url, playlist_title=title)
                            if not t_df.empty:
                                per_section_tracks.append(t_df)
                    except Exception as e:
                        print(f"   - Skipping URL due to error: {url} -> {e}")

                if per_section_tracks:
                    section_df = pd.concat(per_section_tracks, ignore_index=True, sort=False)
                    final_df_list.append(section_df)
                    print(f"   ✅ Added {len(section_df)} tracks to '{title}'")
                else:
                    print(f"   ❌ No tracks found for '{title}'")

    elif isinstance(INDIVIDUAL_LINKS, dict) and INDIVIDUAL_LINKS:
        # Accept dict format: { "Playlist Title": ["url1", "url2", ...], ... }
        items = list(INDIVIDUAL_LINKS.items())
        print("🎵 Building playlists from INDIVIDUAL_LINKS dict in config.py...")
        for idx, (title, urls) in enumerate(items, start=1):
            print(f"\n📋 Processing section {idx}/{len(items)}: {title} ({len(urls)} links)")
            per_section_tracks: list[pd.DataFrame] = []
            for url in urls:
                try:
                    normalized = url if isinstance(url, str) and url.startswith("http") else (f"https://{url}" if isinstance(url, str) else "")
                    if not normalized:
                        continue
                    # Clean the URL for individual track processing
                    cleaned_url = clean_url_for_individual_track(normalized)
                    if "list=" in cleaned_url and ("/playlist" in cleaned_url or "/watch" not in cleaned_url):
                        pl_df = yt.get_playlist_from_url(cleaned_url)
                        if not pl_df.empty:
                            pl_df = pl_df.copy()
                            pl_df["playlist_title"] = title
                            per_section_tracks.append(pl_df)
                    else:
                        t_df = yt.get_track_from_url(cleaned_url, playlist_title=title)
                        if not t_df.empty:
                            per_section_tracks.append(t_df)
                except Exception as e:
                    print(f"   - Skipping URL due to error: {url} -> {e}")

            if per_section_tracks:
                section_df = pd.concat(per_section_tracks, ignore_index=True, sort=False)
                final_df_list.append(section_df)
                print(f"   ✅ Added {len(section_df)} tracks to '{title}'")
            else:
                print(f"   ❌ No tracks found for '{title}'")

    # Process PLAYLIST_URLS if defined (original functionality)
    if PLAYLIST_URLS:
        print("🎵 Migrating playlists from PLAYLIST_URLS in config.py...")
        for i, url in enumerate(PLAYLIST_URLS):
            print(f"\n📋 Processing playlist {i+1}/{len(PLAYLIST_URLS)}: {url}")
            try:
                pl_lib = yt.get_playlist_from_url(url)
                if pl_lib.empty:
                    print(f"❌ No tracks found in playlist {i+1}")
                    continue
                # Add playlist_title column if it doesn't exist
                if "playlist_title" not in pl_lib.columns:
                    pl_lib.insert(0, "playlist_title", f"Playlist {i+1}")
                final_df_list.append(pl_lib)
            except Exception as e:
                print(f"❌ Error processing playlist {i+1}: {e}")

    # Check if we have any tracks to process
    if not final_df_list:
        print("❌ No tracks to process.")
        print("Please add either:")
        print("- PLAYLIST_URLS in config.py for YouTube Music playlists")
        print("- PLAYLISTS_TEXT in config.py for individual videos")
        print("- Use --from-text <file> for text file input")
        return

    full_df = pd.concat(final_df_list, ignore_index=True, sort=False)
    print(f"✅ Collected {len(full_df)} tracks across {full_df['playlist_title'].nunique()} playlist(s)")

    # Lookup on Spotify
    print("🔍 Looking up songs on Spotify...")
    sp_ids = sp.get_spotify_song_ids(full_df)
    full_df.insert(0, "spotify_id", sp_ids)

    # Add to Spotify
    print("📤 Adding to Spotify library...")
    sp.add_playlists_to_library(
        full_df, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, SPOTIFY_USER_ID
    )

    print("\n🎉 All playlists processed!")


if __name__ == "__main__":
    main()