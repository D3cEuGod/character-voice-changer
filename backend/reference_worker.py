"""Isolated CUDA worker for the vendored Seed-VC real-time implementation."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import time
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
import sys
import socket

import numpy as np
import soundfile as sf
import torch
import torchaudio
import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "third_party/seed_vc"
WEIGHTS = ROOT / "models/seed-vc"
INPUT_SAMPLES = 48320  # 3.02 seconds at 16 kHz
OUTPUT_SAMPLES = 22050
VOICES = ("tomori", "taffy", "anon")


def local_model(repo, name, config_filename=None):
    path = WEIGHTS / "tiny" / name
    if config_filename is None:
        return str(path)
    return str(path), str(WEIGHTS / "tiny" / config_filename)


class ReferenceEngine:
    def __init__(self):
        if not torch.cuda.is_available():
            raise RuntimeError("Seed-VC requires an available CUDA GPU.")
        torch.set_num_threads(4)
        torch.backends.cuda.matmul.allow_tf32 = True
        os.chdir(SOURCE)
        sys.path.insert(0, str(SOURCE))
        spec = importlib.util.spec_from_file_location("seed_realtime", SOURCE / "real-time-gui.py")
        self.seed = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.seed)
        self.seed.device = torch.device("cuda")
        self.seed.load_custom_model_from_hf = local_model
        config = yaml.safe_load((WEIGHTS / "tiny/config_dit_mel_seed_uvit_xlsr_tiny.yml").read_text())
        config["model_params"]["speech_tokenizer"]["name"] = str(WEIGHTS / "xlsr")
        runtime_config = WEIGHTS / "runtime.yml"
        runtime_config.write_text(yaml.safe_dump(config), encoding="utf-8")
        self.models = self.seed.load_models(SimpleNamespace(
            fp16=True, checkpoint_path=str(WEIGHTS / "tiny/DiT_uvit_tat_xlsr_ema.pth"),
            config_path=str(runtime_config)))
        self.references = {}
        for voice in VOICES:
            audio, rate = sf.read(ROOT / "assets/references" / f"{voice}.wav", dtype="float32")
            self.references[voice] = torchaudio.functional.resample(torch.from_numpy(audio), rate, 22050).numpy()
        self.prompts = {}
        self.lock = threading.Lock()
        for voice in VOICES:
            self.convert(np.zeros(INPUT_SAMPLES, np.float32), voice)

    @torch.inference_mode()
    def convert(self, audio, voice):
        with self.lock, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            if voice in self.prompts:
                self.seed.prompt_condition, self.seed.mel2, self.seed.style2 = self.prompts[voice]
                self.seed.reference_wav_name = voice
            wave = torch.from_numpy(audio.copy()).to("cuda")
            # Upstream real-time settings. XLSR gets 3.02 s of context, the DiT
            # gets the last 1.52 s. Return one second, with 20 ms held back.
            output = self.seed.custom_infer(
                self.models, self.references[voice], voice, wave, 3200,
                100, 1, 50, 6, .7, 6., cd_difference=1.5)
            self.prompts[voice] = self.seed.prompt_condition, self.seed.mel2, self.seed.style2
            output = output.float().cpu().numpy()
            if output.size != OUTPUT_SAMPLES or not np.isfinite(output).all():
                raise RuntimeError(f"Invalid Seed-VC output shape {output.shape}")
            return np.clip(output, -.99, .99).astype("<f4")


def serve(port, ready_file):
    engine = ReferenceEngine()

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.connection.settimeout(15)

        def reply(self, code, body, content_type="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self.reply(200, json.dumps({"engine": "Seed-VC", "version": 1}).encode())

        def do_POST(self):
            voice = parse_qs(urlsplit(self.path).query).get("voice", [""])[0]
            if voice not in VOICES or self.headers.get("Content-Length") != str(INPUT_SAMPLES * 4):
                self.reply(400, b'{"error":"Invalid voice or audio length"}')
                return
            audio = np.frombuffer(self.rfile.read(INPUT_SAMPLES * 4), dtype="<f4")
            if len(audio) != INPUT_SAMPLES or not np.isfinite(audio).all():
                self.reply(400, b'{"error":"Invalid audio"}')
                return
            try:
                started = time.perf_counter()
                result = engine.convert(audio, voice)
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(result.nbytes))
                self.send_header("X-Inference-Ms", f"{(time.perf_counter()-started)*1000:.1f}")
                self.end_headers()
                self.wfile.write(result.tobytes())
            except Exception as exc:
                self.reply(500, json.dumps({"error": str(exc)}).encode())

        def log_message(self, format, *args):
            pass

    # Keep CUDA inference on the thread that loaded and warmed the models.
    # A fresh request thread creates new CUDA library handles on every packet.
    server = HTTPServer(("127.0.0.1", port), Handler)
    ready_file.write_text(json.dumps({"port": server.server_address[1], "pid": os.getpid()}), encoding="utf-8")
    print(f"Seed-VC ready on {server.server_address[1]}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--ready-file", type=Path, required=True)
    arguments = parser.parse_args()
    serve(arguments.port, arguments.ready_file)
