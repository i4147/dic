import json
import sys
import os

def is_transliteration(farsi_words):
    if not farsi_words:
        return False
    
    for farsi in farsi_words:
        
        if ' ' in farsi:
            continue
        
        
        return True
    
    return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_file.json>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    
    if os.path.exists('t.json'):
        with open('t.json', 'r', encoding='utf-8') as f:
            transliterations = json.load(f)
    else:
        transliterations = {}
    
    
    remaining = {}
    moved_count = 0
    
    for key, value in data.items():
        if is_transliteration(value):
            transliterations[key] = value
            moved_count += 1
        else:
            remaining[key] = value
    
    
    with open('t.json', 'w', encoding='utf-8') as f:
        json.dump(transliterations, f, ensure_ascii=False, indent=2)
    
    
    with open(input_file, 'w', encoding='utf-8') as f:
        json.dump(remaining, f, ensure_ascii=False, indent=2)
    
    print(f"Moved {moved_count} transliterated records to t.json")
    print(f"Remaining records in {input_file}: {len(remaining)}")

if __name__ == '__main__':
    main()