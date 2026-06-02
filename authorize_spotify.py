"""
Run this once locally to authorize Spotify and capture your refresh token.
This version bypasses any cached token and forces fresh consent with the
correct playlist scopes.

Usage:
    python authorize_spotify.py
"""

import os
import requests
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("SPOTIPY_CLIENT_ID", "").strip()
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET", "").strip()
redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8888/callback").strip()

if not client_id or not client_secret:
    print("❌ Missing SPOTIPY_CLIENT_ID or SPOTIPY_CLIENT_SECRET in your .env file")
    exit(1)

SCOPE = "playlist-modify-public playlist-modify-private"

# Build the authorization URL manually — forces fresh consent every time
auth_params = {
    "client_id": client_id,
    "response_type": "code",
    "redirect_uri": redirect_uri,
    "scope": SCOPE,
    "show_dialog": "true",  # ALWAYS show the consent screen, never reuse
}
auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(auth_params)

print("\n--- Spotify One-Time Authorization (Fresh Consent) ---\n")
print("Step 1: Open this URL in your browser:\n")
print(auth_url)
print("\nStep 2: Approve the permissions. IMPORTANT — the screen should mention")
print("        editing your public and private playlists.")
print("\nStep 3: You'll be redirected to a 'site can't be reached' page.")
print("        Copy the FULL URL from the address bar and paste it here:\n")

response_url = input("> ").strip()

# Extract the authorization code from the redirect URL
parsed = urllib.parse.urlparse(response_url)
query = urllib.parse.parse_qs(parsed.query)

if "code" not in query:
    print("❌ No authorization code found in that URL. Make sure you copied the whole thing.")
    exit(1)

code = query["code"][0]

# Exchange the code for tokens
token_response = requests.post(
    "https://accounts.spotify.com/api/token",
    data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    },
)

if token_response.status_code != 200:
    print(f"❌ Token exchange failed: {token_response.status_code}")
    print(token_response.text)
    exit(1)

token_data = token_response.json()
refresh_token = token_data["refresh_token"]
granted_scope = token_data.get("scope", "(none returned)")

print("\n✅ Authorization successful!")
print(f"\n🔑 Scopes granted: {granted_scope}")

if "playlist-modify" not in granted_scope:
    print("\n⚠️  WARNING: The playlist-modify scope was NOT granted!")
    print("   This means the token still can't add tracks.")
    print("   Go to https://www.spotify.com/account/apps/ and remove the app,")
    print("   then run this script again.")
else:
    print("\n✅ Playlist edit scope confirmed — this token can add tracks.")

print("\n--- YOUR REFRESH TOKEN ---")
print(refresh_token)
print("--------------------------")
print("\nNext steps:")
print("1. Copy the refresh token above")
print("2. Paste it into your .env file after SPOTIPY_REFRESH_TOKEN=")
print("3. Also update the SPOTIPY_REFRESH_TOKEN secret on GitHub")
