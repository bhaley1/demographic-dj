import os
import csv
import time
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY", "").strip()

if not LASTFM_API_KEY:
    print("❌ Missing LASTFM_API_KEY environment variable")
    print("   Get a free key at: https://www.last.fm/api/account/create")
    exit(1)

# Countries supported by Last.fm's geo.gettoptracks endpoint
COUNTRIES = [
    "united states", "united kingdom", "canada", "australia", "new zealand",
    "germany", "france", "italy", "spain", "netherlands",
    "belgium", "austria", "switzerland", "sweden", "norway",
    "denmark", "finland", "poland", "portugal", "greece",
    "ireland", "mexico", "brazil", "argentina", "chile",
    "colombia", "peru", "japan", "south korea", "india",
    "indonesia", "thailand", "philippines", "malaysia", "singapore",
    "russia", "ukraine", "turkey", "south africa", "egypt",
    "israel", "saudi arabia", "united arab emirates", "taiwan",
    "ecuador", "venezuela", "uruguay", "costa rica", "panama",
    "dominican republic", "jamaica", "iceland", "croatia",
    "serbia", "bulgaria", "romania", "slovakia", "czech republic",
    "hungary", "lithuania", "latvia", "estonia", "luxembourg",
    "morocco", "kenya", "nigeria", "ghana", "tanzania",
    "pakistan", "bangladesh", "sri lanka", "vietnam",
]


def get_top_tracks_for_country(country, limit=5):
    """
    Fetches top tracks for a country using Last.fm's free geo API.
    Requires a free API key — no OAuth or user auth needed.
    """
    try:
        url = "https://ws.audioscrobbler.com/2.0/"
        params = {
            "method": "geo.gettoptracks",
            "country": country,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "limit": limit,
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            return []

        tracks_raw = data.get("tracks", {}).get("track", [])
        if not tracks_raw:
            return []

        tracks = []
        for i, t in enumerate(tracks_raw[:limit], 1):
            tracks.append({
                "rank": i,
                "name": t.get("name", "Unknown"),
                "artist": t.get("artist", {}).get("name", "Unknown"),
                "country": country.title(),
            })
        return tracks

    except requests.exceptions.RequestException:
        return []
    except Exception:
        return []


def log_to_csv(track_data_list):
    """Appends weekly findings to global_track_history.csv."""
    filename = "global_track_history.csv"
    file_exists = os.path.isfile(filename)

    try:
        with open(filename, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Date", "Country", "Rank", "Artist", "Track"])
            date_str = datetime.now().strftime("%Y-%m-%d")
            for t in track_data_list:
                writer.writerow([date_str, t["country"], t["rank"], t["artist"], t["name"]])
        print(f"📄 Logged {len(track_data_list)} tracks to {filename}")
        return True
    except IOError as e:
        print(f"❌ Failed to write CSV: {e}")
        return False


def main():
    all_tracks = []
    total = len(COUNTRIES)
    print(f"Scanning {total} countries via Last.fm...\n")

    for i, country in enumerate(COUNTRIES, 1):
        tracks = get_top_tracks_for_country(country, limit=5)
        if tracks:
            all_tracks.extend(tracks)
            print(f"✅ [{i:3d}/{total}] {country.title():30s} — {len(tracks)} tracks")
        else:
            print(f"⊘  [{i:3d}/{total}] {country.title():30s} — no data")
        time.sleep(0.1)

    if not all_tracks:
        print("\n❌ No tracks found. Check your LASTFM_API_KEY.")
        exit(1)

    print(f"\n✅ Total tracks collected: {len(all_tracks)}")
    if not log_to_csv(all_tracks):
        exit(1)
    print("✨ Done.")


if __name__ == "__main__":
    main()
