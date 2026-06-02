"""
Reads this week's tracks from global_track_history.csv, ranks them by
how many countries they appeared in (each country weighted equally),
takes the top N, and creates a Spotify playlist.

Uses a local URI cache (uri_cache.json) so tracks found once are never
searched again. This keeps Spotify API calls minimal and avoids rate limits.
"""

import os
import csv
import json
import time
import requests
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET", "").strip()
REFRESH_TOKEN = os.getenv("SPOTIPY_REFRESH_TOKEN", "").strip()

if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
    print("❌ Missing one or more required environment variables:")
    print("   SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REFRESH_TOKEN")
    exit(1)

SPOTIFY_API = "https://api.spotify.com/v1"
TOP_N = 40                      # Number of tracks in the playlist
CACHE_FILE = "uri_cache.json"   # Stores track -> Spotify URI mappings


def load_cache():
    """Load the URI cache from disk. Returns empty dict if not found."""
    if os.path.isfile(CACHE_FILE):
        try:
            with open(CACHE_FILE, encoding="utf-8") as f:
                cache = json.load(f)
            print(f"💾 Loaded URI cache: {len(cache)} known tracks")
            return cache
        except (json.JSONDecodeError, IOError):
            print("⚠️  Cache file unreadable, starting fresh")
            return {}
    print("💾 No cache yet, starting fresh")
    return {}


def save_cache(cache):
    """Write the URI cache back to disk."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved URI cache: {len(cache)} tracks")
    except IOError as e:
        print(f"⚠️  Could not save cache: {e}")


def cache_key(track, artist):
    """Build a normalized cache key for a track."""
    return f"{track.lower().strip()}|||{artist.lower().strip()}"


def get_access_token():
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )
    response.raise_for_status()
    print("✅ Got fresh access token")
    return response.json()["access_token"]


def get_current_user(headers):
    response = requests.get(f"{SPOTIFY_API}/me", headers=headers)
    response.raise_for_status()
    data = response.json()
    return data["id"], data.get("display_name", data["id"])


def search_track(track_name, artist_name, headers, retries=3):
    """Search Spotify with retry on rate limit. Returns URI or None."""
    queries = [
        f"track:{track_name} artist:{artist_name}",
        f"{track_name} {artist_name}",
    ]
    for query in queries:
        for attempt in range(retries):
            response = requests.get(
                f"{SPOTIFY_API}/search",
                params={"q": query, "type": "track", "limit": 1},
                headers=headers,
            )
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                # If the wait is absurdly long (rate limit cooldown), bail out
                if retry_after > 120:
                    print(f"⏳ Rate limited for {retry_after}s — too long, skipping search.")
                    return None
                print(f"⏳ Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after + 1)
                continue
            if response.status_code == 200:
                items = response.json().get("tracks", {}).get("items", [])
                if items:
                    return items[0]["uri"]
                break
            break
    return None


def get_top_global_tracks(csv_file="global_track_history.csv", top_n=TOP_N):
    """
    Rank tracks from the most recent week by number of countries charting.
    Every country counts equally — no population or stream weighting.
    """
    if not os.path.isfile(csv_file):
        print(f"❌ {csv_file} not found.")
        exit(1)

    rows = []
    with open(csv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        print("❌ CSV is empty.")
        exit(1)

    latest_date = max(row["Date"] for row in rows)
    this_week = [row for row in rows if row["Date"] == latest_date]
    print(f"📅 Week of: {latest_date} | Entries: {len(this_week)}")

    country_counts = Counter()
    track_display = {}

    for row in this_week:
        track = row["Track"].strip()
        artist = row["Artist"].strip()
        key = (track.lower(), artist.lower())
        country_counts[key] += 1
        track_display[key] = (track, artist)

    top_tracks = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]

    print(f"\n🌍 Top {top_n} most globally widespread tracks this week:")
    print(f"{'Rank':<5} {'Countries':>9}  {'Artist':<25} {'Track'}")
    print("-" * 70)
    results = []
    for rank, (key, count) in enumerate(top_tracks, 1):
        track, artist = track_display[key]
        print(f"{rank:<5} {count:>9}  {artist:<25} {track}")
        results.append({"track": track, "artist": artist, "country_count": count})

    return results, latest_date


def create_playlist(name, description, headers):
    response = requests.post(
        f"{SPOTIFY_API}/me/playlists",
        headers={**headers, "Content-Type": "application/json"},
        data=json.dumps({"name": name, "description": description, "public": True}),
    )
    if response.status_code == 403:
        print("❌ 403 — re-run authorize_spotify.py and update SPOTIPY_REFRESH_TOKEN secret.")
        exit(1)
    response.raise_for_status()
    playlist = response.json()
    print(f"\n🎵 Created playlist: {playlist['name']}")
    return playlist["id"]


def add_tracks_to_playlist(playlist_id, track_uris, headers):
    for i in range(0, len(track_uris), 100):
        batch = track_uris[i:i+100]
        response = requests.post(
            f"{SPOTIFY_API}/playlists/{playlist_id}/tracks",
            headers={**headers, "Content-Type": "application/json"},
            data=json.dumps({"uris": batch}),
        )
        response.raise_for_status()
    print(f"✅ Added {len(track_uris)} tracks to playlist")


def main():
    access_token = get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    _, display_name = get_current_user(headers)
    print(f"👤 Logged in as: {display_name}")

    # Load the URI cache
    cache = load_cache()

    # Get top N tracks ranked by country count
    top_tracks, date_str = get_top_global_tracks(top_n=TOP_N)

    # Resolve URIs: use cache first, only search for unknown tracks
    print(f"\nResolving {len(top_tracks)} tracks (cache first)...")
    track_uris = []
    from_cache = 0
    searched = 0
    not_found = 0
    cache_updated = False

    for t in top_tracks:
        key = cache_key(t["track"], t["artist"])

        if key in cache:
            if cache[key]:  # non-empty URI
                track_uris.append(cache[key])
                from_cache += 1
            continue

        # Not in cache — search Spotify
        uri = search_track(t["track"], t["artist"], headers)
        searched += 1
        if uri:
            track_uris.append(uri)
            cache[key] = uri
            cache_updated = True
        else:
            cache[key] = ""  # remember that it wasn't found
            cache_updated = True
            not_found += 1
        time.sleep(0.3)

    print(f"\n✅ From cache: {from_cache} | Searched: {searched} | Not found: {not_found}")

    # Persist any new cache entries
    if cache_updated:
        save_cache(cache)

    # Dedup URIs
    track_uris = list(dict.fromkeys(track_uris))

    if not track_uris:
        print("❌ No tracks resolved. If rate limited, try again later.")
        exit(1)

    # Create the playlist
    date_formatted = datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d, %Y")
    playlist_name = f"Global Top 40 — {date_formatted}"
    playlist_desc = (
        f"Top 40 tracks ranked by number of countries charting "
        f"(68 countries, equal weighting). Week of {date_formatted}. Powered by Last.fm."
    )

    playlist_id = create_playlist(playlist_name, playlist_desc, headers)
    add_tracks_to_playlist(playlist_id, track_uris, headers)

    print(f"\n🚀 Done! Open Spotify and look for: '{playlist_name}'")


if __name__ == "__main__":
    main()
