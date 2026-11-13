"""One-second windows for the trained RVC v2 and So-VITS-SVC 3.0 speakers."""
from functools import lru_cache
from math import gcd

import numpy as np
import faiss
import parselmouth
from scipy.ndimage import maximum_filter1d, uniform_filter1d
from scipy.signal import butter, resample_poly, sosfilt
from scipy.signal.windows import hann

from .engine import ROOT, RATE, load_graph, refine_timbre, tone_embedding, tone_spec
from .pitch import pitch_track as rmvpe_pitch

VOICE_RATES = {"tomori": 48000, "anon": 40000, "taffy": 32000}
# How far OpenVoice pulls each trained voice toward its speaking reference; 0 skips the stage.
# On the eval set in tools/eval it lifts speaker similarity for Tomori (0.51 to 0.61) and
# Taffy (0.37 to 0.53), leaves Anon unchanged (0.65), and costs about 20 ms per packet.
TIMBRE_REFINE = {"tomori": 1.0, "anon": 0.0, "taffy": 1.0}
# Voiced windows averaged into the session's estimate of the trained voice's own timbre.
TONE_WINDOWS = 40
# Share of the band above 1.7 kHz taken from the denoised input, in unvoiced and in voiced frames.
CONSONANT_UNVOICED = 0.7
CONSONANT_VOICED = 0.25
# Taffy's character preset avoids mixing the caller's voiced harmonics back in.
CHARACTER_CONSONANT_UNVOICED = 0.35
CHARACTER_CONSONANT_VOICED = 0.0
# Conversational registers estimated from the project's speaker references.
REGISTER = {"tomori": 285, "anon": 310, "taffy": 315}
# Match typical speaking levels across the three independently trained vocoders.
OUTPUT_GAIN = {"tomori": .8, "anon": .8, "taffy": 3.0}
WINDOW = np.sqrt(hann(512, sym=False)).astype(np.float32)
MASK = np.ones((1, 16080), dtype=np.int64)
LATENT = np.zeros((1, 192, 100), dtype=np.float32)
CONSONANT_BAND = butter(3, 1700, btype="highpass", fs=RATE, output="sos")


@lru_cache(maxsize=None)
def graph(name):
    return load_graph(name + ".onnx", gpu=name not in ("gtcrn_simple", "silero_vad_16k_op15"))


@lru_cache(maxsize=2)
def voice_index(name):
    with (ROOT / "models" / (name + ".index")).open("rb") as stream:
        return faiss.read_index(faiss.PyCallbackIOReader(stream.read))


def retrieve(units, name, f0):
    faiss.omp_set_num_threads(2)
    distances, ids, vectors = voice_index(name).search_and_reconstruct(units[0], 8)
    weights = np.where(ids >= 0, np.reciprocal(np.maximum(distances, 1e-5))**2, 0)
    weights /= np.maximum(weights.sum(axis=1, keepdims=True), 1e-12)
    nearest = (np.nan_to_num(vectors) * weights[:, :, None]).sum(axis=1)
    mix = np.where(f0.reshape(-1, 2).max(axis=1) > 0, .38, .06).astype(np.float32)
    return units + (nearest[None] - units) * mix[None, :, None]


class SpeechDetector:
    def __init__(self):
        self.model = graph("silero_vad_16k_op15")
        self.state = np.zeros((2, 1, 128), np.float32)
        self.context = np.zeros(64, np.float32)
        self.pending = np.empty(0, np.float32)
        self.history = np.zeros(16000, np.float32)

    def process(self, samples):
        data = np.concatenate((self.pending, samples))
        consumed = len(data) // 512 * 512
        levels = np.empty(consumed, np.float32)
        for i in range(0, consumed, 512):
            block = data[i:i+512]
            probability, self.state = self.model.run(None, {
                "input": np.concatenate((self.context, block))[None],
                "state": self.state, "sr": np.asarray(16000, dtype=np.int64)})
            levels[i:i+512] = probability.item()
            self.context = block[-64:]
        self.pending = data[consumed:]
        self.history = np.concatenate((self.history, levels))[-16000:]
        scores = np.pad(self.history[len(self.pending):], (0, len(self.pending)), mode="edge")
        # Allow 96 ms on either side of detected speech for stops and fricatives.
        scores = maximum_filter1d(scores, 3073)
        return uniform_filter1d(np.clip((scores - .50) / .25, 0, 1), 160)


class StreamingDenoiser:
    """Keep GTCRN's recurrent state, STFT overlap and fractional hops across packets."""
    def __init__(self):
        self.model = graph("gtcrn_simple")
        self.caches = {a.name: np.zeros(a.shape, np.float32) for a in self.model.get_inputs()[1:]}
        self.previous = np.zeros(256, np.float32)
        self.overlap = np.zeros(256, np.float32)
        self.pending = np.empty(0, np.float32)
        self.history = np.zeros(16000, np.float32)
        self.source_count = 0
        self.detector = SpeechDetector()

    def process(self, window, count):
        previous = round(self.source_count * 16000 / RATE)
        self.source_count += count
        new_count = round(self.source_count * 16000 / RATE) - previous
        audio = resample_poly(window, 320, 441)
        activity = self.detector.process(audio[-new_count:])
        data = np.concatenate((self.pending, audio[-new_count:]))
        consumed = len(data) // 256 * 256
        clean = np.empty(consumed, np.float32)
        for i in range(0, consumed, 256):
            hop = data[i:i + 256]
            bins = np.fft.rfft(np.concatenate((self.previous, hop)) * WINDOW)
            spec = np.stack((bins.real, bins.imag), axis=-1).astype(np.float32)
            enhanced, *states = self.model.run(None, {"mix": spec[None, :, None, :], **self.caches})
            self.caches = dict(zip(self.caches, states))
            re, im = enhanced[0, :, 0].T
            block = WINDOW * np.fft.irfft(re + 1j * im, n=512)
            clean[i:i + 256] = self.overlap + block[:256]
            self.previous, self.overlap = hop, block[256:]
        self.pending = data[consumed:]
        self.history = np.concatenate((self.history, clean))[-16000:]
        # The converter withholds 46 ms at the right edge. The unresolved
        # 16–32 ms here is lookahead only and is never emitted as speech.
        lookahead = 256 + len(self.pending)
        clean = np.concatenate((self.history[lookahead:], audio[-lookahead:] * activity[-lookahead:]))
        return clean, activity


def pitch_track(audio):
    sound = parselmouth.Sound(audio, 16000)
    track = sound.to_pitch_ac(time_step=0.01, pitch_floor=65, pitch_ceiling=650,
                              voicing_threshold=0.48)
    # Praat omits the boundary analysis windows. Align by their timestamps.
    padded = np.zeros(100, np.float32)
    positions = np.rint((track.xs() - 0.005) * 100).astype(int).clip(0, 99)
    padded[positions] = track.selected_array["frequency"]
    return padded


class CharacterModel:
    def __init__(self, name, strength, mode="character"):
        self.name = name
        self.strength = strength
        self.fidelity = name == "taffy" and mode == "character"
        self.register = None
        self.tone = None
        self.tone_windows = 0
        self.denoiser = StreamingDenoiser() if strength else None

    def source_tone(self, wet, voiced_frames):
        """Running mean of the trained voice's own timbre vector, from windows with enough voicing."""
        if voiced_frames >= 25:
            current = tone_embedding(tone_spec(np.pad(wet, (0, (-len(wet)) % 256), mode="reflect")))
            self.tone_windows = min(self.tone_windows + 1, TONE_WINDOWS)
            self.tone = current if self.tone is None else self.tone + (current - self.tone) / self.tone_windows
        return self.tone

    def render(self, window, count):
        if self.strength == 0:
            return window.copy()
        clean, activity = self.denoiser.process(window, count)
        if np.max(activity) < .005 or np.max(np.abs(clean)) < 0.0006:
            return np.zeros_like(window)
        clean *= activity
        f0 = rmvpe_pitch(clean) if self.fidelity else pitch_track(clean)
        voiced = f0[f0 > 0]
        if voiced.size >= 5:
            median = np.log(float(np.median(voiced)))
            self.register = median if self.register is None else .92*self.register + .08*median
        if self.register is not None:
            ratio = np.clip(REGISTER[self.name] / np.exp(self.register), .7, 3.2)
            f0 *= ratio ** self.strength
            np.minimum(f0, 650, out=f0)
        if self.name == "taffy":
            units = graph("hubert_soft").run(None, {"audio": clean[None, None]})[0]
            inputs = {"units": units.repeat(2, axis=1).transpose(0, 2, 1), "f0": f0[None]}
            model = graph("taffy_svc")
        else:
            units = graph("contentvec_768l12").run(None, {
                "input_values": np.pad(clean, 40, mode="reflect")[None], "attention_mask": MASK,
            })[0]
            units = retrieve(units, self.name, f0)
            mel = 1127 * np.log1p(f0 / 700)
            low, high = 1127 * np.log1p(np.array([50., 1100.]) / 700)
            pitch = np.rint((mel - low) * 254 / (high-low) + 1).clip(1, 255).astype("int64")
            inputs = {"units": units.repeat(2, axis=1), "f0": f0[None],
                      "pitch": pitch[None], "noise": LATENT}
            model = graph(self.name + "_rvc")
        generated = model.run(None, inputs)[0].ravel()
        rate = VOICE_RATES[self.name]
        if len(generated) != rate or not np.isfinite(generated).all():
            raise RuntimeError("角色模型返回了无效音频。")
        g = gcd(rate, RATE)
        wet = resample_poly(generated, RATE // g, rate // g)
        # Prevent the vocoder from inventing hiss during pauses. Follow the
        # denoised amplitude envelope while preserving soft, unvoiced consonants.
        rms = np.sqrt(np.maximum(uniform_filter1d(clean**2, 480), 0))
        gate = np.clip((rms - 0.00025) / 0.0015, 0, 1) * activity
        gate = np.interp(np.arange(RATE)*16000/RATE, np.arange(16000), gate)
        wet *= gate
        refine = TIMBRE_REFINE[self.name] * self.strength
        if refine > 0 and np.max(np.abs(wet)) > 0.001:
            # Correct only what the trained voice produced, against the session's timbre
            # estimate. The input's consonants are added afterwards, so they never pass
            # through the converter.
            source = self.source_tone(wet, int(np.count_nonzero(f0)))
            wet = refine_timbre(wet, self.name, refine, source) * gate
        dry = resample_poly(clean, 441, 320)
        # Restore high-frequency consonant detail from the denoised input.
        voiced_mask = np.interp(np.arange(RATE) * 100 / RATE, np.arange(100), f0 > 0)
        unvoiced, voiced = ((CHARACTER_CONSONANT_UNVOICED, CHARACTER_CONSONANT_VOICED)
                           if self.fidelity else (CONSONANT_UNVOICED, CONSONANT_VOICED))
        mix = unvoiced + (voiced - unvoiced) * voiced_mask
        level = np.clip(np.linalg.norm(wet) / max(np.linalg.norm(dry), .02), .4, 2.5)
        wet += mix * sosfilt(CONSONANT_BAND, level * dry - wet)
        return np.clip(self.strength * OUTPUT_GAIN[self.name] * wet + (1-self.strength)*dry, -.99, .99)
