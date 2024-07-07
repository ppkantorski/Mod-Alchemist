import os
import shutil
import re
import sys

def get_game_name_and_mod_name(path, root_dir):
    relative_path = os.path.relpath(path, root_dir)
    parts = relative_path.split(os.sep)
    game_name = parts[0]
    
    # Remove any parts within square brackets
    game_name = re.sub(r'\[.*?\]', '', game_name).strip()
    
    # Check for country-specific folders and adjust game name accordingly
    country = None
    for part in parts[1:]:
        if re.search(r'\[.*?\]', part):
            country = re.sub(r'\[.*?\]', '', part).strip()
            parts.remove(part)
            break

    if country:
        game_name = f"{game_name} ({country})"
    else:
        game_name = game_name.strip()

    mod_name_parts = parts[1:]
    mod_name_parts = [re.sub(r'\[.*?\]', '', part).strip() for part in mod_name_parts]
    mod_name = " ".join(mod_name_parts).strip()
    
    return game_name, mod_name

def create_formatted_structure(folder_path):
    formatted_path = os.path.join(folder_path, 'formatted')
    if not os.path.exists(formatted_path):
        os.makedirs(formatted_path)
    print(f"Creating formatted structure at: {formatted_path}")

    for root, dirs, files in os.walk(folder_path):
        if 'formatted' in root:
            continue
        for file in files:
            if file.endswith('.pchtxt'):
                game_name, mod_name = get_game_name_and_mod_name(root, folder_path)
                
                # Handle nested folders for aspect ratios and similar cases
                if 'Aspect Ratio' in root:
                    mod_name = 'Aspect Ratio ' + os.path.basename(root)
                
                version = file.replace('.pchtxt', '').strip()
                mod_name = re.sub(r' v[0-9.]+$', '', mod_name).strip()
                
                new_dir = os.path.join(formatted_path, f"{game_name} - {mod_name}")
                if not os.path.exists(new_dir):
                    os.makedirs(new_dir)
                    print(f"Created directory: {new_dir}")
                
                shutil.copy(os.path.join(root, file), os.path.join(new_dir, f"{version}.pchtxt"))
                print(f"Copied {file} to {os.path.join(new_dir, f'{version}.pchtxt')}")

def main(folder_path):
    create_formatted_structure(folder_path)
    print("Files have been organized successfully.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python format_repo_2.py /path/to/folder/")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    main(folder_path)
