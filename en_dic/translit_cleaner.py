import argparse
import json
import sys
from pathlib import Path

def is_transliterated(key, value):
    """
    Detects if the value is a transliteration of the key instead of a translation.
    Currently checks for an exact match or case-insensitive match.
    """
    return str(key).strip().lower() == str(value).strip().lower()

def process_bilingual_json():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Remove transliterated records from a bilingual JSON file.")
    parser.add_argument("input_file", help="Path to the JSON file to process.")
    parser.add_argument("-m", action="store_true", help="Save removed transliterated records to 'tl.json'.")
    
    args = parser.parse_args()
    input_path = Path(args.input_file)
    
    if not input_path.is_file():
        print(f"Error: '{args.input_file}' is not a valid file.", file=sys.stderr)
        sys.exit(1)
        
    try:
        # Load the original JSON data
        with input_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            
        if not isinstance(data, dict):
            print("Error: JSON root must be a dictionary/object.", file=sys.stderr)
            sys.exit(1)
            
        cleaned_data = {}
        removed_data = {}
        
        # Separate valid translations from transliterations
        for key, value in data.items():
            if is_transliterated(key, value):
                removed_data[key] = value
            else:
                cleaned_data[key] = value
                
        # Update the original file inplace
        with input_path.open("w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=4)
            
        # If -m flag is provided, save the removed items
        if args.m:
            tl_path = input_path.parent / "tl.json"
            with tl_path.open("w", encoding="utf-8") as f:
                json.dump(removed_data, f, ensure_ascii=False, indent=4)
            print(f"Saved removed records to {tl_path}", file=sys.stderr)
            
        print(f"Successfully updated '{args.input_file}' inplace.", file=sys.stderr)

    except json.JSONDecodeError:
        print(f"Error: '{args.input_file}' is not a valid JSON file.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    process_bilingual_json()
