import csv
import configparser
from contextlib import ExitStack
import json
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src import result_parser as parser


class ProblemReportTests(unittest.TestCase):
    def make_row(self):
        reports = [
            {
                'question_id': question,
                'description': 'Playback stalled,\nplease review',
                'video_urls': [f'https://example.com/{question}.mp4'],
                'browser_info': 'Test browser',
                'reported_at': '2026-10-14T15:24:02.390Z',
            }
            for question in ['q1', 'q2']
        ]
        return {
            'answer.problem_reports': json.dumps(reports),
            'answer.q1': '5',
            'answer.q1_url': reports[0]['video_urls'][0],
            'answer.q2': '3',
            'answer.q2_url': reports[1]['video_urls'][0],
        }

    def test_all_reported_questions_still_require_answers(self):
        with patch.multiple(parser, question_names=['q1', 'q2'], question_name_suffix='', create=True):
            for method in ['acr', 'acr-hr', 'dcr', 'ccr']:
                for question in ['q1', 'q2']:
                    with self.subTest(method=method, question=question):
                        row = self.make_row()
                        self.assertEqual(parser.check_all_answered(row, method), 1)
                        row[f'answer.{question}'] = ''
                        self.assertEqual(parser.check_all_answered(row, method), 0)

    def test_reported_avatar_questions_require_ratings_and_problem_tokens(self):
        with patch.multiple(
            parser, question_names=['q1', 'q2'], problem_tokens=['trust', 'pt_other'], create=True,
        ):
            for method in ['avatar_a', 'avatar_b', 'avatar_pt']:
                for question in ['q1', 'q2']:
                    with self.subTest(method=method, question=question):
                        row = {
                            **self.make_row(),
                            'answer.q1_trust': '5', 'answer.q2_trust': '3',
                            'answer.q1_pt_other': 'Video stalled', 'answer.q2_pt_other': 'Video stalled',
                        }
                        self.assertEqual(parser.check_all_answered(row, method), 1)
                        row[f'answer.{question}_trust'] = ''
                        self.assertEqual(parser.check_all_answered(row, method), 0)
                        row[f'answer.{question}_trust'] = '3'
                        row[f'answer.{question}_pt_other'] = ''
                        self.assertEqual(parser.check_all_answered(row, method), int(method != 'avatar_pt'))

    def test_reported_questions_remain_in_playback_and_variance_checks(self):
        row = {
            **self.make_row(),
            'answer.video_n_finish_q1': '0', 'answer.video_n_finish_q2': '1',
            'answer.video_duration_q1': '10', 'answer.video_duration_q2': '10',
            'answer.video_play_duration_q1': '20', 'answer.video_play_duration_q2': '10',
        }
        with patch.multiple(
            parser, config={}, question_names=['q1', 'q2'], question_name_suffix='', create=True,
        ):
            self.assertFalse(parser.check_video_played(row, 'acr'))
            row['answer.video_n_finish_q1'] = '1'
            self.assertTrue(parser.check_video_played(row, 'acr'))
            self.assertEqual(parser.check_play_duration(row), 1.5)
            self.assertEqual(parser.check_variance(row, 'acr'), 2)

    def test_reported_quality_questions_are_not_automatically_passed(self):
        config = {
            'trapping': {'url_found_in': 'answer.q1_url', 'ans_found_in': 'input.correct_ans'},
            'gold_question': {
                'url_found_in': 'answer.q1_url', 'ans_found_in': 'input.correct_ans',
                'variance': '0', 'gold_ans_format': '(trust)',
            },
        }
        with patch.multiple(
            parser, config=config, question_names=['q1', 'q2'], problem_tokens=['trust'],
            logger=logging.getLogger(__name__), create=True,
        ):
            for method in ['acr', 'acr-hr', 'dcr', 'ccr', 'avatar_a', 'avatar_b', 'avatar_pt']:
                for answer in ['1', '5']:
                    with self.subTest(method=method, answer=answer):
                        row = {
                            **self.make_row(), 'input.correct_ans': '5',
                            'answer.q1': answer, 'answer.q1_trust': answer, 'answer.q1_order': 'rp',
                            'answer.q2_trust': '3', 'answer.q2_tpid': 'lessthan5',
                            'answer.q2_tp': '1', 'answer.q2_repeatedid': 'trust',
                            'answer.q2_repeatingitem': '3',
                        }
                        expected = int(answer == '5')
                        self.assertEqual(parser.check_tps(row, method), expected)
                        self.assertEqual(parser.check_gold_question(row, method)[0], expected)

    def test_multiple_reports_follow_normal_acceptance_checks(self):
        config = {
            'acceptance_criteria': {
                'correct_matrix_bigger_equal': '1',
                'correct_tps_bigger_equal': '1',
            },
        }
        data = {
            'problem_report_count': 2,
            'invalid_problem_report': 0,
            'correct_ishihara_plates': None,
            'correct_matrix': None,
            'correct_tps': 1,
            'complete_answered': 1,
        }
        with patch.object(parser, 'config', config, create=True):
            self.assertEqual(parser.check_if_session_accepted(data), (True, []))
            data['correct_tps'] = 0
            self.assertEqual(parser.check_if_session_accepted(data), (False, ['trapping_question']))

    def test_export_preserves_all_reports_and_final_outcomes(self):
        reports = [
            {
                **report,
                'assignment': 'assignment-1',
                'video_urls': json.dumps(report['video_urls']),
            }
            for report in parser.get_problem_reports(self.make_row())
        ]
        workers = [{
            'assignment': 'assignment-1',
            'accept': 1,
            'accept_and_use': 0,
            'Reject': '',
            'failures': ['variance'],
        }]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'problem_reports.csv'
            parser.save_problem_reports(reports, workers, path)
            with path.open(newline='') as file:
                rows = list(csv.DictReader(file))
            self.assertEqual([row['question_id'] for row in rows], ['q1', 'q2'])
            self.assertEqual(rows[1]['description'], reports[1]['description'])
            self.assertEqual(json.loads(rows[1]['video_urls']), ['https://example.com/q2.mp4'])
            self.assertEqual(rows[1]['accept'], '1')
            self.assertEqual(rows[1]['accept_and_use'], '0')
            self.assertEqual(json.loads(rows[1]['failures']), ['variance'])
            parser.save_problem_reports([], workers, path)
            with path.open(newline='') as file:
                reader = csv.DictReader(file)
                self.assertIn('description', reader.fieldnames)
                self.assertEqual(list(reader), [])

    def test_export_neutralizes_formulas_without_changing_submission_data(self):
        workers = [{
            'assignment': 'assignment-1', 'accept': 0, 'accept_and_use': 0,
            'Reject': 'Invalid report', 'failures': [],
        }]
        for value in ['=1+1', '+1+1', '-1+1', '@SUM(1)', '  =1+1', '\ttext', '\rtext', '\ntext']:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                report = {
                    'assignment': 'assignment-1', 'description': value,
                    'browser_info': value, 'raw_problem_reports': value,
                }
                path = Path(directory) / 'problem_reports.csv'
                parser.save_problem_reports([report], workers, path)
                with path.open(newline='') as file:
                    exported = next(csv.DictReader(file))
                for field in ['description', 'browser_info', 'raw_problem_reports']:
                    self.assertEqual(exported[field], "'" + value)
                    self.assertEqual(report[field], value)

    def test_data_cleaning_exports_reports_without_rejecting_multiple_reports(self):
        row = {
            **self.make_row(),
            'workerid': 'worker-1',
            'hitid': 'hit-1',
            'assignmentid': 'assignment-1',
            'assignmentstatus': 'Submitted',
            'answer.video_n_finish_q1': '1',
            'answer.video_n_finish_q2': '1',
            'answer.video_duration_q1': '10',
            'answer.video_duration_q2': '10',
            'answer.video_play_duration_q1': '10',
            'answer.video_play_duration_q2': '10',
        }
        config = {
            'trapping': {'url_found_in': 'answer.q1_url', 'ans_found_in': 'input.tp_ans'},
            'acceptance_criteria': {'correct_matrix_bigger_equal': '1', 'correct_tps_bigger_equal': '1'},
            'accept_and_use': {
                'variance_bigger_equal': '0',
                'gold_standard_bigger_equal': '1',
                'viewing_duration_over': '2',
            },
        }
        row['input.tp_ans'] = '5'
        invalid_timestamp = parser.get_problem_reports(row)
        invalid_timestamp[0]['reported_at'] = 'invalid'
        invalid_url = parser.get_problem_reports(row)
        invalid_url[0]['video_urls'] = ['https://example.com/wrong.mp4']
        rows = [row]
        for index, payload in enumerate([json.dumps(invalid_timestamp), json.dumps(invalid_url), '=1+1']):
            rows.append({
                **row,
                'assignmentid': f'invalid-{index}',
                'answer.problem_reports': payload,
            })
        rows.append({**row, 'assignmentid': 'unanswered', 'answer.q1': ''})
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            stack.enter_context(patch.multiple(
                parser, config=config, question_names=['q1', 'q2'], question_name_suffix='',
                logger=logging.getLogger(__name__), create=True,
            ))
            for name, value in {
                'check_gold_question': (1, {}),
                'check_variance': 0,
                'check_video_dropped_frame_percent': (0, 0),
                'check_wrong_vcode_should_block': {},
            }.items():
                stack.enter_context(patch.object(parser, name, return_value=value))
            stack.enter_context(patch.object(parser, 'evaluate_maximum_hits', side_effect=lambda workers: workers))
            stack.enter_context(patch.object(
                parser, 'evaluate_rater_performance',
                side_effect=lambda workers, sessions, *args: (workers, sessions, 0, []),
            ))
            stack.enter_context(patch.object(
                parser, 'check_remote_desktop_usage',
                side_effect=lambda workers, sessions, filename: (workers, sessions),
            ))
            for name in [
                'save_approved_ones', 'save_rejected_ones',
                'save_approve_rejected_ones_for_gui', 'save_hits_to_be_extended',
            ]:
                stack.enter_context(patch.object(parser, name))
            path = Path(directory) / 'answers.csv'
            with path.open('w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=list(row))
                writer.writeheader()
                writer.writerows(rows)
            workers, sessions = parser.data_cleaning(str(path), 'acr', [])
            self.assertEqual(workers[0]['accept'], 1)
            self.assertEqual([worker['accept'] for worker in workers[1:]], [0, 0, 0, 0])
            self.assertTrue(all('problem report data was invalid' in worker['Reject'] for worker in workers[1:4]))
            self.assertEqual(workers[-1]['complete_answered'], 0)
            self.assertEqual(len(sessions), 1)
            with (path.parent / 'answers_problem_reports.csv').open(newline='') as file:
                reports = list(csv.DictReader(file))
            self.assertTrue(all(report['excluded_question'] == '0' for report in reports))
            self.assertEqual([report['accept'] for report in reports[:2]], ['1', '1'])
            self.assertEqual(len(reports), 8)
            self.assertTrue(all(report['validation_error'] for report in reports[2:6]))
            self.assertTrue(all(report['accept'] == '0' for report in reports[2:]))
            self.assertEqual(reports[5]['raw_problem_reports'], "'=1+1")

    def test_reported_regular_votes_are_included_in_aggregation(self):
        config = configparser.ConfigParser()
        config.read_dict({
            'general': {'number_of_questions_in_rating': '2'},
            'gold_question': {'url_found_in': 'input.gold_url'},
            'accept_and_use': {},
        })
        row = {
            **self.make_row(),
            'input.gold_url': 'https://example.com/gold.mp4',
            'hitid': 'hit-1', 'workerid': 'worker-1',
        }
        with patch.multiple(
            parser, config=config, question_names=['q1', 'q2'], question_name_suffix='',
            max_found_per_file=-1, pvs_src_map={}, file_to_condition_map={},
            logger=logging.getLogger(__name__), create=True,
        ):
            per_file, _, per_worker = parser.transform('acr', [row], False, False)
            self.assertEqual([item['file_url'] for item in per_file], [row['answer.q1_url'], row['answer.q2_url']])
            self.assertEqual([item['MOS'] for item in per_file], [5, 3])
            self.assertEqual(per_worker['vote'].tolist(), [5, 3])

    def test_reported_gold_occurrence_does_not_discard_later_regular_vote(self):
        config = configparser.ConfigParser()
        config.read_dict({
            'general': {'number_of_questions_in_rating': '2'},
            'gold_question': {'url_found_in': 'input.gold_url'},
            'trapping': {'url_found_in': 'input.trapping_url'},
            'accept_and_use': {},
        })
        row = self.make_row()
        row.update({
            'answer.q2_url': row['answer.q1_url'],
            'answer.problem_reports': json.dumps(parser.get_problem_reports(row)[:1]),
            'input.gold_url': row['answer.q1_url'],
            'input.trapping_url': 'https://example.com/trapping.mp4',
            'hitid': 'hit-1',
            'workerid': 'worker-1',
        })
        for method in ['acr', 'acr-hr']:
            with self.subTest(method=method), patch.multiple(
                parser, config=config, question_names=['q1', 'q2'], question_name_suffix='',
                max_found_per_file=-1, pvs_src_map={}, file_to_condition_map={},
                logger=logging.getLogger(__name__), create=True,
            ):
                per_file, _, per_worker = parser.transform(method, [row], False, False)
                self.assertEqual(len(per_file), 1)
                self.assertEqual(per_file[0]['file_url'], row['answer.q2_url'])
                self.assertEqual(per_file[0]['n'], 1)
                self.assertEqual(per_file[0]['MOS'], 3)
                self.assertEqual(per_worker['vote'].tolist(), [3])

    def test_acrhr_reported_reference_remains_in_dmos_calculation(self):
        config = configparser.ConfigParser()
        config.read_dict({
            'general': {'number_of_questions_in_rating': '4', 'scale': '5'},
            'gold_question': {'url_found_in': 'input.gold_url'},
            'accept_and_use': {},
        })
        row = {
            **self.make_row(),
            'input.gold_url': 'https://example.com/gold.mp4',
            'answer.q3_url': 'https://example.com/reference.mp4',
            'answer.q3': '4',
            'answer.q4_url': 'https://example.com/processed.mp4',
            'answer.q4': '3',
            'hitid': 'hit-1',
            'workerid': 'worker-1',
        }
        for index, question in enumerate(['q1', 'q2', 'q3', 'q4']):
            row[f'input.q{index}'] = row[f'answer.{question}_url']
            row[f'input.q{index}_r'] = row['answer.q1_url' if index < 2 else 'answer.q3_url']
        with tempfile.TemporaryDirectory() as directory, patch.multiple(
            parser, config=config, question_names=['q1', 'q2', 'q3', 'q4'], question_name_suffix='',
            max_found_per_file=-1, pvs_src_map={}, file_to_condition_map={},
            logger=logging.getLogger(__name__), create=True,
        ):
            per_file, _, _ = parser.transform('acr-hr', [row], False, False)
            self.assertIn(row['answer.q1_url'], [item['file_url'] for item in per_file])
            path = Path(directory) / 'per_file.csv'
            parser.pd.DataFrame(per_file).to_csv(path, index=False)
            parser.add_dmos_acrhr(str(path), config)
            with path.open(newline='') as file:
                scores = {item['file_url']: item for item in csv.DictReader(file)}
            self.assertEqual(float(scores[row['answer.q1_url']]['DMOS']), 5)
            self.assertEqual(float(scores[row['answer.q2_url']]['DMOS']), 3)
            self.assertEqual(float(scores[row['answer.q3_url']]['DMOS']), 5)
            self.assertEqual(float(scores[row['answer.q4_url']]['DMOS']), 4)
            self.assertEqual(len(scores), 4)


if __name__ == '__main__':
    unittest.main()
