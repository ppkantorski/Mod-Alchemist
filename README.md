# Mod Alchemist (Ultrahand v1.6.5+)
An Ultrahand package designed for managing and converting mods.

![banner](.pics/banner.png)

## Configuration

The `package.ini` file contains the following configurations:

### Mod Management
- `[*Toggle exeFS Patches]`: Toggles exeFS patches by selection.
- `[*Delete exeFS Patches]`: Deletes selected exeFS patches.
- `[*Toggle Content Mods]`: Toggles content modifications by selection.
- `[*Delete Content Mods]`: Deletes selected content modifications.
- `[*Search Pattern]`: Configure search patterns for mod groups.
- `[Enable All]`: Enables all mods based on search patterns.
- `[Disable All]`: Disables all mods based on search patterns.

### Mod Conversion
- `[*pchtxt -> ips]`: Converts pchtxt files to IPS patches.
- `[*pchtxt -> cheat]`: Converts pchtxt files to cheat codes.

Each configuration has a set of commands that perform the corresponding actions. The commands include moving, deleting, creating directories, copying files, and converting files to specific formats.

## Obtaining Mods

To use the mods provided in the Mod Alchemist package, you will need to obtain them separately. The mods should be placed in the appropriate folders within the `Mod Alchemist` directory.

Please refer to the shared documentation or additional resources to acquire the specific mods you are interested in. Once you have obtained the mods, place them in the corresponding folders within the `Mod Alchemist` directory.

## Installation

To install `Mod Alchemist`:

1. Copy the `Mod Alchemist` directory to `/switch/.packages/`.

Note: Make sure you have organized the mods properly within the subdirectories as mentioned in the "Obtaining Mods" section.

## Additional Information

For more details on the Ultrahand Overlay project and its features, please refer to the [official GitHub repository](https://github.com/ppkantorski/Ultrahand-Overlay).
