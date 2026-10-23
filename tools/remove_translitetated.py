#!/usr/bin/env python3
"""
Detect and remove transliterated Persian translations from an English-Persian dictionary.
Saves removed items to a separate JSON file for reference.
Usage: python script.py <dictionary.json>
"""

import sys
import json
import re
from pathlib import Path


def is_transliterated(persian_text: str) -> bool:
    """
    Detect if a Persian text is just a transliteration (phonetic copy) of English.
    Strategy: Check if the text contains mostly Persian characters that are
    phonetic equivalents of English letters without meaningful Persian words.
    """
    # Remove common Persian diacritics and normalize
    text = persian_text.strip()

    # If empty or too short, consider it transliterated
    if not text or len(text) < 2:
        return True

    # Persian alphabet characters
    persian_chars = set("ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی")

    # Count Persian characters
    persian_count = sum(1 for c in text if c in persian_chars)

    # If less than 60% Persian characters, it's likely transliteration
    if persian_count / len(text) < 0.6:
        return True

    # Check for common transliteration patterns
    # Words that are just phonetic copies (like زیمولوژی for zymology)
    # Often contain these patterns: زیمو (zymo), دیاستاز (diastase), etc.
    transliteration_patterns = [
        r"^زیمو",  # zymo prefix
        r"^انزیم",  # enzyme
        r"^مخمر",  # yeast (but this could be real translation)
        r"^تخمیر",  # fermentation (real translation)
    ]

    # Check if it's a single word without spaces (likely transliteration)
    words = text.split()
    if len(words) == 1 and len(text) > 5:
        # Single long word - could be transliteration
        # Check if it contains typical transliteration suffixes
        if re.search(r"(ولوژی|پلاستیک|سکوپ|ستنیک|تیک)$", text):
            return True

    # Check for mixed English/Persian characters
    english_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
    if any(c in english_chars for c in text):
        return True

    return False


def process_dictionary(filepath: Path):
    """Process the dictionary file and remove transliterated entries."""
    try:
        # Read the JSON file
        with open(filepath, "r", encoding="utf-8") as f:
            dictionary = json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{filepath}': {e}")
        sys.exit(1)

    removed_count = 0
    removed_entries = {}

    # Process each entry
    for word, translations in list(dictionary.items()):
        if not isinstance(translations, list):
            continue

        # Filter out transliterated translations
        original_count = len(translations)
        filtered_translations = [t for t in translations if not is_transliterated(t)]

        # If we removed something, report it
        if len(filtered_translations) != original_count:
            removed = [t for t in translations if t not in filtered_translations]
            removed_entries[word] = removed
            removed_count += len(removed)

            # Update the dictionary
            if filtered_translations:
                dictionary[word] = filtered_translations
            else:
                # If all translations were removed, remove the entry entirely
                del dictionary[word]

    # Write the updated dictionary back
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, ensure_ascii=False, indent=2)

    # Save removed items to a separate JSON file
    if removed_entries:
        removed_filepath = filepath.with_name(filepath.stem + "_removed.json")
        with open(removed_filepath, "w", encoding="utf-8") as f:
            json.dump(removed_entries, f, ensure_ascii=False, indent=2)
        print(f"\nRemoved items saved to: {removed_filepath}")

    # Report results
    print(f"\n{'=' * 60}")
    print(f"Processing complete!")
    print(f"Total transliterated items removed: {removed_count}")
    print(f"{'=' * 60}\n")

    if removed_entries:
        print("Removed entries:")
        print("-" * 60)
        for word, removed in removed_entries.items():
            print(f"  '{word}':")
            for item in removed:
                print(f"    - {item}")
        print("-" * 60)
    else:
        print("No transliterated entries found.")


def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <dictionary.json>")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    process_dictionary(filepath)


if __name__ == "__main__":
    main()
