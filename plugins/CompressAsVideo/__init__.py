import maskgen.exif
import maskgen.video_tools

def save_as_video(source, target, donor):
    """
    Saves image file using quantization tables
    :param source: string filename of source image
    :param target: string filename of target (result). target should have same extension as donor.
    :param donor: string filename of donor MP4
    """

    maskgen.video_tools.runffmpeg(['-i', source, '-y', target])

    maskgen.exif.runexif(['-overwrite_original', '-q', '-all=', target])
    maskgen.exif.runexif(['-P', '-q', '-m', '-TagsFromFile', donor, '-all:all', '-unsafe', target])
    maskgen.exif.runexif(['-P', '-q', '-m', '-XMPToolkit=', target])

def transform(img,source,target, **kwargs):
    donor = kwargs['donor']
    save_as_video(source, target, donor[1])
    
    return None,None
    
def operation():
    return ['AntiForensicCopyExif','AntiForensic',
            'Convert video to donor filetype and copy metadata.', 'ffmpeg', '2.8.4']
    
def args():
    return [('donor', None, 'Video with desired metadata')]

def suffix():
    return 'donor'
