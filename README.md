# Alchemist (Ultrahand v2.1.0+)
An Ultrahand package for managing, converting, and installing mods on the Nintendo Switch.

![banner](.pics/banner.png)

## Overview

Alchemist is a comprehensive mod management package designed to streamline mod organization, conversion, and deployment. It supports exeFS patches, content mods, pchtxt conversion to IPS or cheat formats, and integrates utilities for maintaining a clean SD card environment. Mod repositories are managed dynamically, ensuring users can download, update, and install mods efficiently.

## Configuration

All options are accessible through `package.ini` and its included forwarders.

### Core Features

#### Title ID
- Dynamically tracks the current game using `Title ID`.  
- Automatically updates mod selection and installation paths based on the active title.

#### Mod Management
- `[*exeFS Patches]` and `[*Contents Mods]`: Forwarded sections to toggle, enable, or delete patches or content mods.  
- Search patterns can filter mods for bulk operations.  
- `Enable All` / `Disable All` options apply actions across filtered mods.

#### Mod Conversion
- `[*pchtxt -> ips]`: Converts `.pchtxt` files to IPS patches, creating the required folder structure automatically.  
- `[*pchtxt -> cheat]`: Converts `.pchtxt` files into cheat code format.  
- `[*Delete pchtxt]`: Cleans up `.pchtxt` files after conversion or installation.

#### Mod Installation
- `[*Install pchtxt]` and `[*Install Contents]`: Forwarded sections that install mods from the configured repositories.  
- Supports installation by title ID or search pattern.

#### Miscellaneous Tools
- `Dot Clean` removes macOS metadata files (`._*`) from `/atmosphere/`, `/switch/`, `/config/`, or the entire SD card.  
- `Software Update` integrates automatic updating of the Alchemist package and all associated mod repositories, with version information stored in `config.ini`.

## Obtaining Mods

Alchemist does not include mods directly. Mods are distributed through the Alchemist repositories:

- **Pchtxt Mods**: Available in [Alchemist Repos](https://github.com/ppkantorski/Alchemist-Repos). Users can download individual author packs or use the “Update All” feature within Alchemist.  
- **Content Mods**: Organized by title ID in the same repositories. Use the “Install Contents” section to deploy content mods to the correct directories.

Mods must be placed in the corresponding `repos/pchtxts/` or `repos/contents/` subfolders for Alchemist to process them correctly.

## Installation

1. Unzip `Alchemist.zip` to the root of your SD card. The `Alchemist` folder will appear under `/switch/.packages/`.  
2. Ensure that mods are organized in the `repos` subfolders as outlined above.  
3. Use the package menus to manage, convert, or install mods as needed.

## Additional Information

For detailed instructions, feature documentation, and support, see the [Ultrahand Overlay GitHub repository](https://github.com/ppkantorski/Ultrahand-Overlay).
