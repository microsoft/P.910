"""
/*---------------------------------------------------------------------------------------------
*  Copyright (c) Microsoft Corporation. All rights reserved.
*  Licensed under the MIT License. See License.txt in the project root for license information.
*--------------------------------------------------------------------------------------------*/
@author: Babak Naderi
"""

import argparse
from os.path import isfile, join, basename
import configparser as CP
import csv
import cv2
from PIL import Image, ImageFont, ImageDraw
from moviepy.editor import *

video_extension = '.mp4'
trapping_videos = []
tmp_files = []


def get_video_resolution(video):
    # find out the resolution of sample video
    vid = cv2.VideoCapture(video)
    height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
    width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
    vid.release()
    return (width, height)


def create_image(width, height, clip_id, des_folder):
    # find a proper font size
    expected_text_width = width * 0.8
    percentage = 0
    font_size = 15

    msg = f'Clip {clip_id}'
    while percentage < 0.95 or percentage > 1.05:
        if percentage < 0.95:
            font_size += 5
        else:
            font_size -= 1
        font = ImageFont.truetype("arial.ttf", font_size)
        text_width = font.getsize(msg)[0]
        percentage = text_width / expected_text_width

    # create the image
    img = Image.new('RGB', (width, height), color=(127, 127, 127))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("arial.ttf", font_size)

    text_width = font.getsize(msg)[0]
    text_height = font.getsize(msg)[1]
    d.text(xy=((width - text_width) / 2, height / 2), text=msg, font=font, fill=(255, 255, 255))

    image_path = join(des_folder, f'tmp_{width}_{height}_{clip_id}.png')
    img.save(image_path)
    tmp_files.append(image_path)
    return image_path


def create_video(width, height, clip_id, des_folder):
    img_path = create_image(width, height, clip_id, des_folder)
    frame = cv2.imread(img_path)
    height, width, layers = frame.shape
    video_path =join(des_folder, f'tmp_{width}_{height}_{clip_id}.png')
    video = cv2.VideoWriter(video_path, cv2.VideoWriter_fourcc(*'mp4v'), 1, (width, height))
    # video will
    for sec in range(5):
        video.write(cv2.imread(img_path))
    video.release()
    return video_path


def create_split_screen(width, height, des_a, des_b):
    # Clip A
    return



def create_split_screens(source_folder, des):
    """
    Walk through the source folder and create split screens for each resolution
    :param source_folder:
    :param des:
    :return:
    """
    if not os.path.exists(des):
        os.makedirs(des)

    # find list of files
    source_files = [join(source_folder, f) for f in os.listdir(source_folder) if
                    isfile(join(source_folder, f)) and video_extension in f]
    if len(source_files) == 0:
        return 0
    count = 0
    list_of_file = []
    data = []
    for s_f in source_files:
        (w, h) = get_video_resolution(s_f)
        file_name_A = join(des, f'split_{w},{h}_a.mp4')
        file_name_B = join(des, f'split_{w},{h}_b.mp4')

        if file_name_A not in list_of_file:
            create_split_screen(w, h, file_name_A, file_name_B)
            list_of_file.append(file_name_A)
            list_of_file.append(file_name_B)
            source_file_name = os.path.splitext(basename(s_f))[0]
            data.append({'video_clip': source_file_name,
                         'screen A': f'split_{w},{h}_a.mp4', 'screen B': f'split_{w},{h}_b.mp4' })

    output_report = join(des, 'output_report.csv')
    with open(output_report, 'w', newline='') as output_file:
        headers_written = False
        for f in data:
            if not headers_written:
                writer = csv.DictWriter(output_file, fieldnames=sorted(f))
                headers_written = True
                writer.writeheader()
            writer.writerow(f)


def create_trap_stimulus(source, message, output, cfg):
    """
    Create a trapping clips stimulus
    :param source: path to source stimuli from dataset
    :param message: path to the message clip
    :param output: path to output file
    :param cfg: configuration
    :return:
    """
    # find the source duration
    source_video = VideoFileClip(source)
    msg_video = VideoFileClip(message)
    src_duration = source_video.duration

    post_fix_duration_sec = 1
    source_duration = source_video.duration
    # check how to set the duration
    if ('keep_original_duration' in cfg) and \
            (cfg['keep_original_duration'].upper() == 'TRUE'):
        msg_duration = msg_video.duration
        # if it negative, just use the default 3 seconds
        prefix_duration = source_duration - msg_duration -post_fix_duration_sec
        if prefix_duration <= 0:
            prefix_duration = 3
        prefix_video = source_video.subclip(0, prefix_duration)
    else:
        prefix_video = source_video.subclip(0, min(int(cfg["include_from_source_stimuli_in_second"]), src_duration))

    postfix_clip = source_video.subclip(source_duration-post_fix_duration_sec, source_duration)
    final_clip = concatenate_videoclips([prefix_video, msg_video, postfix_clip])
    final_clip.write_videofile(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create split screen for DCR test.')

    parser.add_argument("--source", help="source directory containing all video clips", required=True)
    parser.add_argument("--des", help="destination directory where the screens to be stored", required=True)

    args = parser.parse_args()

    assert os.path.exists(args.source), f"Invalid source directory {args.source}]"

    print('Start scanning the source clip directory')
    n_created_screens = create_split_screens(args.source, args.des)
    print(f'{n_created_screens} files created.')
