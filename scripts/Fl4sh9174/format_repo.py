import os
import zipfile
import shutil
import re
import sys

def unzip_files(folder_path):
    print("Unzipping files...")
    for item in os.listdir(folder_path):
        if item.endswith('.zip'):
            file_path = os.path.join(folder_path, item)
            game_name = re.sub(r'\[.*?\]', '', item).replace('.zip', '').strip()
            extract_to = os.path.join(folder_path, game_name)
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
                print(f"Unzipped: {file_path} to {extract_to}")

def create_formatted_structure(folder_path):
    formatted_path = os.path.join(folder_path, 'formatted')
    if not os.path.exists(formatted_path):
        os.makedirs(formatted_path)
    print(f"Creating formatted structure at: {formatted_path}")

    for game_dir in os.listdir(folder_path):
        game_dir_path = os.path.join(folder_path, game_dir)
        if os.path.isdir(game_dir_path) and game_dir != 'formatted':
            for root, dirs, files in os.walk(game_dir_path):
                for file in files:
                    if file.endswith('.pchtxt'):
                        relative_path = os.path.relpath(root, folder_path)
                        mod_name_match = re.search(r'\[(.*?)\]', relative_path)
                        if mod_name_match:
                            mod_name_with_version = mod_name_match.group(1)
                            mod_name = re.sub(r' v[0-9.]+$', '', mod_name_with_version).strip()
                            game_name = game_dir
                            version = file.replace('.pchtxt', '').strip()
                            
                            new_dir = os.path.join(formatted_path, f"{game_name} - {mod_name}")
                            if not os.path.exists(new_dir):
                                os.makedirs(new_dir)
                                print(f"Created directory: {new_dir}")
                            
                            shutil.move(os.path.join(root, file), os.path.join(new_dir, f"{version}.pchtxt"))
                            print(f"Moved {file} to {os.path.join(new_dir, f'{version}.pchtxt')}")
            shutil.rmtree(game_dir_path)  # Remove the extracted game directory after processing

def main(folder_path):
    unzip_files(folder_path)
    create_formatted_structure(folder_path)
    print("Files have been organized successfully.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python format_repo.py /path/to/folder/of/zips/")
        sys.exit(1)
    
    folder_path = sys.argv[1]
    main(folder_path)
