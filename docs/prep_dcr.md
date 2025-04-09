[Home](../README.md) > [Preparation](preparation.md) > Preparation for Degradation Category Rating (DCR)

# Preparation of DCR/CCR test

The following steps should be performed to prepare the DCR test setup.
For all the resource files (steps 1-4) an example is provided in `sample_inputs` directory using 
the [MCL-JCV Dataset](http://mcl.usc.edu/mcl-jcv-dataset/).  

**Note**: make sure to first perform steps listed in the [general preparation process](preparation.md).

**Note**: Within the DCR method, the quality of a Processed Video Sequence (`PVS`) is compared to a reference video
 clip (`src`) i.e. a same clip without being processed.  

1. Upload your **PVS** and the References video clips in a cloud server and make them publicly available.
 Use their URLs to create the `rating_clips.csv` file with two columns:`pvs` and `src` . Each row contain a URL of a PVS 
 and URL of its corresponding reference clip. (see [rating_clips_dcr.csv](../sample_inputs/rating_clips_dcr.csv) as an example).

    **NOTE**: Make sure that [CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) are enabled in your server: `Access-Control-Allow-Origin: *`.  
    **NOTE**: It is strongly recommended to setup a Content Delivery Network (CDN) to speed up video loading time for your participants.
    Same applies to all other video materials in the following.
    **Note about file names/urls**:
    * Later in the analyzes, clip's file name will be used as a unique key and appears in the results.    
    * In case you have 'conditions' which are represented with more than one clip, you may consider to use the condition's 
        name in the clip's file name e.g. xxx_c01_xxxx.mp4. When you provide the corresponding pattern, the analyzes script 
        will create aggregated results over conditions as well.  

1. Upload your **training clips** in a cloud server and create the `training_clips.csv` file which contains all URLs in a 
column named `training_pvs` and URLs to corresponding reference clips in column `training_src` 
(see [training_clips_dcr.csv](../sample_inputs/training_clips_dcr.csv) as an example).
    
    **Hint**: Training clips are used for anchoring participants perception, and should represent the entire dataset. 
    They should approximately cover the range from worst to best quality to be expected in the test. It may contain 
    about 5 clips. 
1. Upload your **gold standard clips** in a cloud server and create `gold_clips.csv` file which contains following columns:    
    - `gold_clips_pvs`: URL to the processed video clip
    - `gold_clips_src`: URL to the corresponding reference  video clip
    - `gold_clips_ans`: the correct answer, expected from worker. Note to adjust the number based on the scale you are
    going to use (e.g. by 9-point-discrete scale, if the PVS has an excellent quality, the correct answer will be 9, 
    whereas by 5-point_discrete scale, it will be 5).
    
    see [gold_clips.csv](../sample_inputs/gold_clips_dcr.csv) as an example).
    
    **Hint**: Gold standard clips are used as a hidden quality control item in each session. It is expected that their 
    answers are so obvious for all participants that they all give the `gold_clips_ans` rating (+/- 1 deviation is 
    accepted). For this purpose, it is recommended to use clips with excellent (answer 5) or very bad (answer 1) quality.
        
1. Create trapping stimuli set for your dataset.

    1. Make a copy of sample configuration file `src\configurations\trappings.cfg` and adapt it. 
    See [configuration of create_trapping_clips script ](conf-trapping.md) for more information.
     
    2. Create a `tp_src` directory and add some clips from your dataset to it. Select clips in a way that
		1. Covers fair distributions of clips 
		1. Covers entire range of quality (some good, fair and bad ones)
    
    4. Run `create_trapping_clips.py`
    ``` bash
    cd src\trapping_clips
    pip install -r requirements.txt
    python create_trapping_clips.py ^
        --source tp_src ^
        --des tp_out ^
        --cfg your_config_file.cfg
    ```    
    5. Trapping clips are stored in `tp_out` directory. List of clips and their correct answer can 
    be found in `tp_out\output_report.csv`.
        
1. Upload your **trapping clips** in a cloud server and create `trapping_clips.csv` file which contains all URLs in 
a column named `trapping_pvs`, URLS to reference clips in column `trapping_src` and expected answer to each clip in a 
column named `trapping_ans` (see [trapping_clips.csv](../sample_inputs/trapping_clips_dcr.csv) as an example).

1. Create your custom project by running the master script: 

    1. Make a copy of sample configuration file `src\configurations\master.cfg` and adapt it. 
    See [master script configuration](conf_master.md) for more information.
    
    1. Run master script with all above-mentioned resources as input (following example is for ccr)
        
        ```bash
        cd src
        python master_script.py ^
            --project YOUR_PROJECT_NAME ^
            --method dcr ^
            --cfg your_configuration_file.cfg ^
            --clips rating_clips.csv ^
            --training_clips training_clips.csv ^
            --gold_clips gold_clips.csv ^
            --trapping_clips trapping_clips.csv              
        ```
        Note: file paths are expected to be relative to the current working directory.
    
    1. Double check the outcome of the script. A folder should be created with YOUR_PROJECT_NAME in current working 
    directory which contains: 
    * `YOUR_PROJECT_NAME_dcr.html`: Customized HIT app to be used in Amazon Mechanical Turk (AMT).
    * `YOUR_PROJECT_NAME_publish_batch.csv`: List of dynamic content to be used during publishing batch in AMT.
    * `YOUR_PROJECT_NAME_dcr_result_parser.cfg`: Customized configuration file to be used by `result_parser.py` script
        
Now, you are ready for [Running the Crowdsourcing Test](running_test_mturk.md).