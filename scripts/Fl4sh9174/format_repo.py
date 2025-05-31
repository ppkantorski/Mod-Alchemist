#!/usr/bin/env python3
import os
import zipfile
import shutil
import re
import sys
import unicodedata

# ----- Normalization and Capitalization Helpers -----

def sanitize_name(name):
    """
    Remove accents and unwanted characters, and replace ' - ' with a single space.
    """
    normalized = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    cleaned = normalized.replace("'", "").replace("’", "").replace("`", "").replace('"', "")
    cleaned = cleaned.replace(" - ", " ")   # Merge any " - " into a single space
    cleaned = ' '.join(cleaned.split())     # Collapse multiple spaces
    return cleaned.strip()

def capitalize_hyphenated(word):
    """
    Capitalize both parts of a hyphenated word.
    E.g. "yooka-laylee" → "Yooka-Laylee"
    """
    parts = word.split('-')
    capitalized_parts = []
    for part in parts:
        if part:
            capitalized_parts.append(part[0].upper() + part[1:].lower() if len(part) > 1 else part.upper())
        else:
            capitalized_parts.append('')
    return '-'.join(capitalized_parts)

# Regex for Roman numerals (supports up to 3999: I, II, III, IV, …, XIII, …, MMMCMXCIX, etc.)
ROMAN_NUMERAL_PATTERN = re.compile(
    r"^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$",
    re.IGNORECASE
)

# A set of known acronyms (fully uppercase) that should remain uppercase exactly as is.
ACRONYMS = {
    "HD", "2D", "3D", "4K", "VR", "AI", "API", "USB", "CPU", "GPU", "DVD", "CD",
    "RPG", "FPS", "MMO", "MMORPG", "LAN", "GUI", "NPC", "FFVII", "FFVIII"
}

def is_roman_numeral(word):
    """
    Return True if the word is a valid Roman numeral (case-insensitive).
    """
    return bool(ROMAN_NUMERAL_PATTERN.match(word))

def title_case_preserve_numbers(name):
    """
    Title-case with these rules:
      • Fully uppercase acronyms remain unchanged (e.g. HD, 2D, 3D, FFVII, etc.).
      • Roman numerals are fully uppercase (e.g. 'iii' → 'III', 'xI' → 'XI').
      • Hyphenated words are capitalized on both sides (→ 'Yooka-Laylee').
      • Conjoined Roman numerals with &, +, or | become fully uppercase (e.g. 'I&ii' → 'I&II').
      • Small filler words (a, an, and, the, of, in, etc.) become lowercase only if:
           – they appear in the middle (not first or last),
           – and they are not immediately after a subtitle marker.
      • After a subtitle marker (":", "~", "–", "—", or "-"), force capitalization on all subsequent words
        until the next subtitle marker or end-of-title.
    """
    lowercase_exceptions = {
        "a", "an", "and", "as", "at", "but", "by", "for", "from",
        "in", "nor", "of", "on", "or", "so", "the", "to", "with", "yet"
    }
    subtitle_markers = {":", "~", "-", "–", "—"}

    words = name.split()
    capitalized_words = []
    force_capitalize = False

    for idx, raw_word in enumerate(words):
        # Check if this word contains a subtitle marker
        contains_marker = any(marker in raw_word for marker in subtitle_markers)

        # Break on subtitle markers, but keep them in the split list
        split_parts = re.split(r'([:~\-–—])', raw_word)
        rebuilt = []

        for part in split_parts:
            if part in subtitle_markers:
                # Keep the marker as-is, then force the next real segment to capitalize
                rebuilt.append(part)
                force_capitalize = True
                continue

            lower_part = part.lower()
            is_first = (idx == 0)
            is_last = (idx == len(words) - 1)

            def capitalize_special(subword):
                # 1) If subword (uppercased) is in ACRONYMS, return it unchanged
                if subword.upper() in ACRONYMS:
                    return subword.upper()
                # 2) If subword is a standalone Roman numeral, uppercase it
                if is_roman_numeral(subword):
                    return subword.upper()
                # 3) Check for compound Roman numerals (e.g. "I&ii")
                for sep in ['&', '+', '|']:
                    if sep in subword:
                        pieces = subword.split(sep)
                        if all(is_roman_numeral(p) for p in pieces):
                            return sep.join(p.upper() for p in pieces)
                # 4) Otherwise, capitalize hyphens normally
                return capitalize_hyphenated(subword)

            # Determine whether to capitalize or lowercase this segment
            if force_capitalize or is_first or is_last or (lower_part not in lowercase_exceptions):
                sub_hyphens = part.split('-')
                rebuilt.append('-'.join(capitalize_special(p) for p in sub_hyphens))
            else:
                # It's a filler word in the middle → keep lowercase
                rebuilt.append(lower_part)

        capitalized_words.append(''.join(rebuilt))

        # If this raw_word did NOT contain a marker, stop forcing capitalization on the next word
        if not contains_marker:
            force_capitalize = False

    # Finally, ensure the first and last words are definitely capitalized with special rules:
    if capitalized_words:
        # First word:
        first_split = capitalized_words[0].split('-')
        capitalized_words[0] = '-'.join(
            p.upper() if (p.upper() in ACRONYMS or is_roman_numeral(p)) else capitalize_hyphenated(p)
            for p in first_split
        )
        # Last word:
        last_split = capitalized_words[-1].split('-')
        capitalized_words[-1] = '-'.join(
            p.upper() if (p.upper() in ACRONYMS or is_roman_numeral(p)) else capitalize_hyphenated(p)
            for p in last_split
        )

    return ' '.join(capitalized_words)

def clean_title(name):
    """
    Convenience function to run both sanitize_name → title_case_preserve_numbers
    in one call.
    """
    return title_case_preserve_numbers(sanitize_name(name))

# ----- Unzipping and Formatting for this Repo -----

def unzip_files(folder_path):
    print("Unzipping files...\n")
    for item in os.listdir(folder_path):
        if item.lower().endswith('.zip'):
            file_path = os.path.join(folder_path, item)
            # Remove any bracketed tags (e.g. "[something]") then strip “.zip”
            raw_game_name = re.sub(r'\[.*?\]', '', item).replace('.zip', '').strip()
            cleaned_game_name = clean_title(raw_game_name)
            extract_to = os.path.join(folder_path, cleaned_game_name)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            print(f"✅ Unzipped: {file_path} → {extract_to}")

def create_formatted_structure(folder_path):
    formatted_path = os.path.join(folder_path, 'formatted')
    os.makedirs(formatted_path, exist_ok=True)
    print(f"\nOrganizing into: {formatted_path}\n")

    for game_dir in os.listdir(folder_path):
        game_dir_path = os.path.join(folder_path, game_dir)
        # Skip the "formatted" folder itself
        if not os.path.isdir(game_dir_path) or game_dir == 'formatted':
            continue

        # Compute the cleaned, title-cased game name once:
        cleaned_game_name = clean_title(game_dir)

        for root, dirs, files in os.walk(game_dir_path):
            for file in files:
                if file.lower().endswith('.pchtxt'):
                    # Look for a [mod_name vX.Y] segment in the path
                    relative_path = os.path.relpath(root, folder_path)
                    mod_match = re.search(r'\[(.*?)\]', relative_path)
                    if not mod_match:
                        continue

                    raw_mod_name = mod_match.group(1)
                    # Strip off any trailing " v<digits>" from the bracketed part
                    mod_name_no_version = re.sub(r' v[0-9.]+$', '', raw_mod_name).strip()

                    cleaned_mod_name = clean_title(mod_name_no_version)
                    version = file[:-len('.pchtxt')].strip()

                    target_dir = os.path.join(
                        formatted_path,
                        f"{cleaned_game_name} - {cleaned_mod_name}"
                    )
                    os.makedirs(target_dir, exist_ok=True)

                    source_file = os.path.join(root, file)
                    dest_file = os.path.join(target_dir, f"{version}.pchtxt")
                    shutil.move(source_file, dest_file)
                    print(f"📦 Moved {file} → {os.path.join(target_dir, f'{version}.pchtxt')}")

        # Once done walking this game’s directory, remove it entirely
        shutil.rmtree(game_dir_path)
        print(f"🗑️ Removed temporary folder: {game_dir_path}")

    print("\n✅ All files organized successfully.")

def main(folder_path):
    unzip_files(folder_path)
    create_formatted_structure(folder_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python format_repo.py /path/to/folder/of/zips/")
        sys.exit(1)

    folder_path = sys.argv[1]
    main(folder_path)
