import json
import os
import re


def phonetic_reduce(word, is_persian=False):
    word = word.lower()
    if is_persian:
        groups = {
            "ب": "b",
            "پ": "p",
            "ت": "t",
            "ط": "t",
            "د": "d",
            "ث": "s",
            "س": "s",
            "ص": "s",
            "ذ": "z",
            "ز": "z",
            "ض": "z",
            "ظ": "z",
            "ک": "k",
            "گ": "g",
            "ق": "k",
            "غ": "k",
            "خ": "k",
            "ج": "j",
            "چ": "c",
            "ش": "s",
            "ژ": "j",
            "ف": "f",
            "ل": "l",
            "ر": "r",
            "م": "m",
            "ن": "n",
            "ح": "h",
            "ه": "h",
            "و": "",
            "ی": "",
            "ا": "",
            "آ": "",
            "ع": "",
            "ئ": "",
            "ء": "",
            " ": "",
            "-": "",
        }
    else:
        word = word.replace("ch", "c")
        word = word.replace("sh", "s")
        word = word.replace("ph", "f")
        word = re.sub(r"[aeiouywh]", "", word)
        groups = {
            "b": "b",
            "p": "p",
            "t": "t",
            "d": "d",
            "s": "s",
            "z": "z",
            "c": "c",
            "x": "s",
            "k": "k",
            "g": "g",
            "q": "k",
            "j": "j",
            "f": "f",
            "v": "v",
            "l": "l",
            "r": "r",
            "m": "m",
            "n": "n",
        }

    res = []
    for char in word:
        if char in groups:
            val = groups[char]
            if val:
                res.append(val)

    return "".join(res)


def is_transliterated(en, fa):
    en_p = phonetic_reduce(en, is_persian=False)
    fa_p = phonetic_reduce(fa, is_persian=True)

    if not en_p or not fa_p:
        return False

    if en_p == fa_p:
        return True

    if abs(len(en_p) - len(fa_p)) <= 2:
        if en_p in fa_p or fa_p in en_p:
            return True

        matches = 0
        i, j = 0, 0
        while i < len(en_p) and j < len(fa_p):
            if en_p[i] == fa_p[j]:
                matches += 1
                i += 1
                j += 1
            elif len(en_p) > len(fa_p):
                i += 1
            else:
                j += 1
        if matches >= max(len(en_p), len(fa_p)) - 2:
            return True

    return False


def main():
    input_file = "enfa.json"
    trans_file = "t.json"

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    print(f"Loading {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if os.path.exists(trans_file):
        print(f"Loading existing {trans_file}...")
        with open(trans_file, "r", encoding="utf-8") as f:
            transliterated = json.load(f)
    else:
        transliterated = {}

    remaining = {}

    new_count = 0
    total = len(data)
    print(f"Processing {total} entries...")

    for i, (en, fa) in enumerate(data.items()):
        if is_transliterated(en, fa):
            transliterated[en] = fa
            new_count += 1
        else:
            remaining[en] = fa

        if (i + 1) % 50000 == 0:
            print(f"Processed {i + 1}/{total}...")

    print(f"Found {new_count} new transliterated words.")

    print(f"Updating {trans_file}...")
    with open(trans_file, "w", encoding="utf-8") as f:
        json.dump(transliterated, f, ensure_ascii=False, indent=2)

    print(f"Updating {input_file}...")
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(remaining, f, ensure_ascii=False, indent=2)

    print("Done.")
    print(
        f"Summary: New Transliterated: {new_count}, Total Transliterated: {len(transliterated)}, Remaining: {len(remaining)}"
    )


if __name__ == "__main__":
    main()
