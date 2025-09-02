#!/usr/bin/env python3
import argparse
import fnmatch
import os
from pathlib import Path
import re
from typing import Iterable, List, Optional

# =========================
# Export mode
# =========================
def load_ignore_patterns(ignore: Iterable[str], ignore_file: Optional[Path]) -> List[str]:
    patterns = list(ignore) if ignore else []
    if ignore_file:
        for line in ignore_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            patterns.append(line)
    return patterns

def should_ignore_dir(dir_path: Path, root: Path, patterns: List[str]) -> bool:
    if not patterns:
        return False
    rel = dir_path.relative_to(root).as_posix()
    name = dir_path.name
    return any(
        fnmatch.fnmatch(name, p) or fnmatch.fnmatch(rel, p.rstrip("/"))
        for p in patterns
    )

def write_tree(root: Path, output_file: Path, ignore_patterns: List[str], verbose: bool, max_depth: Optional[int]) -> None:
    def _tree(dir_path: Path, prefix: str = "", current_depth: int = 0) -> list[str]:
        if max_depth is not None and current_depth > max_depth:
            return []

        if verbose:
            print(f"[SCAN] {dir_path}")

        entries = sorted(
            (e for e in dir_path.iterdir() if not (e.is_dir() and should_ignore_dir(e, root, ignore_patterns))),
            key=lambda e: (not e.is_dir(), e.name.lower()),
        )

        lines = []
        for i, entry in enumerate(entries):
            if entry.is_dir() and should_ignore_dir(entry, root, ignore_patterns):
                if verbose:
                    print(f"[SKIP] Ignored folder: {entry}")
                continue

            connector = "└─ " if i == len(entries) - 1 else "├─ "
            line = prefix + connector + entry.name + ("/" if entry.is_dir() else "")
            lines.append(line)

            if entry.is_dir():
                extension = "   " if i == len(entries) - 1 else "│  "
                lines.extend(_tree(entry, prefix + extension, current_depth + 1))

        return lines

    if verbose:
        print(f"[EXPORT] Starting from root: {root}")

    lines = [root.name + "/"] if max_depth is None or max_depth >= 0 else []
    if max_depth is None or max_depth > 0:
        lines.extend(_tree(root, current_depth=0))

    output_file.write_text("\n".join(lines), encoding="utf-8")
    if verbose:
        print(f"[DONE] Structure exported to: {output_file}")

# =========================
# Create mode
# =========================
# Corrected regex to handle a single space after the connector and improved name capture.
LINE_RE = re.compile(r'^(?P<prefix>(?:│  |   )*)(?P<conn>├── |└── |├─ |└─ )?(?P<name>[^/]+?)(?P<slash>/?)$')

def parse_line(line: str):
    if not line.strip():
        return None
    
    m = LINE_RE.match(line.rstrip("\n"))
    if not m:
        # Fallback for the root line which might not match the full pattern
        if not re.match(r'^[a-zA-Z0-9_-]+/?$', line.strip()):
            return None
        return (True, 0, line.strip().rstrip('/'), line.strip().endswith('/'))

    prefix = m.group("prefix") or ""
    conn = m.group("conn")
    name = (m.group("name") or "").strip()
    is_dir = bool(m.group("slash"))
    is_root_line = conn is None and prefix == ""
    
    # Standardize spaces for depth calculation
    normalized_prefix = prefix.replace("│  ", "   ")
    depth = 0 if is_root_line else len(normalized_prefix) // 3
    
    # Strip trailing slash from name if it's a directory
    if is_dir and name.endswith('/'):
        name = name[:-1]

    return (is_root_line, depth, name, is_dir)

def create_structure_from_file(file_path: Path, dest_root: Path, strip_root: bool, verbose: bool) -> None:
    lines = file_path.read_text(encoding="utf-8").splitlines()
    base_dir = dest_root
    dirs_stack: List[Path] = []
    
    first_line_is_root = False
    
    # Pre-process lines to determine if the first line is a root directory
    if lines:
        first_parsed = parse_line(lines[0])
        if first_parsed and first_parsed[0]:
            first_line_is_root = True
            
    if verbose:
        print(f"[CREATE] Starting from root: {dest_root}")

    for i, raw in enumerate(lines):
        parsed = parse_line(raw)
        if not parsed:
            continue

        is_root_line, depth, name, is_dir = parsed

        if is_root_line and first_line_is_root:
            if not strip_root:
                base_dir = dest_root / name
                base_dir.mkdir(parents=True, exist_ok=True)
                if verbose:
                    print(f"[CREATE] Root directory: {base_dir}")
                dirs_stack.append(base_dir)
            elif verbose:
                print(f"[SKIP] Root folder '{name}' ignored (--strip-root enabled)")
            # Do not process the root line again
            continue

        # Adjust the directory stack based on depth
        if depth > len(dirs_stack):
            # This should not happen with correctly formatted files
            continue
        elif depth < len(dirs_stack):
            dirs_stack = dirs_stack[:depth]

        # Use the correct parent directory
        parent = base_dir if depth == 0 else dirs_stack[-1]
        target = parent / name
        
        if is_dir:
            target.mkdir(parents=True, exist_ok=True)
            if verbose:
                print(f"[DIR] {target}")
            # Ensure the stack is at the correct depth before appending
            while len(dirs_stack) > depth:
                dirs_stack.pop()
            dirs_stack.append(target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "a", encoding="utf-8"):
                pass
            if verbose:
                print(f"[FILE] {target}")

    if verbose:
        print(f"[DONE] Folder structure created in: {base_dir if base_dir != dest_root else dest_root}")

# =========================
# CLI
# =========================
def main():
    parser = argparse.ArgumentParser(description="Export or create folder structures.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Export folder structure to a text file.")
    export_parser.add_argument("root", help="Root directory to export.")
    export_parser.add_argument("-o", "--output", default="structure.txt", help="Output file path.")
    export_parser.add_argument("--ignore", action="append", default=[], help="Glob pattern for directories to ignore.")
    export_parser.add_argument("--ignore-file", type=Path, help="File with glob patterns to ignore.")
    export_parser.add_argument("--verbose", action="store_true", help="Show detailed actions.")
    export_parser.add_argument("--depth", type=int, default=None, help="Maximum depth of the directory tree to export (0 for root only, None for unlimited).")

    create_parser = subparsers.add_parser("create", help="Create folder structure from a text file.")
    create_parser.add_argument("file", type=Path, help="Path to the text file containing the folder structure.")
    create_parser.add_argument("-d", "--dir", type=Path, default=Path("."), help="Destination root directory.")
    create_parser.add_argument("--strip-root", action="store_true", help="Ignore the top-level root line.")
    create_parser.add_argument("--verbose", action="store_true", help="Show detailed actions.")

    args = parser.parse_args()

    if args.command == "export":
        root_dir = Path(args.root).resolve()
        out_file = Path(args.output).resolve()
        if not root_dir.is_dir():
            print(f"Error: {root_dir} is not a valid directory")
            return
        patterns = load_ignore_patterns(args.ignore, args.ignore_file)
        write_tree(root_dir, out_file, patterns, args.verbose, args.depth)

    elif args.command == "export":
        root_dir = Path(args.root).resolve()
        out_file = Path(args.output).resolve()
        if not root_dir.is_dir():
            print(f"Error: {root_dir} is not a valid directory")
            return
        patterns = load_ignore_patterns(args.ignore, args.ignore_file)
        write_tree(root_dir, out_file, patterns, args.verbose, args.depth)

if __name__ == "__main__":
    main()