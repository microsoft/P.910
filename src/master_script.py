"""
/*---------------------------------------------------------------------------------------------
*  Copyright (c) Microsoft Corporation. All rights reserved.
*  Licensed under the MIT License. See License.txt in the project root for license information.
*--------------------------------------------------------------------------------------------*/
@author: Babak Naderi
"""

import argparse
import os
import asyncio
import base64
import random
import string


import configparser as CP
import pandas as pd

import create_input as ca

from jinja2 import Template
from azure_clip_storage import AzureClipStorage, TrappingSamplesInStore, GoldSamplesInStore
import math


def create_analyzer_cfg(cfg, template_path, out_path, n_HITs):
    """
    create cfg file to be used by analyzer script (DCR method)
    :param cfg:
    :param template_path:
    :param out_path:
    :return:
    """
    print("Start creating config file for result_parser")
    config = {}

    config['q_num'] = int(cfg['create_input']['number_of_clips_per_session']) + \
                      int(cfg['create_input']['number_of_trapping_per_session']) + \
                      int(cfg['create_input']['number_of_gold_clips_per_session'])

    config['max_allowed_hits'] = cfg['hit_app_html']['allowed_max_hit_in_project'] \
        if 'allowed_max_hit_in_project' in cfg['hit_app_html'] else n_HITs

    config['quantity_hits_more_than'] = cfg['hit_app_html']['quantity_hits_more_than']
    config['quantity_bonus'] = cfg['hit_app_html']['quantity_bonus']
    config['quality_top_percentage'] = cfg['hit_app_html']['quality_top_percentage']
    config['quality_bonus'] = cfg['hit_app_html']['quality_bonus']

    default_condition = r'.*_c(?P<condition_num>\d{1,2})_.*.mp4'
    default_keys = 'condition_num'
    config['condition_pattern'] = cfg['create_input'].get("condition_pattern", default_condition)
    config['condition_keys'] = cfg['create_input'].get("condition_keys", default_keys)

    # only video
    config['scale'] = cfg['hit_app_html']['scale']
    config['accepted_device'] = cfg['viewing_condition']['accepted_device']
    config['min_device_resolution'] = cfg['viewing_condition']['min_device_resolution']
    config['min_screen_refresh_rate'] = cfg['viewing_condition']['min_screen_refresh_rate']
    # gold    
    if 'gold_clips_src' in cfg['hit_app_html']:
        config['gold_ans_format'] = cfg['hit_app_html']['gold_ans_format']

    with open(template_path, 'r') as file:
        content = file.read()
        file.seek(0)
    t = Template(content)
    cfg_file = t.render(cfg=config)
       

    with open(out_path, 'w') as file:
        file.write(cfg_file)
        file.close()
    print(f"  [{out_path}] is created")


def get_rand_id(chars=string.ascii_uppercase + string.digits, N=10):
    """
    Generate random id to be used in multiple places like cookies_name
    :param chars:
    :param N:
    :return:
    """
    return ''.join(random.choice(chars) for _ in range(N))


async def create_hit_app_dcr(master_cfg, template_path, out_path, training_path, trap_path, general_cfg, n_HITs,
                             is_ccr):
    """
    Create the hit_app (html file) corresponding to this project for dcr
    :param master_cfg:
    :param template_path:
    :param out_path:
    :param training_path:
    :param general_cfg:
    :return:
    """
    print("Start creating custom hit_app (html)")
    create_input_cfg = master_cfg['create_input']
    hit_app_html_cfg = master_cfg['hit_app_html']
    viewing_condition_cfg = master_cfg['viewing_condition']

    config = {}
    config['cookie_name'] = hit_app_html_cfg['cookie_name'] if 'cookie_name' in hit_app_html_cfg else 'dcr_'+get_rand_id()
    config['qual_cookie_name'] = hit_app_html_cfg['qual_cookie_name'] if 'qual_cookie_name' in hit_app_html_cfg else 'qual_'+get_rand_id()
    config['allowed_max_hit_in_project'] = hit_app_html_cfg['allowed_max_hit_in_project'] if 'allowed_max_hit_in_project' in hit_app_html_cfg else  n_HITs
    config['contact_email'] = hit_app_html_cfg["contact_email"] if "contact_email" in cfg else "ic3ai@outlook.com"
    config['internet_speed_Mbps'] = hit_app_html_cfg["internet_speed_Mbps"] if "internet_speed_Mbps" in hit_app_html_cfg else 80


    config['hit_base_payment'] = hit_app_html_cfg['hit_base_payment']
    config['quantity_hits_more_than'] = hit_app_html_cfg['quantity_hits_more_than']
    config['quantity_bonus'] = hit_app_html_cfg['quantity_bonus']
    config['quality_top_percentage'] = hit_app_html_cfg['quality_top_percentage']
    config['quality_bonus'] = round(float(hit_app_html_cfg['quality_bonus']) + float(hit_app_html_cfg['quantity_bonus']), 2)
    config['sum_quantity'] = round(float(hit_app_html_cfg['quantity_bonus']) + float(hit_app_html_cfg['hit_base_payment']), 2)
    config['sum_quality'] = round(config['quality_bonus'] + float(hit_app_html_cfg['hit_base_payment']), 2)

    config['min_screen_refresh_rate'] = viewing_condition_cfg['min_screen_refresh_rate'] if 'min_screen_refresh_rate' in viewing_condition_cfg else 30
    config['min_device_resolution'] = viewing_condition_cfg['min_device_resolution'] if 'min_device_resolution' in viewing_condition_cfg else '{w: 1280, h:720}'
    config['accepted_device'] = viewing_condition_cfg['accepted_device'] if 'accepted_device' in viewing_condition_cfg else '["PC"]'
    config['video_player'] = hit_app_html_cfg['video_player']
    if is_ccr:
        config['scale_points'] = int(hit_app_html_cfg['scale']) if 'scale' in hit_app_html_cfg else 7
        if config['scale_points'] not in [4, 7]:
            print(' Warning: For CCR test method, scale should be 4 (JVET) or 7 (original) points. Will continue with '
                  '7 point.')
            config['scale_points'] = 7
    else:
        config['scale_points'] = hit_app_html_cfg['scale'] if 'scale' in hit_app_html_cfg else 5

    config['is_ccr'] = 'true' if is_ccr else 'false'
    config = {**config, **general_cfg}
    # rating urls
    rating_urls = []
    n_clips = int(create_input_cfg['number_of_clips_per_session'])
    n_traps = int(create_input_cfg['number_of_trapping_per_session'])
    n_gold = int(create_input_cfg['number_of_gold_clips_per_session']) if 'number_of_gold_clips_per_session' in \
                                                                          create_input_cfg else 0

    # 'dummy':'dummy' is added becuase of current bug in AMT for replacing variable names. See issue #6
    for i in range(0, n_clips):
        rating_urls.append({"ref": f"${{Q{i}_R}}", "processed": f"${{Q{i}_P}}", 'dummy': 'dummy'})

    if n_traps > 1:
        print("More than 1 trapping clips question is not supported. Proceed with 1 trap")
    if n_traps > 0:
        rating_urls.append({"ref": "${TP_REF}", "processed": "${TP_CLIP}", 'dummy': 'dummy'})
    if n_gold > 1:
        print("More than 1 gold clip question is not supported. Proceed with 1 gold")
    if n_gold > 0:
        rating_urls.append({"ref": "${GOLD_REF}", "processed": "${GOLD_CLIP}", 'dummy': 'dummy'})
        config['gold_ans'] = "${GOLD_ANS}"
    else:
        config['gold_ans'] = ""

    config['rating_urls'] = rating_urls

    # training urls
    df_train = pd.read_csv(training_path)
    train_urls = []
    # train_ref = None
    for _, row in df_train.iterrows():
        train_urls.append({"ref": f"{row['training_src']}", "processed": f"{row['training_pvs']}", 'dummy': 'dummy'})
    # add a trapping clips to the training section
    if n_traps > 0:
        df_trap = pd.DataFrame()
        if trap_path and os.path.exists(trap_path):
            df_trap = pd.read_csv(trap_path, nrows=1)
        else:
            trapclipsstore = TrappingSamplesInStore(master_cfg['TrappingQuestions'], 'TrappingQuestions')
            df_trap = await trapclipsstore.get_dataframe()
        # trapping clips are required, at list 1 clip should be available here
        if len(df_trap.index) < 1:
            raise "At least one trapping clip is required"
        for _, row in df_trap.head(n=1).iterrows():
            trap_ref = row['trapping_src']
            trap_pvs = row['trapping_pvs']
            trap_ans = row['trapping_ans']
        train_urls.append({"ref": f"{trap_ref}", "processed": f"{trap_pvs}", 'dummy': 'dummy'})
        config['training_trap_urls'] = trap_pvs
        config['training_trap_ans'] = trap_ans

    config['training_urls'] = train_urls

    with open(template_path, 'r') as file:
        content = file.read()
        file.seek(0)
    t = Template(content)
    html = t.render(cfg=config)

    with open(out_path, 'w') as file:
        file.write(html)
    print(f"  [{out_path}] is created")


async def create_hit_app_acr(master_cfg, template_path, out_path, training_path, trap_path, general_cfg, n_HITs):
    """
    Create the ACR.html file corresponding to this project
    :param master_cfg:
    :param template_path:
    :param out_path:
    :param training_path:
    :param trap_path:
    :param general_cfg:
    :return:
    """
    print("Start creating custom acr.html")

    create_input_cfg = master_cfg['create_input']
    hit_app_html_cfg = master_cfg['hit_app_html']
    viewing_condition_cfg = master_cfg['viewing_condition']

    config = dict()
    config['debug'] = hit_app_html_cfg['debug'] if 'debug' in hit_app_html_cfg else 'false'
    config['use_trapping_question'] = hit_app_html_cfg['use_trapping_question']
    config['use_repeated_question'] = hit_app_html_cfg['use_repeated_question']
    #config['instruction_html'] = hit_app_html_cfg['instruction_html']
    #config['rating_questions'] = hit_app_html_cfg['rating_questions']
    #config['rating_answers'] = hit_app_html_cfg['rating_answers']
    if test_method == 'avatar':
        config['template'] = hit_app_html_cfg['template'].lower().strip()
        # check for accepted values : avatar_a, avatar_b, or avatar_problem_token
        if config['template'] not in ['avatar_a', 'avatar_b', 'avatar_problem_token']:
            raise SystemExit("Error: 'template' should be one of the following values: avatar_a, avatar_b, or avatar_problem_token. Update the config file:", config['template'])

    config['cookie_name'] = hit_app_html_cfg['cookie_name'] if 'cookie_name' in hit_app_html_cfg else \
        f'acr_{get_rand_id()}'
    config['qual_cookie_name'] = hit_app_html_cfg['qual_cookie_name'] if 'qual_cookie_name' in hit_app_html_cfg else \
        f'qul_{get_rand_id()}'

    config['allowed_max_hit_in_project'] = hit_app_html_cfg['allowed_max_hit_in_project'] \
        if 'allowed_max_hit_in_project' in hit_app_html_cfg else  n_HITs
    config['contact_email'] = hit_app_html_cfg["contact_email"] if "contact_email" in hit_app_html_cfg else\
        "ic3ai@outlook.com"
    config['internet_speed_Mbps'] = hit_app_html_cfg["internet_speed_Mbps"] if "internet_speed_Mbps" in hit_app_html_cfg else 80

    config['hit_base_payment'] = hit_app_html_cfg['hit_base_payment']
    config['quantity_hits_more_than'] = hit_app_html_cfg['quantity_hits_more_than']
    config['quantity_bonus'] = hit_app_html_cfg['quantity_bonus']
    config['quality_top_percentage'] = hit_app_html_cfg['quality_top_percentage']
    config['quality_bonus'] = round(float(hit_app_html_cfg['quality_bonus']) + float(hit_app_html_cfg['quantity_bonus']), 2)
    config['sum_quantity'] = round(float(hit_app_html_cfg['quantity_bonus']) + float(hit_app_html_cfg['hit_base_payment']), 2)
    config['sum_quality'] = round(config['quality_bonus'] + float(hit_app_html_cfg['hit_base_payment']),2 )

    config['min_screen_refresh_rate'] = viewing_condition_cfg[
        'min_screen_refresh_rate'] if 'min_screen_refresh_rate' in viewing_condition_cfg else 30
    config['min_device_resolution'] = viewing_condition_cfg[
        'min_device_resolution'] if 'min_device_resolution' in viewing_condition_cfg else '{w: 1280, h:720}'
    config['accepted_device'] = viewing_condition_cfg[
        'accepted_device'] if 'accepted_device' in viewing_condition_cfg else '["PC"]'
    config['scale_points'] = hit_app_html_cfg['scale'] if 'scale' in hit_app_html_cfg else 5
    config['video_player'] = hit_app_html_cfg['video_player']

    config = {**config, **general_cfg}

    # rating urls
    n_clips = int(create_input_cfg['number_of_clips_per_session'])
    n_traps = int(create_input_cfg['number_of_trapping_per_session'])
    n_gold = int(create_input_cfg['number_of_gold_clips_per_session']) if 'number_of_gold_clips_per_session' in \
                                                                          create_input_cfg else 0
    rating_urls = []
    for i in range(0, n_clips):
        rating_urls.append('${Q'+str(i)+'}')
    if n_traps > 1:
        raise Exception("More than 1 trapping question is not supported.")
    if n_traps == 1:
        rating_urls.append('${TP_CLIP}')

    if n_gold > 1:
        raise Exception("more than 1 gold question is not supported.")
    if n_gold == 1:
        rating_urls.append('${GOLD_CLIP}')
        config['gold_ans'] = "${GOLD_ANS}"
    else:
        config['gold_ans'] = ""
    config['rating_urls'] = rating_urls

    # trappings
    if trap_path and os.path.exists(trap_path):
        df_trap = pd.read_csv(trap_path, nrows=1)
    else:
        trap_clips_store = TrappingSamplesInStore(master_cfg['TrappingQuestions'], 'TrappingQuestions')
        df_trap = await trap_clips_store.get_dataframe()
    # trapping clips are required, at list 1 clip should be available here
    if len(df_trap.index) < 1 and int(create_input_cfg['number_of_clips_per_session']) > 0:
        raise Exception("At least one trapping clip is required")
    for _, row in df_trap.head(n=1).iterrows():
        trap_url = row['trapping_pvs']
        trap_ans = row['trapping_ans']

    config['training_trap_urls'] = trap_url
    config['training_trap_ans'] = trap_ans

    # training urls
    train_urls = []
    if not args.training_gold_clips:
        df_train = pd.read_csv(training_path)
        train_urls = []
        for _, row in df_train.iterrows():
            train_urls.append(row['training_pvs'])
        train_urls.append(trap_url)

    if args.training_gold_clips:
        df_train = pd.read_csv(args.training_gold_clips)
        gold_in_train = []
        cols = list(df_train.columns.where(df_train.columns.str.endswith('_ans')).dropna())

        for _, row in df_train.iterrows():
            train_urls.append(row["training_pvs"])
            data = {
                'url': row["training_pvs"],
            }
            for col in cols:
                if not math.isnan(row[col]):
                    # coded_ans = get_encoded_gold_ans(row["training_clips"], row[col])
                    prfx = col.split('_')[0]
                    data[prfx] = {'ans': str(int(row[col])), 'msg': row[f"{prfx}_msg"],
                                  'var': round(row[f"{prfx}_var"])}
            gold_in_train.append(data.copy())
        config["training_gold_clips"] = gold_in_train

    config['training_urls'] = train_urls

    with open(template_path, 'r') as file:
        content = file.read()
        file.seek(0)
    t = Template(content)
    html = t.render(cfg=config)

    with open(out_path, 'w') as file:
        file.write(html)
    print(f"  [{out_path}] is created")


async def create_hit_app_acrhr(master_cfg, template_path, out_path, training_path, trap_path, general_cfg, n_HITs):
    """
    Create the ACR-HR.html file corresponding to this project
    :param master_cfg:
    :param template_path:
    :param out_path:
    :param training_path:
    :param trap_path:
    :param general_cfg:
    :return:
    """
    print("Start creating custom acr-hr.html")

    create_input_cfg = master_cfg['create_input']
    hit_app_html_cfg = master_cfg['hit_app_html']
    viewing_condition_cfg = master_cfg['viewing_condition']

    config = {}
    config['cookie_name'] = hit_app_html_cfg['cookie_name'] if 'cookie_name' in hit_app_html_cfg else \
        f'acr_{get_rand_id()}'
    config['qual_cookie_name'] = hit_app_html_cfg['qual_cookie_name'] if 'qual_cookie_name' in hit_app_html_cfg else \
        f'qul_{get_rand_id()}'

    config['allowed_max_hit_in_project'] = hit_app_html_cfg['allowed_max_hit_in_project'] \
        if 'allowed_max_hit_in_project' in hit_app_html_cfg else n_HITs
    config['contact_email'] = hit_app_html_cfg["contact_email"] if "contact_email" in hit_app_html_cfg else\
        "ic3ai@outlook.com"
    config['internet_speed_Mbps'] = hit_app_html_cfg["internet_speed_Mbps"] if "internet_speed_Mbps" in hit_app_html_cfg else 80

    config['hit_base_payment'] = hit_app_html_cfg['hit_base_payment']
    config['quantity_hits_more_than'] = hit_app_html_cfg['quantity_hits_more_than']
    config['quantity_bonus'] = hit_app_html_cfg['quantity_bonus']
    config['quality_top_percentage'] = hit_app_html_cfg['quality_top_percentage']
    config['quality_bonus'] = float(hit_app_html_cfg['quality_bonus']) + float(hit_app_html_cfg['quantity_bonus'])
    config['sum_quantity'] = float(hit_app_html_cfg['quantity_bonus']) + float(hit_app_html_cfg['hit_base_payment'])
    config['sum_quality'] = config['quality_bonus'] + float(hit_app_html_cfg['hit_base_payment'])

    config['min_screen_refresh_rate'] = viewing_condition_cfg[
        'min_screen_refresh_rate'] if 'min_screen_refresh_rate' in viewing_condition_cfg else 30
    config['min_device_resolution'] = viewing_condition_cfg[
        'min_device_resolution'] if 'min_device_resolution' in viewing_condition_cfg else '{w: 1280, h:720}'
    config['accepted_device'] = viewing_condition_cfg[
        'accepted_device'] if 'accepted_device' in viewing_condition_cfg else '["PC"]'
    config['scale_points'] = hit_app_html_cfg['scale'] if 'scale' in hit_app_html_cfg else 5


    config = {**config, **general_cfg}

    # rating urls
    n_clips = int(create_input_cfg['number_of_clips_per_session'])
    n_traps = int(create_input_cfg['number_of_trapping_per_session'])
    n_gold = int(create_input_cfg['number_of_gold_clips_per_session']) if 'number_of_gold_clips_per_session' in \
                                                                          create_input_cfg else 0
    rating_urls = []
    for i in range(0, n_clips):
        rating_urls.append('${Q'+str(i)+'}')
    ref_urls = []
    for i in range(0, n_clips):
        ref_urls.append('${Q' + str(i) + '_R}')

    if n_traps > 1:
        raise Exception("More than 1 trapping question is not supported.")
    if n_traps == 1:
        rating_urls.append('${TP_CLIP}')

    if n_gold > 1:
        raise Exception("more than 1 gold question is not supported.")
    if n_gold == 1:
        rating_urls.append('${GOLD_CLIP}')
        config['gold_ans'] = "${GOLD_ANS}"
    else:
        config['gold_ans'] = ""
    config['rating_urls'] = rating_urls
    config['ref_urls'] = ref_urls

    # trappings
    if trap_path and os.path.exists(trap_path):
        df_trap = pd.read_csv(trap_path, nrows=1)
    else:
        trap_clips_store = TrappingSamplesInStore(master_cfg['TrappingQuestions'], 'TrappingQuestions')
        df_trap = await trap_clips_store.get_dataframe()
    # trapping clips are required, at list 1 clip should be available here
    if len(df_trap.index) < 1 and int(create_input_cfg['number_of_clips_per_session']) > 0:
        raise Exception("At least one trapping clip is required")
    for _, row in df_trap.head(n=1).iterrows():
        trap_url = row['trapping_pvs']
        trap_ans = row['trapping_ans']

    config['training_trap_urls'] = trap_url
    config['training_trap_ans'] = trap_ans

    # training urls
    df_train = pd.read_csv(training_path)
    train_urls = []
    for _, row in df_train.iterrows():
        train_urls.append(row['training_pvs'])
    train_urls.append(trap_url)

    config['training_urls'] = train_urls

    with open(template_path, 'r') as file:
        content = file.read()
        file.seek(0)
    t = Template(content)
    html = t.render(cfg=config)

    with open(out_path, 'w') as file:
        file.write(html)
    print(f"  [{out_path}] is created")


# checked
async def prepare_csv_for_create_input(cfg, test_method, clips, gold, trapping, general, color_vision_res_path):
    """
    Merge different input files into one dataframe
    :param test_method
    :param clips:
    :param trainings:
    :param gold:
    :param trapping:
    :param general:
    :return:
    """
    df_clips = pd.DataFrame()
    df_gold = pd.DataFrame()
    df_trap = pd.DataFrame()
    rating_clips = []
    if clips and os.path.exists(clips):
        df_clips = pd.read_csv(clips)
    else:
        rating_clips_stores = cfg.get('RatingClips', 'RatingClipsConfigurations').split(',')
        for model in rating_clips_stores:
            enhancedClip = AzureClipStorage(cfg[model], model)
            eclips = await enhancedClip.clip_names
            eclips_urls = [enhancedClip.make_clip_url(clip) for clip in eclips]

            print('length of urls for store [{0}] is [{1}]'.format(model, len(await enhancedClip.clip_names)))
            rating_clips = rating_clips + eclips_urls
        # todod also src
        df_clips = pd.DataFrame({'pvs': rating_clips})

    df_general = pd.read_csv(general)
    df_color_vision = pd.read_csv(color_vision_res_path)
    # add prefix cv_ to color vision columns
    df_color_vision.columns = ['cv_'+col for col in df_color_vision.columns]
    # randomize 
    df_color_vision = df_color_vision.sample(frac=1).reset_index(drop=True)
    df_general = df_general.sample(frac=1).reset_index(drop=True) 

    if gold and os.path.exists(gold):
        df_gold = pd.read_csv(gold)
    else:
        goldclipsstore = GoldSamplesInStore(cfg['GoldenSample'], 'GoldenSample')
        df_gold = await goldclipsstore.get_dataframe()
        print('total gold clips from store [{0}]'.format(len(await goldclipsstore.clip_names)))

    if trapping and os.path.exists(trapping):
        df_trap = pd.read_csv(trapping)
    else:
        trapclipsstore = TrappingSamplesInStore(cfg['TrappingQuestions'], 'TrappingQuestions')
        df_trap = await trapclipsstore.get_dataframe()
        print('total trapping clips from store [{0}]'.format(len(await trapclipsstore.clip_names)))
    result = pd.concat([df_clips, df_gold, df_trap, df_general, df_color_vision], axis=1, sort=False)
    return result


# checked
def prepare_basic_cfg(df):
    """
    Create basic config file to be inserted inside the HTML template. Basically adding variables to be filled in the
    template.
    :param df:
    :return:
    """
    config = {}
    # nothing for now, if it will be decided to include dynamic images for CMPs then it can be added here
    return config


# checked
def get_path(test_method):
    """
    check all the preequsites and see if all resources are available
    :param test_method:
    :param is_p831_fest:
    :return:
    """
    #   for acr
    acr_template_path = os.path.join(os.path.dirname(__file__), 'template/ACR_template.html')
    acr_cfg_template_path = os.path.join(os.path.dirname(__file__),
                                         'assets_master_script/result_parser_template.cfg')

    # for acr-hr
    acrhr_template_path = os.path.join(os.path.dirname(__file__), 'template/ACRHR_template.html')
    acrhr_cfg_template_path = os.path.join(os.path.dirname(__file__),
                                           'assets_master_script/result_parser_template.cfg')

    #   for dcr
    dcr_template_path = os.path.join(os.path.dirname(__file__), 'template/DCR_template.html')
    dcr_ccr_cfg_template_path = os.path.join(os.path.dirname(__file__),
                                             'assets_master_script/result_parser_template.cfg')

    #   for avatar
    avatar_template_path = os.path.join(os.path.dirname(__file__), 'template/avatar_template.html')
    avatar_cfg_template_path = os.path.join(os.path.dirname(__file__),
                                         'assets_master_script/result_parser_template.cfg')

    method_to_template = {  # (method, is_p831_fest)
        ('acr'): (acr_template_path, acr_cfg_template_path),
        ('dcr'): (dcr_template_path, dcr_ccr_cfg_template_path),
        ('acr-hr'): (acrhr_template_path, acrhr_cfg_template_path),
        ('ccr'): (dcr_template_path, dcr_ccr_cfg_template_path),
        ('avatar'): (avatar_template_path, avatar_cfg_template_path),
    }

    template_path, cfg_path = method_to_template[(test_method)]
    assert os.path.exists(template_path), f'No html template file found  in {template_path}'
    assert os.path.exists(cfg_path), f'No cfg template  found  in {cfg_path}'

    return template_path, cfg_path


# checked
async def main(cfg, test_method, args):

    # check assets
    general_path = os.path.join(os.path.dirname(__file__), 'assets_master_script/general.csv')
    internal_general_path = os.path.join(os.path.dirname(__file__), 'assets_master_script/internal_general.csv')
    if os.path.exists(internal_general_path):
        general_path = internal_general_path
    assert os.path.exists(general_path), f"No csv file containing general infos in {general_path}"
    color_vision_res_path = os.path.join(os.path.dirname(__file__), 'assets_master_script/color_vision_plates.csv')
    internal_color_vision_res_path = os.path.join(os.path.dirname(__file__), 'assets_master_script/internal_color_vision_plates_20122024.csv')
    if os.path.exists(internal_color_vision_res_path):
        color_vision_res_path = internal_color_vision_res_path
    assert os.path.exists(color_vision_res_path), f"No csv file containing color vision plates infos in {color_vision_res_path}"
    template_path, cfg_path = get_path(test_method)

    cfg_hit_app = cfg["hit_app_html"]

    # check clip_packing_strategy
    # TODO: check it
    clip_packing_strategy = "random"
    if "clip_packing_strategy" in cfg["create_input"]:
        clip_packing_strategy = cfg["create_input"]["clip_packing_strategy"].strip().lower()
        if clip_packing_strategy == "balanced_block":
            # condition pattern is needed
            if not(("condition_pattern" in cfg["create_input"]) & ("condition_keys" in cfg["create_input"])):
                raise SystemExit("Error: by 'balanced_block' strategy, 'condition_pattern' and 'condition_keys' should "
                                 "be specified in the configuration.")
            if (',' in cfg["create_input"]["condition_keys"]) & ("block_keys" not in cfg["create_input"]):
                raise SystemExit("Error: In 'balanced_block' strategy, 'block_keys' should be specified in "
                                 "configuration when 'condition_keys' contains more than one key.")
        elif not(clip_packing_strategy == "random"):
            raise SystemExit("Error: Unexpected value for 'clip_packing_strategy' in the configuration file")

    # create output folder *******
    output_dir = args.project
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    # prepare format
    df = await prepare_csv_for_create_input(cfg, test_method, args.clips, args.gold_clips, args.trapping_clips, general_path, color_vision_res_path)

    # create inputs
    print('Start validating inputs')
    ca.validate_inputs(df, test_method)
    print('... validation is finished.')

    output_csv_file = os.path.join(output_dir, args.project+'_publish_batch.csv')
    df.to_csv(output_csv_file, index=False)
    print(f"  [{output_csv_file}] is created")
    n_HITs = ca.create_input_for_mturk(cfg['create_input'], df, test_method, output_csv_file)

    # check settings of quantity bonus
    if not (int(cfg_hit_app["quantity_hits_more_than"]) in range(int(n_HITs/2),  int(n_HITs*2/3)+1)):
        print("\nWARNING: it seems that 'quantity_hits_more_than' not set properly. Consider to use a number in"
                              f" the range of [{int(n_HITs/2)}, {int(n_HITs*2/3)}].\n")

    # Create general config for variables in the HTML template
    general_cfg = prepare_basic_cfg(df)

    # create hit_app
    output_file_name = f"{args.project}_{test_method}.html"
    output_html_file = os.path.join(output_dir, output_file_name)
    # ********************
    if test_method in ['dcr', 'ccr']:
        await create_hit_app_dcr(cfg, template_path, output_html_file, args.training_clips, args.trapping_clips,
                                 general_cfg, n_HITs, test_method == 'ccr')
    elif test_method in ['acr', 'avatar']:
        await create_hit_app_acr(cfg, template_path, output_html_file, args.training_clips, args.trapping_clips,
                                 general_cfg, n_HITs)
    elif test_method == 'acr-hr':
        await create_hit_app_acrhr(cfg, template_path, output_html_file, args.training_clips, args.trapping_clips,
                                 general_cfg, n_HITs)
    else:
        print('Method is not supported yet.')

    # create a config file for analyzer ********
    output_cfg_file_name = f"{args.project}_{test_method}_result_parser.cfg"
    output_cfg_file = os.path.join(output_dir, output_cfg_file_name)
    create_analyzer_cfg(cfg, cfg_path, output_cfg_file, n_HITs)


if __name__ == '__main__':
    print("Welcome to the Master script for P.910-crowd Toolkit.")
    parser = argparse.ArgumentParser(description='Master script to prepare test')
    parser.add_argument("--project", help="Name of the project", required=True)
    parser.add_argument("--cfg", help="Configuration file, see master.cfg", required=True)
    parser.add_argument("--method", required=True,
                        help="one of the test methods: 'acr', 'acr-hr', 'dcr', 'ccr', 'avatar'")
    parser.add_argument("--clips", help="A csv containing urls of all clips to be rated in column 'pvs', in "
                                        "case of DCR it should also contain a column for 'src'")
    parser.add_argument("--gold_clips", help="A csv containing urls of all gold clips in column 'gold_clips_pvs' and "
                                             "their answer in column 'gold_clips_ans'. For DCR also 'gold_clips_src' "
                                             "is needed")
    parser.add_argument("--training_clips", help="A csv containing urls of all training clips to be rated in training "
                                                 "section. Columns 'training_pvs' and 'training_src' in case of DCR",
                        required=False)
    parser.add_argument("--trapping_clips", help="A csv containing urls of all trapping clips. Columns 'trapping_pvc'"
                                                 "and 'trapping_ans'. In case of DCR also 'trapping_src'")
    parser.add_argument(
        "--training_gold_clips", default=None, help="A csv containing urls and details of gold training questions ",
        required=False)

    # check input arguments
    args = parser.parse_args()

    methods = ['acr', 'dcr', 'acr-hr', 'pc', 'ccr', 'avatar']
    test_method = args.method.lower()
    assert test_method in methods, f"No such a method supported, please select between {methods}"
    assert os.path.exists(args.cfg), f"No config file in {args.cfg}"

    if args.training_clips:
        assert os.path.exists(args.training_clips), f"No csv file containing training clips in {args.training_clips}"
    elif args.training_gold_clips:
        assert os.path.exists(
            args.training_gold_clips), f"No csv file containing training_gold_clips in {args.training_gold_clips}"
    else:
        raise ValueError("No training or training_gold clips provided")

    cfg = CP.ConfigParser()
    cfg._interpolation = CP.ExtendedInterpolation()
    cfg.read(args.cfg)

    if args.clips:
        assert os.path.exists(args.clips), f"No csv file containing clips in {args.clips}"
    elif cfg.has_option('RatingClips', 'RatingClipsConfigurations'):
        assert len(cfg['RatingClips']['RatingClipsConfigurations']) > 0, f"No cloud store for clips specified in config"
    else:
        raise ValueError("Neither clips file nor cloud store provided for rating clips")

    if args.gold_clips:
        assert os.path.exists(args.gold_clips), f"No csv file containing gold clips in {args.gold_clips}"
    elif cfg.has_option('GoldenSample', 'Path'):
        assert len(cfg['GoldenSample']['Path']) > 0, "No golden clips store found"
    else:
        raise ValueError("Neither gold clips file nor store configuration provided")

    if args.trapping_clips:
        assert os.path.exists(args.trapping_clips), f"No csv file containing trapping  clips in {args.trapping_clips}"
    elif cfg.has_option('TrappingQuestions', 'Path'):
        assert len(cfg['TrappingQuestions']['Path']) > 0, "No golden clips store found"
    else:
        raise ValueError("Neither trapping clips file nor store configuration provided")

    asyncio.run(main(cfg, test_method, args))
