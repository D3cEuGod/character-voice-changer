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

- WO Mic Client 保持“已连接”。
- 变声器“麦克风”选择 `Microphone (WO Mic Device)`，模式选择“Discord 通话”，开启实时变声。
- 软件自动优先使用 `CABLE Input (VB-Audio Virtual Cable)` 写入变声结果；没有 VB-CABLE 时才使用 Steam 备用设备。
- Discord 的输入选择 **CABLE Output (VB-Audio Virtual Cable)**，输出仍选择自己的耳机。Discord 若选 WO Mic，会绕过变声处理。
- 安装新驱动后重新打开变声器和 Discord，以重新枚举设备。

本次安装已看到 Windows PnP 中的 `VB-Audio Virtual Cable` 状态为 OK；完整的 VB-CABLE 回录与 Discord 远端听感仍需重启后验证，不能用此前 Steam 的回录结果替代。
