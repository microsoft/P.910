"""
/*---------------------------------------------------------------------------------------------
*  Copyright (c) Microsoft Corporation. All rights reserved.
*  Licensed under the MIT License. See License.txt in the project root for license information.
*--------------------------------------------------------------------------------------------*/
@author: Babak Naderi
"""
import argparse
import subprocess
import os
import uuid
import time

import cv2
import numpy as np
import pandas as pd
from tempfile import mkstemp

FREEZE_PROBABILITY = 0.5
FREEZE_DURATION = 5
GOOD_QUALITY_CRF = 17
DEFAULT_GOP = 30


class TempFileList:
    def __init__(self):
        self._filelist = []

    def mktemp(self, *, prefix='', suffix=''):
        fd, fn = mkstemp(prefix=prefix, suffix=suffix)
        os.close(fd)
        self._filelist.append(fn)
        return fn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for f in self._filelist:
            try:
                os.unlink(f)
            except (FileNotFoundError, IOError):
                pass
        self._filelist = []


def _probe_fps(path):
    """Return video FPS using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        "-of", "csv=p=0",
        str(path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    num, den = result.stdout.strip().split('/')
    return int(num) / int(den)


def _probe_duration(path):
    """Return video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        str(path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def _get_bitrate_kbps(path):
    """Return video bitrate in kbps (file_size * 8 / duration / 1000)."""
    size_bytes = os.path.getsize(path)
    duration = _probe_duration(path)
    return round(size_bytes * 8 / duration / 1000, 1)


def _inflate_to_target_bitrate(src, dst, target_size_bytes, *, gop=DEFAULT_GOP):
    """
    Re-encode *src* so the output file size closely matches *target_size_bytes*.
    Uses target-bitrate mode with subtle noise to ensure the encoder reaches
    the desired size even when content has high temporal redundancy.
    """
    duration = _probe_duration(src)
    target_bitrate = int(target_size_bytes * 8 / duration)

    ffmpeg_cmd = [
        "ffmpeg", "-i", str(src), "-y",
        "-threads", "1",
        "-preset", "veryfast",
        "-vf", "noise=alls=5:allf=t",
        "-keyint_min", "2",
        "-g", str(gop),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-b:v", str(target_bitrate),
        "-maxrate", str(int(target_bitrate * 1.2)),
        "-bufsize", str(int(target_bitrate * 2)),
        "-an",
        str(dst)
    ]
    subprocess.run(ffmpeg_cmd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def generate_freeze_mask(n_frames, probability, freeze_duration, rng):
    """
    Generate a per-frame freeze mask (0 = keep, 1 = freeze/repeat last frame).
    Frame 0 is never frozen. Each freeze event freezes exactly *freeze_duration*
    consecutive frames. Total frozen fraction is capped at *probability*.
    """
    mask = [0] * n_frames
    remaining_freeze = 0
    for i in range(1, n_frames):
        current_frozen = sum(mask[:i])
        current_fraction = current_frozen / i

        if remaining_freeze > 0:
            mask[i] = 1
            remaining_freeze -= 1
        elif current_fraction < probability and rng.random() < probability:
            duration = min(freeze_duration, n_frames - i)
            mask[i] = 1
            remaining_freeze = duration - 1
        else:
            mask[i] = 0
    return mask


def apply_frame_freeze(input_mp4, output_mp4, seed=None):
    """
    Apply frame freeze to a video. Frozen frames repeat the last unfrozen frame.
    Output frame count equals input frame count.
    Returns freeze statistics dict.
    """
    rng = np.random.default_rng(seed)

    fps = _probe_fps(input_mp4)
    cap = cv2.VideoCapture(input_mp4)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {input_mp4}")

    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if n_frames <= 0:
        raise RuntimeError(f"Cannot determine frame count: {input_mp4}")

    mask = generate_freeze_mask(n_frames, FREEZE_PROBABILITY, FREEZE_DURATION, rng)

    out = None
    last_good_frame = None
    frames_written = 0

    for i in range(n_frames):
        ret, frame = cap.read()
        if not ret:
            break

        if mask[i] == 1 and last_good_frame is not None:
            write_frame = last_good_frame
        else:
            write_frame = frame
            last_good_frame = frame.copy()

        if out is None:
            h, w = write_frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'FFV1')
            out = cv2.VideoWriter(output_mp4, fourcc, fps, (w, h))

        out.write(write_frame)
        frames_written += 1

    cap.release()
    if out is not None:
        out.release()

    n_frozen = sum(mask[:frames_written])
    return {
        'n_frames': frames_written,
        'n_frozen_frames': n_frozen,
        'freeze_percent': round(n_frozen / frames_written * 100, 1) if frames_written > 0 else 0,
    }


def process_single_video(input_mp4, out_directory, seed=None):
    """Process one video: apply frame freeze and match source bitrate."""
    src_size = os.path.getsize(input_mp4)
    src_name = os.path.basename(input_mp4)
    out_basename = f"{os.path.splitext(src_name)[0]}_freeze_{uuid.uuid4().hex[:8]}.mp4"

    with TempFileList() as temp_files:
        # Step 1: apply frame freeze to lossless intermediate
        intermediate = temp_files.mktemp(prefix="freeze_", suffix=".mkv")
        stats = apply_frame_freeze(input_mp4, intermediate, seed=seed)

        # Step 2: re-encode to match source file size
        out_path = os.path.join(out_directory, out_basename)
        _inflate_to_target_bitrate(intermediate, out_path, src_size)

    return {
        'src': src_name,
        'output': out_basename,
        'src_size_bytes': src_size,
        'output_size_bytes': os.path.getsize(os.path.join(out_directory, out_basename)),
        'src_bitrate_kbps': _get_bitrate_kbps(input_mp4),
        'output_bitrate_kbps': _get_bitrate_kbps(os.path.join(out_directory, out_basename)),
        **stats,
    }


def collect_input_files(input_path):
    """Collect video files from a directory or CSV file."""
    if os.path.isdir(input_path):
        files = []
        for f in sorted(os.listdir(input_path)):
            if f.lower().endswith('.mp4'):
                files.append(os.path.join(input_path, f))
        return files
    elif input_path.lower().endswith('.csv'):
        df = pd.read_csv(input_path)
        col = 'src' if 'src' in df.columns else 'gold_src'
        return [row[col] for _, row in df.iterrows()]
    else:
        raise ValueError(f"Input must be a directory or CSV file: {input_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Apply frame freeze (discontinuity) to video clips with bitrate matching.')
    parser.add_argument('--input', required=True,
                        help='Input directory with .mp4 files, or a CSV file with src or gold_src column')
    parser.add_argument('--output_dir', required=True,
                        help='Output directory for frozen videos')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for reproducibility')
    args = parser.parse_args()

    input_files = collect_input_files(args.input)
    if not input_files:
        print("No input files found.")
        return

    os.makedirs(args.output_dir, exist_ok=True)

    results = []
    start_time = time.time()

    for i, input_mp4 in enumerate(input_files):
        if not os.path.exists(input_mp4):
            print(f"File {input_mp4} does not exist. Skipping...")
            continue

        clip_seed = args.seed + i if args.seed is not None else None
        print(f"[{i+1}/{len(input_files)}] Processing {os.path.basename(input_mp4)}...")
        try:
            result = process_single_video(input_mp4, args.output_dir, seed=clip_seed)
            results.append(result)
            print(f"  -> {result['output']} | freeze: {result['freeze_percent']}% "
                  f"| src: {result['src_bitrate_kbps']} kbps | out: {result['output_bitrate_kbps']} kbps")
        except Exception as e:
            print(f"  Error: {e}")

    if results:
        report_path = os.path.join(args.output_dir, 'frame_freeze_report.csv')
        pd.DataFrame(results).to_csv(report_path, index=False)
        elapsed = time.time() - start_time
        minutes, seconds = divmod(int(elapsed), 60)
        print(f"\nDone! {len(results)} clips processed in {minutes}m {seconds}s.")
        print(f"Report saved to: {report_path}")


if __name__ == '__main__':
    main()
