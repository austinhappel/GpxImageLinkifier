import datetime
import pytz
from GpxImageLinkifier import GIL

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

TEST_GPX_PATH1 = 'test_files/gpx_files/20120825-ranier-skyline-trail-raw.gpx'
TEST_GPX_PATH2 = 'test_files/gpx_files/20130629-bandera-mountain-descent.gpx'
TEST_IMAGE_PATH = 'test_files/image_files/jpg/IMG_7106.JPG'
TEST_IMAGE_FOLDER_PATH1 = 'test_files/image_files/jpg/ranier/'
TEST_IMAGE_FOLDER_PATH2 = 'test_files/image_files/jpg/bandera/'

gil1 = GIL(TEST_GPX_PATH1, TEST_IMAGE_FOLDER_PATH1)
gil2 = GIL(TEST_GPX_PATH2, TEST_IMAGE_FOLDER_PATH2)


def test_get_gpx_data():
    """tests that a valid gpxpy-parsed object is returned from get_gpx_data"""

    gpx = gil1.get_gpx_data(TEST_GPX_PATH1)

    assert str(gpx.__module__) == 'gpxpy.gpx'


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
                                          gil1.get_gpx_data(TEST_GPX_PATH1))

    assert point.latitude == 46.787799
    assert point.longitude == -121.733713


def test_parse_timeString():
    """tests if the timestring parser works"""

    assert gil1.parse_timeString('4d3h12s') -\
        datetime.timedelta(days=4, hours=3, seconds=12) ==\
        datetime.timedelta(milliseconds=0)


if __name__ == "__main__":
    pass
