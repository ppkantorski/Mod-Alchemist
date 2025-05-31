import os
import shutil
import unicodedata
import sys

def sanitize_name(name):
    # Remove accents and unwanted characters
    normalized = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    cleaned = normalized.replace("'", "").replace("’", "").replace("`", "").replace('"', '')
    cleaned = cleaned.replace(" - ", " ")  # Remove " - " to avoid duplication
    cleaned = ' '.join(cleaned.split())  # Collapse multiple spaces
    return cleaned.strip()

def title_case_preserve_numbers(name):
    # Capitalize title correctly with exceptions for filler words in the middle
    lowercase_exceptions = {
        "a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "nor",
        "of", "on", "or", "so", "the", "to", "yet", "with"
    }

    words = name.split()
    result = []

    for i, word in enumerate(words):
        if (0 < i < len(words) - 1) and word.lower() in lowercase_exceptions:
            result.append(word.lower())
        else:
            result.append(word.capitalize())

    return ' '.join(result)

def create_formatted_structure(root_folder):
    formatted_path = os.path.join(root_folder, 'formatted')
    os.makedirs(formatted_path, exist_ok=True)
    print(f"Creating formatted structure at: {formatted_path}")

    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.endswith('.pchtxt'):
                version = file.replace('.pchtxt', '').strip()

                # Extract game name from parent folder
                game_name = os.path.basename(os.path.dirname(os.path.join(root, file)))
                game_name = sanitize_name(game_name)

                # Remove trailing "Graphics" if it exists from old names
                if game_name.endswith("Graphics"):
                    game_name = game_name[:-len("Graphics")].strip()

                # Apply proper title casing
                game_name = title_case_preserve_numbers(game_name)

                mod_name = "Graphics Mods"
                target_dir = os.path.join(formatted_path, f"{game_name} - {mod_name}")
                os.makedirs(target_dir, exist_ok=True)

                source_path = os.path.join(root, file)
                dest_path = os.path.join(target_dir, f"{version}.pchtxt")

                shutil.copy2(source_path, dest_path)
                print(f"Copied {source_path} → {dest_path}")

def main(folder_path):
    create_formatted_structure(folder_path)
    print("Done!")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python collect_graphics_mods.py /path/to/root/folder")
        sys.exit(1)

    folder_path = sys.argv[1]
    main(folder_path)
