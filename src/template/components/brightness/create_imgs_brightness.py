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
    if level not in range(1, max_level+1):
        return None
    gray_code = background[0]+max_level-level+1
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


def create_matrix_image():
    backgrounds = [15, 72, 128, 185, 240]
    #levels = [2, 3, 4]
    levels = [4]
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
            level = random.choice(levels)
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
    for i in range(100):
        create_matrix_image()


if __name__ == '__main__':
    method1_numbers()
    #method2_shapes()







