from PIL import Image
from PIL.ExifTags import TAGS
import argparse
import os
import datetime
import gpxpy

# constants
CWD = os.getcwd()

# argument parsing
parser = argparse.ArgumentParser(
    description='''Links timestamps in photographs to timestamps in GPX data.
You can either add GPX data to your images' EXIF data, or output a geojson file
with waypoints linking images to specific GPX tracks.''',
    # usage='',
    # epilog='',
    add_help=True,
)

parser.add_argument('gpx',
                    type=str,
                    nargs=1,
                    help='Path to the GPX file to use.'
                    )

parser.add_argument('image_folder',
                    type=str,
                    nargs=1,
                    help='Path to the image files to use.'
                    )

parser.add_argument('--output',
                    '-o',
                    type=str,
                    nargs=1,
                    help='Output path. Defaults to current working directory.',
                    default=CWD
                    )

parser.add_argument('--type',
                    '-t',
                    type=str,
                    nargs=1,
                    help='The output type. Options are geojson or gpx. \
                        Defaults to geojson.',
                    choices=['geojson', 'gpx'],
                    default='geojson'
                    )

parser.add_argument('--accuracy',
                    '-a',
                    type=str,
                    nargs=1,
                    help='''The timeframe that determines a positive match.
Defaults to 1s. Use "s" for seconds, "m" for minutes and "h" for hours. For
 example input like: 2h20m means any time within a range of 2 hours and 20
 minutes will count as a match. Defaults to 1s.''',
                    default='1s'
                    )

parser.add_argument('--offset',
                    type=str,
                    nargs=1,
                    help='''The amount of time to offset GPX timestamps before
 comparing them to photo timestamps. Useful if the clocks on your GPS and
 camera are not in sync. Defaults to 0. Use a prefix of "+" to add time
 and "-" to subtract time. Use "s" for seconds, "m" for minutes and "h" for
 hours. For example input like: 2h20m means 2 hours and 20 minutes will
 be added to GPX timestamps before comparing timestamps on your images.''',
                    default='0'
                    )

args = parser.parse_args()

print args
print args.gpx


def get_exif(fn):
    ret = {}
    i = Image.open(fn)
    info = i._getexif()
    for tag, value in info.items():
        decoded = TAGS.get(tag, tag)
        ret[decoded] = value
    return ret

filename = 'image_files/nef/resized/DSC_0159.JPG'


def parse_timeString():
    """Parses a timestring like "1m2s" or "3h2m1s" into a timedelta"""
    return datetime.timedelta(0)


def get_gpx_data(path):
    """Opens a gpx file and parses it with gpxpy"""

    fileName, fileExtension = os.path.splitext(path)

    if fileExtension is not '.gpx':
        raise ValueError('Target file is not a gpx file.')

    gpx_file = open(os.path.abspath(path), 'r')
    return gpxpy.parse(gpx_file)
