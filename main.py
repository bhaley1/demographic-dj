import os
import csv
import time
from datetime import datetime
import requests
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Setup & Authentication
load_dotenv()

# Client credentials flow — no user interaction needed, works in CI
client_id = os.getenv("SPOTIPY_CLIENT_ID", "").strip()
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET", "").strip()

if not client_id or not client_secret:
    print("❌ Missing SPOTIPY_CLIENT_ID or SPOTIPY_CLIENT_SECRET")
    exit(1)

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=client_id,
    client_secret=client_secret
))


def get_all_countries():
    """
    Fetches all countries from REST Countries API.
    Falls back to a curated list if the API is unavailable.
    """
    print("--- Fetching global country list ---")
    url = "https://restcountries.com/v3.1/all?fields=name"
    
    # Curated list of countries with known Spotify charts
    fallback_countries = [
        "United States", "United Kingdom", "Canada", "Australia", "New Zealand",
        "Germany", "France", "Italy", "Spain", "Netherlands",
        "Belgium", "Austria", "Switzerland", "Sweden", "Norway",
        "Denmark", "Finland", "Poland", "Czech Republic", "Hungary",
        "Romania", "Portugal", "Greece", "Ireland", "Mexico",
        "Brazil", "Argentina", "Chile", "Colombia", "Peru",
        "Japan", "South Korea", "China", "India", "Indonesia",
        "Thailand", "Vietnam", "Philippines", "Malaysia", "Singapore",
        "Russia", "Ukraine", "Turkey", "South Africa", "Egypt",
        "Israel", "Saudi Arabia", "United Arab Emirates", "Hong Kong", "Taiwan"
    ]
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, list):
            countries = [c['name']['common'] for c in data]
            print(f"✅ Fetched {len(countries)} countries from API")
            return countries
        else:
            print(f"⚠️  Unexpected API response format, using fallback list")
            return fallback_countries
    except requests.exceptions.RequestException as e:
        print(f"⚠️  API Error: {e}, using fallback list of {len(fallback_countries)} countries")
        return fallback_countries


def get_top_tracks_for_country(country_name, limit=5):
    """
    Finds the official 'Top 50' playlist for a country and returns the top N tracks.
    Returns empty list if the playlist is not found or inaccessible.
    """
    try:
        query = f"Top 50 {country_name} official"
        results = sp.search(q=query, type='playlist', limit=1)
        
        if not results.get('playlists', {}).get('items'):
            return []

        playlist_id = results['playlists']['items'][0]['id']
        
        # Fetch tracks from the playlist
        tracks = sp.playlist_items(playlist_id, limit=limit)
        
        track_data = []
        for item in tracks.get('items', []):
            if item.get('track') and item['track'].get('uri'):
                try:
                    track_data.append({
                        'uri': item['track']['uri'],
                        'name': item['track'].get('name', 'Unknown'),
                        'artist': item['track'].get('artists', [{}])[0].get('name', 'Unknown'),
                        'country': country_name
                    })
                except (KeyError, IndexError):
                    continue
        
        return track_data
    except spotipy.exceptions.SpotifyException as e:
        # 403 Forbidden, 404 Not Found, etc. — just skip this country
        return []
    except Exception as e:
        print(f"⚠️  Unexpected error for {country_name}: {e}")
        return []


def log_to_csv(track_data_list):
    """Logs the weekly findings to a historical CSV file."""
    filename = "global_track_history.csv"
    file_exists = os.path.isfile(filename)
    
    try:
        with open(filename, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Date", "Country", "Artist", "Track Name", "URI"])
                
            date_str = datetime.now().strftime("%Y-%m-%d")
            for track in track_data_list:
                writer.writerow([
                    date_str,
                    track['country'],
                    track['artist'],
                    track['name'],
                    track['uri']
                ])
        print(f"📄 Logged {len(track_data_list)} tracks to {filename}")
        return True
    except IOError as e:
        print(f"❌ Failed to write CSV: {e}")
        return False


def main():
    countries = get_all_countries()
    all_track_data = []
    
    print(f"Scanning {len(countries)} countries for Spotify Charts...")

    for i, country in enumerate(countries, 1):
        try:
            tracks = get_top_tracks_for_country(country, limit=5)
            if tracks:
                all_track_data.extend(tracks)
                print(f"✅ [{i}/{len(countries)}] Gathered Top 5 from {country}")
            else:
                print(f"⊘ [{i}/{len(countries)}] No chart found for {country}")
            
            # Respect rate limits
            time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n⚠️  Scan interrupted by user")
            break
        except Exception as e:
            print(f"❌ [{i}/{len(countries)}] Error processing {country}: {e}")
            continue

    if not all_track_data:
        print("❌ No tracks found across all countries.")
        print("⚠️  Check that your Spotify API credentials are valid and have proper permissions.")
        exit(1)

    print(f"\n✅ Total tracks collected: {len(all_track_data)}")
    
    # Log to CSV
    success = log_to_csv(all_track_data)
    
    if not success:
        exit(1)
    
    print("\n✨ Weekly scan complete. CSV updated.")


if __name__ == "__main__":
    main()
