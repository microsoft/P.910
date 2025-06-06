"""
/*---------------------------------------------------------------------------------------------
*  Copyright (c) Microsoft Corporation. All rights reserved.
*  Licensed under the MIT License. See License.txt in the project root for license information.
*--------------------------------------------------------------------------------------------*/
@author: Babak Naderi
"""

from PIL import Image, ImageFilter
import os.path
from os import path


def blur_img(source, output, r):
    """Blur ``source`` image with radius ``r`` and save it to ``output``."""
    source_img = Image.open(source)
    out_img = source_img.filter(ImageFilter.BoxBlur(r))
    out_img.save(output)


if __name__ == '__main__':
    source_image = "source/img8.jpg"
    out_dir = "out"
    radius_range = range(10)
    if not path.exists(out_dir):
        os.mkdir(out_dir)

    file_name = os.path.basename(source_image)
    tmp = file_name.split('.')
    source_name = tmp[0]
    for i in radius_range:
        blur_img(source_image, f'{out_dir}/{source_name}_{i}.jpg', i)
