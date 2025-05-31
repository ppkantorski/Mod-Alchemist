#!/usr/bin/env python3
import os
import re
import sys
import shutil
import tempfile
import subprocess
import unicodedata

def sanitize_name(name):
    """Normalize game names: remove symbols, accents, and replace ' - ' with space."""
    n = unicodedata.normalize('NFKD', name).encode('ascii','ignore').decode('ascii')
    n = n.replace("'", "").replace("’", "").replace("`", "").replace('"', "")
    n = n.replace(" - ", " ")  # Replace problematic ' - ' only in the game name
    return ' '.join(n.split()).strip()

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

# Regex for Roman numerals (supports up to 3999): I, II, III, IV, V, VI, VII, VIII, IX, X, XI, etc.
ROMAN_NUMERAL_PATTERN = re.compile(
    r"^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$",
    re.IGNORECASE
)

# A set of known acronyms (fully uppercase) that should remain uppercase exactly as is.
ACRONYMS = {
    "HD", "2D", "3D", "4K", "VR", "AI", "API", "USB", "CPU", "GPU", "DVD", "CD",
    "RPG", "FPS", "MMO", "MMORPG", "LAN", "GUI", "NPC", "FFVII", "FFVIII", "FX", "FFIX", "FFX", "FFXII"
}

def is_roman_numeral(word):
    """Return True if the word is a valid Roman numeral (e.g. I, ii, Xx, etc.)."""
    return bool(ROMAN_NUMERAL_PATTERN.match(word))

def title_case_preserve_numbers(name):
    """
    Title-case with these rules:
      • Fully uppercase acronyms remain unchanged (e.g. HD, 2D, 3D, FFVII, etc.).
      • Roman numerals are fully uppercase (e.g. iI iIi → III, xI → XI).
      • Hyphenated words are capitalized on both sides (→ Yooka-Laylee).
      • Conjoined Roman numerals with '&', '+', or '|' become fully uppercase (e.g. I&ii → I&II).
      • Small filler words (a, an, and, the, of, in, etc.) become lowercase
        only if they are in the middle of the title (not first, not last, not
        immediately after a subtitle marker).
      • After a subtitle marker ( :, ~, –, —, - ), force capitalization on all
        subsequent words until the next subtitle marker or end-of-title.
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
                # Keep the subtitle marker, then force subsequent parts to capitalize
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
                # Split hyphenated sub-parts, apply capitalize_special to each half
                sub_parts = part.split('-')
                capitalized_sub_parts = [capitalize_special(sp) for sp in sub_parts]
                capitalized_parts.append('-'.join(capitalized_sub_parts))
            else:
                # It’s a lowercase exception in the middle of the title, so keep it lowercase.
                capitalized_parts.append(lower_part)

        result.append(''.join(capitalized_parts))

        # If this word did not contain a subtitle marker, stop forcing next capitalization
        if not contains_marker:
            force_capitalize_mode = False

    # Always capitalize the FIRST and LAST words in the entire title (using same special rules):
    if result:
        first_word_parts = result[0].split('-')
        result[0] = '-'.join(
            sp.upper() if (sp.upper() in ACRONYMS or is_roman_numeral(sp)) else capitalize_hyphenated(sp)
            for sp in first_word_parts
        )

        last_word_parts = result[-1].split('-')
        result[-1] = '-'.join(
            sp.upper() if (sp.upper() in ACRONYMS or is_roman_numeral(sp)) else capitalize_hyphenated(sp)
            for sp in last_word_parts
        )

    return ' '.join(result)

def find_title_id(path):
    """Look for a 16-character Title ID under any 'contents/' directory in path."""
    for root, dirs, _ in os.walk(path):
        if os.path.basename(root).lower() == 'contents':
            for d in dirs:
                if re.fullmatch(r'[0-9A-Fa-f]{16}', d):
                    return d
    return None

def extract_with_7z(rar_path, tmpdir):
    """
    Extract only atmosphere/contents/* using 7z (same as your original).
    Return True if extraction succeeded (7z return code 0 OR
    we already found a Title ID folder inside tmpdir).
    """
    cmd = [
        "7z", "x", "-y",
        rar_path,
        f"-o{tmpdir}",
        "atmosphere/contents/*"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return (proc.returncode == 0) or (find_title_id(tmpdir) is not None)

def process_rar(root_folder, rar_relpath, output_root):
    """
    1) Parse “release_<version>.rar” → version string.
    2) Sanitize + title-case the game folder name.
    3) Extract with 7z into a temp dir.
    4) Find Title ID under any '*/contents/<16hex>/'.
    5) Copy that content into output/<GameName>/version/<TitleID>/.
    """
    subdir, filename = os.path.split(rar_relpath)
    version_match = re.match(r"release_(.+)\.rar$", filename, re.I)
    if not version_match:
        print(f"❌ Invalid release name: {filename}")
        return
    version = version_match.group(1)
    raw_game_name = os.path.basename(subdir)

    # Clean & normalize game name
    cleaned_name = sanitize_name(raw_game_name)
    game_name = title_case_preserve_numbers(cleaned_name)
    pack_label = f"{game_name} - Graphics Pack"

    rar_path = os.path.join(root_folder, rar_relpath)
    with tempfile.TemporaryDirectory() as tmp:
        ok = extract_with_7z(rar_path, tmp)
        if not ok:
            print(f"❌ Extraction error (7z) on {rar_relpath}")
            return

        title_id = find_title_id(tmp)
        if not title_id:
            print(f"❌ No Title ID found in {rar_relpath}")
            return  # Skip if no valid Title ID folder

        version_dir = os.path.join(output_root, pack_label, version)
        os.makedirs(version_dir, exist_ok=True)

        src = os.path.join(tmp, "atmosphere", "contents", title_id)
        dst = os.path.join(version_dir, title_id)
        try:
            shutil.copytree(src, dst, dirs_exist_ok=True)
            print(f"✅ {rar_relpath} → {os.path.join(pack_label, version, title_id)}")
        except Exception as e:
            print(f"❌ Copy failed for {rar_relpath}: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python collect_content_mods.py /path/to/root")
        sys.exit(1)

    root = sys.argv[1]
    output = os.path.join(root, "format2")
    os.makedirs(output, exist_ok=True)

    tasks = []
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if re.match(r"release_.*\.rar$", fn, re.I):
                rel = os.path.relpath(os.path.join(dirpath, fn), root)
                tasks.append(rel)

    for relpath in tasks:
        process_rar(root, relpath, output)

    print("✅ Done.")

if __name__ == "__main__":
    main()
