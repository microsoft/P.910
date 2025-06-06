import pandas as pd
import collections
from src import create_input


def test_conv_filename_to_condition():
    create_input.file_to_condition_map.clear()
    pattern = r'.*_c(?P<cond>\d{2})_.*\.mp4'
    result = create_input.conv_filename_to_condition('video_c03_clip.mp4', pattern)
    assert result == collections.OrderedDict([('cond', '03')])


def test_add_clips_random_shape():
    clips = pd.Series(['a.mp4', 'b.mp4', 'c.mp4'])
    df = pd.DataFrame()
    create_input.add_clips_random(clips, 2, df)
    assert df.shape == (2, 2)
    assert set(df.columns) == {'Q0', 'Q1'}
    # ensure all values are from the original list
    for col in df.columns:
        assert set(df[col]).issubset(set(clips))
