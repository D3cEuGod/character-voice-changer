"""Pace files as a microphone, convert over WebSocket, record the real virtual microphone.

Run with .venv-gui/Scripts/python.exe. Requires paired WASAPI virtual audio devices.
This checks transport and playback, not Discord's remote audio or human listening.
"""
import argparse
import json
from pathlib import Path
import queue
import sys
import threading
import time

import numpy as np
import sounddevice as sd
import soundfile as sf
import soxr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gui.audio import SpeakerStream, discord_pair, list_devices, live_slack
from gui.backend import BackendClient
from gui.live import LiveMonitor


class FileMic:
    rate = 22050
    active = True
    name = "paced test file"
    dropped = 0
    level = 0

    def __init__(self):
        self.blocks = queue.Queue()

    def close(self):
        self.active = False


def test(client, path, voice, mode, sender, receiver, output, repeat):
    signal, rate = sf.read(path, dtype="float32", always_2d=True)
    signal = np.tile(soxr.resample(signal.mean(axis=1), rate, 22050), repeat)
    mic = FileMic()
    health = client.health()
    reference_voices = health.get("reference_voices", ("tomori", "taffy") if health.get("reference_engine") else ())
    slack = live_slack(voice in reference_voices, voice, mode, True)
    speaker = SpeakerStream(sender, slack_seconds=slack, receiver=receiver)
    device_latency = speaker.latency
    expected, recorded, ticks, stops = [], [], [], []
    write = speaker.write

    def tee(samples):
        expected.append(samples.copy())
        write(samples)

    speaker.write = tee
    ready = threading.Event()
    monitor = LiveMonitor(client.live_url(voice, 1, mode), mic, speaker,
                          lambda hello: ready.set(), ticks.append, lambda *args: stops.append(args))
    capture_rate = 48000
    try:
        with sd.InputStream(device=receiver.index, samplerate=capture_rate, channels=1, latency=.1,
                            extra_settings=sd.WasapiSettings(auto_convert=True),
                            callback=lambda block, *args: recorded.append(block[:, 0].copy())):
            speaker.start()
            monitor.start()
            if not ready.wait(15):
                raise RuntimeError(f"WebSocket handshake failed: {stops}")
            start = time.perf_counter()
            padded = np.r_[np.zeros(4410, np.float32), signal, np.zeros(22050, np.float32)]
            for offset in range(0, len(padded), 441):
                mic.blocks.put(padded[offset:offset+441])
                time.sleep(max(0, start+(offset+441)/22050-time.perf_counter()))
            monitor.request_stop()
            monitor.join(15)
            time.sleep(.2)
    finally:
        monitor.request_stop(abort=True)
        if monitor.ident is not None:
            monitor.join(5)
        speaker.close()
    if stops != [("user", "")] or not expected or not recorded:
        raise RuntimeError(f"Conversion did not complete: {stops}")
    sent = soxr.resample(np.concatenate(expected), speaker.rate, capture_rate)
    heard = np.concatenate(recorded)
    size = 1 << (len(heard)+len(sent)-1).bit_length()
    correlation = np.fft.irfft(np.fft.rfft(heard, size)*np.conj(np.fft.rfft(sent, size)), size)
    lag = int(correlation.argmax())
    norm = np.linalg.norm(sent.astype(np.float64))*np.linalg.norm(heard.astype(np.float64))
    agreement = float(np.clip(correlation[lag]/max(norm, 1e-12), -1., 1.))
    name = f"{path.stem}-{voice}-{mode}"
    sf.write(output / f"{name}-received.wav", heard, capture_rate)
    sf.write(output / f"{name}-sent.wav", sent, capture_rate)
    (output / f"{name}-trace.json").write_text(json.dumps(ticks), encoding="utf-8")
    return {"input": str(path), "voice": voice, "mode": mode, "repeat": repeat,
            "correlation": round(agreement, 5), "signal_delay_s": round(lag/capture_rate, 3),
            "p95_ms": round(float(np.percentile([tick["last_ms"] for tick in ticks], 95)), 1),
            "max_ms": round(float(max(tick["last_ms"] for tick in ticks)), 1),
            "starvations": speaker.starvations, "device_underflows": speaker.device_underflows,
            "fifo_dropped": speaker.fifo.dropped,
            "playback_slack_s": slack, "device_latency_s": round(device_latency, 4),
            "underruns": speaker.underruns, "full_scale_pct": round(float(np.mean(abs(heard)>=.999)*100), 5),
            "audio_present": bool(np.max(abs(sent))>.02)}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("inputs", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("character", "call"), default="character")
    parser.add_argument("--voices", nargs="+", default=("tomori", "taffy", "anon"))
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    pair = discord_pair(list_devices("input"), list_devices("output"))
    if pair is None:
        raise RuntimeError("No paired virtual microphone devices were found.")
    client = BackendClient()
    results = {"health": client.health(), "sender": pair[0].name, "receiver": pair[1].name, "tests": []}
    for path in args.inputs:
        for voice in args.voices:
            row = test(client, path, voice, args.mode, *pair, args.output, args.repeat)
            results["tests"].append(row)
            print(json.dumps(row), flush=True)
    (args.output / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return int(any(row["underruns"] or row["correlation"] < .99 or not row["audio_present"]
                   or row["full_scale_pct"] for row in results["tests"]))


if __name__ == "__main__":
    sys.exit(main())
