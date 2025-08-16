from getpass import getpass
from typing import Tuple, List, Callable
import spotipy
import re
from tqdm import tqdm
from spotipy import SpotifyOAuth

import numpy as np
import pandas as pd
import logging

from .YoutubeMusicSource import YoutubeMusicSource


class SpotifyTarget:
    min_score = 2  # Smaller than 4
    max_album_post = 50

    song_response_mapper = {"name": "title", "artists": "artists", "id": "id"}
    album_response_mapper = {"name": "title", "artists": "artists", "id": "id", "album_type": "_type",
                             "release_date": "year"}

    def __init__(self, client_id=None, client_secret=None):
        if client_id is None or client_secret is None:
            client_id = input("Client id:")
            client_secret = getpass()
        auth_manager = spotipy.SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        self.sp = spotipy.Spotify(auth_manager=auth_manager)
        self.logger = logging.getLogger("DEBUG")

    def add_playlists_to_library(self, playlists: pd.DataFrame, client_id, client_secret, redirect_uri, username):
        auth_sp = spotipy.Spotify(
            auth_manager=SpotifyOAuth(
                client_id, client_secret, redirect_uri, username=username, scope="playlist-modify-private"
            )
        )

        # Normalize input
        playlists = playlists.copy()
        playlists = playlists.dropna(subset=["spotify_id", "playlist_title"])
        playlists = playlists.reset_index(drop=True)

        # Group by target playlist title and create each playlist, adding songs in batches
        for playlist_title, group in playlists.groupby("playlist_title"):
            raw_ids = [sid for sid in list(group["spotify_id"]) if pd.notna(sid)]
            # Only accept IDs that look like valid Spotify track IDs (22-char base62)
            song_ids = [sid for sid in raw_ids if isinstance(sid, str) and re.fullmatch(r"[A-Za-z0-9]{22}", sid)]
            if len(song_ids) == 0:
                print(f"Skipping playlist '{playlist_title}' — 0 valid Spotify matches")
                continue

            response = auth_sp.user_playlist_create(
                auth_sp.current_user()["id"], playlist_title, public=False
            )
            new_playlist_id = response["id"]

            def add_batch(batch: list[str]):
                if batch:
                    auth_sp.playlist_add_items(new_playlist_id, batch)

            self.execute_in_batches(add_batch, song_ids, limit=100)

    def get_spotify_song_ids(self, df: pd.DataFrame) -> List[str]:
        song_ids_add = []
        songs_not_found = []

        if df.empty:
            return []

        found, ambiguous, not_found = 0, 0, 0

        print("Looking up songs on spotify...")
        for idx, target_song in tqdm(df.iterrows(), total=df.shape[0]):
            song, score = self.search_for_song(target_song)
            if score > 0:
                song_ids_add.append(song["id"])
                found += 1
            elif score <= 0:
                not_found += 1
                songs_not_found.append(target_song)
                song_ids_add.append(pd.NA)

        for song in songs_not_found:
            print(f"Song {song['title']}, {song['artists']} in playlist {song['playlist_title']}"
                  f" was not found.")

        return song_ids_add

    def search_for_song(self, song: pd.Series):
        # Try multiple search variations for better matching
        search_variations = self._generate_search_variations(song)

        best_candidate = None
        best_score = -1

        for search_string in search_variations:
            try:
                response = self.sp.search(search_string, type="track", limit=20)
                candidates = pd.DataFrame(response["tracks"]["items"])

                if not candidates.empty:
                    if "artists" in candidates.columns:
                        candidates["artists"] = YoutubeMusicSource.parse_artists(candidates["artists"])

                    available_columns = [col for col in self.song_response_mapper.keys() if col in candidates.columns]
                    attr_filtered_candidates = candidates[available_columns]

                    rename_dict = {col: self.song_response_mapper[col] for col in available_columns}
                    attr_filtered_candidates = attr_filtered_candidates.rename(columns=rename_dict)

                    candidate, score = self.select_best_candidate(song, attr_filtered_candidates)

                    if score > best_score:
                        best_candidate = candidate
                        best_score = score

            except Exception:
                continue

        # Fallback: title-only broader search if we still have nothing good
        if best_score <= 0 and isinstance(song.get("title"), str):
            try:
                cleaned_title = re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", song["title"]).strip())
                response = self.sp.search(cleaned_title, type="track", limit=50)
                candidates = pd.DataFrame(response["tracks"]["items"])
                if not candidates.empty:
                    if "artists" in candidates.columns:
                        candidates["artists"] = YoutubeMusicSource.parse_artists(candidates["artists"])
                    available_columns = [col for col in self.song_response_mapper.keys() if col in candidates.columns]
                    attr_filtered_candidates = candidates[available_columns]
                    rename_dict = {col: self.song_response_mapper[col] for col in available_columns}
                    attr_filtered_candidates = attr_filtered_candidates.rename(columns=rename_dict)
                    candidate, score = self.select_best_candidate(song, attr_filtered_candidates)
                    if score > best_score:
                        best_candidate, best_score = candidate, score
            except Exception:
                pass

        return best_candidate, best_score
    
    def _generate_search_variations(self, song: pd.Series):
        """Generate multiple search variations for better matching"""
        title = song["title"]
        artists_str = str(song["artists"]).replace("[", "").replace("]", "").replace("\'", "")

        # Clean up title
        suffixes_to_remove = [
            " (Official Audio)", " (Official Video)", " (Official Music Video)",
            " (Lyrics)", " (Lyric Video)", " (Audio)", " (Video)",
            " (Slowed)", " (Sped Up)", " (Remix)", " (Lo-Fi Remix)",
            " (Instrumental)", " (Beat)", " (Type Beat)", " (Free)",
            " [FREE]", " (No Copyright Music)", " (No Copyright)",
            " (slowed)", " (sped up)", " (remix)", " (instrumental)",
            " (beat)", " (type beat)", " (free)", " [free]"
        ]

        for suffix in suffixes_to_remove:
            if title.lower().endswith(suffix.lower()):
                title = title[:-len(suffix)]

        # Strip bracketed content like [...] and (...)
        title = re.sub(r"\[[^\]]*\]", "", str(title))
        title = re.sub(r"\([^\)]*\)", "", title)
        title = title.strip()

        # Try to extract likely artist/title from hyphenated titles often used by compilation channels
        # e.g. "Epic Neoclassical Music - Audiomachine - Deceit and Betrayal" -> artist: Audiomachine, title: Deceit and Betrayal
        likely_artist_from_title = None
        likely_title_from_title = None
        if " - " in title:
            segments = [seg.strip() for seg in title.split(" - ") if seg.strip()]
            if len(segments) >= 2:
                likely_title_from_title = segments[-1]
                candidate_artist = segments[-2]
                descriptor_keywords = [
                    "music", "orchestral", "cinematic", "epic", "drone", "instrumental",
                    "records", "studios", "mix", "channel", "official", "masterpiece"
                ]
                if not any(kw in candidate_artist.lower() for kw in descriptor_keywords):
                    likely_artist_from_title = candidate_artist

        # Get first artist only
        first_artist = artists_str.split(',')[0].strip() if ',' in artists_str else artists_str

        # Extract quoted titles like Balmorhea "Elegy"
        quoted_titles = re.findall(r'"([^"]{2,})"', song["title"]) if isinstance(song["title"], str) else []

        # Handle common artist name variations and incorrect artist info
        artist_variations = [first_artist]

        if any(char.isdigit() for char in first_artist) and len(first_artist) < 10:
            if "clams casino" in title.lower():
                artist_variations.append("Clams Casino")
            elif "post malone" in title.lower():
                artist_variations.append("Post Malone")
            elif "kanye west" in title.lower():
                artist_variations.append("Kanye West")
            elif "kendrick lamar" in title.lower():
                artist_variations.append("Kendrick Lamar")
            elif "juice wrld" in title.lower():
                artist_variations.append("Juice WRLD")
            elif "asap rocky" in title.lower():
                artist_variations.append("A$AP Rocky")

        if "post malone" in first_artist.lower():
            artist_variations.append("Post Malone")
        elif "kanye west" in first_artist.lower():
            artist_variations.append("Kanye West")
        elif "kendrick lamar" in first_artist.lower():
            artist_variations.append("Kendrick Lamar")
        elif "juice wrld" in first_artist.lower():
            artist_variations.append("Juice WRLD")
        elif "asap rocky" in first_artist.lower():
            artist_variations.append("A$AP Rocky")
        elif "clams casino" in first_artist.lower():
            artist_variations.append("Clams Casino")

        variations = []
        for artist in artist_variations:
            variations.extend([
                f"{title} {artist}",
                f"{artist} {title}",
            ])

        clean_title = title
        if " - " in clean_title:
            clean_title = clean_title.split(" - ", 1)[1]

        variations.extend([
            clean_title,
            f"{clean_title} {first_artist}",
        ])

        if likely_title_from_title:
            variations.extend([
                likely_title_from_title,
                f"{likely_title_from_title} {first_artist}",
            ])
        if likely_artist_from_title and likely_title_from_title:
            variations.extend([
                f"{likely_title_from_title} {likely_artist_from_title}",
                f"{likely_artist_from_title} {likely_title_from_title}",
            ])

        for qt in quoted_titles:
            qt_clean = qt.strip()
            if qt_clean:
                variations.extend([
                    qt_clean,
                    f"{qt_clean} {first_artist}",
                ])

        clean_title_no_suffix = clean_title
        for suffix in [" (Live)", " (live)", " (Official Audio)", " (Official Video)", " (Official Music Video)"]:
            if clean_title_no_suffix.endswith(suffix):
                clean_title_no_suffix = clean_title_no_suffix[:-len(suffix)]
                break

        if clean_title_no_suffix != clean_title:
            variations.extend([
                clean_title_no_suffix,
                f"{clean_title_no_suffix} {first_artist}",
            ])

        if any(char.isdigit() for char in first_artist) and len(first_artist) < 10:
            variations.append(clean_title)

        popular_songs = ["good morning", "loyalty", "congratulations", "too many nights", "i'm god"]
        if any(pop_song in clean_title.lower() for pop_song in popular_songs):
            variations.append(clean_title)

        variations = list(dict.fromkeys([v.strip() for v in variations if v.strip()]))

        return variations

    def select_best_candidate(self, target_item: pd.Series, candidates: pd.DataFrame):
        scores = [self.similarity_score_df(target_item, row) for idx, row in candidates.iterrows()]
        
        if len(scores) > 0:
            best_hit_index = np.argmax(scores)
            best_hit_score = scores[best_hit_index]
            best_hit = candidates.iloc[best_hit_index, :]
        else:
            best_hit = pd.Series()
            best_hit_score = 0

        return best_hit, best_hit_score

    @staticmethod
    def found_item_message(item, result_code):
        if result_code == -1:
            return f"\033[1;32;40m Found: {item['title']} by {str(item['artists'])} \033[0;37;40m"
        elif result_code == 0:
            return f"\033[1;33;40m Ambiguous result for {item['title']} by {str(item['artists'])} \033[0;37;40m"
        elif result_code == 1:
            return f"\033[1;33;40m Not found {item['title']} by {str(item['artists'])} \033[0;37;40m"

    ######### Album workflow ###########

    def add_albums_to_library(self, spotify_ids: List[str], client_id, client_secret, redirect_uri):
        auth_sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id, client_secret, redirect_uri,
                                                            scope="user-library-modify"))
        self.execute_in_batches(auth_sp.current_user_saved_albums_add,  spotify_ids, 50)

    def get_spotify_album_ids(self, albums: pd.DataFrame) -> list[str]:
        review_album_indices: list[int] = []
        best_matches: list[pd.Series] = []

        found, ambiguous, not_found = 0, 0, 0

        print("Looking up albums on spotify...")
        for idx, target_album in tqdm(albums.iterrows(), total=albums.shape[0]):
            best_candidate, score = self.search_for_album(target_album)
            if score >= self.min_score:
                found += 1
            elif score > 0:
                review_album_indices.append(idx)
                ambiguous += 1
            else:
                not_found += 1
            best_matches.append(best_candidate)

        best_matches_ids = [song["id"] for song in best_matches]
        albums.insert(0, "id", best_matches_ids)

        print(f"Results: \t \034[1;32;40m {found} \034[1;37;40m found, \034[1;33;40m {ambiguous} "
              f"\034[1;37;40m ambiguous, \034[1;31;40m {not_found} \034[1;37;40m not found \n")

        drop_albums_idx = self.eliminate_dialogue(albums, review_album_indices, best_matches)
        confirmed_albums = albums.drop(drop_albums_idx, axis=0)
        confirmed_albums = confirmed_albums.dropna()

        return confirmed_albums["id"]

    def eliminate_dialogue(self, albums: pd.DataFrame, review_album_indices: list[int], best_matches: list[pd.Series]):
        print("The following albums could not be matched properly. Please deselect albums you do not want to add by "
              "entering their corresponding number (multiple possible, separated by commas.")
        review_album_list = np.asarray(review_album_indices)
        drop: set = set()

        def print_candidates(indices):
            for idx, row in albums.iloc[indices, :].iterrows():

                if idx not in drop:
                    out = str(idx) + "\t" + str(row["artists"]) + ": " + row["title"] \
                          + "\t to \t" + str(best_matches[idx]["artists"]) + ": " + best_matches[idx]["title"]

                    out = "\033[1;33;40m" + out + "\033[1;37;40m"
                    print(out)

        while True:
            print_candidates(review_album_list)
            print("If nothing should be edited, please type 'nothing'.")
            i = input()
            cleaned_i = i.replace(" ", "").split(",")

            if not i.lower() == 'nothing':

                try:
                    cleaned_i = [int(x) for x in cleaned_i]
                except Exception:
                    print("Please only type in numbers separated with commas")
                    continue

            for e in cleaned_i:
                drop.add(e)

            while True:
                i2 = input("Continue editing? y/n \n")
                if i2 == "n":
                    print(f"Adding closest matches for the remaining {len(review_album_list)} candidates...")
                    return review_album_list
                elif i2 == "y":
                    break

    def search_for_album(self, album_info) -> Tuple[pd.Series, int]:
        query = self.generate_search_string(album_info)
        response = self.sp.search(query, type="album", limit=10)
        candidates = response["albums"]["items"]
        candidates = pd.DataFrame(candidates)

        if candidates.empty:
            empty = album_info
            album_info["id"] = pd.NA
            return empty, -1

        attr_filtered_candidates = candidates[self.album_response_mapper]
        attr_filtered_candidates = attr_filtered_candidates.rename(columns=self.album_response_mapper)
        attr_filtered_candidates["year"] = self.parse_year(attr_filtered_candidates["year"])
        attr_filtered_candidates["artists"] = YoutubeMusicSource.parse_artists(attr_filtered_candidates["artists"])
        best_candidate, score = self.select_best_candidate_album(album_info, attr_filtered_candidates)
        return best_candidate, score

    def select_best_candidate_album(self, target_album: pd.Series, candidates: pd.DataFrame) -> Tuple[pd.Series, int]:
        scores = []
        candidate_album_infos = []
        for idx, hit in candidates.iterrows():
            candidate_album_infos.append(hit)
            scores.append(self.similarity_score_df(target_album, hit))

        if len(scores) > 0:
            best_hit_index = np.argmax(scores)
            best_hit = candidate_album_infos[best_hit_index]
            best_hit_score = scores[best_hit_index]
        else:
            best_hit = pd.Series(index=target_album.index)
            best_hit_score = 0

        return best_hit, best_hit_score

    @staticmethod
    def generate_search_string(obj: pd.Series):
        # Clean up the title - remove common suffixes and prefixes
        title = obj["title"]
        
        # Remove common suffixes that might interfere with matching
        suffixes_to_remove = [
            " (Official Audio)", " (Official Video)", " (Official Music Video)",
            " (Lyrics)", " (Lyric Video)", " (Audio)", " (Video)",
            " (Slowed)", " (Sped Up)", " (Remix)", " (Lo-Fi Remix)",
            " (Instrumental)", " (Beat)", " (Type Beat)", " (Free)",
            " [FREE]", " (No Copyright Music)", " (No Copyright)",
            " (slowed)", " (sped up)", " (remix)", " (instrumental)",
            " (beat)", " (type beat)", " (free)", " [free]"
        ]
        
        for suffix in suffixes_to_remove:
            if title.lower().endswith(suffix.lower()):
                title = title[:-len(suffix)]
        
        # Clean up artists string
        artists_str = str(obj["artists"]).replace("[", "").replace("]", "").replace("\'", "")
        
        # Create multiple search variations for better matching
        search_variations = [
            f"{title} {artists_str}",  # Original
            title,  # Just title
            f"{title} {artists_str.split(',')[0]}" if ',' in artists_str else f"{title} {artists_str}"  # First artist only
        ]
        
        return search_variations[0]  # Return the best variation for now

    @staticmethod
    def similarity_score(album_1: pd.Series, album_2: pd.Series):
        score = 0

        for attr in album_1.index.values:
            if album_1[attr] == album_2[attr]:
                score += 1
        return score

    @staticmethod
    def similarity_score_df(a: pd.Series, b: pd.Series):
        score = 0
        
        # Normalize strings for comparison
        def normalize_string(s):
            if pd.isna(s):
                return ""
            return str(s).lower().strip()

        def normalize_for_exact(s: str) -> str:
            s = s.lower()
            s = re.sub(r"\[[^\]]*\]", "", s)
            s = re.sub(r"\([^\)]*\)", "", s)
            s = re.sub(r"[^\w\s]", " ", s)
            s = re.sub(r"\s+", " ", s).strip()
            return s
        
        # Check title similarity (most important)
        if "title" in a and "title" in b:
            title_a = normalize_string(a["title"])
            title_b = normalize_string(b["title"])
            
            # Clean up titles for comparison (remove common suffixes)
            suffixes_to_remove = [" (slowed)", " (sped up)", " (remix)", " (instrumental)", " (beat)", " (type beat)", " (free)", " [free]"]
            for suffix in suffixes_to_remove:
                if title_a.endswith(suffix):
                    title_a = title_a[:-len(suffix)]
                if title_b.endswith(suffix):
                    title_b = title_b[:-len(suffix)]
            
            # Much stricter title matching
            if title_a == title_b:
                score += 20  # Exact title match (much higher weight)
            elif title_a in title_b or title_b in title_a:
                # Only give points if the match is substantial (not just a word)
                if len(title_a) > 3 and len(title_b) > 3:
                    score += 5  # Partial title match (reduced)
                else:
                    score += 1  # Very minor match
            elif any(word in title_b for word in title_a.split() if len(word) > 3):
                score += 1  # Word overlap (only for longer words)

            # Exact match ignoring punctuation/parentheticals
            if normalize_for_exact(title_a) and normalize_for_exact(title_a) == normalize_for_exact(title_b):
                score += 10
        
        # Check artist similarity (less important than title, but still significant)
        if "artists" in a and "artists" in b:
            artists_a = normalize_string(a["artists"])
            artists_b = normalize_string(b["artists"])
            
            if artists_a == artists_b:
                score += 3  # Exact artist match (reduced from 5)
            elif artists_a in artists_b or artists_b in artists_a:
                score += 1  # Partial artist match (reduced from 2)
            else:
                # Check if any individual artist matches
                artists_a_list = [artist.strip() for artist in artists_a.split(',')]
                artists_b_list = [artist.strip() for artist in artists_b.split(',')]
                
                for artist_a in artists_a_list:
                    for artist_b in artists_b_list:
                        if artist_a and artist_b and (artist_a in artist_b or artist_b in artist_a):
                            score += 1
                            break
        
        # Prioritize original versions over remixes/mashups
        if "title" in b:
            title_b = normalize_string(b["title"])
            # Penalize remixes, mashups, and covers, but be more lenient with featured artists
            remix_keywords = ["remix", "mashup", "cover", "x", "×"]
            for keyword in remix_keywords:
                if keyword in title_b:
                    score -= 3  # Penalty for remixes/mashups
                    break
            
            # Be more lenient with featured artists - only penalize if it's clearly a remix/mashup
            if "feat" in title_b or "ft" in title_b:
                # Only penalize if it's clearly a remix/mashup, not just a featured artist
                if any(keyword in title_b for keyword in ["remix", "mashup", "cover", "x", "×"]):
                    score -= 2  # Smaller penalty for remixes with featured artists
                else:
                    score -= 1  # Very small penalty for featured artists in original songs
        
        # Prioritize primary artist (first artist in the list)
        if "artists" in b:
            artists_b = normalize_string(b["artists"])
            artists_b_list = [artist.strip() for artist in artists_b.split(',')]
            
            # If the first artist is the one we're looking for, give bonus
            if "title" in a and "artists" in a:
                title_a = normalize_string(a["title"])
                artists_a = normalize_string(a["artists"])
                
                # Try to extract the expected artist from the title
                expected_artist = None
                if "clams casino" in title_a:
                    expected_artist = "clams casino"
                elif "post malone" in title_a:
                    expected_artist = "post malone"
                elif "kanye west" in title_a:
                    expected_artist = "kanye west"
                elif "kendrick lamar" in title_a:
                    expected_artist = "kendrick lamar"
                
                if expected_artist and artists_b_list and expected_artist in artists_b_list[0].lower():
                    score += 5  # Bonus for primary artist match
        
        # Require both title AND artist to match reasonably well
        if "title" in a and "title" in b and "artists" in a and "artists" in b:
            title_a = normalize_string(a["title"])
            title_b = normalize_string(b["title"])
            artists_a = normalize_string(a["artists"])
            artists_b = normalize_string(b["artists"])
            
            # Clean up titles for artist check too
            suffixes_to_remove = [" (slowed)", " (sped up)", " (remix)", " (instrumental)", " (beat)", " (type beat)", " (free)", " [free]"]
            for suffix in suffixes_to_remove:
                if title_a.endswith(suffix):
                    title_a = title_a[:-len(suffix)]
                if title_b.endswith(suffix):
                    title_b = title_b[:-len(suffix)]
            
            # Check if artists are completely different
            artists_a_list = [artist.strip() for artist in artists_a.split(',')]
            artists_b_list = [artist.strip() for artist in artists_b.split(',')]
            
            artist_match_found = False
            for artist_a in artists_a_list:
                for artist_b in artists_b_list:
                    if artist_a and artist_b and (artist_a in artist_b or artist_b in artist_a):
                        artist_match_found = True
                        break
            
            # Heuristic: channel-like uploaders shouldn't cause artist mismatch penalties
            channel_like_keywords = [
                "records", "music only", "studios", "channel", "official", "cosmonaut", "cercle", "mix", "cinematic"
            ]
            artists_a_is_channel_like = any(kw in artists_a for kw in channel_like_keywords)

            # If titles are very similar but artists are completely different, apply a smaller penalty (or none if channel-like)
            if (title_a == title_b or title_a in title_b or title_b in title_a) and not artist_match_found:
                if not artists_a_is_channel_like:
                    # Only apply penalty if the original artist looks like a real artist (not timestamp/channel)
                    if not any(char.isdigit() for char in artists_a) or len(artists_a) > 10:
                        score -= 5  # Reduced penalty for title match but no artist match
            
            # Bonus for good title AND artist match
            if (title_a == title_b or title_a in title_b or title_b in title_a) and artist_match_found:
                score += 5  # Bonus for good title AND artist match
        
        return score

    @staticmethod
    def parse_year(dates):
        return [str(date)[:4] for date in list(dates)]

    @staticmethod
    def execute_in_batches(func: Callable, _list: list, limit: int, ):
        batches = int(len(_list) / limit)
        for i in range(batches + 1):
            lower_idx = i * limit

            full_upper_idx = (i + 1) * limit
            upper_idx = full_upper_idx if full_upper_idx <= len(_list) - 1 else len(_list) - 1
            func(_list[lower_idx:upper_idx])