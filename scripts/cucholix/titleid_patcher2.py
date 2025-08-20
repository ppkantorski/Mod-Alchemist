#!/usr/bin/env python3
import os
import json
import re
import unicodedata
import sys
from pathlib import Path
from difflib import get_close_matches

def load_title_database(db_path="US.en.json"):
    """Load the title database from JSON file."""
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Title database not found: {db_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in title database: {db_path}")
        sys.exit(1)

def load_cnmts_database(cnmts_path="cnmts.json"):
    """Load the cnmts database from JSON file."""
    try:
        with open(cnmts_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ CNMTS database not found: {cnmts_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in CNMTS database: {cnmts_path}")
        sys.exit(1)

def sanitize_name(name):
    """Remove accents and unwanted characters, and replace ' - ' with a single space."""
    normalized = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    cleaned = normalized.replace("'", "").replace("'", "").replace("`", "").replace('"', '')
    cleaned = cleaned.replace(" - ", " ")
    cleaned = ' '.join(cleaned.split())
    return cleaned.strip()

def capitalize_hyphenated(word):
    """Capitalize both parts of a hyphenated word."""
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

ACRONYMS = {
    "HD", "2D", "3D", "4K", "VR", "AI", "API", "USB", "CPU", "GPU", "DVD", "CD",
    "RPG", "FPS", "MMO", "MMORPG", "LAN", "GUI", "NPC",
    "FFVII", "FFVIII", "FFIX", "FFX", "FFXII",
    "FX", "2K", "5K", "8K", "V1", "V2", "V3", "V4", "DOF"
}

def is_roman_numeral(word):
    """Return True if the word is a valid Roman numeral."""
    return bool(ROMAN_NUMERAL_PATTERN.match(word))

def title_case_preserve_numbers(name):
    """Title-case with special rules for acronyms, Roman numerals, etc."""
    lowercase_exceptions = {
        "a", "an", "and", "as", "at", "but", "by", "for", "from",
        "in", "nor", "of", "on", "or", "so", "the", "to", "with", "yet"
    }
    subtitle_markers = {":", "~", "-", "–", "—"}

    words = name.split()
    result = []
    force_capitalize_mode = False

    for idx, word in enumerate(words):
        contains_marker = any(marker in word for marker in subtitle_markers)
        split_parts = re.split(r'([:~\-–—])', word)
        capitalized_parts = []

        for part in split_parts:
            if part in subtitle_markers:
                capitalized_parts.append(part)
                force_capitalize_mode = True
                continue

            lower_part = part.lower()
            is_first = (idx == 0)
            is_last = (idx == len(words) - 1)

            def capitalize_special(w):
                if w.upper() in ACRONYMS:
                    return w.upper()
                if is_roman_numeral(w):
                    return w.upper()
                for sep in ['&', '+', '|']:
                    if sep in w:
                        parts = w.split(sep)
                        if all(is_roman_numeral(p) for p in parts):
                            return sep.join(p.upper() for p in parts)
                return capitalize_hyphenated(w)

            if force_capitalize_mode or is_first or is_last or (lower_part not in lowercase_exceptions):
                sub_parts = part.split('-')
                capitalized_sub = [capitalize_special(sp) for sp in sub_parts]
                capitalized_parts.append('-'.join(capitalized_sub))
            else:
                capitalized_parts.append(lower_part)

        result.append(''.join(capitalized_parts))

        if not contains_marker:
            force_capitalize_mode = False

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

def normalize_title(text):
    """Normalize title names for matching."""
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-zA-Z0-9 ]', '', text).lower()
    return ' '.join(text.split())

def create_title_mapping(title_db):
    """Create normalized mapping of game name -> title ID."""
    title_map = {}
    normalized_title_map = {}
    
    for entry in title_db.values():
        name = entry.get("name")
        tid = entry.get("id")
        if name and tid:
            title_map[name.strip()] = tid.strip()
            normalized_title_map[normalize_title(name)] = tid.strip()
    
    return title_map, normalized_title_map

def find_title_id_by_build_id(build_id, cnmts_db, debug=False):
    """Find title ID by matching build ID prefix against full build IDs in cnmts.json."""
    if not build_id:
        return None, None
        
    build_id = build_id.upper()
    
    for title_id, versions in cnmts_db.items():
        for version_num, version_data in versions.items():
            content_entries = version_data.get("contentEntries", [])
            for entry in content_entries:
                full_build_id = entry.get("buildId")
                if full_build_id and entry.get("type") == 1:
                    # Check if the build ID from .pchtxt matches the start of the full build ID
                    if full_build_id.upper().startswith(build_id):
                        if debug:
                            return title_id.upper(), full_build_id
                        return title_id.upper(), None
    
    return None, None

def get_title_id_from_name(game_name, normalized_title_map):
    """Fuzzy match game name to title ID using normalized names."""
    if not game_name:
        return None

    norm_query = normalize_title(game_name)

    # Exact match
    if norm_query in normalized_title_map:
        return normalized_title_map[norm_query]

    # Substring match
    for title_key in normalized_title_map.keys():
        if norm_query in title_key:
            return normalized_title_map[title_key]

    # Fuzzy fallback
    matches = get_close_matches(norm_query, normalized_title_map.keys(), n=1, cutoff=0.5)
    if matches:
        return normalized_title_map[matches[0]]

    return None

def extract_game_name_from_folder(folder_name):
    """Extract and format game name from folder name."""
    game_name = sanitize_name(folder_name)
    
    # Remove trailing "Graphics" if it exists
    if game_name.endswith("Graphics"):
        game_name = game_name[:-len("Graphics")].strip()
    
    # Apply title case formatting
    game_name = title_case_preserve_numbers(game_name)
    
    return game_name

def extract_nsobid_from_pchtxt(file_path):
    """Extract the nsobid (build ID) from a .pchtxt file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("@nsobid-"):
                    # Extract the build ID after @nsobid-
                    build_id = line[8:]  # Remove "@nsobid-"
                    return build_id.upper()
        return None
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return None

def extract_region_from_filename(filename):
    """Extract region code from filename like '1.0.3_US.pchtxt' -> 'US'."""
    # Remove .pchtxt extension
    name_without_ext = filename.replace('.pchtxt', '')
    
    # Look for pattern like _XX where XX is 2-3 letter region code
    region_match = re.search(r'_([A-Z]{2,3})$', name_without_ext)
    if region_match:
        return region_match.group(1)
    
    return None

def patch_pchtxt_file(file_path, game_name, title_id):
    """Patch a single .pchtxt file with the title ID."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Find and update the header line (starts with #)
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("#"):
                # Check if it already has a title ID in brackets
                if "[" in line and "]" in line:
                    # Replace existing title ID
                    lines[i] = f"# {game_name} [{title_id}]\n"
                else:
                    # Add title ID to existing header
                    lines[i] = line.strip() + f" [{title_id}]\n"
                updated = True
                break

        if not updated:
            # Find the line after @nsobid to insert header
            nsobid_index = -1
            for i, line in enumerate(lines):
                if line.startswith("@nsobid-"):
                    nsobid_index = i
                    break
            
            if nsobid_index >= 0:
                # Insert after @nsobid line, but before any empty line
                insert_index = nsobid_index + 1
                if insert_index < len(lines) and lines[insert_index].strip() == "":
                    insert_index += 1
                lines.insert(insert_index, f"# {game_name} [{title_id}]\n")
            else:
                # Insert at the beginning if no @nsobid found
                lines.insert(0, f"# {game_name} [{title_id}]\n")

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        return True
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False

def patch_original_files_with_buildid(root_folder, title_db_path="US.en.json", cnmts_db_path="cnmts.json"):
    """
    Walk through the original folder structure and patch all .pchtxt files
    with their corresponding title IDs using build ID mapping.
    """
    # Load databases
    title_db = load_title_database(title_db_path)
    cnmts_db = load_cnmts_database(cnmts_db_path)
    
    title_map, normalized_title_map = create_title_mapping(title_db)
    
    print(f"Loaded {len(normalized_title_map)} titles from title database")
    print(f"Loaded CNMTS database with {len(cnmts_db)} title entries")
    print(f"Scanning folder: {root_folder}\n")
    
    stats = {
        'processed': 0,
        'patched_by_buildid': 0,
        'patched_by_name': 0,
        'no_buildid': 0,
        'no_title_id': 0,
        'errors': 0,
        'regional_variants': 0
    }
    
    for current_root, dirs, files in os.walk(root_folder):
        # Skip the formatted directory if it exists
        if 'formatted' in current_root:
            continue
            
        pchtxt_files = [f for f in files if f.lower().endswith('.pchtxt')]
        if not pchtxt_files:
            continue
            
        # Extract game name from folder
        folder_name = os.path.basename(current_root)
        game_name = extract_game_name_from_folder(folder_name)
        
        print(f"📁 {folder_name}")
        print(f"   Game: {game_name}")
        
        # Group files by region to show regional variants
        regional_files = {}
        for file in pchtxt_files:
            region = extract_region_from_filename(file)
            if region:
                regional_files[region] = file
                stats['regional_variants'] += 1
        
        if regional_files:
            print(f"   🌍 Regional variants detected: {', '.join(regional_files.keys())}")
        
        # Process each .pchtxt file in this folder
        for file in pchtxt_files:
            file_path = os.path.join(current_root, file)
            stats['processed'] += 1
            
            region = extract_region_from_filename(file)
            region_suffix = f" ({region})" if region else ""
            
            # First, try to get title ID from build ID
            build_id = extract_nsobid_from_pchtxt(file_path)
            title_id = None
            method = None
            
            if build_id:
                title_id, full_build_id = find_title_id_by_build_id(build_id, cnmts_db, debug=True)
                if title_id:
                    method = "build_id"
                    stats['patched_by_buildid'] += 1
                    print(f"   🔍 Build ID match: {build_id} -> {full_build_id}")
                else:
                    print(f"   ⚠️  Build ID {build_id} not found in CNMTS database")
            else:
                stats['no_buildid'] += 1
                print(f"   ⚠️  No build ID found in {file}")
            
            # If build ID lookup failed, try name-based lookup
            if not title_id:
                title_id = get_title_id_from_name(game_name, normalized_title_map)
                if title_id:
                    method = "name"
                    stats['patched_by_name'] += 1
            
            if title_id:
                if patch_pchtxt_file(file_path, game_name, title_id):
                    print(f"   ✅ Patched: {file}{region_suffix} with [{title_id}] (via {method})")
                else:
                    stats['errors'] += 1
            else:
                print(f"   ❌ No title ID found for: {file}{region_suffix}")
                stats['no_title_id'] += 1
        
        print()  # Empty line for readability
    
    # Print summary
    print("=" * 60)
    print("SUMMARY:")
    print(f"Files processed: {stats['processed']}")
    print(f"Files patched via build ID: {stats['patched_by_buildid']}")
    print(f"Files patched via name matching: {stats['patched_by_name']}")
    print(f"Regional variant files detected: {stats['regional_variants']}")
    print(f"Files with no build ID: {stats['no_buildid']}")
    print(f"Files with no title ID found: {stats['no_title_id']}")
    print(f"Errors: {stats['errors']}")
    print("=" * 60)

def main():
    if len(sys.argv) not in [2, 3, 4]:
        print("Usage: python patch_buildid_titleids.py /path/to/root/folder [path/to/US.en.json] [path/to/cnmts.json]")
        print("If database paths are not provided, it will look for 'US.en.json' and 'cnmts.json' in the current directory.")
        sys.exit(1)

    root_folder = sys.argv[1]
    title_db_path = sys.argv[2] if len(sys.argv) >= 3 else "US.en.json"
    cnmts_db_path = sys.argv[3] if len(sys.argv) == 4 else "cnmts.json"
    
    if not os.path.exists(root_folder):
        print(f"❌ Root folder not found: {root_folder}")
        sys.exit(1)
    
    patch_original_files_with_buildid(root_folder, title_db_path, cnmts_db_path)

if __name__ == "__main__":
    main()