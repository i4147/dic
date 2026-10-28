import re
import sys
from pathlib import Path

def remove_parentheses_inplace(file_path):
    path = Path(file_path)
    
    if not path.is_file():
        print(f"Error: '{file_path}' is not a valid file.", file=sys.stderr)
        sys.exit(1)

    # Regular expression to match text inside parentheses and the parentheses themselves
    pattern = re.compile(r'\s*\([^)]*\)')

    try:
        # Read the entire content of the file
        content = path.read_text(encoding='utf-8')
        
        # Remove the parentheses
        cleaned_content = pattern.sub('', content)
        
        # Write the cleaned content back to the same file
        path.write_text(cleaned_content, encoding='utf-8')
        print(f"Successfully updated '{file_path}' inplace.", file=sys.stderr)
        
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python script.py <input_file>", file=sys.stderr)
        sys.exit(1)
        
    remove_parentheses_inplace(sys.argv[1])
