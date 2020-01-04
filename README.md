<h3 align="center">
  <img src="https://user-images.githubusercontent.com/4778878/30754005-b7a7e808-9f86-11e7-8b0f-79d1006babdf.jpg" alt="fastlane Logo" />
</h3>

Welcome to the brand new DVH Analytics, rewritten as a native OS application with wxPython. This version is currently 
only available as source code during the public beta. Compiled versions will be available after successful testing. The 
previous web-based version can be found [here](https://github.com/cutright/DVH-Analytics-Bokeh) but is no longer being 
developed.

### How to Run
If you have macOS Mojave or later, we have a compiled executable beta.  See [this](https://github.com/cutright/DVH-Analytics/issues/23) post for information.

Install via pip:
~~~
$ pip install dvha
~~~
If you've installed via pip or setup.py, launch from your terminal with:
~~~
$ dvha
~~~
If you've cloned the project, but did not run the setup.py installer, launch DVHA with:
~~~
$ python dvha_app.py
~~~
See our [installation notes](https://github.com/cutright/DVH-Analytics/blob/master/install_notes.md) for SQL setup and 
potential Shapely install issues. 

### About
DVH Analytics is a software application to help radiation oncology departments build an in-house database of treatment 
planning data for the purpose of historical comparisons and statistical analysis.

The application builds a SQL database of DVHs and various planning parameters from DICOM files 
(i.e., Plan, Structure, Dose). Since the data is extracted directly from DICOM files, we intend
to accommodate an array of treatment planning system vendors.

<img src='https://user-images.githubusercontent.com/4778878/61014986-8cb61d80-a34f-11e9-8316-a810669f119f.jpg' align='right' width='400' alt="DVH Analytics screenshot">

In addition to viewing DVH data, this software provides methods to:

- download queried data
- create time-series plots of various planning and dosimetric variables
- calculate correlations
- generate multi-variable linear and machine learning regressions.
- Additional screenshots available [here](https://github.com/cutright/DVH-Analytics/issues/9).


The code is built upon these core libraries:
* [wxPython Phoenix](https://github.com/wxWidgets/Phoenix) - Build a native GUI on Windows, Mac, or Unix systems
* [Pydicom](https://github.com/pydicom/pydicom) - Read, modify and write DICOM files with python code
* [dicompyler-core](https://github.com/dicompyler/dicompyler-core) - Extensible radiation therapy research platform and viewer for DICOM and DICOM RT
* [Bokeh](https://github.com/bokeh/bokeh) - Interactive Web Plotting for Python
* [scikit-learn](https://github.com/scikit-learn/scikit-learn) - Machine Learning in Python


### Citing DVH Analytics
DOI: [https://doi.org/10.1002/acm2.12401](https://doi.org/10.1002/acm2.12401)  
Cutright D, Gopalakrishnan M, Roy A, Panchal A, and Mittal BB. "DVH Analytics: A DVH database for clinicians and researchers." Journal of Applied Clinical Medical Physics 19.5 (2018): 413-427.

DOI: [https://doi.org/10.1016/j.adro.2019.11.006](https://doi.org/10.1016/j.adro.2019.11.006)  
Roy A, Cutright D, Gopalakrishnan M, Yeh AB, and Mittal BB. "A Risk-Adjusted Control Chart to Evaluate IMRT Plan Quality." Advances in Radiation Oncology (2019).


### Dependencies
* [Python](https://www.python.org) >3.5
* [wxPython Phoenix](https://github.com/wxWidgets/Phoenix) >= 4.0.4
* [Pydicom](https://github.com/darcymason/pydicom) >=1.0
* [dicompyler-core](https://pypi.python.org/pypi/dicompyler-core) 0.5.3
* [Bokeh](http://bokeh.pydata.org/en/latest/index.html) >= 1.2.0
* [PostgreSQL](https://www.postgresql.org/) and [psycopg2](http://initd.org/psycopg/)
* [SciPy](https://scipy.org)
* [NumPy](http://numpy.org)
* [Shapely](https://github.com/Toblerity/Shapely)
* [Statsmodels](https://github.com/statsmodels/statsmodels) 0.8.0
* [Scikit-learn](http://scikit-learn.org)
* [regressors](https://pypi.org/project/regressors/)

