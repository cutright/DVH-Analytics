<a>
  <img src="https://user-images.githubusercontent.com/4778878/30754005-b7a7e808-9f86-11e7-8b0f-79d1006babdf.jpg" height='130' alt="DVHA logo"/>
</a>

---------  

DVH Analytics (DVHA) is a software application for building a local database of radiation oncology 
treatment planning data. It imports data from DICOM-RT files (i.e., plan, dose, and structure), creates a SQL database, 
provides customizable plots, and provides tools for generating linear, multi-variable, and machine learning 
regressions.

<a href="https://pypi.org/project/dvha/">
        <img src="https://img.shields.io/pypi/v/dvha.svg" alt="PyPi Version" /></a>
<a href="https://lgtm.com/projects/g/cutright/DVH-Analytics/context:python">
        <img src="https://img.shields.io/lgtm/grade/python/g/cutright/DVH-Analytics.svg?logo=lgtm&label=code%20quality" alt="LGTM Code Quality" /></a>


DVHA Executables
---------
Executable versions of DVHA can be found [here](https://github.com/cutright/DVH-Analytics/releases). 
Please keep in mind this software is still in beta. If you have issues, compiling from source may be more informative. 


About
---------
<img src='https://user-images.githubusercontent.com/4778878/61014986-8cb61d80-a34f-11e9-8316-a810669f119f.jpg' align='right' width='300' alt="DVH Analytics screenshot">

In addition to viewing DVH data, this software provides methods to:

- download queried data
- create time-series plots of various planning and dosimetric variables
- calculate correlations
- generate multi-variable linear and machine learning regressions
- share regression models with other DVHA users
- additional screenshots available [here](https://github.com/cutright/DVH-Analytics/issues/9)


The code is built with these core libraries:
* [wxPython Phoenix](https://github.com/wxWidgets/Phoenix) - Build a native GUI on Windows, Mac, or Unix systems
* [Pydicom](https://github.com/pydicom/pydicom) - Read, modify and write DICOM files with python code
* [dicompyler-core](https://github.com/dicompyler/dicompyler-core) - A library of core radiation therapy modules for DICOM RT
* [Bokeh](https://github.com/bokeh/bokeh) - Interactive Web Plotting for Python
* [scikit-learn](https://github.com/scikit-learn/scikit-learn) - Machine Learning in Python


Installation
---------
To install via pip:
```
pip install dvha
```
If you've installed via pip or setup.py, launch from your terminal with:
```
dvha
```
If you've cloned the project, but did not run the setup.py installer, launch DVHA with:
```
python dvha_app.py
```
See our [installation notes](https://github.com/cutright/DVH-Analytics/blob/master/install_notes.md) for potential 
Shapely install issues on MS Windows and help setting up a PostgreSQL database if it is preferred over SQLite3. 


Dependencies
---------
* [Python](https://www.python.org) >3.5
* [wxPython Phoenix](https://github.com/wxWidgets/Phoenix) >= 4.0.4
* [Pydicom](https://github.com/darcymason/pydicom) >=1.4.0
* [dicompyler-core](https://pypi.python.org/pypi/dicompyler-core) 0.5.3
* [Bokeh](http://bokeh.pydata.org/en/latest/index.html) >= 1.2.0, < 2.0.0
* [PostgreSQL](https://www.postgresql.org/) (optional) and [psycopg2](http://initd.org/psycopg/)
* [SQLite3](https://docs.python.org/2/library/sqlite3.html)
* [SciPy](https://scipy.org)
* [NumPy](http://numpy.org)
* [Shapely](https://github.com/Toblerity/Shapely)
* [Statsmodels](https://github.com/statsmodels/statsmodels) >=0.8.0
* [Scikit-learn](http://scikit-learn.org) >= 0.21.0
* [regressors](https://pypi.org/project/regressors/)
* [RapidFuzz](https://github.com/rhasspy/rapidfuzz)
* [selenium](https://github.com/SeleniumHQ/selenium/)
* [PhantomJS](https://phantomjs.org/)


Support
---------  
If you like DVHA and would like to support our mission, all we ask is that you cite us if we helped your 
publication, or help the DVHA community by submitting bugs, issues, feature requests, or solutions on the 
[issues page](https://github.com/cutright/DVH-Analytics/issues).

Cite
---------  
DOI: [https://doi.org/10.1002/acm2.12401](https://doi.org/10.1002/acm2.12401)  
Cutright D, Gopalakrishnan M, Roy A, Panchal A, and Mittal BB. "DVH Analytics: A DVH database for clinicians and researchers." Journal of Applied Clinical Medical Physics 19.5 (2018): 413-427.

The previous web-based version described in the above publication can be found 
[here](https://github.com/cutright/DVH-Analytics-Bokeh) but is no longer being developed.

Related Publications
---------  
DOI: [https://doi.org/10.1016/j.adro.2019.11.006](https://doi.org/10.1016/j.adro.2019.11.006)  
Roy A, Cutright D, Gopalakrishnan M, Yeh AB, and Mittal BB. "A Risk-Adjusted Control Chart to Evaluate IMRT Plan Quality." Advances in Radiation Oncology (2019).


Selected Studies Using DVHA
---------  
*5,000 Patients*  
National Cancer Institute (5R01CA219013-03): Active 8/1/17 → 7/31/22  
[Retrospective NCI Phantom-Monte Carlo Dosimetry for Late Effects in Wilms Tumor](https://www.scholars.northwestern.edu/en/projects/retrospective-nci-phantom-monte-carlo-dosimetry-for-late-effects--5)  
Brannigan R (Co-Investigator), Kalapurakal J (PD/PI), Kazer R (Co-Investigator)

*265 Patients*  
DOI: [https://doi.org/10.1016/j.ijrobp.2019.06.2509](https://doi.org/10.1016/j.ijrobp.2019.06.2509)  
Gross J, et al. "Determining the organ at risk for lymphedema after regional nodal irradiation in 
breast cancer." International Journal of Radiation Oncology* Biology* Physics 105.3 (2019): 649-658.