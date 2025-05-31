#!/usr/bin/env python3
import os
import shutil
import unicodedata
import sys
import re

def sanitize_name(name):
    """
    Remove accents and unwanted characters, and replace ' - ' with a single space.
    """
    normalized = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    cleaned = normalized.replace("'", "").replace("’", "").replace("`", "").replace('"', '')
    cleaned = cleaned.replace(" - ", " ")  # Remove " - " to avoid duplication
    cleaned = ' '.join(cleaned.split())    # Collapse multiple spaces
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

# Regex for Roman numerals (supports up to 3999): I, II, III, IV, V, VI, VII, VIII, IX, X, XI, etc.
ROMAN_NUMERAL_PATTERN = re.compile(
    r"^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$",
    re.IGNORECASE
)

# A set of known acronyms (fully uppercase) that should remain uppercase.
ACRONYMS = {
    "HD", "2D", "3D", "4K", "VR", "AI", "API", "USB", "CPU", "GPU", "DVD", "CD",
    "RPG", "FPS", "MMO", "MMORPG", "LAN", "GUI", "NPC", "FFVII", "FFVIII", "FX", "FFIX", "FFX", "FFXII"
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
      • Roman numerals become fully uppercase (e.g. iIi → III, xI → XI).
      • Hyphenated words are capitalized on both sides (→ Yooka-Laylee).
      • Conjoined Roman numerals with '&', '+', or '|' become fully uppercase (e.g. I&ii → I&II).
      • Small filler words (a, an, and, the, of, in, etc.) become lowercase
        only if they appear in the middle and are not immediately after a subtitle marker,
        except the first and last words (which always capitalized).
      • After a subtitle marker (":", "~", "–", "—", or "-"), force capitalization
        on all subsequent words (until the next subtitle marker or end).
    """
    lowercase_exceptions = {
        "a", "an", "and", "as", "at", "but", "by", "for", "from",
        "in", "nor", "of", "on", "or", "so", "the", "to", "with", "yet"
    }
    subtitle_markers = {":", "~", "-", "–", "—"}

    words = name.split()
    result = []
    force_capitalize_mode = False  # Once True, stays True until next subtitle marker

    for idx, word in enumerate(words):
        # Detect if this word contains any subtitle marker character
        contains_marker = any(marker in word for marker in subtitle_markers)

        # Split on subtitle markers but keep them in the list
        split_parts = re.split(r'([:~\-–—])', word)
        capitalized_parts = []

        for part in split_parts:
            if part in subtitle_markers:
                # Append the marker itself, then force-capitalize subsequent parts
                capitalized_parts.append(part)
                force_capitalize_mode = True
                continue

            lower_part = part.lower()
            is_first = (idx == 0)
            is_last = (idx == len(words) - 1)

            # Helper: capitalize a sub-word with special rules for acronyms, roman numerals, and conjoined numerals
            def capitalize_special(w):
                # If w (case-insensitive) is in our ACRONYMS set, uppercase it fully.
                if w.upper() in ACRONYMS:
                    return w.upper()
                # If w alone is a Roman numeral, uppercase it fully.
                if is_roman_numeral(w):
                    return w.upper()
                # Handle compound Roman numerals separated by &, +, or |
                for sep in ['&', '+', '|']:
                    if sep in w:
                        parts = w.split(sep)
                        if all(is_roman_numeral(p) for p in parts):
                            return sep.join(p.upper() for p in parts)
                # Otherwise, capitalize hyphenated words normally.
                return capitalize_hyphenated(w)

            # Decide how to capitalize this segment:
            if force_capitalize_mode or is_first or is_last or (lower_part not in lowercase_exceptions):
                # Split any hyphens, apply capitalize_special to each half
                sub_parts = part.split('-')
                capitalized_sub = [capitalize_special(sp) for sp in sub_parts]
                capitalized_parts.append('-'.join(capitalized_sub))
            else:
                # In-the-middle filler word: keep lowercase
                capitalized_parts.append(lower_part)

        result.append(''.join(capitalized_parts))

        # If this word did not contain a subtitle marker, stop forcing next capitalization
        if not contains_marker:
            force_capitalize_mode = False

    # Always capitalize the FIRST and LAST words (using the same special rules):
    if result:
        first_parts = result[0].split('-')
        result[0] = '-'.join(
            sp.upper() if (sp.upper() in ACRONYMS or is_roman_numeral(sp)) else capitalize_hyphenated(sp)
            for sp in first_parts
        )

        last_parts = result[-1].split('-')
        result[-1] = '-'.join(
            sp.upper() if (sp.upper() in ACRONYMS or is_roman_numeral(sp)) else capitalize_hyphenated(sp)
            for sp in last_parts
        )

    return ' '.join(result)

def create_formatted_structure(root_folder):
    """
    Walk root_folder for all .pchtxt files. For each one:
      1. Extract folder name → raw game name.
      2. sanitize_name() → remove weird characters.
      3. Remove trailing "Graphics" if present.
      4. title_case_preserve_numbers() to get final Game Name.
      5. Create folder: formatted/<Game Name> - Graphics Mods/
      6. Copy each .pchtxt into that folder as <version>.pchtxt.
    """
    formatted_path = os.path.join(root_folder, 'formatted')
    os.makedirs(formatted_path, exist_ok=True)
    print(f"Creating formatted structure at: {formatted_path}\n")

    for current_root, dirs, files in os.walk(root_folder):
        for file in files:
            if not file.lower().endswith('.pchtxt'):
                continue

            version = file[:-len('.pchtxt')].strip()
            parent_dir = os.path.basename(current_root)
            game_name = sanitize_name(parent_dir)

            # Remove trailing "Graphics" if it exists (exact match at end)
            if game_name.endswith("Graphics"):
                game_name = game_name[:-len("Graphics")].strip()

            # Title-case with acronyms, roman-numeral, and compound-numeral logic
            game_name = title_case_preserve_numbers(game_name)

            mod_name = "Graphics Mods"
            target_dir = os.path.join(formatted_path, f"{game_name} - {mod_name}")
            os.makedirs(target_dir, exist_ok=True)

            source_path = os.path.join(current_root, file)
            dest_path = os.path.join(target_dir, f"{version}.pchtxt")

            shutil.copy2(source_path, dest_path)
            print(f"Copied {source_path} → {dest_path}")

    print("\nDone!")

def main():
    if len(sys.argv) != 2:
        print("Usage: python collect_graphics_mods.py /path/to/root/folder")
        sys.exit(1)

    folder_path = sys.argv[1]
    create_formatted_structure(folder_path)

if __name__ == "__main__":
    main()
