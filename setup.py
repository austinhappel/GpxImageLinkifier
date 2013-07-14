from distutils.core import setup
import setuptools

setup(
    name='GpxImageLinkifier',
    version='0.1.0',
    author='Austin Happel',
    author_email='austin@austinhappel.com',
    packages=['GpxImageLinkifier', 'GpxImageLinkifier.test'],
    # scripts=['bin/gil.py', ],
    url='http://pypi.python.org/pypi/GpxImageLinkifier/',
    license='LICENSE.txt',
    description='Links GPX tracks to photographs by matching the image\
    timestamp\ (in the EXIF data) to the timestamp in the GPX track supplied.',
    long_description=open('README.txt').read(),
    install_requires=[
        "PIL==1.1.7",
        "gpxpy==0.8.9",
        "lxml==3.2.1",
        "wsgiref==0.1.2",
    ],
    entry_points={
        'console_scripts': [
            'gil = GpxImageLinkifier.gil:main',
        ]
    }
)
