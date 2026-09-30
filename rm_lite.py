#!/usr/bin/env python3
import sys
import json

def is_transliteration(s):
    persian_specific = set("گچپژ")
    common_persian = set("شخزآذطظضثقفعهح")
    
    
    if any(c in persian_specific for c in s):
        return False
    
    
    count = sum(1 for c in s if c in common_persian)
    
    
    return count == 0

def clean_entry(translations):
    if not isinstance(translations, list):
        return translations
    
    
    kept = [t for t in translations if not is_transliteration(t)]
    
    
    if not kept:
        kept = translations
    
    return kept

def main():
    if len(sys.argv) != 2:
        print("Usage: python clean_dict.py <dict.json>")
        sys.exit(1)
    
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    cleaned = {k: clean_entry(v) for k, v in data.items()}
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    
    print(f"Updated {path}")

if __name__ == "__main__":
    main()