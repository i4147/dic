import json
import sys
fn=sys.argv[1]

with open(fn, 'r', encoding='utf-8') as f:
    data = json.load(f)


uniq = {}
remaining = {}

for key, translations in data.items():
    if isinstance(translations, list) and len(translations) == 1:
        uniq[key] = translations
    else:
        remaining[key] = translations


with open('uniq.json', 'w', encoding='utf-8') as f:
    json.dump(uniq, f, ensure_ascii=False, indent=2)


with open('dictionary_remaining.json', 'w', encoding='utf-8') as f:
    json.dump(remaining, f, ensure_ascii=False, indent=2)

print(f"Moved {len(uniq)} records to uniq.json")
print(f"{len(remaining)} records remain")
