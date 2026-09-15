# LUT generator handover

## Purpose and source

Experimental RGB-delta lookup table (LUT) generation from one aligned image
pair. `gen_lut.py` is the primary implementation. It averages measured RGB
deltas into a 33-cubed grid and writes an R-fastest Resolve `.cube` file.
`test.py` and `sanity.py` are retained predecessor experiments.

## Run and verify

Install `requirements.txt`. Put exactly one `Original_*` and one `Corrected_*`
image in an isolated working directory, then run `gen_lut.py` there.

For the reproducible documentation check, also install Matplotlib and run:

```sh
python examples/generate_demo.py --output-dir /path/outside/git/lut_demo
```

The example invokes the actual primary script. It reads the resulting `.cube`,
checks 35,937 finite nodes and RGB file order against a known adjustment, and
plots the applied result in `docs/lut_verification.png`. It uses an 8-bit
synthetic chart. Generated inputs and cube files remain outside Git.

## Boundary and limitations

This public repository contains the focused experiment. The publication scope includes
the two demonstration screenshots after SDR conversion, approved on 15SEP2026.
Only `docs/lut_before_rec709.png` and `docs/lut_after_rec709.png` are the film-frame
presentation exception. Keep source-film files, film-cell scans, Resolve archives,
original image pairs, generated LUTs, and environments out of Git. The private source archive remains separate. No new licence is granted
by this documentation change.

The primary script silently writes an identity cube when the input pair is
missing or ambiguous. It infers scale from maximum pixel value and assumes
three-channel input. Its 16-bit colour handling is not established by the
8-bit demo. It does not perform geometric registration, colour-space conversion,
sparse-grid interpolation, or calibrated film-colour reconstruction.

## Current state and next work

The README leads with the film-cell LUT before/after pair.
`examples/convert_hdr_pair.py` applies the same explicit Rec.2020/PQ 1,000-nit
to 100-nit Rec.709 conversion to both inputs. It uses NumPy, Pillow, and FFmpeg
with fixed Mobius settings; its command and verification are in
`docs/film_cell_example_15SEP2026.md`. The input display tags are deliberately
overridden only through the explicit source-assumption flag. Do not infer the
original HDR encoding from a screenshot profile. The synthetic chart remains
the independent check of the primary LUT generator. The former illustrative
pipeline diagram was removed. Before broader use, add explicit
input paths and validation, verify bit-depth handling, and review the earlier
`test.py` variant's output order. Do not present that predecessor as equivalent
to the checked primary path. Use lowercase_snake_case for new first-party files.
State Mac Mini M4 in commits made on this machine.

## Documentation and Git identity

Use first person for personal decisions and experience in README prose. Use
direct technical language for software behaviour and instructions. Do not
describe the maintainer as "the owner". Preserve quoted source wording and
technical ownership terms.

Local commits must use `swithmario` and
`28229111+swithmario@users.noreply.github.com`. Verify both author and committer
before pushing. Histories were corrected on 15SEP2026; compare an older checkout
with the corrected remote before merging or pushing it. Record Mac Mini M4 in
commits made on this machine.
