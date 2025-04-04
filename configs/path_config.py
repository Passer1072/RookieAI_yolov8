import os
from pathlib import Path
import sys

HOME_PATH = Path(os.path.realpath(sys.argv[0])).parent

DATA_PATH = HOME_PATH / "data"

DLL_PATH = HOME_PATH / "DLLs"
