#!/usr/bin/env python3
import os
import shutil
import re
import sys
import unicodedata

# ----- Normalization & Title‐Casing Helpers (same as other repos) -----

def sanitize_name(name):
    """
    Remove accents and unwanted characters, replace ' - ' with a single space,
    and collapse multiple spaces.
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
    capitalized_parts = []
    for part in parts:
        if part:
            capitalized_parts.append(part[0].upper() + part[1:].lower() if len(part) > 1 else part.upper())
        else:
            capitalized_parts.append('')
    return '-'.join(capitalized_parts)

# Regex for Roman numerals up to 3999
ROMAN_NUMERAL_PATTERN = re.compile(
    r"^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$",
    re.IGNORECASE
)

# Known acronyms to force‐uppercase exactly
ACRONYMS = {
    "HD", "2D", "3D", "4K", "VR", "AI", "API", "USB", "CPU", "GPU", "DVD", "CD",
    "RPG", "FPS", "MMO", "MMORPG", "LAN", "GUI", "NPC", "FFVII", "FFVIII", "FX", "FFIX", "FFX", "FFXII"
}

def is_roman_numeral(word):
    """
    Return True if `word` is a valid Roman numeral (case‐insensitive).
    """
    return bool(ROMAN_NUMERAL_PATTERN.match(word))

def title_case_preserve_numbers(name):
    """
    Title-case with these rules:
      • Fully uppercase acronyms remain unchanged (e.g. HD, 2D, 3D, FFVII, etc.).
      • Roman numerals become fully uppercase (e.g. 'iii' → 'III', 'xI' → 'XI').
      • Hyphenated words are capitalized on both sides (→ 'Yooka-Laylee').
      • Small filler words (a, an, and, the, of, in, etc.) become lowercase
        only if they appear in the middle and are not immediately after a subtitle marker,
        except the first and last words (always capitalized).
      • After a subtitle marker (":", "~", "–", "—", or "-"), force capitalization
        on all subsequent words until the next subtitle marker or end.
      • Compound Roman numerals joined by &, +, or | become fully uppercase
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
        contains_marker = any(marker in raw_word for marker in subtitle_markers)
        split_parts = re.split(r'([:~\-–—])', raw_word)
        rebuilt_parts = []

        for part in split_parts:
            if part in subtitle_markers:
                # Keep marker, force next segments to capitalize
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
                # Check for compound Roman numerals joined by &, +, |
                for sep in ('&', '+', '|'):
                    if sep in subword:
                        pieces = subword.split(sep)
                        if all(is_roman_numeral(p) for p in pieces):
                            return sep.join(p.upper() for p in pieces)
                return capitalize_hyphenated(subword)

            if force_capitalize_mode or is_first or is_last or (lower_part not in lowercase_exceptions):
                sub_parts = part.split('-')
                rebuilt_parts.append('-'.join(capitalize_special(p) for p in sub_parts))
            else:
                rebuilt_parts.append(lower_part)

        result.append(''.join(rebuilt_parts))
        if not contains_marker:
            force_capitalize_mode = False

    # Always capitalize first and last words fully:
    if result:
        # First word
        first_split = result[0].split('-')
        new_first = []
        for p in first_split:
            if p.upper() in ACRONYMS or is_roman_numeral(p):
                new_first.append(p.upper())
            else:
                new_first.append(capitalize_hyphenated(p))
        result[0] = '-'.join(new_first)

        # Last word
        last_split = result[-1].split('-')
        new_last = []
        for p in last_split:
            if p.upper() in ACRONYMS or is_roman_numeral(p):
                new_last.append(p.upper())
            else:
                new_last.append(capitalize_hyphenated(p))
        result[-1] = '-'.join(new_last)

    return ' '.join(result)

def clean_title(name):
    """
    Run sanitize_name() → title_case_preserve_numbers() in one shot.
    """
    return title_case_preserve_numbers(sanitize_name(name))


# ----- Revised get_game_name_and_mod_name & Structure Logic -----

def get_game_name_and_mod_name(path, root_dir):
    """
    Given a folder path where a .pchtxt lives, derive:
      • game_name (honoring "[Country]" folders, ", The", etc.), then clean_title().
      • mod_name  (join of all sub‐folders except game, handling Aspect Ratio,
                   version suffix " vX", etc.), then clean_title().
    """
    relative_path = os.path.relpath(path, root_dir)
    parts = relative_path.split(os.sep)

    # 1) Derive raw game folder (strip [tags], handle ", The")
    raw_game = parts[0]
    raw_game = re.sub(r'\[.*?\]', '', raw_game).strip()
    if ', The' in raw_game:
        p = raw_game.split(', The')
        raw_game = f"The {p[0]}{p[1]}"
    raw_game = raw_game.replace(" - ", " ")

    # 2) Check for country folder like "[USA]" etc.
    country = None
    for p in parts[1:]:
        if re.search(r'\[.*?\]', p):
            country = re.sub(r'\[.*?\]', '', p).strip()
            break
    if country:
        raw_game = f"{raw_game} ({country})"

    # 3) Clean/title-case the game name:
    game_name = clean_title(raw_game)

    # 4) Derive raw mod_name
    #    a) If path contains "Aspect Ratio" segment, use that
    if 'Aspect Ratio' in relative_path:
        aspect_folder = os.path.basename(path)
        raw_mod = f"Aspect Ratio {aspect_folder}"
    else:
        # b) Otherwise join all folder parts after the first as mod components
        mod_parts = [re.sub(r'\[.*?\]', '', p).strip() for p in parts[1:]]
        if mod_parts:
            raw_mod = " ".join(mod_parts)
        else:
            raw_mod = ""

        # c) If raw_mod ends in " v<digits>" → preserve version suffix as part of mod_name
        m = re.search(r'(.*) v[0-9.]+$', raw_mod)
        if m:
            raw_mod = m.group(1)

    raw_mod = raw_mod.strip()

    # 5) Clean/title-case the mod_name:
    mod_name = clean_title(raw_mod) if raw_mod else ""

    return game_name, mod_name


def create_formatted_structure(folder_path):
    """
    Walk `folder_path` for all `.pchtxt` files. For each:
      1) Derive (game_name, mod_name) via get_game_name_and_mod_name.
      2) Place the file under formatted/"<Game Name> - <Mod Name>"/"<version>.pchtxt".
    """
    formatted_path = os.path.join(folder_path, 'formatted')
    os.makedirs(formatted_path, exist_ok=True)
    print(f"Creating formatted structure at: {formatted_path}\n")

    for root, dirs, files in os.walk(folder_path):
        # Skip anything already under "formatted"
        if 'formatted' in root.split(os.sep):
            continue

        for file in files:
            if not file.lower().endswith('.pchtxt'):
                continue

            game_name, mod_name = get_game_name_and_mod_name(root, folder_path)
            version = file[:-len('.pchtxt')].strip()

            # If mod_name ended up empty, we still create "Game Name - "
            combined_dir_name = f"{game_name} - {mod_name}".rstrip()
            new_dir = os.path.join(formatted_path, combined_dir_name)
            os.makedirs(new_dir, exist_ok=True)

            src = os.path.join(root, file)
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
