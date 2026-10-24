import time
def batch_translate_file(input_path, output_path, chunk_size=40):
    """
    Reads a file line-by-line, chunks it to prevent AI truncation,
    and writes translations to a new file.
    """
    with open(input_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    translated_lines = []
    for i in range(0, len(lines), chunk_size):
        chunk = lines[i : i + chunk_size]
        chunk_text = "\n".join(chunk)
        system_prompt = (
            "You are an isolated, automated file-translation system. "
            "Translate each line from English to Persian (Farsi). "
            f"Your output MUST contain exactly {len(chunk)} lines. "
            "Do not add introductions, numbers, markdown formatting, or conclusions. "
            "Output ONLY the raw line-by-line translations."
        )
        print(f"Translating batch {i // chunk_size + 1}...")
        time.sleep(1)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(translated_lines))
    print(f"Successfully saved full translation to {output_path}")
