import os
import json

images_folder = "images"
metadata_file = "images_metadata.json"

with open(metadata_file, "r", encoding="utf-8") as f:
    metadata = json.load(f)

new_metadata = []
for idx, item in enumerate(metadata, start=1):
    old_name = item["filename"]
    ext = os.path.splitext(old_name)[1]  # Garde l'extension
    new_name = f"image{idx}{ext}"

    old_path = os.path.join(images_folder, old_name)
    new_path = os.path.join(images_folder, new_name)

    if os.path.exists(old_path):
        os.rename(old_path, new_path)
        item["filename"] = new_name
    else:
        print(f"⚠️ Fichier introuvable : {old_path}")
    
    new_metadata.append(item)

with open(metadata_file, "w", encoding="utf-8") as f:
    json.dump(new_metadata, f, indent=2, ensure_ascii=False)

print("✅ Tous les fichiers ont été renommés et les métadonnées mises à jour.")
