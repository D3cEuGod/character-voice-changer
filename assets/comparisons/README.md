# 参考 / 旧版 / 新版试听

三段之间有约 0.65 秒静音，已对齐播放音量，方便比较音色。精确时间见 `segments.json`。

- `tomori.wav`：用户提供的“凑企鹅”演唱人声片段 → 0.1.1 → 当前 `deng` RVC。第一段是用户选择的目标示例，未核实原始录制来源，不作为已确认的角色原始配音。
- `taffy.wav`：塔菲直播原声 → 0.1.1 → 当前 `mygf-tf` RVC。
- `anon.wav`：爱音官方 CM 原声 → 0.1.1 → 当前 `Anon_v2` RVC。

新旧变声段均由 `assets/previews/original.wav` 的同一句中文输入生成。它是 Windows 合成语音；这里不将它当作用户本人的麦克风输入。原始角色参考与用户目标示例的出处见 `assets/references/sources.json`。

运行中的后端准备好后，可用 `tools/eval/make_previews.py` 重新生成；旧版本固定为提交 `a9d9139977bbc0ab257876fe0b1f60c4abac9078` 对应的 0.1.1。
