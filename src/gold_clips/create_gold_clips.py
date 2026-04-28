"""
/*---------------------------------------------------------------------------------------------
*  Copyright (c) Microsoft Corporation. All rights reserved.
*  Licensed under the MIT License. See License.txt in the project root for license information.
*--------------------------------------------------------------------------------------------*/
@author: Babak Naderi
"""
import argparse
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from tempfile import TemporaryFile, mkstemp

import pandas as pd
import os
import uuid
import shutil
import random
import time

ffmpeg_template = 'ffmpeg -i "{}" -y -c:v libx264 -g {} -pix_fmt yuv420p -crf {} "{}"'
# define three types of gold clips equal, better, worse , they should be accessable in all functions
gold_clips = ['equal', 'better', 'worse']
default_gop = 30
larger_size_crf = 13
good_quality_crf = 17
crf_for_bad_quality = 47
crf_for_equal_quality = [17, 20, 27]


def create_gld_ccr(type, input_mp4, out_dir, prefix=''):
    gold_pvs = f"{uuid.uuid4()}.mp4"
    gold_src = f"{uuid.uuid4()}.mp4"
    while os.path.exists(os.path.join(out_dir, gold_pvs)):
        gold_pvs = f"{uuid.uuid4()}.mp4"
    while os.path.exists(os.path.join(out_dir, gold_src)):
        gold_src = f"{uuid.uuid4()}.mp4"

    pvs_path = os.path.join(out_dir, gold_pvs)
    src_path = os.path.join(out_dir, gold_src)

    with TempFileList() as temp_files:
        if type == 'equal':
            gold_answer = 0
            crf = random.choice(crf_for_equal_quality)
            run_ffmeg_encoder(input_mp4, src_path, crf=crf, gop=default_gop)
            shutil.copy(src_path, pvs_path)
        elif type == 'better':
            # pvs should be better than src
            gold_answer = 3
            run_ffmeg_encoder(input_mp4, pvs_path, crf=good_quality_crf, gop=default_gop)
            bad_raw = temp_files.mktemp(prefix="bad_raw_", suffix=".mp4")
            run_ffmeg_encoder(input_mp4, bad_raw, crf=crf_for_bad_quality, gop=default_gop)
            _inflate_to_target_bitrate(bad_raw, src_path,
                                       os.path.getsize(pvs_path))
        else:
            # pvs should be worse than src
            gold_answer = -3
            run_ffmeg_encoder(input_mp4, src_path, crf=good_quality_crf, gop=default_gop)
            bad_raw = temp_files.mktemp(prefix="bad_raw_", suffix=".mp4")
            run_ffmeg_encoder(input_mp4, bad_raw, crf=crf_for_bad_quality, gop=default_gop)
            _inflate_to_target_bitrate(bad_raw, pvs_path,
                                       os.path.getsize(src_path))

    pvs_bitrate = _get_bitrate_kbps(pvs_path)
    src_bitrate = _get_bitrate_kbps(src_path)
    return gold_pvs, gold_src, gold_answer, pvs_bitrate, src_bitrate


def run_ffmeg_encoder(src, dst, *, crf, gop, fast=False):
    ffmpeg_cmd = [
        "ffmpeg",
        "-i", str(src),
        "-y",
        "-threads", "1",
        "-preset", "veryfast" if (fast or crf > 17) else "veryslow",
        "-keyint_min", "2",
        "-g", str(gop),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", str(crf),
        str(dst)
    ]
    subprocess.run(ffmpeg_cmd, check=True)


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


def _inflate_to_target_bitrate(src, dst, target_size_bytes, *, gop=default_gop):
    """
    Re-encode *src* so the output file size closely matches *target_size_bytes*.

    Combines a subtle noise injection (invisible but increases encoder complexity)
    with target-bitrate mode to guarantee the output reaches the desired size.
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
        filelist = self._filelist
        if len(filelist) > 0:
            self._filelist = []

            for f in filelist:
                try:
                    os.unlink(f)
                except FileNotFoundError:
                    pass
                except IOError as e:
                    print(f"error removing temporary file {f}: {e}")


def create_gld_acr(input_mp4, out_dir):
    with TempFileList() as temp_files:
        good_raw_fn = temp_files.mktemp(prefix="good_raw_", suffix=".mp4")
        run_ffmeg_encoder(input_mp4, good_raw_fn, crf=good_quality_crf, gop=default_gop)
        good_size = os.path.getsize(good_raw_fn)

        bad_raw_fn = temp_files.mktemp(prefix="bad_raw_", suffix=".mp4")
        run_ffmeg_encoder(input_mp4, bad_raw_fn, crf=crf_for_bad_quality, gop=default_gop)

        # Re-encode bad clip to match good clip's file size
        bad_fn_large_size = temp_files.mktemp(prefix="bad_", suffix=".mp4")
        _inflate_to_target_bitrate(bad_raw_fn, bad_fn_large_size, good_size)
        
        bad_basename = f"{uuid.uuid4()}.mp4"
        bad_fn = os.path.join(out_dir, bad_basename)
        shutil.move(bad_fn_large_size, bad_fn)        

        good_basename = f"{uuid.uuid4()}.mp4"
        good_fn = os.path.join(out_dir, good_basename)
        shutil.move(good_raw_fn, good_fn)        

        return good_basename, bad_basename, _get_bitrate_kbps(good_fn), _get_bitrate_kbps(bad_fn)


def _process_single_clip_ccr(input_mp4, out_directory):
    """Worker: process one clip for CCR method. Returns list of result dicts."""
    src_name = os.path.basename(input_mp4)
    results = []
    for gtype in gold_clips:
        gold_pvs, gold_src, gold_answer, pvs_bitrate, src_bitrate = create_gld_ccr(gtype, input_mp4, out_directory)
        if gold_pvs is None:
            print(f"Failed to create gold clip for {input_mp4} of type {gtype}. Skipping...")
            continue
        results.append({
            'gold_src': src_name,
            'gold_clips_pvs': gold_pvs,
            'gold_clips_src': gold_src,
            'gold_clips_ans': gold_answer,
            'gold_type': gtype,
            'pvs_bitrate_kbps': pvs_bitrate,
            'src_bitrate_kbps': src_bitrate
        })
    return results


def _process_single_clip_acr(input_mp4, out_directory):
    """Worker: process one clip for ACR method. Returns list of result dicts."""
    src_name = os.path.basename(input_mp4)
    good_pvs, bad_pvs, good_bitrate, bad_bitrate = create_gld_acr(input_mp4, out_directory)
    return [
        {'gold_src': src_name, 'gold_clips_pvs': good_pvs, 'gold_clips_ans': 5, 'gold_pvs_bitrate_kbps': good_bitrate},
        {'gold_src': src_name, 'gold_clips_pvs': bad_pvs, 'gold_clips_ans': 1, 'gold_pvs_bitrate_kbps': bad_bitrate},
    ]


def process_gold_clips(input_csv, test_method, out_directory, num_workers=1):
    start_time = time.time()
    df = pd.read_csv(input_csv)
    results = []
    # create directory if it does not exist    
    os.makedirs(out_directory, exist_ok=True)

    # Collect valid input files
    input_files = []
    for _, row in df.iterrows():
        input_mp4 = row['gold_src']
        if not os.path.exists(input_mp4):
            print(f"File {input_mp4} does not exist. Skipping...")
            continue
        input_files.append(input_mp4)

    if not input_files:
        print("No valid input files found.")
        return

    # Select worker function and build argument tuples
    if test_method == "ccr":
        worker_fn = _process_single_clip_ccr
        worker_args = [(f, out_directory) for f in input_files]
    elif test_method == "acr":
        worker_fn = _process_single_clip_acr
        worker_args = [(f, out_directory) for f in input_files]
    else:
        raise ValueError(f"Unknown test method: {test_method}")

    output_csv = os.path.join(out_directory, f"{test_method}_gold_clips.csv")
    actual_csv = output_csv
    available_cores = os.cpu_count() or 1
    effective_workers = max(1, min(num_workers, len(input_files), available_cores))

    def _safe_write_csv(df, path):
        """Write CSV, falling back to a new file if the target is locked."""
        nonlocal actual_csv
        try:
            df.to_csv(path, index=False)
            actual_csv = path
        except (PermissionError, OSError):
            base, ext = os.path.splitext(path)
            fallback = f"{base}_{int(time.time())}{ext}"
            df.to_csv(fallback, index=False)
            actual_csv = fallback

    if effective_workers <= 1:
        # Sequential processing
        for args in worker_args:
            clip_results = worker_fn(*args)
            results.extend(clip_results)
            # save intermediate results
            _safe_write_csv(pd.DataFrame(results), output_csv)
    else:
        # Parallel processing
        with ProcessPoolExecutor(max_workers=effective_workers) as executor:
            futures = {
                executor.submit(worker_fn, *args): args[0]
                for args in worker_args
            }
            for future in as_completed(futures):
                input_file = futures[future]
                try:
                    clip_results = future.result()
                    results.extend(clip_results)
                    _safe_write_csv(pd.DataFrame(results), output_csv)
                    print(f"Processed {input_file}: {len(clip_results)} clip(s)")
                except Exception as e:
                    print(f"Error processing {input_file}: {e}")

    result_df = pd.DataFrame(results)
    _safe_write_csv(result_df, output_csv)
    elapsed = time.time() - start_time
    minutes, seconds = divmod(int(elapsed), 60)
    print(f"Done! {len(result_df)} clips created in {minutes}m {seconds}s. Check {actual_csv}")

    if actual_csv != output_csv:
        print(f"WARNING: Could not write to {output_csv} (file may be open). "
              f"Results saved to {actual_csv} instead.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process gold clips for test method.')
    parser.add_argument('--input_csv', required=True, help='Input CSV file with column gold_src. Clips must be in high quality with no distortions.')
    parser.add_argument('--test_method', required=True,
                        help='Test method: acr or ccr')
    parser.add_argument('--output_dir', required=True, help='Output directory to create files there')
    parser.add_argument('--num_workers', type=int, default=1,
                        help='Number of parallel workers (default: 1)')

    args = parser.parse_args()

    supported = ('acr', 'ccr')
    if args.test_method.lower() not in supported:
        raise ValueError(f'Supported methods: {supported}')

    process_gold_clips(args.input_csv, args.test_method.lower(), args.output_dir,
                       num_workers=args.num_workers)
