"""
/*---------------------------------------------------------------------------------------------
*  Copyright (c) Microsoft Corporation. All rights reserved.
*  Licensed under the MIT License. See License.txt in the project root for license information.
*--------------------------------------------------------------------------------------------*/
@author: Babak Naderi
"""

import argparse
from os.path import isfile, join, basename, dirname
import os
import configparser as CP
import pandas as pd
import math
import random
import numpy as np
import re
import collections
from random import shuffle
import itertools

file_to_condition_map = {}


def validate_inputs(df, method):
    """
    Validate the structure, and fields in row_input.csv and configuration file
    :param df: current input given
    :param method: test method
    """
    columns = list(df.columns)

    # check mandatory columns
    required_columns_acr = ['pvs', 'block_matrix_url', 'circles', 'triangles', 'trapping_ans', 'trapping_pvs',
                            'gold_clips_pvs', 'gold_clips_ans', 'cv_plate', 'cv_url']
    # tps are always the references.
    required_columns_dcr = ['pvs', 'src', 'block_matrix_url', 'circles', 'triangles', 'trapping_ans', 'trapping_pvs',
                            'trapping_src', 'gold_clips_pvs', 'gold_clips_src', 'gold_clips_ans', 'cv_plate', 'cv_url']

    required_columns_acrhr = ['pvs', 'src', 'block_matrix_url', 'circles', 'triangles', 'trapping_ans', 'trapping_pvs',
                              'gold_clips_pvs', 'gold_clips_ans']
    if method in ['acr', 'avatar']:
        req = required_columns_acr
    elif method in ['dcr', 'ccr']:
        req = required_columns_dcr
    elif method in ['acr-hr']:
        req = required_columns_acrhr

    for column in req:
        assert column in columns, f"No column found with '{column}' in input file"


def conv_filename_to_condition(f_name, condition_pattern):
    """
    extract the condition name from filename given the mask in the config
    :param f_name:
    :return:
    """
    if f_name in file_to_condition_map:
        return file_to_condition_map[f_name]
    file_to_condition_map[f_name] = {'Unknown': 'NoCondition'}
    m = re.match(condition_pattern, f_name)
    if m:
        file_to_condition_map[f_name] = m.groupdict('')
        file_to_condition_map[f_name] = collections.OrderedDict(sorted(file_to_condition_map[f_name].items()))
    return file_to_condition_map[f_name]


def add_clips_balanced_block(clips, condition_pattern, keys, n_clips_per_session, output_df):
    """
    Balanced block design. TODO: check the code for video
    :param clips:
    :param condition_pattern:
    :param keys:
    :param n_clips_per_session:
    :param output_df:
    :return:
    """
    block_keys = [x.strip() for x in keys.split(',')]
    if len(block_keys) > 2:
        raise SystemExit("Error: balanced_block design- only up to 2 keys in 'block_keys' are supported")
    data = pd.DataFrame(columns=block_keys.copy().insert(0,' url'))

    for clip in clips:
        condition = conv_filename_to_condition(clip, condition_pattern)
        tmp = condition.copy()
        tmp['url'] = clip
        data = data.append(tmp, ignore_index=True)
    if 'Unknown' in data:
        unknown_count = data['Unknown'].dropna().count()
        raise SystemExit(f"Error: balanced_block design- {unknown_count} clips did not match the 'condition_pattern'.")

    # check if block design is possible
    df_agg = data.groupby(block_keys).agg(count_url=('url', 'count'))

    #      are all combinations exists
    num_unique = {}
    for key in block_keys:
        num_unique[key] = len(data[key].unique())
    combination = np.prod(list(num_unique.values()))

    if len(df_agg) != combination:
        raise SystemExit("Error: balanced_block design- Not all combination between block_keys exist.")
    #      check if in each block similar number of clips appears
    files_per_block = df_agg.count_url.unique()
    if len(files_per_block) > 1:
        raise SystemExit("Error: balanced_block design- unequal number of clips per block")

    # check number of files and how to combine elements
    #      number of clips in the session should be a multiples of values of first block_key
    n_clips_in_block = num_unique[block_keys[0]]
    if n_clips_per_session % n_clips_in_block != 0:
        raise SystemExit("Error: balanced_block design- number_of_clips_per_session should be a multiples of values of "
                         f"first block_key. Found {num_unique[block_keys[0]]} unique values for '{block_keys[0]}'. "
                         f"Therefore number_of_clips_per_session should be a multiples of {num_unique[block_keys[0]]})")
    # create the blocks
    n_clips = clips.count()
    #  create block sets
    column_names = [f"url_{i}" for i in range(0, num_unique[block_keys[0]])]
    blocked_df = pd.DataFrame(columns=column_names)
    filtered_data_list = []

    if len(block_keys) > 1:
        # only 2 blocks were allowed
        key1_unique_values = list(data[block_keys[1]].unique())
        for val in key1_unique_values:
            filtered_data_list.append(data[data[block_keys[1]]==val].copy().reset_index(drop=True))
    else:
        filtered_data_list.append(data)

    key0_unique_values = list(data[block_keys[0]].unique())
    for d in filtered_data_list:
        i = 0
        u = {}
        for val in key0_unique_values:
            tmp = d[d[block_keys[0]] == val].url.tolist()
            random.shuffle(tmp)
            u[f"url_{i}"] = tmp
            i += 1
        tmp_df = pd.DataFrame.from_dict(u)
        blocked_df = blocked_df.append(tmp_df, ignore_index=True)

    # shuffel
    blocked_df = blocked_df.sample(frac=1)
    # add extra blocks to have complete sessions
    blocks_per_session = n_clips_per_session / n_clips_in_block
    if len(blocked_df) % blocks_per_session != 0:
        n_extra_blocks = int(blocks_per_session - (len(blocked_df) % blocks_per_session))
        extra_blocks = blocked_df.sample(n=n_extra_blocks)
        blocked_df = blocked_df.append(extra_blocks, ignore_index=True)

    # create the sessions
    np_blocks = blocked_df[column_names].to_numpy()
    np_blocks_reshaped = np.reshape(np_blocks, (-1, n_clips_per_session), order='c')
    q_order = random.sample(range(n_clips_per_session),n_clips_per_session)
    i = 0
    for q in range(n_clips_per_session):
        output_df[f'Q{q}'] = np_blocks_reshaped[:, q_order[i]]
        i += 1
    return output_df


def add_clips_balanced_block_ccr(clips, refs, condition_pattern, keys, n_clips_per_session, output_df):
    # create the structure only using clips
    add_clips_balanced_block(clips, condition_pattern, keys, n_clips_per_session, output_df)
    clips = clips.tolist()
    refs = refs.tolist()
    for q in range(n_clips_per_session):
        clip_list = output_df[f'Q{q}'].tolist()
        ref_list = []
        for c in clip_list:
            ref_list.append(refs[clips.index(c)])
        output_df[f'Q{q}_R'] = ref_list
        output_df.rename(columns={f'Q{q}': f'Q{q}_P'}, inplace=True)


def add_clips_random(clips, n_clips_per_session, output_df):
    """
    Select random set of videos for each session.
    :param clips:
    :param n_clips_per_session:
    :param output_df:
    :return:
    """
    n_clips = clips.count()
    n_sessions = math.ceil(n_clips / n_clips_per_session)
    needed_clips = n_sessions * n_clips_per_session

    all_clips = np.tile(clips.to_numpy(), (needed_clips // n_clips) + 1)[:needed_clips]
    #   check the method: clips_selection_strategy
    random.shuffle(all_clips)

    clips_sessions = np.reshape(all_clips, (n_sessions, n_clips_per_session))

    for q in range(n_clips_per_session):
        output_df[f'Q{q}'] = clips_sessions[:, q]


# checked
def add_clips_random_dcr(clips, refs, n_clips_per_session, output_df):
    """
    Select random set of videos for each session for DCR test.
    :param clips:
    :param refs:
    :param n_clips_per_session:
    :param output_df:
    :return:
    """
    n_clips = clips.count()
    n_sessions = math.ceil(n_clips / n_clips_per_session)
    needed_clips = n_sessions * n_clips_per_session

    full_clips = np.tile(clips.to_numpy(), (needed_clips // n_clips) + 1)[:needed_clips]
    full_refs = np.tile(refs.to_numpy(), (needed_clips // n_clips) + 1)[:needed_clips]

    full = list(zip(full_clips, full_refs))
    random.shuffle(full)
    full_clips, full_refs = zip(*full)

    clips_sessions = np.reshape(full_clips, (n_sessions, n_clips_per_session))
    refs_sessions = np.reshape(full_refs, (n_sessions, n_clips_per_session))

    for q in range(n_clips_per_session):
        output_df[f'Q{q}_P'] = clips_sessions[:, q]
        output_df[f'Q{q}_R'] = refs_sessions[:, q]


# checked
def add_clips_random_acrhr(clips, refs, n_clips_per_session, output_df):
    """
    Select random set of videos for each session for ACR_HR test.
    :param clips:
    :param refs:
    :param n_clips_per_session:
    :param output_df:
    :return:
    """
    n_clips = clips.count()
    n_sessions = math.ceil(n_clips / n_clips_per_session)
    needed_clips = n_sessions * n_clips_per_session

    full_clips = np.tile(clips.to_numpy(), (needed_clips // n_clips) + 1)[:needed_clips]
    full_refs = np.tile(refs.to_numpy(), (needed_clips // n_clips) + 1)[:needed_clips]

    full = list(zip(full_clips, full_refs))
    random.shuffle(full)
    full_clips, full_refs = zip(*full)

    clips_sessions = np.reshape(full_clips, (n_sessions, n_clips_per_session))
    refs_sessions = np.reshape(full_refs, (n_sessions, n_clips_per_session))

    for q in range(n_clips_per_session):
        output_df[f'Q{q}'] = clips_sessions[:, q]
        output_df[f'Q{q}_R'] = refs_sessions[:, q]


def get_random_plate(df, plate,n_sessions):
    df_cv = df[['cv_plate', 'cv_url']].copy()
    # filter for cv_plate = plate_3
    df_cv_plate = df_cv[df_cv['cv_plate'] == plate].copy()
    # randomly select n_sessions , it could be n_sessions > number of rows in df_cv_plate3
    if n_sessions > df_cv_plate.shape[0]:
        df_cv_plate = df_cv_plate.sample(n=n_sessions, replace=True)
    else:
        df_cv_plate = df_cv_plate.sample(n=n_sessions, replace=False)

    return df_cv_plate['cv_url'].tolist()

def get_random_block_matrix(df, type, n_sessions): 
    
    cols = ['circles','triangles','block_matrix_url']
    if 'type' in df.columns:        
        cols.append('type')
        # only keep cols 
        df_cv = df[cols].copy()
        df_cv = df_cv[df_cv['type'] == type].dropna()
        # drop type column
        df_cv = df_cv.drop(columns=['type'])
    else:
        df_cv = df[cols].copy().dropna()        
    
    if n_sessions > df_cv.shape[0]:
        df_cv = df_cv.sample(n=n_sessions, replace=True)
    else:
        df_cv = df_cv.sample(n=n_sessions, replace=False)
    # drop empty rows
    df_cv = df_cv.dropna().reset_index(drop=True)
    
    return df_cv

def create_input_for_acr(cfg, df, output_path):
    """
    create the input for the acr methods
    :param cfg:
    :param df:
    :param output_path:
    :return:
    """
    clips = df['pvs'].dropna()
    n_clips = clips.count()
    n_clips_per_session = int(cfg['number_of_clips_per_session'])
    output_df = pd.DataFrame()
    packing_strategy = cfg.get("clip_packing_strategy", "random").strip().lower()

    if packing_strategy == "balanced_block":
        add_clips_balanced_block(clips, cfg["condition_pattern"], cfg.get("block_keys", cfg["condition_keys"]),
                                 n_clips_per_session, output_df)
    elif packing_strategy == "random":
        add_clips_random(clips, n_clips_per_session, output_df)

    n_sessions = math.ceil(n_clips / int(cfg['number_of_clips_per_session']))
    print(f'{n_clips} clips and {n_sessions} sessions')

    # block_matrix
    
    q1_blocks_df = get_random_block_matrix(df, 'q1', n_sessions)
    # rename columns block_matrix_url: t1_matrix_url, circles: t1_matrix_c, triangles: t1_matrix_t
    q1_blocks_df = q1_blocks_df.rename(columns={'block_matrix_url': 't1_matrix_url', 'circles': 't1_matrix_c', 'triangles': 't1_matrix_t'})        
    
    q2_blocks_df = get_random_block_matrix(df, 'q2', n_sessions)    
    # rename columns block_matrix_url: t2_matrix_url, circles: t2_matrix_c, triangles: t2_matrix_t
    q2_blocks_df = q2_blocks_df.rename(columns={'block_matrix_url': 't2_matrix_url', 'circles': 't2_matrix_c', 'triangles': 't2_matrix_t'})
    output_df = pd.concat([output_df, q1_blocks_df, q2_blocks_df], axis=1)
   
    
    # to obfuscate the correct answer
    output_df['t1_matrix_c'] = output_df['t1_matrix_c'] + 2
    output_df['t1_matrix_t'] = output_df['t1_matrix_t'] + 3


    # randomly select color vision plates
    output_df['cv_plate_3_url'] = get_random_plate(df, 'plate_3', n_sessions)
    output_df['cv_plate_4_url'] = get_random_plate(df, 'plate_4', n_sessions)

    # trappings
    if int(cfg['number_of_trapping_per_session']) > 0:
        if int(cfg['number_of_trapping_per_session']) > 1:
            print("more than one TP is not supported for now - continue with 1")
        # n_trappings = int(cfg['general']['number_of_trapping_per_session']) * n_sessions
        #n_trappings = n_sessions
        tmp = df[['trapping_pvs', 'trapping_ans']].copy()
        tmp.dropna(inplace=True)            
        if n_sessions > tmp.shape[0]:
            tmp = tmp.sample(frac=1).reset_index(drop=True)
            delta = n_sessions - tmp.shape[0]
            tmp = pd.concat([tmp, tmp.sample(n=delta, replace=True)])
        else:
            tmp = tmp.sample(n=n_sessions, replace=False)      
        output_df['TP_CLIP'] = tmp['trapping_pvs'].tolist()
        output_df['TP_ANS'] = tmp['trapping_ans'].tolist()

    # gold_clips
    if int(cfg['number_of_gold_clips_per_session']) > 0:
        if int(cfg['number_of_gold_clips_per_session']) > 1:
            print("more than one gold_clip is not supported for now - continue with 1")
        
        tmp = df[['gold_clips_pvs', 'gold_clips_ans']].copy()
        tmp.dropna(inplace=True)            
        if n_sessions > tmp.shape[0]:
            tmp = tmp.sample(frac=1).reset_index(drop=True)
            delta = n_sessions - tmp.shape[0]
            tmp = pd.concat([tmp, tmp.sample(n=delta, replace=True)])
        else:
            tmp = tmp.sample(n=n_sessions, replace=False)

        output_df['GOLD_CLIP'] = tmp['gold_clips_pvs'].tolist()
        output_df['GOLD_ANS'] = tmp['gold_clips_ans'].tolist()
    output_df.to_csv(output_path, index=False)
    return len(output_df)


def create_input_for_acrhr(cfg, df, output_path):
    """
    create the input for the acrhr methods
    :param cfg:
    :param df:
    :param output_path:
    :return:
    """
    clips = df['pvs'].dropna()
    refs = df['src'].dropna()
    n_clips = clips.count()
    if n_clips != refs.count():
        raise SystemExit('size of "pvs" and "src" are not equal.')

    unique_refs = refs.drop_duplicates()
    tmp_clips = pd.concat([clips, unique_refs], ignore_index=True, axis=0)
    tmp_clips = tmp_clips.rename('pvs')
    tmp_refs = pd.concat([refs, unique_refs], ignore_index=True, axis=0)
    full = pd.concat([tmp_clips, tmp_refs], axis=1, join='inner')
    clips = full['pvs']
    refs = full['src']

    n_clips = clips.count()

    n_clips_per_session = int(cfg['number_of_clips_per_session'])
    output_df = pd.DataFrame()
    packing_strategy = cfg.get("clip_packing_strategy", "random").strip().lower()

    #  the packing is similar to the dcr/ccr.
    if packing_strategy == "balanced_block":
        # to be checked
        add_clips_balanced_block_ccr(clips, refs, cfg["condition_pattern"], cfg.get("block_keys", cfg["condition_keys"])
                                     , n_clips_per_session, output_df)
    elif packing_strategy == "random":
        add_clips_random_acrhr(clips, refs, n_clips_per_session, output_df)

    n_sessions = math.ceil(n_clips / n_clips_per_session)
    print(f'{n_clips} clips and {n_sessions} sessions')

    # block_matrix
    nPairs = 2 * n_sessions
    urls = df['block_matrix_url'].dropna()
    circles = df['circles'].dropna()
    triangles = df['triangles'].dropna()

    urls_extended = np.tile(urls.to_numpy(), (nPairs // urls.count()) + 1)[:nPairs]
    circles_extended = np.tile(circles.to_numpy(), (nPairs // circles.count()) + 1)[:nPairs]
    triangles_extended = np.tile(triangles.to_numpy(), (nPairs // triangles.count()) + 1)[:nPairs]

    full_array = np.transpose(np.array([urls_extended, circles_extended, triangles_extended]))
    new_2 = np.reshape(full_array, (n_sessions, 6))
    np.random.shuffle(new_2)
    output_df = output_df.assign(
        **{'t1_matrix_url': new_2[:, 0], 't1_matrix_c': new_2[:, 1], 't1_matrix_t': new_2[:, 2],
           't2_matrix_url': new_2[:, 3], 't2_matrix_c': new_2[:, 4], 't2_matrix_t': new_2[:, 5]})
    # to obfuscate the correct answer
    output_df['t1_matrix_c'] = output_df['t1_matrix_c'] + 2
    output_df['t1_matrix_t'] = output_df['t1_matrix_t'] + 3

    # trappings
    if int(cfg['number_of_trapping_per_session']) > 0:
        if int(cfg['number_of_trapping_per_session']) > 1:
            print("more than one TP is not supported for now - continue with 1")
        # n_trappings = int(cfg['general']['number_of_trapping_per_session']) * n_sessions
        n_trappings = n_sessions
        tmp = df[['trapping_pvs', 'trapping_ans']].copy()
        tmp.dropna(inplace=True)
        tmp = tmp.sample(n=n_trappings, replace=True)
        trap_source = tmp['trapping_pvs'].dropna()
        trap_ans_source = tmp['trapping_ans'].dropna()

        full_trappings = np.tile(trap_source.to_numpy(), (n_trappings // trap_source.count()) + 1)[:n_trappings]
        full_trappings_answer = np.tile(trap_ans_source.to_numpy(), (n_trappings // trap_ans_source.count()) + 1)[
                                :n_trappings]

        full_tp = list(zip(full_trappings, full_trappings_answer))
        random.shuffle(full_tp)

        full_trappings, full_trappings_answer = zip(*full_tp)
        output_df['TP_CLIP'] = full_trappings
        output_df['TP_ANS'] = full_trappings_answer

    # gold_clips
    if int(cfg['number_of_gold_clips_per_session']) > 0:
        if int(cfg['number_of_gold_clips_per_session']) > 1:
            print("more than one gold_clip is not supported for now - continue with 1")
        n_gold_clips = n_sessions
        gold_clip_source = df['gold_clips_pvs'].dropna()
        gold_clip_ans_source = df['gold_clips_ans'].dropna()

        full_gold_clips = np.tile(gold_clip_source.to_numpy(),
                                  (n_gold_clips // gold_clip_source.count()) + 1)[:n_gold_clips]
        full_gold_clips_answer = np.tile(gold_clip_ans_source.to_numpy(), (n_gold_clips // gold_clip_ans_source.count())
                                         + 1)[:n_gold_clips]
        full_gc = list(zip(full_gold_clips, full_gold_clips_answer))
        random.shuffle(full_gc)

        full_gold_clips, full_gold_clips_answer = zip(*full_gc)
        output_df['GOLD_CLIP'] = full_gold_clips
        output_df['GOLD_ANS'] = full_gold_clips_answer

    output_df.to_csv(output_path, index=False)
    return len(output_df)


# checked
def create_input_for_dcr(cfg, df, output_path):
    """
    create the input for the dcr method
    :param cfg:
    :param df:
    :param output_path:
    :return:
    """
    clips = df['pvs'].dropna()
    refs = df['src'].dropna()

    n_clips = clips.count()
    if n_clips != refs.count():
        raise SystemExit('size of "pvs" and "src" are not equal.')
    n_clips_per_session = int(cfg['number_of_clips_per_session'])

    output_df = pd.DataFrame()
    packing_strategy = cfg.get("clip_packing_strategy", "random").strip().lower()

    if packing_strategy == "balanced_block":
        # to be checked
        add_clips_balanced_block_ccr(clips, refs, cfg["condition_pattern"], cfg.get("block_keys", cfg["condition_keys"])
                                     , n_clips_per_session, output_df)
    elif packing_strategy == "random":
        add_clips_random_dcr(clips, refs, n_clips_per_session, output_df)

    n_sessions = math.ceil(n_clips / n_clips_per_session)
    print(f'{n_clips} clips and {n_sessions} sessions')

    # block_matrix
    q1_blocks_df = get_random_block_matrix(df, 'q1', n_sessions)
    # rename columns block_matrix_url: t1_matrix_url, circles: t1_matrix_c, triangles: t1_matrix_t
    q1_blocks_df = q1_blocks_df.rename(columns={'block_matrix_url': 't1_matrix_url', 'circles': 't1_matrix_c', 'triangles': 't1_matrix_t'})        
    
    q2_blocks_df = get_random_block_matrix(df, 'q2', n_sessions)    
    # rename columns block_matrix_url: t2_matrix_url, circles: t2_matrix_c, triangles: t2_matrix_t
    q2_blocks_df = q2_blocks_df.rename(columns={'block_matrix_url': 't2_matrix_url', 'circles': 't2_matrix_c', 'triangles': 't2_matrix_t'})
    output_df = pd.concat([output_df, q1_blocks_df, q2_blocks_df], axis=1)
   
    
    # to obfuscate the correct answer
    output_df['t1_matrix_c'] = output_df['t1_matrix_c'] + 2
    output_df['t1_matrix_t'] = output_df['t1_matrix_t'] + 3


    # randomly select color vision plates
    output_df['cv_plate_3_url'] = get_random_plate(df, 'plate_3', n_sessions)
    output_df['cv_plate_4_url'] = get_random_plate(df, 'plate_4', n_sessions)

    # trappings
    if int(cfg['number_of_trapping_per_session']) > 0:
        if int(cfg['number_of_trapping_per_session']) > 1:
            print("more than one TP is not supported for now - continue with 1")
        # n_trappings = int(cfg['general']['number_of_trapping_per_session']) * n_sessions
        #n_trappings = n_sessions

        tmp = df[['trapping_pvs', 'trapping_src', 'trapping_ans']].copy()
        tmp.dropna(inplace=True)        
        if n_sessions > tmp.shape[0]:
            tmp = tmp.sample(frac=1).reset_index(drop=True)
            delta = n_sessions - tmp.shape[0]
            tmp = pd.concat([tmp, tmp.sample(n=delta, replace=True)])
        else:
            tmp = tmp.sample(n=n_sessions, replace=False)            
        
        output_df['TP_CLIP'] = tmp['trapping_pvs'].tolist()
        output_df['TP_REF'] = tmp['trapping_src'].tolist()
        output_df['TP_ANS'] = tmp['trapping_ans'].tolist()


    # gold clips
    if int(cfg['number_of_gold_clips_per_session']) > 0:
        if int(cfg['number_of_gold_clips_per_session']) > 1:
            print("more than one Gold Question is not supported for now - continue with 1")

        tmp = df[['gold_clips_pvs', 'gold_clips_src', 'gold_clips_ans']].copy()
        tmp.dropna(inplace=True)        
        if n_sessions > tmp.shape[0]:            
            tmp = tmp.sample(frac=1).reset_index(drop=True)            
            delta = n_sessions - tmp.shape[0]            
            tmp = pd.concat([tmp, tmp.sample(n=delta, replace=True)])            
        else:
            tmp = tmp.sample(n=n_sessions, replace=False)  

        output_df['GOLD_REF'] = tmp['gold_clips_src'].tolist()
        output_df['GOLD_CLIP'] = tmp['gold_clips_pvs'].tolist()
        output_df['GOLD_ANS'] = tmp['gold_clips_ans'].tolist()
    output_df.to_csv(output_path, index=False)
    return len(output_df)

# checked
def create_input_for_mturk(cfg, df, method, output_path):
    """
    Create input.csv for MTurk
    :param cfg: configuration  file
    :param df:  row input, see validate_inputs for details
    :param output_path: path to output file
    """
    if method in ['acr', 'avatar']:
        return create_input_for_acr(cfg, df, output_path)
    elif method in ['dcr', 'ccr']:
        return create_input_for_dcr(cfg, df, output_path)
    elif method in ['acr-hr']:
        return create_input_for_acrhr(cfg, df, output_path)
    else:
        return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create input.csv for DCR test. ')
    # Configuration: read it from trapping clips.cfg
    parser.add_argument("--row_input", required=True,
                        help="All urls depending to the test method, for DCR: 'pvs', 'src', 'block_matrix_url', "
                             "'circles', 'triangles', 'trapping_ans', 'trapping_pvs', 'trapping_src', 'gold_clips_pvs',"
                             "'gold_clips_src', 'gold_clips_ans'")
    parser.add_argument("--cfg", default="create_input.cfg",
                        help="explains the test")

    parser.add_argument("--method", default="dcr", required=True,
                        help="one of the test methods: acr, dcr")
    args = parser.parse_args()

    #row_input = join(dirname(__file__), args.row_input)
    row_input = args.row_input
    assert os.path.exists(row_input), f"No file in {row_input}]"

    #cfg_path = join(dirname(__file__), args.cfg)
    cfg_path = args.cfg
    assert os.path.exists(cfg_path), f"No file in {cfg_path}]"

    methods = ["acr", "dcr"]
    exp_method = args.method.lower()
    assert exp_method in methods, f"{exp_method} is not a supported method, select from: acr, dcr."

    cfg = CP.ConfigParser()
    cfg._interpolation = CP.ExtendedInterpolation()
    cfg.read(cfg_path)

    print('Start validating inputs')
    df = pd.read_csv(row_input)
    validate_inputs(df, exp_method)
    print('... validation is finished.')

    output_file = os.path.splitext(row_input)[0]+'_'+exp_method+'_publish_batch.csv'
    create_input_for_mturk(cfg['general'], df, exp_method, output_file)
