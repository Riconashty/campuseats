import sys
from pathlib import Path

# Ensures src/ is on sys.path so 'import campuseats' works seamlessly
src_path = str(Path(__file__).resolve().parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

if __name__ == '__main__':
    print("Hello, CampusEats!")
