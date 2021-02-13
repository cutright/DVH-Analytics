# Change log of DVH Analytics

v0.9.5 (2021.02.13)
------------
 - [GUI] Fixed bug preventing User Preferences window from loading if on Windows without Edge being available [Issue 144](https://github.com/cutright/DVH-Analytics/issues/144)
 - [ROI Map] Fixed bug where ROI Map edits didn't update previous imports [Issue 142](https://github.com/cutright/DVH-Analytics/issues/142)
 - [Misc] Catch locale issue between wxWidgets and python [140](https://github.com/cutright/DVH-Analytics/issues/140)

v0.9.4 (2021.02.06)
-------------------------
 - [Import] New OVH calculation [Issue 111](https://github.com/cutright/DVH-Analytics/issues/111)
 - [Import] Bump DVHA-MLCA to 0.2.3.post1 to prevent crash if younge_complexity_score returned 0
 - [GUI] Fix for: Changing locale may cause crash on Windows [Issue 140](https://github.com/cutright/DVH-Analytics/issues/140)

v0.9.3.post1 (2021.01.29)
-------------------------
 - [Import] Fix for [Issue 137](https://github.com/cutright/DVH-Analytics/issues/137)

v0.9.3 (2021.01.14)
--------------------
 - [GUI] Edge backend available for MSW (wxpython >=4.1.1)
 - [GUI] Only visible plots are redrawn on window resizing
 - [Import] Closing import progress, DICOM Import, or main windows terminate file parsing threads
 - [Database Admin] Fixed bug preventing delete by study by StudyInstanceUID [Issue 135](https://github.com/cutright/DVH-Analytics/issues/135)

v0.9.2.post2 (2021.01.09)
--------------------
 - [Import] Use default DVH calc if high resolution fails [Issue 133](https://github.com/cutright/DVH-Analytics/issues/133)

v0.9.2.post1 (2021.01.09)
--------------------
 - [PyPI] Allow dicompyler-core 0.5.5, since 0.5.6 is not on PyPI

v0.9.2 (2021.01.09)
--------------------
 - [Database] Added centroid_dist_to_iso_min and centroid_dist_to_iso_max columns to DVHs table
 - [Linting] Applied Black code style
 - [Docs] Backend documentation at [dvha.readthedocs.io](http://dvha.readthedocs.io)
 - [Import] Resolve import crash when DICOM-RT Plan is missing FractionGroupSequence [Issue 127](https://github.com/cutright/DVH-Analytics/issues/127) 
 - [GUI] Allow for smaller window sizes, set min resolution to 1200 x 700 [Issue 123](https://github.com/cutright/DVH-Analytics/issues/123)
 - [Import] Handle NumberOfFractionsPlanned when stored as a string [Issue 131](https://github.com/cutright/DVH-Analytics/issues/131)

v0.9.1.post1 (2020.12.25)
-------------------------
 - [Import] Check for dicompyler-core version before using 'memmap_rtdose' [Issue #128](https://github.com/cutright/DVH-Analytics/issues/128)

v0.9.1 (2020.12.13)
--------------------
 - [Options] Clicking 'Cancel' in user options properly reloads options from file now
 - [Import] High resolution DVH calculation with interpolation for small volume ROIs [Issue 119](https://github.com/cutright/DVH-Analytics/issues/119)
 - [Import] DVHs in the SQL DB now store 5 decimals instead 2 [Issue 119](https://github.com/cutright/DVH-Analytics/issues/119)
 - [Import] Use dicompyler-core's memory mapping on dvh calculation MemoryError [Issue 119](https://github.com/cutright/DVH-Analytics/issues/119)
 - [ROI Map] Allow commas in roi names [Issue 121](https://github.com/cutright/DVH-Analytics/issues/121)

v0.9.0 (2020.12.4)
--------------------
 - [Database] New feature to apply edits to database by uploading a CSV for SQL commands
 - [Import] Validate custom date and dose values when apply all selected [Issue 116](https://github.com/cutright/DVH-Analytics/issues/116)

v0.8.9.post2 (2020.12.4)
--------------------
 - [Control Chart] Fix bug that crashed DVHA when no dates are available [Issue 115](https://github.com/cutright/DVH-Analytics/issues/115)

v0.8.9.post1 (2020.11.16)
--------------------
 - [Import] Resolved bug where empty ROI slice crashed DTH calculation [Issue 113](https://github.com/cutright/DVH-Analytics/issues/113)

v0.8.9 (2020.11.15)
--------------------
 - [Import] Importing DICOM-RT Dose file no longer causes crash if no matching Plan is found [Issue 105](https://github.com/cutright/DVH-Analytics/issues/105)
 - [Import] Added a Pre-Process DICOM method in DICOM Import window to generate new StudyInstanceUIDs [Issue 106](https://github.com/cutright/DVH-Analytics/issues/106)
 - [Machine Learning] New, more direct, work-flow to get to Machine Learning [Issue 107](https://github.com/cutright/DVH-Analytics/issues/107)
 - [Misc] Properly catch NaN values for ML and Regression [Issue 109](https://github.com/cutright/DVH-Analytics/issues/109)
 - [Import] DTHs now include negative distances (inside the PTV) [Issue 111](https://github.com/cutright/DVH-Analytics/issues/111)
 - [Database] New feature added to recalculate various PTV/ROI metrics

v0.8.8 (2020.11.03)
--------------------
 - [Import] Check FileDataSet object for ReferencedRTPlanSequence before use [Issue 100](https://github.com/cutright/DVH-Analytics/issues/100)
 - [Import] dicompyler-core upgraded for non-HFS DVH support, missing tag catches for RTPLan date/time [Issue 62](https://github.com/cutright/DVH-Analytics/issues/62) and [Issue 99](https://github.com/cutright/DVH-Analytics/issues/99)
 - [Import] Check for copying/moving files to an already existing file path [Issue 103](https://github.com/cutright/DVH-Analytics/issues/103) 
 - [ROI Map] Bug fixes for ROI Manager on Import DICOM screen [Issue 102](https://github.com/cutright/DVH-Analytics/issues/102) 
 - [Misc] Set min size of main view to avoid layout issues [Issue 101](https://github.com/cutright/DVH-Analytics/issues/101)

v0.8.7 (2020.10.21)
--------------------
 - [Import] If DICOM-RT Plan doesn't have a StudyDate, other dicom files with 
 matching StudyInstanceUID will be searched. The StudyDate from the first CT or MR file will be used.
 - [Import] ROI/PTV spread values are now in cm to match displayed units.
 - [Correlation] Bug fix for Group 2 Correlation Matrix [Issue 97](https://github.com/cutright/DVH-Analytics/issues/97)

v0.8.6 (2020.09.17)
--------------------
 - [Import] Don't allow DICOM DVH import from a summed dose grid [Issue 95](https://github.com/cutright/DVH-Analytics/issues/95)
 
v0.8.5 (2020.09.12)
--------------------
 - [Import] DICOM RT-Dose summation bug fix when multiple patient summations occur [Issue 94](https://github.com/cutright/DVH-Analytics/issues/94)
 - [Import] Option to skip copying of images/misc DICOM files to imported directory [Issue 93](https://github.com/cutright/DVH-Analytics/issues/93)

v0.8.4post1 (2020.08.31)
--------------------
 - [PyPI] Correction to MANIFEST.in to include TG263 CSV worksheet

v0.8.4 (2020.07.11)
--------------------
 - [Database] Better exception catch for SQL Write Test
 - [Logging] Redirect print statements to logger
 - [Import] Plan complexities are now fx-weighted sums over Rx complexities
 - [Plotting] Allow for LCL/UCL overrides (e.g., capping pass-rates at 100%)

v0.8.3 (2020.06.11)
--------------------
 - [Database] Initialize SQL tables if needed on Write Test (avoids crash)
 - [Import] Cap DVH max dose to prevent excessive memory use [Issue 83](https://github.com/cutright/DVH-Analytics/issues/83)
 - [Import] Save ROI Map in Import Module pushes ROI Map changes to previous imports as well
 - [Import] When right-clicking ROI, then Add <ROI> as Physician ROI, ensure right-clicked ROI is added as a variation 
 if a different Physician ROI name is used
 - [Plot Visuals] DVH Line selection and nonselection options available in User Settings
 - [Plot Visuals] Fix for [Issue 86](https://github.com/cutright/DVH-Analytics/issues/86)
 - [ROI Map] ROI Types now stored in ROI Map [Issue 81](https://github.com/cutright/DVH-Analytics/issues/81)

v0.8.2 (2020.06.05)
--------------------
 - [SQL] Added a DB write test, execute before importing [Issue 82](https://github.com/cutright/DVH-Analytics/issues/82)
 - [Options] Catch import of older incompatible options [Issue 84](https://github.com/cutright/DVH-Analytics/issues/84)
 - [Import] Catch rapidfuzz import errors, disable name prediction rather than crash [Issue 82](https://github.com/cutright/DVH-Analytics/issues/82)
 
v0.8.1 (2020.05.22)
--------------------
 - [Query] Allow user to define different database connections for each Group
 - [Database] PostgreSQL users can export their DB to SQLite
 - [Database] Export database to JSON
 - [ROI Map] Only prompt user about ROI Map saving if it has been edited


v0.8.0 (2020.05.15)
--------------------
 - [Error Logging] Implemented error logging, stored in ~/Apps/dvh_analytics/logs. Code borrowed from dicompyler.


v0.7.9 (2020.05.06)
--------------------
 - [Misc] Remove references to the deprecated import_settings.txt file
 - [ROI Map] Fix GH Issue [75](https://github.com/cutright/DVH-Analytics/issues/75)
 - [ROI Map] Deleting a physician in the ROI Map module now actually deletes the .roi file stored locally
 - [ROI Map] Alert user on ROI Map frame close that ROI Map won't be saved when using the OS's window close button
 - [ROI Map] Prevent TypeError on editing physician name
 - [ROI Map] Bug fix for validating new physician name

v0.7.8 (2020.05.01)
--------------------
 - [Import] Only allow `DoseSummationType` of `PLAN` or `BRACHY` if multiple dose files are found 
 GH Issue [68](https://github.com/cutright/DVH-Analytics/issues/68).
 - [Import] Bug fix: If multiple files are found for a plan-set, select only the latest file per 
 `os.path.getmtime`. Previously, only the first file found was used.

v0.7.7 (2020.04.21)
--------------------
 - [DVH] Proper dvh bin-centers (errors were <= bin_width/2)
 - [Import] If a plan does not have a BeamSequence or IonBeamSequence (e.g., brachy), a dummy beam is created to 
 prevent crash if this plan is included in a query.
 - [Correlation] None-type values are now removed before correlation calculation and any patient removed from this 
 calculation is displayed in an error window.

v0.7.6 (2020.04.15)
--------------------
 - [Import] Using rapidfuzz for name prediction (for MIT licensing)
 - [Import] Fix for None-Type error with roi_type query during import
 - [Export] PNG support for figure export
 - [Export] Bundle PhantomJS in executables or load from ~/Apps/dvh_analytics
 - [Plots] Grid line customization (color, thickness, alpha)
 - [Misc] Store last positions of certain windows (i.e., UserSettings, ExportFigure) 
 - [Misc] Optionally auto-backup SQLite DB after successful import (enable this in Database Administrator) 
 or manually backup database in the menu Data -> Backup SQLite DB


v0.7.5 (2020.04.09)
--------------------
 - [Import] Option to import DVH stored in DICOM RT-Dose rather than calculate it. NOTE: Currently the source of the DVH
  is not stored in the database.
 - [Import] Fixed bug that caused datetime parsing to fail if DICOM timestamp had fractional seconds
 (avoid the "unconverted data remains" error).
 - [Import] Option to turn off automatic dose summation: [#57](https://github.com/cutright/DVH-Analytics/issues/57)
 - [Import] Bug fix: [#59](https://github.com/cutright/DVH-Analytics/issues/59)
 - [Import] SQLite import_time_stamp now actually includes time, and is in your local timezone
 - [Import] SoftwareVersions and Deferred read error fix: [#36](https://github.com/cutright/DVH-Analytics/issues/36)
 - [Import] Treatment modalities are sorted before importing so database doesn't have ModalityA,ModalityB and 
 ModalityB,ModalityA
 - [Export] New figure export implementation in tool bar, supports SVG and HTML. Note that SVG export requires 
 phantomJS to be installed, which is not a python library.
 - [Plots] Plot options in User Settings no longer require DVHA to be restarted to be applied.

v0.7.4 (2020.03.13)
--------------------
 - [Endpoints] Fixed a bug where endpoint short-hand would not display on MS Windows
 - [Import] Users can edit ROI Names with a right-click, rather than editing ROI Map
 - [Import] Other right-click menu bug fixes on ROI tree
 - [Import] Plan complexity calculation corrected, now is direct sum of all CP complexities
 - [Import] Catch PatientSetupSequence error to allow for brachytherapy plan import
 - [Import] Implement scipy.nd_image.map_coordinates for ~2.5x faster dose interpolation
 - [Import] Fixed bug where DVHA could crash if trying to parse non-DICOM files (e.g. .html)
 - [PyPI] scikit-learn changed 0.21 to 0.21.0, updated requirements.txt (as of v0.7.3.post1)
 - [Settings] Inbox and Imported directory settings were not sticking: fixed per [issue #48](https://github.com/cutright/DVH-Analytics/issues/48)
 - [ROI Name Map] Implementation of TG-263 compliance
 - [ROI Name Map] Fixes for [issue #48](https://github.com/cutright/DVH-Analytics/issues/48)
 - [ROI Name Map] Fixes for [issue #50](https://github.com/cutright/DVH-Analytics/issues/50)
 - [Misc] To see which python libraries and versions are being used: Help -> Python Libraries Used

v0.7.3 (2020.03.04)
--------------------
 - [Import] Users can right-click an ROI name for a pop-up menu to more easily edit the ROI map
 - [Import] Adding an ROI variation with right-click menu will predict a physician ROI name using fuzzy logic.   
 *NOTE: python-Levenshtein is an optional pip install for fuzzywuzzy speed improvements, but may require non-python 
 libraries to be installed. python-Levenshtein is not required for DVHA and makes no noticeable speed 
 improvements for these purposes.*
 - [Import] Fix for [Issue #43](https://github.com/cutright/DVH-Analytics/issues/43) (DICOM Dose Summation)
 - [Import] Fix for bug that ignored PTV related calculation for patients with multiple plans on one CT
 - [Import] Fix for bug where importing did not use ROI Map edits during import screen
 - [Import] Import window checkbox statuses default to previous import statuses
 - [Machine Learning] Bug fix in model viewer that could not properly load non-default hyper-parameter values
 - [Misc] Google user group now created [here](https://groups.google.com/forum/#!forum/dvh-analytics)

v0.7.2 (2020.02.11)
--------------------
 - [Import] Fix for [Issue #35](https://github.com/cutright/DVH-Analytics/issues/35)
 - [Import] Fixed bug that kept StudyInstanceUID error after deleting the plan in the DB 
 and multiple plans are attached to the same StudyInstanceUID in the import fileset
 - [Import] Ensure all imported plans are moved when multiple plans are attached to the same StudyInstanceUID

v0.7.1 (2020.02.10)
--------------------
 - [Executable] Reduced file size by ~20MB, MS Windows icon now works (needs fine-tuning)
 - [Import] Ignore metacache.mim files on import, they throw a MemoryError in pydicom.read_file
 - [Import] Fix for [Issue #26](https://github.com/cutright/DVH-Analytics/issues/26)
 - [Import] Fixed a bug that lost parsed data after browsing for a new import directory, even when clicking cancel
 - [Misc] Import, ROI Map, and Database windows now close on application quit
 - [Misc] Better window management, only one instance of Import, ROI Map, and Database at a time
 
v0.7.0 (2020.01.27)
--------------------
 - [Import] Allow user to keep dicom files in the selected import directory
 - [Import] Prevent crash on dose summation, dose sum bug still not fixed
 - [Modeling] Allow user to open ML model without explicitly generating an MVR model
 - [Query] Fix for [Issue #37](https://github.com/cutright/DVH-Analytics/issues/37)
 - [Query] Proper min and max label updates with units in numerical query dialog
 - [RadBio] Fix for [Issue #34](https://github.com/cutright/DVH-Analytics/issues/34)
 - [Time Series] Calculate tests for normality, two sample t-test, and Wilcoxon ranksum
 - [Misc] Corrected units for beam perimeter and area


v0.6.9 (2020.01.17)
--------------------
 - [Correlation] Catch crash if there is insufficient data for a correlation calculation
 - [Modeling] Allow user to load saved models (Multi-Variable and Machine Learning)
    Still under development, currently ML must be loaded after a MVR has been generated
 - [Query] Fix for [issue 20](https://github.com/cutright/DVH-Analytics/issues/20)
 - [Query] Corrected physician count of query
 - [Executable] Initial version with MS Windows executable available 


v0.6.8 (2020.01.14)
--------------------
 - [DICOM Importer] Fix for [issue 30](https://github.com/cutright/DVH-Analytics/issues/30)
 - [Machine Learning] Fix for [issue 29](https://github.com/cutright/DVH-Analytics/issues/29)
 - [Misc] LICENSE was renamed to LICENSE.txt in v0.6.7, but MANIFEST.in and paths.LICENSE_PATH were not updated
 - [Multi-Variable Regression] Added "Backward Elimination" button to automatically remove insignificant 
    variables using backward elimination


v0.6.7 (2020.01.13)
--------------------
 - [Database] SQLite3 is now supported
 - [Database Connection] The last successful SQL connections settings are stored for easy reload
 - [DICOM Importer] Auto assign ROI type physician_roi name is gtv, ctv, itv, or ptv 
 - [DICOM Importer] Allow import dialog to close on crash
 - [DICOM Importer] Sometimes sim_study_date and birth_date were not date objects, more robust age calculator to account for this


v0.6.6 (2020.01.09)
--------------------
 - [About] Fix bug that displayed version of last options save instead of currently installed version
 - [Endpoints] ensure extra_column_data values do not have commas, issue [20](https://github.com/cutright/DVH-Analytics/issues/20)
 - [Time Series] Prevent crash if simulation date is not able to be parsed by dateutil

v0.6.5 (2020.01.08)
--------------------
 - [Correlation] New tab added showing a correlation matrix
 - [Database Editor] Fix for GH Issue 19
 - [DICOM Importer] Fix for GH Issue 18
 - [DICOM Importer] Added Save ROI Map button, Importing actually saves ROI map now
 - [Export] Fixed a bug that would not export DVHs Summary without also exporting DVHs
 - [Export] Fixed a bug when exporting RadBio data, could crash when writing gamma ('\u03b3')
 - [Machine Learning] Mean-square error prints in scientific notation if not between 1 and 1000
 - [Query] DVH bin width may be set. SQL still stores 1cGy bin widths, but query will keep dvh data
    using specified bin width.  This results in faster bokeh plot generation.
 - [Query] Query Groups are back!
 - [Regressions] Bug fix when removing None and NaN data
 - [Regressions] MS Windows only, if multiple dependent variables were defined, each new view displayed the same bokeh 
    layout. The following Machine Learning windows had the correct data. Fixed by including dependent variable name 
    html file name for multi-variable_regression. Did not affect other OSs because html files are stored only for MSW.
 - [Regressions] Catch error on multi-variable regression, print error to dialog window
 - [User Options] Fixed bug that did not restore saved options after clicking cancel

v0.6.4 (2020.01.08)
--------------------
Skipped due to PyPi / setup tools issues.

v0.6.3 (2019.12.15)
--------------------
 - [Database Connection] Initialize SQL tables upon successful new database connection
 - [Database Connection] Catch invalid SQL credentials at launch, automatically open connection settings dialog
 - [DICOM Importer] Display PTV ROI type in RT Structure tree.  Helpful for multi- PTV plans.
 - [DICOM Importer] Set force=True with pydicom.read_file() for XiO support  [issue #15](https://github.com/cutright/DVH-Analytics/issues/15)
 - [DICOM Importer] Apply fix for TransferSyntaxUID error [issue #16](https://github.com/cutright/DVH-Analytics/issues/16)
 - [Query] Added a catch and error dialog for a MemoryError when querying if users queries more data than their system can handle

v0.6.2 (2019.12.08)
--------------------
 - [Machine Learning] More visual options available in settings
 - [Plot Visuals] Hover information pop-ups display with data only. Trends, stats, etc. no longer clutter
 - [Stats Data] Spreadsheet class created, used to display Stats data with ability to edit. 
 This means you can add custom numerical data for trending, regressions, machine learning.
 - [Misc] All data, multi-variable regression, and machine learning windows close when main window is closed

v0.6.1 (2019.7.10)
--------------------
 - [Control Chart] Adjusted Control Charts automatically populated from Regressions tab after running model
 - [Machine Learning] Redesigned PlotRandomForest class to PlotMachineLearning to support Random Forest, Decision Tree, 
 Gradient Boost, and Support Vector Machine
 - [Machine Learning] Modules redesigned to allow for complete input parameter customization
 - [Machine Learning] Modules allow for data splitting (training and testing)
 - [Machine Learning] Models can be saved to a pickle file, their use not yet implemented
 - [Regression] Run all regressions on run

v0.6.0 (2019.7.6)
--------------------
DVH Analytics has been completely rewritten using the wxPython Phoenix framework.
 - Tested on Mac OS Mojave, Windows 7, and Linux.
 - No longer depends on launching bokeh servers
 - PostgreSQL database is still needed and is in largely the same format as before (new columns added)
 - Modeling with Random Forest has been added, other algorithms coming soon
 - Control Charts and Adjusted Control Charts have been added
 - Currently only one query group is allowed, 2nd group will come in a future version
 - DICOM files are properly connected with SOPInstanceUIDs rather than just StudyInstanceUIDs
 - Multiple plans connected by the same StudyInstanceUID will have their dose grids automatically summed
   - WARNING: this assumes your dose grids are aligned, interpolation for non-aligned grids coming soon

v0.5.6 (2019.2.14)
--------------------
* Allow roi_name in query

v0.5.5 (2019.2.14)
--------------------
* Beam complexity is now CP MU weighted sum (not mean complexity)
* Plan complexity is MU weighted sum of beam complexity times scaling factor in default_options.py
* Toxicity and complexity values now can be stored as NULL values

v0.5.4 (2019.2.11)
--------------------
* In the Regression tab, plotting any variable with min, median, mean, or max crashed on axis title update. Fixed.
* Min, mean, median and max of beam complexity, beam area, control point MU now calculated at time of import
    * These new values are available for time-series, correlation, and regression tabs in the main view
* Terminal now prints mrn of excluded plans due to non-numeral data used for correlation / regression
* Fixed bug causing crash at import due to some now missing SQL columns

v0.5.3 (2019.1.31)
--------------------
* Bokeh >=1.0.4 now required
* Import Notes tab added to Admin view for quick reference
* Protocol and Toxicity tabs added to Admin view
    * Use Protocol tab to designate plans that are attached to a particular protocol
    * Use Toxicity tab to enter toxicity grades (must be integer values)
    * DVH Analytics 0.5.4 will have appropriate statistical tests for toxicity data
    * Selecting rows in the table will auto-populate the MRN Input text area
    * Note that you can copy and paste multiple rows from Excel into the text area inputs
* Plotting PTV Distances in Regression tab previously caused a crash, issue resolved

v0.5.2 (2019.1.18)
--------------------
* Beginning development for toxicity and protocol data
    * New columns added to the Plans and DVHs SQL tables to tag toxicity scale and grade
        * Toxicity grade must be a positive integer, default value is -1 indicating no reported toxicity
        * New tab in Admin view to manage toxicity and protocol information
    * New column added to Plans SQL table to indicate if a plan is part of a protocol
    * Next version will have GUI in the Admin view to update this information more easily than via Database Editor
* Input text for action selected by radio buttons in ROI Manager now properly updates based on current selections
* If a plan for a given Study Instance UID is in your database when importing a plan with the same Study Instance UID,
a message incorrectly indicated the plan was moved to the misc.  This message has been corrected and the files remain 
in the inbox.
* New radio button for Post Import Calculations easily allowing you calculate only missing values (instead of 
recalculating the entire database or entering your own custom SQL condition)

v0.5.1 (2019.1.7)
--------------------
* 0.5.0 Code was not running with pip install
    * Changed absolute imports to relative imports, some file reorganizing

v0.5.0 (2019.1.6)
--------------------
* New ROI Name Manger layout
    * plot now displays entire physician roi map
    * you can show all data or filter institutional rois by linked, unlinked, or branched
    * Functionality added to merge one physician roi into another
* Previously, importing a ROI Map automatically added institutional rois to physician rois. This behavior has been 
removed. Adding a new physician will still create a default list of physician rois based on the insitutional roi 
list. The DEFAULT physician will include only institutional rois
* Minor changes to Database Editor layout
    * Database editor now updates without recreating layout (much faster table update after query)
    * Database table no longer uses a slider for width
* Downloading tables with values that have , in them now replaced with ; instead of ^
* tables in Admin View sorted by mrn by default

v0.4.10 (2019.1.1)
--------------------
* Bad reference to SQL config settings in the Ignore DVH button of the ROI Name Mangaer of the Admin view

v0.4.9 (2019.1.1)
--------------------
* Organize modules in tools directory
* Generalize update_all_in_db functions in database_editor.py
* ensure all options read from custom options file if available
* Backup tab functionality in Admin view was incomplete since modularization of bokeh views
    * Backup selection menus now update
    * Backup preferences works again

v0.4.8 (2018.12.27)
--------------------
* Reorganize python files into directories:
    * path updated with: import update_sys_path
    * columns.py and custom_titles.py now have code wrapped in a class
    * Multiple simultaneous sessions enabled again by wrapping all bokeh objects into classes
* Remove test files
* Catch keyboard interrupt in \_\_main\_\_.py for graceful shutdown
* Moved import_warning_log.txt to user's data directory
* All preferences stored in user folder now so that there's no need to run servers with sudo
* May need to copy files from <script-dir>/preferences into ~/Apps/dvh_analytics/preferences/
* Data directory defaults to ~/Apps/dvh_analytics/data but can still be customized
* All sql/preference backups stored in ~/Apps/dvh_analytics/data/backup now (can't customize)
* options.py now contains imports (os and paths.py)
    * This broke refresh_options, code added to ignore ModuleType
* Automatically update uncategorized variations in ROI Manager after importing data, updating database, deleting data, 
or reimporting database

v0.4.7 (2018.12.6)
--------------------
* Move csv creation to python for less javascript (download.js)
* Some bug catches if certain fields are too long to import into its SQL column
* ROI Name Manager in the Admin view displays a table of the currently saved ROI Map of the 
currently selected physician

v0.4.697 (2018.11.11)
--------------------
* The docker compose file for DVH Analytics Docker had a bug such that it would not share import and sql connection settings between 
main, admin, and settings views.  A directory was created to share changes with each server.
* DVH Analytics will detect if you're using Docker and have docker applicable default sql connection settings
* Note that DVH Analytics Docker has only been validated on Mac

v0.4.62 & v0.4.68 (2018.11.11)
--------------------
* If a RT Plan that is incompatible with the current version of dicom_mlc_analyzer.py, DVH Analytics would crash. 
Now the command prompt will print the failed RT Plan file, and skip the MLC Analyzer tab update, preventing a crash.
* Moving to the bokeh_components directory caused relative import errors. As a temporary fix, all python files moved 
to main dvh directory. This version was verified to work via pip install (and subsequently running with dvh command 
calling \_\_main\_\_.py for entry point), as well as in docker.
* These versions were explicitly tested by running source code with direct bokeh serve calls, pip install of 
DVH Analytics, and using docker-compose.

v0.4.6 (2018.11.6)
--------------------
* MAJOR restructuring with majority of main.py moved into bokeh_components directory
    * Next release will begin working on better efficiency
* Residual chart added to Regression tab, will develop into Control Chart
* Begin making code more concise using classes and dictionaries
* Issue #42 - Regression drop-downs not updating properly when deleting/changing EP
* MLC Analyzer does not cause crash if DICOM plan file cannot be found

v0.4.5 (scrapped)
--------------------

v0.4.4b, v0.4.4.4c, v0.4.4.1 (2018.11.1)
--------------------
* Minor tweaks for on compliance with DICOM files from http://www.cancerimagingarchive.net/
* Move Files Check box added in admin view if user wishes to keep files in the inbox

v0.4.4a (2018.11.1)
--------------------
* Minor tweak to check for TPS Vendor tags prior to accessing, working on compliance with DICOM files from 
http://www.cancerimagingarchive.net/

v0.4.4 (2018.08.15)
--------------------
* typo in keyword for parameter in dicom_to_sql (import_latest_plan_only changes to import_latest_only)
* Shapely speedups enabled, if available
    * Shapely has calcs available in C, as opposed to C++
* centroid, dist_to_ptv_centroids, dth (distance to target histogram), spread_x, spread_y, spread_z, cross_section_max, 
cross_section_median, columns added to DVHs
    * These columns can be added by clicking Create Tables from Settings view, if running from source
    * Running from Docker or pip install shouldn't need to do this manually
* dist_to_ptv_centroids and dth must be calculated from Admin view after proper ROI name mapping
* dth_string calculated with Calc PTV Dist in Admin view
    * the string stored is csv representing a histogram with 0.1mm bins
* centroid, spread, and cross-sections also calculated at time of import
    * calc in Admin view only required for data imported prior to 0.4.4 install
* Admin view now specifies Post-Import calculations via dropdown
    * Added choice "Default Post-Import" to run through all calcs not done at time of DICOM import
* Endpoints for review DVH now calculated

v0.4.3 (2018.08.04)
--------------------
* IMPORT_LATEST_ONLY removed from options.py in lieu of a simple checkbox in the admin view.
* Settings view now has functionality to edit parameters in options.py. These edits are stored 
in preferences/options via pickle.  If preferences/options does not exist, the default values in 
options.py are used.
* Draft of a user manual is now available.

v0.4.2 (2018.07.31)
--------------------
* Download button added for DVH endpoints.
* LITE_VIEW added to options.py. If this is set to True, only Query and DVHs tabs are rendered.  The 
DVHs tab is stripped down to only calculate endpoints, although they are not displayed.  This is 
to avoid any table or plots being  displayed. No correlation data is calculated.  Users working 
with VERY large datasets may find  this useful if all they want is to query and quickly calculate 
DVH endpoints.
* The download dropdown button on the Query tab has been non-functional since we updated for Bokeh 
0.13.0 compatibility.  This button works as expected now.

v0.4.1 (2018.07.23)
--------------------
* The DVH Analytics Docker image now has an empty file , /this_is_running_from_docker, 
which is used by DVH Analytics to detect if the user is running Docker. This helps 
DVH Analytics know where to look for SQL and import settings, as reflected in 
get_settings.py.
* The default behavior for adding a physician in the ROI Name Manager is to copy 
institutional ROIs as physician ROIs.
* The Admin view now has a feature to backup and restore preferences. This is mostly 
useful for backing up ROI maps. If you're using Docker, it's strongly recommended you backup your 
preferences since relaunching an image *may* restore your preference defaults.
* The database backup feature in the Admin view has been fixed to work with Docker. If you're running 
DVH Analytics source code locally, be sure you have the postgres sql command line tools installed, specifically 
pg_dumpall needs to be available.
* If a new physician was created in ROI Name Manager, and then ROI Map was saved while 
the newly added physician had no physician ROIs, an empty .roi file was created causing 
subsequent Admin view launches to crash.  This bug has been fixed; empty Physicians will not 
be stored and adding a new Physician automatically copies your institutional ROIs as 
physician ROIs.
* DVH Analytics is FINALLY using a change log.