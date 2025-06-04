[Home](../README.md) > [Preparation](preparation.md) > Preparation for Photorealistic Avatars evaluation

# Preparation for Photorealistic Avatar Evaluation

Follow the steps below to prepare the `avatar` test setup. Examples for all resource files (steps 1-4) are provided in the `sample_inputs` directory. To prepare the samples we used [LivePortrait]. 

**Note**: Ensure that you first complete the steps listed in the [general preparation process](preparation.md).

**Note**: Processed Video Sequences (`PVS`) should be encoded in formats supported by major web browsers. For a list of supported encodings, refer to [this guide](https://developer.mozilla.org/en-US/docs/Web/Media/Formats/Video_codecs#codec_details). You can use [FFmpeg](https://www.ffmpeg.org/) for encoding.

For details about the different test methods for Photorealistic Avatars, please refer to the [accompanying paper](https://arxiv.org/pdf/2411.09066). This repository provides two templates as described in the paper:
* **Template A**: A no-reference method where participants rate their agreement with 8 statements after watching only the avatar video. The scale ranges from Strongly Disagree (1) to Strongly Agree (5).
* **Template B**: A full-reference method where participants rate their agreement with 3 statements after watching both the avatar video and the driving video. The scale ranges from Strongly Disagree (1) to Strongly Agree (5).

### Steps to Prepare Resources for the `avatar` Test

1. **Upload PVS Clips**  
   Upload your **PVS** clips to a cloud server and make them publicly accessible. Use the URLs to create the `rating_clips.csv` file with a column named `pvs`. Each row should contain the URL of a PVS (see [rating_clips_avatar_a.csv](../sample_inputs/rating_clips_avatar_a.csv) for an example).

   If using `Template B`, horizontally stack the avatar video and the driving video so that the avatar video appears on the left and the driving video on the right. The resulting video becomes the `pvs` for Template B. See [rating_clips_avatar_b.csv](../sample_inputs/rating_clips_avatar_b.csv) for an example. Below is a sample FFmpeg command:

   ```bash
   ffmpeg -i avatar_1.mp4 -i real_video_1.mp4 -filter_complex "hstack" pvs1.mp4
   ```

   **Important Notes**:
   - Ensure that [CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) is enabled on your server: `Access-Control-Allow-Origin: *`.
   - It is strongly recommended to set up a Content Delivery Network (CDN) to improve video loading times for participants. This applies to all other video materials mentioned below.
   - File names/URLs: Clip file names will be used as unique keys in the analysis and will appear in the results. If you have 'conditions' represented by multiple clips, consider including the condition name in the file name (e.g., `xxx_c01_xxxx.mp4`). Providing the corresponding pattern allows the analysis script to aggregate results over conditions.

2. **Upload Training Gold Clips**  
   Upload your **training gold clips** to a cloud server and create the `avatar_training_clips_a.csv` file, which contains all URLs in a column named `training_pvs` (see [avatar_training_clips_a.csv](../sample_inputs/avatar_training_clips_a.csv) for examples).

   **Hints**:
   - Training clips are used to anchor participants' perceptions and should represent the entire dataset. They should approximately cover the range from worst to best quality on different scales. It is recommended to use up to 5 clips.
   - For avatar evaluations, training gold clips include feedback for participants based on their answers. Provide the correct answer for each question in the `*_ans` field, the acceptable tolerance in the `*_var` column, and the corresponding message for out-of-range ratings in the `*_msg` column. Leave the `*_ans` cell empty if any rating is acceptable. See the example files for more details.

3. **Upload Gold Standard Clips**  
   Upload your **gold standard clips** to a cloud server and create the `gold_clips.csv` file with the following columns:
   - `gold_clips_pvs`: URL to the processed video clip.
   - `gold_clips_ans`: The correct answer expected from participants. Since avatars have multiple scales, provide the correct answers as a comma-separated list (e.g., `(scale1_ans, scale2_ans, scale3_ans)`). For Template B, an example answer could be `(5,5,5)`. Use `_` as a placeholder for scales without a correct answer (e.g., `(5,_,5)`). The order of scales should match the configuration file explained later in this document.

   See [avatar_gold_clips_b.csv](../sample_inputs/avatar_gold_clips_b.csv) for an example.

   **Hint**: Gold standard clips are hidden quality control items. Their answers should be so obvious that all participants provide the correct rating (±1 deviation is accepted). Use clips with extreme quality levels (e.g., strongly agree - 5, or strongly disagree - 1) for each scale.

4. **Create Trapping Stimuli**  
   1. Copy the sample configuration file `src\configurations\trappings.cfg` and adapt it. See [configuration of create_trapping_clips script](conf-trapping.md) for more details.
   2. Create a `tp_src` directory and add clips from your dataset. Ensure the selection:
      - Covers a fair distribution of clips.
      - Includes a range of quality levels (good, fair, and bad).
   3. Run the `create_trapping_clips.py` script:
      ```bash
      cd src\trapping_clips
      pip install -r requirements.txt
      python create_trapping_clips.py ^
          --source tp_src ^
          --des tp_out ^
          --cfg your_config_file.cfg ^
          --font path_to_font.ttf ^
          --avatar
      ```
   4. Trapping clips will be stored in the `tp_out` directory. The list of clips and their correct answers can be found in `tp_out\trapping_output_report.csv`.

5. **Upload Trapping Clips**  
   Upload your **trapping clips** to a cloud server and create the `trapping_clips.csv` file with the following columns:
   - `trapping_pvs`: URLs of the trapping clips.
   - `trapping_ans`: Expected answers for each clip.

   See [avatar_trapping_clips_a.csv](../sample_inputs/avatar_trapping_clips_a.csv) for an example.

6. **Create Your Custom Project**  
   1. Copy the sample configuration file `src\configurations\master.cfg` and adapt it. See [master script configuration](conf_master.md) for more details, especially the sections dedicated to Avatar, where you specify the template to use and other settings.
   2. Run the master script with all the resources prepared above. For example:
      ```bash
      cd src
      python master_script.py ^
          --project YOUR_PROJECT_NAME ^
          --method avatar ^
          --cfg your_configuration_file.cfg ^
          --clips rating_clips.csv ^
          --training_gold_clips training_clips.csv ^
          --gold_clips gold_clips.csv ^
          --trapping_clips trapping_clips.csv
      ```
      **Note**: File paths should be relative to the current working directory.
   3. Verify the script's output. A folder named `YOUR_PROJECT_NAME` will be created in the current working directory, containing:
      - `YOUR_PROJECT_NAME_acr.html`: Customized HIT app for Amazon Mechanical Turk (AMT).
      - `YOUR_PROJECT_NAME_publish_batch.csv`: List of dynamic content for publishing the batch in AMT.
      - `YOUR_PROJECT_NAME_avatar_result_parser.cfg`: Configuration file for the `result_parser.py` script.

You are now ready to proceed with [Running the Crowdsourcing Test](running_test_mturk.md).