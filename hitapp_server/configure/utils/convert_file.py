"""
/*---------------------------------------------------------------------------------------------
*  Copyright (c) Microsoft Corporation. All rights reserved.
*  Licensed under the MIT License. See License.txt in the project root for license information.
*--------------------------------------------------------------------------------------------*/
@author: Aditya Khant
"""

from pathlib import Path
import os

SUBSTITUTION_DECORATOR_PRE = "<<"
SUBSTITUTION_DECORATOR_POST = ">>"

def decorate_substition(value):
    """
    Decorate a value with the substitution decorator.
    :param value: (String) The value to decorate.
    :return: (String) The decorated value.
    """
    return SUBSTITUTION_DECORATOR_PRE + str(value) + SUBSTITUTION_DECORATOR_POST

def convert_file(file_dict, common_config):
    """
    Convert a file in config. 
    :param file_dict: (Dict) The configuration for the conversion.
    :return write_to: (Path) The path the converted file is written to.
    """
    name, config = list(file_dict.items())[0]
    print(f"Converting {name}...")
    base_path = Path(common_config['base_path'])
    location = base_path / Path(config["location"])
    with open(location, 'r') as f:
        data = f.read()
        for old, new in config.get('substitutions', {}).items():
            data = data.replace(decorate_substition(old), new)
    is_template = config.get('is_template', False)
    write_to = config.get("write_to", None)
    if write_to is not None:
        write_to = base_path / Path(write_to)
    elif is_template:
        write_to = location.with_suffix('')
    else:
        write_to = location
    os.makedirs(write_to.parent, exist_ok=True)
    with open(write_to, 'w') as f:
        f.write(data)
    return write_to
    
    
    