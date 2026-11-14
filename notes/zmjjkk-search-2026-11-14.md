# ZmjjKK / 郑永康语音权重检索

日期：2026-11-14。目标为可下载并验证、能接入本机变声器的说话人权重，优先 RVC `.pth` 与配套 `.index`，同时检索 SoVITS、声音克隆和 AI 翻唱线索。本次未取得符合条件的权重，未添加可用角色，也不能据此断言所有地方都不存在。

## 新线索

找到 CHILLSOO 的 [ZmjjKK AI 翻唱《网》](https://www.bilibili.com/list/1847270864/?bvid=BV1fHiGBpE52&oid=115815017880070)，BV 号 `BV1fHiGBpE52`。页面标签包含康康、ZmjjKK、郑永康和 AI 翻唱。公开简介只写原曲出处，没有看到模型类型、权重文件、训练配置或网盘下载地址。

这说明存在以该名字发布的 AI 翻唱作品，不能仅凭标题判断它使用 RVC，或者推断专用权重已经公开。该作品是目前更有价值的作者线索，尚未得到可安装文件。未代用户给作者发消息或评论。

## 实际检索范围

- 名字：`郑永康`、`康康`、`康神`、`ZmjjKK`、`KangKang`、`Kang-Kang`、`ZhengYongkang`、`zheng-yong-kang`；搭配 RVC、SoVITS、GPT-SoVITS、变声器、声音模型、权重、pth、AI 翻唱与下载。
- 直接查询 Hugging Face 的模型、数据集和 Space 目录，共 24 个名字 / 目录组合。中文三名及两种完整拼音没有命中；`KangKang` 和 `ZmjjKK` 的命中进一步核对文件清单、任务类型和模型配置。`Kang-Kang` 被站点宽泛匹配为 `kang`，结果较多且部分达到 100 条上限，不当作完整穷尽。
- GitHub 按 `ZmjjKK`、`郑永康`、`康康 RVC`、`康神` 搜仓库，核对较相关仓库的 README 或文件列表；不是仅凭仓库名认定声音模型。
- 对妙音、Fish Audio、Weights、ModelScope 与 B 站等做域名 / 关键词检索，扩展“康神语音盒”和 AI 翻唱的线索。没有把搜索索引没有结果当成完整站内目录的证明。

## 已排除的候选

| 候选 | 核对结果 |
| --- | --- |
| [sake2323/zmjjkk-lora](https://huggingface.co/sake2323/zmjjkk-lora) | FLUX.1-dev 图像 LoRA，配套 JPG 样图，不是语音转换权重 |
| `zmjjkk1122/zmjjkk` | 文件清单未见 RVC / SoVITS 权重与索引 |
| `kangkang/kangkang` 等 | 若干空仓库或只有元数据；没有可用说话人权重 |
| `kangkangjacky/my_awesome_mind_model` | wav2vec2 音频分类、MINDS14 任务，不是该选手的语音转换模型 |
| 其余 `KangKang` 命中 | 问答、金融、机器人、OCR、图像工具或其他用户的应用；未建立与选手专用语音模型的关系 |
| [jiubao76799-png/ZmjjKK-skills](https://github.com/jiubao76799-png/ZmjjKK-skills) | Markdown 语言风格 / 角色模拟说明，没有声音生成权重；只读说明，未安装该技能 |
| [real-reb/sts2-ZmjjkkMod](https://github.com/real-reb/sts2-ZmjjkkMod) | 游戏角色模组，README 描述游戏代码和运行资源 |
| [chenwenxiong/zmjjkk](https://github.com/chenwenxiong/zmjjkk) | 根目录为 HTML、图片和 MP3 音频，未见模型权重；不作为实时语音算法 |
| “康神语音盒”下载页面 | 搜索结果介绍主要是录音条目 / 预设音效，未找到公开的权重下载与架构说明 |

## 访问限制

妙音 WordPress 搜索接口和 MCP 页面匿名请求返回 403；B 站视频信息 API 返回 412。随后使用普通浏览器打开作品并滚动到评论区，页面显示 3 条评论，匿名能看到的两条主要为 @ 选手，没有下载地址；完整评论要求登录，未取得其余内容。作品正文仍只有原曲出处。部分旧 GitHub 搜索命中的仓库读取时返回 404。没有绕过这些限制，也没有购买、注册或安装不明客户端。

因此结论仅为“本次公开检索未获得可下载验证的语音权重”，不代表作者没有自用模型，或登录后 / 群内一定没有资源。若后续获得发布者的 RVC 文件，可按现有导入器检查架构、索引维度和实际输出再接入。

Hugging Face 名字查询和候选元数据摘要保存在 `evaluation/0.4.2/`，方便继续追踪。
