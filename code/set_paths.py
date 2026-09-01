from pathlib import Path

def get_project_root():
    try:
        start = Path(__file__).resolve().parent
    except NameError:
        start = Path.cwd().resolve()

    for path in [start] + list(start.parents):
        if (path / "code").exists() and (path / "notebooks").exists():
            return path

    return start

PROJECT_ROOT = get_project_root()
print ("Project Root: ", PROJECT_ROOT)

SRC_DIR = PROJECT_ROOT / "code"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
OUTPUTS_DIR = PROJECT_ROOT / "output"