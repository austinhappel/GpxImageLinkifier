===========================
GPX Image Linkifier
===========================

Links your photograph's timestamps to the timestamps in your GPX tracks. Currently, this package will only output geojson linking images to tracks. Your photos' EXIF data will not be changed.

Installation
-------------

You can install this globally if you want. If you do, you'll get access to the ``gil`` commandline command.

::
  
    pip install https://austinhappel.github.com/GpxImageLinkifier/something.tgz
  

Usage
-------

Firstly, try the help::

    gil -h

Very basic usage looks like this::

    gil path/to/tracks.gpx path/to/images_folder/

To output to a file, you'll add the ``--output-path`` parameter::

    gil path/to/tracks.gpx path/to/images_folder/ --output-path ~/Desktop/output.geojson

Timezone differences
'''''''''''''''''''''''

Oh but wait, maybe your camera's clock is on a different timezone than your gps! No biggy. use ``--tz-images`` and ``--tz-gpx``. For their values, use any pytz-friendly timezone code::

    gil path/to/tracks.gpx path/to/images_folder/ --tz-images US/Pacific  --tz-images UTC    
