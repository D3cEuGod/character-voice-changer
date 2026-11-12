"""Rebuild the three OpenVoice reference vectors from pinned public recordings."""
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen

import numpy as np
from scipy.signal import resample_poly

from backend.engine import ROOT, RATE, decode, tone_spec, tone_embedding

LINES = ("https://raw.githubusercontent.com/telecom888/Live2dOnAndroid/"
         "af08c7b8a0c77444502f27fab0c19e88aeb3c923/app/src/main/assets/voices_builtin/")
TAFFY = ("https://huggingface.co/datasets/KYOU-0/Ace-Taffy-voice/resolve/"
         "48623d4de7338a82a83bd9c76a9a4ee193aadb3f/raw/2025-06-26_21-15/")


def read_line(url):
    with urlopen(url, timeout=60) as response:
        return decode(response.read())


def read_taffy(times):
    # The pinned source is signed PCM16 stereo, 48 kHz, with a 44-byte header.
    start, end = times
    first = 44 + 4 * round(start * 48000)
    last = 44 + 4 * round(end * 48000) - 1
    request = Request(TAFFY + "audio.wav", headers={"Range": f"bytes={first}-{last}"})
    with urlopen(request, timeout=60) as response:
        if not response.headers.get("Content-Range", "").startswith(f"bytes {first}-{last}/"):
            raise RuntimeError("Reference server did not return the requested excerpt")
        data = response.read(last-first+1)
        if len(data) != last-first+1:
            raise RuntimeError("Incomplete reference excerpt")
    stereo = np.frombuffer(data, dtype="<i2").reshape(-1, 2)
    return resample_poly(stereo.astype("float32").mean(axis=1) / 32768, 147, 320)


def main():
    output = ROOT / "voices"
    output.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=5) as pool:
        for key in ("taffy", "tomori", "anon"):
            if key == "taffy":
                tone_clips = pool.map(read_taffy, [(995.202, 998.814), (1008.482, 1025.726),
                                                  (1029.602, 1035.646), (1096.418, 1103.518)])
            else:
                tone_clips = pool.map(read_line, [f"{LINES}{key}/ja/{i}.mp3" for i in (0, 2, 3, 6, 9, 13)])
            vectors = []
            for clip in tone_clips:
                parts = [clip[i:i + 4 * RATE] for i in range(0, len(clip), 4 * RATE)]
                parts = sorted((x for x in parts if len(x) >= RATE // 4),
                               key=lambda x: np.mean(x**2), reverse=True)[:3]
                vectors.append(np.mean([tone_embedding(tone_spec(x)) for x in parts], axis=0))
            vector = np.mean(vectors, axis=0)
            if vector.shape != (1, 256, 1) or not np.isfinite(vector).all():
                raise ValueError(f"Invalid reference vector: {key}")
            path = output / f"{key}.npy"
            tmp = path.with_suffix(".tmp")
            with tmp.open("wb") as stream:
                np.save(stream, vector, allow_pickle=False)
            tmp.replace(path)
            print(f"{key}: saved reference vector", flush=True)


if __name__ == "__main__":
    main()
