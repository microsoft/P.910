[Home](../README.md) > Analyzing Data

# Analyzing Data

When your Batch is finished, download the answers from HIT App Server (from now on `downloaded_batch_result.csv`) and
 also from AMT (from now on `downloaded_amt_results.csv`). 

1. (optional) Modify `condition_pattern` in your result parser config file i.e.`YOUR_PROJECT_NAME_ccr_result_parser.cfg` which was 
created in the first step ([preparation](preparation.md)).

    **Note**: In case there is possible to have a condition level aggregation in your dataset, uncomment the 
    `condition_pattern` and `condition_keys`.
    
    **Note**: The `condition_pattern` specifies which part of the clip URL refers to the condition name/number that they are
    representing. Clips with the same value on that position, are considered to belong to the same condition and votes 
    assigned to them will be aggregated to create the `per_condition` report. Example: Assuming `D501_C03_M2_S02.mp4` is 
    a file name,and `03` is the condition name. The pattern should be set to `.*_c(?P<condition_num>\d{1,2})_.*.mp4` , 
    and the `condition_keys` to `condition_num`.
   
1. (optional) Update config file create for the result parser in the first step ([preparation](preparation.md)) if you 
want to have experiment specific criteria for data cleansing process.
    
    1. Criteria for **accepting** a submission (if the following criteria are not met then the submission will be added to reject list):
    
    ```INI
        [acceptance_criteria]
        all_video_played_equal: 1        
        correct_matrix_bigger_equal: 1
        correct_tps_bigger_equal: 1        
        allowedMaxHITsInProject: NUMBER
        # if you set it to 1, then the submissions with wrong answer to gold-clip will be rejected.
        gold_standard_bigger_equal:0
        # if workers fail in these performance criteria their submissions will be failed.
        rater_min_acceptance_rate_current_test : 30
        rater_min_accepted_hits_current_test : 0
        block_rater_if_acceptance_and_used_rate_below : 20              
    ```
    
    * `all_video_played_equal: 1` : All the videos has should have been watched until the end.        
    * `correct_matrix_bigger_equal: 1`: At least one of the brightness tests (matrix with images) should be answered correctly
    * `correct_tps_bigger_equal: 1`: The trapping question should be answered correctly        
    * `allowedMaxHITsInProject: NUMBER`: A worker cannot participate in more than `NUMBER` sessions      
    * `gold_standard_bigger_equal:0`: if you set it to 1, then the submissions with wrong answer to gold-clip will be rejected. 
    * `rater_min_acceptance_rate_current_test : 30`:  Minimum acceptance rate for a worker in this test. If they have 
    an acceptance rate below this percentage all of their submission will be rejected. 
    * `rater_min_accepted_hits_current_test : 0` The minimum number of accepted submissions that a worker should have. 
    * `block_rater_if_acceptance_and_used_rate_below : 20`: If the accidence rate of a worker in this study is below this
    threshold, the worker will be added to the "block" list with a proper message. You may upload the "block" list later 
    in your AMT account to block those workers.
   
    1. All submissions that are accepted and passed the following criteria are considered reliable and will be used/aggregated.
    Consequently if they failed then the submission will not be used but the worker will be paid.
      
    ```INI
        [accept_and_use]
        variance_bigger_equal: 0.15
        #outlier_removal: true
        gold_standard_bigger_equal:1
        viewing_duration_over:1.15
        correct_matrix_bigger_equal: 2
        # rater performance criteria
        # percentage of "accept and used" submissions in current job
        rater_min_acceptance_rate_current_test : 80
        rater_min_accepted_hits_current_test : 1                    
    ```
    * `variance_bigger_equal: 0.15` Minimum variance in ratings of a session (beside votes to gold and trapping questions). 
    It is to detect straightliners.
    * `outlier_removal: true` Remove the comment to activate the automatic outlier detection method.  The [z-score
    outlier detection method](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm) is used i.e. all votes 
    with an absolute z-score of 3.29 or higher will be considered as outlier and removed. 
    * `gold_standard_bigger_equal:1` Submissions with wrong answers to the gold questions will not be used.
    * `viewing_duration_over:1.15` If the overall play-back duration exceed 115% of videos' duration, the submission will not be used
    * `correct_matrix_bigger_equal: 2` Both brightness tests (matrix with images) should be answered correctly
    * `rater_min_acceptance_rate_current_test : 80` Minimum acceptance rate for a worker in this test. If they have 
    an acceptance rate below this percentage all of their submission will to be used.
    * `rater_min_accepted_hits_current_test : 1` The minimum number of accepted submissions that a worker should have.   
    
1. Run `result_parser.py` 
        
    ``` bash
    cd src
    python result_parser.py ^
        --cfg your_configuration_file.cfg ^ 
        --method dcr  ^
        --answers downloaded_batch_result.csv ^
        --amt_answers downloaded_amt_results.csv ^
        --quantity_bonus all ^
        --quality_bonus
    ```
    * `--cfg` use the configuration file generated for your project in the [preparation](preparation.md) step here (i.e.`YOUR_PROJECT_NAME_ccr_result_parser.cfg`).
    * `--method` could be `acr`, `dcr`, `ccr`, `acr-hr`, `avatar_a` and `avatar_b`.
    * `--quantity_bonus` could be `all`, or `submitted`. It specify which assignments should be considered when calculating
    the amount of quantity bonus (everything i.e. `all` or just the assignments with status submitted i.e. `submitted`).
    * `--answers` the answer csv file downloaded from HIT App Server.
    * `--amt_answers` the answer csv file downloaded from AMT.
    
    Beside the console outputs, following files will be generated in the same directory as the `--answers` file is located in.
    All file names will start with the `--answers` file name.   
    * `[downloaded_batch_result]_data_cleaning_report`: Data cleansing report. Each line refers to one line in answer file. 
    * `[downloaded_batch_result]_accept_reject_gui.csv`: A report to be used for approving and rejecting assignments. One line
    for each assignment which has a status of "submitted". 
    * `[downloaded_batch_result]_votes_per_clip.csv`: Aggregated result per clip, including MOS, standard deviations, and 95% Confidence Intervals.  
    * `[downloaded_batch_result]_votes_per_cond.csv`: Aggregated result per condition.
    * `[downloaded_batch_result]_votes_per_worker.csv`: Long format of rating per clip, includes: HITId, workerid, file, vote and condition.
    * `[downloaded_batch_result]_quantity_bonus_report.csv`: List of workers who are eligible for quantity bonus with the amount of bonus (to be used with the mturk_utils.py).
    * `[downloaded_batch_result]_quality_bonus_report.csv`: List of workers who are eligible for quality bonus with the amount of bonus (to be used with the mturk_utils.py).
    * `[downloaded_batch_result]_extending.csv`: List of HITIds with number of assignment per each which are needed to reach a specific number of votes per clip.
    * `[downloaded_batch_result]_block_list.csv`: List of workers with low performance that potentially can be blocked from future jobs.             
    * In addition a summary in the condition level will be provided for all three scales in `[downloaded_batch_result]_votes_per_cond_all`.
        
        
## Approve/Reject submissions

Depending to how you create the HITs (using the AMT website or script) you should use the same method for approving/rejecting
submission.

### Approve/Reject submissions - using website.
 
 1. Go to “**Manage**”> “**Results**”> find your *Batch* and select “**Review Results**”.
   
 1. Click on "**Upload CSV**" and upload the `[downloaded_batch_result]_accept_reject_gui.csv` file.
 
### Approve/Reject submissions - using script/API.

 1. Run the following script:
 
    ```bash
    cd src
    python mturk_utils.py ^
        --cfg mturk.cfg ^
        --approve_reject [downloaded_batch_result]_accept_reject_gui.csv  
    ```
    

## Assign bonuses

 1. Run the following script with both `[downloaded_batch_result]_quantity_bonus_report.csv` and 
 `[downloaded_batch_result]_quality_bonus_report.csv`:
 
    ```bash
    cd src
    python mturk_utils.py ^
        --cfg mturk.cfg ^
        --send_bonus [downloaded_batch_result]_*_bonus_report.csv
    ```
 ## Extending HITs
 
 In case you want to reach the intended number of votes per clips, you may use the following procedure:
 
 1. During **Approve/Reject submission** process, select _Republish rejected assignment(s) for other Workers to complete_.
 2. Run the following script with `[downloaded_batch_result]_extending.csv`: 
 
     ```bash
    cd src
    python mturk_utils.py ^
        --cfg mturk.cfg ^
        --extend_hits [downloaded_batch_result]_extending.csv
    ```
    **Note:** 
    
    * Extending HITs is only possible with the above API call. As a result, new assignments will be created by API call.
    Assignments create by API call are not visible in the website. From the report printed by script you can see how many 
    assignments are created. In addition, you can see in your account that some amount of funds are hold for liability.
    However, when the assignments are finished and submitted by workers, you can review/download them in website.
    Until then, you may use following script call to check the status of those assignments:
    
        ```bash
        cd src
        python mturk_utils.py ^
            --cfg mturk.cfg ^
            --extended_hits_status [downloaded_batch_result]_extending.csv
        ```  
    * From AMT website: _HITs created with fewer than 10 assignments cannot be extended to have 10 or more assignments.
     Attempting to add assignments in a way that brings the total number of assignments for a HIT from fewer than 10 assignments
      to 10 or more assignments will result in an `AWS.MechanicalTurk.InvalidMaximumAssignmentsIncrease exception.`_ 