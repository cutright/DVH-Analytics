# TODO

1. **Import**
    - [ ] Need to test import of DICOM files other than Plan, Dose, Structure
        - [X] Non-DICOM files are properly ignored
        - [X] Test DICOM files other than plan, dose, structure 
    - [ ] Imports based on sop instance uid rather than study instance uid
        - [X] Update file tree to Patient -> Study -> Plan -> Files
        - [X] Auto combine multiple plans within one study_instance_uid
        - [ ] Implement dicom_dose_sum.py borrowed from dicompyler plugin (testing failed)
        - [ ] Still need to properly assign files (only one file per study, not a list)
        - [ ] Rx dose of 2nd plan not importing?
        - [ ] Allow a single structure file for two plans pointing to same file
        - [ ] Dose sums that require interpolation failing. Issue posted [here](https://groups.google.com/forum/?utm_medium=email&utm_source=footer#!msg/dicompyler/qkU2CtYzgLg/EbaV5foXAgAJ)
        - [X] move_files should be called after study completely imported, not plan

2. **Open/Save and Import**
    * *Open/Save*
        - [ ] Needs testing, crashes observed
    * *Import*
        - [ ] Allow user to import outcome or QA data to run correlations/stats

3. **Regression**
    - [ ] Machine learning modules in Regression tab (after running multi-variable regression) aren't complete 
    - [X] Need to be able to store a model (particularly for use in Control Chart)
        - [ ] Change to storage of variable names rather than regression object, recalc regression with current data
    - [X] Plot regression with ML
    - [X] importance bar chart

4. **Control Chart**
    - [X] Implement Adjusted Control Charts based on a regression model

5. **Database Editor**
    - [ ] Allow user to re-perform "post-import" calculations

6. **Documentation**
    - [X] Review code, add doc strings and comments
    - [ ] Rewrite/Update DVH Analytics manual
    - [X] Update LICENSE to include licenses of software dependencies

7. **GUI**
    - [X] Allow sorting of tables (added in DataTable object)
        - [ ] Rad bio and Endpoint table need to remember original order before implementing sort
    - [ ] Allow for a simultaneous 2nd query as found in pure bokeh version of DVHA
    - [X] Window sizes should be relative to user's screen resolution

8. **Calculations**
    - [ ] dicompyler's dvhcalc.get_dvh().min sometimes reporting excessively small doses
    - [x] sample roi's for min distance calculations
    - [ ] Min distance calculation needs points sampled inside top and bottom slices