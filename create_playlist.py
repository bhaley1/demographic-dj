"""
Reads this week's tracks from global_track_history.csv and creates
a Spotify playlist on your account. Runs in GitHub Actions using a
stored refresh token — no browser interaction needed.
"""

import os
import csv
import json
import time
import requests
from datetime import datetime
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


def get_access_token():
    """Exchange refresh token for a fresh access token."""
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
    token = response.json()["access_token"]
    print("✅ Got fresh access token")
    return token


def get_current_user(headers):
    """Get the Spotify user ID and display name."""
    response = requests.get(f"{SPOTIFY_API}/me", headers=headers)
    response.raise_for_status()
    data = response.json()
    return data["id"], data.get("display_name", data["id"])


def search_track(track_name, artist_name, headers):
    """Search Spotify for a track and return its URI."""
    # Try structured query first
    query = f"track:{track_name} artist:{artist_name}"
    response = requests.get(
        f"{SPOTIFY_API}/search",
        params={"q": query, "type": "track", "limit": 1},
        headers=headers,
    )
    if response.status_code == 200:
        items = response.json().get("tracks", {}).get("items", [])
        if items:
            return items[0]["uri"]

    # Fall back to plain text search
    query = f"{track_name} {artist_name}"
    response = requests.get(
        f"{SPOTIFY_API}/search",
        params={"q": query, "type": "track", "limit": 1},
        headers=headers,
    )
    if response.status_code == 200:
        items = response.json().get("tracks", {}).get("items", [])
        if items:
            return items[0]["uri"]

    return None


def get_this_weeks_tracks():
    """
    Read global_track_history.csv and return unique tracks from the most recent date.
    """
    filename = "global_track_history.csv"
    if not os.path.isfile(filename):
        print(f"❌ {filename} not found.")
        exit(1)

    rows = []
    with open(filename, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        print("❌ CSV is empty.")
        exit(1)

    # Print the first row so we can see the actual column names
    print(f"📋 CSV columns: {list(rows[0].keys())}")
    print(f"📋 Sample row: {rows[0]}")

    # Get only the most recent date
    latest_date = max(row["Date"] for row in rows)
    this_week = [row for row in rows if row["Date"] == latest_date]
    print(f"📅 Using tracks from: {latest_date} ({len(this_week)} entries)")
    return this_week, latest_date


def create_playlist(user_id, name, description, headers):
    """Create a new public playlist."""
    response = requests.post(
        f"{SPOTIFY_API}/me/playlists",
        headers={**headers, "Content-Type": "application/json"},
        data=json.dumps({
            "name": name,
            "description": description,
            "public": True,
        }),
    )
    if response.status_code == 403:
        print("❌ 403 Forbidden — re-run authorize_spotify.py and update SPOTIPY_REFRESH_TOKEN secret.")
        exit(1)
    response.raise_for_status()
    playlist = response.json()
    print(f"🎵 Created playlist: {playlist['name']}")
    return playlist["id"]


def add_tracks_to_playlist(playlist_id, track_uris, headers):
    """Add tracks to a playlist in batches of 100."""
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
    # Auth
    access_token = get_access_token()
    headers = {"Authorization": f"Bearer {access_token}"}
    user_id, display_name = get_current_user(headers)
    print(f"👤 Logged in as: {display_name} ({user_id})")

    # Load this week's tracks
    tracks, date_str = get_this_weeks_tracks()

    # Detect column names dynamically
    sample = tracks[0]
    track_col = next((k for k in sample.keys() if k.lower() == "track"), None)
    artist_col = next((k for k in sample.keys() if k.lower() == "artist"), None)

    if not track_col or not artist_col:
        print(f"❌ Could not find Track/Artist columns. Found: {list(sample.keys())}")
        exit(1)

    print(f"✅ Using columns: track='{track_col}', artist='{artist_col}'")

    # Deduplicate
    seen = set()
    unique_tracks = []
    for t in tracks:
        key = (t[track_col].lower().strip(), t[artist_col].lower().strip())
        if key not in seen:
            seen.add(key)
            unique_tracks.append(t)
    print(f"🔍 Unique tracks this week: {len(unique_tracks)}")

    # Search Spotify
    print("Searching Spotify...")
    track_uris = []
    found = 0
    not_found = 0

    for t in unique_tracks:
        uri = search_track(t[track_col], t[artist_col], headers)
        if uri:
            track_uris.append(uri)
            found += 1
        else:
            not_found += 1
        time.sleep(0.05)

    track_uris = list(dict.fromkeys(track_uris))
    print(f"✅ Found: {found} | Not found: {not_found} | Unique URIs: {len(track_uris)}")

    if not track_uris:
        print("❌ No tracks found on Spotify.")
        print("   Check that SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET are correct.")
        exit(1)

    # Create playlist
    date_formatted = datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d, %Y")
    playlist_name = f"Global Top 5s — {date_formatted}"
    playlist_desc = f"Top 5 tracks from 68 countries via Last.fm. Week of {date_formatted}."

    playlist_id = create_playlist(user_id, playlist_name, playlist_desc, headers)
    add_tracks_to_playlist(playlist_id, track_uris, headers)

    print(f"\n🚀 Done! Open Spotify and look for: '{playlist_name}'")


if __name__ == "__main__":
    main()
