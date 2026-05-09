import os
import csv
import time
from datetime import datetime
import requests
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# 1. Setup & Authentication
load_dotenv()

# Required scope for creating and modifying playlists in 2026
SCOPE = "playlist-modify-public"

# Initialize Spotify client with manual browser override
# This prevents the "flashing" screen by printing a manual login link in the terminal
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope=SCOPE,
    cache_path=".cache",
    open_browser=False
))

def get_all_countries():
    """
    Fetches all countries from REST Countries API.
    Uses 'fields' parameter to comply with 2026 API requirements.
    """
    print("--- Fetching global country list ---")
    url = "https://restcountries.com/v3.1/all?fields=name"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if isinstance(data, list):
            return [c['name']['common'] for c in data]
        else:
            print(f"⚠️ API Error: {data.get('message', 'Unknown response format')}")
            return ["USA", "United Kingdom", "Iceland", "Canada", "Germany", "Japan"]
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return ["USA", "United Kingdom", "Iceland", "Canada", "Germany", "Japan"]

def get_top_tracks_for_country(country_name, limit=5):
    """
    Finds the official 'Top 50' playlist for a country and returns the top 5 tracks.
    Updated for 2026 endpoint requirements.
    """
    query = f"Top 50 {country_name} official"
    results = sp.search(q=query, type='playlist', limit=1)
    
    if not results['playlists']['items']:
        return []

    playlist_id = results['playlists']['items'][0]['id']
    
    # Use additional_types to satisfy 2026 requirement for playlist items
    tracks = sp.playlist_items(playlist_id, limit=limit, additional_types=['track'])
    
    track_data = []
    for item in tracks['items']:
        if item.get('track'):
            track_data.append({
                'uri': item['track']['uri'],
                'name': item['track']['name'],
                'artist': item['track']['artists'][0]['name'],
                'country': country_name
            })
    return track_data

def log_to_csv(track_data_list):
    """Logs the weekly findings to a historical CSV file."""
    filename = "global_track_history.csv"
    file_exists = os.path.isfile(filename)
    
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Date", "Country", "Artist", "Track Name", "URI"])
            
        date_str = datetime.now().strftime("%Y-%m-%d")
        for track in track_data_list:
            writer.writerow([date_str, track['country'], track['artist'], track['name'], track['uri']])
    print(f"📄 Logged {len(track_data_list)} tracks to {filename}")

def main():
    countries = get_all_countries()
    all_track_data = []
    
    print(f"Scanning {len(countries)} countries for Spotify Charts...")

    for country in countries:
        try:
            tracks = get_top_tracks_for_country(country, limit=5)
            if tracks:
                all_track_data.extend(tracks)
                print(f"✅ Gathered Top 5 from {country}")
            
            time.sleep(0.1) 
        except Exception:
            # Continues if a specific country chart is unavailable (403 or 404)
            continue

    if not all_track_data:
        print("❌ No tracks found. Verify User Management whitelist in the dashboard.")
        return

    log_to_csv(all_track_data)

    # Prepare and update the playlist
    unique_track_uris = list(set([t['uri'] for t in all_track_data]))
    date_str = datetime.now().strftime("%b %d, %Y")
    
    print(f"Creating new playlist: Global Top 5s - {date_str}...")
    
    try:
        # Use current_user_playlist_create for 2026 compatibility
        playlist = sp.current_user_playlist_create(
            name=f"Global Top 5s - {date_str}", 
            description=f"Automated Global Top 5s. Generated on {date_str}.",
            public=True
        )

        # Batch add tracks (Spotify limit is 100 per request)
        for i in range(0, len(unique_track_uris), 100):
            batch = unique_track_uris[i:i+100]
            sp.playlist_add_items(playlist['id'], items=batch)

        print(f"\n🚀 Success! Playlist '{playlist['name']}' is live on your profile.")
        
    except Exception as e:
        print(f"❌ Failed to create playlist: {e}")

if __name__ == "__main__":
    main()