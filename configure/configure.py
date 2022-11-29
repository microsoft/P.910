"""
/*---------------------------------------------------------------------------------------------
*  Copyright (c) Microsoft Corporation. All rights reserved.
*  Licensed under the MIT License. See License.txt in the project root for license information.
*--------------------------------------------------------------------------------------------*/
@author: Aditya Khant
"""

import argparse
import yaml
from utils.convert_file import convert_file
from utils.download_file import download_file

def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-c','--config', type=str, default='configs/online.yaml')
    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    common_config = config['common']
    converts = config.get('convert', {})
    converts = {} if converts is None else converts
    downloads = config.get('download', {})
    downloads = {} if downloads is None else downloads
    for k, v in converts.items():
        convert_file({k: v}, common_config)
    for k, v in downloads.items():
        download_file({k: v}, common_config)
    print("Done!")
        
if __name__ == "__main__":
    main()