#!/usr/bin/env python3
"""
Headless extractor using unar/7z (no Keka). Designed for the NX-IPS-romfs-compilation repo.
Installs required: `brew install unar p7zip`
Set KEEP_TMP=1 to preserve temp extraction folders for debugging.
"""
import os, re, sys, shutil, tempfile, subprocess, unicodedata, urllib.request, zipfile

# ---------------- Config ----------------
TMP_ROOT = os.path.expanduser("~/keka_extract_tmp")   # safe, in HOME
KEEP_TMP = os.environ.get("KEEP_TMP", "") != ""
# ---------------- Helpers (naming/title) ----------------
def sanitize_name(name):
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    for ch in ("'", "’", "`", '"'):
        n = n.replace(ch, "")
    n = n.replace(" - ", " ")
    return " ".join(n.split()).strip()

def capitalize_hyphenated(word):
    parts = word.split("-")
    out = []
    for p in parts:
        if not p:
            out.append("")
        elif len(p) == 1:
            out.append(p.upper())
        else:
            out.append(p[0].upper() + p[1:].lower())
    return "-".join(out)

ROMAN_NUMERAL_PATTERN = re.compile(r"^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$", re.IGNORECASE)
ACRONYMS = {"HD","2D","3D","4K","VR","AI","API","USB","CPU","GPU","DVD","CD",
            "RPG","FPS","MMO","MMORPG","LAN","GUI","NPC",
            "FFVII","FFVIII","FFIX","FFX","FFXII","FX","2K","5K","8K","V1","V2","V3","V4","DOF"}

def is_roman_numeral(w): return bool(ROMAN_NUMERAL_PATTERN.match(w))

def title_case_preserve_numbers(name):
    lowercase_exceptions = {"a","an","and","as","at","but","by","for","from","in","nor","of","on","or","so","the","to","with","yet"}
    subtitle_markers = {":","~","-","–","—"}
    words = name.split()
    result = []
    force_cap = False
    for idx, word in enumerate(words):
        contains_marker = any(m in word for m in subtitle_markers)
        parts = re.split(r'([:~\-–—])', word)
        out_parts = []
        for part in parts:
            if part in subtitle_markers:
                out_parts.append(part)
                force_cap = True
                continue
            lp = part.lower()
            is_first = idx == 0
            is_last = idx == len(words) - 1
            def cap_special(w):
                if w.upper() in ACRONYMS: return w.upper()
                if is_roman_numeral(w): return w.upper()
                for sep in ('&','+','|'):
                    if sep in w:
                        sub = w.split(sep)
                        if all(is_roman_numeral(x) for x in sub):
                            return sep.join(x.upper() for x in sub)
                return capitalize_hyphenated(w)
            if force_cap or is_first or is_last or (lp not in lowercase_exceptions):
                out_parts.append('-'.join(cap_special(sp) for sp in part.split('-')))
            else:
                out_parts.append(lp)
        result.append(''.join(out_parts))
        if not contains_marker:
            force_cap = False
    if result:
        result[0] = '-'.join(sp.upper() if (sp.upper() in ACRONYMS or is_roman_numeral(sp)) else capitalize_hyphenated(sp) for sp in result[0].split('-'))
        result[-1] = '-'.join(sp.upper() if (sp.upper() in ACRONYMS or is_roman_numeral(sp)) else capitalize_hyphenated(sp) for sp in result[-1].split('-'))
    return ' '.join(result)

def find_title_path(path):
    hex_re = re.compile(r'^[0-9A-Fa-f]{16}$')
    for root, dirs, _ in os.walk(path):
        for d in dirs:
            if hex_re.match(d):
                return os.path.join(root, d)
    return None

# ---------------- Extraction functions ----------------
def which_exec(names):
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None

UNAR = which_exec(["unar"])
SEVENZ = which_exec(["7z", "7zz"])  # prefer 7z if present

def extract_with_unar(archive_path, outdir):
    if UNAR is None:
        return False, "unar not installed"
    os.makedirs(outdir, exist_ok=True)
    cmd = [UNAR, "-o", outdir, "-f", archive_path]  # -f overwrite if needed
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode(errors="replace")
    err = proc.stderr.decode(errors="replace")
    ok = (proc.returncode == 0)
    return ok, f"rc={proc.returncode} stdout={out[:1000]!r} stderr={err[:1000]!r}"

def extract_with_7z(archive_path, outdir):
    if SEVENZ is None:
        return False, "7z not installed"
    os.makedirs(outdir, exist_ok=True)
    # 7z expects -o<dir> (no space) — but passing as single arg works too for many wrappers; use concatenated to be safe
    cmd = [SEVENZ, "x", archive_path, f"-o{outdir}", "-y"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode(errors="replace")
    err = proc.stderr.decode(errors="replace")
    ok = (proc.returncode == 0)
    return ok, f"rc={proc.returncode} stdout={out[:1000]!r} stderr={err[:1000]!r}"

def extract_archive_headless(archive_path, outdir):
    """
    Try best extractor for extension:
      .rar -> unar then 7z
      .7z  -> 7z then unar
    Returns (True, debugstr) or (False, debugstr)
    """
    ext = archive_path.lower().rsplit(".",1)[-1]
    if ext == "rar":
        # prefer unar for rar
        if UNAR:
            ok, dbg = extract_with_unar(archive_path, outdir)
            if ok: return True, "unar: " + dbg
            # else try 7z
        if SEVENZ:
            ok, dbg = extract_with_7z(archive_path, outdir)
            if ok: return True, "7z: " + dbg
        return False, "no suitable extractor succeeded; tried unar and 7z. " + (dbg if 'dbg' in locals() else "")
    elif ext == "7z":
        if SEVENZ:
            ok, dbg = extract_with_7z(archive_path, outdir)
            if ok: return True, "7z: " + dbg
        if UNAR:
            ok, dbg = extract_with_unar(archive_path, outdir)
            if ok: return True, "unar: " + dbg
        return False, "no suitable extractor succeeded for .7z"
    else:
        # generic try unar then 7z
        if UNAR:
            ok, dbg = extract_with_unar(archive_path, outdir)
            if ok: return True, "unar: " + dbg
        if SEVENZ:
            ok, dbg = extract_with_7z(archive_path, outdir)
            if ok: return True, "7z: " + dbg
        return False, "no extractor available for extension: " + ext

# ---------------- Processing per archive ----------------
def process_rar(root_folder, rar_relpath, output_root):
    subdir, filename = os.path.split(rar_relpath)
    version_match = re.match(r"release_(.+?)(?:\.part\d+)?\.(rar|7z)$", filename, re.IGNORECASE)
    if not version_match:
        print(f"❌ Invalid release name: {filename}")
        return
    version = version_match.group(1)
    raw_game_name = os.path.basename(subdir)
    cleaned_name = sanitize_name(raw_game_name)
    game_name = title_case_preserve_numbers(cleaned_name)
    pack_label = f"{game_name} - Graphics Pack"

    rar_path = os.path.join(root_folder, rar_relpath)

    os.makedirs(TMP_ROOT, exist_ok=True)
    tmpdir = tempfile.mkdtemp(prefix="extract_", dir=TMP_ROOT)
    try:
        ok, dbg = extract_archive_headless(rar_path, tmpdir)
        if not ok:
            print(f"❌ Extraction error (headless) on {rar_relpath}: {dbg}")
            if KEEP_TMP:
                print("Temp dir kept at:", tmpdir)
            return

        title_path = find_title_path(tmpdir)
        if not title_path:
            # maybe files extracted but no TitleID folder, show debugging
            any_files = False
            for _r,_d,files in os.walk(tmpdir):
                if files:
                    any_files = True
                    break
            if any_files:
                print(f"❌ Extracted but no TitleID found for {rar_relpath}. Inspect: {tmpdir} — dbg: {dbg}")
            else:
                print(f"❌ No files extracted for {rar_relpath}. dbg: {dbg}")
            if KEEP_TMP:
                print("Temp dir kept at:", tmpdir)
            return

        title_id = os.path.basename(title_path)
        version_dir = os.path.join(output_root, pack_label, version)
        os.makedirs(version_dir, exist_ok=True)
        dst = os.path.join(version_dir, title_id)
        try:
            shutil.copytree(title_path, dst, dirs_exist_ok=True)
            print(f"✅ {rar_relpath} → {os.path.join(pack_label, version, title_id)}")
        except Exception as e:
            print(f"❌ Copy failed for {rar_relpath}: {e}")

    finally:
        if KEEP_TMP:
            print("Kept tmpdir for debugging:", tmpdir)
        else:
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

# ---------------- pchtxt processing (unchanged) ----------------
def process_pchtxt(root_folder, output_path):
    os.makedirs(output_path, exist_ok=True)
    print(f"Creating formatted pchtxt structure at: {output_path}\n")
    for current_root, dirs, files in os.walk(root_folder):
        if 'contents_formatted' in current_root or 'pchtxt_formatted' in current_root:
            continue
        for file in files:
            if not file.lower().endswith('.pchtxt'):
                continue
            version = file[:-len('.pchtxt')].strip()
            parent_dir = os.path.basename(current_root)
            game_name = sanitize_name(parent_dir)
            if game_name.endswith("Graphics"):
                game_name = game_name[:-len("Graphics")].strip()
            game_name = title_case_preserve_numbers(game_name)
            mod_name = "Graphics Mods"
            target_dir = os.path.join(output_path, f"{game_name} - {mod_name}")
            os.makedirs(target_dir, exist_ok=True)
            source_path = os.path.join(current_root, file)
            dest_path = os.path.join(target_dir, f"{version}.pchtxt")
            shutil.copy2(source_path, dest_path)
            print(f"Copied {source_path} → {dest_path}")
    print("\nDone processing pchtxt!")

# ---------------- main ----------------
def main():
    # refuse to run as root — running as root was causing /var/root/ issues earlier
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        print("Refusing to run as root. Run this script as your normal user (no sudo).")
        sys.exit(1)

    zip_url = "https://github.com/cucholix/NX-IPS-romfs-compilation/archive/refs/heads/main.zip"
    zip_path = "NX-IPS-romfs-compilation-main.zip"
    unzip_dir = "NX-IPS-romfs-compilation-main"

    if not os.path.exists(unzip_dir):
        if not os.path.exists(zip_path):
            print("Downloading repo zip...")
            urllib.request.urlretrieve(zip_url, zip_path)
            print("Download complete.")
        print("Unzipping repo...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")
        print("Unzip complete.")

    root = unzip_dir
    output_contents = os.path.join(".", "contents_formatted")
    os.makedirs(output_contents, exist_ok=True)

    tasks = []
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if re.match(r"release_(.+?)(?:\.part\d+)?\.(rar|7z)$", fn, re.IGNORECASE):
                if fn.lower().endswith(".part01.rar") or (fn.lower().endswith(".rar") and ".part" not in fn.lower()) or fn.lower().endswith(".7z"):
                    rel = os.path.relpath(os.path.join(dirpath, fn), root)
                    tasks.append(rel)

    if not UNAR and not SEVENZ:
        print("ERROR: neither 'unar' nor '7z' found. Install with: brew install unar p7zip")
        sys.exit(1)

    for relpath in tasks:
        process_rar(root, relpath, output_contents)

    print("✅ Done processing content mods.")
    output_pchtxt = os.path.join(".", "pchtxt_formatted")
    process_pchtxt(root, output_pchtxt)

if __name__ == '__main__':
    main()
