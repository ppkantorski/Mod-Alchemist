import os
import shutil
import re
import sys
import rarfile

def transform_game_name(game_name):
    # Move 'The' to the front if it exists
    if ', The' in game_name:
        parts = game_name.split(', The')
        game_name = f"The {parts[0]}{parts[1]}"
    
    # Remove ' - ' from the game name
    game_name = game_name.replace(' - ', ' ')
    
    # Remove any '/'
    game_name = game_name.replace(':', '')

    print("Game Name "+game_name)
    return game_name

def extract_rar_files(folder_path):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.rar'):
                rar_path = os.path.join(root, file)
                with rarfile.RarFile(rar_path) as rf:
                    rf.extractall(root)
                print(f"Extracted {rar_path}")

def get_game_name_and_mod_name(path, root_dir):
    relative_path = os.path.relpath(path, root_dir)
    parts = relative_path.split(os.sep)
    
    # The first part is the game name
    game_name = parts[0]
    
    # Remove any parts within square brackets
    game_name = re.sub(r'\[.*?\]', '', game_name).strip()
    
    # Transform the game name
    game_name = transform_game_name(game_name)
    
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

    # Handle Aspect Ratio mods specifically
    if 'Aspect Ratio' in relative_path:
        aspect_ratio = os.path.basename(os.path.dirname(path)).replace("'", ".").replace("`", ".")
        mod_name = f'Aspect Ratio {aspect_ratio}'
    else:
        # Handle versioned mod names like "Disable Fog v1"
        if re.search(r' v\d+', parts[-1]):
            mod_name = parts[-2] + " " + parts[-1]
        else:
            # For other cases, use the immediate parent directory name
            mod_name = parts[-2]
    
    # Replace ` and ' with . in the mod name
    mod_name = mod_name.replace("'", ".").replace("`", ".").replace("21-9", "21.9")
    # Remove any '/' from mod name
    mod_name = mod_name.replace(':', '')

    # For handling the outlier mod (missing name) on the repo
    mod_name = mod_name.replace("Trailblazers", "4K")

    return game_name, mod_name

def create_formatted_structure(folder_path):
    extract_rar_files(folder_path)
    
    formatted_path = os.path.join(folder_path, 'formatted')
    if not os.path.exists(formatted_path):
        os.makedirs(formatted_path)
    #print(f"Creating formatted structure at: {formatted_path}")

    for root, dirs, files in os.walk(folder_path):
        if 'formatted' in root:
            continue
        for file in files:
            if file.endswith('.pchtxt'):
                game_name, mod_name = get_game_name_and_mod_name(root, folder_path)
                
                version = file.replace('.pchtxt', '').strip()
                
                new_dir = os.path.join(formatted_path, f"{game_name} - {mod_name}")
                
                if not os.path.exists(new_dir):
                    os.makedirs(new_dir)
                    #print(f"Created directory: {new_dir}")
                
                source_file = os.path.join(root, file)
                destination_file = os.path.join(new_dir, f"{version}.pchtxt")
                
                shutil.copy(source_file, destination_file)
                #print(f"Copied {source_file} to {destination_file}")

def main(folder_path):
    create_formatted_structure(folder_path)
    print("Files have been organized successfully.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python format_repo_4.py /path/to/folder/")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    main(folder_path)
