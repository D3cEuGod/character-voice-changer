import numpy as np
from scipy.signal import correlate

from .engine import RATE
from .character import CharacterModel

FRAME = 8192
SHORT_FRAME = 4410
OVERLAP = 1024
SPEECH_LOOKAHEAD = 2304
JOIN = 320
SEARCH = 110
FADE = np.linspace(0, 1, JOIN, dtype="float32")


def pcm(samples):
    return np.rint(np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()


class LiveVoice:
    """Keep acoustic context and a short lookahead at packet edges."""
    def __init__(self, voice_id, strength, lookahead=OVERLAP):
        self.model = CharacterModel(voice_id, strength)
        self.lookahead = lookahead
        self.history = np.zeros(RATE, np.float32)
        self.tail = np.empty(0, np.float32)

    def process(self, frame):
        count = len(frame)
        self.history[:-count] = self.history[count:]
        self.history[-count:] = frame
        rendered = self.model.render(self.history, count)
        start = RATE-count-(self.lookahead if self.tail.size else 0)
        end = RATE-self.lookahead
        shift = 0
        if self.tail.size and self.model.strength > 0:
            # SOLA: align the overlapping voiced cycles before mixing them.
            probe = rendered[start-SEARCH:start+JOIN+SEARCH]
            old = self.tail[:JOIN]
            energy = np.convolve(probe**2, np.ones(JOIN, np.float32), mode="valid")
            scores = correlate(probe, old, mode="valid") / np.sqrt(np.maximum(energy, 1e-9))
            if np.mean(old**2) > 1e-7 and scores.max() > 0.3 * np.linalg.norm(old):
                shift = int(scores.argmax()) - SEARCH
        result = rendered[start+shift:end+shift].copy()
        if self.tail.size:
            result[:JOIN] = self.tail[:JOIN]*(1-FADE) + result[:JOIN]*FADE
        # Keep nominal duration even when the best join lies a few samples later.
        self.tail = rendered[end+shift:].copy()
        if len(self.tail) < self.lookahead:
            self.tail = np.pad(self.tail, (0, self.lookahead-len(self.tail)), mode="edge")
        return result

    def feed(self, data):
        frame = np.frombuffer(data, dtype="<i2").astype("float32") / 32768
        return pcm(self.process(frame))

    def flush(self):
        if not self.tail.size:
            return self.tail.copy()
        # Supply real lookahead to the denoiser and vocoder for the last syllable.
        last = self.process(np.zeros(SHORT_FRAME, np.float32))[:self.lookahead]
        self.tail = np.empty(0, np.float32)
        return last

    def finish(self):
        return pcm(self.flush())
