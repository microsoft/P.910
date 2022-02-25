"""
/*---------------------------------------------------------------------------------------------
*  Copyright (c) Microsoft Corporation. All rights reserved.
*  Licensed under the MIT License. See License.txt in the project root for license information.
*--------------------------------------------------------------------------------------------*/
@author: Babak Naderi
"""

import argparse
import boto3
import json
import os
import configparser as CP
import csv
import xml.etree.ElementTree as ET
import re
import random
import botocore
import statistics


def send_message(client, cfg):
    """
    Sends an email to list of workers given the worker ids.
    Configuration should be set in section "send_emaiil" in the mturk.cfg file
    :param client: boto3 client object for communicating to MTurk
    :param cfg: configuration file with section "send_emaiil"
    :return:
    """

    worker_ids = cfg['worker_ids'].replace(' ', '').split(',')
    # in each call it is possible to send up to 100 messages
    worker_pack_size = 100
    chunked_worker_ids = [worker_ids[i:i + worker_pack_size] for i in range(0, len(worker_ids), worker_pack_size)]
    count = 1
    success_messages = 0
    failed_group=[]
    for woker_group in chunked_worker_ids:
        response = client.notify_workers(
                 Subject=cfg['subject'],
                 MessageText=cfg['message'],
                 WorkerIds=woker_group
         )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            print (f"Group {count}: sending message... Success" )
            success_messages += len(woker_group)
        else:
            failed_group.extend(woker_group)
            print(f"Group {count}: sending message... Failed")
        count += 1
    print(f"{success_messages} emails sent successfully")


def extend_hits(client, file_path):
    """
        Extending the given HIT by increasing the maximum number of assignments of an existing HIT.
        :param client: boto3 client object for communicating to MTurk
        :param file_path: list of HITs to be extended with number of extra assigned per HIT
    """
    with open(file_path, mode='r') as hit_list:
        reader = csv.DictReader(hit_list)
        line_count = 0
        success = 0
        failed = 0
        for row in reader:
            try:
                if line_count == 0:
                    assert 'HITId' in row, f"No column found with name 'HITId' in [{hit_list}]"
                    assert 'n_extended_assignments' in row, f"No column found with name 'n_extended_assignments' " \
                        f"in [{hit_list}]"
                else:
                    line_count =  line_count +1


                response = client.create_additional_assignments_for_hit(
                    HITId=row["HITId"],
                    NumberOfAdditionalAssignments=int(row["n_extended_assignments"]),
                    UniqueRequestToken=f'extend_hits_{row["HITId"]}_{row["n_extended_assignments"]}'
                )
                success = success + 1
            except Exception as ex:
                print(f'   - Error HIT: {row["HITId"]} can not be extended by {row["n_extended_assignments"]}.'
                      f' msg:{str(ex)}')
                failed = failed + 1
        print(f' ')
        print(f'{success} HITs are extended, {failed} are failed to extend.')
        print(f' ')
        print(f'Use "python mturk_utils.py --cfg YOUR_CFG --extended_hits_status {file_path}" to see the status of new assignments.')


def extended_hits_report(client, file_path):
    """
        Create a report on how many assignments are pending.
        :param client: boto3 client object for communicating to MTurk
        :param file_path: list of HITs to be extended with number of extra assigned per HIT
    """
    with open(file_path, mode='r') as hit_list:
        reader = csv.DictReader(hit_list)
        pending = 0
        available = 0
        line_count = 0
        requested = 0
        print('Start creating a report...')
        for row in reader:
            try:
                if line_count == 0:
                    assert 'HITId' in row, f"No column found with name 'HITId' in [{hit_list}]"
                    assert 'n_extended_assignments' in row, f"No column found with name 'n_extended_assignments' " \
                        f"in [{hit_list}]"
                else:
                    line_count = line_count + 1
                response = client.get_hit(
                    HITId=row["HITId"]
                )
                pending = pending + response["HIT"]["NumberOfAssignmentsPending"]
                available = available + response["HIT"]["NumberOfAssignmentsAvailable"]
                requested = requested + int(row["n_extended_assignments"])
            except Exception as e:
                print(f'Error HIT: cannot get the status of {row["HITId"]}.'
                      f' msg:{str(e)}')
                pass
        print(f'From {requested} extended assignments, {available} are available for workers, and {pending} are pending.'
              f' {requested-(available+pending)} should be completed (assuming all extensions were successful). ')


def assign_bonus(client, bonus_list_path):
    """
    Assign bonuses to group of workers.
    A csv file with following columns need to be provided: workerId, assignmentId, bonusAmount, reason
    :param client: boto3 client object for communicating to MTurk
    :param bonus_list_path: path to the csv file with following columns:workerId, assignmentId, bonusAmount, reason
    :return:
    """
    print('Sending bonuses...')
    with open(bonus_list_path, 'r') as bonus_list:
        entries = list(csv.DictReader(bonus_list))

    bonus_amounts = [float(entry['bonusAmount']) for entry in entries]
    num_bonus_workers = len(bonus_amounts)
    total_bonus = round(sum(bonus_amounts), 2)
    max_bonus = max(bonus_amounts)
    mean_bonus = round(total_bonus / num_bonus_workers, 2)
    median_bonus = statistics.median(bonus_amounts)

    print(f'Number of workers: {num_bonus_workers}, total: {total_bonus}, max: {max_bonus}, mean: {mean_bonus}, median: {median_bonus}')
    proceed = input('Proceed (y/N)?: ')
    if len(proceed) > 0 and proceed.lower() not in ['y', 'n']:
        exit(f'Unknown value "{proceed}"')
    if len(proceed) == 0 or proceed.lower() == 'n':
        exit()

    failed = 0
    for row in entries:
        assert 'workerId' in row
        assert 'assignmentId' in row
        assert 'bonusAmount' in row
        assert 'reason' in row

        response = client.send_bonus(
            WorkerId=row['workerId'],
            BonusAmount=row['bonusAmount'],
            AssignmentId=row['assignmentId'],
            Reason=row['reason']
        )

        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            print(f'Failed to send for {row}')
            failed += 1

    print(f'Bonuses sent, failed {failed}, succeeded {num_bonus_workers - failed}')        


def approve_reject_assignments_together(client, assignment_path):
    """
    Assign bonuses to group of workers.
    A csv file with following columns need to be provided: workerId, assignmentId, bonusAmount, reason
    :param client: boto3 client object for communicating to MTurk
    :param assignment_path: path to the csv file with: workerId, assignmentId, bonusAmount, reason
    :param approve: boolean when false the script reject answers
    :return:
    """

    print('Approving/Rejecting assignments')
    with open(assignment_path, mode='r') as assignment_list:
        reader = csv.DictReader(assignment_list)
        line_count = 0
        successApp = 0
        successRej = 0
        failed=0
        for row in reader:
            if line_count == 0:
                assert 'assignmentId' in row,  f"No column found with name 'assignmentId' in [{assignment_path}]"
                assert 'HITId' in row, f"No column found with name 'HITId' in [{assignment_path}]"
                assert 'Approve' in row, f"No column found with name 'Approve' in [{assignment_path}]"
                assert 'Reject' in row, f"No column found with 'Reject' in [{assignment_path}]"

            if row['Approve'] =='x':
                # approving
                response = client.approve_assignment(
                    AssignmentId=row['assignmentId']
                )
                if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                    successApp += 1
                else:
                    print(f'\tFailed:  "Approving assignment" {row["assignmentId"]}:')
                    failed += 1

            else:
                # rejecting
                response = client.reject_assignment(
                    AssignmentId=row['assignmentId'],
                    RequesterFeedback=row['Reject']
                )
                if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                    successRej += 1
                else:
                    print(f'\tFailed:  "Rejecting assignment" {row["assignmentId"]}:')
                    failed += 1

            line_count += 1
        print(f'Processed {line_count} assignments - Approved {successApp} assignments and reject {successRej}. '
              f'The script failed on {failed} calls.')




def approve_reject_assignments(client, assignment_path, approve):
    """
    Assign bonuses to group of workers.
    A csv file with following columns need to be provided: workerId, assignmentId, bonusAmount, reason
    :param client: boto3 client object for communicating to MTurk
    :param assignment_path: path to the csv file with: workerId, assignmentId, bonusAmount, reason
    :param approve: boolean when false the script reject answers
    :return:
    """
    if approve:
        print('Approving assignments')
    else:
        print('Rejecting assignments')
    with open(assignment_path, mode='r') as assignment_list:
        reader = csv.DictReader(assignment_list)
        line_count = 0
        success=0
        failed=0
        for row in reader:
            if line_count == 0:
                assert 'assignmentId' in row,  f"No column found with assignmentId in [{assignment_path}]"
                if not approve:
                    assert 'feedback' in row, f"No column found with feedback in [{assignment_path}]"
            if approve:
                # approving
                response = client.approve_assignment(
                    AssignmentId=row['assignmentId']
                )
                if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                    success += 1
                else:
                    print(f'\tFailed:  "Approving assignment" {row["assignmentId"]}:')
                    failed += 1

            else:
                # rejecting
                response = client.reject_assignment(
                    AssignmentId=row['assignmentId'],
                    RequesterFeedback=row['feedback']
                )
                if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                    success += 1
                else:
                    print(f'\tFailed:  "Rejecting assignment" {row["assignmentId"]}:')
                    failed += 1

            line_count += 1
        print(f'Processed {line_count} assignments - sent {success} calls was successful and {failed} calls failed.')



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Utility script to handle a MTurk study.')
    # Configuration: read it from mturk.cfg
    parser.add_argument("--cfg", default="mturk.cfg",
                        help="Read mturk.cfg for all the details (path relative to current working directory)")
    parser.add_argument("send_emails", nargs='?', help="send emails (configuration is needed)")
    parser.add_argument("--send_bonus", type=str, help="give bonus to a group of worker. Path to a csv file "
                                                       "(columns: workerId, assignmentId, bonusAmount, reason). "
                                                       "Path relative to current working directory")

    parser.add_argument("--approve", type=str,
                        help="Approve all assignments found in the input csv file. Path to a csv file "
                             "(columns: assignmentId). Path relative to current working directory")
    parser.add_argument("--reject", type=str,
                        help="Reject all assignments found in the input csv file. Path to a csv file "
                             "(columns: assignmentId,feedback). Path relative to current working directory")

    parser.add_argument("--approve_reject", type=str,
                        help="Approve or reject assignments found in the input csv file. Path to a csv file "
                             "(columns: assignmentId, HITId, approve, reject). Path relative to current working "
                             "directory")

    parser.add_argument("--extend_hits", type=str,
                        help="Extends hits for the given number of extra assignments. Path to a csv file "
                             "(Columns: HITId, nExtraAssignments). Path relative to current working "
                             "directory")
    parser.add_argument("--extended_hits_status", type=str,
                        help="Get status of assignments that are generated by the extended HITs. Expect the path to the"
                             "csv file used with '--extend_hits' command.")

    args = parser.parse_args()

    #cfgpath = os.path.join(os.path.dirname(__file__), args.cfg)
    cfgpath = args.cfg
    assert os.path.exists(cfgpath), f"No configuration file as [{cfgpath}]"
    cfg = CP.ConfigParser()
    cfg.read(cfgpath)

    # create mturk client
    mturk_general = cfg['general']

    client = boto3.client(
        'mturk',
        endpoint_url=mturk_general['endpoint_url'],
        region_name=mturk_general['region_name'],
        aws_access_key_id=mturk_general['aws_access_key_id'],
        aws_secret_access_key=mturk_general['aws_secret_access_key'],
        )

    if args.send_emails is not None:
        send_message(client, cfg['send_email'])
    if args.send_bonus is not None:
        bonus_list_path = args.send_bonus
        assert os.path.exists(bonus_list_path), f"No input file found in [{bonus_list_path}]"
        assign_bonus(client, bonus_list_path)

    if args.approve is not None:
        assignments_list_path = args.approve
        assert os.path.exists(assignments_list_path), f"No input file found in [{assignments_list_path}]"
        approve_reject_assignments(client, assignments_list_path, approve=True)

    if args.reject is not None:
        assignments_list_path = args.reject
        assert os.path.exists(assignments_list_path), f"No input file found in [{assignments_list_path}]"
        approve_reject_assignments(client, assignments_list_path, approve=False)

    if args.approve_reject is not None:
        assignments_list_path = args.approve_reject
        assert os.path.exists(assignments_list_path), f"No input file found in [{assignments_list_path}]"
        approve_reject_assignments_together(client, assignments_list_path)

    if args.extend_hits is not None:
        hit_list = args.extend_hits
        assert os.path.exists(hit_list), f"No input file found in [{hit_list}]"
        extend_hits(client, hit_list)

    if args.extended_hits_status is not None:
        hit_list = args.extended_hits_status
        assert os.path.exists(hit_list), f"No input file found in [{hit_list}]"
        extended_hits_report(client, hit_list)
