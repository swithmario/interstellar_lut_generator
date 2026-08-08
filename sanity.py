# resolve_identity33.py  – writes Resolve-neutral identity cube
N = 33
with open("identity33.cube","w") as f:
    f.write('TITLE "identity33"\nLUT_3D_SIZE 33\n')
    f.write('DOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
    for r in range(N):          # any loop order is fine
        for g in range(N):
            for b in range(N):
                R = r/(N-1); G = g/(N-1); B = b/(N-1)
                f.write(f"{B:.6f} {G:.6f} {R:.6f}\n")   # <<< B G R
print("identity33.cube written.")
