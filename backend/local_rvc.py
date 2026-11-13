"""Verified, user-installed RVC v2 speakers. Weights are never unpickled by the server."""
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from .engine import ROOT, load_graph

DIRECTORY = ROOT / "models/local-rvc"
REGISTRY = DIRECTORY / "profiles.json"


@dataclass(frozen=True)
class Profile:
    label: str
    graph: str
    index: Path
    sample_rate: int
    target_hz: float
    semitones: float | None
    index_rate: float
    protect: float
    source: str


def verified_file(relative, expected):
    path = (DIRECTORY / relative).resolve()
    if not path.is_relative_to(DIRECTORY.resolve()) or not path.is_file():
        raise ValueError(f"Installed RVC file is missing or outside its directory: {relative}")
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise ValueError(f"Installed RVC file failed its SHA-256 check: {relative}")
    return path


@lru_cache(maxsize=3)
def profile(voice):
    if not REGISTRY.exists():
        return None
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if registry.get("version") != 1:
        raise ValueError("Unsupported local RVC registry version")
    data = registry.get("voices", {}).get(voice)
    if data is None:
        return None
    graph = verified_file(data["graph"], data["graph_sha256"])
    index = verified_file(data["index"], data["index_sha256"])
    rate, target = int(data["sample_rate"]), float(data["target_hz"])
    ratio, protect = float(data["index_rate"]), float(data["protect"])
    shift = data.get("semitones")
    if (rate not in (32000, 40000, 48000) or not 80 <= target <= 650
            or not 0 <= ratio <= 1 or not 0 <= protect <= .5
            or shift is not None and not -24 <= float(shift) <= 24):
        raise ValueError("Invalid local RVC inference settings")
    return Profile(str(data.get("label", voice)), graph.relative_to(ROOT / "models").as_posix(), index, rate, target,
                   None if shift is None else float(shift), ratio, protect, data.get("source", "user model"))


@lru_cache(maxsize=3)
def graph(voice):
    return load_graph(profile(voice).graph)
