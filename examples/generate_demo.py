"""Run gen_lut.py on a deterministic RGB chart and plot the exported result."""

import argparse
from pathlib import Path
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("examples/output"))
    parser.add_argument("--figure", type=Path, default=Path("docs/lut_verification.png"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    # Every quantised RGB cell is observed. Ceil prevents 8-bit rounding from
    # assigning a nominal node to the preceding cell in the primary script.
    levels = np.ceil(np.linspace(0, 255, 33)).astype(np.uint8)
    red, green = np.meshgrid(levels, levels[::-1])
    tiles = [np.stack((red, green, np.full_like(red, b)), axis=-1) for b in levels]
    source = np.concatenate([np.concatenate(tiles[i:i + 11], axis=1)
                             for i in range(0, 33, 11)], axis=0)
    a = source.astype(np.float32) / 255
    correction = np.stack((1.07 * a[..., 0] + 0.025,
                           0.93 * a[..., 1] + 0.012,
                           0.82 * a[..., 2] + 0.012 * a[..., 0]), axis=-1)
    corrected = np.rint(np.clip(correction, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(source).save(out / "Original_rgb_chart.png")
    Image.fromarray(corrected).save(out / "Corrected_rgb_chart.png")
    # A dedicated fixture directory avoids the primary script's ambiguous
    # multiple-input fallback. The script itself is executed unchanged.
    if len(list(out.glob("Original_*.*"))) != 1 or len(list(out.glob("Corrected_*.*"))) != 1:
        raise ValueError("Use a dedicated output directory with one fixture pair")
    subprocess.run([sys.executable, str(root / "gen_lut.py")], cwd=out, check=True)
    cube_path = out / "Interstellar_Cliff_RGB_OK.cube"
    rows = np.loadtxt(cube_path, skiprows=4)
    if rows.shape != (33 ** 3, 3) or not np.isfinite(rows).all():
        raise ValueError("The exported cube must contain 35,937 finite RGB nodes")
    if rows.min() < 0 or rows.max() > 1:
        raise ValueError("Cube values are outside the declared domain")
    # The .cube file stores R fastest, then G, then B.
    cube = rows.reshape(33, 33, 33, 3).transpose(2, 1, 0, 3)
    indices = np.floor(a * 32).astype(int)
    applied = cube[indices[..., 0], indices[..., 1], indices[..., 2]]
    expected = np.clip(indices / 32 + 0.6 * (corrected / 255 - a), 0, 1)
    error = float(np.max(np.abs(applied - expected)))
    if error > 1e-6:
        raise ValueError(f"Exported RGB order or measured delta check failed: {error}")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12})
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), layout="constrained")
    for ax, data, title in zip(axes, [source, corrected, applied], [
        "Input: deterministic RGB chart",
        "Reference: known warm colour adjustment",
        "Actual exported LUT applied at 60% strength",
    ]):
        ax.imshow(data, interpolation="nearest")
        ax.set_title(title, loc="left", pad=8)
        ax.set_axis_off()
    fig.suptitle("Interstellar LUT Generator — real script output", fontsize=18)
    fig.supxlabel("33 × 33 × 33 nodes checked • R-fastest file order • synthetic 8-bit fixture\n"
                  "Each tile is a blue-channel slice. This is a numerical check, not film-colour recovery.", fontsize=11)
    args.figure.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.figure, dpi=120)
    plt.close(fig)
    print(f"Checked {len(rows):,} nodes; max absolute node error {error:.3g}")
    print(f"Wrote {args.figure}")


if __name__ == "__main__":
    main()
