"""
/*---------------------------------------------------------------------------------------------
*  Copyright (c) Microsoft Corporation. All rights reserved.
*  Licensed under the MIT License. See License.txt in the project root for license information.
*--------------------------------------------------------------------------------------------*/
@author: Aditya Khant
"""
from pathlib import Path
import requests
import os

def download_file(file_dict, common_config):
    """
    Downloads a file and writes it to the specified places.
    :param file_dict: (Dict) The configuration for the download.
    :return write_to: (List) The list of paths the downloaded file is written to.
    """
    base_path = Path(common_config['base_path'])
    name, config = list(file_dict.items())[0]
    print(f"Downloading {name}...")
    location = config["location"]
    # download file
    r = requests.get(location, stream=True)
    content = r.content
    for path in config["write_to"]:
        write_to = base_path / Path(path)
        os.makedirs(write_to.parent, exist_ok=True)
        with open(write_to, 'wb') as f:
            f.write(content)
    return write_to
    