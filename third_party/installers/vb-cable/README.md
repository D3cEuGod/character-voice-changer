# VB-CABLE 官方原版安装包

来源：[VB-Audio 官方下载页](https://vb-audio.com/Cable/)。VB-CABLE 是 donationware，欢迎支持原作者；它不是本项目的开源代码。原始 ZIP 未修改，原作者的安装说明、许可证与声明保留在包内及 `VENDOR-README.txt`。不把驱动集成进本程序的自动安装流程，作为独立前置组件手动安装。

文件：`VBCABLE_Driver_Pack46.zip`。SHA-256：

```text
bc44e8974191a5a2427d6c979e2dab08dbb09925f3f435dfa2f0ba3e45b6eb90
```

下载来源、时间和大小见 `provenance.json`。本机检查到安装程序有效签名来自 BUREL VINCENT Entrepreneur individuel，Win10/11 驱动目录的有效签名来自 Microsoft Windows Hardware Compatibility Publisher。

## 安装

1. 把 ZIP 的**全部文件**解压到纯英文目录，例如 `C:\Temp\VBCable`。不要直接在 ZIP 里运行，也避免在带中文的项目路径中运行安装器；本机曾因此出现找不到 INF 的报错。
2. 64 位 Windows 右键 `VBCABLE_Setup_x64.exe`，选“以管理员身份运行”，点 **Install Driver**。
3. 安装结束后保存工作并手动重启 Windows。安装器要求重启，本项目不自动重启电脑。

## 变声器与 Discord

```text
手机麦克风 → WO Mic → 角色变声器 → CABLE Input → CABLE Output → Discord
```

- WO Mic Client 保持“已连接”，取消“设置 → 本地播放”，避免额外播放原声。
- 变声器“麦克风”选择 `Microphone (WO Mic Device)`，打开“发到语音软件”（想自己也听到就再打开“耳返”），开启实时变声。
- 软件自动优先使用 `CABLE Input (VB-Audio Virtual Cable)` 写入变声结果；没有 VB-CABLE 时才使用 Steam 备用设备。
- Discord 的输入选择 **CABLE Output (VB-Audio Virtual Cable)**，输出仍选择自己的耳机。Discord 若选 WO Mic，会绕过变声处理。
- 安装新驱动后重新打开变声器和 Discord，以重新枚举设备。

重启后，用户已在真实 Discord 通话中确认 VB-CABLE 能传递变声结果；关闭 WO Mic 本地播放后，朋友确认只剩变声。0.2.1 已补做 VB-CABLE 本机回录，短句平均约 0.74 秒、长句约 0.66–0.68 秒，三位角色各约 48 秒长句均零断流。手机传输和 Discord 远端延迟未计入，仍需实际通话复听。本次驱动内部设置保留默认，不需要再次重启 Windows。
