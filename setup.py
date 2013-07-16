from setuptools import setup

setup(
    name='GpxImageLinkifier',
    version='0.1.1',
    author='Austin Happel',
    author_email='austin@austinhappel.com',
    packages=[
        'GpxImageLinkifier',
    ],
    url='https://pypi.python.org/pypi/GpxImageLinkifier',
    license='LICENSE.txt',
    description='Links GPX tracks to photographs by matching the image timestamp (in the EXIF data) to the timestamp in the GPX track supplied.',
    long_description=open('README.txt').read(),
    install_requires=[
        "PIL==1.1.7",
        "gpxpy==0.8.9",
        "lxml==3.2.1",
        "pytz"
    ],
    entry_points={
        'console_scripts': [
            'gil = GpxImageLinkifier.gil:main',
        ]
    },
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Environment :: Console',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    ]
)
