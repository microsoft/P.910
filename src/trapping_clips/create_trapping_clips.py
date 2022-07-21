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


def create_msg_video(cfg, des, org):
    """
    Create a message video (duration 5 sec) to be added to the given original image
    :param cfg:
    :param des:
    :param org:
    :return:
    """
    # find out the resolution of sample video
    vid = cv2.VideoCapture(org)
    height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
    width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))

    vid.release()
    list_videos = []
    for score in range(int(cfg['scale_min']), int(cfg['scale_max'])+1):
        video_name = join(des, f'video_{width}_{height}_{score}.mp4')
        # check if a trapping video is already created
        if video_name in trapping_videos:
            list_videos.append((score, video_name))
            continue
        image_file_name = join(des, f'tmp_{width}_{height}_{score}.png')
        create_msg_img(cfg, score, des, width, height)

        frame = cv2.imread(image_file_name)
        height, width, layers = frame.shape

        video = cv2.VideoWriter(video_name, cv2.VideoWriter_fourcc(*'mp4v'), 1, (width, height))
        # video will
        for sec in range(5):
            video.write(cv2.imread(image_file_name))
        video.release()
        tmp_files.append(video_name)
        trapping_videos.append(video_name)
        list_videos.append((score, video_name))
    return list_videos


def create_msg_img(cfg, score, des, v_width, v_height):
    """
    Create an image with the specified attention message from config file and the given size
    :param cfg:
    :param score:
    :param des:
    :param v_width:
    :param v_height:
    :return:
    """
    title = "Attention:"
    # find a proper font size
    expected_text_width = v_width*0.8
    percentage = 0
    font_size = 15
    text = ''
    if len(cfg['message_line1']) > len(cfg['message_line2']):
        text = cfg['message_line1']
    else:
        text = cfg['message_line2']
    while percentage < 0.95 or percentage > 1.05:
        if percentage < 0.95:
            font_size += 5
        else:
            font_size -= 1
        font = ImageFont.truetype("arial.ttf", font_size)
        text_width = font.getsize(text)[0]
        percentage = text_width / expected_text_width

    # create the image
    img = Image.new('RGB', (v_width, v_height), color=(127, 127, 127))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("arial.ttf", font_size)

    text = title
    text_width = font.getsize(text)[0]
    text_height = font.getsize(text)[1]
    d.text(xy=((v_width-text_width)/2, v_height/2-3*text_height), text=text, font=font, fill=(255, 255, 255))

    text = cfg['message_line1'].format(score)
    text_width = font.getsize(text)[0]
    d.text(xy=((v_width - text_width) / 2, v_height / 2 - text_height), text=text, font=font, fill=(255, 255, 255))

    text = cfg['message_line2'].format(score)
    text_width = font.getsize(text)[0]
    d.text(xy=((v_width - text_width) / 2, v_height / 2 + text_height/2), text=text, font=font, fill=(255, 255, 255))
    image_path = join(des, f'tmp_{v_width}_{v_height}_{score}.png')
    img.save(image_path)
    tmp_files.append(image_path)
    return image_path


def create_trap_db(cfg, source_folder, des):
    """
    Creates the trapping clips dataset
    :param cfg: configuration file
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
    for s_f in source_files:
        msg_videos = create_msg_video(cfg, des, s_f)
        for (score, msg_f) in msg_videos:
            # create output filename format [source_filename]_tp_[suffix from
            output_f_name = f'{os.path.splitext(basename(s_f))[0]}_{score}.mp4'
            output_path = join(des,
                               output_f_name)
            create_trap_stimulus(s_f,
                                 msg_f,
                                 output_path, cfg)
            count += 1
            list_of_file.append({'trapping_pvs': output_f_name, 'trapping_ans': score})
    output_report = join(des, 'output_report.csv')
    with open(output_report, 'w', newline='') as output_file:
        headers_written = False
        for f in list_of_file:
            if not headers_written:
                writer = csv.DictWriter(output_file, fieldnames=sorted(f))
                headers_written = True
                writer.writeheader()
            writer.writerow(f)

    return count


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
        if prefix_duration <= 3:
            prefix_duration = 3
        prefix_video = source_video.subclip(0, prefix_duration)
    else:
        prefix_video = source_video.subclip(0, min(int(cfg["include_from_source_stimuli_in_second"]), src_duration))

    postfix_clip = source_video.subclip(source_duration-post_fix_duration_sec, source_duration)
    final_clip = concatenate_videoclips([prefix_video, msg_video, postfix_clip])
    final_clip.write_videofile(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create trapping clips dataset.')

    parser.add_argument("--source", help="source directory containing all videos", required=True)
    parser.add_argument("--des", help="destination directory where the clips will be stored", required=True)
    # Configuration: read it from trapping.cfg
    parser.add_argument("--cfg",
                        help="Check trapping.cfg for all the details", required=True)
    args = parser.parse_args()

    cfgpath = args.cfg
    assert os.path.exists(cfgpath), f"No configuration file in {cfgpath}]"
    assert os.path.exists(args.source), f"Invalid source directory {args.source}]"

    cfg = CP.ConfigParser()
    cfg._interpolation = CP.ExtendedInterpolation()
    cfg.read(cfgpath)

    tp_cfg = cfg._sections['trappings']

    print('Start creating files')
    n_created_files = create_trap_db(tp_cfg, args.source, args.des)
    print(f'{n_created_files} files created.')

    # remove tmp files
    for f in tmp_files:
        os.remove(f)
