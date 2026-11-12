import numpy as np
from scipy.signal import correlate, firwin

from .engine import RATE
from .character import CharacterModel

FRAME = 8192
SHORT_FRAME = 4410
OVERLAP = 1024
SPEECH_LOOKAHEAD = 2304
JOIN = 320
SEARCH = 110
FADE = np.linspace(0, 1, JOIN, dtype="float32")
# Keep the level through each packet join (see blend). False restores the plain linear fade.
LEVEL_JOIN = True
SPLIT_PAD = 31
SPLIT = firwin(2 * SPLIT_PAD + 1, 2500, fs=RATE).astype("float32")


def pcm(samples):
    return np.rint(np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()


def blend(old, new):
    """Crossfade two renderings of the same 14.5 ms without the level sagging in the middle.

    old and new carry SPLIT_PAD samples of context on both sides. A linear fade only keeps
    the level when both signals are identical; the vocoder's noise-like components differ
    between renderings and lose up to half their power halfway through. Each band is
    therefore scaled by the gain that restores its level for the correlation measured
    between the two renderings: 1 where they agree, up to sqrt(2) where they are unrelated.
    """
    core = slice(SPLIT_PAD, SPLIT_PAD + JOIN)
    out = np.zeros(JOIN, np.float32)
    old_low, new_low = np.convolve(old, SPLIT, mode="valid"), np.convolve(new, SPLIT, mode="valid")
    for a, b in ((old_low, new_low), (old[core] - old_low, new[core] - new_low)):
        power = float(np.sqrt(np.dot(a, a) * np.dot(b, b)))
        agreement = float(np.clip(np.dot(a, b) / power, 0, 1)) if power > 1e-9 else 1.0
        gain = 1 / np.sqrt((1 - FADE)**2 + FADE**2 + 2 * FADE * (1 - FADE) * agreement)
        out += (a * (1 - FADE) + b * FADE) * gain
    return out


class LiveVoice:
    """Keep acoustic context and a short lookahead at packet edges."""
    def __init__(self, voice_id, strength, lookahead=OVERLAP):
        self.model = CharacterModel(voice_id, strength)
        self.lookahead = lookahead
        self.history = np.zeros(RATE, np.float32)
        self.tail = np.empty(0, np.float32)
        self.sent = np.zeros(SPLIT_PAD, np.float32)  # the samples emitted just before the tail

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
        if self.tail.size and LEVEL_JOIN and self.model.strength > 0:
            first = start + shift
            result[:JOIN] = blend(np.concatenate((self.sent, self.tail[:JOIN+SPLIT_PAD])),
                                  rendered[first-SPLIT_PAD:first+JOIN+SPLIT_PAD])
        elif self.tail.size:
            result[:JOIN] = self.tail[:JOIN]*(1-FADE) + result[:JOIN]*FADE
        self.sent = result[-SPLIT_PAD:].copy()
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
