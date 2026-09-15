"""Convert an explicitly interpreted Rec.2020/PQ PNG pair to Rec.709 SDR.

Requires NumPy, Pillow, and FFmpeg with the CPU tonemap filter. The source
interpretation is explicit because screenshots can carry display-space tags.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, PngImagePlugin


def pq_to_nits(code):
    """ST 2084 EOTF. PQ code 1 means 10,000 nits, regardless of mastering peak."""
    m1, m2 = 2610 / 16384, 2523 / 32
    c1, c2, c3 = 3424 / 4096, 2413 / 128, 2392 / 128
    p = np.power(np.clip(code, 0, 1), 1 / m2)
    return 10000 * np.power(np.maximum(p - c1, 0) / (c2 - c3 * p), 1 / m1)


def rgb_to_xyz(primaries):
    xy = np.asarray(primaries, dtype=np.float64)
    columns = np.vstack((xy[:, 0] / xy[:, 1], np.ones(3),
                         (1 - xy.sum(axis=1)) / xy[:, 1]))
    white = np.array([0.3127 / 0.3290, 1, (1 - 0.3127 - 0.3290) / 0.3290])
    return columns * np.linalg.solve(columns, white)


REC2020_TO_REC709 = np.linalg.solve(
    rgb_to_xyz([(0.640, 0.330), (0.300, 0.600), (0.150, 0.060)]),
    rgb_to_xyz([(0.708, 0.292), (0.170, 0.797), (0.131, 0.046)]),
)


def tone_map(rgb, peak_ratio, ffmpeg):
    """Pass linear RGB to FFmpeg as planar G, B, R float32, without YUV."""
    height, width, _ = rgb.shape
    planar = np.stack([rgb[..., 1], rgb[..., 2], rgb[..., 0]]).astype('<f4')
    command = [ffmpeg, '-v', 'error', '-f', 'rawvideo', '-pixel_format',
               'gbrpf32le', '-video_size', f'{width}x{height}', '-framerate', '1',
               '-color_primaries', 'bt2020', '-color_trc', 'linear',
               '-i', 'pipe:0', '-frames:v', '1', '-vf',
               f'tonemap=mobius:param=0.3:desat=0:peak={peak_ratio:.12g}',
               '-f', 'rawvideo', '-pix_fmt', 'gbrpf32le', 'pipe:1']
    result = subprocess.run(command, input=planar.tobytes(), capture_output=True,
                            check=True)
    if len(result.stdout) != planar.nbytes:
        raise ValueError('FFmpeg returned an unexpected frame size')
    mapped = np.frombuffer(result.stdout, dtype='<f4').reshape(3, height, width)
    return np.stack([mapped[2], mapped[0], mapped[1]], axis=-1).astype(np.float64)


def rec709_code(linear):
    linear = np.clip(linear, 0, 1)
    return np.where(linear < 0.018, 4.5 * linear,
                    1.099 * np.power(linear, 0.45) - 0.099)


def convert(source, destination, source_peak, target_peak, ffmpeg, icc):
    header = source.read_bytes()[:26]
    if header[:8] != b'\x89PNG\r\n\x1a\n' or header[24] != 8:
        raise ValueError('This example requires an 8-bit PNG input')
    with Image.open(source) as im:
        if im.format != 'PNG' or im.mode not in ('RGB', 'RGBA'):
            raise ValueError('This example requires an 8-bit RGB/RGBA PNG')
        if im.mode == 'RGBA' and np.any(np.asarray(im.getchannel('A')) != 255):
            raise ValueError('Flatten non-opaque input explicitly before conversion')
        code = np.asarray(im.convert('RGB'), dtype=np.float64) / 255
    nits = pq_to_nits(code)
    mapped = tone_map(np.minimum(nits, source_peak) / target_peak,
                      source_peak / target_peak, ffmpeg)
    linear709 = np.einsum('...c,dc->...d', mapped, REC2020_TO_REC709, optimize=False)
    if not np.isfinite(linear709).all():
        raise ValueError('Non-finite conversion result')
    out = np.rint(255 * rec709_code(linear709)).astype(np.uint8)
    metadata = PngImagePlugin.PngInfo()
    # H.273: BT.709 primaries, BT.709 transfer, RGB matrix, full range.
    metadata.add(b'cICP', bytes([1, 1, 0, 1]))
    Image.fromarray(out).save(destination, pnginfo=metadata, icc_profile=icc)
    with Image.open(destination) as saved:
        assert saved.mode == 'RGB' and saved.size == (out.shape[1], out.shape[0])
        assert np.array_equal(np.asarray(saved), out)
        assert saved.info['icc_profile'] == icc
    return {
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'output': destination.name,
        'output_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
        'width': out.shape[1], 'height': out.shape[0],
        'source_max_channel_nits': float(nits.max()),
        'source_channels_above_assumed_peak': int((nits > source_peak).sum()),
        'output_gamut_clipped_channels': int(((linear709 < 0) | (linear709 > 1)).sum()),
        'output_min_max_code': [int(out.min()), int(out.max())],
    }


def verify_transform(source_peak, target_peak, ffmpeg):
    # Independent reference values for PQ display luminance.
    assert abs(float(pq_to_nits(0.5080784215)) - 100) < 0.001
    assert abs(float(pq_to_nits(0.7518270962)) - 1000) < 0.001
    assert np.allclose(REC2020_TO_REC709 @ np.ones(3), 1, atol=1e-12)
    ramp = np.repeat(np.linspace(0, source_peak / target_peak, 1001)[None, :, None], 3, axis=2)
    mapped = tone_map(ramp, source_peak / target_peak, ffmpeg)
    linear709 = np.einsum('...c,dc->...d', mapped, REC2020_TO_REC709, optimize=False)
    codes = np.rint(255 * rec709_code(linear709)).astype(np.uint8)
    assert np.all(codes[0, 0] == 0) and np.all(codes[0, -1] == 255)
    assert np.all(np.diff(codes.astype(int), axis=1) >= 0)
    assert np.array_equal(codes[..., 0], codes[..., 1])
    assert np.array_equal(codes[..., 1], codes[..., 2])
    low = np.array([[[0.1, 0.2, 0.05]]])
    assert np.allclose(tone_map(low, source_peak / target_peak, ffmpeg), low, atol=1e-7)
    return {'pq_reference_values': 'passed', 'neutral_ramp': 'monotonic',
            'black_code': 0, 'source_peak_white_code': 255,
            'rgb_plane_order': 'passed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--output-icc', type=Path, required=True,
                        help='A standard BT.709 transfer/primaries RGB ICC profile')
    parser.add_argument('--assume-rec2020-pq', action='store_true', required=True,
                        help='Explicitly override source display-profile tags')
    parser.add_argument('--source-peak-nits', type=float, default=1000)
    parser.add_argument('--target-peak-nits', type=float, default=100)
    parser.add_argument('--ffmpeg', default='ffmpeg')
    args = parser.parse_args()
    if not 0 < args.target_peak_nits < args.source_peak_nits <= 10000:
        parser.error('Require 0 < target peak < source peak <= 10,000 nits')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    destinations = [args.output_dir / f'lut_{role}_rec709.png' for role in ('before', 'after')]
    if any(p.exists() for p in destinations):
        parser.error('Output images already exist; choose a new output directory')
    icc = args.output_icc.read_bytes()
    checks = verify_transform(args.source_peak_nits, args.target_peak_nits, args.ffmpeg)
    records = [convert(src, dst, args.source_peak_nits, args.target_peak_nits,
                       args.ffmpeg, icc)
               for src, dst in zip([args.before, args.after], destinations)]
    report = {'source_interpretation': 'Rec.2020 / ST 2084 PQ / full range',
              'source_profile_override': True, 'source_peak_nits': args.source_peak_nits,
              'target': 'Rec.709 SDR / BT.709 transfer / full-range 8-bit RGB',
              'target_peak_nits': args.target_peak_nits,
              'tone_map': 'FFmpeg mobius, param=0.3, desat=0, fixed shared peak',
              'gamut_mapping': 'linear D65 matrix then clip to Rec.709 gamut',
              'checks': checks, 'images': records}
    (args.output_dir / 'conversion_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
