import asyncio
import logging
import numpy as np
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from . import engine
from .character import graph
from .live import FRAME, SHORT_FRAME, OVERLAP, SPEECH_LOOKAHEAD, LiveVoice

MAX_BYTES = 24 * 1024 * 1024


@asynccontextmanager
async def lifespan(app):
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
    yield


app = FastAPI(title="角色变声器", version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware,
                   allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.get("/api/health")
def health():
    return {"status": "ok", "engine": "RVC v2 / So-VITS-SVC 3.0", "provider": graph("taffy_svc").get_providers()[0],
            "sample_rate": engine.RATE,
            "max_seconds": engine.MAX_SECONDS, "max_bytes": MAX_BYTES}


@app.get("/api/voices")
def voices():
    return [{"id": key, "name": name} for key, name in engine.VOICES.items()]


def process(data, voice_id, strength):
    return engine.wav_bytes(engine.convert(engine.decode(data), voice_id, strength))


@app.post("/api/convert", response_class=Response, responses={
    200: {"content": {"audio/wav": {}}, "description": "PCM 16-bit WAV"}
}, openapi_extra={"requestBody": {"required": True, "content": {
    mime: {"schema": {"type": "string", "format": "binary"}}
    for mime in ("audio/wav", "audio/flac", "audio/mpeg", "audio/ogg", "application/octet-stream")
}}})
async def convert(request: Request, voice_id: Literal["tomori", "taffy", "anon"],
                  strength: Annotated[float, Query(ge=0, le=1, allow_inf_nan=False)] = 1.0):
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
            wav = await run_in_threadpool(process, data, voice_id, strength)
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
               low_latency: bool = False, speech_context: bool = False):
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
        session = LiveVoice(voice_id, strength, lookahead)
        frame_size = SHORT_FRAME if low_latency else FRAME
        hello = {"sample_rate": engine.RATE, "frame_samples": frame_size, "format": "s16le"}
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
