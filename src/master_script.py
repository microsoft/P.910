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
from azure_clip_storage import AzureClipStorage, TrappingSamplesInStore, GoldSamplesInStore, PairComparisonSamplesInStore


# todo for ACR
def create_analyzer_cfg_general(cfg, cfg_section, template_path, out_path):
    """
    create cfg file to be used by analyzer script (acr, p835, and echo_impairment_test method)
    :param cfg:
    :param cfg_section_name: 'acr_html', 'p835_html', 'echo_impairment_test_html'
    :param template_path:
    :param out_path:
    :return:
    """
    print("Start creating config file for result_parser")
    config = {}

    config['q_num'] = int(cfg['create_input']['number_of_clips_per_session']) + \
                      int(cfg['create_input']['number_of_trapping_per_session']) + \
                      int(cfg['create_input']['number_of_gold_clips_per_session'])

    config['max_allowed_hits'] = cfg_section['allowed_max_hit_in_project']

    config['quantity_hits_more_than'] = cfg_section['quantity_hits_more_than']
    config['quantity_bonus'] = cfg_section['quantity_bonus']
    config['quality_top_percentage'] = cfg_section['quality_top_percentage']
    config['quality_bonus'] = cfg_section['quality_bonus']
    default_condition = r'.*_c(?P<condition_num>\d{1,2})_.*.wav'
    default_keys = 'condition_num'
    config['condition_pattern'] = cfg['create_input'].get("condition_pattern", default_condition)
    config['condition_keys'] = cfg['create_input'].get("condition_keys", default_keys)

    with open(template_path, 'r') as file:
        content = file.read()
        file.seek(0)
    t = Template(content)
    cfg_file = t.render(cfg=config)

    with open(out_path, 'w') as file:
        file.write(cfg_file)
        file.close()
    print(f"  [{out_path}] is created")


def create_analyzer_cfg_dcr(cfg, template_path, out_path):
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

    config['max_allowed_hits'] = cfg['hit_app_html']['allowed_max_hit_in_project']

    config['quantity_hits_more_than'] = cfg['hit_app_html']['quantity_hits_more_than']
    config['quantity_bonus'] = cfg['hit_app_html']['quantity_bonus']
    config['quality_top_percentage'] = cfg['hit_app_html']['quality_top_percentage']
    config['quality_bonus'] = cfg['hit_app_html']['quality_bonus']

    default_condition = r'.*_c(?P<condition_num>\d{1,2})_.*.wav'
    default_keys = 'condition_num'
    config['condition_pattern'] = cfg['create_input'].get("condition_pattern", default_condition)
    config['condition_keys'] = cfg['create_input'].get("condition_keys", default_keys)

    # only video
    config['scale'] = cfg['hit_app_html']['scale']
    config['accepted_device'] = cfg['viewing_condition']['accepted_device']
    config['min_device_resolution'] = cfg['viewing_condition']['min_device_resolution']
    config['min_screen_refresh_rate'] = cfg['viewing_condition']['min_screen_refresh_rate']

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
    return ''.join(random.choice(chars) for _ in range(N))


# checked
async def create_hit_app_dcr(master_cfg, template_path, out_path, training_path, trap_path, general_cfg):
    """
    Create the hit_app (html file) corresponding to this project for ccr and dcr
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
    config['cookie_name'] = hit_app_html_cfg['cookie_name'] if 'cookie_name' in hit_app_html_cfg else 'qual_'+get_rand_id()
    config['qual_cookie_name'] = hit_app_html_cfg['qual_cookie_name'] if 'qual_cookie_name' in hit_app_html_cfg else 'qual_'+get_rand_id()
    config['allowed_max_hit_in_project'] = hit_app_html_cfg['allowed_max_hit_in_project']
    config['contact_email'] = hit_app_html_cfg["contact_email"] if "contact_email" in cfg else "ic3ai@outlook.com"

    config['hit_base_payment'] = hit_app_html_cfg['hit_base_payment']
    config['quantity_hits_more_than'] = hit_app_html_cfg['quantity_hits_more_than']
    config['quantity_bonus'] = hit_app_html_cfg['quantity_bonus']
    config['quality_top_percentage'] = hit_app_html_cfg['quality_top_percentage']
    config['quality_bonus'] = float(hit_app_html_cfg['quality_bonus']) + float(hit_app_html_cfg['quantity_bonus'])
    config['sum_quantity'] = float(hit_app_html_cfg['quantity_bonus']) + float(hit_app_html_cfg['hit_base_payment'])
    config['sum_quality'] = config['quality_bonus'] + float(hit_app_html_cfg['hit_base_payment'])

    config['min_screen_refresh_rate'] = viewing_condition_cfg['min_screen_refresh_rate'] if 'min_screen_refresh_rate' in viewing_condition_cfg else 60
    config['min_device_resolution'] = viewing_condition_cfg['min_device_resolution'] if 'min_device_resolution' in viewing_condition_cfg else '{w: 1280, h:720}'
    config['accepted_device'] = viewing_condition_cfg['accepted_device'] if 'accepted_device' in viewing_condition_cfg else '["PC"]'
    config['scale_points'] = hit_app_html_cfg['scale'] if 'scale' in hit_app_html_cfg else 5


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
            raise ("At least one trapping clip is required")
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


# TODO ACR
async def create_hit_app_acr(cfg, template_path, out_path, training_path, trap_path, cfg_g, cfg_trapping_store,
                             general_cfg):
    """
    Create the ACR.html file corresponding to this project
    :param cfg:
    :param template_path:
    :param out_path:
    :return:
    """
    print("Start creating custom acr.html")
    df_trap = pd.DataFrame()
    if trap_path and os.path.exists(trap_path):
        df_trap = pd.read_csv(trap_path, nrows=1)
    else:
        trapclipsstore = TrappingSamplesInStore(cfg_trapping_store, 'TrappingQuestions')
        df_trap = await trapclipsstore.get_dataframe()
    # trapping clips are required, at list 1 clip should be available here
    if len(df_trap.index) < 1 and int(cfg_g['number_of_clips_per_session']) > 0:
        raise ("At least one trapping clip is required")
    for _, row in df_trap.head(n=1).iterrows():
        trap_url = row['trapping_clips']
        trap_ans = row['trapping_ans']

    config = {}
    config['cookie_name'] = cfg['cookie_name']
    config['qual_cookie_name'] = cfg['qual_cookie_name']
    config['allowed_max_hit_in_project'] = cfg['allowed_max_hit_in_project']
    config['training_trap_urls'] = trap_url
    config['training_trap_ans'] = trap_ans
    config['contact_email'] = cfg["contact_email"] if "contact_email" in cfg else "ic3ai@outlook.com"

    config['hit_base_payment'] = cfg['hit_base_payment']
    config['quantity_hits_more_than'] = cfg['quantity_hits_more_than']
    config['quantity_bonus'] = cfg['quantity_bonus']
    config['quality_top_percentage'] = cfg['quality_top_percentage']
    config['quality_bonus'] = float(cfg['quality_bonus']) + float(cfg['quantity_bonus'])
    config['sum_quantity'] = float(cfg['quantity_bonus']) + float(cfg['hit_base_payment'])
    config['sum_quality'] = config['quality_bonus'] + float(cfg['hit_base_payment'])
    config = {**config, **general_cfg}

    df_train = pd.read_csv(training_path)
    train = []
    for _, row in df_train.iterrows():
        train.append(row['training_clips'])
    train.append(trap_url)
    config['training_urls'] = train

    # rating urls
    rating_urls = []
    n_clips = int(cfg_g['number_of_clips_per_session'])
    n_traps = int(cfg_g['number_of_trapping_per_session'])
    n_gold_clips = int(cfg_g['number_of_gold_clips_per_session'])

    for i in range(0, n_clips):
        rating_urls.append('${Q'+str(i)+'}')
    if n_traps > 1:
        raise Exception("more than 1 trapping clips question is not supported.")
    if n_traps == 1:
        rating_urls.append('${TP}')

    if n_gold_clips > 1:
        raise Exception("more than 1 gold question is not supported.")
    if n_gold_clips == 1:
        rating_urls.append('${gold_clips}')

    config['rating_urls'] = rating_urls

    with open(template_path, 'r') as file:
        content = file.read()
        file.seek(0)
    t = Template(content)
    html = t.render(cfg=config)

    with open(out_path, 'w') as file:
        file.write(html)
    print(f"  [{out_path}] is created")


# checked
async def prepare_csv_for_create_input(cfg, test_method, clips, gold, trapping, general):
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

        df_clips = pd.DataFrame({'pvs': rating_clips})

    df_general = pd.read_csv(general)

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
    result = pd.concat([df_clips, df_gold, df_trap, df_general], axis=1, sort=False)
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
    #acr_template_path = os.path.join(os.path.dirname(__file__), 'P808Template/ACR_template.html')
    #acr_cfg_template_path = os.path.join(os.path.dirname(__file__),
    #                                     'assets_master_script/acr_result_parser_template.cfg')

    #   for dcr
    dcr_template_path = os.path.join(os.path.dirname(__file__), 'template/DCR_template.html')
    dcr_ccr_cfg_template_path = os.path.join(os.path.dirname(__file__),
                                             'assets_master_script/dcr_result_parser_template.cfg')

    method_to_template = { # (method, is_p831_fest)
       # ('acr'): (acr_template_path, acr_cfg_template_path),
        ('dcr'): (dcr_template_path, dcr_ccr_cfg_template_path),
    }

    template_path, cfg_path = method_to_template[(test_method)]
    assert os.path.exists(template_path), f'No html template file found  in {template_path}'
    assert os.path.exists(cfg_path), f'No cfg template  found  in {cfg_path}'

    return template_path, cfg_path


# checked
async def main(cfg, test_method, args):

    # check assets
    general_path = os.path.join(os.path.dirname(__file__), 'assets_master_script/general.csv')
    assert os.path.exists(general_path), f"No csv file containing general infos in {general_path}"
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
    df = await prepare_csv_for_create_input(cfg, test_method, args.clips, args.gold_clips, args.trapping_clips, general_path)

    # create inputs
    print('Start validating inputs')
    ca.validate_inputs(cfg['create_input'], df, test_method)
    print('... validation is finished.')

    output_csv_file = os.path.join(output_dir, args.project+'_publish_batch.csv')
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

    if test_method == 'dcr':
        await create_hit_app_dcr(cfg, template_path, output_html_file, args.training_clips, args.trapping_clips,
                                     general_cfg)
    else:
        print('Method is not supported yet.')

    # create a config file for analyzer ********
    output_cfg_file_name = f"{args.project}_{test_method}_result_parser.cfg"
    output_cfg_file = os.path.join(output_dir, output_cfg_file_name)

    if test_method in ['acr']:
        create_analyzer_cfg_general(cfg, cfg_hit_app, cfg_path, output_cfg_file)
    else:
        create_analyzer_cfg_dcr(cfg, cfg_path, output_cfg_file)


if __name__ == '__main__':
    print("Welcome to the Master script for P.910-crowd Toolkit.")
    parser = argparse.ArgumentParser(description='Master script to prepare test')
    parser.add_argument("--project", help="Name of the project", required=True)
    parser.add_argument("--cfg", help="Configuration file, see master.cfg", required=True)
    parser.add_argument("--method", required=True,
                        help="one of the test methods: 'acr', 'acr-hr', 'dcr', 'pc'")
                        #help="one of the test methods: 'acr', 'dcr', 'ccr', or 'p835', 'echo_impairment_test'")
    parser.add_argument("--clips", help="A csv containing urls of all clips to be rated in column 'pvs', in "
                                        "case of DCR it should also contain a column for 'src'")
    parser.add_argument("--gold_clips", help="A csv containing urls of all gold clips in column 'gold_clips_pvs' and "
                                             "their answer in column 'gold_clips_ans'. For DCR also 'gold_clips_src' "
                                             "is needed")
    parser.add_argument("--training_clips", help="A csv containing urls of all training clips to be rated in training "
                                                 "section. Columns 'training_pvs' and 'training_src' in case of DCR",
                        required=True)
    parser.add_argument("--trapping_clips", help="A csv containing urls of all trapping clips. Columns 'trapping_pvc'"
                                                 "and 'trapping_ans'. In case of DCR also 'trapping_src'")
    # check input arguments
    args = parser.parse_args()

    methods = ['acr', 'dcr', 'acr-hr', 'pc']
    test_method = args.method.lower()
    assert test_method in methods, f"No such a method supported, please select between {methods}"
    assert os.path.exists(args.cfg), f"No config file in {args.cfg}"
    assert os.path.exists(args.training_clips), f"No csv file containing training clips in {args.training_clips}"

    cfg = CP.ConfigParser()
    cfg._interpolation = CP.ExtendedInterpolation()
    cfg.read(args.cfg)

    if args.clips:
        assert os.path.exists(args.clips), f"No csv file containing clips in {args.clips}"
    elif cfg.has_option('RatingClips', 'RatingClipsConfigurations'):
        assert len(cfg['RatingClips']['RatingClipsConfigurations']) > 0, f"No cloud store for clips specified in config"
    else:
        assert True, "Neither clips file not cloud store provided for rating clips"

    if args.gold_clips:
        assert os.path.exists(args.gold_clips), f"No csv file containing gold clips in {args.gold_clips}"
    elif cfg.has_option('GoldenSample', 'Path'):
        assert len(cfg['GoldenSample']['Path']) > 0, "No golden clips store found"
    else:
        assert True, "Neither gold clips file nor store configuration provided"

    if args.trapping_clips:
        assert os.path.exists(args.trapping_clips), f"No csv file containing trapping  clips in {args.trapping_clips}"
    elif cfg.has_option('TrappingQuestions', 'Path'):
        assert len(cfg['TrappingQuestions']['Path']) > 0, "No golden clips store found"
    else:
        assert True, "Neither Trapping clips file nor store configuration provided"

    asyncio.run(main(cfg, test_method, args))