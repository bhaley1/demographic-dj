# demographic-dj

Automated weekly scanner that collects the top 5 tracks from Spotify charts across ~250 countries and logs them to a historical CSV.

## What This Does

Every week (Sunday 00:00 UTC), GitHub Actions:
1. Scans Spotify's "Top 50" official charts across all countries
2. Extracts the top 5 tracks from each country's chart
3. Appends them to `global_track_history.csv` with date, artist, and track name
4. Commits the updated CSV back to the repo

The resulting CSV is a time-series snapshot of global streaming demographics — what's topping charts everywhere, region by region.

## Setup

### 1. Get Spotify API Credentials

Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard):
- Log in or create an account
- Create a new app
- Copy your **Client ID** and **Client Secret**

### 2. Set GitHub Secrets

In your repo, go to **Settings > Secrets and variables > Actions** and add:
- `SPOTIPY_CLIENT_ID` — your Client ID from Spotify
- `SPOTIPY_CLIENT_SECRET` — your Client Secret from Spotify

**Important:** When pasting secrets, make sure there are no trailing newlines or spaces.

### 3. Local Testing (Optional)

To test locally before the workflow runs:

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and fill in your Spotify credentials
nano .env

# Install dependencies
pip install -r requirements.txt

# Run the scan
python main.py
```

This will create/update `global_track_history.csv` locally.

## What Changed From the Original

### Authentication
- **Before:** Used interactive OAuth flow (`SpotifyOAuth`) with browser redirect. Impossible in CI.
- **After:** Uses client credentials flow (`SpotifyClientCredentials`). Works headless. No browser needed.

### Secrets Handling
- **Before:** Secrets weren't stripped, so trailing newlines caused malformed API requests.
- **After:** Secrets are explicitly `.strip()`'d before use.

### Error Handling
- **Before:** Script would hang on auth, then crash on missing CSV file.
- **After:** Graceful fallbacks — if REST Countries API is down, uses a curated list of countries. If a country's chart doesn't exist, skips it. Returns proper exit codes.

### Playlist Creation
- **Before:** Attempted to create a new Spotify playlist each week (needs user auth).
- **After:** Removed from CI. The script now *only* collects data and logs to CSV. You can manually create/update playlists from the CSV if you want, or extend the script later with a separate manual step that runs locally with user credentials.

### Logging & Debugging
- Added progress counters (`[N/250]`) so you can see the scan progress.
- Better error messages if Spotify API credentials are missing or invalid.
- Clearer output distinguishing between successful grabs, skipped countries, and errors.

## Workflow Schedule

The workflow runs on a schedule defined in `.github/workflows/update_playlist.yml`:

```yaml
on:
  schedule:
    - cron: '0 0 * * 0'  # Every Sunday at 00:00 UTC
  workflow_dispatch:     # Manual trigger available
```

You can adjust the cron expression to run on a different schedule, or click "Run workflow" in the Actions tab to trigger it manually.

## Data Structure

`global_track_history.csv` has columns:
- `Date` — YYYY-MM-DD when the scan ran
- `Country` — Country name
- `Artist` — Track artist
- `Track Name` — Song title
- `URI` — Spotify URI (can be used to embed/link tracks)

Example row:
```
2026-06-01,Iceland,Kaytranada,Well Kept Secret,spotify:track:1a2b3c...
```

## Troubleshooting

**"Missing SPOTIPY_CLIENT_ID or SPOTIPY_CLIENT_SECRET"**
- Check that the secrets are set in GitHub Settings > Secrets
- Make sure the names match exactly (case-sensitive)

**"No tracks found across all countries"**
- Your API credentials may be invalid or revoked
- Try running locally with `.env` to isolate the issue

**Workflow doesn't run on schedule**
- GitHub Actions requires at least one commit on the default branch in the past 60 days to keep scheduled workflows active
- You can manually trigger via "Run workflow" in the Actions tab

**"fatal: pathspec 'global_track_history.csv' did not match any files"**
- This was the original error. Should be fixed now. If it resurfaces, the scan likely returned 0 tracks (check Spotify API credentials).

## Future Enhancements

- **Playlist creation from CSV:** Add a separate script that reads the CSV and creates a curated playlist
- **Filtering:** Aggregate by region, genre, or language
- **Database:** Store in a proper database instead of CSV for faster queries
- **Visualization:** Create charts showing which countries have overlapping top tracks
