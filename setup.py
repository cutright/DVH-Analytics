from setuptools import setup, find_packages
from options import DefaultOptions

requires = [
    'wxpython',
    'pypubsub',
    'numpy',
    'scipy',
    'pydicom >= 0.9.9',
    'matplotlib',
    'six >= 1.5',
    'dicompyler-core',
    'Jinja2',
    'PyYaml',
    'bokeh >= 1.0.4',
    'python-dateutil',
    'psycopg2-binary',
    'shapely[vectorized]',
    'statsmodels',
]

setup(
    name='dvh-analytics-desktop',
    include_package_data=True,
    packages=find_packages(),
    version=VERSION,
    description='Create a database of DVHs, GUI with wxPython, plots with Bokeh',
    author='Dan Cutright',
    author_email='dan.cutright@gmail.com',
    url='https://github.com/cutright/DVH-Analytics',
    download_url='https://github.com/cutright/DVH-Analytics/archive/master.zip',
    license="MIT License",
    keywords=['dvh', 'radiation therapy', 'research', 'dicom', 'dicom-rt', 'bokeh', 'analytics', 'wxpython'],
    classifiers=[],
    install_requires=requires,
    entry_points={
        'console_scripts': [
            'dvh=dvh.__main__:main',
        ],
    },
    long_description="""DVH Database for Clinicians and Researchers
    
    DVH Analytics is a software application to help radiation oncology departments build an in-house database of 
    treatment planning data for the purpose of historical comparisons and statistical analysis. This code is still in 
    development. Please contact the developer if you are interested in testing or collaborating.

    The application builds a SQL database of DVHs and various planning parameters from DICOM files (i.e., Plan, Structure, 
    Dose). Since the data is extracted directly from DICOM files, we intend to accommodate an array of treatment planning 
    system vendors.
    """
)