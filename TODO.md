# TODO

1. **ROI Map**
    - [ ] User needs a way to create a ROI map, current GUI is largely non-functional
    - [ ] Needs better visual than current tree, visual from the pure Bokeh app was useful, maybe a wx.CustomListCtrl 
    could work?
    - [ ] Most ROI Map interaction should be able to occur at time of import, ROI Map in tool bar to be used for 
    clean up later
        - [ ] Add ability to add physician map at import dialog, add variations, etc.

2. **Import**
    - [ ] Need to test on Windows/Linux
    - [ ] Need to test import of DICOM files other than Plan, Dose, Structure
    - [ ] Currently code connects strictly by StudyInstanceUID and assumes the latest files appropriate
        - [ ] Should probably have a layer of verification with SOP Instance checks
    - [ ] Better ROI map integration
    - [ ] Unchecking anything in the ROI tree does nothing
    - [ ] Thread the file/dicom parsing process so UI updates on the fly in Windows (works as is on Mac, and maybe linux too)

3. **Regression**
    - [ ] Machine learning modules in Regression tab (after running multi-variable regression) aren't complete 
    - [ ] Need to be able to store a model (particularly for use in Control Chart)
    - [ ] Correlation Matrix from pure Bokeh App not yet used

4. **Control Chart**
    - [ ] Implement Adjusted Control Charts based on a regression model

5. **Open/Save, Close, Print, Export, and Import**
    * *Open/Save*
        - [ ] User should be able to store a set of queried data so they can return to this state 
        at a later date if the database changes
        - [ ] Needs a data object that captures the data immediately after query
        - [ ] Remaining data could be recalculated
        - [ ] Maybe just pickle the QuerySQL objects stored in MainFrame.data in main.py?
    * *Close*
        - [ ] This function has not been updated in a while, is surely not clearing all data anymore
        - [ ] Perhaps could hijack the method used for open/save, and a save a state at app launch?
    * *Print*
        - [ ] Need a report generator
    * *Export*
        - [ ] Some tabs have a CSV export already, would like to create a dialog for CSV Export on tool that lets 
        you check off which elements can be exported as CSV
        - [ ] DataTable objects from models/datatable.py have a .csv property already
        - [ ] Need a export method for plots
    * *Import*
        - [ ] Would like to give user ability to export data to a csv, then add custom columns and reimport data
        - [ ] This will allow user to import outcome or QA data to run correlations/stats

6. **Database Editor**
    - [X] UIs are built, and their associated functions are largely already written, just need to connect them

7. **Windows/Linux Plotting**
    * Windows:
        - [ ] wx.html2 has issues on Windows generating javascript views
        - [ ] Tried SetPage() and LoadURL(), tested on Windows 7 with latest IE, maybe Windows 10 works?
        - [ ] Registry edit needed? [html2.WebView and "blocked content" on Windows/IE](https://groups.google.com/forum/#!topic/wxpython-dev/epBVWHC7l6E)
    * Linux:
        - [X] Plot is displayed, but no interactivity
        - [X] Issue [#4](https://github.com/cutright/DVH-Analytics-Desktop/issues/4): Turns out not a Linux issue

8. **Icons**
    - [ ] I borrowed (stole) icons from dicompyler for the DICOM file tree.  Should make my own.
    - [ ] Be sure toolbar icons are cited properly (they're all for free use)
    - [ ] Regression icons are Star Wars right now... just temporary

9. **Plan/Rx/Beam Data**
    - [ ] Pure bokeh version of DVHA allowed user to explore plan, rx, and beam data in a tabular format
    - [ ] Data is already stored during application run, just needs a GUI

10. **Documentation**
    - [ ] Review code, add doc strings and comments
    - [ ] Rewrite/Update DVH Analytics manual