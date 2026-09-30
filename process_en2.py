import json


def main():
    with open("en2.txt", "r", encoding="utf-8") as f:
        en2_words = [line.strip() for line in f if line.strip()]

    with open("enfa.json", "r", encoding="utf-8") as f:
        enfa = json.load(f)

    translated = {}
    missing = []

    for word in en2_words:
        if word in enfa:
            translated[word] = enfa[word]
        elif word.lower() in enfa:
            translated[word] = enfa[word.lower()]
        elif word.capitalize() in enfa:
            translated[word] = enfa[word.capitalize()]
        else:
            missing.append(word)

    print(f"Total words: {len(en2_words)}")
    print(f"Translated from enfa: {len(translated)}")
    print(f"Missing: {len(missing)}")

    with open("en2_partially_translated.json", "w", encoding="utf-8") as f:
        json.dump(translated, f, ensure_ascii=False, indent=2)

    with open("en2_missing.txt", "w", encoding="utf-8") as f:
        for word in missing:
            f.write(word + "\n")


if __name__ == "__main__":
    main()
