# make_resolve_lut_OK.py
import numpy as np, glob, sys
from PIL import Image

SIZE = 33
STRENGTH = 0.6
OUT = "Interstellar_Cliff_RGB_OK.cube"

orig = glob.glob("Original_*.*")
corr = glob.glob("Corrected_*.*")

def load(p):
    a=np.asarray(Image.open(p),np.float32)
    a/=65535.0 if a.max()>256 else 255.0
    return a

cube = np.zeros((SIZE,SIZE,SIZE,3),np.float32)

if len(orig)==1 and len(corr)==1:
    A,B = load(orig[0]), load(corr[0])
    if A.shape!=B.shape: sys.exit("Resolution mismatch")
    idx = np.floor(A.reshape(-1,3)*(SIZE-1)).astype(int)
    delta = (B-A).reshape(-1,3)
    cnt = np.zeros((SIZE,SIZE,SIZE),np.int32)
    for (r,g,b),d in zip(idx,delta):
        cube[r,g,b]+=d;  cnt[r,g,b]+=1
    mask=cnt>0
    cube[mask]/=cnt[mask,None]; cube*=STRENGTH   # average + scale

lin=np.linspace(0,1,SIZE,dtype=np.float32)
for r in range(SIZE):
    for g in range(SIZE):
        for b in range(SIZE):
            base=np.array([lin[r],lin[g],lin[b]])
            cube[r,g,b]=np.clip(base+cube[r,g,b],0,1)

with open(OUT,"w") as f:
    f.write(f'TITLE "{OUT}"\nLUT_3D_SIZE {SIZE}\n')
    f.write('DOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
    # ---- Resolve grid order: B slowest, G mid, R fastest ----
    for b in range(SIZE):
        for g in range(SIZE):
            for r in range(SIZE):
                R,G,B = cube[r,g,b]            # write RGB
                f.write(f"{R:.6f} {G:.6f} {B:.6f}\n")
print("✓ Wrote", OUT)
