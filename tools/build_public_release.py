"""导出可以公开上传的“公开版”源代码：不带角色模型、头像、原声、VB-CABLE 安装包和私人笔记，也不带 Git 历史。

用法（在项目目录里）：
  python tools\\build_public_release.py D:\\VoiceChanger-public            # 只导出文件
  python tools\\build_public_release.py D:\\VoiceChanger-public --git      # 另外建一个只有一次提交的新仓库

导出的是某个提交（默认 HEAD）里登记在 Git 的文件，工作区里没提交的改动和本机模型都不会带出去。
导出后：
- 删掉 EXCLUDE 里列出的路径；
- 用 tools/public/ 里的文件覆盖同名文件（公开版 README、LICENSE、CHANGELOG、许可说明、空的角色表）；
- 放一个 PUBLIC_EDITION 标记，后端看到它就不再加载、也不下载内置角色；
- 最后逐个文件检查：没有模型权重、图片、音频（预热用的合成语音除外）、安装包，也没有超过 2 MB 的文件。
检查不通过时报错退出，不会留下半成品仓库。
"""
from __future__ import annotations

import argparse
import fnmatch
import io
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OVERLAY_PREFIX = "tools/public/"  # 公开版专用的 README、LICENSE 等，导出时覆盖到根目录

# 公开版不带的路径（相对项目根目录，支持通配符；目录会整个删掉）
EXCLUDE = (
    "notes",                        # 私人开发笔记与本机记录
    "docs",                         # 截图里有角色头像
    "voices",                       # 旧版角色的说话人特征
    "assets/*-avatar.*",            # 官方头像
    "assets/*-chibi.*",
    "assets/taffy-avatar.ico",
    "assets/*-source.json",
    "assets/references",            # 角色原声片段
    "assets/comparisons",           # 角色变声对照
    "assets/pitch-comparisons",
    "assets/previews/*",            # 只保留 original.wav（Windows 合成语音，后端预热要用）
    "!assets/previews/original.wav",
    "third_party/installers",       # VB-CABLE 安装包，按其授权不能随仓库再分发
    "third_party/seed_vc",          # 可选的 GPL-3.0 对照引擎，公开版不用
    "setup_reference_engine.py",
    "requirements-reference.txt",
    "backend/reference_worker.py",
    "tools/seed_models.json",
    "prepare_voices.py",            # 准备旧版角色特征
    "tools/public",                 # 覆盖文件本身，已经拷到根目录
    "tools/build_public_release.py",
)

# 检查：这些后缀一律不许出现（下面的白名单除外）
BANNED_SUFFIXES = {".pth", ".pt", ".ckpt", ".safetensors", ".index", ".onnx", ".npy", ".npz", ".bin",
                   ".zip", ".7z", ".rar", ".exe", ".msi", ".dll",
                   ".wav", ".flac", ".mp3", ".ogg", ".m4a",
                   ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp"}
ALLOWED = {"assets/previews/original.wav", "assets/app-icon.png", "assets/app-icon.ico"}
MAX_BYTES = 2 << 20

MARKER = """这是角色变声器的公开版：不带任何内置角色。
后端看到这个文件就只准备共用模型（ContentVec、RMVPE、GTCRN、Silero VAD），声线由用户在界面里导入。
删掉它会让后端去下载旧版内置角色，公开版不要删。
"""


def excluded(path: str) -> bool:
    hit = False
    for pattern in EXCLUDE:
        negate = pattern.startswith("!")
        pattern = pattern.lstrip("!")
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path, pattern + "/*"):
            hit = not negate
    return hit


def export(ref: str, out: Path) -> tuple[list[str], list[str]]:
    """把 ref 里的文件解到 out：跳过排除的路径，tools/public/ 里的文件覆盖到根目录。

    覆盖文件也取自同一个提交，所以导出结果只取决于 ref，和工作区里没提交的改动无关。
    """
    data = subprocess.run(["git", "archive", "--format=tar", ref], cwd=ROOT, check=True, capture_output=True).stdout
    written, overlays = {}, {}
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            if member.name.startswith(OVERLAY_PREFIX):
                overlays[member.name[len(OVERLAY_PREFIX):]] = archive.extractfile(member).read()
            elif not excluded(member.name):
                written[member.name] = archive.extractfile(member).read()
    if not overlays:
        raise SystemExit(f"{ref} 里没有 {OVERLAY_PREFIX}，无法导出公开版")
    for name, blob in {**written, **overlays}.items():
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)
    (out / "PUBLIC_EDITION").write_text(MARKER, encoding="utf-8")
    return sorted(written), sorted(overlays)


def audit(out: Path) -> list[str]:
    """返回不该出现在公开版里的文件和原因；空列表表示通过。"""
    problems = []
    for path in sorted(out.rglob("*")):
        if not path.is_file() or ".git" in path.relative_to(out).parts:
            continue
        relative = path.relative_to(out).as_posix()
        if relative in ALLOWED:
            continue
        if path.suffix.lower() in BANNED_SUFFIXES:
            problems.append(f"{relative}: 不允许的文件类型")
        elif path.stat().st_size > MAX_BYTES:
            problems.append(f"{relative}: 超过 2 MB")
    for name in ("PUBLIC_EDITION", "LICENSE", "README.md", "THIRD_PARTY_NOTICES.md", "assets/characters.json"):
        if not (out / name).is_file():
            problems.append(f"{name}: 缺少")
    return problems


def init_repo(out: Path, ref: str) -> None:
    version = (out / "VERSION").read_text(encoding="utf-8").strip()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=out, check=True)
    subprocess.run(["git", "add", "-A"], cwd=out, check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"角色变声器 {version} 公开版"], cwd=out, check=True)
    print(f"已在 {out} 建立新仓库（main 分支，一次提交，没有私人仓库的历史）")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path, help="导出到这个文件夹（必须不存在或为空）")
    parser.add_argument("--ref", default="HEAD", help="导出哪个提交，默认 HEAD")
    parser.add_argument("--git", action="store_true", help="导出后建立只有一次提交的新 Git 仓库")
    args = parser.parse_args(argv)
    out = args.out.resolve()
    if out == ROOT or ROOT in out.parents:
        parser.error("导出目录不能在项目文件夹里面")
    if out.exists() and any(out.iterdir()):
        parser.error(f"{out} 不是空文件夹")
    out.mkdir(parents=True, exist_ok=True)
    try:
        files, copied = export(args.ref, out)
        problems = audit(out)
        if problems:
            raise SystemExit("公开版检查没通过：\n  " + "\n  ".join(problems))
        if args.git:
            init_repo(out, args.ref)
    except BaseException:
        shutil.rmtree(out, ignore_errors=True)
        raise
    print(f"导出 {len(files)} 个文件，覆盖 {len(copied)} 个公开版文件，检查通过：{out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
