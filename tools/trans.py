import os
import time
def batch_translate_file(input_path="en.txt", output_path="translated.txt", batch_size=30):
    """
    Splits a single-word-per-line file into chunks to prevent AI truncation.
    """
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        return
    with open(input_path, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    total_words = len(words)
    print(f"Loaded {total_words} words. Processing in batches of {batch_size}...")
    with open(output_path, "w", encoding="utf-8") as f:
        pass
    for i in range(0, total_words, batch_size):
        chunk = words[i:i + batch_size]
        chunk_text = "\n".join(chunk)
        prompt = f"""You are a precise translation tool. Translate the following English words into target language. 
Output EXACTLY one translated word per line matching the input order. Do not include numbers, notes, explanations, or introductory text.

Input words:
{chunk_text}"""
        print(f"\n--- [Batch {i//batch_size + 1}] Send this text to Arena AI ---")
        print(prompt)
        print("---------------------------------------------------------")
        input("Press Enter once you have collected the translation from the AI to proceed...")
