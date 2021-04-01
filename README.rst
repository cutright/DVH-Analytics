DVH Analytics
=============

|logo|


DVH Analytics (DVHA) is a software application for building a local database of radiation oncology 
treatment planning data. It imports data from DICOM-RT files (*i.e.*, plan, dose, and structure), creates a SQL database,
provides customizable plots, and provides tools for generating linear, multi-variable, and machine learning 
regressions.

|pypi| |Docs| |lgtm-cq| |lgtm| |lines| |repo-size| |code-style|


Documentation
-------------
Be sure to check out the `latest release <https://github.com/cutright/DVH-Analytics/releases>`__
for the user manual PDF, which is geared towards the user interface. For
power-users, `dvha.readthedocs.io <http://dvha.readthedocs.io>`__
contains detailed documentation for backend tools (*e.g.*, if you want to
perform queries with python commands).

Executables
-----------
Executable versions of DVHA can be found `here <https://github.com/cutright/DVH-Analytics/releases>`__.
Please keep in mind this software is still in beta. If you have issues, compiling from source may be more informative. 


About
-----
|screenshot|

In addition to viewing DVH data, this software provides methods to:

- download queried data
- create time-series plots of various planning and dosimetric variables
- calculate correlations
- generate multi-variable linear and machine learning regressions
- share regression models with other DVHA users
- additional screenshots available `here <https://github.com/cutright/DVH-Analytics/issues/9>`__


The code is built with these core libraries:

* `wxPython Phoenix <https://github.com/wxWidgets/Phoenix>`__ - Build a native GUI on Windows, Mac, or Unix systems
* `Pydicom <https://github.com/pydicom/pydicom>`__ - Read, modify and write DICOM files with python code
* `dicompyler-core <https://github.com/dicompyler/dicompyler-core>`__ - A library of core radiation therapy modules for DICOM RT
* `Bokeh <https://github.com/bokeh/bokeh>`__ - Interactive Web Plotting for Python
* `scikit-learn <https://github.com/scikit-learn/scikit-learn>`__ - Machine Learning in Python


Installation
------------
To install via pip:

.. code-block:: console

    $ pip install dvha

If you've installed via pip or setup.py, launch from your terminal with:

.. code-block:: console

    $ dvha

If you've cloned the project, but did not run the setup.py installer, launch DVHA with:

.. code-block:: console

    $ python dvha_app.py

See our `installation notes <https://github.com/cutright/DVH-Analytics/blob/master/install_notes.md>`__ for potential
Shapely install issues on MS Windows and help setting up a PostgreSQL database if it is preferred over SQLite3. 


Dependencies
------------
* `Python <https://www.python.org>`__ >3.5
* `wxPython Phoenix <https://github.com/wxWidgets/Phoenix>`__ >= 4.0.4, < 4.1.0
* `Pydicom <https://github.com/darcymason/pydicom>`__ >=1.4.0
* `dicompyler-core <https://pypi.python.org/pypi/dicompyler-core>`__ >= 0.5.4
* `Bokeh <http://bokeh.pydata.org/en/latest/index.html>`__ >= 1.2.0, < 2.0.0
* `PostgreSQL <https://www.postgresql.org/>`__ (optional) and `psycopg2 <http://initd.org/psycopg/>`__
* `SQLite3 <https://docs.python.org/2/library/sqlite3.html>`__
* `SciPy <https://scipy.org>`__
* `NumPy <http://numpy.org>`__
* `Shapely <https://github.com/Toblerity/Shapely>`__ < 1.7.0
* `Statsmodels <https://github.com/statsmodels/statsmodels>`__ >=0.8.0
* `Scikit-image <https://scikit-image.org>`__
* `Scikit-learn <http://scikit-learn.org>`__ >= 0.21.0
* `regressors <https://pypi.org/project/regressors/>`__
* `RapidFuzz <https://github.com/rhasspy/rapidfuzz>`__
* `selenium <https://github.com/SeleniumHQ/selenium/>`__
* `PhantomJS <https://phantomjs.org/>`__
* `DVHA MLC Analyzer <http://mlca.dvhanalytics.com>`__


Support
-------
If you like DVHA and would like to support our mission, all we ask is that you cite us if we helped your 
publication, or help the DVHA community by submitting bugs, issues, feature requests, or solutions on the 
`issues page <https://github.com/cutright/DVH-Analytics/issues>`__.

Cite
----
DOI: `https://doi.org/10.1002/acm2.12401 <https://doi.org/10.1002/acm2.12401>`__
  Cutright D, Gopalakrishnan M, Roy A, Panchal A, and Mittal BB. "DVH Analytics: A DVH database for clinicians and researchers." Journal of Applied Clinical Medical Physics 19.5 (2018): 413-427.

The previous web-based version described in the above publication can be found 
`here <https://github.com/cutright/DVH-Analytics-Bokeh>`__ but is no longer being developed.

Related Publications
--------------------
DOI: `http://doi.org/10.1002/mp.14795 <http://doi.org/10.1002/mp.14795>`__
  Roy A, Widjaja R, Wang M, Cutright D, Gopalakrishnan M, Mittal BB. "Treatment plan quality control using multivariate control charts." Medical Physics. (2021).

DOI: `https://doi.org/10.1016/j.adro.2019.11.006 <https://doi.org/10.1016/j.adro.2019.11.006>`__
  Roy A, Cutright D, Gopalakrishnan M, Yeh AB, and Mittal BB. "A Risk-Adjusted Control Chart to Evaluate IMRT Plan Quality." Advances in Radiation Oncology (2019).


Selected Studies Using DVHA
---------------------------
*5,000 Patients*  
National Cancer Institute (5R01CA219013-03): Active 8/1/17 → 7/31/22  
`Retrospective NCI Phantom-Monte Carlo Dosimetry for Late Effects in Wilms Tumor <https://www.scholars.northwestern.edu/en/projects/retrospective-nci-phantom-monte-carlo-dosimetry-for-late-effects--5>`__
Brannigan R (Co-Investigator), Kalapurakal J (PD/PI), Kazer R (Co-Investigator)

*265 Patients*  
DOI: `https://doi.org/10.1016/j.ijrobp.2019.06.2509 <https://doi.org/10.1016/j.ijrobp.2019.06.2509>`__
Gross J, et al. "Determining the organ at risk for lymphedema after regional nodal irradiation in 
breast cancer." International Journal of Radiation Oncology* Biology* Physics 105.3 (2019): 649-658.

.. |pypi| image:: https://img.shields.io/pypi/v/dvha.svg
   :target: https://pypi.org/project/dvha/
   :alt: pypi

.. |lgtm-cq| image:: https://img.shields.io/lgtm/grade/python/g/cutright/DVH-Analytics.svg?logo=lgtm&label=code%20quality
   :target: https://lgtm.com/projects/g/cutright/DVH-Analytics/context:python
   :alt: lgtm code quality

.. |lgtm| image:: https://img.shields.io/lgtm/alerts/g/cutright/DVH-Analytics.svg?logo=lgtm
   :target: https://lgtm.com/projects/g/cutright/DVH-Analytics/alerts
   :alt: lgtm

.. |Docs| image:: https://readthedocs.org/projects/dvha/badge/?version=latest
   :target: https://dvha.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

.. |lines| image:: https://img.shields.io/tokei/lines/github/cutright/dvh-analytics
   :target: https://img.shields.io/tokei/lines/github/cutright/dvh-analytics
   :alt: Lines of code

.. |repo-size| image:: https://img.shields.io/github/languages/code-size/cutright/dvh-analytics
   :target: https://img.shields.io/github/languages/code-size/cutright/dvh-analytics
   :alt: Repo Size

.. |code-style| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Code style: black

.. |logo| raw:: html

    <a>
      <img src="https://user-images.githubusercontent.com/4778878/92505112-351c7780-f1c9-11ea-9b5c-0de1ad2d131d.png" width='400' alt="DVHA logo"/>
    </a>

.. |screenshot| raw:: html

    <img src='https://user-images.githubusercontent.com/4778878/61014986-8cb61d80-a34f-11e9-8316-a810669f119f.jpg' align='right' width='300' alt="DVH Analytics screenshot">
