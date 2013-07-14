import datetime
import pytz
from GpxImageLinkifier import GIL
import gpxpy
import gpxpy.gpx
import os
import json

# EXIF timestamps for test images:
# test_files/image_files/jpg/IMG_7106.JPG             2013:05:25 18:40:43
## NOTE: RANIER CAMERA CLOCK WAS AHEAD OF GPS BY ~4m56s
# test_files/image_files/jpg/ranier/DSC_9506.jpg      2012-08-25 17:16:28
# test_files/image_files/jpg/ranier/DSC_9507.jpg      2012-08-25 17:16:33
# test_files/image_files/jpg/ranier/DSC_9508.jpg      2012-08-25 17:17:44
# test_files/image_files/jpg/ranier/DSC_9509.jpg      2012-08-25 17:25:00
## NOTE: BANDERA CAMERA CLOCK WAS IN SYNC WITH GPS
# test_files/image_files/jpg/bandera/DSC_0159.jpg     2013-06-29 15:31:01
# test_files/image_files/jpg/bandera/DSC_0160.jpg     2013-06-29 15:44:16
# test_files/image_files/jpg/bandera/DSC_0161.jpg     2013-06-29 15:44:16
# test_files/image_files/jpg/bandera/DSC_0162.jpg     2013-06-29 15:46:02
CWD = os.path.dirname(os.path.realpath(__file__))
TEST_GPX_PATH1 = os.path.join(CWD, 'test_files/gpx_files/test_gpx_1_pacific.gpx')
TEST_GPX_PATH2 = os.path.join(CWD, 'test_files/gpx_files/test_gpx_2_pacific.gpx')
TEST_IMAGE_PATH = os.path.join(CWD, 'test_files/image_files/jpg/test_image.jpg')
TEST_IMAGE_FOLDER_PATH1 = os.path.join(CWD, 'test_files/image_files/jpg/ranier/')
TEST_IMAGE_FOLDER_PATH2 = os.path.join(CWD, 'test_files/image_files/jpg/bandera/')

gil1 = GIL(TEST_GPX_PATH1, TEST_IMAGE_FOLDER_PATH1)
gil2 = GIL(TEST_GPX_PATH2, TEST_IMAGE_FOLDER_PATH2)


def test_find_match_non_image():
    """find_matches works with lists if properly formatted."""

    # should work
    testlist = [
        {
            "foo": 'correct',
            "timestamp": datetime.datetime.strptime('2012-08-25T20:59:20.1530Z', '%Y-%m-%dT%H:%M:%S.%fZ')
        }
    ]

    bad_testlist = [
        {
            "foo": 'wrong',
            "wrong": datetime.datetime.strptime('2012-08-25T20:59:20.1530Z', '%Y-%m-%dT%H:%M:%S.%fZ')
        }
    ]

    # should not work
    testdict = {
        "something": {
            "foo": 'correct',
            "timestamp": datetime.datetime.strptime('2012-08-25T20:59:20.1530Z', '%Y-%m-%dT%H:%M:%S.%fZ')
        }
    }

    # lists are supported
    assert gil1.find_matches(testlist)[0]['content'] == testlist[0]

    # dicts are not, return 0 matches.
    assert len(gil1.find_matches(testdict)) == 0

    # the dicts in the list must have a timestamp property or they are discarded.
    assert len(gil1.find_matches(bad_testlist)) == 0


def test_get_image_timestamp():
    """tests if a valid datetime object is being returned from the
get_image_timestamp method"""

    dt = datetime.datetime.strptime('2013:05:25 18:40:43', '%Y:%m:%d %H:%M:%S')
    dt = pytz.utc.localize(dt)
    ts = gil1.get_image_timestamp(TEST_IMAGE_PATH)

    assert type(ts) == type(dt)
    assert dt == ts


def test_find_timestamp_gpx_match():
    """find_timestamp_gpx_match returns a gpx point that most closely matches
    the image's timestamp"""
    valid_date = pytz.utc.localize(datetime.datetime.strptime('2012-08-25T20:59:20.1530Z',
                                                              '%Y-%m-%dT%H:%M:%S.%fZ'))

    point = gil1.find_timestamp_gpx_match(valid_date,
                                          gil1.add_gpx_data(TEST_GPX_PATH1))

    assert point.latitude == 46.787799
    assert point.longitude == -121.733713


def test_parse_timeString():
    """tests if the timestring parser works"""

    assert gil1.parse_timeString('4d3h12s') -\
        datetime.timedelta(days=4, hours=3, seconds=12) ==\
        datetime.timedelta(milliseconds=0)


def test_add_gpx_data():
    """add_gpx_data appends to self.datasets and accepts a gpx file path or
    a gpxpy.gpx.GPX object"""
    gil = GIL()
    print gil.gpx_datasets
    parsed_data = gil.add_gpx_data(TEST_GPX_PATH1)

    assert isinstance(parsed_data, gpxpy.gpx.GPX)
    print gil.gpx_datasets
    assert len(gil.gpx_datasets) == 1

    gil.add_gpx_data(parsed_data)

    assert len(gil.gpx_datasets) == 2
    assert isinstance(gil.gpx_datasets[1], gpxpy.gpx.GPX)


def test_timezones():
    """All pytz timezones are supported for tz-images and tz-gpx"""
    gpx_file = open(TEST_GPX_PATH1, 'r')
    gpx_data = gpxpy.parse(gpx_file)
    target_point = gpx_data.tracks[0].segments[0].points[0]
    target_time = target_point.time
    # target point's timestamp is 2012-08-25 20:59:20
    target_ts = datetime.datetime.strptime('2012-08-25 20:59:20', '%Y-%m-%d %H:%M:%S')
    content = [
        {
            "foo": 'correct',
            "timestamp": datetime.datetime.strptime('2012-08-25 20:59:20', '%Y-%m-%d %H:%M:%S')
        }
    ]

    def localize_ts(ts, tz):
        timezone = pytz.timezone(tz)
        return ts + timezone.utcoffset(ts)

    # convert GPX data timezone but not images timezone
    for new_tz in pytz.common_timezones:
        target_point.time = localize_ts(target_time, new_tz)
        gil = GIL(tz_gpx=new_tz, gpx_path=gpx_data)

        assert len(gil.find_matches(content)) == 1

    # convert image timezone but not gpx
    for new_tz in pytz.common_timezones:
        content[0]['timestamp'] = localize_ts(target_ts, new_tz)
        gil = GIL(tz_images=new_tz, gpx_path=gpx_data)

        assert len(gil.find_matches(content)) == 1

    # negative assertion
    for new_tz in pytz.common_timezones:
            # convert GPX data timezone (of the first point) but
            # not images timezone
            target_point.time = localize_ts(target_time, new_tz)

            # set accuracy timedelta to 0 to not get false-positives with the
            # other points in the gpx file that we're not changing.
            gil = GIL(tz_gpx=new_tz, tz_images=new_tz, gpx_path=gpx_data,
                      accuracy='0s')

            # only run assertion on timezones that actually have an offset
            tz = pytz.timezone(new_tz)
            if tz.utcoffset(target_point.time) !=\
                    pytz.utc.utcoffset(target_point.time):
                assert len(gil.find_matches(content)) == 0


def test_to_xml():
    """to_xml returns valid xml"""
    # should work
    testlist = [
        {
            "foo": 'correct',
            "timestamp": datetime.datetime.strptime('2012-08-25T20:59:20.1530Z', '%Y-%m-%dT%H:%M:%S.%fZ')
        }
    ]
    match_latitude = 46.787799
    match_longitude = -121.733713

    gil1.find_matches(testlist)

    gpxpy_data = gpxpy.parse(gil1.to_xml())

    assert gpxpy_data.waypoints[0].latitude == match_latitude
    assert gpxpy_data.waypoints[0].longitude == match_longitude


def test_to_geojson():
    """to_xml returns valid xml"""
    # should work
    testlist = [
        {
            "foo": 'correct',
            "timestamp": datetime.datetime.strptime('2012-08-25T20:59:20.1530Z', '%Y-%m-%dT%H:%M:%S.%fZ')
        }
    ]
    match_latitude = 46.787799
    match_longitude = -121.733713

    gil1.find_matches(testlist)

    gpxpy_data = json.loads(gil1.to_geojson())

    assert gpxpy_data['features'][0]['geometry']['coordinates'][0] == match_longitude
    assert gpxpy_data['features'][0]['geometry']['coordinates'][1] == match_latitude


if __name__ == "__main__":
    pass
