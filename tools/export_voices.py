"""Export pinned RVC v2 and So-VITS-SVC 3.0 weights to fixed one-second ONNX graphs.

Build inputs are the upstream checkouts and weights listed in README.md.
Run in a separate torch environment. Normal application startup uses ONNX only.
"""
import argparse
import json
import math
import sys
import tempfile
import types
from pathlib import Path

import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]


def export(module, inputs, names, name):
    import onnx
    target = ROOT / "models" / f"{name}.onnx"
    with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".part", delete=False) as tmp:
        part = Path(tmp.name)
    try:
        module.eval()
        torch.onnx.export(module, inputs, str(part), dynamo=False, opset_version=18,
                          input_names=names, output_names=["output"], external_data=False)
        onnx.checker.check_model(str(part))
        part.replace(target)
    finally:
        part.unlink(missing_ok=True)


def export_rvc(src, weights, key):
    sys.path.insert(0, str(src))
    from infer.lib.infer_pack.models_onnx import SynthesizerTrnMsNSFsidM

    checkpoint = torch.load(weights / f"{key}.pth", map_location="cpu", weights_only=True)
    config = checkpoint["config"]
    config[-3] = checkpoint["weight"]["emb_g.weight"].shape[0]
    net = SynthesizerTrnMsNSFsidM(*config, is_half=False, version=checkpoint["version"])
    missing, unexpected = net.load_state_dict(checkpoint["weight"], strict=False)
    if unexpected or any(not k.startswith("enc_q.") for k in missing):
        raise ValueError(f"Incompatible RVC checkpoint: {missing}, {unexpected}")

    class RVC(nn.Module):
        def __init__(self):
            super().__init__()
            self.net = net

        def forward(self, units, pitch, f0, noise):
            return self.net(units, torch.tensor([100]), pitch, f0, torch.tensor([0]), noise)

    export(RVC(), (torch.randn(1, 100, 768), torch.full((1, 100), 80),
                   torch.full((1, 100), 220.), torch.randn(1, 192, 100)),
           ["units", "pitch", "f0", "noise"], key + "_rvc")


def export_taffy(src, weights):
    sys.path.insert(0, str(src))
    from hubert.hubert_model import HubertSoft
    from vdecoder.hifigan.models import SineGen

    # Equivalent expressions for operations unsupported by the legacy exporter:
    # the phase-wrap correction only adds multiples of 2*pi before sine.
    def sine(self, hz):
        return torch.sin(torch.cumsum(hz / self.sampling_rate, dim=1) * (2 * math.pi))

    def coarse(f0):
        low = 1127 * math.log1p(50 / 700)
        high = 1127 * math.log1p(1100 / 700)
        return ((1127 * torch.log1p(f0 / 700) - low) * (254 / (high-low)) + 1.5).clamp(1,255).long()

    SineGen._f02sine = sine
    # Upstream's inference network imports just this symbol from a module
    # that also loads its audio training and plotting dependencies.
    utils = types.ModuleType("utils")
    utils.f0_to_coarse = coarse
    sys.modules["utils"] = utils
    import models
    cfg = json.loads((src / "configs/nyarutaffy.json").read_text())
    net = models.SynthesizerTrn(641, 56, **cfg["model"])
    state = torch.load(weights / "taffy.pth", map_location="cpu", weights_only=True)["model"]
    net.load_state_dict(state)

    class Taffy(nn.Module):
        def __init__(self):
            super().__init__()
            self.net = net

        def forward(self, units, f0):
            return self.net.infer(units, f0, torch.tensor([[cfg["spk"]["taffy"]]]))

    export(Taffy(), (torch.randn(1,256,100), torch.full((1,100),220.)),
           ["units","f0"], "taffy_svc")

    class Units(HubertSoft):
        def forward(self, audio):
            return self.units(audio)

    hubert = Units()
    state = torch.load(weights / "hubert.pt", map_location="cpu", weights_only=True)
    torch.nn.modules.utils.consume_prefix_in_state_dict_if_present(state, "module.")
    hubert.load_state_dict(state)
    torch.backends.mha.set_fastpath_enabled(False)
    export(hubert, (torch.randn(1,1,16000),), ["audio"], "hubert_soft")


if __name__ == "__main__":
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("voice", choices=["tomori","anon","taffy"])
    p.add_argument("source", type=Path)
    p.add_argument("weights", type=Path)
    args = p.parse_args()
    torch.manual_seed(0)
    torch.set_num_threads(3)
    if args.voice == "taffy":
        export_taffy(args.source.resolve(), args.weights.resolve())
    else:
        export_rvc(args.source.resolve(), args.weights.resolve(), args.voice)
