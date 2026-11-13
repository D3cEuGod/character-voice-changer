# Seed-VC integration

Upstream: https://github.com/Plachtaa/seed-vc

Pinned revision: `51383efd921027683c89e5348211d93ff12ac2a8`.

This snapshot contains the upstream real-time inference entry point and its
modules. The upstream GNU GPL v3 is retained in `LICENSE`. This is an optional
comparison engine, enabled only by `VOICE_REFERENCE_ENGINE=seed`. Embedded components
retain their copyright headers and license files. This code is distributed as
source; see `backend/reference_worker.py` for this application's adapter.

One change to upstream: `modules/length_regulator.py` imports the optional DAC
quantizer inside the `vector_quantize` branch. The Tiny real-time checkpoint does
not use this branch, so the DAC training dependency is unnecessary at runtime.

The GUI entry point is imported for `load_models` and `custom_infer`; the upstream
GUI is not launched. Our worker uses FP16, six diffusion steps, CFG 0.7, a
maximum six-second reference prompt, 3.02 seconds of rolling semantic context,
1.52 seconds of diffusion context, and 200 ms input packets. Cached prompts are
separate for all three characters. Inference runs on one persistent CUDA thread.

Weights are downloaded separately, from the original publishers, with pinned
revisions and SHA-256 checks in `tools/seed_models.json`. Model licenses remain
separate from the code license. No weights are checked into this repository.

Additional license texts for the embedded HiFT/CAMPPlus (Apache 2.0) and optional
BigVGAN / HiFi-GAN (MIT) components are included in `licenses/`. Their original
copyright headers are retained. The default application uses dedicated imported
RVC models for all three voices. This runtime is retained for optional comparisons.
