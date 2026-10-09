from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "static"
DESTINATION = ROOT / "public" / "static"

shutil.copytree(
    SOURCE,
    DESTINATION,
    dirs_exist_ok=True,
    ignore=shutil.ignore_patterns("uploads"),
)
