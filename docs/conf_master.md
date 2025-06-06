[Home](../README.md) > [Preparation](preparation.md) 

# Configure for `master_script.py`
 
This describes the configuration for the `master_script.py`. A sample configuration file can be found in [`configurations\master.cfg`](.\src\configurations\master.cfg).
 
## `[create_input]`

* `number_of_clips_per_session:10`: Number of clips from "rating_clips" to be included in the "Rating section" of each HIT/viewing session. 
* `number_of_trapping_per_session:1`: Number of trapping questions to be included in the "Rating section".
* `number_of_gold_clips_per_session:1`:Number of gold clips to be included in the "Rating section".
* (optional)  `condition_pattern:`: Specifies a regex to extract the condition name from the clip URL. example: 
Assuming the URL is `htttp://test.com/D501_C03_M2_S02.mp4` is the clip URL, and "03" is the condition name. 
The pattern will be `.*_c(?P<condition_num>\d{1,2})_.*.mp4`, you should also use condition_keys with `condition_num`.
* (optional)  `condition_keys:` comma separated list of keys appearing in the `condition_pattern`:
* (optional)  `clip_packing_strategy:random`: Either `random` or `balanced_block`. It specifies How to select clips 
which will be assessed in a same HIT. For the `balanced_block` design, `condition_pattern`, `condition_pattern`, and
 `condition_pattern` should be specified.  `number_of_clips_per_session` should be a multiple of the unique values of the 
 key specified in the `block_keys`. 
* (optional)  `block_keys:`:  The key(s) to be used for creating the blocks should be specified here.Up to two keys. 
A comma separated list. For multiple keys, all values of the first key should appear in one block.


## `[hit_app_html]` 
* `scale:5`: number of points for the rating scale to be used. either 5 or 9.
* `video_player: no-scale`: Specify if the videos should be scaled to fill the page, set `max-height` to fill the page with the video.  
* (optional)`cookie_name:pcrwdv_test`: A cookie with this name will be used to store the current state of a worker in this project.
 Key attributes like number of assignments answered by the worker, if the training or setup sections are needed. 
 It is a project specific value. If not specified a random name will be generated by master script and used.
* (optional)`qual_cookie_name:viewing01`: A cookie with this name will show if the user passed the Qualification section.
The cookies expires after 1 month. If a worker could not successfully pass the Qualification section, they will see the 
following message next time they want to perform a HIT from this group:
    ````text
    There is no assignments that match to your profile now. Please try it again in two-weeks time.
    We thank you for your participation.
    ````
    If not specified, a random name will be generated for this project and used.
* (optional)`allowed_max_hit_in_project:60`: Number of assignments that one worker can perform from this project. 
If not specified the maximum possible number will be used automatically.
* `hit_base_payment:0.5`: Base payment for an accepted assignment from this HIT. This value will be used as information.
* `quantity_hits_more_than: 30`: Defines the necessary hits required for quantity bonus.
* `quantity_bonus: 0.1`: The amount of the quantity bonus to be paid for each accepted assignment.
* `quality_top_percentage: 20`: Defines when quality bonus should be applied (in addition, participant should be 
eligible for quantity bonus).
* `quality_bonus: 0.15`: the amount of the quality bonus per accepted assignment.

### Settings specific to Avatar
 
* `use_trapping_question: 0` set it to 1 for template avatar_a otherwise 0
* `use_repeated_question:0`set it to 1 for template avatar_a otherwise 0
* `horizontal_rating: 1`,  set to 1 so the rating scale is displayed horizontally
* `template: avatar_a`, set the template to be either `avatar_a`, or `avatar_b`
* `gold_ans_format: lookslike,facialexpressions,gesture_acc`, comment for template a. Expect to have a column `gold_clips_ans` formatted like `(X,Y,...)` where `X` is correct answer to scale "lookslike",etc. When the answer is not importart use `_`. Example is `(5,_,1)`.

## `[viewing_condition]` 
* `min_screen_refresh_rate:30`: The minimum screen refresh rate that user's monitor should have to be able to participate in this study.
The value should be bigger than the maximum frame rate of videos in your dataset. 
Measurements will be done automatically and could be subject to some deviation from the real screen refresh rate.

* `min_device_resolution: {w: 1280, h:720}`: minimum device resolution so that the participant can take part in the test.
 Measurements will be done automatically and could be subject to some deviation from the real screen refresh rate.

* `accepted_device:["PC"]`: List of accepted devices (e.g. "PC", "MOBILE"). 
Measurements will be done automatically and could be subject to some deviation from the real screen refresh rate.

