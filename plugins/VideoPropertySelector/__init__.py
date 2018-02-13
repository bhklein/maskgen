import maskgen
import numpy as np
import os
from maskgen.video_tools import getMeta

"""
Select FFPROBE properties
"""



def __get_channel_data(source_data, codec_type):
    for data in source_data:
        if data['codec_type'] == codec_type:
            return data

def transform(img, source, target, **kwargs):
    meta = getMeta(source,show_streams=True)
    video_data = __get_channel_data(meta[0],'video')
    return video_data,None

def operation():
    return {'name': 'SelectRegion',
            'category': 'Select',
            'software': 'maskgen',
            'type': 'selector',
            'version': maskgen.__version__[0:6],
            'description': 'Gather Meta Information',
            'transitions': [
                'video.video'
            ]
            }


def suffix():
    return '.png'