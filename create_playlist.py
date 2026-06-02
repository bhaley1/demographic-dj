"""
Reads this week's tracks from global_track_history.csv, ranks them by
how many countries they appeared in (each country weighted equally),
takes the top N, and:
  1. Creates a Spotify playlist shell on your account
  2. Writes the ranked list (with Spotify search links) to weekly_top40.txt

Spotify blocks adding tracks via API for individual developer accounts
(Development Mode policy), so tracks are added manually. The text file
gives you a clean list with one-tap search links for each track.

Uses a local URI cache (uri_cache.json) so tracks found once are never
searched again, keeping Spotify API calls minimal.
"""

import os
import csv
import json
import time
import urllib.parse
import requests
from datetime import datetime
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET", "").strip()
REFRESH_TOKEN = os.getenv("SPOTIPY_REFRESH_TOKEN", "").strip()

SPOTIFY_API = "https://api.spotify.com/v1"
TOP_N = 40
CACHE_FILE = "uri_cache.json"
LIST_FILE = "weekly_top40.txt"


def load_cache():
    if os.path.isfile(CACHE_FILE):
        try:
            with open(CACHE_FILE, encoding="utf-8") as f:
                cache = json.load(f)
            print(f"💾 Loaded URI cache: {len(cache)} known tracks")
            return cache
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved URI cache: {len(cache)} tracks")
    except IOError as e:
        print(f"⚠️  Could not save cache: {e}")


def cache_key(track, artist):
    return f"{track.lower().strip()}|||{artist.lower().strip()}"


def get_access_token():
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        return None
    try:
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
    except Exception as e:
        print(f"⚠️  Could not get access token: {e}")
        return None


def search_track(track_name, artist_name, headers, retries=3):
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
                if retry_after > 120:
                    print(f"⏳ Rate limited {retry_after}s — skipping.")
                    return None
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


def write_list_file(top_tracks, date_str):
    """Write the ranked list to a text file with Spotify search links."""
    date_formatted = datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d, %Y")
    lines = []
    lines.append(f"GLOBAL TOP 40 — {date_formatted}")
    lines.append("Ranked by number of countries charting (68 countries, equal weighting)")
    lines.append("Powered by Last.fm")
    lines.append("=" * 60)
    lines.append("")

    for rank, t in enumerate(top_tracks, 1):
        # Build a Spotify search URL — one tap opens the track in Spotify
        search_q = urllib.parse.quote(f"{t['track']} {t['artist']}")
        search_url = f"https://open.spotify.com/search/{search_q}"
        lines.append(f"{rank:>2}. {t['artist']} — {t['track']}")
        lines.append(f"    Countries: {t['country_count']}  |  {search_url}")
        lines.append("")

    content = "\n".join(lines)
    with open(LIST_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"📝 Wrote ranked list to {LIST_FILE}")


def create_playlist_shell(headers, date_str):
    """Create an (empty) playlist shell. Tracks added manually due to API limits."""
    date_formatted = datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d, %Y")
    name = f"Global Top 40 — {date_formatted}"
    desc = (
        f"Top 40 tracks ranked by number of countries charting "
        f"(68 countries, equal weighting). Week of {date_formatted}. Powered by Last.fm."
    )
    try:
        response = requests.post(
            f"{SPOTIFY_API}/me/playlists",
            headers={**headers, "Content-Type": "application/json"},
            data=json.dumps({"name": name, "description": desc, "public": True}),
        )
        response.raise_for_status()
        print(f"🎵 Created playlist shell: {name}")
    except Exception as e:
        print(f"⚠️  Could not create playlist shell: {e}")


def main():
    # Rank the tracks (this always works — no Spotify needed)
    top_tracks, date_str = get_top_global_tracks(top_n=TOP_N)

    # Write the list file (this is what gets emailed)
    write_list_file(top_tracks, date_str)

    # Optionally create the playlist shell and warm the URI cache
    access_token = get_access_token()
    if access_token:
        headers = {"Authorization": f"Bearer {access_token}"}
        create_playlist_shell(headers, date_str)

        # Warm the cache for any new tracks (helps if write access returns later)
        cache = load_cache()
        updated = False
        for t in top_tracks:
            key = cache_key(t["track"], t["artist"])
            if key not in cache:
                uri = search_track(t["track"], t["artist"], headers)
                cache[key] = uri or ""
                updated = True
                time.sleep(0.3)
        if updated:
            save_cache(cache)

    print("\n✨ Done. The Top 40 list is ready in weekly_top40.txt")


if __name__ == "__main__":
    main()
