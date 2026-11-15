# character-voice-changer

A local, real-time voice changer for Windows that turns your microphone into an anime character's voice and sends it to Discord.

Pick Tomori Takamatsu, Ace Taffy, Anon Chihaya or Matikanetannhauser, speak normally, and the app converts your speech on your own GPU. VB-CABLE uses 120 ms packets; Steam and file conversion retain 200 ms packets. It can also convert recorded or imported audio files. Conversion runs locally.

## Key Features

- Four installed RVC v2 voices (40k / 48k), with matched retrieval indexes and RMVPE pitch extraction
- Install user-supplied `.pth` / `.index` pairs with checksum verification and a one-second inference check
- Real-time conversion over a local WebSocket, with reduced buffering for VB-CABLE and a session refresh every 3,000 packets
- Discord output through a virtual microphone (Steam Streaming Microphone or VB-CABLE), or local monitoring
- Streaming noise suppression (GTCRN) and voice activity detection (Silero VAD), silent during pauses
- File mode: record or import WAV / FLAC / MP3 / OGG, compare original and result, save as WAV
- Desktop GUI that starts and stops the backend by itself; unchanged model checks and compatible optimized graphs are cached locally
- Objective evaluation tools: character error rate, speaker similarity and packet-join energy
- Characters grouped by franchise (MyGO!!!!!, VTubers, Umamusume), switched with a carousel; custom RVC IDs and display names are supported by the importer and API
- Original character recordings playable directly in the GUI
- Versioned releases with a changelog; current internal beta is 0.5.0

## Tech Stack

- Python 3.13
- FastAPI and Uvicorn (HTTP and WebSocket backend)
- ONNX Runtime with DirectML
- Optional experimental Seed-VC runtime, disabled by default
- RVC v2, So-VITS-SVC 3.0, OpenVoice V2, ContentVec, HuBERT-Soft
- GTCRN, Silero VAD, RMVPE, Praat (parselmouth), FAISS
- PySide6 (Qt 6), sounddevice (PortAudio), soxr

## Screenshots

All images are captures of the running app on Windows 11, taken while the self-check drove it against the real backend.

<table>
  <tr>
    <td colspan="2" align="center">
      <img src="docs/images/live-on-air.png" alt="Real-time conversion running" width="92%" />
      <br />
      <sub>
        <strong>EN:</strong> Real-time conversion running. The avatar frame turns red, the level bars move, and the status line shows the devices, delay and per-packet processing time.<br />
        <strong>中文：</strong> 实时变声进行中。头像描边变红，电平条在动，状态行显示设备、延迟和每包处理时间。
      </sub>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <img src="docs/images/main-window.png" alt="Main window with Taffy selected" width="100%" />
      <br />
      <sub>
        <strong>EN:</strong> Main window on a white background with pink accents. Categories, the character carousel and strength on the left, one large switch on the right. Chibi Taffy sits next to the title.<br />
        <strong>中文：</strong> 白底粉色点缀的主窗口。左边是分类、角色转盘和强度，右边一个大开关，标题旁是 Q 版塔菲。
      </sub>
    </td>
    <td width="50%" align="center">
      <img src="docs/images/file-converted.png" alt="File conversion with a finished result" width="100%" />
      <br />
      <sub>
        <strong>EN:</strong> File mode after a conversion. The result is tagged with the input, character, strength and processing mode that produced it.<br />
        <strong>中文：</strong> 文件变声完成后。结果标着生成它的输入、角色、强度和处理方式。
      </sub>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <img src="docs/images/voice-tomori.png" alt="Tomori selected" width="100%" />
      <br />
      <sub>
        <strong>EN:</strong> MyGO!!!!! category. Tomori sits in the centre and Anon waits, blurred, on the right; the triangles switch between them.<br />
        <strong>中文：</strong> MyGO!!!!! 分类。灯在中间，爱音在右侧虚化，两边的三角形用来切换。
      </sub>
    </td>
    <td width="50%" align="center">
      <img src="docs/images/voice-anon.png" alt="Anon selected" width="100%" />
      <br />
      <sub>
        <strong>EN:</strong> Anon selected. Tomori moves to the left side; the frame, caption and switch take Anon's colour.<br />
        <strong>中文：</strong> 选中爱音。灯移到左侧，描边、标注和开关换成爱音的角色色。
      </sub>
    </td>
  </tr>
  <tr>
    <td colspan="2" align="center">
      <img src="docs/images/voice-tannhauser.jpg" alt="Umamusume category with Matikanetannhauser selected" width="78%" />
      <br />
      <sub>赛马娘分类中的诗歌剧：独立的 48k RVC 模型、官方头像与角色原声，默认自动音域再 +4。</sub>
    </td>
  </tr>
</table>

## Chinese Notes / 中文说明

一个在本机运行的角色变声器。选择高松灯、永雏塔菲、千早爱音或赛马娘的诗歌剧，对着麦克风说话，变声后的声音发给 Discord，也可以转换录音和音频文件。

## Latest 安装说明

当前版本：`0.5.0`（内测版）

需要 Windows 10 或 11、Python 3.13 和 Git。默认后端是 ONNX / DirectML 的 RVC v2，本机验证为 RTX 5060 Ti 16 GB。常规运行不需要额外的 CUDA / PyTorch 环境。

1. 克隆仓库，双击 `start-gui.cmd`。
2. 首次启动会建立虚拟环境并安装依赖。已安装三套本地角色模型时，只准备 ContentVec、RMVPE、GTCRN 和 VAD 等必要推理图。没有本地模型时会准备原来的兼容声线（约 2 GB 权重及导出环境）；这与本次导入的新声线有区别。权重均校验 SHA-256。
3. 窗口右上角显示“后端：已连接”后即可使用。之后可以离线运行。

后续启动会复用已成功校验、且文件标识和时间等属性未变化的模型校验结果。共享推理图的优化结果保存在本机 `.run/ort-cache/`，按原图、运行库、系统与显卡驱动区分；角色 RVC 图仍从原文件加载。首次运行、模型或驱动变化时会重新准备缓存，三位角色的实际音频预热仍会执行。需要强制重算所有校验值时设置 `VOICE_VERIFY_MODELS=1`；排查图缓存问题时设置 `VOICE_ORT_CACHE=0`。这些本机缓存不上传 Git。

所有已安装角色都可以切换处理方式。新 RVC 模型的默认“音色优先”采用 0.75 检索比例、0.33 清音特征混合；“通话清晰”将检索比例降到最多 0.5，清音混合比例降到最多 0.15，以保留更多原始发音特征。两档均使用 RMVPE，不再串接 OpenVoice 或混回输入者的有声波形。头像下会显示实际模型名，避免把兼容声线误认为已安装的新模型。

### 音高 +4 试用与试听

0.4.2 按用户选定的效果，让 GUI 的高松灯、永雏塔菲和千早爱音都默认使用“自动音域再 +4”。左栏只保留以下两档，“原声 +4”已从界面和启动参数中移除。实时和文件变声都生效；切档后旧文件结果不会被当成新档位的结果，实时会话会自动重连，周期刷新也会保留所选档位。

| 档位 | 做法 | 原声中位音高 150 Hz 时，以塔菲为例 |
| --- | --- | --- |
| 模型默认 | 使用原有模型配置；本机三位均为自动匹配角色音域 | 约 429 Hz |
| 自动音域再 +4 | 原有自动音域匹配后再升 4 个半音 | 约 541 Hz |

保留原有 650 Hz 上限和音色强度对移调量的缩放；表中是 100% 强度的简化例子，真实说话还会保留起伏。自动再 +4 会更高，但音高本身不等于角色相似度。普通双击即可使用这档；命令行 `start-gui.cmd --pitch-preset model` 可按原设置启动。

用同一段现有回归集的**合成男声**生成了 [灯](assets/pitch-comparisons/tomori.wav)、[塔菲](assets/pitch-comparisons/taffy.wav)、[爱音](assets/pitch-comparisons/anon.wav) 三份对照，顺序均为“模型默认 → 自动音域再 +4”，两段间隔 0.6 秒，已删除原声 +4 的试听段。[原始输入](assets/pitch-comparisons/input-male.wav) 与 [时间段 / 参数 / 校验值](assets/pitch-comparisons/manifest.json) 一并保存。这些对照使用文件接口的 200 ms 包，不代表端到端延迟或真人听感结论。详见 [0.4.2 记录](notes/auto-pitch-default-0.4.2.md)。

本机已导入的模型如下，清单与 SHA-256 见 [安装记录](notes/installed-rvc-models.json)：

| 角色 | 实际权重 | 来源 |
| --- | --- | --- |
| 高松灯 | `deng.pth` / 40k RVC v2 | 用户提供的教程模型与配套索引 |
| 永雏塔菲 | `mygf-tf.pth` / 40k RVC v2 | 用户提供的 `Ai塔菲.zip` |
| 千早爱音 | `Anon_v2.pth` / 40k RVC v2 | Wanlau 的 BanG Dream 对白模型及配套索引 |
| 诗歌剧 | `uma-Matikane_Tannhauser.pth` / 48k RVC v2 | 用户提供的 `诗歌剧.zip` 与配套 v2 索引 |

0.5.0 新增“赛马娘”分类，诗歌剧有官方头像和角色原声按钮，同样默认自动音域再 +4。初始自动目标音域 417.4 Hz 来自约 3 秒官方语音的基频中位数，仅作初始校准。当前版本的四份音色优先示例已重新生成：[灯](assets/previews/tomori.wav)、[塔菲](assets/previews/taffy.wav)、[爱音](assets/previews/anon.wav)、[诗歌剧](assets/previews/tannhauser.wav)；均使用同一段合成中文输入、自动再 +4，文件转换不代表实时延迟。参数和校验值见[试听清单](assets/previews/manifest.json)。

### 导入模型与迁移电脑

大权重不放进 Git。迁移本机这套声线时，把整个 `models/local-rvc/` 文件夹一并复制到新电脑的项目目录；其中的配置使用相对路径，并校验推理图与索引。只克隆源码不会自动获得网盘里的用户模型。

也可以在后端环境已准备好后分别导入自己的权重与索引：

```powershell
.venv\Scripts\python.exe tools\import_rvc.py --voice tomori --checkpoint "D:\模型\deng.pth" --index "D:\模型\deng.index" --target-hz 320
.venv\Scripts\python.exe tools\import_rvc.py --voice taffy --checkpoint "D:\模型\mygf-tf.pth" --index "D:\模型\taffy.index" --target-hz 429
.venv\Scripts\python.exe tools\import_rvc.py --voice anon --checkpoint "D:\模型\Anon_v2.pth" --index "D:\模型\anon.index" --target-hz 310
.venv\Scripts\python.exe tools\import_rvc.py --voice tannhauser --name "诗歌剧" --checkpoint "D:\模型\uma-Matikane_Tannhauser.pth" --index "D:\模型\added_IVF1310_Flat_nprobe_1_uma-Matikane_Tannhauser_v2.index" --target-hz 417.4
```

导入器使用 `torch.load(weights_only=True)`，验证 RVC v2 / f0 架构、已填充的 768 维索引、说话人编号和完整一秒输出，通过后才更新角色配置。导入后重启后端和界面。`--pitch 12` 可使用固定半音移调，默认按目标音域自动调整。`.index` 应与该权重配套，不能把别的角色索引混用。

Seed-VC 作为对照实现保留，需要显式设置 `VOICE_REFERENCE_ENGINE=seed` 才安装并启用；它需要额外 CUDA 环境和约 1.5 GB 权重。它不是本版本默认通话后端。

左栏先选分类（目前有 MyGO!!!!! 和 V圈），再用角色转盘两侧的三角形、键盘左右键或点旁边的角色切换。当前角色在中间，同一分类的其他角色在两侧虚化显示。换分类时会选回这个分类上次用的角色。“角色原声”播放当前角色的真实配音 / 直播片段，参考音出处、片段时间和校验值在 [assets/references/sources.json](assets/references/sources.json)。

新增角色时，把头像放进 `assets/`，在 [assets/characters.json](assets/characters.json) 的 `voices` 里写上角色色和头像文件名，再把角色 id 放进某个分类，或新建一个分类。后端返回、但没有登记的角色会归入“其他”。

想把入口放到任务栏：运行一次 `powershell -NoProfile -ExecutionPolicy Bypass -File make-shortcut.ps1`，右键生成的“角色变声器”快捷方式，在“显示更多选项”里选“固定到任务栏”。

### 在 Discord 里用

1. 在界面底部的“麦克风”里选原声输入。如果用手机，通过 WO Mic 接入时这里选 `Microphone (WO Mic Device)`；WO Mic Client 保持已连接，并取消“设置 → 本地播放”。
2. 选角色，在“实时变声”页选“Discord 通话”，点一下大圆键。
3. 界面会显示 Discord 该选的输入设备名。在 Discord 的“用户设置 → 语音与视频 → 输入设备”里选它。安装 VB-CABLE 后选 `CABLE Output (VB-Audio Virtual Cable)`，Steam 为备用。Discord 的输出设备继续用耳机。
4. 在 Discord 的 Input Profile 里选择 **Studio**（无额外音频处理），避免 Voice Isolation / Krisp 再次切掉变声结果。旧界面没有此选项时，检查噪声抑制和输入灵敏度。然后用麦克风测试或让朋友确认句首和轻声。

WO Mic 是原声输入，Steam 虚拟麦克风是变声输出。Discord 继续选 WO Mic 会绕过变声器。也可以使用 VB-CABLE，不限于 Steam。

如果朋友先听到原声、约一秒后又听到变声，先确认 WO Mic 的“本地播放”已关闭，并检查 Windows 的麦克风“侦听此设备”是否开启。本机这次关闭 WO Mic 本地播放后，朋友确认重复声音消失。软件音色强度保持 100% 时，本地 RVC 路径仅输出转换波形；降低强度会按比例混入原声。本机 VB-CABLE 测试延迟约 0.7 秒，还需叠加 WO Mic 和 Discord 的延迟。

项目目录已保存 [VB-CABLE 官方原版安装包与安装说明](third_party/installers/vb-cable/README.md)。软件优先使用 VB-CABLE，Steam 为备用。驱动需要独立以管理员安装并重启；安装器请从纯英文临时目录运行。

### 长时间通话与实验延迟档

默认每发出 3,000 个实时音频包自动重开一次实时变声。VB-CABLE 的 120 ms 包约每 6 分钟触发，Steam 的 200 ms 包约每 10 分钟触发；静音包也计数。刷新会释放并重开采集、播放和 WebSocket 会话，重置降噪、音高跟踪、重采样和播放缓冲，保留角色、强度、处理方式和设备。窗口、后端进程和已经加载的模型继续运行。刷新时会有短暂停顿；这是针对长时间退化的缓解措施，尚未确认退化的唯一原因。

0.4.3 起，达到包数后会先等待输入与输出同时安静至少 600 ms，避免当场切断正在说的一句话；持续说话或噪声偏高时会推迟。完整收尾、关闭设备后，还会等待旧线程退出并留出 250 ms 的设备释放间隔，再走正常启动流程。刷新仍有短暂停顿，在释放期间开始说的新一句仍可能丢失，不能当作无缝切换。

状态行显示“本轮包数”和“自动刷新次数”。手动停止、设备错误或退出时不会自动重开，等待重开期间也可点停止取消。可从 PowerShell 在项目目录里运行：

```powershell
.\start-gui.cmd --live-restart-packets 5000
.\start-gui.cmd --live-restart-packets 0
.\start-gui.cmd --live-packet-ms 100
```

上面分别是改成 5,000 包、关闭自动刷新，以及启用实验 100 ms 包。普通双击仍是 3,000 包和稳定的 120 ms。100 ms 档仅影响 VB-CABLE 的普通 RVC 路径；短句本机回录约 0.63 秒，但爱音的带噪长句出现一次断流，因此未作为默认。完整前瞻和模型权重不变，Steam、文件变声与 Seed-VC 保留原包长。

## 当前状态

0.5.0 新增诗歌剧，并针对轻声句首、句尾滋滋声和切角色时的爆音继续调整：连续 48 Hz 高通、随背景残余电平调整的输出门控、背景之上弱句首的提前识别；切换时先淡出、排空旧设备缓冲，再完整重开实时会话。VB-CABLE 的目标播放缓冲由 240 ms 改为 320 ms，给偶发慢回包留余量，保留 120 ms 包长。四条声线各约 40.8 秒的最后一轮回录均无断流，整段和最后有声秒波形相关性为 1.00000，本机测得约 0.66～0.69 秒；不含手机和 Discord 额外延迟。尚未完整复现用户的持续滋滋声，也未完成小时级通话测试，不能保证完全消失。结果、失败轮与限制见 [0.5.0 记录](notes/poetry-edges-0.5.0.md)。

**参考音来源更正：** 0.1.0 / 0.1.1 的灯和爱音参考音来自第三方应用，实际上是 MiMo 合成语音，并非动画原始配音。以前把它们称为“角色日语对白”不准确，相应的相似度数字不能代表与真实角色的相似度。0.2.0 改用动画官方角色 CM 的原始表演并分离配乐，塔菲改用可追溯的直播说话片段，旧引擎的音色向量也已重新生成。

用户已通过真实 Discord 通话确认 VB-CABLE 能传递变声结果，并在关闭 WO Mic 本地播放后确认朋友只听到变声。尚未对该链路系统评测角色相似度或长时间稳定性。自动相似度分数不等于人耳判断。

用户提供的“凑企鹅”视频是演唱目标示例，未核实原始录制方式，不作为已确认的角色原始配音。灯的新默认音域为 320 Hz，目标是贴近用户选定的示例；官方 CM 原声仍单独保留供对照。两种参考不混为一谈。

## 0.1.0 发布说明

- 变声引擎从单一的 OpenVoice 音色转换，换成每位角色专用的模型：高松灯和千早爱音用 RVC v2，永雏塔菲用 So-VITS-SVC 3.0。
- 找到并修掉了“听不清”的主要原因。原来的音色校正对每个一秒窗口单独估计音色，相邻的包被处理得不一样。改用整段会话的音色向量、只校正模型自己的输出之后，16 句测试的字错误率从 16.3% 降到 6.5%。
- 每 200 毫秒一次的包接缝不再有音量下陷。
- 界面重新设计，三位角色都有头像。

完整列表见 [CHANGELOG.md](CHANGELOG.md)。

## 当前文件结构

- `VERSION`，版本号，后端和界面都读它
- `start-gui.cmd`，双击启动界面；后端没有运行时由界面启动
- `start-backend.cmd`，单独启动后端
- `setup_models.py`，按固定版本下载模型并校验，缺少角色模型时调用导出
- `prepare_voices.py`，从固定版本的参考录音重建三个音色向量
- `tools/import_rvc.py`，验证、导出并安装用户 RVC 模型
- `backend/local_rvc.py`，读取本地模型配置并校验文件
- `tools/model_integrity.py`、`backend/graph_cache.py`，模型校验缓存和本机推理图优化缓存
- `third_party/rvc/`，RVC 的 MIT 许可证和集成说明
- `setup_reference_engine.py`、`backend/reference_worker.py`，可选的 Seed-VC 对照实现
- `third_party/seed_vc/`，Seed-VC 的 GPL v3 许可证和版本说明
- `make-shortcut.ps1`，生成带头像图标的快捷方式
- `backend/app.py`，HTTP 与 WebSocket 接口
- `backend/engine.py`，音频解码、OpenVoice 音色校正、文件转换入口
- `backend/character.py`，降噪、语音检测、音高跟踪和三位角色的模型推理
- `backend/live.py`，按包渲染、SOLA 对齐和接缝交叉淡化
- `gui/app.py`，主窗口
- `gui/widgets.py`、`gui/theme.py`，自绘控件（含角色转盘）和配色
- `gui/catalog.py`、`assets/characters.json`，角色分类和每位角色的颜色、头像
- `gui/audio.py`，设备、录音、播放和实时通道的缓冲
- `gui/live.py`，实时变声的工作线程
- `gui/backend.py`，后端客户端和启动器
- `gui/taskbar.py`，任务栏图标归组
- `gui/selfcheck.py`，打开真实窗口跑一遍主要流程
- `tools/export_voices.py`，把 RVC 和 So-VITS-SVC 权重导出成 ONNX
- `tools/eval/`，客观评测脚本
- `voices/`，三个 256 维音色向量
- `assets/`，头像、Q 版形象、图标、角色原声和试听示例
- `notes/`，决策记录和已知问题
- `CHANGELOG.md`，更新日志

`models/` 里的权重和 `.run/` 里的构建缓存不进仓库。

## 目前能做什么

### 实时变声

- 麦克风输入连续重采样到 22,050 Hz；VB-CABLE 默认每 120 毫秒送一包，Steam 为 200 毫秒
- 输出发往 Discord 用的虚拟麦克风，或从耳机监听
- 说话时切换角色或强度会自动重连
- 默认每 3,000 包自动刷新实时会话，不重启程序或重载模型
- 停顿时输出静音，不会把底噪变成角色的声音
- 界面显示延迟、每包处理时间、丢弃的输入和播放断流次数

### 文件变声

- 录音，或导入 WAV、FLAC、MP3、OGG，最长 60 秒
- 原声和结果随时切换试听，播放位置保持不变
- 另存为 22,050 Hz 单声道 WAV
- 结果与生成它的输入、角色、强度和处理方式绑定，改了设置就不能把旧结果当成新结果保存

### 界面

- 角色列表来自后端，按分类显示；左右三角切换，当前角色居中，其余角色在两侧虚化
- 每位角色都能播放原始配音或直播录音作对照
- 白色底，粉色点缀
- 启动时检查后端，没有运行就启动，关闭窗口时一并停止
- 后端启动失败时显示脚本的退出码和最后几行输出
- 设备被拔出、引擎被占用时给出原因并释放设备

## 当前推理流程

一包音频经过的步骤：

1. GTCRN 连续降噪，Silero VAD 判断是否在说话。
2. RMVPE 跟踪音高，按所选档位使用固定半音、原有角色目标音域，或在模型设置后再升调。
3. ContentVec 第 12 层提取 768 维发音特征，检索本角色索引的 8 个近邻，以距离平方的倒数加权。
4. 在特征域保护清辅音，再由本角色的 RVC v2 模型生成波形。100% 强度时不会把说话人的原始有声波形混回来，也不会再经过另一个音色转换模型。
5. 语音门控、SOLA 对齐、分频交叉淡化与最终限幅，再发送有 104 毫秒前瞻的音频。

没有导入本地角色模型时仍可使用原来的兼容声线，界面会显示实际模型名。原兼容路径和可选 Seed-VC 的历史取舍见决策记录。

每一步为什么这样做、试过哪些别的做法，记录在 [notes/decisions.md](notes/decisions.md)。

## 0.1.0 的评测记录

以下为历史结果。灯和爱音的相似度对照音已查明为第三方合成语音，不能用来评价与角色原始配音的接近程度。

在 i5-12400F、RTX 5060 Ti、Windows 11 上测得。

| 项目 | 结果 |
| --- | --- |
| 每 200 毫秒一包的处理时间 | 平均 59 毫秒，95 分位 80 毫秒 |
| 从说话到虚拟麦克风收到声音的延迟 | 0.77 到 0.88 秒 |
| Discord 通话输出的播放断流 | 六次短句测试都是 0 次 |
| 字错误率，干净女声 / 干净男声 / 加噪男声 | 1.3% / 2.0% / 16.3% |
| 说话人相似度，高松灯 / 永雏塔菲 / 千早爱音 | 0.607 / 0.541 / 0.661 |
| 包接缝处的能量 | 0.94 以上（修复前 0.82 到 0.86） |

字错误率和相似度来自 `tools/eval/` 的 16 句合成语音测试集，每个条件每位角色 153 个字。没有做过真人录音和听感测试。

## 接口

后端监听 `http://127.0.0.1:8765`，[接口文档](http://127.0.0.1:8765/docs) 在后端运行时可以打开。

| 请求 | 返回 |
| --- | --- |
| `GET /api/health` | 版本、引擎、推理设备、采样率、最长时长和上传大小上限 |
| `GET /api/voices` | 数组，每条记录包含 `id` 和中文 `name` |
| `POST /api/convert?voice_id=taffy&strength=1` | 请求体直接放音频文件字节。成功返回 `audio/wav`，22,050 Hz 单声道 PCM16 |

`voice_id` 以 `GET /api/voices` 为准；本机有 `tomori`、`taffy`、`anon`、`tannhauser`。额外角色导入后重启后端即可成为可用选项，未安装的角色不显示，非法 ID 返回 422。`strength` 范围 0 到 1。所有角色支持 `mode=character`（音色优先，默认）和 `mode=call`（通话清晰），文件接口和实时接口使用同一参数。支持 WAV、FLAC、MP3、OGG，单声道或双声道，8 到 96 kHz，0.35 到 60 秒，最多 24 MiB。

RVC 音高参数同样适用于两个接口：GUI 当前默认发送 `pitch_offset=4`，在模型配置调整之后再升 4 半音。低层接口仍支持通用 `pitch_shift` 固定移调，便于已有客户端和导入配置继续工作；不再提供专门的原声 +4 预设。二者均为有限数值，范围 -24 至 +24；两者可同时给出，省略时保留旧客户端的原有模型配置。`GET /api/health` 的 `pitch_control` 表明支持，WebSocket 握手回显所用值。Seed-VC 参考路径未实现这两个音高控制，GUI 对相关角色禁用音高选择。

错误用 HTTP 状态码和 JSON 的 `detail` 表示。413 是文件过大，422 是音频或参数无效，429 是引擎正忙，500 是推理失败。一次只处理一个转换任务或一个实时会话。

```powershell
curl.exe --fail-with-body "http://127.0.0.1:8765/api/convert?voice_id=taffy&strength=1" -H "Content-Type: audio/wav" --data-binary "@assets/previews/original.wav" -o taffy-test.wav
```

### 实时通道

连接 `ws://127.0.0.1:8765/api/live?voice_id=taffy&strength=1&low_latency=true&speech_context=true&packet_ms=120`，等待首条 JSON 消息：

```json
{"sample_rate": 22050, "frame_samples": 2646, "format": "s16le", "lookahead_samples": 2304}
```

1. 把采集到的音频连续重采样为 22,050 Hz 单声道，每凑齐 `frame_samples` 个小端 PCM16 样本发一条二进制消息。
2. 每发一包收到一条二进制 PCM16 回包。累计输入不足前瞻时，回包是空二进制消息；累计输出长度始终为 `max(0, 累计输入样本数 - lookahead_samples)`。此例首包为 342 个样本，后续每包 2,646 个，按顺序播放。
3. 正常停止时，把不足一包的输入补零发出，再发文本 `finish`，读回剩余样本（此例为 2,304 个）和关闭帧。输入总长不足前瞻时，尾包返回全部输入样本；无输入时为空。中途取消可以直接断开。
4. 关闭码 1013 是引擎正忙，1003 是包长度不对，1001 是超过 30 秒没有收到音频，1008 是来源不被允许。切换角色或强度需要重新连接。

`packet_ms` 支持 80、100、120 和 200，省略时保留旧客户端的 200 毫秒 / 4,410 样本；80 和 100 为实验包长，GUI 只开放 100 的可选档。`GET /api/health` 的 `live_packet_ms` 列出支持值，GUI 连接旧后端时回退到兼容包长。实验 Seed-VC 保留 200 毫秒。省略 `low_latency` 时每包 8,192 个样本，省略 `speech_context` 时前瞻为 1,024 个样本。以握手里的 `frame_samples` 为准。

## 评测

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\eval\make_evalset.ps1 -Sentences tools\eval\sentences.txt -OutDir .run\evalset
powershell -NoProfile -ExecutionPolicy Bypass -File tools\eval\run_config.ps1 -Tag my-change
.venv\Scripts\python.exe tools\eval\join_test.py my-change
```

`run_config.ps1` 在进程内按实时路径渲染测试集，输出字错误率、相似度和耗时，不占用正在运行的后端。识别用的 SenseVoice 模型和 CAM++ 模型需要自己放进 `.run/`，位置见脚本开头；角色参考音使用仓库里的真实录音。`compare_references.py` 可对同一批新旧输出分别计算提示录音和独立片段的相似度。

`.venv-gui\Scripts\python.exe -m gui.selfcheck` 打开真实窗口，把导入、变声、试听、保存、录音、实时变声、角色切换和退出跑一遍。试听会出声。录音和实时变声需要一对虚拟音频线设备提供麦克风信号，找不到时跳过。设备被拔出、引擎被占用和启动脚本失败是模拟的，输出里有注明。

## 声线与素材来源

本项目是爱好者作品，与角色、表演者和权利方没有关联。模型权重不随仓库分发，由 `setup_models.py` 从原发布地址按固定版本下载。

| 项目 | 来源 |
| --- | --- |
| 旧版兼容声线的灯、爱音模型 | TogetsuDo 发布的 RVC v2 权重和 FAISS 索引。[高松灯](https://huggingface.co/TogetsuDo/tomori-rvc) · [千早爱音](https://huggingface.co/TogetsuDo/anon-rvc) |
| 旧版兼容声线的塔菲模型 | NyaruTaffy 32 kHz 的 So-VITS-SVC 3.0 权重，使用配置里的 `taffy` 说话人。[模型与配置](https://huggingface.co/spaces/ZilliaxOfficial/nyaru-svc-3.0/tree/main) |
| 原始参考录音 | [灯官方角色 CM](https://www.youtube.com/watch?v=oo5DW-QZYeo)、[爱音官方角色 CM](https://www.youtube.com/watch?v=7GZ-7YQ-sKk) 分离配乐后的说话片段；[塔菲直播数据集](https://huggingface.co/datasets/KYOU-0/Ace-Taffy-voice)。固定版本、时间段和校验值见 `assets/references/sources.json`。旧第三方合成参考已替换 |
| 本次导入的模型 | 灯与塔菲为用户提供的 `.pth` / `.index`；爱音取自 [Wanlau/RVC_BanGDream](https://huggingface.co/Wanlau/RVC_BanGDream)，使用 bestdori 对白数据训练。权重与索引的固定版本、SHA-256 见安装记录 |
| RVC 后端 | [RVC 官方项目](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)，MIT 许可，固定导出版本与实现说明见 `third_party/rvc/` |
| 可选对照引擎 | [Seed-VC](https://github.com/Plachtaa/seed-vc)，源码与 GPL v3 见 `third_party/seed_vc/`；下载地址与 SHA-256 见 `tools/seed_models.json`。默认不安装、不启动 |
| 高松灯、千早爱音的头像 | 从动画《BanG Dream! It's MyGO!!!!!》官网的角色立绘裁出，版权归原权利方所有。[角色页](https://anime.bang-dream.com/mygo/character/) |
| 永雏塔菲的头像 | 账号的公开头像。[账号主页](https://space.bilibili.com/1265680561) |
| Q 版永雏塔菲 | 游戏《盲盒派对》联动角色“王牌发明家”的 Q 版形象，取自该游戏的 BWIKI 文件页，版权归原权利方所有。[角色页](https://wiki.biligame.com/gachaparty/?curid=378) |
| 诗歌剧模型、头像与原声 | 模型来自用户的 `诗歌剧.zip`，训练数据未核实；头像与短语音为 [Cygames 官方角色页](https://umamusume.jp/character/matikanetannhauser) 提供的素材，来源与校验值见 `assets/tannhauser-source.json`，版权归原权利方所有 |
| 试听示例 | `assets/previews/original.wav` 是 Windows 中文合成语音，其余由本后端转换。界面从 0.3.0 起不再播放它们，保留给评测和自检 |
| 算法与模型 | [RVC](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) · [OpenVoice](https://github.com/myshell-ai/OpenVoice) · [GTCRN](https://github.com/Xiaobin-Rong/gtcrn) · [Silero VAD](https://github.com/snakers4/silero-vad)。各模型的下载地址和校验值在 `setup_models.py` |

请不要用变声结果冒充真人或发布成官方内容。

## 文档约定

有实质性改动时同步更新：

- `VERSION` 和 `CHANGELOG.md`
- `notes/decisions.md`
- `notes/known-issues.md`
- 必要时更新本 README；每次发版重新核对版本号、数字和截图

## 下一步

1. 用用户本人的麦克风录音和真实 Discord 通话校准音域、音色、清晰度与延迟。
2. 扩充跨场景、没有参与训练的原始对白，检查模型的泛化。
3. 对照试听确认默认档位；自动相似度不代替听感。
4. 在其他显卡和没有独立显卡的电脑上测速度。
