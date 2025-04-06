import requests
import os
import json
from pathlib import Path
from urllib.parse import urlparse
import re
import time

OUTPUT_DIR = "images"
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "TimeAndPlaceBot/1.0"
}

CITIES = [
    {"name": "Paris", "lat": 48.8566, "lon": 2.3522},
    {"name": "New York", "lat": 40.7128, "lon": -74.0060},
    {"name": "London", "lat": 51.5074, "lon": -0.1278},
    {"name": "Tokyo", "lat": 35.6895, "lon": 139.6917},
    {"name": "Sydney", "lat": -33.8688, "lon": 151.2093},
    {"name": "Rio de Janeiro", "lat": -22.9068, "lon": -43.1729},
    {"name": "Cairo", "lat": 30.0444, "lon": 31.2357},
    {"name": "Cape Town", "lat": -33.9249, "lon": 18.4241},
    {"name": "Moscow", "lat": 55.7558, "lon": 37.6176},
    {"name": "Beijing", "lat": 39.9042, "lon": 116.4074},
    {"name": "Berlin", "lat": 52.5200, "lon": 13.4050},
    {"name": "Madrid", "lat": 40.4168, "lon": -3.7038},
    {"name": "Rome", "lat": 41.9028, "lon": 12.4964},
    {"name": "Bangkok", "lat": 13.7563, "lon": 100.5018},
    {"name": "Los Angeles", "lat": 34.0522, "lon": -118.2437},
    {"name": "Toronto", "lat": 43.6510, "lon": -79.3470}
]

def sanitize_filename(url):
    return os.path.basename(urlparse(url).path)

def extract_date(value):
    match = re.match(r"(\d{4})([-:]?)(\d{2})?([-:]?)(\d{2})?", value)
    if match:
        year = match.group(1)
        month = match.group(3) or "01"
        day = match.group(5) or "01"
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}", int(year)
    return None, None

def get_images_near_location(city, radius_km=10, limit=30, start_year=None, end_year=None):
    lat = city["lat"]
    lon = city["lon"]
    name = city["name"]

    print(f"🔍 Fetching images near {name}...")

    endpoint = "https://commons.wikimedia.org/w/api.php"
    images = []

    params = {
        "action": "query",
        "generator": "geosearch",
        "ggscoord": f"{lat}|{lon}",
        "ggsradius": radius_km * 1000,
        "ggslimit": limit,
        "ggsnamespace": 6,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|metadata",
        "format": "json",
        "formatversion": 2
    }

    response = requests.get(endpoint, headers=HEADERS, params=params)
    data = response.json()

    if "query" not in data:
        return []

    for page in data["query"]["pages"]:
        imageinfo = page.get("imageinfo", [])
        if not imageinfo:
            continue

        info = imageinfo[0]
        metadata = info.get("extmetadata", {})
        exif = info.get("metadata", [])

        lat_page = page.get("coordinates", [{}])[0].get("lat", lat)
        lon_page = page.get("coordinates", [{}])[0].get("lon", lon)

        date_raw = metadata.get("DateTimeOriginal", {}).get("value", "")
        if not date_raw:
            for meta in exif:
                if meta.get("name") == "DateTimeOriginal":
                    date_raw = meta.get("value", "")
                    break

        full_date, year = extract_date(date_raw or "")
        if not year:
            continue
        if start_year and year < start_year:
            continue
        if end_year and year > end_year:
            continue

        description = metadata.get("ImageDescription", {}).get("value", "").strip()

        author = metadata.get("Artist", {}).get("value", "").strip()
        license_name = metadata.get("LicenseShortName", {}).get("value", "CC BY-SA")
        license_url = metadata.get("LicenseUrl", {}).get("value", "")
        credits = f"{author} / Wikimedia Commons / {license_name}"
        if license_url:
            credits += f" ({license_url})"

        img_url = info.get("url")
        if not img_url:
            continue

        filename = sanitize_filename(img_url)
        local_path = os.path.join(OUTPUT_DIR, filename)

        if not os.path.exists(local_path):
            try:
                img_response = requests.get(img_url, stream=True, headers=HEADERS)
                if img_response.status_code == 200:
                    with open(local_path, "wb") as f:
                        for chunk in img_response.iter_content(1024):
                            f.write(chunk)
                    print(f"✅ Downloaded: {filename}")
                else:
                    print(f"⚠️ Failed to download {filename}: {img_response.status_code}")
                    continue
            except Exception as e:
                print(f"❌ Error downloading {filename}: {e}")
                continue

        images.append({
            "filename": filename,
            "lat": float(lat_page),
            "lng": float(lon_page),
            "year": year,
            "date": full_date if full_date else str(year),
            "description": description,
            "credits": credits,
            "city": name
        })

    return images

if __name__ == "__main__":
    start_year = 1900
    end_year = 2025
    total_images = []

    for city in CITIES:
        try:
            images = get_images_near_location(city, radius_km=10, limit=30, start_year=start_year, end_year=end_year)
            total_images.extend(images)
            time.sleep(1)  # Respecte l'API
        except Exception as e:
            print(f"Erreur avec la ville {city['name']}: {e}")

    with open("images_metadata_global.json", "w", encoding="utf-8") as f:
        json.dump(total_images, f, indent=2, ensure_ascii=False)

    print(f"✅ {len(total_images)} images sauvegardées dans images_metadata_global.json")
