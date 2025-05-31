#!/usr/bin/env python3
import os
import shutil
import re
import sys
import unicodedata

# ----- Normalization & Title‐Casing Helpers (identical to other repos) -----

def sanitize_name(name):
    """
    Remove accents and unwanted characters, and replace ' - ' with a single space.
    """
    normalized = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    cleaned = normalized.replace("'", "").replace("’", "").replace("`", "").replace('"', "")
    # Merge any " - " into a single space, collapse extra spaces
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
    "RPG", "FPS", "MMO", "MMORPG", "LAN", "GUI", "NPC",
    "FFVII", "FFVIII", "FFIX", "FFX", "FFXII",
    "FX", "2K", "V1", "V2", "V3", "V4"
}

def is_roman_numeral(word):
    """
    Return True if `word` is a valid Roman numeral (case‐insensitive).
    """
    return bool(ROMAN_NUMERAL_PATTERN.match(word))

def title_case_preserve_numbers(name):
    """
    Title‐case with these rules:
      • Fully uppercase acronyms remain unchanged (e.g. HD, 2D, 3D, FFVII, etc.).
      • Roman numerals become fully uppercase (e.g. 'iii' → 'III', 'xI' → 'XI').
      • Hyphenated words are capitalized on both sides (→ 'Yooka-Laylee').
      • Small filler words (a, an, and, the, of, in, etc.) become lowercase
        only if they appear in the middle and are not immediately after a subtitle marker,
        except the first and last words (which always get capitalized).
      • After a subtitle marker (":", "~", "–", "—", or "-"), force capitalization
        on all subsequent words (until the next subtitle marker or end).
      • Compound Roman numerals joined by &, +, or | become fully uppercase (e.g. "I&ii" → "I&II").
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
        # Check if this word contains any subtitle marker
        contains_marker = any(marker in raw_word for marker in subtitle_markers)

        # Split on subtitle markers (keeping them in the list)
        split_parts = re.split(r'([:~\-–—])', raw_word)
        rebuilt_parts = []

        for part in split_parts:
            if part in subtitle_markers:
                # Keep marker, then force next segments to capitalize
                rebuilt_parts.append(part)
                force_capitalize_mode = True
                continue

            lower_part = part.lower()
            is_first = (idx == 0)
            is_last = (idx == len(words) - 1)

            def capitalize_special(subword):
                # 1) If subword uppercase is in ACRONYMS → uppercase it
                if subword.upper() in ACRONYMS:
                    return subword.upper()
                # 2) If subword is a Roman numeral → uppercase it
                if is_roman_numeral(subword):
                    return subword.upper()
                # 3) Check for compound Roman numerals joined by &, +, |
                for sep in ('&', '+', '|'):
                    if sep in subword:
                        pieces = subword.split(sep)
                        if all(is_roman_numeral(p) for p in pieces):
                            return sep.join(p.upper() for p in pieces)
                # 4) Otherwise → just hyphen‐capitalize normally
                return capitalize_hyphenated(subword)

            if force_capitalize_mode or is_first or is_last or (lower_part not in lowercase_exceptions):
                sub_parts = part.split('-')
                rebuilt_parts.append('-'.join(capitalize_special(p) for p in sub_parts))
            else:
                # In-middle filler word → keep lowercase
                rebuilt_parts.append(lower_part)

        result.append(''.join(rebuilt_parts))

        # If this raw_word did NOT contain a marker, stop forcing capitalization on the next
        if not contains_marker:
            force_capitalize_mode = False

    # Finally, ensure the first and last words are capitalized with special logic:
    if result:
        # First word:
        first_split = result[0].split('-')
        new_first = []
        for p in first_split:
            if p.upper() in ACRONYMS or is_roman_numeral(p):
                new_first.append(p.upper())
            else:
                new_first.append(capitalize_hyphenated(p))
        result[0] = '-'.join(new_first)

        # Last word:
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
    Convenience: run sanitize_name → title_case_preserve_numbers in one shot.
    """
    return title_case_preserve_numbers(sanitize_name(name))

# ----- Original Repo Logic, Now Injecting Our Title‐Casing -----

def transform_game_name(game_name):
    """
    1) Move ", The" to front, if present.
    2) Remove any " - " substring.
    """
    if ', The' in game_name:
        parts = game_name.split(', The')
        # e.g., "Zelda, The" → "The Zelda"
        game_name = f"The {parts[0]}{parts[1]}"
    # Remove " - " exactly
    game_name = game_name.replace(' - ', ' ')
    return game_name

def get_game_name_and_mod_name(path, root_dir):
    """
    Given `path` (where a .pchtxt file lives) and the `root_dir`,
    derive:
      • game_name  (with country if present, then sanitized+title‐cased)
      • mod_name   (sanitized+title‐cased), handling Aspect Ratio and version suffix.
    """
    relative_path = os.path.relpath(path, root_dir)
    parts = relative_path.split(os.sep)

    # The first part is the raw game folder name
    raw_game = parts[0]
    # Strip out any bracketed tags, then transform
    raw_game = re.sub(r'\[.*?\]', '', raw_game).strip()
    raw_game = transform_game_name(raw_game)

    # Check for country‐specific folders (look for something like "[USA]" or "[JP]" etc.)
    country = None
    for part in parts[1:]:
        if re.search(r'\[.*?\]', part):
            country = re.sub(r'\[.*?\]', '', part).strip()
            break

    if country:
        raw_game = f"{raw_game} ({country})"

    # Now sanitize + title‐case the game name exactly as in other repos:
    game_name = clean_title(raw_game)

    # Determine mod_name
    # If path contains "Aspect Ratio", then:
    if 'Aspect Ratio' in relative_path:
        # e.g. "<...>/Aspect Ratio/16:9/[files]"
        aspect_ratio = os.path.basename(os.path.dirname(path)).replace("'", ".")
        raw_mod = f"Aspect Ratio {aspect_ratio}"
    else:
        # If the last folder has a version suffix " v\d+", attach it to the previous part
        last_part = parts[-1]
        if re.search(r' v\d+', last_part):
            # e.g. .../SomeMod/Disable Fog v1/file.pchtxt → mod = "Disable Fog v1"
            raw_mod = parts[-2] + " " + last_part
        else:
            # Otherwise just take the immediate parent folder name
            raw_mod = parts[-2]

    # Sanitize + title‐case mod_name as well
    mod_name = clean_title(raw_mod)

    return game_name, mod_name

def create_formatted_structure(folder_path):
    """
    Walk `folder_path` for all .pchtxt files. For each one:
      1) Derive (game_name, mod_name) via get_game_name_and_mod_name.
      2) Sanitize and title‐case those exactly the same as other repos.
      3) Copy <…>.pchtxt into formatted/<Game Name> - <Mod Name>/<version>.pchtxt.
    """
    formatted_path = os.path.join(folder_path, 'formatted')
    os.makedirs(formatted_path, exist_ok=True)
    print(f"Creating formatted structure at: {formatted_path}\n")

    for root, dirs, files in os.walk(folder_path):
        # Skip the “formatted” directory itself
        if 'formatted' in root.split(os.sep):
            continue

        for file in files:
            if not file.lower().endswith('.pchtxt'):
                continue

            # Derive game_name and mod_name
            game_name, mod_name = get_game_name_and_mod_name(root, folder_path)

            version = file[:-len('.pchtxt')].strip()  # strip the ".pchtxt"
            new_dir = os.path.join(formatted_path, f"{game_name} - {mod_name}")
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
        print("Usage: python format_repo_3.py /path/to/folder/")
        sys.exit(1)

    folder_path = sys.argv[1]
    main(folder_path)
