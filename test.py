# build_lut_rgb.py --------------------------------------------------
# Pure RGB Δ-mapping LUT (no colour-space gymnastics).
# ------------------------------------------------------------------
# requirements:  pip install numpy pillow
# ------------------------------------------------------------------
import numpy as np
from PIL import Image
import glob, os, time, sys

# ---------- user config -------------------------------------------
ORIGINAL_PATTERN  = "Original_*.tif"
CORRECTED_PATTERN = "Corrected_*.tif"
LUT_SIZE   = 33                    # 17 / 33 / 65
STRENGTH   = 1.0                   # 1 = full delta, 0.5 = half, etc.
OUTPUT_LUT = "Interstellar_Cliff_RGB.cube"
# ------------------------------------------------------------------

def first_match(pat):
    files = glob.glob(pat)
    if not files:
        sys.exit(f"No file matches '{pat}'")
    if len(files) > 1:
        print(f"Multiple matches for {pat}, using {files[0]}")
    return files[0]

orig_file = first_match(ORIGINAL_PATTERN)
corr_file = first_match(CORRECTED_PATTERN)
print(f"Using:\n  Original  = {orig_file}\n  Corrected = {corr_file}")

# -------- load (Pillow supports 16-bit TIFF) ----------------------
def load_rgb(path):
    arr = np.asarray(Image.open(path), np.float32)
    if arr.dtype != np.float32: arr = arr.astype(np.float32)
    if arr.max() > 256:         # 16-bit
        arr /= 65535.0
    else:                       # 8-bit
        arr /= 255.0
    return arr

A = load_rgb(orig_file)
B = load_rgb(corr_file)
if A.shape != B.shape:
    sys.exit("Images not same resolution!")

delta = B - A     # pixel-wise RGB difference  (range ≈ –1 .. +1)

# -------- accumulate into cube ------------------------------------
cube   = np.zeros((LUT_SIZE, LUT_SIZE, LUT_SIZE, 3), np.float32)
counts = np.zeros((LUT_SIZE, LUT_SIZE, LUT_SIZE),   np.int32)

idx = np.floor(A.reshape(-1,3) * (LUT_SIZE-1)).clip(0,LUT_SIZE-1).astype(int)
for (r,g,b), d in zip(idx, delta.reshape(-1,3)):
    cube[r,g,b] += d
    counts[r,g,b] += 1

nz = counts > 0
cube[nz] /= counts[nz,None]     # average ΔRGB per bin
cube *= STRENGTH                # scale

# -------- build final LUT grid ------------------------------------
lin = np.linspace(0,1,LUT_SIZE, dtype=np.float32)
for r in range(LUT_SIZE):
    for g in range(LUT_SIZE):
        for b in range(LUT_SIZE):
            base = np.array([lin[r], lin[g], lin[b]], np.float32)
            cube[r,g,b] = np.clip(base + cube[r,g,b], 0, 1)

# -------- write .cube (R-fastest) ---------------------------------
with open(OUTPUT_LUT,"w") as f:
    f.write('TITLE "Interstellar Cliff RGB"\n')
    f.write(f'LUT_3D_SIZE {LUT_SIZE}\n')
    f.write('DOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n')
    for r in range(LUT_SIZE):
        for g in range(LUT_SIZE):
            for b in range(LUT_SIZE):
                rr,gg,bb = cube[r,g,b]
                f.write(f"{rr:.6f} {gg:.6f} {bb:.6f}\n")

print(f"✓ Wrote {OUTPUT_LUT}")
