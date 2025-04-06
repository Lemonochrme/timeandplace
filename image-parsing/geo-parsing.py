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
    "User-Agent": "TimeAndPlaceBot/1.0 (https://yourdomain.example; contact@example.com)"
}

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

def get_images_near_location(lat, lon, radius_km=10, limit=30, start_year=None, end_year=None):
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

        # Coords
        lat_page = page.get("coordinates", [{}])[0].get("lat", lat)
        lon_page = page.get("coordinates", [{}])[0].get("lon", lon)

        # Date
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

        # Description
        description = metadata.get("ImageDescription", {}).get("value", "").strip()

        # Credits
        author = metadata.get("Artist", {}).get("value", "").strip()
        license_name = metadata.get("LicenseShortName", {}).get("value", "CC BY-SA")
        license_url = metadata.get("LicenseUrl", {}).get("value", "")
        credits = f"{author} / Wikimedia Commons / {license_name}"
        if license_url:
            credits += f" ({license_url})"

        # Image
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
            "credits": credits
        })

    return images

if __name__ == "__main__":
    lat = 48.8566
    lon = 2.3522
    images = get_images_near_location(lat, lon, radius_km=10, limit=20, start_year=1990, end_year=2022)

    with open("images_metadata_world.json", "w", encoding="utf-8") as f:
        json.dump(images, f, indent=2, ensure_ascii=False)

    print("✅ Metadata saved to images_metadata_world.json")
