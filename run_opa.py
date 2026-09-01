"""Repository launcher for the Orbital Perturbation Analyzer public edition."""

from pathlib import Path
import sys


SOURCE_DIRECTORY = Path(__file__).resolve().parent / "src"
if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIRECTORY))

from gui.main_window import main


if __name__ == "__main__":
    main()
