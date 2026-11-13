"""Install Seed-VC's isolated CUDA runtime and pinned model files on NVIDIA systems."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from setup_models import fetch

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / ".run/seed-env/Scripts/python.exe"


def main():
    if os.environ.get("VOICE_REFERENCE_ENGINE") != "seed":
        return
    if not shutil.which("nvidia-smi"):
        print("Seed-VC CUDA runtime skipped. Existing RVC voices are available.")
        return
    if not PYTHON.is_file():
        PYTHON.parent.parent.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "venv", str(PYTHON.parent.parent)], check=True)
    check = "from importlib.metadata import version; assert version('torch')=='2.7.1+cu128' and version('torchaudio')=='2.7.1+cu128'"
    if subprocess.run([str(PYTHON), "-c", check], capture_output=True).returncode:
        subprocess.run([str(PYTHON), "-m", "pip", "install", "--no-cache-dir", "torch==2.7.1", "torchaudio==2.7.1",
                        "--index-url", "https://download.pytorch.org/whl/cu128"], check=True)
    requirements = ROOT / "requirements-reference.txt"
    check = ("from importlib.metadata import version; from pathlib import Path; "
             "assert all(version(p)==v for p,v in (line.split('==') for line in "
             f"Path({str(requirements)!r}).read_text().splitlines() if line))")
    if subprocess.run([str(PYTHON), "-c", check], capture_output=True).returncode:
        subprocess.run([str(PYTHON), "-m", "pip", "install", "--no-cache-dir", "-r", str(requirements)], check=True)
    models = ROOT / "models/seed-vc"
    entries = json.loads((ROOT / "tools/seed_models.json").read_text(encoding="utf-8"))
    for entry in entries:
        target = models / entry["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        fetch(target, entry["url"], entry["sha256"])


if __name__ == "__main__":
    main()
