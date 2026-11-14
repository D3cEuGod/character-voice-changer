import asyncio
import logging
import numpy as np
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from enum import IntEnum
from functools import partial
import time
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from . import __version__, engine, reference, local_rvc
from .character import graph, voice_index
from .pitch import model as pitch_model
from .live import FRAME, SHORT_FRAME, REALTIME_FRAME, FAST_FRAME, BALANCED_FRAME, OVERLAP, SPEECH_LOOKAHEAD, LiveVoice

MAX_BYTES = 24 * 1024 * 1024


class PacketMs(IntEnum):
    fast = 80
    balanced = 100
    realtime = 120
    standard = 200


@asynccontextmanager
async def lifespan(app):
    started = time.perf_counter()
    if all(local_rvc.profile(v) is not None for v in engine.VOICES):
        # Only independent session creation / index reads are parallel. Warmup
        # stays serial: DirectML forbids concurrent Run calls on one shared graph.
        loads = [partial(graph, name) for name in
                 ('gtcrn_simple', 'silero_vad_16k_op15', 'contentvec_768l12')]
        loads += [pitch_model]
        loads += [partial(local_rvc.graph, v) for v in engine.VOICES]
        loads += [partial(voice_index, v) for v in engine.VOICES]
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix='model-load') as pool:
            for result in pool.map(lambda load: load(), loads):
                pass
        logging.getLogger('uvicorn.error').info('Models prepared in %.2f s', time.perf_counter()-started)
    sample = engine.decode((engine.ROOT / "assets/previews/original.wav").read_bytes())
    warmup = np.pad(sample, (0, (-len(sample)) % SHORT_FRAME)).reshape(-1, SHORT_FRAME)
    for voice_id in engine.VOICES:
        voice = LiveVoice(voice_id, 1, SPEECH_LOOKAHEAD)
        for frame in warmup:
            if np.max(np.abs(voice.process(frame))) > .002:
                break
        else:
            raise RuntimeError(f"角色模型启动自检没有检测到语音：{voice_id}")
    app.state.busy = asyncio.Lock()
    try:
        yield
    finally:
        reference.client().close()


app = FastAPI(title="角色变声器", version=__version__, lifespan=lifespan)
app.add_middleware(CORSMiddleware,
                   allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.get("/api/health")
def health():
    worker = reference.client()
    ready = worker.port is not None and worker.process is not None and worker.process.poll() is None
    profiles = {voice: local_rvc.profile(voice) for voice in engine.VOICES}
    references = sorted(reference.PREFERRED_VOICES) if ready else []
    models = {voice: ("Seed-VC · 直播参考" if voice == "taffy" and voice in references
                      else "Seed-VC · 原声参考" if voice in references
                      else f"{profile.label} · RVC v2 {profile.sample_rate//1000}k" if profile is not None
                      else "So-VITS-SVC 3.0" if voice == "taffy" else "RVC v2")
              for voice, profile in profiles.items()}
    current_engine = "Seed-VC / RVC" if ready else "RVC v2" if all(profiles.values()) else "RVC v2 / So-VITS-SVC 3.0"
    provider = ("PyTorch CUDA" if ready else local_rvc.graph(next(voice for voice, profile in profiles.items() if profile)).get_providers()[0]
                if any(profiles.values()) else graph("taffy_svc").get_providers()[0])
    return {"status": "ok", "version": __version__, "engine": current_engine,
            "reference_engine": ready, "reference_error": reference.client().failure,
            "reference_voices": sorted(references), "voice_models": models,
            "provider": provider,
            "sample_rate": engine.RATE,
            "live_packet_ms": [80, 100, 120, 200],
            "pitch_control": True,
            "max_seconds": engine.MAX_SECONDS, "max_bytes": MAX_BYTES}


@app.get("/api/voices")
def voices():
    return [{"id": key, "name": name} for key, name in engine.VOICES.items()]


def process(data, voice_id, strength, mode="character", pitch_shift=None, pitch_offset=0):
    return engine.wav_bytes(engine.convert(engine.decode(data), voice_id, strength, mode,
                                           pitch_shift=pitch_shift, pitch_offset=pitch_offset))


@app.post("/api/convert", response_class=Response, responses={
    200: {"content": {"audio/wav": {}}, "description": "PCM 16-bit WAV"}
}, openapi_extra={"requestBody": {"required": True, "content": {
    mime: {"schema": {"type": "string", "format": "binary"}}
    for mime in ("audio/wav", "audio/flac", "audio/mpeg", "audio/ogg", "application/octet-stream")
}}})
async def convert(request: Request, voice_id: Literal["tomori", "taffy", "anon"],
                  strength: Annotated[float, Query(ge=0, le=1, allow_inf_nan=False)] = 1.0,
                  mode: Literal["character", "call"] = "character",
                  pitch_shift: Annotated[float | None, Query(ge=-24, le=24, allow_inf_nan=False)] = None,
                  pitch_offset: Annotated[float, Query(ge=-24, le=24, allow_inf_nan=False)] = 0):
    lock = request.app.state.busy
    if lock.locked():
        raise HTTPException(429, "正在处理另一段音频，请稍后重试。")
    async with lock:
        data = bytearray()
        async for chunk in request.stream():
            if len(data) + len(chunk) > MAX_BYTES:
                raise HTTPException(413, "音频文件超过 24 MiB。")
            data.extend(chunk)
        try:
            wav = await run_in_threadpool(process, data, voice_id, strength, mode, pitch_shift, pitch_offset)
        except engine.AudioError as exc:
            raise HTTPException(422, str(exc)) from exc
        except Exception as exc:
            logging.exception("Voice conversion failed")
            raise HTTPException(500, "转换失败，请查看后端日志。") from exc
    return Response(wav, media_type="audio/wav", headers={
        "Content-Disposition": f'attachment; filename="{voice_id}.wav"',
        "Cache-Control": "no-store",
    })


@app.websocket("/api/live")
async def live(ws: WebSocket, voice_id: Literal["tomori", "taffy", "anon"],
               strength: Annotated[float, Query(ge=0, le=1, allow_inf_nan=False)] = 1.0,
               low_latency: bool = False, speech_context: bool = False,
               packet_ms: PacketMs = PacketMs.standard,
               mode: Literal["character", "call"] = "character",
               pitch_shift: Annotated[float | None, Query(ge=-24, le=24, allow_inf_nan=False)] = None,
               pitch_offset: Annotated[float, Query(ge=-24, le=24, allow_inf_nan=False)] = 0):
    if ws.headers.get("origin") not in (None, "http://localhost:5173", "http://127.0.0.1:5173"):
        await ws.close(code=1008)
        return
    await ws.accept()
    lock = ws.app.state.busy
    if lock.locked():
        await ws.close(code=1013, reason="Engine is busy")
        return
    async with lock:
        lookahead = SPEECH_LOOKAHEAD if speech_context else OVERLAP
        session = LiveVoice(voice_id, strength, lookahead, mode,
                            pitch_shift=pitch_shift, pitch_offset=pitch_offset)
        frame_size = SHORT_FRAME if low_latency else FRAME
        if low_latency and session.model.reference is None:
            frame_size = {80: FAST_FRAME, 100: BALANCED_FRAME, 120: REALTIME_FRAME, 200: SHORT_FRAME}[packet_ms]
        hello = {"sample_rate": engine.RATE, "frame_samples": frame_size, "format": "s16le"}
        hello.update(pitch_shift=pitch_shift, pitch_offset=pitch_offset)
        if speech_context:
            hello["lookahead_samples"] = lookahead
        await ws.send_json(hello)
        try:
            while True:
                message = await asyncio.wait_for(ws.receive(), timeout=30)
                if message["type"] == "websocket.disconnect":
                    return
                if message.get("text") == "finish":
                    await ws.send_bytes(await run_in_threadpool(session.finish))
                    await ws.close()
                    return
                data = message.get("bytes")
                if data is None or len(data) != frame_size * 2:
                    await ws.close(code=1003, reason=f"Expected {frame_size} mono PCM16 samples")
                    return
                await ws.send_bytes(await run_in_threadpool(session.feed, data))
        except TimeoutError:
            await ws.close(code=1001, reason="Idle microphone")
        except WebSocketDisconnect:
            return
