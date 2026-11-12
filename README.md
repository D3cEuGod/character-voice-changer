# 本地角色变声器

选择高松灯、永雏塔菲或千早爱音，可以转换音频文件，也可以边说话边向 Discord 发送变声。灯和爱音使用各自的 RVC v2 模型和配套检索索引。塔菲使用 So-VITS-SVC 3.0 的塔菲说话人。三者均使用角色对白进行 OpenVoice 音色校正，Windows 优先用 DirectML 运行声学模型。

## 在 Discord 里说话

1. 双击 `start-gui.cmd`。在变声器的“麦克风”里选择你平时说话的设备。WO Mic 手机麦克风的名称通常是 `Microphone (WO Mic Device)`。
2. 选角色，强度先设为 100%，在“实时变声”选择“Discord 通话”并打开开关。界面会显示 Discord 应选择的输入设备。
3. 在 Discord 的“用户设置 → 语音与视频 → 输入设备”选择界面显示的完整名称。本机验证过的输入是 `Microphone (Steam Streaming Microphone)`，变声器会自动写入 `Speakers (Steam Streaming Microphone)`。Discord 的输出设备继续用耳机。
4. 用 Discord 自带的麦克风测试说一句话。停掉变声开关后，句子应在缓冲播完后消失；若还能持续听到自己的新讲话，检查 Discord 当前选中的输入设备。
5. 如果已安装 VB-CABLE，软件优先向 `CABLE Input` 发送，Discord 选择 `CABLE Output`。没有成对的虚拟设备时，界面提示安装并刷新设备。[VB-CABLE 官方说明](https://vb-audio.com/Cable/index.htm)

## Windows 启动

双击 `start-backend.cmd`。脚本使用 Python 3.13 和项目内的 `.venv`。本机已备好模型。新电脑首次启动需要 Git 和联网，脚本下载模型、校验 SHA-256，再用独立的 PyTorch 环境导出三个角色。模型和检索索引在 `models/`，构建缓存位于 `.run/`，日常变声可以离线运行。服务就绪时会显示 `Uvicorn running on http://127.0.0.1:8765`。按 Ctrl+C 停止服务。

用浏览器打开 [接口文档](http://127.0.0.1:8765/docs)，或在项目目录用 PowerShell 直接试听塔菲声线。

```powershell
curl.exe --fail-with-body "http://127.0.0.1:8765/api/convert?voice_id=taffy&strength=1" -H "Content-Type: audio/wav" --data-binary "@assets/previews/original.wav" -o taffy-test.wav
```

## 文件与录音接口

| 请求 | 返回 |
| --- | --- |
| `GET /api/health` | 引擎就绪状态、采样率、最长时长和上传大小上限 |
| `GET /api/voices` | 数组，每条记录包含 `id` 和中文 `name` |
| `POST /api/convert?voice_id=taffy&strength=1` | 请求体直接放音频文件字节。成功返回 `audio/wav`，22,050 Hz 单声道 PCM16 |

`voice_id` 取 `tomori`、`taffy`、`anon`；`strength` 范围 0–1，默认为 1。设为 0 可试听经过统一采样的原声。支持 WAV、FLAC、MP3、OGG，单声道或双声道，8–96 kHz，0.35–60 秒，最多 24 MiB。浏览器录音可先编码成 PCM WAV 再提交。

错误使用 HTTP 状态码和 JSON 的 `detail`。413 表示文件过大，422 表示音频或参数无效，429 表示引擎正忙，500 表示推理失败。参数验证错误的 `detail` 为数组。一次只处理一个转换任务或一个监听会话。

## 麦克风监听协议

桌面 GUI 追加 `&low_latency=true&speech_context=true`，每包 4,410 个样本（200 毫秒）。握手中的 `lookahead_samples` 为 2,304，首包返回 2,106 个样本，正常收尾补回 2,304 个样本。保留约 104 毫秒的上下文有助于识别句首辅音。旧客户端省略 `speech_context` 时仍保留 1,024 个样本。

连接 `ws://127.0.0.1:8765/api/live?voice_id=taffy&strength=1`，等待首条 JSON 消息。成功时返回 `{"sample_rate":22050,"frame_samples":8192,"format":"s16le"}`。

1. 将设备采集的音频连续重采样为 22,050 Hz 单声道，凑齐 8,192 个小端 PCM16 样本后发送一条 16,384 字节的二进制消息。原生客户端可以直接连接，Web 开发客户端允许从 localhost 或 127.0.0.1 的 5173 端口连接。
2. 每帧收到一条二进制 PCM16 回包。首包有 7,168 个样本，后续每包有 8,192 个样本。按顺序播放，服务端保留 1,024 个样本用于交叉淡化。每个输入块约 372 毫秒，设备缓冲、采集与推理还会影响监听延迟。
3. 正常停止时，剩余不足一帧的输入可补零，发送后再发文本 `finish`。读完末尾 PCM 和正常关闭帧；需要精确保存时从末尾裁掉补入的样本。中途取消可直接断开连接。
4. 关闭码 1013 表示引擎正忙，1003 表示帧格式错误，1001 表示空闲超过 30 秒。切换角色或强度时重新连接。输出可送到用户所选播放设备；在其他软件里作为麦克风使用时，需要系统已有的虚拟音频设备。

## 声线与美术素材

| 项目 | 本地文件及来源 |
| --- | --- |
| 高松灯、千早爱音 | 各自使用 TogetsuDo 发布的歌声转换权重和 FAISS 索引。ContentVec 提取发音特征，Praat 跟踪音高。校正用的向量来自角色日语对白。[高松灯权重](https://huggingface.co/TogetsuDo/tomori-rvc) · [千早爱音权重](https://huggingface.co/TogetsuDo/anon-rvc) · [参考对白](https://github.com/telecom888/Live2dOnAndroid/tree/af08c7b8a0c77444502f27fab0c19e88aeb3c923/app/src/main/assets/voices_builtin) |
| 永雏塔菲 | 使用 HuBERT-Soft 和 NyaruTaffy 32 kHz 权重，选择配置中的 `taffy`（说话人 0）。校正向量来自直播的日常说话片段。[模型与配置](https://huggingface.co/spaces/ZilliaxOfficial/nyaru-svc-3.0/tree/main) · [参考音频](https://huggingface.co/datasets/KYOU-0/Ace-Taffy-voice) |
| 永雏塔菲头像 | `assets/taffy-avatar.jpg` 为账号公开头像，511 × 512。[账号主页](https://space.bilibili.com/1265680561) |
| 试听 | `assets/previews/original.wav` 为 Windows 中文合成语音。同目录 `tomori.wav`、`taffy.wav`、`anon.wav` 均由本后端转换，便于比较同一句话。 |

`prepare_voices.py` 记录了参考文件的固定版本、音频时间段和向量提取方法。如需重建向量，在模型准备好后运行 `.venv\Scripts\python.exe prepare_voices.py`。

运行期间，GTCRN 连续处理麦克风底噪，Silero VAD 识别说话区间。后端在相邻音频包之间对齐波形，再发往桌面客户端的播放缓冲区。各模型下载地址、版本和校验值保存在 `setup_models.py`。[GTCRN](https://github.com/Xiaobin-Rong/gtcrn) · [Silero VAD](https://github.com/snakers4/silero-vad) · [RVC](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) · [OpenVoice](https://github.com/myshell-ai/OpenVoice)

## 桌面界面

双击 `start-gui.cmd`。脚本使用 Python 3.13 和项目内的 `.venv-gui`，首次运行会安装 `gui/requirements.txt` 里的 PySide6、sounddevice 等依赖。界面启动时检查 `/api/health`：后端已在运行就直接复用；没有运行就启动 `start-backend.cmd` 并等到就绪，关闭窗口时一并停止由界面启动的后端。启动失败时，窗口顶部显示脚本的退出码和最后几行输出。

项目根目录的“角色变声器”快捷方式同样运行 `start-gui.cmd`，图标是头像。要放到任务栏，右键这个快捷方式，在“显示更多选项”里选“固定到任务栏”；或者在界面运行时右键任务栏上的图标选“固定到任务栏”。Windows 不允许程序替用户完成这一步。快捷方式里是绝对路径，项目文件夹移动后运行 `powershell -NoProfile -ExecutionPolicy Bypass -File make-shortcut.ps1` 重新生成。

1. 角色卡来自 `GET /api/voices`，默认选中永雏塔菲。每张卡的“示例”按钮播放 `assets/previews/` 下的对应文件。
2. 用红色按钮录音，或导入 WAV、FLAC、MP3、OGG。调好音色强度后点“开始变声”，文件字节原样提交给 `POST /api/convert`。
3. “原声”和“变声结果”可在播放中切换，位置保持不变。“另存为 WAV”写出后端返回的原始字节。
4. 每段结果都记着生成它的输入、角色和强度。改了其中任何一项，结果试听和保存就不可用，改回去或重新变声后恢复；换输入会作废旧输入的全部结果。
5. “实时变声”按上面的 WebSocket 协议工作。本机监听从所选设备播放，Discord 通话只发往虚拟麦克风。监听和文件转换共用一个引擎，开着监听时不能转换文件。切换角色、强度或设备会重新连接。请戴耳机，外放会被麦克风收回去。

界面源码在 `gui/`，直接运行用 `.venv-gui\Scripts\python.exe -m gui`。可选参数：`--backend-url` 指定后端地址，`--no-autostart` 不自动启动后端。未处理的错误写入 `.run/gui.log`。

`.venv-gui\Scripts\python.exe -m gui.selfcheck` 会打开真实窗口，用正在运行的后端把导入、变声、试听、保存、录音、监听、角色切换和退出跑一遍，逐项打印结果，产物写到 `.run/selfcheck/`。试听会从默认输出设备出声。录音和监听需要一对虚拟音频线设备来提供麦克风信号，找不到时跳过。设备被拔出、引擎被占用和后端启动失败都是模拟的，输出里有注明；自动启动用同样的命令在 8766 端口另起一个后端来验证。

## GUI 开发

交给 Claude 的完整任务在 [CLAUDE_GUI.md](CLAUDE_GUI.md)。
