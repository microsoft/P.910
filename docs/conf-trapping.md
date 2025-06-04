 [Home](../README.md) > [Preparation](preparation.md) > [Preparation for Degradation Category Rating (DCR)](prep_dcr.md) > Configure for `create_trapping_clips.py`
 
 # Configure for `create_trapping_Clips.py`
 
 This describes the configuration for the `create_trapping_clips` script. A sample configuration file can be found in
  `configurations\trapping.cfg`.
 The `create_trapping_clips` script creates the trapping clips using a subset of videos in the original dataset. 
 For each video, it will use the video parts from begining and end, and add a text message in between asking participant 
 to select an specific answer to show their attention. 
  
 ## `[trappings]`
 * `messages_line1`, `messages_line2`: the message to be shown to the participant. `{0}` will be replaced with a number 
 between `scale_min`, and `scale_max`.   
 `message_duration_in_seconds`: for how long should the message be shown
 `scale_min`: minimum score that can be selected using the scale e.g. 1.
 `scale_max`: maximum score that can be selected using the scale e.g. 5.
  
 **One** of the following options should be used:
 
 * `include_from_source_stimuli_in_second = 2`: use first 2 seconds from the `source` clips to generate the trapping clips.
 It may lead to a clip duration that is different from the rest of clips which should be rated. 
 
* `keep_original_duration = true`: As a result each generated clips will be as long as the corresponding original clip.
It is the recommended setting.

If the default font `arial.ttf` is not available on your system, provide the path to a TrueType font file using the `--font` argument when running `create_trapping_clips.py`.
 
  