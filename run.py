import os
import sys
from pathlib import Path

# Ensures src/ is on sys.path so 'import campuseats' works seamlessly
src_path = str(Path(__file__).resolve().parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from campuseats import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", app.config.get("PORT", 5000)))
    app.run(host="0.0.0.0", port=port, debug=True)
