import os
import json
import re
import unicodedata
from pathlib import Path
from difflib import get_close_matches

# Load title DB
with open("EE.en.json", "r", encoding="utf-8") as f:
    title_db = json.load(f)

# Normalize title names for matching
def normalize_title(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')  # remove accents
    text = re.sub(r'[^a-zA-Z0-9 ]', '', text).lower()  # remove punctuation and lowercase
    return ' '.join(text.split())  # normalize whitespace

# Create a normalized mapping of game name -> title ID
title_map = {}
normalized_title_map = {}
for entry in title_db.values():
    name = entry.get("name")
    tid = entry.get("id")
    if name and tid:
        title_map[name.strip()] = tid.strip()
        normalized_title_map[normalize_title(name)] = tid.strip()

# Fuzzy match game name to title ID using normalized names
def get_title_id(game_name):
    if not game_name:
        return None

    norm_query = normalize_title(game_name)

    # Exact match
    if norm_query in normalized_title_map:
        return normalized_title_map[norm_query]

    # Substring match (e.g., "Atelier Sophie 2" in "Atelier Sophie 2: The Alchemist of the Mysterious Dream")
    for title_key in normalized_title_map.keys():
        if norm_query in title_key:
            return normalized_title_map[title_key]

    # Fuzzy fallback
    matches = get_close_matches(norm_query, normalized_title_map.keys(), n=1, cutoff=0.5)
    if matches:
        return normalized_title_map[matches[0]]

    return None

# Update all .pchtxt files in formatted/
def update_pchtxt_headers(formatted_dir):
    formatted_path = Path(formatted_dir)
    if not formatted_path.exists():
        print(f"❌ Directory not found: {formatted_dir}")
        return

    for game_folder in formatted_path.iterdir():
        if not game_folder.is_dir() or " - Graphics Mods" not in game_folder.name:
            continue

        game_name = game_folder.name.replace(" - Graphics Mods", "").strip()
        if not game_name:
            print(f"⚠️ Could not extract game name from folder: {game_folder.name}")
            continue

        title_id = get_title_id(game_name)
        if not title_id:
            print(f"❌ Title ID not found for: {game_name}")
            continue

        for pchtxt in game_folder.glob("*.pchtxt"):
            try:
                with open(pchtxt, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # Replace or insert title ID in header line
                updated = False
                for i, line in enumerate(lines):
                    if line.startswith("#"):
                        if "[" in line and "]" in line:
                            lines[i] = f"# {game_name} [{title_id}]\n"
                        else:
                            lines[i] = line.strip() + f" [{title_id}]\n"
                        updated = True
                        break

                if not updated:
                    lines.insert(1, f"# {game_name} [{title_id}]\n")

                with open(pchtxt, "w", encoding="utf-8") as f:
                    f.writelines(lines)

                print(f"✅ Updated: {pchtxt.name} with [{title_id}]")
            except Exception as e:
                print(f"❌ Error processing {pchtxt.name}: {e}")

# Run it
update_pchtxt_headers("formatted")
