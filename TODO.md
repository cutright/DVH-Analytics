# TODO

1. **Import**
    - [ ] Need to test import of DICOM files other than Plan, Dose, Structure
        - [X] Non-DICOM files are properly ignored
        - [ ] Test DICOM files other than plan, dose, structure 
    - [ ] Imports based on sop instance uid rather than study instance uid
        - [X] Update file tree to Patient -> Study -> Plan -> Files
        - [X] Auto combine multiple plans within one study_instance_uid
        - [ ] Implement dicom_dose_sum.py borrowed from dicompyler plugin (testing failed)
            - [ ] Still need to properly assign files (only one file per study, not a list)
            - [ ] Rx dose of 2nd plan not importing?
            - [ ] Allow a single structure file for two plans pointing to same file
            - [ ] Dose sums that require dose summation failing. Issue posted [here](https://groups.google.com/forum/?utm_medium=email&utm_source=footer#!msg/dicompyler/qkU2CtYzgLg/EbaV5foXAgAJ)
            - [ ] move_files should be called after study completely imported, not plan

2. **Open/Save and Import**
    * *Open/Save*
        - [ ] Needs testing, crashes observed
    * *Import*
        - [ ] Allow user to import outcome or QA data to run correlations/stats

3. **Regression**
    - [ ] Machine learning modules in Regression tab (after running multi-variable regression) aren't complete 
    - [ ] Need to be able to store a model (particularly for use in Control Chart)
    - [ ] Correlation Matrix from pure Bokeh App not yet used

4. **Control Chart**
    - [ ] Implement Adjusted Control Charts based on a regression model

5. **Database Editor**
    - [ ] Allow user to re-perform "post-import" calculations

6. **Documentation**
    - [ ] Review code, add doc strings and comments
    - [ ] Rewrite/Update DVH Analytics manual
    - [ ] Update LICENSE to include licenses of software dependencies

7. **GUI**
    - [ ] Move models.datatable.py to [ObjectListView](http://www.blog.pythonlibrary.org/2009/12/23/wxpython-using-objectlistview-instead-of-a-listctrl/)
    - [ ] Allow for a simultaneous 2nd query as found in pure bokeh version of DVHA