#!/usr/bin/env python3
import os
import shutil
import re
import sys
import unicodedata

# ----- Normalization & Title‐Casing Helpers -----

def sanitize_name(name):
    normalized = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    cleaned = normalized.replace("'", "").replace("’", "").replace("`", "").replace('"', "")
    cleaned = cleaned.replace(" - ", " ")
    cleaned = ' '.join(cleaned.split())
    return cleaned.strip()

def capitalize_hyphenated(word):
    parts = word.split('-')
    capitalized_parts = []
    for part in parts:
        if part:
            capitalized_parts.append(part[0].upper() + part[1:].lower() if len(part) > 1 else part.upper())
        else:
            capitalized_parts.append('')
    return '-'.join(capitalized_parts)

ROMAN_NUMERAL_PATTERN = re.compile(
    r"^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$",
    re.IGNORECASE
)

# Known acronyms to force‐uppercase exactly
ACRONYMS = {
    "HD", "2D", "3D", "4K", "VR", "AI", "API", "USB", "CPU", "GPU", "DVD", "CD",
    "RPG", "FPS", "MMO", "MMORPG", "LAN", "GUI", "NPC",
    "FFVII", "FFVIII", "FFIX", "FFX", "FFXII",
    "FX", "2K", "5K", "8K", "V1", "V2", "V3", "V4", "DOF"
}

def is_roman_numeral(word):
    return bool(ROMAN_NUMERAL_PATTERN.match(word))

def title_case_preserve_numbers(name):
    lowercase_exceptions = {
        "a", "an", "and", "as", "at", "but", "by", "for", "from",
        "in", "nor", "of", "on", "or", "so", "the", "to", "with", "yet"
    }
    subtitle_markers = {":", "~", "-", "–", "—"}
    words = name.split()
    result = []
    force_capitalize_mode = False

    for idx, raw_word in enumerate(words):
        contains_marker = any(marker in raw_word for marker in subtitle_markers)
        split_parts = re.split(r'([:~\-–—])', raw_word)
        rebuilt_parts = []

        for part in split_parts:
            if part in subtitle_markers:
                rebuilt_parts.append(part)
                force_capitalize_mode = True
                continue

            lower_part = part.lower()
            is_first = (idx == 0)
            is_last = (idx == len(words) - 1)

            def capitalize_special(subword):
                if subword.upper() in ACRONYMS:
                    return subword.upper()
                if is_roman_numeral(subword):
                    return subword.upper()
                for sep in ('&', '+', '|'):
                    if sep in subword:
                        pieces = subword.split(sep)
                        if all(is_roman_numeral(p) for p in pieces):
                            return sep.join(p.upper() for p in pieces)
                return capitalize_hyphenated(subword)

            if force_capitalize_mode or is_first or is_last or (lower_part not in lowercase_exceptions):
                sub_parts = part.split('-')
                rebuilt_parts.append('-'.join(capitalize_special(s) for s in sub_parts))
            else:
                rebuilt_parts.append(lower_part)

        result.append(''.join(rebuilt_parts))
        if not contains_marker:
            force_capitalize_mode = False

    if result:
        first_split = result[0].split('-')
        result[0] = "-".join(capitalize_hyphenated(p) if not is_roman_numeral(p) else p.upper() for p in first_split)

        last_split = result[-1].split('-')
        result[-1] = "-".join(capitalize_hyphenated(p) if not is_roman_numeral(p) else p.upper() for p in last_split)

    return " ".join(result)

def clean_title(name):
    return title_case_preserve_numbers(sanitize_name(name))


# ----- Game & Mod Name Logic -----

def strip_versions(text):
    """
    Remove any substrings that look like version numbers, e.g.:
      - 1.0, 1.2.3
      - v1.0, v2.3.4
    """
    return re.sub(r'\b(v?\d+(?:\.\d+){1,2})\b', '', text, flags=re.IGNORECASE).strip()


def get_game_name_and_mod_name(path, root_dir):
    relative_path = os.path.relpath(path, root_dir)
    parts = relative_path.split(os.sep)

    raw_game = parts[0]
    raw_game = re.sub(r'\[.*?\]', '', raw_game).strip()
    if ", The" in raw_game:
        p = raw_game.split(", The")
        raw_game = f"The {p[0]}{p[1]}"
    raw_game = raw_game.replace(" - ", " ")

    country = None
    for p in parts[1:]:
        if re.search(r'\[.*?\]', p):
            country = re.sub(r'\[.*?\]', '', p).strip()
            break
    if country:
        raw_game = f"{raw_game} ({country})"
    game_name = clean_title(raw_game)

    sub_folders = [ re.sub(r'\[.*?\]', '', p).strip() for p in parts[1:] ]
    sub_folders = [sf for sf in sub_folders if sf.lower() != "pchtxt"]

    if "Aspect Ratio" in relative_path:
        aspect_folder = os.path.basename(path)
        raw_mod = f"Aspect Ratio {aspect_folder}"
    else:
        if sub_folders:
            m = re.match(r'^([0-9]+(?:\.[0-9]+)*)\s*(.*)$', sub_folders[0])
            if m:
                trailing = m.group(2).strip()
                if trailing:
                    sub_folders[0] = trailing
                else:
                    sub_folders = sub_folders[1:]

        if country and sub_folders:
            prefix = country.lower()
            candidate = sub_folders[0].lower()
            if candidate.startswith(prefix):
                sub_folders[0] = sub_folders[0][len(country):].lstrip()

        if sub_folders:
            raw_mod = " ".join(sub_folders).strip()
        else:
            raw_mod = ""

        raw_mod = strip_versions(raw_mod)
        m2 = re.match(r'^(.*)\s+v[0-9.]+$', raw_mod, re.IGNORECASE)
        if m2:
            raw_mod = m2.group(1).strip()

    mod_name = clean_title(raw_mod) if raw_mod else ""
    return game_name, mod_name


# ----- File Structure Logic -----

def create_formatted_structure(folder_path):
    formatted_path = os.path.join(folder_path, "formatted")
    os.makedirs(formatted_path, exist_ok=True)
    print(f"Creating formatted structure at: {formatted_path}\n")

    for root, dirs, files in os.walk(folder_path):
        if "formatted" in root.split(os.sep):
            continue

        for filename in files:
            if not filename.lower().endswith(".pchtxt"):
                continue

            game_name, mod_name = get_game_name_and_mod_name(root, folder_path)
            version = filename[:-len(".pchtxt")].strip()
            combined_dir = f"{game_name} - {mod_name}".rstrip()
            new_dir = os.path.join(formatted_path, combined_dir)
            os.makedirs(new_dir, exist_ok=True)

            src = os.path.join(root, filename)
            dst = os.path.join(new_dir, f"{version}.pchtxt")
            shutil.copy(src, dst)
            print(f"Copied {src} → {dst}")

    print("\nDone!\n")


def main(folder_path):
    create_formatted_structure(folder_path)
    print("All files have been organized successfully.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python format_repo_2.py /path/to/folder/")
        sys.exit(1)

    folder_path = sys.argv[1]
    main(folder_path)
