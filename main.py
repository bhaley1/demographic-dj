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

# Required scope for playlist management in 2026
SCOPE = "playlist-modify-public"

# Updated to prevent terminal "flashing" by forcing a manual URL copy/paste
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope=SCOPE,
    cache_path=".cache",
    open_browser=False  # Crucial: This forces the terminal to show the login link
))

def get_all_countries():
    """
    Fetches country list with 'fields' filter to prevent 2026 API TypeErrors.
    """
    print("--- Fetching global country list ---")
    url = "https://restcountries.com/v3.1/all?fields=name"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if isinstance(data, list):
            return [c['name']['common'] for c in data]
        else:
            print(f"⚠️ API Warning: Falling back to default country list.")
            return ["USA", "United Kingdom", "Iceland", "Canada", "Germany", "Japan"]
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return ["USA", "United Kingdom", "Iceland", "Canada", "Germany", "Japan"]

def get_top_tracks_for_country(country_name, limit=5):
    """
    Finds 'Top 50' playlists and extracts track metadata.
    """
    query = f"Top 50 {country_name} official"
    results = sp.search(q=query, type='playlist', limit=1)
    
    if not results['playlists']['items']:
        return []

    playlist_id = results['playlists']['items'][0]['id']
    
    # Satisfies 2026 'additional_types' requirement
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
    """Saves track history to local CSV."""
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
    
    print(f"Scanning {len(countries)} countries...")

    for country in countries:
        try:
            tracks = get_top_tracks_for_country(country, limit=5)
            if tracks:
                all_track_data.extend(tracks)
                print(f"✅ Found tracks for {country}")
            
            time.sleep(0.1) # Small delay to avoid 429 Rate Limiting
        except Exception:
            continue

    if not all_track_data:
        print("❌ No tracks retrieved. Check User Management whitelist.")
        return

    log_to_csv(all_track_data)

    unique_track_uris = list(set([t['uri'] for t in all_track_data]))
    date_str = datetime.now().strftime("%b %d, %Y")
    
    print(f"Creating Global Playlist: {date_str}...")
    
    try:
        # Uses current_user endpoint for 2026 dashboard permissions
        playlist = sp.current_user_playlist_create(
            name=f"Global Top 5s - {date_str
