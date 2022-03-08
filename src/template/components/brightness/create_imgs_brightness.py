"""
/*---------------------------------------------------------------------------------------------
*  Copyright (c) Microsoft Corporation. All rights reserved.
*  Licensed under the MIT License. See License.txt in the project root for license information.
*--------------------------------------------------------------------------------------------*/
@author: Babak Naderi
"""

from PIL import Image, ImageFont, ImageDraw
import random
import os.path
from os import path
import base64
import pandas as pd

def generate_rand_num(n):
    """
    Create n 3-digits random numbers
    :param n:
    :return:
    """
    nums = []
    for i in range(n):
        r = random.randint(100, 999)
        nums.append(r)
    return nums


def level_to_rgb(level, background):
    """
    Converts internal consept of level to a gray color for text in RGB
    :param level: range from 1 to 15
    :return: tuple referring to (R, G, B)
    """
    #Level goes from 1 to 15, starting from level1:(30,30,30), and getting darker with 1 point
    if level not in range(1, 16):
        return None
    gray_code = background[0]+15-level+1
    print(f"{level}::{gray_code}")
    return (gray_code, gray_code, gray_code)


def create_image(path, level, text, background):
    """
    Create an image and store it in the given path.
    :param path:
    :param level:
    :param text:
    :return:
    """
    W, H = (500, 500)
    # create an empty image 500x500 px
    img = Image.new("RGB", (W, H), background)
    image_editable = ImageDraw.Draw(img)
    # use another font or download this one
    try:
        font = ImageFont.truetype(font_name, 150)
        w, h = image_editable.textsize(text, font=font)
        image_editable.text(((W-w)/2, (H-h)/2), text, level_to_rgb(level, background), font=font)
        img.save(f"{path}/{background[0]}_{level}_{text}.jpg", "JPEG")
    except Exception as e:
        print("Please download 'Roboto-Thin' font in this directory, or change the font name in the source code")
        print(e)


def create_image_shapes():
    background = (15, 15, 15)
    W, H = (500, 500)
    # create an empty image 500x500 px
    img = Image.new("RGB", (W, H), background)
    image_editable = ImageDraw.Draw(img)

    img2 =Image.new("RGB", (W, H), (100, 100, 100))
    image_editable.paste(img2, (50, 100))
    background.save('out.png')


def create_image_range(bg):
    background = (bg, bg, bg)
    levels = range(min_level, max_level+1)
    path_dir = f"pics_{bg}"
    if not path.exists(path_dir):
        os.mkdir(path_dir)
    for l in levels:
        for n in rand_nums:
            create_image(path_dir, l, f"{n}", background)


def get_color(background, level):
    c = (background[0]+level, background[1]+level, background[2]+level)
    return c


NO_SHAPE = 0
CIRCLE = 1
TRIANGLE = 2


def create_block(background, level, shape):
    canvas = Image.new('RGB', (100, 100), background)
    img_draw = ImageDraw.Draw(canvas)
    front_color = get_color(background, level)
    if shape == CIRCLE:
        d = random.randint(40, 60)
        start = random.randint(0, 40)
        img_draw.ellipse((start, start, start+d, start+d), fill=front_color, outline=front_color)
    elif shape == TRIANGLE:
        d = random.randint(0, 30)
        img_draw.polygon(((50, d), (100-d, 100-d), (d, 100-d)), fill=front_color, outline=front_color)
    canvas.save('tmp.png')


def create_matrix_image(level):
    backgrounds = [15, 72, 128, 185, 240]
    #levels = [2, 3, 4]
    # levels = [4]
    shapes = [NO_SHAPE, CIRCLE, TRIANGLE]
    count_circle = 0
    count_triangle = 0
    canvas = Image.new('RGB', (400, 400), (0, 0, 0))
    for i in range(4):
        bgs = backgrounds.copy()
        random.shuffle(bgs)
        x = 0
        for bg in bgs:
            if (x==4): continue
            shape = random.choice(shapes)
            # level = random.choice(levels)
            if (shape == CIRCLE):
                count_circle += 1
            elif (shape == TRIANGLE ):
                count_triangle += 1
            create_block((bg, bg, bg), level, shape)
            tmp_block = Image.open('tmp.png')
            canvas.paste(tmp_block, (x * 100, i * 100))
            x += 1
    name = f"c:{count_circle}_t:{count_triangle}"
    name_coded = base64.b64encode(name.encode('ascii')).decode('ascii')
    canvas.save(f'{name_coded}.jpg')
    print(f" c:{count_circle}, t:{count_triangle}")
    return {'c':{count_circle}, 't':{count_triangle}, 'name': {f'{name_coded}.jpg'}}


def method1_numbers():
    """
    create images with numbers
    :return:
    """
    global rand_nums, max_level, min_level, font_name
    font_name = "Roboto-Thin.ttf"
    max_level = 14
    # should be 1, to save space just started from 10
    min_level = 12

    # 3 different numbers, for real application something like 20 would be good
    rand_nums = generate_rand_num(3)
    bgs = [15, 72, 128, 185, 240]
    for bg in bgs:
        create_image_range(bg)
    print(rand_nums)


def method2_shapes():
    """
    create matrix of images with shapes
    :return:
    """
    list = []
    difference_to_bg = 5
    for i in range(10):
        info = create_matrix_image(difference_to_bg)
        list.append(info)
    df = pd.DataFrame(list)
    df.to_csv(f'matrix_files-details_{difference_to_bg}.csv')


def print_matrix_name():
    data =['Yzo0X3Q6MTA=','Yzo0X3Q6Mw==','Yzo0X3Q6Ng==','Yzo0X3Q6Nw==','Yzo0X3Q6OA==','Yzo1X3Q6Mg==','Yzo1X3Q6Mw==','Yzo1X3Q6NA==','Yzo1X3Q6Ng==','Yzo1X3Q6NQ==','Yzo1X3Q6Nw==','Yzo1X3Q6OA==','Yzo1X3Q6OQ==','Yzo2X3Q6Mg==','Yzo2X3Q6Mw==','Yzo2X3Q6NA==','Yzo2X3Q6Ng==','Yzo2X3Q6NQ==','Yzo2X3Q6Nw==','Yzo2X3Q6OA==','Yzo3X3Q6Mg==','Yzo3X3Q6Mw==','Yzo3X3Q6NA==','Yzo3X3Q6Ng==','Yzo3X3Q6NQ==','Yzo3X3Q6Nw==','Yzo3X3Q6OA==','Yzo4X3Q6Mg==','Yzo4X3Q6Mw==','Yzo4X3Q6NA==','Yzo4X3Q6Ng==','Yzo4X3Q6NQ==','Yzo4X3Q6Nw==','Yzo5X3Q6Mg==','Yzo5X3Q6MQ==','Yzo5X3Q6Mw==','Yzo5X3Q6NQ==','YzoxMF90OjM=','YzoxMV90OjM=','YzoxX3Q6MTI=','YzoxX3Q6Ng==','YzoxX3Q6NQ==','YzoxX3Q6Nw==','YzoyX3Q6MTA=','YzoyX3Q6Ng==','YzozX3Q6MTA=','YzozX3Q6NQ==','YzozX3Q6Nw==','YzozX3Q6OA==','YzozX3Q6OQ==']
    df = pd.DataFrame(columns=['name', 'c', 't'])
    for c in range (0,17):
        for t in range(0, 17):
            name = f"c:{c}_t:{t}"
            name_coded = base64.b64encode(name.encode('ascii')).decode('ascii')
            if name_coded in data:
                df = df.append({'name': f'{name_coded}.jpg', 'c':c, 't':t}, ignore_index=True)

    df.to_csv('name_to_nums.csv')

if __name__ == '__main__':
    #method1_numbers()
    random.seed(10)
    method2_shapes()
    #print_matrix_name()







