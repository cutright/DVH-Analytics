# TODO

1. **ROI Map**
    - [X] User needs a way to create a ROI map, current GUI is largely non-functional
    - [X] Needs better visual than current tree, visual from the pure Bokeh app was useful, maybe a wx.CustomListCtrl 
    could work?
        - Using original visualization
    - [X] Most ROI Map interaction should be able to occur at time of import, ROI Map in tool bar to be used for 
    clean up later
        - [X] Add ability to add physician map at import dialog, add variations, etc.
    - [X] Complete functionality
    - [X] Just needs to save changes
        * This should include a difference calculator to auto update database

2. **Import**
    - [X] Need to test on Windows/Linux
    - [ ] Need to test import of DICOM files other than Plan, Dose, Structure
    - [ ] Currently code connects strictly by StudyInstanceUID and assumes the latest files appropriate. 
    Should further organize with SOP Instance checks
    - [X] Better ROI map integration

3. **Regression**
    - [ ] Machine learning modules in Regression tab (after running multi-variable regression) aren't complete 
    - [ ] Need to be able to store a model (particularly for use in Control Chart)
    - [ ] Correlation Matrix from pure Bokeh App not yet used

4. **Control Chart**
    - [ ] Implement Adjusted Control Charts based on a regression model

5. **Open/Save, Close, Print, Export, and Import**
    * *Open/Save*
        - [X] User should be able to store a set of queried data so they can return to this state 
        at a later date if the database changes
        - [X] Needs a data object that captures the data immediately after query
        - [X] Remaining data could be recalculated
        - [X] Maybe just pickle the QuerySQL objects stored in MainFrame.data in main.py?
        - [X] Include filters and add to UI after load
        - [X] Save endpoints, radbio, regressions
    * *Close*
        - [X] This function has not been updated in a while, is surely not clearing all data anymore
    * *Export*
        - [X] Some tabs have a CSV export already, would like to create a dialog for CSV Export on tool that lets 
        you check off which elements can be exported as CSV
        - [X] DataTable objects from models/datatable.py have a .csv property
        - [X] Need a export method for plots
    * *Import*
        - [ ] Would like to give user ability to export data to a csv, then add custom columns and reimport data. 
        This will allow user to import outcome or QA data to run correlations/stats

6. **Windows/Linux Plotting**
    * Windows:
        - [X] wx.html2 has issues on Windows generating javascript views
        - [X] Tried SetPage() and LoadURL(), tested on Windows 7 with latest IE, maybe Windows 10 works?
        - [X] Registry edit needed? [html2.WebView and "blocked content" on Windows/IE](https://groups.google.com/forum/#!topic/wxpython-dev/epBVWHC7l6E)
            * See [latest](https://wxpython.org/Phoenix/docs/html/wx.html2.WebView.html) wxPython dev
            * Use wheel from [here](https://wxpython.org/Phoenix/snapshot-builds/)
        - [X] [Fixed!](https://github.com/wxWidgets/Phoenix/issues/1256)
    * Linux:
        - [X] Plot is displayed, but no interactivity
        - [X] Issue [#4](https://github.com/cutright/DVH-Analytics-Desktop/issues/4): Turns out not a Linux issue

7. **Icons**
    - [X] I borrowed (stole) icons from dicompyler for the DICOM file tree.  Should make my own.
    - [X] Be sure toolbar icons are cited properly (they're all for free use)
    - [X] Regression icons are Star Wars right now... just temporary

8. **Plan/Rx/Beam Data**
    - [X] Pure bokeh version of DVHA allowed user to explore plan, rx, and beam data in a tabular format
    - [X] Data is already stored during application run, just needs a GUI
    - [X] Needs export functionality

9. **Database Editor**
    - [X] UIs are built, and their associated functions are largely already written, just need to connect them
    - [X] Build new message dialog on sql exceptions so the entire error is shown
    - [X] Create custom Exception class to more robustly catch DVH_SQL() update and query errors
    - [ ] Allow user to re-perform "post-import" calculations

10. **Documentation**
    - [ ] Review code, add doc strings and comments
    - [ ] Rewrite/Update DVH Analytics manual
    - [ ] Update LICENSE to include licenses of software dependencies

11. **GUI**
    - [X] Dynamically resize plots with parent window
    - [ ] Move models.datatable.py to [ObjectListView](http://www.blog.pythonlibrary.org/2009/12/23/wxpython-using-objectlistview-instead-of-a-listctrl/)