# demographic-dj

Automated weekly scanner that collects the top 5 tracks from Spotify charts across 60+ countries and logs them to a historical CSV.

## What This Does

Every week (Sunday 00:00 UTC), GitHub Actions:
1. Fetches data from Spotify's public charts endpoint (no authentication required)
2. Collects the top 5 tracks from available country charts
3. Appends them to `global_track_history.csv` with date, country, artist, and track name
4. Commits the updated CSV back to the repo

The resulting CSV is a time-series snapshot of global streaming demographics — what's topping charts everywhere, region by region.

## Setup

### 1. Clone the Repo (If You Haven't Already)

```bash
git clone https://github.com/bhaley1/demographic-dj.git
cd demographic-dj
```

### 2. No API Credentials Needed

Unlike the previous version, this uses Spotify's **public charts endpoint** which requires no authentication. You don't need to set up any GitHub secrets.

### 3. Local Testing (Optional)

To test locally before the workflow runs:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the scan
python main.py
```

This will create/update `global_track_history.csv` locally.

## What Changed From the Previous Version

### Authentication
- **Before:** Required Spotify API credentials (Client ID, Client Secret). Endpoints blocked access without user auth.
- **After:** Uses Spotify's public charts endpoint at `https://charts.spotify.com/`. No authentication needed.

### Country Support
- **Before:** Attempted to scan all 250 countries via Spotify's "Top 50" playlists. Most were inaccessible (401 errors).
- **After:** Scans 60+ countries with actual Spotify chart data available. Country list is curated and maintainable.

### Error Handling
- **Before:** Crashed on auth failures.
- **After:** Gracefully skips countries with no chart data.

### Dependencies
- **Before:** `spotipy` (Spotify SDK), `requests`, `python-dotenv`
- **After:** `requests` (HTTP), `python-dotenv` (for future extensibility)

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
- `Country Code` — ISO country code (US, GB, CA, etc.)
- `Country Name` — Full country name
- `Artist` — Track artist
- `Track Name` — Song title
- `Rank` — Position on the chart

Example rows:
```
2026-06-01,US,United States,Taylor Swift,Anti-Hero,1
2026-06-01,GB,United Kingdom,Olivia Rodrigo,vampire,2
2026-06-01,CA,Canada,The Weeknd,Blinding Lights,3
```

## Troubleshooting

**"No tracks found across all countries"**
- Spotify's charts endpoint may be temporarily unavailable
- Try running the workflow manually via the Actions tab
- Check if `requests` library is installed correctly

**Workflow doesn't run on schedule**
- GitHub Actions requires at least one commit on the default branch in the past 60 days to keep scheduled workflows active
- You can manually trigger via "Run workflow" in the Actions tab

**CSV file not created on first run**
- The script creates the file automatically. If it doesn't appear, check the Actions log for errors.

## Supported Countries

The script currently supports 60+ countries with available Spotify chart data:

US, GB, CA, AU, NZ, DE, FR, IT, ES, NL, BE, AT, CH, SE, NO, DK, FI, PL, CZ, HU, RO, PT, GR, IE, MX, BR, AR, CL, CO, PE, JP, KR, CN, IN, ID, TH, VN, PH, MY, SG, RU, UA, TR, ZA, EG, IL, SA, AE, HK, TW, EC, VE, UY, PY, CR, PA, DO, JM, TT, BS, PR, IS, LU, HR, BA, RS, BG, SI, SK, LT, LV, EE, CY, MT, LB, OM, KW, QA, BH, MA, TN, KE, NG, GH, UG, TZ, PK, BD, LK, NP, KH, LA, MM, TL, BN, MV

To add more countries or modify the list, edit the `COUNTRY_CODE_MAP` in `main.py`.

## Future Enhancements

- **Playlist creation:** Build a curated playlist from the weekly chart data
- **Filtering:** Aggregate by region, genre, or language
- **Database:** Store in PostgreSQL/SQLite for faster queries
- **Visualization:** Create charts showing global music trends over time
- **Notifications:** Alert when a track goes viral across regions
