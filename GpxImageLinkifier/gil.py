from PIL import Image
from PIL.ExifTags import TAGS
import argparse
import os
import datetime
import gpxpy
import gpxpy.gpx
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
                 output_format='geojson', offset_gpx='0s', offset_images='0s',
                 accuracy='1m', tz_images='UTC', tz_gpx='UTC', image_prefix='',
                 verbose=False, isCLI=False):

        errors = False
        self.isCLI = isCLI
        self.gpx_datasets = []

        # required arguments
        if gpx_path is not None:
            if isinstance(gpx_path, str):
                if self.validate_file(gpx_path, 'r') is False:
                    self.write_error(self.error_messages['bad_file'] % gpx_path)
                    errors = True
                else:
                    self.add_gpx_data(os.path.abspath(gpx_path))
            elif isinstance(gpx_path, gpxpy.gpx.GPX):
                self.add_gpx_data(gpx_path)

        # parse image folder
        if image_folder is not None:
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
        self.offset_gpx = self.parse_timeString(offset_gpx)
        self.offset_images = self.parse_timeString(offset_images)
        self.accuracy = self.parse_timeString(accuracy)
        self.image_prefix = image_prefix
        self.verbose = verbose

        # automatically find matches and display output if being used from CLI.
        # ---------------------------------------------------------------------
        if isCLI is True:
            # stop if there are errors with the input
            if errors is True:
                return

            matches = self.find_matches(self.image_folder)

            if output_format == 'geojson':
                result = self.to_geojson()
            elif output_format == 'gpx':
                result = self.to_gpx()

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

        parser.add_argument('--offset-gpx',
                            type=str,
                            help='''The amount of time to ADD to GPX timestamps
before comparing them to photo timestamps. Useful if the clocks on your GPS and
camera are not in sync. Defaults to 0. Use a prefix of "+" to add time and "-"
to subtract time. Use "s" for seconds, "m" for minutes and "h" for hours. For
example input like: 2h20m means 2 hours and 20 minutes will be added to GPX
timestamps before comparing timestamps on your images.''',
                            default='0s'
                            )

        parser.add_argument('--offset-images',
                            type=str,
                            help='''The amount of time to ADD to image timestamps
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

        parser.add_argument('-v',
                            '--verbose',
                            help='''Display detailed logging information.''',
                            action='store_true'
                            )
        args = parser.parse_args()
        return args

    def add_gpx_data(self, path):
        """Appends new gpx data to self.gpx_datasets. Will parse a gpx file if
        path is a file path, otherwise if path is a gpxpy.gpx.GPX object, it
        will add the object directly to self.gpx_datasets."""

        if isinstance(path, gpxpy.gpx.GPX):
            self.gpx_datasets.append(path)
            return path
        else:
            gpx_file = open(path, 'r')
            parsed_gpx_data = gpxpy.parse(gpx_file)
            self.gpx_datasets.append(parsed_gpx_data)
            return parsed_gpx_data

    def localize_image_timestamp(self, ts):
        # localize timestamp to desired timezone, then convert that to UTC.
        timestamp = self.tz_images.localize(ts)

        return timestamp.astimezone(pytz.utc)

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

        return self.localize_image_timestamp(timestamp)

    def find_timestamp_gpx_match(self, target_datetime, gpx_data=None,
                                 accuracyDelta=datetime.timedelta(minutes=1),
                                 offsetGpxDelta=datetime.timedelta(seconds=0),
                                 offsetImageDelta=datetime.timedelta(seconds=0)):

        matches = []

        target_datetime = target_datetime + offsetImageDelta

        if gpx_data is None:
            gpx_data = self.gpx_datasets

        def check_for_match(point):
            ts = to_tz(point.time + offsetGpxDelta)

            self.log('GPX Point timestamp: %s' % point.time)
            self.log('GPX Point timestamp + offset: %s' % ts)
            self.log('Time delta of point - target timestamp: %s' % abs(ts - target_datetime))
            if abs(ts - target_datetime) < accuracyDelta:
                matches.append(point)

        def check_closest_point_match(matches):
            """Compares GPX points to find which one most closely matches
            the target"""

            best_point_match = None

            for match in matches:
                if best_point_match is None or\
                    (abs(to_tz(match.time + offsetGpxDelta) - target_datetime)
                        < abs(to_tz(best_point_match.time + offsetGpxDelta) - target_datetime)):
                    best_point_match = match

            return best_point_match

        def to_tz(ts):
            """localize a timestamp to the same timezone as the GPX data,
            then return it's UTC equivalent for comparison."""
            ts = self.tz_gpx.localize(ts)
            return ts.astimezone(pytz.utc)

        def walk_gpx(data):
            """walk gpxpy data tracks and waypoints, looking for
            closest match."""
            for track in data.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        check_for_match(point)

            for waypoint in data.waypoints:
                check_for_match(point)

        if isinstance(gpx_data, list):
            # gpx_data is internally stored array of gpx datasets. Need an
            # extra loop.
            for data in gpx_data:
                walk_gpx(data)

        elif isinstance(gpx_data, gpxpy.gpx.GPX):
            # gpx_data is straight up gpxpy track. Start walking it.
            walk_gpx(gpx_data)

        return check_closest_point_match(matches)

    def save_matches_as_gpxpy(self):
        gpx_data = gpxpy.gpx.GPX()

        # Create points:
        for match in self.matches:
            gpx_data.waypoints.append(gpxpy.gpx.GPXWaypoint(
                longitude=match['location'].longitude,
                latitude=match['location'].latitude,
                elevation=match['location'].elevation,
                name=str(match['content'])))

        self.matches_gpxpy = gpx_data

    # -------------------------------------------------------------------------
    # CLI-related methods
    # -------------------------------------------------------------------------

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

    # CLI output methods
    # -------------------------------------------------------------------------

    def log(self, msg):
        if self.verbose is True:
            self.write_to_cli(msg)

    def write_to_cli(self, output):
        sys.stdout.write(output + '\n\r')

    def write_to_file(self, filepath, content):
        f = open(filepath, 'w')
        f.write(content)
        f.close

    def write_error(self, output):
        self.write_to_cli('ERROR: ' + output)

    # -------------------------------------------------------------------------
    # Output related methods
    # -------------------------------------------------------------------------

    def to_geojson(self):
        """Generates a geojson file linking lat/long with images."""

        geojson_python = {
            "type": "FeatureCollection",
            "features": []
        }

        for match in self.matches:
            geojson_python['features'].append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        match["location"].longitude,
                        match["location"].latitude,
                        match["location"].elevation
                    ]
                },
                "properties": {
                    "content": self.image_prefix + str(match["content"])
                }
            })

        return json.dumps(geojson_python, indent=4)

    def to_xml(self):
        """returns GPX XML of the matches found."""
        return self.matches_gpxpy.to_xml()

    # -------------------------------------------------------------------------
    # Actionable methods
    # -------------------------------------------------------------------------

    def find_matches(self, content):
        """finds GPX timestamp matches for the content passed in. Content can
        be either 1) an image path string or 2) a list/dict of objects with a
        timestamp property."""
        gpx_data = self.gpx_datasets
        gpx_matches = []
        supported_file_extensions = [
            '.jpg',
            '.JPG',
            '.jpg',
            '.jpeg'
        ]

        def add_match(content, gpx_match):
            if (gpx_match is not None):
                gpx_matches.append({
                    "content": content,
                    "location": gpx_match
                })

        if isinstance(content, str):
            # content is an image path.
            abs_image_path = os.path.abspath(content)
            images = os.listdir(os.path.abspath(content))

            for image in images:
                image_path = os.path.join(abs_image_path, image)
                file_name, file_extension = os.path.splitext(image_path)
                self.log('====================')
                self.log('Finding match for: %s' % image)

                # only loop through supported files
                if file_extension in supported_file_extensions:
                    match = self.find_timestamp_gpx_match(
                        self.get_image_timestamp(image_path),
                        gpx_data,
                        accuracyDelta=self.accuracy,
                        offsetGpxDelta=self.offset_gpx,
                        offsetImageDelta=self.offset_images)

                    add_match(image, match)

        elif isinstance(content, list):
            # content is a dict or list, no need for image exif parsing
            for item in content:
                if 'timestamp' in item and isinstance(item['timestamp'], datetime.datetime):
                    match = self.find_timestamp_gpx_match(
                        self.localize_image_timestamp(item['timestamp']),
                        gpx_data,
                        accuracyDelta=self.accuracy,
                        offsetGpxDelta=self.offset_gpx,
                        offsetImageDelta=self.offset_images)

                    add_match(item, match)

        self.matches = gpx_matches
        self.save_matches_as_gpxpy()

        return gpx_matches


def main():
    args = GIL.parse_arguments()
    GIL(gpx_path=args.gpx_path,
        image_folder=args.image_folder,
        image_prefix=args.image_prefix,
        output_path=args.output_path,
        output_format=args.output_format,
        offset_gpx=args.offset_gpx,
        offset_images=args.offset_images,
        tz_images=args.tz_images,
        tz_gpx=args.tz_gpx,
        verbose=args.verbose,
        isCLI=True)


if __name__ == "__main__":
    main()