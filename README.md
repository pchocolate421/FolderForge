# FolderForge

A command-line tool for exporting and recreating directory structures. FolderForge is a simple but powerful utility that allows you to easily document the layout of a folder by exporting its structure to a text file. You can then use that same file to recreate the exact folder and file hierarchy on any machine. This is perfect for documenting project layouts, creating templates, or sharing a consistent structure with your team.

## 📝 Features

*   **Export:** Generate a tree-like text representation of any directory.
*   **Create:** Build a complete folder and file structure from a text file.
*   **Filtering:** Use glob patterns to ignore specific directories during export.
*   **Depth Control:** Limit the export to a specific number of directory levels.

## 🚀 Getting Started

To use FolderForge, you can simply run the script from your terminal. Since all dependencies are part of the Python standard library, there's no need to install anything.

1.  Clone the repository:

    ```bash
    git clone [https://github.com/your-username/folderforge.git]
    cd folderforge
    ```
2.  Run the script:

    You can run the script directly with `python folderforge.py`. For convenience, you may want to add it to your system's PATH.

## 🛠️ Usage

FolderForge has two main commands: `export` and `create`.

### `export`

Exports a directory tree to a text file.

```bash
python folderforge.py export <root_directory> [options]