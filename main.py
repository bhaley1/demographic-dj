import os
import csv
import time
from datetime import datetime
import requests
from dotenv import load_dotenv

# Setup
load_dotenv()

# Mapping of country names to Spotify chart country codes
COUNTRY_CODE_MAP = {
    "United States": "US",
    "United Kingdom": "GB",
    "Canada": "CA",
    "Australia": "AU",
    "New Zealand": "NZ",
    "Germany": "DE",
    "France": "FR",
    "Italy": "IT",
    "Spain": "ES",
    "Netherlands": "NL",
    "Belgium": "BE",
    "Austria": "AT",
    "Switzerland": "CH",
    "Sweden": "SE",
    "Norway": "NO",
    "Denmark": "DK",
    "Finland": "FI",
    "Poland": "PL",
    "Czech Republic": "CZ",
    "Hungary": "HU",
    "Romania": "RO",
    "Portugal": "PT",
    "Greece": "GR",
    "Ireland": "IE",
    "Mexico": "MX",
    "Brazil": "BR",
    "Argentina": "AR",
    "Chile": "CL",
    "Colombia": "CO",
    "Peru": "PE",
    "Japan": "JP",
    "South Korea": "KR",
    "China": "CN",
    "India": "IN",
    "Indonesia": "ID",
    "Thailand": "TH",
    "Vietnam": "VN",
    "Philippines": "PH",
    "Malaysia": "MY",
    "Singapore": "SG",
    "Russia": "RU",
    "Ukraine": "UA",
    "Turkey": "TR",
    "South Africa": "ZA",
    "Egypt": "EG",
    "Israel": "IL",
    "Saudi Arabia": "SA",
    "United Arab Emirates": "AE",
    "Hong Kong": "HK",
    "Taiwan": "TW",
    "Ecuador": "EC",
    "Venezuela": "VE",
    "Uruguay": "UY",
    "Paraguay": "PY",
    "Costa Rica": "CR",
    "Panama": "PA",
    "Dominican Republic": "DO",
    "Jamaica": "JM",
    "Trinidad and Tobago": "TT",
    "Bahamas": "BS",
    "Puerto Rico": "PR",
    "Iceland": "IS",
    "Luxembourg": "LU",
    "Croatia": "HR",
    "Bosnia and Herzegovina": "BA",
    "Serbia": "RS",
    "Bulgaria": "BG",
    "Slovenia": "SI",
    "Slovakia": "SK",
    "Lithuania": "LT",
    "Latvia": "LV",
    "Estonia": "EE",
    "Cyprus": "CY",
    "Malta": "MT",
    "Lebanon": "LB",
    "Oman": "OM",
    "Kuwait": "KW",
    "Qatar": "QA",
    "Bahrain": "BH",
    "Morocco": "MA",
    "Tunisia": "TN",
    "Kenya": "KE",
    "Nigeria": "NG",
    "Ghana": "GH",
    "Uganda": "UG",
    "Tanzania": "TZ",
    "Pakistan": "PK",
    "Bangladesh": "BD",
    "Sri Lanka": "LK",
    "Nepal": "NP",
    "Cambodia": "KH",
    "Laos": "LA",
    "Myanmar": "MM",
    "Timor-Leste": "TL",
    "Brunei": "BN",
    "Maldives": "MV",
}


def get_top_tracks_for_country(country_code, limit=5):
    """
    Fetches top tracks from Spotify's public charts endpoint.
    No authentication required.
    """
    try:
        url = f"https://charts.spotify.com/charts/top-200-{country_code}/latest/download"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse CSV response
        lines = response.text.strip().split('\n')
        tracks = []
        
        # Skip header row, take up to 'limit' rows
        for line in lines[1:limit+1]:
            parts = line.split(',')
            if len(parts) >= 3:
                try:
                    tracks.append({
                        'rank': parts[0],
                        'name': parts[1].strip(),
                        'artist': parts[2].strip(),
                        'country_code': country_code
                    })
                except (IndexError, AttributeError):
                    continue
        
        return tracks
    except requests.exceptions.HTTPError:
        # 404 or other HTTP error — country code not valid for charts
        return []
    except Exception as e:
        return []


def get_supported_countries():
    """
    Returns a list of countries with Spotify chart data available.
    This is a curated list of supported country codes.
    """
    return list(COUNTRY_CODE_MAP.items())


def log_to_csv(track_data_list):
    """Logs the weekly findings to a historical CSV file."""
    filename = "global_track_history.csv"
    file_exists = os.path.isfile(filename)
    
    try:
        with open(filename, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(["Date", "Country Code", "Country Name", "Artist", "Track Name", "Rank"])
                
            date_str = datetime.now().strftime("%Y-%m-%d")
            for track in track_data_list:
                # Reverse lookup country name from code
                country_name = [name for name, code in COUNTRY_CODE_MAP.items() if code == track['country_code']]
                country_name = country_name[0] if country_name else "Unknown"
                
                writer.writerow([
                    date_str,
                    track['country_code'],
                    country_name,
                    track['artist'],
                    track['name'],
                    track.get('rank', '')
                ])
        print(f"📄 Logged {len(track_data_list)} tracks to {filename}")
        return True
    except IOError as e:
        print(f"❌ Failed to write CSV: {e}")
        return False


def main():
    countries = get_supported_countries()
    all_track_data = []
    
    print(f"Scanning {len(countries)} countries for Spotify Charts...")
    print("(Using Spotify's public charts endpoint — no API auth required)\n")

    for i, (country_name, country_code) in enumerate(countries, 1):
        try:
            tracks = get_top_tracks_for_country(country_code, limit=5)
            if tracks:
                all_track_data.extend(tracks)
                print(f"✅ [{i:3d}/{len(countries)}] {country_name:20s} — {len(tracks)} tracks")
            else:
                print(f"⊘ [{i:3d}/{len(countries)}] {country_name:20s} — no chart data")
            
            # Small delay to avoid hammering the endpoint
            time.sleep(0.05)
        except KeyboardInterrupt:
            print("\n⚠️  Scan interrupted by user")
            break
        except Exception as e:
            print(f"❌ [{i:3d}/{len(countries)}] {country_name} — error: {e}")
            continue

    if not all_track_data:
        print("\n❌ No tracks found across all countries.")
        print("⚠️  Spotify charts endpoint may be unavailable.")
        exit(1)

    print(f"\n✅ Total tracks collected: {len(all_track_data)}")
    
    # Log to CSV
    success = log_to_csv(all_track_data)
    
    if not success:
        exit(1)
    
    print("\n✨ Weekly scan complete. CSV updated.")


if __name__ == "__main__":
    main()
