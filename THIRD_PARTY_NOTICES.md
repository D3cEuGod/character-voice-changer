# 第三方组件与许可

角色变声器使用了下面这些开源软件、模型和外部组件。每一项的许可以上游仓库或发布页为准；这里列出的是 1.0.0 发布时核对的版本和许可类型，方便分发前检查。

## 程序库

| 组件 | 版本 | 许可 | 用在哪里 |
| --- | --- | --- | --- |
| [Qt 6 / PySide6](https://doc.qt.io/qtforpython-6/) | 6.12.0 | LGPL-3.0 | 桌面界面 |
| [NumPy](https://numpy.org/) | 2.5.4 | BSD-3-Clause | 音频数组 |
| [SciPy](https://scipy.org/) | 1.18.1 | BSD-3-Clause | 后端信号处理 |
| [python-sounddevice](https://github.com/spatialaudio/python-sounddevice) / [PortAudio](https://www.portaudio.com/) | 0.5.6 | MIT | 录音和播放 |
| [python-soundfile](https://github.com/bastibe/python-soundfile) / [libsndfile](https://libsndfile.github.io/libsndfile/) | 0.14.0 | BSD-3-Clause / LGPL-2.1 | 读写音频文件 |
| [python-soxr](https://github.com/dofuuz/python-soxr) / libsoxr | 1.1.0 | LGPL-2.1+ | 重采样 |
| [websockets](https://github.com/python-websockets/websockets) | 17.4 | BSD-3-Clause | 实时变声通道 |
| [FastAPI](https://github.com/fastapi/fastapi) | 0.162.4 | MIT | 本机引擎接口 |
| [Uvicorn](https://github.com/encode/uvicorn) | 0.54.0 | BSD-3-Clause | 本机引擎服务 |
| [ONNX Runtime (DirectML)](https://github.com/microsoft/onnxruntime) | 1.24.4 | MIT | 模型推理 |
| [ONNX](https://github.com/onnx/onnx) | 1.23.2 | Apache-2.0 | 模型格式 |
| [FAISS](https://github.com/facebookresearch/faiss) | 1.16.0 | MIT | 检索索引 |
| [Praat / parselmouth](https://github.com/YannickJadoul/Parselmouth) | 0.4.7 | **GPL-3.0** | 兼容声线的音高提取 |

**分发时要注意：** parselmouth（Praat）是 GPL-3.0。只要安装包里带上它，整个程序的分发就要遵守 GPL-3.0（提供源代码等）。如果不想这样，需要先把它从默认引擎里换掉。

## 模型与算法

| 组件 | 许可 | 说明 |
| --- | --- | --- |
| [RVC (Retrieval-based-Voice-Conversion-WebUI)](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) | MIT | 推理流程参考，见 `third_party/rvc/` |
| [RMVPE](https://github.com/yxlllc/RMVPE) | 以上游为准 | 音高提取模型 |
| [ContentVec](https://github.com/auspicious3000/contentvec) | MIT | 语音内容特征 |
| [GTCRN](https://github.com/Xiaobin-Rong/gtcrn)（sherpa-onnx 导出） | MIT | 降噪 |
| [Silero VAD](https://github.com/snakers4/silero-vad) | MIT | 语音检测 |
| [OpenVoice V2](https://github.com/myshell-ai/OpenVoice) | MIT | 兼容声线的音色校正，见 `models/LICENSE.txt` |
| [So-VITS-SVC 3.0 塔菲模型](https://huggingface.co/spaces/ZilliaxOfficial/nyaru-svc-3.0) | 以上游为准 | 兼容声线 |
| [Seed-VC](https://github.com/Plachtaa/seed-vc) | **GPL-3.0** | 可选对照引擎，默认不安装，见 `third_party/seed_vc/` |

## 角色声线与素材

角色名称、头像、官方配音片段和角色声线模型（`models/local-rvc/` 里的 `.pth` / `.index`）的权利属于各自的权利人，**不属于本项目**，也不随 Git 仓库分发大权重。它们只供个人在本机娱乐使用。公开或收费分发前，必须先取得权利人的授权，或改用原创 / 已获授权的声线和形象。

## 外部组件

[VB-CABLE](https://vb-audio.com/Cable/) 是 VB-Audio 的 donationware 虚拟声卡驱动，不是本项目的开源代码。仓库里保存了官方原版安装包，供本机手动安装；把它打进自己的安装包再分发，需要按 [VB-Audio 授权说明](https://vb-audio.com/Services/licensing.htm) 取得许可。
