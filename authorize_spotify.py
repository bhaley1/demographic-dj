"""
Run this once locally to authorize Spotify and capture your refresh token.
After running this, copy the refresh token into your GitHub secrets.

Usage:
    python authorize_spotify.py
"""

import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

client_id = os.getenv("SPOTIPY_CLIENT_ID", "").strip()
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET", "").strip()
redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback").strip()

if not client_id or not client_secret:
    print("❌ Missing SPOTIPY_CLIENT_ID or SPOTIPY_CLIENT_SECRET in your .env file")
    exit(1)

SCOPE = "playlist-modify-public playlist-modify-private"

auth_manager = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=SCOPE,
    cache_path=".cache",
    open_browser=False,
)

print("\n--- Spotify One-Time Authorization ---\n")
print("Step 1: Go to this URL in your browser:\n")
print(auth_manager.get_authorize_url())
print("\nStep 2: After authorizing, you'll be redirected to a URL that looks like:")
print("  http://localhost:8888/callback?code=AQD...\n")
print("Step 3: Paste that full URL here:")

response_url = input("> ").strip()

# Exchange the code for tokens
code = auth_manager.parse_response_code(response_url)
token_info = auth_manager.get_access_token(code)

refresh_token = token_info["refresh_token"]

print("\n✅ Authorization successful!")
print("\n--- YOUR REFRESH TOKEN ---")
print(refresh_token)
print("--------------------------")
print("\nNext steps:")
print("1. Copy the refresh token above")
print("2. Go to your GitHub repo → Settings → Secrets and variables → Actions")
print("3. Add a new secret named: SPOTIPY_REFRESH_TOKEN")
print("4. Paste the refresh token as the value")
print("5. Also add SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET if not already there")
print("\nOnce that's done, the weekly workflow will create playlists automatically.")
