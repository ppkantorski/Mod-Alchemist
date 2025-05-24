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
    n = n.replace("'", "").replace("’", "").replace("`", "").replace('"', '')
    n = n.replace(" - ", " ")  # Replace problematic ' - ' only in the game name
    return ' '.join(n.split()).strip()

def title_case_preserve_numbers(name):
    """Capitalize words while preserving full-uppercase acronyms."""
    return ' '.join(w.capitalize() if not w.isupper() else w for w in name.split())

def find_title_id(path):
    """Look for 16-character Title ID under any 'contents/' directory."""
    for root, dirs, _ in os.walk(path):
        if os.path.basename(root).lower() == 'contents':
            for d in dirs:
                if re.fullmatch(r'[0-9A-Fa-f]{16}', d):
                    return d
    return None

def extract_with_7z(rar_path, tmpdir):
    """Extract only atmosphere/contents/* using 7z."""
    cmd = [
        "7z", "x", "-y",
        rar_path,
        f"-o{tmpdir}",
        "atmosphere/contents/*"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc.returncode == 0 or find_title_id(tmpdir) is not None

def process_rar(root_folder, rar_relpath, output_root):
    subdir, file = os.path.split(rar_relpath)
    version_match = re.match(r"release_(.+)\.rar$", file, re.I)
    if not version_match:
        print(f"❌ Invalid release name: {file}")
        return
    version = version_match.group(1)
    raw_game_name = os.path.basename(subdir)

    # Clean and normalize game name (remove " - ", keep suffix clean)
    cleaned_name = sanitize_name(raw_game_name)
    game_name = title_case_preserve_numbers(cleaned_name)
    pack_label = f"{game_name} - Graphics Pack"  # Final folder

    rar_path = os.path.join(root_folder, rar_relpath)
    with tempfile.TemporaryDirectory() as tmp:
        ok = extract_with_7z(rar_path, tmp)
        if not ok:
            print(f"❌ Extraction error (7z) on {rar_relpath}")
            return

        title_id = find_title_id(tmp)
        if not title_id:
            print(f"❌ No Title ID found in {rar_relpath}")
            return  # Skip making directory if no Title ID found

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
