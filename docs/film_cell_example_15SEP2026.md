# Film-cell LUT example

## Image identity

The owner supplied the two screenshots from the original LUT workflow on
15SEP2026. Both show the same 4K Blu-ray frame. The colour reference used to
create the LUT was an IMAX film cell of that frame. The bluer supplied image is
the result after the LUT. The other supplied image is the before view.

The displayed pair preserves the supplied crops and dimensions: before is
1274 by 712 pixels; after is 1272 by 716 pixels. No image registration,
resizing, independent exposure adjustment, or image generation was applied.
The conversion below prepares the existing result for display. The separate
synthetic chart checks the current `gen_lut.py` implementation.

## Display transform

The owner selected this input interpretation:

| Parameter | Value |
| --- | --- |
| Input primaries | Rec.2020, D65 |
| Input transfer | ST 2084 PQ |
| Source peak | 1,000 cd/m² |
| Input sample range | Full-range 8-bit RGB |
| SDR reference peak | 100 cd/m² |
| Tone mapping | FFmpeg Mobius, transition 0.3, desaturation disabled |
| Gamut conversion | Linear D65 Rec.2020 to Rec.709 matrix, then gamut clipping |
| Output transfer | BT.709 |
| Output range | Full-range 8-bit RGB; black 0, reference peak white 255 |
| Output metadata | BT.709 ICC profile and matching PNG cICP `[1, 1, 0, 1]` |

The source files carry Display P3 screenshot tags. The explicit
`--assume-rec2020-pq` option implements the owner's chosen interpretation of
their sample values. Source metadata is retained in the private originals;
it is not copied into the converted PNGs.

PQ code 1 represents 10,000 cd/m². A 1,000-nit PQ reference is approximately
0.751827. The converter decodes PQ before applying the shared tone curve.
It does not treat byte value 255 as 1,000 nits or stretch each image separately.

## Reproduce the conversion

Install NumPy, Pillow, and an FFmpeg build with the CPU `tonemap` filter.
Supply a standard RGB ICC profile with BT.709 primaries and transfer.
On macOS, the system includes `ITU-709.icc`.

```sh
python examples/convert_hdr_pair.py \
  --before /path/to/before.png \
  --after /path/to/after.png \
  --output-dir /path/outside/git/rec709_pair \
  --output-icc '/System/Library/ColorSync/Profiles/ITU-709.icc' \
  --assume-rec2020-pq \
  --source-peak-nits 1000 \
  --target-peak-nits 100
```

The command writes both PNGs and a conversion receipt with source/output
hashes. Original screenshots and bulk media remain outside Git. The example
accepts opaque 8-bit PNGs. This source override is intentional; use an actual
source profile for other images.

## Verification

The 15SEP2026 run used FFmpeg 8.1.2, NumPy 2.2.6, and Pillow 12.3.0.
Checks passed for known PQ luminance values, RGB plane order, a monotonic
neutral ramp, black 0, and 1,000-nit source white mapped to output 255.
The saved PNGs decoded to the exact computed 8-bit arrays and carried the
expected Rec.709 metadata. Both outputs were inspected visually.

No input channel exceeded the selected 1,000-nit peak. Gamut clipping affected
11 of 2,721,264 channel values before the LUT and 5,094 of 2,732,256 after it.
No non-finite output was found. The final conversion also passed with Python
runtime warnings treated as errors.

This transform uses NumPy for PQ and primary conversion and FFmpeg for the
linear-light tone curve. The local FFmpeg build does not include `zscale`.
The implementation does not use YUV conversion or chroma subsampling.

## References

- [ITU-R BT.2100](https://www.itu.int/rec/R-REC-BT.2100): HDR primaries and transfer functions.
- [ITU-R BT.709](https://www.itu.int/rec/R-REC-BT.709): HDTV primaries and signal encoding.
- [FFmpeg tonemap](https://ffmpeg.org/ffmpeg-filters.html#tonemap): linear-light Mobius operator and peak setting.
- [PNG specification](https://www.w3.org/TR/png-3/#11cICP): colour metadata.

The movie imagery remains the property of its respective rights holders.
Its inclusion illustrates this colour-processing experiment and grants no
rights to the underlying film.
