"""Rebuild legacy timbre vectors from the verified original recordings in assets/references."""
import numpy as np

from backend.engine import ROOT, RATE, VOICES, decode, tone_spec, tone_embedding


def main():
    output = ROOT / "voices"
    output.mkdir(exist_ok=True)
    for voice in VOICES:
        recording = ROOT / "assets/references" / f"{voice}.wav"
        audio = decode(recording.read_bytes())
        parts = [audio[start:start + 4 * RATE] for start in range(0, len(audio), 4 * RATE)]
        vectors = [tone_embedding(tone_spec(part)) for part in parts if len(part) >= RATE // 4]
        vector = np.mean(vectors, axis=0).astype(np.float32)
        if vector.shape != (1, 256, 1) or not np.isfinite(vector).all():
            raise ValueError(f"Invalid reference vector: {voice}")
        path = output / f"{voice}.npy"
        temporary = path.with_suffix(".tmp")
        with temporary.open("wb") as stream:
            np.save(stream, vector, allow_pickle=False)
        temporary.replace(path)
        print(f"{voice}: reference vector rebuilt from {recording.name}", flush=True)


if __name__ == "__main__":
    main()
