#!/usr/bin/env python3
import os
import shutil
import re
import sys
import rarfile
import unicodedata

# ----- Normalization & Title‐Casing Helpers -----

def sanitize_name(name):
    """
    Remove accents and unwanted characters, replace ' - ' with a single space,
    remove extra quotes/apostrophes, collapse multiple spaces.
    """
    normalized = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    cleaned = normalized.replace("'", "").replace("’", "").replace("`", "").replace('"', "")
    cleaned = cleaned.replace(" - ", " ")
    cleaned = ' '.join(cleaned.split())
    return cleaned.strip()

def capitalize_hyphenated(word):
    """
    Capitalize both parts of a hyphenated word. E.g. "yooka-laylee" → "Yooka-Laylee".
    """
    parts = word.split('-')
    capitalized = []
    for part in parts:
        if part:
            capitalized.append(part[0].upper() + part[1:].lower() if len(part) > 1 else part.upper())
        else:
            capitalized.append('')
    return '-'.join(capitalized)

# Regex for Roman numerals (supports up to 3999)
ROMAN_NUMERAL_PATTERN = re.compile(
    r"^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$",
    re.IGNORECASE
)

# Known uppercase acronyms we want to preserve exactly
ACRONYMS = {
    "HD", "2D", "3D", "4K", "VR", "AI", "API", "USB", "CPU", "GPU", "DVD", "CD",
    "RPG", "FPS", "MMO", "MMORPG", "LAN", "GUI", "NPC", "FFVII", "FFVIII", "FX", "FFIX", "FFX", "FFXII", "2K", "V1", "V2", "V3", "V4"
}

def is_roman_numeral(word):
    """
    Return True if `word` is a valid Roman numeral (case‐insensitive).
    """
    return bool(ROMAN_NUMERAL_PATTERN.match(word))

def title_case_preserve_numbers(name):
    """
    Title‐case `name` with these rules:
      • Fully uppercase acronyms remain unchanged (e.g. HD, 2D, 3D, FFVII, etc.).
      • Roman numerals become fully uppercase (e.g. 'iii' → 'III', 'xI' → 'XI').
      • Hyphenated words are capitalized on both sides (→ 'Yooka-Laylee').
      • Small filler words (a, an, and, the, of, in, etc.) become lowercase
        only if they appear in the middle and are not immediately after a subtitle marker,
        except the first and last words (always capitalized).
      • After a subtitle marker (":", "~", "–", "—", or "-"), force capitalization
        on all subsequent words until the next subtitle marker or the end.
      • Compound Roman numerals joined by "&", "+", or "|" become fully uppercase
        (e.g. "I&ii" → "I&II").
    """
    lowercase_exceptions = {
        "a", "an", "and", "as", "at", "but", "by", "for", "from",
        "in", "nor", "of", "on", "or", "so", "the", "to", "with", "yet"
    }
    subtitle_markers = {":", "~", "-", "–", "—"}

    words = name.split()
    result = []
    force_capitalize_mode = False

    for idx, raw_word in enumerate(words):
        # Check if this raw_word contains any subtitle marker (to force‐caps afterward)
        contains_marker = any(marker in raw_word for marker in subtitle_markers)

        # Split on any subtitle marker but keep the markers themselves
        split_parts = re.split(r'([:~\-–—])', raw_word)
        compounded = []

        for part in split_parts:
            if part in subtitle_markers:
                # Keep the marker, then force‐capitalize subsequent parts
                compounded.append(part)
                force_capitalize_mode = True
                continue

            lower_part = part.lower()
            is_first = (idx == 0)
            is_last  = (idx == len(words) - 1)

            def cap_one(subword):
                # If it's an acronym, uppercase it
                if subword.upper() in ACRONYMS:
                    return subword.upper()
                # If it's a Roman numeral, uppercase it
                if is_roman_numeral(subword):
                    return subword.upper()
                # If it’s a compound Roman numeral joined by &, +, or |
                for sep in ("&", "+", "|"):
                    if sep in subword:
                        pieces = subword.split(sep)
                        if all(is_roman_numeral(p) for p in pieces):
                            return sep.join(p.upper() for p in pieces)
                # Otherwise just capitalize hyphenated segments
                return capitalize_hyphenated(subword)

            if force_capitalize_mode or is_first or is_last or (lower_part not in lowercase_exceptions):
                # Split hyphens, apply cap_one to each
                subs = part.split('-')
                compounded.append("-".join(cap_one(s) for s in subs))
            else:
                # Middle filler word → keep lowercase
                compounded.append(lower_part)

        result.append("".join(compounded))
        # If this raw_word did not contain a subtitle marker, exit force‐capitalize
        if not contains_marker:
            force_capitalize_mode = False

    # Finally, ALWAYS capitalize the very first and very last words (same rules)
    if result:
        first_split = result[0].split("-")
        new_first = []
        for p in first_split:
            if p.upper() in ACRONYMS or is_roman_numeral(p):
                new_first.append(p.upper())
            else:
                new_first.append(capitalize_hyphenated(p))
        result[0] = "-".join(new_first)

        last_split = result[-1].split("-")
        new_last = []
        for p in last_split:
            if p.upper() in ACRONYMS or is_roman_numeral(p):
                new_last.append(p.upper())
            else:
                new_last.append(capitalize_hyphenated(p))
        result[-1] = "-".join(new_last)

    return " ".join(result)

def clean_title(name):
    """
    Combine sanitize_name() + title_case_preserve_numbers() into one call.
    """
    return title_case_preserve_numbers(sanitize_name(name))

def transform_game_name_raw(raw_game):
    """
    Move ", The" to the front and remove any stray colons:
      e.g. "Skyrim, The" → "The Skyrim"
    """
    if ", The" in raw_game:
        parts = raw_game.split(", The")
        raw_game = f"The {parts[0]}{parts[1]}"
    raw_game = raw_game.replace(":", "")     # strip out colons
    raw_game = raw_game.replace(" - ", " ")   # remove literal “ - ”
    return raw_game

def extract_rar_files(folder_path):
    """
    Only extract top‐level archives matching "release_*.rar" in the root folder_path.
    Do NOT dive into subfolders (so we skip those tiny per‐mod RARs).
    """
    # We look at *only* the immediate children of `folder_path`.
    for item in os.listdir(folder_path):
        full = os.path.join(folder_path, item)
        if not os.path.isfile(full):
            continue

        # Only process those .rar that match "release_*.rar" at the top level
        if item.lower().startswith("release_") and item.lower().endswith(".rar"):
            try:
                with rarfile.RarFile(full) as rf:
                    rf.extractall(folder_path)
                print(f"Extracted top‐level archive: {full}")
            except rarfile.Error as e:
                print(f"❌ Failed to extract {full}: {e}")

def get_game_name_and_mod_name(path, root_dir):
    """
    Given a folder `path` containing a .pchtxt, return (game_name, mod_name).
    1) game_name ← first‐level folder under root_dir, strip bracketed tags, move ", The", 
       remove colons, possibly append "(Country)", then run clean_title(...).
    2) mod_name ← if 'Aspect Ratio' in path → "Aspect Ratio <foldername>"; 
       else if last folder ends in " v<digits>" → "<parent> <lastFolder>";
       else immediate parent folder.  
       Afterwards, replace ' / ` → ".", "21-9" → "21.9", remove colons, 
       handle "Trailblazers" → "4K", then run clean_title(...).
    """
    relative = os.path.relpath(path, root_dir)
    parts = relative.split(os.sep)

    # --- raw_game_name logic ---
    raw_game = parts[0]
    raw_game = re.sub(r'\[.*?\]', '', raw_game).strip()
    raw_game = transform_game_name_raw(raw_game)

    # check for country code deeper in path
    country = None
    for p in parts[1:]:
        if re.search(r'\[.*?\]', p):
            country = re.sub(r'\[.*?\]', '', p).strip()
            break
    if country:
        raw_game = f"{raw_game} ({country})"

    game_name = clean_title(raw_game)

    # --- raw_mod_name logic ---
    if "Aspect Ratio" in relative:
        aspect_folder = os.path.basename(path)
        raw_mod = f"Aspect Ratio {aspect_folder}"
    else:
        last_folder = parts[-1]
        if re.search(r' v\d+', last_folder):
            parent_folder = parts[-2]
            raw_mod = f"{parent_folder} {last_folder}"
        else:
            raw_mod = parts[-2] if len(parts) > 1 else ""

    raw_mod = raw_mod.strip()
    raw_mod = raw_mod.replace("'", ".").replace("`", ".")
    raw_mod = raw_mod.replace("21-9", "21.9")
    raw_mod = raw_mod.replace(":", "")
    if raw_mod == "Trailblazers":
        raw_mod = "4K"

    mod_name = clean_title(raw_mod) if raw_mod else ""
    return game_name, mod_name

def create_formatted_structure(folder_path):
    """
    1) extract_rar_files(folder_path)  # only top‐level releases
    2) walk every subfolder for .pchtxt
    3) for each .pchtxt, compute (game_name, mod_name) with get_game_name_and_mod_name
    4) copy into formatted/"<Game Name> - <Mod Name>"/"<version>.pchtxt"
    """
    extract_rar_files(folder_path)

    formatted_path = os.path.join(folder_path, "formatted")
    os.makedirs(formatted_path, exist_ok=True)

    for root, dirs, files in os.walk(folder_path):
        # Skip anything already under “formatted”
        if "formatted" in root.split(os.sep):
            continue

        for f in files:
            if not f.lower().endswith(".pchtxt"):
                continue

            game_name, mod_name = get_game_name_and_mod_name(root, folder_path)
            version = f[:-len(".pchtxt")].strip()

            combined = f"{game_name} - {mod_name}".strip()
            target_dir = os.path.join(formatted_path, combined)
            os.makedirs(target_dir, exist_ok=True)

            src = os.path.join(root, f)
            dst = os.path.join(target_dir, f"{version}.pchtxt")
            shutil.copy(src, dst)
            print(f"Copied {src} → {dst}")

    print("\nAll files have been organized successfully.")

def main(folder_path):
    create_formatted_structure(folder_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python format_repo_4.py /path/to/folder/")
        sys.exit(1)

    folder_path = sys.argv[1]
    main(folder_path)
