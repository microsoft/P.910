"""
/*---------------------------------------------------------------------------------------------
*  Copyright (c) Microsoft Corporation. All rights reserved.
*  Licensed under the MIT License. See License.txt in the project root for license information.
*--------------------------------------------------------------------------------------------*/
@author: Babak Naderi
"""

import csv
import statistics
from builtins import int

import math
import pandas as pd
import argparse
import os
import numpy as np
import sys
import re
from scipy import stats
from scipy.stats import spearmanr
import time
import itertools
import configparser as CP
import collections
import warnings

max_found_per_file = -1


def outliers_modified_z_score(votes):
    """
    return  outliers, using modified z-score
    :param votes:
    :return:
    """
    threshold = 3.5

    median_v = np.median(votes)
    median_absolute_deviation_v = np.median([np.abs(v - median_v) for v in votes])

    if median_absolute_deviation_v == 0:
        median_absolute_deviation_v = sys.float_info.min

    modified_z_scores = [np.abs(0.6745 * (v - median_v) / median_absolute_deviation_v)
                         for v in votes]
    x = np.array(modified_z_scores)
    v = np.array(votes)
    v = v[(x < threshold)]
    return v.tolist()

def outliers_iqr(votes):
    """
    Remove  outliers, using IRQ outlier detection method
    :param votes:
    :return:
    """
    if len(votes) < 2 or statistics.stdev(votes) == 0:
        return votes

    threshold = 1.5
    q75, q25 = np.percentile(votes, [75, 25])
    iqr = q75 - q25
    if iqr == 0:
        iqr = 0.7
    x = np.array(votes)
    v = np.array(votes)
    v = v[(x <= q75 + threshold * iqr) & (x >= q25 - threshold * iqr)]
    return v.tolist()

#todo add boxplot as well
def outliers_z_score(votes):
    """
    Remove  outliers, using z-score
    :param votes:
    :return:
    """
    if len(votes) < 2 or statistics.stdev(votes) == 0:
        return votes

    threshold = 3.29

    z = np.abs(stats.zscore(votes))
    x = np.array(z)
    v = np.array(votes)
    v = v[x < threshold]
    return v.tolist()


def check_if_session_accepted(data):
    """
    Check if the session can be accepted given the criteria in config
    Note: qualification and setup are skipped as they are checked in JS. Workers cannot continue if they do not pass.
    :param data:
    :return:
    """

    msg = "Make sure you follow the instruction:"
    accept = True
    failures = []

    if data['correct_matrix'] is not None and data['correct_matrix'] < \
            int(config['acceptance_criteria']['correct_matrix_bigger_equal']):
        accept = False
        msg += "Brightness test failed."
        failures.append('brightness_test')

    if data['correct_tps'] < int(config['acceptance_criteria']['correct_tps_bigger_equal']):
        accept = False
        msg += "Wrong answer to the Trapping clip(s);"
        failures.append('trapping_question')

    if 'gold_standard_bigger_equal' in config['acceptance_criteria'] and \
            data['correct_gold_question'] < int(config['acceptance_criteria']['gold_standard_bigger_equal']):
        accept = False
        msg += "Wrong answer to the Gold clip(s);"
        failures.append('gold_question')

    """
    if data['all_videos_played'] != int(config['acceptance_criteria']['all_video_played_equal']):
        accept = False
        msg += "All videos are not watched;"
        failures.append('all_videos_played')
    """
    if not accept:
        data['Reject'] = msg
    else:
        data['Reject'] = ""
    return accept, failures


def check_if_session_should_be_used(data):
    """
    Check if the session should be used or not. Only look at the sessions that are accepted.
    :param data:
    :return:
    """
    if data['accept'] != 1:
        return False, []
    
    should_be_used = True
    failures = []

    if data['variance_in_ratings'] < float(config['accept_and_use']['variance_bigger_equal']):
        should_be_used = False
        failures.append('variance')
    
    if 'correct_gold_question' in data and data['correct_gold_question'] < int(config['accept_and_use']['gold_standard_bigger_equal']):
        should_be_used = False
        failures.append('gold')

    if 'percent_over_play_duration' in data and data['percent_over_play_duration'] > float(config['accept_and_use']['viewing_duration_over']):
        should_be_used = False
        failures.append('viewing_duration')

    if 'correct_matrix_bigger_equal' in config['accept_and_use']:
        # for backward compatibility
        if data['correct_matrix'] is not None and data['correct_matrix'] < int(config['accept_and_use']['correct_matrix_bigger_equal']):
            should_be_used = False
            failures.append('correct_matrix_all')

    return should_be_used, failures


def check_video_played(row, method):
    """
    check if all videos for questions played until the end
    :param row:
    :param method: acr,dcr, ot ccr
    :return:
    """
    question_played = 0
    try:
        if method in ['acr', 'acr-hr', 'dcr', 'ccr']:
            for q_name in question_names:
                if int(row[f'answer.video_n_finish_{q_name}']) > 0:
                    question_played += 1
    except:
        return False
    return question_played == len(question_names)


def check_tps(row, method):
    """
    Check if the trapping clip(s) are answered correctly
    :param row:
    :param method: acr, dcr, or acr-hr
    :return:
    """
    correct_tps = 0
    tp_url = row[config['trapping']['url_found_in']]
    tp_correct_ans = [int(float(row[config['trapping']['ans_found_in']]))]
    try:
        suffix = ''
        for q_name in question_names:
            if tp_url in row[f'answer.{q_name}_url']:
                # found a trapping clips question
                given_ans = int(row[f'answer.{q_name}{suffix}'])
                if method == 'ccr' and row[f'answer.{q_name}_order'] == 'pr':
                    given_ans= given_ans * -1
                if given_ans in tp_correct_ans:
                    correct_tps = 1
                    return correct_tps
    except:
        pass
    return correct_tps


def check_variance(row, method):
    """
    Check how is variance of ratings in the session (to detect straightliners)
    :param row:
    :return:
    """
    r = []
    for q_name in question_names:
        if 'gold_question' in config and row[config['gold_question']['url_found_in']] in row[f'answer.{q_name}_url']:
            continue
        if 'trapping' in config and row[config['trapping']['url_found_in']] in row[f'answer.{q_name}_url']:
            continue
        try:
            if method == 'ccr':
                order = 1 if row[f'answer.{q_name}{question_name_suffix}_order'] == 'pr' else -1
                r.append(int(row[f'answer.{q_name}{question_name_suffix}']) * order)
            else:
                r.append(int(row[f'answer.{q_name}{question_name_suffix}']))
        except:
            pass
    try:
        v = statistics.variance(r) if len(r)> 1 else 1
        return v
    except:
        pass
    return -1


def check_gold_question(row, method):
    """
    Check if the gold_question is answered correctly
    :param row:
    :return:
    """
    correct_gq = 0
    try:
        gq_url = row[config['gold_question']['url_found_in']]
        # consider abs to support gold questions in ccr test        
        gq_correct_ans = int(float(row[config['gold_question']['ans_found_in']]))
        gq_var = int(float(config['gold_question']['variance']))

        for q_name in question_names:
            if gq_url in row[f'answer.{q_name}_url']:
                # found a gold standard question
                if int(row[f'answer.{q_name}']) in range(gq_correct_ans-gq_var, gq_correct_ans+gq_var+1):
                    correct_gq = 1
                    return correct_gq
    except Exception as e:
        print('Gold Question error: '+ e)
        return None
    return correct_gq


def check_matrix(row):
    """
    check if the matrix questions are answered correctly
    :param row:
    :return: number of correct answers
    """

    c1_correct = float(row['input.t1_matrix_c'])
    t1_correct = float(row['input.t1_matrix_t'])
    # it might be that answer of matrix1 is obfuscated
    if 'matrix_ans_obfuscated' in config['acceptance_criteria'] \
            and int(config['acceptance_criteria']['matrix_ans_obfuscated']) ==1:
        c1_correct -= 2
        t1_correct -= 3

    c2_correct = float(row['input.t2_matrix_c'])
    t2_correct = float(row['input.t2_matrix_t'])

    given_c1 = float(row['answer.t1_circles'])
    given_t1 = float(row['answer.t1_triangles'])

    given_c2 = float(row['answer.t2_circles'])
    given_t2 = float(row['answer.t2_triangles'])

    n_correct = 0

    if int(c1_correct) == int(given_c1) and int(t1_correct) == int(given_t1):
        n_correct += 1
    #else:
    #    print(f'wrong matrix 1: c1 {c1_correct},{given_c1} | t1 {t1_correct},{given_t1}')
    if int(c2_correct) == int(given_c2) and int(t2_correct) == int(given_t2):
        n_correct += 1
    #else:
    #    print(f'wrong matrix 2: c2 {c2_correct},{given_c2} | t2 {t2_correct},{given_t2}')
    return n_correct


def check_play_duration(row):
    """
    Check the ratio of play-back duration to clip duration
    :param row:
    :return: ration of play-back to clip
    """
    total_duration = sum(float(row[f'answer.video_duration_{q}']) for q in question_names)
    total_play_duration = sum(float(row[f'answer.video_play_duration_{q}']) for q in question_names)
    if total_duration == 0:
        return float('inf')
    return total_play_duration/total_duration


def data_cleaning(filename, method, wrong_vcodes):
   """
   Data screening process
   :param filename:
   :param method: acr, dcr, or ccr
   :return:
   """
   print('Start by Data Cleaning...')
   with open(filename, encoding="utf8") as csvfile:

    reader = csv.DictReader(csvfile)
    # lowercase the fieldnames
    reader.fieldnames = [field.strip().lower() for field in reader.fieldnames]

    worker_list = []
    use_sessions = []
    not_using_further_reasons = []
    not_accepted_reasons = []

   #"""
    failed_workers = []
   #in_df.sort_values(by=['answer.visual_acuity_result'], ascending=False, inplace=True)
   #"""
    for row in reader:
        setup_was_hidden = row['answer.cmp1'] is None or len(row['answer.cmp1'].strip()) == 0
        d = dict()

        d['worker_id'] = row['workerid']
        d['HITId'] = row['hitid']
        d['assignment'] = row['assignmentid']
        d['status'] = row['assignmentstatus']

        # step1. check if audio of all X questions are played at least once
        d['all_videos_played'] = 1 if check_video_played(row, method) else 0

        # check if setup was shown
        if setup_was_hidden:
            # the setup is not shown
            #d['correct_cmps'] = None
            d['correct_matrix'] = None
        else:
            # step2. check math
            d['correct_matrix'] = check_matrix(row)
        # step 4. check tps
        d['correct_tps'] = check_tps(row, method)
        # step5. check gold_standard,
        d['correct_gold_question']  = check_gold_question(row, method)

        # step6. check variance in a session rating
        d['variance_in_ratings'] = check_variance(row, method)

        d['percent_over_play_duration'] = check_play_duration(row)

        if 'answer.video_loading_duration_ms' in row:
            d['video_loading_duration'] = row['answer.video_loading_duration_ms']
            
        should_be_accepted, accept_failures = check_if_session_accepted(d)

        if should_be_accepted:
            d['accept'] = 1
            d['Approve'] = 'x'
        else:
            d['accept'] = 0
            d['Approve'] = ''
        not_accepted_reasons.extend(accept_failures)

        should_be_used, failures = check_if_session_should_be_used(d)
        d['failures'] = failures
        """
        #--------------------------
        failures = []
        #d['VAT'] = row['answer.visual_acuity_result']
        if should_be_used and float(d['video_load']) > 30000:
            should_be_used = True
            d['accept'] = 1
            #failed_workers.append(d['worker_id'])
        else:
            should_be_used = False
            d['accept'] = 0

        # --------------------------
        """
        not_using_further_reasons.extend(failures)

        if should_be_used:
            d['accept_and_use'] = 1
            use_sessions.append(row)
        else:
            d['accept_and_use'] = 0

        worker_list.append(d)

    report_file = os.path.splitext(filename)[0] + '_data_cleaning_report.csv'

    approved_file = os.path.splitext(filename)[0] + '_accept.csv'
    rejected_file = os.path.splitext(filename)[0] + '_rejection.csv'

    accept_reject_gui_file = os.path.splitext(filename)[0] + '_accept_reject_gui.csv'
    extending_hits_file = os.path.splitext(filename)[0] + '_extending.csv'
    block_list_file = os.path.splitext(filename)[0] + '_block_list.csv'

    print(f'{len(worker_list)} submissions are processed.')

    # reject hits when the user performed more than the limit
    worker_list = evaluate_maximum_hits(worker_list)
    # check rater_min_* criteria

    worker_list, use_sessions, num_rej_perform, block_list = evaluate_rater_performance(worker_list, use_sessions, True)
    worker_list, use_sessions, num_not_used_sub_perform, _ = evaluate_rater_performance(worker_list, use_sessions)
    #num_rej_perform = 0

    #worker_list = add_wrong_vcodes(worker_list, wrong_vcodes)
    accept_and_use_sessions = [d for d in worker_list if d['accept_and_use'] == 1]
    not_using_further_reasons = []
    for d in worker_list:
        if d['accept'] == 1 and d['accept_and_use'] == 0:
            not_using_further_reasons.extend(d['failures'])
    # cases with more than 5 wrong vcodes
    wrong_v_code_freq = check_wrong_vcode_should_block(wrong_vcodes)

    write_dict_as_csv(worker_list, report_file)
    save_approved_ones(worker_list, approved_file)
    save_rejected_ones(worker_list, rejected_file, wrong_vcodes, not_accepted_reasons, num_rej_perform)
    save_approve_rejected_ones_for_gui(worker_list, accept_reject_gui_file, wrong_vcodes)
    save_hits_to_be_extended(worker_list, extending_hits_file)

    if len(block_list) > 0:
        save_block_list(block_list, block_list_file, wrong_v_code_freq)
    not_used_reasons_list = list(collections.Counter(not_using_further_reasons).items())
    not_used_reasons_list.append(('performance', num_not_used_sub_perform))

    print(f"   {len(accept_and_use_sessions)} answers are good to be used further {not_used_reasons_list}")
    print(f"   Data cleaning report is saved in: {report_file}")
    tmp_path = os.path.splitext(filename)[0] + '_not_used_reasons.csv'
    with open(tmp_path, 'w') as fp:
        fp.write('\n'.join('%s, %s' % x for x in not_used_reasons_list))
    return worker_list, use_sessions


def evaluate_rater_performance(data, use_sessions, reject_on_failure=False):
    """
    Evaluate the workers performance based on the following criteria in cofnig file:
        rater_min_acceptance_rate_current_test
        rater_min_accepted_hits_current_test
    :param data:
    :param use_sessions:
    :param reject_on_failure: if True, check the criteria on [acceptance_criteria] otehrwise check it in the
    [accept_and_use] section of config file.
    :return:
    """
    section = 'acceptance_criteria' if reject_on_failure else 'accept_and_use'

    if ('rater_min_acceptance_rate_current_test' not in config[section]) \
            and ('rater_min_accepted_hits_current_test' not in config[section]):
        return data, use_sessions, 0, []

    df = pd.DataFrame(data)
    # rater_min_accepted_hits_current_test

    grouped = df.groupby(['worker_id', 'accept_and_use']).size().unstack(fill_value=0).reset_index()
    
    grouped = grouped.rename(columns={0: 'not_used_count', 1: 'used_count'})
    grouped['acceptance_rate'] = (grouped['used_count'] * 100)/(grouped['used_count'] + grouped['not_used_count'])
    grouped.to_csv('tmp.csv')

    if 'rater_min_acceptance_rate_current_test' in config[section]:
        rater_min_acceptance_rate_current_test = int(config[section]['rater_min_acceptance_rate_current_test'])
    else:
        rater_min_acceptance_rate_current_test = 0

    if 'rater_min_accepted_hits_current_test' in config[section]:
        rater_min_accepted_hits_current_test = int(config[section]['rater_min_accepted_hits_current_test'])
    else:
        rater_min_accepted_hits_current_test = 0

    grouped_rej = grouped[(grouped.acceptance_rate < rater_min_acceptance_rate_current_test)
                      | (grouped.used_count < rater_min_accepted_hits_current_test)]
    workers_list_to_remove = list(grouped_rej['worker_id'])

    result = []
    num_not_used_submissions = 0
    for d in data:
        if d['worker_id'] in workers_list_to_remove:
            d['accept_and_use'] = 0
            d['rater_performance_pass'] = 0
            num_not_used_submissions += 1
            if reject_on_failure:
                d['accept'] = 0
                d['Approve'] = ""
                tmp = grouped_rej[grouped_rej['worker_id'].str.contains(d['worker_id'])]
                if len(d['Reject'])>0:
                    d['Reject'] = d['Reject'] + f" Failed in performance criteria- only {tmp['acceptance_rate'].iloc[0]:.2f}% of submissions passed data cleansing."
                else:
                    d['Reject'] = f"Make sure you follow the instruction: Failed in performance criteria- only { tmp['acceptance_rate'].iloc[0]:.2f}% of submissions passed data cleansing."
        else:
            d['rater_performance_pass'] = 1
        result.append(d)

    u_session_update = []
    for us in use_sessions:
        if us['workerid'] not in workers_list_to_remove:
            u_session_update.append(us)

    block_list = []
    if 'block_rater_if_acceptance_and_used_rate_below' in config[section]:
        tmp = grouped[(grouped.acceptance_rate < int(config[section]['block_rater_if_acceptance_and_used_rate_below'])) &((grouped['used_count'] + grouped['not_used_count']) >=5)]
        block_list = list(tmp['worker_id'])

    return result, u_session_update, num_not_used_submissions, block_list


def evaluate_maximum_hits(data):
    """
    Check if worker performed more task than what is allowed
    :param data:
    :return:
    """
    df = pd.DataFrame(data)

    small_df = df[['worker_id']].copy()
    grouped = small_df.groupby(['worker_id']).size().reset_index(name='counts')
    grouped = grouped[grouped.counts > int(config['acceptance_criteria']['allowedMaxHITsInProject'])]
    # grouped.to_csv('out.csv')
    print(f"{len(grouped.index)} workers answered more than the allowedMaxHITsInProject"
          f"(>{config['acceptance_criteria']['allowedMaxHITsInProject']})")
    cheater_workers_list = list(grouped['worker_id'])

    cheater_workers_work_count = dict.fromkeys(cheater_workers_list, 0)
    result = []
    for d in data:
        if d['worker_id'] in cheater_workers_work_count:
            if cheater_workers_work_count[d['worker_id']] >= int(config['acceptance_criteria']['allowedMaxHITsInProject']):
                d['accept'] = 0
                d['Reject'] += f"More than allowed limit of {config['acceptance_criteria']['allowedMaxHITsInProject']}"
                d['accept_and_use'] = 0
                d['Approve'] = ''
            else:
                cheater_workers_work_count[d['worker_id']] += 1
        result.append(d)
    return result


def save_approve_rejected_ones_for_gui(data, path, wrong_vcodes):
    """
    save approved/rejected in a csv-file to be used in GUI
    :param data:
    :param path:
    :return:
    """
    df = pd.DataFrame(data)
    df = df[df.status == 'Submitted']
    small_df = df[['worker_id','assignment', 'HITId', 'Approve', 'Reject']].copy()
    small_df.rename(columns={'assignment': 'assignmentId', 'worker_id':'WorkerId'}, inplace=True)
    if wrong_vcodes is not None:
        wrong_vcodes_assignments = wrong_vcodes[['WorkerId','AssignmentId', 'HITId']].copy()
        wrong_vcodes_assignments["Approve"] = ""
        wrong_vcodes_assignments["Reject"] = "wrong verification code"
        wrong_vcodes_assignments.rename(columns={'AssignmentId': 'assignmentId'}, inplace=True)
        small_df = small_df.append(wrong_vcodes_assignments, ignore_index=True)
    small_df.to_csv(path, index=False)


def save_approved_ones(data, path):
    """
    save approved results in the given path
    :param data:
    :param path:
    :return:
    """
    df = pd.DataFrame(data)
    df = df[df.accept == 1]
    c_accepted = df.shape[0]
    df = df[df.status == 'Submitted']
    if df.shape[0] == c_accepted:
        print(f'    {c_accepted} answers are accepted')
    else:
        print(f'    overall {c_accepted} answers are accepted, from them {df.shape[0]} were in submitted status')
    small_df = df[['assignment']].copy()
    small_df.rename(columns={'assignment': 'assignmentId'}, inplace=True)
    small_df.to_csv(path, index=False)


def save_block_list(block_list, path, wrong_v_code_freq):
    """
    write the list of workers to be blocked in a csv file.
    :param block_list:
    :param path:
    :return:
    """
    df = pd.DataFrame(block_list, columns=['Worker ID'])
    df['UPDATE BlockStatus'] = "Block"
    df['BlockReason'] = f'Less than {config["acceptance_criteria"]["block_rater_if_acceptance_and_used_rate_below"]}% acceptance rate'

    if wrong_v_code_freq is not None and len(wrong_v_code_freq) > 0:
        df2 = pd.DataFrame(wrong_v_code_freq, columns=['Worker ID'])
        df2['UPDATE BlockStatus'] = "Block"
        df2['BlockReason'] = "Wrong verification code"
        # concat the two dataframes
        df = pd.concat([df, df2], ignore_index=True)
    df.to_csv(path, index=False)


def check_wrong_vcode_should_block(wrong_vcodes):
    if wrong_vcodes is None:
        return []       
    # count the number of wrong verification code per worker
    small_df = wrong_vcodes[['WorkerId']].copy()
    grouped = small_df.groupby(['WorkerId']).size().reset_index(name='counts')
    # get the workers that have more than 5 wrong verification code
    grouped = grouped[grouped.counts >= 5]
    print(f"{len(grouped.index)} workers have more than 5 wrong verification code")
    cheater_workers_list = list(grouped['WorkerId'])
    return cheater_workers_list



def save_rejected_ones(data, path, wrong_vcodes, not_accepted_reasons, num_rej_perform):
    """
    Save the rejected ones in the path
    :param data:
    :param path:
    :return:
    """
    df = pd.DataFrame(data)
    df = df[df.accept == 0]
    c_rejected = df.shape[0]
    if wrong_vcodes is not None:
        c_rejected += len(wrong_vcodes.index)
    df = df[df.status == 'Submitted']
    if df.shape[0] == c_rejected:
        print(f'    {c_rejected} answers are rejected')
    else:
        print(f'    overall {c_rejected} answers are rejected, from them {df.shape[0]} were in submitted status')

    not_accepted_reasons_list = list(collections.Counter(not_accepted_reasons).items())
    not_accepted_reasons_list.append(('Wrong Verification Code', len(wrong_vcodes.index)))
    if num_rej_perform != 0:
        not_accepted_reasons_list.append(('Performance', num_rej_perform))

    print(f'         Rejection reasons: {not_accepted_reasons_list}')

    small_df = df[['assignment', 'Reject']].copy()
    small_df.rename(columns={'assignment': 'assignmentId', 'Reject': 'feedback'}, inplace=True)
    if wrong_vcodes is not None:
        wrong_vcodes_assignments = wrong_vcodes[['AssignmentId']].copy()
        wrong_vcodes_assignments["feedback"] = "Wrong verificatioon code"
        wrong_vcodes_assignments.rename(columns={'AssignmentId': 'assignmentId'}, inplace=True)
        small_df = small_df.append(wrong_vcodes_assignments, ignore_index=True)
    small_df.to_csv(path, index=False)


def save_hits_to_be_extended(data, path):
    """
    Save the list of HITs that are accepted but not to be used. The list can be used to extend those hits
    :param data:
    :param path:
    :return:
    """
    df = pd.DataFrame(data)
    df = df[(df.accept == 1) & (df.accept_and_use == 0)]
    small_df = df[['HITId']].copy()
    grouped = small_df.groupby(['HITId']).size().reset_index(name='counts')
    grouped.rename(columns={'counts': 'n_extended_assignments'}, inplace=True)
    grouped.to_csv(path, index=False)


def filter_answer_by_status_and_workers(answer_df, all_time_worker_id_in, new_woker_id_in, status_in):
    """
    return answered who are in the specific status
    :param answer_df:
    :param all_time_worker_id_in:
    :param new_woker_id_in:
    :param status_in:
    :return:
    """

    frames = []
    if 'all' in status_in:
        # new_worker_id_in.extend(old_worker_id_in)
        answer_df = answer_df[answer_df['worker_id'].isin(all_time_worker_id_in)]
        return answer_df
    if 'submitted' in status_in:
        d1 = answer_df[answer_df['status'] == "Submitted"]
        d1 = d1[d1['worker_id'].isin(all_time_worker_id_in)]
        frames.append(d1)
        d2 = answer_df[answer_df['status'] != "Submitted"]
        d2 = d2[d2['worker_id'].isin(new_woker_id_in)]
        frames.append(d2)
        return pd.concat(frames)


def calc_quantity_bonuses(answer_list, conf, path):
    """
    Calculate the quantity bonuses given the configurations
    :param answer_list:
    :param conf:
    :param path:
    :return:
    """
    if path is not None:
        print('Calculate the quantity bonuses...')
    df = pd.DataFrame(answer_list)

    old_answers = df[df['status'] != "Submitted"]
    grouped = df.groupby(['worker_id'], as_index=False)['accept'].sum()
    old_answers_grouped = old_answers.groupby(['worker_id'], as_index=False)['accept'].sum()

    # condition more than 30 hits
    grouped = grouped[grouped.accept >= int(config['bonus']['quantity_hits_more_than'])]
    old_answers_grouped = old_answers_grouped[old_answers_grouped.accept >= int(config['bonus']['quantity_hits_more_than'])]

    old_eligible = list(old_answers_grouped['worker_id'])
    eligible_all = list(grouped['worker_id'])
    new_eligible = list(set(eligible_all)-set(old_eligible))

    # the bonus should be given to the tasks that are either automatically accepted or submited. The one with status
    # accepted should have been already payed.
    filtered_answers = filter_answer_by_status_and_workers(df, eligible_all, new_eligible, conf)
    # could be also accept_and_use
    grouped = filtered_answers.groupby(['worker_id'], as_index=False)['accept'].sum()
    grouped['bonusAmount'] = grouped['accept']*float(config['bonus']['quantity_bonus'])

    # now find an assignment id
    df.drop_duplicates('worker_id', keep='first', inplace=True)
    w_ids = list(dict(grouped['worker_id']).values())
    df = df[df.isin(w_ids).worker_id]
    small_df = df[['worker_id', 'assignment']].copy()
    merged = pd.merge(grouped, small_df, how='inner', left_on='worker_id', right_on='worker_id')
    merged.rename(columns={'worker_id': 'workerId', 'assignment': 'assignmentId'}, inplace=True)

    merged['reason'] = f'Well done! More than {config["bonus"]["quantity_hits_more_than"]} accepted submissions.'
    merged = merged.round({'bonusAmount': 2})

    if path is not None:
        merged.to_csv(path, index=False)
        print(f'   Quantity bonuses report is saved in: {path}')
    return merged


def calc_inter_rater_reliability(answer_list, overall_mos, test_method, use_condition_level):
    """
    Calculate the inter_rater reliability for all workers and also average for the study
    :param answer_list:
    :param overall_mos:
    :return:
    """
    mos_name = method_to_mos[f"{test_method}{question_name_suffix}"]

    reliability_list = []
    df = pd.DataFrame(answer_list)
    tmp = pd.DataFrame(overall_mos)
    if use_condition_level:
        aggregate_on = 'condition_name'
    else:
        aggregate_on = 'file_url'
    c_df = tmp[[aggregate_on, mos_name]].copy()
    c_df.rename(columns={mos_name: 'mos'}, inplace=True)

    candidates = df['workerid'].unique().tolist()

    for worker in candidates:
        # select answers
        worker_answers = df[df['workerid'] == worker]
        votes_p_file, votes_per_condition, _ = transform(test_method, worker_answers.to_dict('records'),
                                                         use_condition_level, True)
        aggregated_data = pd.DataFrame(votes_per_condition if use_condition_level else votes_p_file)

        if len(aggregated_data) > 0:
            merged = pd.merge(aggregated_data, c_df, how='inner', left_on=aggregate_on, right_on=aggregate_on)
            r = calc_correlation(merged["mos"].tolist(), merged[mos_name].tolist())
        else:
            r = 0
        entry = {'workerId': worker, 'r': r}
        reliability_list.append(entry)
    irr = pd.DataFrame(reliability_list)
    return irr, irr['r'].mean()


def calc_quality_bonuses(quantity_bonus_result, answer_list, overall_mos, conf, path, n_workers, test_method, use_condition_level):
    """
    Calculate the quality bonuses given the configurations
    :param quantity_bonus_result:
    :param answer_list:
    :param overall_mos:
    :param conf:
    :param path:
    :param test_method:
    :param use_condition_level: if true the condition level aggregation will be used otherwise file level
    :return:
    """

    print('Calculate the quality bonuses...')
    max_workers = int(n_workers * int(conf['bonus']['quality_top_percentage']) / 100)
    eligible_df, _ = calc_inter_rater_reliability(answer_list, overall_mos, test_method, use_condition_level)

    if len(eligible_df.index) > 0:
        eligible_df = eligible_df[eligible_df['r'] >= float(conf['bonus']['quality_min_pcc'])]
        eligible_df = eligible_df.sort_values(by=['r'], ascending=False)

        merged = pd.merge(eligible_df, quantity_bonus_result, how='inner', left_on='workerId', right_on='workerId')
        smaller_df = merged[['workerId', 'r', 'accept', 'assignmentId']].copy()
        smaller_df['bonusAmount'] = smaller_df['accept'] * float(config['bonus']['quality_bonus'])

        smaller_df = smaller_df.round({'bonusAmount': 2})
        smaller_df['reason'] = f'Well done! You belong to top {conf["bonus"]["quality_top_percentage"]}%.'
    else:
        smaller_df = pd.DataFrame(columns=['workerId',	'r', 'accept', 'assignmentId', 	'bonusAmount', 'reason'])
    smaller_df.head(max_workers).to_csv(path, index=False)
    print(f'   Quality bonuses report is saved in: {path}')


def write_dict_as_csv(dic_to_write, file_name, *args, **kwargs):
    """
    utility function to write a dict object in a csv file
    :param dic_to_write:
    :param file_name:
    :return:
    """
    headers = kwargs.get('headers', None)
    with open(file_name, 'w', newline='') as output_file:
        if headers is None:
            if len(dic_to_write) > 0:
                headers = list(dic_to_write[0].keys())
            else:
                headers = []
        writer = csv.DictWriter(output_file, fieldnames=headers)
        writer.writeheader()
        for d in dic_to_write:
            writer.writerow(d)


file_to_condition_map = {}


def conv_filename_to_condition(f_name):
    """
    extract the condition name from filename given the mask in the config
    :param f_name:
    :return:
    """
    if f_name in file_to_condition_map:
        return file_to_condition_map[f_name]
    file_to_condition_map[f_name] = {'Unknown': 'NoCondition' }
    pattern = ''
    if config.has_option('general','condition_pattern'):
        pattern = config['general']['condition_pattern']
    m = re.match(pattern, f_name)
    if m:
        file_to_condition_map[f_name] = m.groupdict('')

    return file_to_condition_map[f_name]


def dict_value_to_key(d, value):
    """
    Utility function to key for a given value inside the dic
    :param d:
    :param value:
    :return:
    """
    for k, v in d.items():
        if v == value:
            return k
    return None


method_to_mos = {
    "acr": 'MOS',
    "dcr": 'DMOS',
    "acr-hr": 'MOS',
    'ccr': 'CMOS'
}

question_names = []
question_name_suffix = ''
create_per_worker = True
pvs_src_map = {}


def transform(test_method, sessions, agrregate_on_condition, is_worker_specific):
    """
    Given the valid sessions from answer.csv, group votes per files, and per conditions.
    Assumption: file name contains the condition name/number, which can be extracted using "condition_patten" .
    :param sessions:
    :return:
    """
    data_per_file = {}
    global max_found_per_file
    global file_to_condition_map
    global pvs_src_map
    file_to_condition_map ={}
    data_per_condition = {}
    data_per_worker = []
    mos_name = method_to_mos[f"{test_method}{question_name_suffix}"]

    input_question_names = [f"q{i}" for i in range(0, int(config['general']['number_of_questions_in_rating']))]
    if test_method == 'acr-hr':
        for session in sessions:
            for question in input_question_names:
                if f'input.{question}_r' in session:
                    pvs_src_map[session[f'input.{question}']] = session[f'input.{question}_r']

    for session in sessions:
        found_gold_question = False
        for question in question_names:
            # is it a trapping clips question
            if 'trapping' in config and session[config['trapping']['url_found_in']] == session[f'answer.{question}_url']:
                continue
            # is it a gold clips            
            if not found_gold_question and\
                    session[config['gold_question']['url_found_in']] == session[f'answer.{question}_url']:
                found_gold_question = True
                continue            
            short_file_name = session[f'answer.{question}_url'].rsplit('/', 1)[-1]
            file_name = session[f'answer.{question}_url']
            if file_name not in data_per_file:
                data_per_file[file_name] = []
            votes = data_per_file[file_name]
            try:
                votes.append(int(session[f'answer.{question}{question_name_suffix}']))
                cond =conv_filename_to_condition(file_name)
                tmp = {'HITId': session['hitid'],
                    'workerid': session['workerid'],
                        'file':file_name,
                       'short_file_name': file_name.rsplit('/', 1)[-1],
                        'vote': int(session[f'answer.{question}{question_name_suffix}'])}

                tmp.update(cond)
                data_per_worker.append(tmp)
            except Exception as err:
                print(err)
                pass
    # convert the format: one row per file
    group_per_file = []
    condition_detail = {}
    outlier_removed_count = 0
    for key in data_per_file.keys():
        tmp = dict()
        votes = data_per_file[key]
        vote_counter = 1
        # outlier removal per file
        if (not (is_worker_specific) and 'outlier_removal' in config['accept_and_use']) \
                and (config['accept_and_use']['outlier_removal'].lower() in ['true', '1', 't', 'y', 'yes']):

            v_len = len(votes)
            if v_len >5:
                #votes = outliers_z_score(votes)
                votes = outliers_iqr(votes)
            v_len_after = len(votes)
            if v_len != v_len_after:
                #print(f'{v_len - v_len_after} removed ({key})')
                outlier_removed_count += v_len - v_len_after

        # extra step:: add votes to the per-condition dict
        tmp_n = conv_filename_to_condition(key)
        if agrregate_on_condition:
            condition_keys = config['general']['condition_keys'].split(',')
            condition_keys.append('Unknown')
            condition_dict = {k: tmp_n[k] for k in tmp_n.keys() & condition_keys}
            tmp = condition_dict.copy()
            condition_dict = collections.OrderedDict(sorted(condition_dict.items()))
            for num_combinations in range(len(condition_dict)):
                combinations = list(itertools.combinations(condition_dict.values(), num_combinations + 1))
                for combination in combinations:
                    condition = '____'.join(combination).strip('_')
                    if condition not in data_per_condition:
                        data_per_condition[condition]=[]
                        pattern_dic ={dict_value_to_key(condition_dict, v): v for v in combination}
                        for k in condition_dict.keys():
                            if k not in pattern_dic:
                                pattern_dic[k] = ""
                        condition_detail[condition] = pattern_dic

                    data_per_condition[condition].extend(votes)

        else:
            condition = 'Overall'
            if condition not in data_per_condition:
                data_per_condition[condition] = []
            data_per_condition[condition].extend(votes)

        tmp['file_url'] = key
        tmp['short_file_name'] = key.rsplit('/', 1)[-1]
        for vote in votes:
            tmp[f'vote_{vote_counter}'] = vote
            vote_counter += 1
        count = vote_counter

        tmp['n'] = count-1
        # tmp[mos_name] = abs(statistics.mean(votes))
        tmp[mos_name] = statistics.mean(votes)
        if tmp['n'] > 1:
            tmp[f'std{question_name_suffix}'] = statistics.stdev(votes)
            tmp[f'95%CI{question_name_suffix}'] = (1.96 * tmp[f'std{question_name_suffix}']) / math.sqrt(tmp['n'])
        else:
            tmp[f'std{question_name_suffix}'] = None
            tmp[f'95%CI{question_name_suffix}'] = None
        if tmp['n'] > max_found_per_file:
            max_found_per_file = tmp['n']
        group_per_file.append(tmp)
    if outlier_removed_count != 0:
        print(f'  Overall {outlier_removed_count} outliers are removed in per file aggregation.')
    # convert the format: one row per condition
    group_per_condition = []
    outlier_removed_count = 0
    if agrregate_on_condition:
        for key in data_per_condition.keys():
            tmp = dict()
            tmp['condition_name'] = key
            votes = data_per_condition[key]
            # apply z-score outlier detection
            if (not(is_worker_specific) and 'outlier_removal' in config['accept_and_use']) \
                    and (config['accept_and_use']['outlier_removal'].lower() in ['true', '1', 't', 'y', 'yes']):
                v_len = len(votes)
                #votes = outliers_z_score(votes)
                votes = outliers_iqr(votes)                
                v_len_after = len(votes)
                if v_len != v_len_after:
                    outlier_removed_count += v_len-v_len_after
            tmp = {**tmp, **condition_detail[key]}
            tmp['n'] = len(votes)
            if tmp['n'] > 0:
                # tmp[mos_name] = abs(statistics.mean(votes))
                tmp[mos_name] = statistics.mean(votes)
            else:
                tmp[mos_name] = None
            if tmp['n'] > 1:
                tmp[f'std{question_name_suffix}'] = statistics.stdev(votes)
                tmp[f'95%CI{question_name_suffix}'] = (1.96 * tmp[f'std{question_name_suffix}']) / math.sqrt(tmp['n'])
            else:
                tmp[f'std{question_name_suffix}'] = None
                tmp[f'95%CI{question_name_suffix}'] = None

            group_per_condition.append(tmp)
        if outlier_removed_count != 0:
            print(f'  Overall {outlier_removed_count} outliers are removed in per condition aggregation.')
    return group_per_file, group_per_condition, data_per_worker


def create_headers_for_per_file_report(test_method, condition_keys):
    """
    add default values in the dict
    :param d:
    :return:
    """
    mos_name = method_to_mos[f"{test_method}{question_name_suffix}"]
    header = ['file_url', 'n', mos_name, 'std', '95%CI', 'short_file_name'] + condition_keys
    max_votes = max_found_per_file
    if max_votes == -1:
        max_votes = int(config['general']['expected_votes_per_file'])
    for i in range(1, max_votes+1):
        header.append(f'vote_{i}')

    return header


def calc_payment_stat(df):
    """
    Calculate the statistics for payments
    :param df:
    :return:
    """
    if 'Answer.time_page_hidden_sec' in df.columns:
        df['Answer.time_page_hidden_sec'].where(df['Answer.time_page_hidden_sec'] < 3600, 0, inplace=True)
        df['time_diff'] = df["work_duration_sec"] - df['Answer.time_page_hidden_sec']
        median_time_in_sec = df["time_diff"].median()
    else:
        median_time_in_sec = df["work_duration_sec"].median()
    payment_text = df['Reward'].values[0]
    paymnet = re.findall("\d+\.\d+", payment_text)

    avg_pay = 3600*float(paymnet[0])/median_time_in_sec
    formatted_time = time.strftime("%M:%S", time.gmtime(median_time_in_sec))

    return formatted_time, avg_pay


def calc_stats(input_file):
    """
    calc the statistics considering the time worker spend
    :param input_file:
    :return:
    """
    df = pd.read_csv(input_file, low_memory=False)
    df_full = df.copy()
    overall_time, overall_pay = calc_payment_stat(df)

    # full study, all sections were shown
    df_full = df_full[~df_full['Answer.2_birth_year'].isna()]
    full_time, full_pay = calc_payment_stat(df_full)

    # no qual
    df_no_qual = df[df['Answer.2_birth_year'].isna()]
    df_no_qual_no_setup = df_no_qual[df_no_qual['Answer.t1_circles'].isna()]
    only_rating = df_no_qual_no_setup[df_no_qual_no_setup['Answer.t1'].isna()].copy()

    if len(only_rating)>0:
        only_r_time, only_r_pay = calc_payment_stat(only_rating)
    else:
        only_r_time = 'No-case'
        only_r_pay = 'No-case'
    data = {'Case': ['All submissions', 'All sections', 'Only rating'],
            'Percent of submissions': [1, len(df_full.index)/len(df.index), len(only_rating.index)/len(df.index)],
            'Work duration (median) MM:SS': [overall_time, full_time, only_r_time ],
            'payment per hour ($)': [overall_pay, full_pay, only_r_pay]}
    stat = pd.DataFrame.from_dict(data)
    print('Payment statistics:')
    print(stat.to_string(index=False))


def calc_correlation(cs, lab):
    """
    calc the spearman's correlation
    :param cs:
    :param lab:
    :return:
    """
    rho, pval = spearmanr(cs, lab)
    return rho


def number_of_unique_workers(answers, used):
    """
    return numbe rof unique workers
    :param answers:
    :return:
    """
    df = pd.DataFrame(answers)
    df.drop_duplicates('worker_id', keep='first', inplace=True)

    df_used = pd.DataFrame(used)
    df_used.drop_duplicates('workerid', keep='first', inplace=True)
    return len(df), len(df_used)

def recover_submission_withoiut_matching_vcode(hit_ans, amt_ans, not_in_hitapp):
    # iterate over daraftame
    for index, row in not_in_hitapp.iterrows(): 
        # find the matching row in amt
        amt_row = amt_ans[amt_ans['AssignmentId'] == row['Answer.hitapp_assignmentId']]
        if len(amt_row) == 1:
            # add the row to the hitapp
            print('Find a potential match for a wrong vcode submission (internal assignment id: ' + row['Answer.hitapp_assignmentId'] + ')')

def combine_amt_hit_server(amt_ans_path, hitapp_ans_path):
    """
    Combine the answers from the AMT and the HIT_APP Server
    :param amt_ans_path:
    :param hitapp_ans_path:
    :return:
    """
    amt_ans = pd.read_csv(amt_ans_path, low_memory=False)
    hitapp_ans = pd.read_csv(hitapp_ans_path, low_memory=False)

    columns_to_remove = amt_ans.columns.difference(['WorkerId', 'Answer.v_code', 'HITId',
                                             'HITTypeId', 'AssignmentId', 'WorkTimeInSeconds',
                                             'Reward', 'Answer.hitapp_assignmentId'])
    amt_ans.drop(columns=columns_to_remove, inplace=True)
    hitapp_ans.rename(columns={"WorkerId": "hitapp_workerid",
                               "AssignmentId": "hitapp_assignmentid",
                               "HITId": "hitapp_hitid",
                               "HITTypeId": "hitapp_hittypeid"},  inplace=True)
    # remove stript vcodes entered by workers
    amt_ans['Answer.v_code'] = amt_ans['Answer.v_code'].str.strip()
    # check if there are submission without conuter part key in hitapp servers
    not_in_hitapp = amt_ans[~amt_ans['Answer.v_code'].isin(hitapp_ans.v_code)]
    recover_submission_withoiut_matching_vcode(hitapp_ans, amt_ans, not_in_hitapp)
    merged = pd.merge(hitapp_ans, amt_ans, left_on='v_code', right_on='Answer.v_code')

    columns_to_remove = ['Answer.v_code']
    if "work_duration_sec" not in merged.columns:
        merged.rename(columns={"WorkTimeInSeconds": "work_duration_sec"}, inplace=True)
    else:
        columns_to_remove.append("WorkTimeInSeconds")
    merged.drop(columns=columns_to_remove, inplace=True)

    merged_ans_path = os.path.splitext(hitapp_ans_path)[0] + '_merged.csv'
    merged.to_csv(merged_ans_path, index=False)
    #todo: check if the assignment ids are also equal
    return merged_ans_path, not_in_hitapp


def add_dmos_acrhr(agg_per_file_path, cfg):
    """
    Calculate the DMOS values for ACR-HR test
    :param agg_per_file_path:
    :param cfg:
    :return:
    """
    global pvs_src_map
    df = pd.DataFrame({'keys':pvs_src_map.keys() ,'val':pvs_src_map.values()})
    df.to_csv(agg_per_file_path.replace('.csv', '_dict.csv'), index=False)
    per_file = pd.read_csv(agg_per_file_path, low_memory=False)
    mos_dict = dict(zip(per_file.file_url, per_file.MOS))
    dmos_list = []
    scale_max = int(cfg['general']['scale'])

    for index, row in per_file.iterrows():
        mos_ref = mos_dict[pvs_src_map[row['file_url']]]
        mos_pvs = mos_dict[row['file_url']]
        dmos = min([mos_pvs - mos_ref + scale_max, scale_max])
        dmos_list.append(dmos)

    per_file = per_file.assign(DMOS=dmos_list)
    per_file.to_csv(agg_per_file_path, index=False)


def analyze_results(config, test_method, answer_path, amt_ans_path,  list_of_req, quality_bonus):
    """
    main method for calculating the results
    :param config:
    :param test_method:
    :param answer_path:
    :param list_of_req:
    :param quality_bonus:
    :return:
    """
    global question_name_suffix

    suffixes = ['']
    wrong_v_code = None
    if amt_ans_path:
        answer_path, wrong_v_code = combine_amt_hit_server(amt_ans_path, answer_path)
    full_data, accepted_sessions = data_cleaning(answer_path, test_method, wrong_v_code)

    n_workers, n_workers_used = number_of_unique_workers(full_data, accepted_sessions)
    print(f"{n_workers} workers participated in this batch, answers of {n_workers_used} are used.")
    # disabled becuase of the HITAPP_server
    calc_stats(answer_path)
    # votes_per_file, votes_per_condition = transform(accepted_sessions)
    if len(accepted_sessions) > 1:
        condition_set = []
        for suffix in suffixes:
            question_name_suffix = suffix
            print("Transforming data (the ones with 'accepted_and_use' ==1 --> group per clip")
            use_condition_level = config.has_option('general', 'condition_pattern')

            votes_per_file, vote_per_condition, data_per_worker = transform(test_method, accepted_sessions,
                                                           config.has_option('general', 'condition_pattern'), False)

            votes_per_file_path = os.path.splitext(answer_path)[0] + f'_votes_per_clip{question_name_suffix}.csv'
            votes_per_cond_path = os.path.splitext(answer_path)[0] + f'_votes_per_cond{question_name_suffix}.csv'

            condition_keys = []
            if config.has_option('general', 'condition_pattern'):
                condition_keys = config['general']['condition_keys'].split(',')
                votes_per_file = sorted(votes_per_file, key=lambda i: i[condition_keys[0]])
                condition_keys.append('Unknown')
            headers = create_headers_for_per_file_report(test_method, condition_keys)
            write_dict_as_csv(votes_per_file, votes_per_file_path, headers=headers)
            print(f'   Votes per files are saved in: {votes_per_file_path}')

            if test_method in ['acr-hr']:
                add_dmos_acrhr(votes_per_file_path, config)

            if use_condition_level:
                vote_per_condition = sorted(vote_per_condition, key=lambda i: i['condition_name'])
                write_dict_as_csv(vote_per_condition, votes_per_cond_path)
                print(f'   Votes per files are saved in: {votes_per_cond_path}')
                condition_set.append(pd.DataFrame(vote_per_condition))
            if create_per_worker:
                write_dict_as_csv(data_per_worker, os.path.splitext(answer_path)[0] + f'_votes_per_worker{question_name_suffix}.csv')


        bonus_file = os.path.splitext(answer_path)[0] + '_quantity_bonus_report.csv'
        quantity_bonus_df = calc_quantity_bonuses(full_data, list_of_req, bonus_file)

        if quality_bonus:
            quality_bonus_path = os.path.splitext(answer_path)[0] + '_quality_bonus_report.csv'
            if 'all' not in list_of_req:
                quantity_bonus_df = calc_quantity_bonuses(full_data, ['all'], None)
            if use_condition_level:
                votes_to_use = vote_per_condition
            else:
                votes_to_use = votes_per_file
            calc_quality_bonuses(quantity_bonus_df, accepted_sessions, votes_to_use, config, quality_bonus_path,
                                 n_workers, test_method, use_condition_level)

        inter_rate_reliability, avg_irr = calc_inter_rater_reliability( accepted_sessions, votes_to_use, test_method,
                                                                         use_condition_level)
        irr_path = os.path.splitext(answer_path)[0] + '_irr_report.csv'
        inter_rate_reliability.to_csv(irr_path, index=False)

        if "min_inter_rater_reliability" in config['accept_and_use'] and \
                avg_irr < float(config['accept_and_use']['min_inter_rater_reliability']):
            text = f"Warning: Average Inter-rater reliability of this study {avg_irr:.3f} is below threshold. " \
                f"It is highly possible that many unreliable ratings are included."
        else:
            text = f"Average Inter-rater reliability of study: {avg_irr:.3f}"

        print(text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Utility script to evaluate answers to the pcrowd batch')
    # Configuration: read it from mturk.cfg
    parser.add_argument("--cfg", required=True,
                        help="Contains the configurations see acr_result_parser.cfg as an example")
    parser.add_argument("--method", required=True,
                        help="one of the test methods: 'acr','acr-hr', 'dcr', 'ccr'")
    parser.add_argument("--answers", required=True,
                        help="Answers csv file from HIT App Server, path relative to current directory")
    parser.add_argument("--amt_answers",
                        help="Answers csv file from AMT, path relative to current directory")

    parser.add_argument('--quantity_bonus', help="specify status of answers which should be counted when calculating "
                                                " the amount of quantity bonus. All answers will be used to check "
                                                "eligibility of worker, but those with the selected status here will "
                                                "be used to calculate the amount of bonus. A comma separated list:"
                                                " all|submitted. Default: submitted",
                        default="submitted")

    parser.add_argument('--quality_bonus', help="Quality bonus will be calculated. Just use it with your final download"
                                                " of answers and when the project is completed", action="store_true")
    args = parser.parse_args()
    methods = ['dcr', 'acr', 'acr-hr', 'ccr']
    test_method = args.method.lower()
    assert test_method in methods, f"No such a method supported, please select between {methods} "

    cfg_path = args.cfg
    assert os.path.exists(cfg_path), f"No configuration file at [{cfg_path}]"
    config = CP.ConfigParser()
    config.read(cfg_path)

    assert (args.answers is not None), f"--answers  are required]"
    # answer_path = os.path.join(os.path.dirname(__file__), args.answers)
    answer_path = args.answers

    if args.amt_answers is None:
        warnings.warn("No AMT answer is provided with --amt_answers. That means the WorkerId, HITIds, ect. are internal "
                      "HIT APP server ids. Therefore bonus reports cannot be used. ")
        amt_ans_path = None
    else:
        amt_ans_path = args.amt_answers

    assert os.path.exists(answer_path), f"No input file found in [{answer_path}]"
    list_of_possible_status = ['all', 'submitted']

    list_of_req = args.quantity_bonus.lower().split(',')
    for req in list_of_req:
        assert req.strip() in list_of_possible_status, f"unknown status {req} used in --quantity_bonus"

    np.seterr(divide='ignore', invalid='ignore')
    question_names = [f"q{i}" for i in range(1, int(config['general']['number_of_questions_in_rating']) + 1)]
    # start
    analyze_results(config, test_method,  answer_path, amt_ans_path,  list_of_req, args.quality_bonus)
