import requests
import os
import json
from urllib.parse import urlparse
from pathlib import Path
import re

OUTPUT_DIR = "images"
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "TimeAndPlaceBot/1.0"
}

def sanitize_filename(url):
    return os.path.basename(urlparse(url).path)

def extract_date(value):
    # Gère formats comme : "2015:06:24 13:45:00" ou "2024-03-04"
    match = re.match(r"(\d{4})([-:]?)(\d{2})?([-:]?)(\d{2})?", value)
    if match:
        year = match.group(1)
        month = match.group(3) or "01"
        day = match.group(5) or "01"
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}", int(year)
    return None, None

def get_images_from_category(category, limit=20, start_year=None, end_year=None):
    endpoint = "https://commons.wikimedia.org/w/api.php"

    params = {
        "action": "query",
        "generator": "categorymembers",
        "gcmtitle": f"Category:{category}",
        "gcmtype": "file",
        "gcmlimit": limit,
        "prop": "imageinfo|coordinates",
        "iiprop": "url|extmetadata|metadata",
        "format": "json",
        "formatversion": 2
    }

    response = requests.get(endpoint, params=params, headers=HEADERS)
    data = response.json()

    results = []

    if "query" in data:
        for page in data["query"]["pages"]:
            imageinfo = page.get("imageinfo", [])
            if not imageinfo:
                continue

            info = imageinfo[0]
            metadata = info.get("extmetadata", {})
            exif = info.get("metadata", [])
            coords = page.get("coordinates", [])

            lat, lon = None, None
            if coords:
                lat = coords[0].get("lat")
                lon = coords[0].get("lon")

            # --- Extraction date complète ---
            date_raw = None
            if "DateTimeOriginal" in metadata:
                date_raw = metadata["DateTimeOriginal"]["value"]
            else:
                for meta in exif:
                    if meta.get("name") == "DateTimeOriginal":
                        date_raw = meta["value"]
                        break

            full_date, year = extract_date(date_raw or "")

            # Appliquer le filtre de date
            if not year:
                continue
            if start_year and year < start_year:
                continue
            if end_year and year > end_year:
                continue

            # --- Description ---
            description = metadata.get("ImageDescription", {}).get("value", "").strip()

            # --- Crédits ---
            author = metadata.get("Artist", {}).get("value", "").strip()
            license_name = metadata.get("LicenseShortName", {}).get("value", "CC BY-SA")
            license_url = metadata.get("LicenseUrl", {}).get("value", "")
            credits = f"{author} / Wikimedia Commons / {license_name}"
            if license_url:
                credits += f" ({license_url})"

            # --- Image ---
            img_url = info.get("url")
            if not img_url:
                continue

            filename = sanitize_filename(img_url)
            local_path = os.path.join(OUTPUT_DIR, filename)

            if lat and lon:
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

                results.append({
                    "filename": filename,
                    "lat": float(lat),
                    "lng": float(lon),
                    "year": int(year),
                    "date": full_date if full_date else str(year),
                    "description": description,
                    "credits": credits
                })

    return results

if __name__ == "__main__":
    category = "New_York_City"
    start_year = 1980
    end_year = 2024
    images_data = get_images_from_category(category, limit=100, start_year=start_year, end_year=end_year)

    with open("images_metadata.json", "w", encoding="utf-8") as f:
        json.dump(images_data, f, indent=2, ensure_ascii=False)

    print("✅ Metadata saved to images_metadata.json")
