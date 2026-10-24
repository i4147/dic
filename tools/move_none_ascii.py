"""
move_non_ascii_lowercase.py

Usage:
    python move_non_ascii_lowercase.py <input_file>

Reads <input_file>, keeps only lines that are pure ASCII lowercase (a-z),
moves every other line into mixed.txt, and rewrites the input file with
just the pure-lowercase lines.
"""
import sys
from pathlib import Path
def main() -> None:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <input_file>", file=sys.stderr)
        sys.exit(1)
    src = Path(sys.argv[1])
    if not src.is_file():
        print(f"error: {src} is not a file", file=sys.stderr)
        sys.exit(2)
    mixed_path = src.with_name("mixed.txt")
    pure: list[str] = []
    mixed: list[str] = []
    with src.open("r", encoding="utf-8", newline="") as fh:
        for line in fh:
            body = line.rstrip("\r\n")
            if body and all("a" <= ch <= "z" for ch in body):
                pure.append(line)
            else:
                mixed.append(line)
    with mixed_path.open("w", encoding="utf-8", newline="") as fh:
        fh.writelines(mixed)
    with src.open("w", encoding="utf-8", newline="") as fh:
        fh.writelines(pure)
    print(f"kept  {len(pure):>6} pure-lowercase lines in {src}")
    print(f"moved {len(mixed):>6} mixed / non-lowercase lines to {mixed_path}")
if __name__ == "__main__":
    main()
