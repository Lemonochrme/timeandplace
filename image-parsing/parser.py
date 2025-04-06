import requests
import os
import json
from urllib.parse import urlparse
from pathlib import Path

OUTPUT_DIR = "images"
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "TimeAndPlaceBot/1.0"
}

def sanitize_filename(url):
    return os.path.basename(urlparse(url).path)

def get_images_from_category(category, limit=10):
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

            year = None
            if "DateTimeOriginal" in metadata:
                year = metadata["DateTimeOriginal"]["value"][:4]
            else:
                for meta in exif:
                    if meta.get("name") == "DateTimeOriginal":
                        year = meta["value"][:4]

            img_url = info.get("url")
            if not img_url:
                continue

            filename = sanitize_filename(img_url)
            local_path = os.path.join(OUTPUT_DIR, filename)

            if lat and lon and year and year.isdigit():
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
                    "year": int(year)
                })

    return results

if __name__ == "__main__":
    category = "Cape_Town"
    images_data = get_images_from_category(category, limit=1)

    with open("images_metadata.json", "w", encoding="utf-8") as f:
        json.dump(images_data, f, indent=2)
    print("✅ Metadata saved to images_metadata.json")
