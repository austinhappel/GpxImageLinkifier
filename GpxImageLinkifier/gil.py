from PIL import Image
from PIL.ExifTags import TAGS
import argparse
import os
import datetime
import gpxpy
import pytz
import json
import re
import sys

# constants
CWD = os.getcwd()


class GIL():

    error_messages = {
        'bad_file': 'File path %s does not exist or is not read/writable.',
        'bad_dir': 'File path %s does not exist or is not a directory.',
        'bad_timezone': 'Bad timezone: %s',
        'required_param': 'Parameter "%s" is required and cannot be None.'
    }

    def __init__(self,
                 gpx_path=None, image_folder=None, output_path=None,
                 output_format='geojson', offset='0s', accuracy='1m',
                 tz_images='UTC', tz_gpx='UTC', image_prefix='',
                 isCLI=False):

        errors = False

        # required arguments
        if gpx_path is None:
            self.write_error(self.error_messages['required_param'] %
                             'gpx_path')

        if image_folder is None:
            self.write_error(self.error_messages['required_param'] %
                             'image_folder')

        if self.validate_file(gpx_path, 'r') is False:
            self.write_error(self.error_messages['bad_file'] % gpx_path)
            errors = True
        else:
            self.gpx_path = os.path.abspath(gpx_path)

        # parse image folder
        if self.validate_dir(image_folder) is False:
            self.write_error(self.error_messages['bad_dir'] %
                             image_folder)
            errors = True
        else:
            self.image_folder = os.path.abspath(image_folder)

        # parse images timezone
        if self.validate_timezone(tz_images) is False:
            self.write_error(self.error_messages['bad_timezone'] %
                             tz_images)
            errors = True
        else:
            self.tz_images = pytz.timezone(tz_images)

        # parse gpx timezone
        if self.validate_timezone(tz_gpx) is False:
            self.write_error(self.error_messages['bad_timezone'] % tz_gpx)
            errors = True
        else:
            self.tz_gpx = pytz.timezone(tz_gpx)

        # parse output option
        if output_path is not None:
            if self.validate_file(output_path, 'w') is False:
                self.write_error(self.error_messages['bad_file'] % output_path)
                errors = True
            else:
                self.output_path = os.path.abspath(output_path)

        else:
            self.output_path = None

        # parse offset and accuracy timedelta strings
        self.offset = self.parse_timeString(offset)
        self.accuracy = self.parse_timeString(accuracy)
        self.image_prefix = image_prefix

        # automatically find matches and display output if being used from CLI.
        # ---------------------------------------------------------------------
        if isCLI is True:
            # stop if there are errors with the input
            if errors is True:
                return

            matches = self.find_matches(self.gpx_path, self.image_folder)

            if output_format == 'geojson':
                result = self.output_geojson(matches)

            if self.output_path is None:
                self.write_to_cli(result)
            else:
                f = open(self.output_path, 'w')
                f.write(result)
                f.close()

    @classmethod
    def parse_arguments(self):
        # argument parsing
        parser = argparse.ArgumentParser(
            description='''Links timestamps in photographs to timestamps in GPX
data. You can either add GPX data to your images' EXIF data, or output a
geojson file with waypoints linking images to specific GPX tracks.''',
            # usage='',
            # epilog='',
            add_help=True,
        )

        parser.add_argument('gpx_path',
                            type=str,
                            help='Path to the GPX file to use.'
                            )

        parser.add_argument('image_folder',
                            type=str,
                            help='Path to the image files to use.'
                            )

        parser.add_argument('--output-path',
                            '-o',
                            type=str,
                            help='Output file path.'
                            )

        parser.add_argument('--output-format',
                            '-t',
                            type=str,
                            help='The output format. Options are geojson or\
                            gpx. Defaults to geojson.',
                            choices=['geojson', 'gpx'],
                            default='geojson'
                            )

        parser.add_argument('--accuracy',
                            '-a',
                            type=str,
                            help='''The timeframe that determines a positive
match. Defaults to 1m. Use "s" for seconds, "m" for minutes and "h" for hours.
For example input like: 2h20m means any time within a range of 2 hours and 20
minutes will count as a match. Defaults to 1m.''',
                            default='1m'
                            )

        parser.add_argument('--offset',
                            type=str,
                            help='''The amount of time to offset GPX timestamps
before comparing them to photo timestamps. Useful if the clocks on your GPS and
camera are not in sync. Defaults to 0. Use a prefix of "+" to add time and "-"
to subtract time. Use "s" for seconds, "m" for minutes and "h" for hours. For
example input like: 2h20m means 2 hours and 20 minutes will be added to GPX
timestamps before comparing timestamps on your images.''',
                            default='0s'
                            )

        parser.add_argument('--tz-images',
                            type=str,
                            help='The timezone the image timestamps are in.',
                            default='UTC'
                            )

        parser.add_argument('--tz-gpx',
                            type=str,
                            help='The timezone the GPX timestamps are in.',
                            default='UTC'
                            )
        parser.add_argument('--image-prefix',
                            type=str,
                            help='''A string prefix to add to matched image
filenames in the output data.''',
                            default=''
                            )
        args = parser.parse_args()
        return args

    # globals
    gpx_datasets = []

    def parse_timeString(self, timestring):
        """Parses a timestring like "1m2s" or "3h2m1s" into a timedelta"""
        expression = '((?P<days>[0-9]*)[dD])*((?P<hours>[0-9]*)[hH])*((?P<minutes>[0-9]*)[mM])*((?P<seconds>[0-9]*)[sS])*'
        time = re.search(expression, timestring)
        days = int(time.group('days')) if time.group('days') is not None else 0
        hours = int(time.group('hours')) if time.group('hours') is not None else 0
        minutes = int(time.group('minutes')) if time.group('minutes') is not None else 0
        seconds = int(time.group('seconds')) if time.group('seconds') is not None else 0
        return datetime.timedelta(days=days,
                                  hours=hours,
                                  minutes=minutes,
                                  seconds=seconds)

    def get_gpx_data(self, path):
        """Parses a gpx file into a gpxpy object"""
        gpx_file = open(path, 'r')
        parsed_gpx_data = gpxpy.parse(gpx_file)
        self.gpx_datasets.append(parsed_gpx_data)
        return parsed_gpx_data

    def get_image_timestamp(self, path):
        """Gets the timestamp of a photo from its exif data."""
        info = {}
        i = Image.open(path)
        exif = i._getexif()
        for tag, value in exif.items():
            decoded = TAGS.get(tag, tag)
            info[decoded] = value

        timestamp = datetime.datetime.strptime(info['DateTime'],
                                               '%Y:%m:%d %H:%M:%S')

        # localize timestamp to desired timezone, then convert that to UTC.
        timestamp = self.tz_images.localize(timestamp)

        return timestamp.astimezone(pytz.utc)

    def find_timestamp_gpx_match(self, target_datetime, gpx_data,
                                 accuracyDelta=datetime.timedelta(minutes=1),
                                 offsetDelta=datetime.timedelta(seconds=0)):

        matches = []

        def check_for_match(point):
            ts = to_tz(point.time + offsetDelta)
            if abs(ts - target_datetime) < accuracyDelta:
                matches.append(point)

        def check_closest_point_match(matches):
            """Compares GPX points to find which one most closely matches
            the target"""

            best_point_match = None

            for match in matches:
                if best_point_match is None or\
                    (abs(to_tz(match.time + offsetDelta) - target_datetime)
                        < abs(to_tz(best_point_match.time + offsetDelta) - target_datetime)):
                    best_point_match = match

            return best_point_match

        def to_tz(ts):
            ts = self.tz_gpx.localize(ts)
            return ts.astimezone(pytz.utc)

        # loop through tracks and search for match
        for track in gpx_data.tracks:
            for segment in track.segments:
                for point in segment.points:
                    check_for_match(point)

        for waypoint in gpx_data.waypoints:
            check_for_match(point)

        return check_closest_point_match(matches)

    # -------------------------------------------------------------------------
    # CLI-related methods
    # -------------------------------------------------------------------------

    def validate_timezone(self, timezoneString):
        try:
            pytz.timezone(timezoneString)
        except pytz.exceptions.UnknownTimeZoneError:
            return False

        return True

    def validate_file(self, filepath, mode):
        fp = os.path.abspath(filepath)
        try:
            open(fp, mode)
        except IOError:
            return False

        return True

    def validate_dir(self, filepath):
        fp = os.path.abspath(filepath)
        return os.path.isdir(fp)

    # -------------------------------------------------------------------------
    # Output related methods
    # -------------------------------------------------------------------------

    def output_geojson(self, matches=None):
        """Generates a geojson file linking lat/long with images."""

        if matches is None:
            matches = self.matches

        geojson_python = {
            "type": "FeatureCollection",
            "features": []
        }
        for match in matches:
            geojson_python['features'].append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        match["gpx"].longitude,
                        match["gpx"].latitude,
                        match["gpx"].elevation
                    ]
                },
                "properties": {
                    "name": "Photo",
                    "image": self.image_prefix + match["image"]["name"]
                }
            })

        return json.dumps(geojson_python, indent=4)

    def write_to_cli(self, output):
        sys.stdout.write(output + '\n\r')

    def write_to_file(self, filepath, content):
        f = open(filepath, 'w')
        f.write(content)
        f.close

    def write_error(self, output):
        self.write_to_cli('ERROR: ' + output)

    # -------------------------------------------------------------------------
    # Actionable methods
    # -------------------------------------------------------------------------

    def find_matches(self, gpx_path, image_path):
        gpx_data = self.get_gpx_data(gpx_path)
        abs_image_path = os.path.abspath(image_path)
        images = os.listdir(os.path.abspath(image_path))
        image_gpx_links = []
        supported_file_extensions = [
            '.jpg',
            '.JPG',
            '.jpg',
            '.jpeg'
        ]

        for image in images:
            image_path = os.path.join(abs_image_path, image)
            file_name, file_extension = os.path.splitext(image_path)

            # only loop through supported files
            if file_extension in supported_file_extensions:
                match = self.find_timestamp_gpx_match(
                    self.get_image_timestamp(image_path),
                    gpx_data,
                    accuracyDelta=self.accuracy,
                    offsetDelta=self.offset)

                if (match is not None):
                    image_gpx_links.append({
                        "image": {
                            "name": image,
                        },
                        "gpx": match
                    })

        self.matches = image_gpx_links
        return image_gpx_links


def main():
    args = GIL.parse_arguments()
    GIL(gpx_path=args.gpx_path,
        image_folder=args.image_folder,
        image_prefix=args.image_prefix,
        output_path=args.output_path,
        output_format=args.output_format,
        offset=args.offset,
        tz_images=args.tz_images,
        tz_gpx=args.tz_gpx,
        isCLI=True)


if __name__ == "__main__":
    main()