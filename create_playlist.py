"""
Reads this week's tracks from global_track_history.csv, ranks them by
how many countries they appeared in (each country weighted equally),
takes the top 20, and creates a Spotify playlist.
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
TOP_N = 20  # Number of tracks to include in the playlist


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
    """Search Spotify with retry on rate limit."""
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
    Read the most recent week from the CSV and rank tracks by number of
    countries they appeared in. Every country counts equally — no population
    or stream weighting.
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

    # Most recent date only
    latest_date = max(row["Date"] for row in rows)
    this_week = [row for row in rows if row["Date"] == latest_date]
    print(f"📅 Week of: {latest_date} | Entries: {len(this_week)}")

    # Count how many distinct countries each track appears in
    # Key: (track, artist) — lowercased for matching
    country_counts = Counter()
    track_display = {}  # store original casing for display/search

    for row in this_week:
        track = row["Track"].strip()
        artist = row["Artist"].strip()
        country = row["Country"].strip()
        key = (track.lower(), artist.lower())
        country_counts[key] += 1
        track_display[key] = (track, artist)  # keep original casing

    # Sort by country count descending, take top N
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

    # Get top 20 tracks ranked by country count (equal weighting)
    top_tracks, date_str = get_top_global_tracks(top_n=TOP_N)

    # Search Spotify for each — only 20 searches, fast and under rate limit
    print(f"\nSearching Spotify for {len(top_tracks)} tracks...")
    track_uris = []
    found = 0
    not_found = 0

    for t in top_tracks:
        uri = search_track(t["track"], t["artist"], headers)
        if uri:
            track_uris.append(uri)
            found += 1
            print(f"  ✅ {t['artist']} — {t['track']}")
        else:
            not_found += 1
            print(f"  ⊘  {t['artist']} — {t['track']} (not found on Spotify)")
        time.sleep(0.3)

    print(f"\n✅ Found: {found} | Not found: {not_found}")

    if not track_uris:
        print("❌ No tracks found on Spotify. Try again in a few minutes.")
        exit(1)

    # Create playlist
    date_formatted = datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d, %Y")
    playlist_name = f"Global Top 20 — {date_formatted}"
    playlist_desc = (
        f"Top 20 tracks ranked by number of countries charting (68 countries, "
        f"equal weighting). Week of {date_formatted}. Powered by Last.fm."
    )

    playlist_id = create_playlist(playlist_name, playlist_desc, headers)
    add_tracks_to_playlist(playlist_id, track_uris, headers)

    print(f"\n🚀 Done! Open Spotify and look for: '{playlist_name}'")


if __name__ == "__main__":
    main()
