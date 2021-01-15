#!/usr/bin/env python
# -*- coding: utf-8 -*-

# dialogs.database.py
"""
Classes based on wx.Dialog for models.database_editor.py
In general, this classes will manifest themselves in the GUI on
initialization. They should contain a function names
action which will be executed on a dialog resolution of wx.ID_OK
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
from datetime import datetime
from os import mkdir, rename
from os.path import join, basename
from dvha.db.sql_connector import (
    DVH_SQL,
    echo_sql_db,
    is_file_sqlite_db,
    write_test,
)
import dvha.db.update as db_update
from dvha.models.import_dicom import ImportDicomFrame
from dvha.paths import DATA_DIR
from dvha.tools.errors import SQLError, SQLErrorDialog
from dvha.tools.utilities import (
    delete_directory_contents,
    move_files_to_new_path,
    delete_file,
    get_file_paths,
    delete_imported_dicom_files,
    move_imported_dicom_files,
    MessageDialog,
    get_window_size,
)
from dvha.tools.threading_progress import ProgressFrame
from pubsub import pub


class CalculationsDialog(wx.Dialog):
    """
    Dialog to perform various calcs for values not stored in DICOM files.
    """

    def __init__(self):
        wx.Dialog.__init__(self, None, title="Calculations")

        self.choices = [
            "PTV Distances",
            "PTV Overlap",
            "ROI Spread",
            "ROI Cross-Section",
            "ROI Surface Area",
            "OAR-PTV Centroid Distance",
            "All",
        ]
        self.combo_box_calculate = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=self.choices,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.text_ctrl_condition = wx.TextCtrl(self, wx.ID_ANY, "")
        self.button_ok = wx.Button(self, wx.ID_OK, "Calculate")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__do_layout()

        self.LUT = {
            "PTV Distances": {
                "func": db_update.update_ptv_dist_data,
                "title": "Calculating PTV Distance Metrics",
            },
            "PTV Overlap": {
                "func": db_update.update_ptv_overlap,
                "title": "Calculating PTV Overlap",
            },
            "OAR-PTV Centroid Distance": {
                "func": db_update.update_ptv_centroid_distances,
                "title": "Calculating OAR-PTV Centroid Distances",
            },
            "ROI Spread": {
                "func": db_update.update_roi_spread,
                "title": "Calculating ROI Spreads",
            },
            "ROI Cross-Section": {
                "func": db_update.update_roi_cross_section,
                "title": "Calculating ROI Cross-Sections",
            },
            "ROI Surface Area": {
                "func": db_update.update_roi_surface_area,
                "title": "Calculating ROI Surface Areas",
            },
        }

        pub.subscribe(self.do_next_calculation, "do_next_calculation")

        self.close_msg = None

        self.run()

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_wrapper_inner = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_condition = wx.BoxSizer(wx.VERTICAL)
        sizer_calc_and_check = wx.BoxSizer(wx.HORIZONTAL)
        sizer_calculate = wx.BoxSizer(wx.VERTICAL)

        label_calculate = wx.StaticText(self, wx.ID_ANY, "Calculate:")
        sizer_calculate.Add(label_calculate, 0, wx.BOTTOM, 5)
        sizer_calculate.Add(self.combo_box_calculate, 0, 0, 0)
        sizer_calc_and_check.Add(sizer_calculate, 0, wx.EXPAND, 0)
        sizer_input.Add(
            sizer_calc_and_check,
            0,
            wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT,
            5,
        )

        label_condition = wx.StaticText(self, wx.ID_ANY, "Condition:")
        sizer_condition.Add(label_condition, 0, wx.BOTTOM, 5)
        sizer_condition.Add(self.text_ctrl_condition, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_condition, 0, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper_inner.Add(sizer_input, 0, wx.ALL | wx.EXPAND, 5)

        sizer_ok_cancel.Add(self.button_ok, 0, wx.ALL, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_wrapper_inner.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        sizer_wrapper.Add(sizer_wrapper_inner, 0, wx.EXPAND, 0)

        self.SetSizer(sizer_wrapper)
        sizer_wrapper.Fit(self)
        self.Layout()

        self.SetSize((get_window_size(0.3, 1)[0], self.Size[1]))
        self.Center()

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK:
            if self.calculation == "All":
                self.close_msg = "do_next_calculation"
                self.do_next_calculation(init=True)
            else:
                self.run_calculation()
                self.close()

    def close(self):
        pub.unsubAll(topicName="do_next_calculation")
        self.Destroy()

    def run_calculation(self):
        ProgressFrame(
            self.threading_obj_list,
            self.func,
            title=self.title,
            close_msg=self.close_msg,
            action_msg="Processing Study",
            sub_gauge=True,
            kwargs=True,
        )

    def do_next_calculation(self, init=False):
        if init:
            self.combo_box_calculate.SetValue(self.choices[0])

        if self.calculation != "All":
            self.run_calculation()
            index = self.choices.index(self.calculation)
            self.combo_box_calculate.SetValue(self.choices[index + 1])
        else:
            self.close()

    @property
    def condition(self):
        text = self.text_ctrl_condition.GetValue()
        return text if text else None

    @property
    def threading_obj_list(self):
        uids = db_update.query(
            "DVHs", "study_instance_uid", self.condition, unique=True
        )
        return [{"uid": uid, "callback": self.callback} for uid in uids]

    @property
    def calculation(self):
        return self.combo_box_calculate.GetValue()

    @property
    def title(self):
        return self.LUT[self.calculation]["title"]

    @property
    def func(self):
        return self.LUT[self.calculation]["func"]

    @staticmethod
    def callback(msg):
        pub.sendMessage("sub_progress_update", msg=msg)


class ChangeOrDeleteBaseClass(wx.Dialog):
    """
    A class generalized for changing a patient identifier or deleting a study for a patient
    """

    def __init__(
        self,
        text_input_1_label,
        text_input_2_label,
        ok_button_label,
        title,
        mrn=None,
        study_instance_uid=None,
    ):
        """
        :param text_input_1_label: label of first text input in GUI
        :type text_input_1_label: str
        :param text_input_2_label: label of second text input in GUI
        :type text_input_2_label: str
        :param ok_button_label: label of OK button in GUI
        :type ok_button_label: str
        :param title: title of the wx.Dialog object
        :type title: str
        :param mrn: optional initial value for mrn
        :type mrn: str
        :param study_instance_uid: options initial value for study instance uid
        :type study_instance_uid: str
        """
        wx.Dialog.__init__(self, None, title=title)

        self.initial_mrn = mrn
        self.initial_study_instance_uid = study_instance_uid

        self.text_input_1_label = text_input_1_label
        self.text_input_2_label = text_input_2_label

        self.combo_box_patient_identifier = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=["MRN", "Study Instance UID"],
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.text_ctrl_1 = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_ctrl_2 = wx.TextCtrl(self, wx.ID_ANY, "")
        self.button_ok = wx.Button(self, wx.ID_OK, ok_button_label)
        self.button_ok.Disable()
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        self.run()

    def __set_properties(self):
        self.text_ctrl_1.SetMinSize((365, 22))
        if self.initial_mrn or self.initial_study_instance_uid is None:
            self.combo_box_patient_identifier.SetValue("MRN")
        else:
            self.combo_box_patient_identifier.SetValue("Study Instance UID")
        self.on_identifier_change(None)

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_new_value = wx.BoxSizer(wx.VERTICAL)
        sizer_value = wx.BoxSizer(wx.VERTICAL)
        sizer_patient_identifier = wx.BoxSizer(wx.HORIZONTAL)
        label_patient_identifier = wx.StaticText(
            self, wx.ID_ANY, "Patient Identifier:"
        )
        sizer_patient_identifier.Add(label_patient_identifier, 0, wx.ALL, 5)
        sizer_patient_identifier.Add(
            self.combo_box_patient_identifier, 0, wx.TOP, 2
        )
        sizer_input.Add(
            sizer_patient_identifier, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5
        )
        label_text_input_1 = wx.StaticText(
            self, wx.ID_ANY, self.text_input_1_label
        )
        sizer_value.Add(label_text_input_1, 0, wx.EXPAND | wx.ALL, 5)
        sizer_value.Add(
            self.text_ctrl_1, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5
        )
        sizer_input.Add(sizer_value, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        label_text_input_2 = wx.StaticText(
            self, wx.ID_ANY, self.text_input_2_label
        )
        sizer_new_value.Add(label_text_input_2, 0, wx.EXPAND | wx.ALL, 5)
        sizer_new_value.Add(
            self.text_ctrl_2, 0, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5
        )
        sizer_input.Add(sizer_new_value, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_wrapper.Add(sizer_input, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        sizer_ok_cancel.Add(self.button_ok, 0, wx.ALL, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_wrapper.Add(
            sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, 10
        )
        self.SetSizer(sizer_wrapper)
        sizer_wrapper.Fit(self)
        self.Layout()
        self.Center()

    def __do_bind(self):
        self.Bind(
            wx.EVT_COMBOBOX,
            self.on_identifier_change,
            id=self.combo_box_patient_identifier.GetId(),
        )
        self.Bind(wx.EVT_TEXT, self.text_ticker, id=self.text_ctrl_1.GetId())
        self.Bind(wx.EVT_TEXT, self.text_ticker, id=self.text_ctrl_2.GetId())

    def text_ticker(self, evt):
        [self.button_ok.Disable, self.button_ok.Enable][
            self.is_action_allowed
        ]()

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK:
            self.action()
        self.Destroy()

    def action(self):
        """
        Should be over-written in classes that inherit this class, but needs to be defined here since run refers to it
        """
        pass

    def on_identifier_change(self, evt):
        value = {
            "Study Instance UID": self.initial_study_instance_uid,
            "MRN": self.initial_mrn,
        }[self.combo_box_patient_identifier.GetValue()]
        if value is not None:
            self.text_ctrl_1.SetValue(value)
            wx.CallAfter(self.text_ctrl_2.SetFocus)

    @property
    def sql_column(self):
        return (
            self.combo_box_patient_identifier.GetValue()
            .lower()
            .replace(" ", "_")
        )

    @property
    def is_id_valid(self):
        with DVH_SQL() as cnx:
            func = [cnx.is_uid_imported, cnx.is_mrn_imported][
                self.combo_box_patient_identifier.GetValue() == "MRN"
            ]
            ans = func(self.text_ctrl_1.GetValue())
        return ans

    @property
    def is_action_allowed(self):
        return self.is_id_valid and bool(self.text_ctrl_2.GetValue())


class ChangePatientIdentifierDialog(ChangeOrDeleteBaseClass):
    """
    Change MRN or Study Instance UID in all SQL tables
    """

    def __init__(self, mrn=None, study_instance_uid=None):
        """
        :param mrn: optional initial value for mrn
        :type mrn: str
        :param study_instance_uid: options initial value for study instance uid
        :type study_instance_uid: str
        """
        ChangeOrDeleteBaseClass.__init__(
            self,
            "Value:",
            "New Value:",
            "Change",
            "Change Patient Identifier",
            mrn=mrn,
            study_instance_uid=study_instance_uid,
        )

    def action(self):
        old_id = self.text_ctrl_1.GetValue()
        new_id = self.text_ctrl_2.GetValue()

        with DVH_SQL() as cnx:
            validation_func = [cnx.is_uid_imported, cnx.is_mrn_imported][
                self.sql_column == "mrn"
            ]
            change_func = [cnx.change_uid, cnx.change_mrn][
                self.sql_column == "mrn"
            ]

            if validation_func(old_id):
                if (
                    self.sql_column == "study_instance_uid"
                    and validation_func(new_id)
                ):
                    wx.MessageBox(
                        "This Study Instance UID is already in use.",
                        "%s Error"
                        % self.combo_box_patient_identifier.GetValue(),
                        wx.OK | wx.ICON_WARNING,
                    )
                else:
                    change_func(old_id, new_id)
            else:
                wx.MessageBox(
                    "No studies found with this %s."
                    % self.combo_box_patient_identifier.GetValue(),
                    "%s Error" % self.combo_box_patient_identifier.GetValue(),
                    wx.OK | wx.ICON_WARNING,
                )


class DeletePatientDialog(ChangeOrDeleteBaseClass):
    """
    Delete all data in SQL database for a given MRN or study instance uid
    """

    def __init__(self, mrn=None, study_instance_uid=None):
        """
        :param mrn: optional initial value for mrn
        :type mrn: str
        :param study_instance_uid: options initial value for study instance uid
        :type study_instance_uid: str
        """
        ChangeOrDeleteBaseClass.__init__(
            self,
            "Delete:",
            'Type "delete" to authorize:',
            "Delete",
            "Delete Patient",
            mrn=mrn,
            study_instance_uid=study_instance_uid,
        )

    def action(self):
        if self.text_ctrl_2.GetValue() == "delete":
            value = self.text_ctrl_1.GetValue()
            key = "mrn" if self.sql_column == "mrn" else "uid"
            kwarg = {key: value}
            with DVH_SQL() as cnx:
                dicom_files = cnx.get_dicom_file_paths(**kwarg)
                cnx.delete_rows("%s = '%s'" % (self.sql_column, value))

            DeleteFilesFromQuery(self, dicom_files)

    @property
    def is_action_allowed(self):
        return self.is_id_valid and self.text_ctrl_2.GetValue() == "delete"


class EditDatabaseDialog(wx.Dialog):
    """
    Generic UI object to edit values in SQL database with table, column, and condition
    """

    def __init__(self, inital_values=None):
        """
        :param inital_values: optional variable to provide initial values to table, column, value, or condition
        :type inital_values: dict
        """
        wx.Dialog.__init__(self, None, title="Edit Database Values")

        self.initial_values = inital_values
        self.error = False

        self.combo_box_table = wx.ComboBox(
            self,
            wx.ID_ANY,
            choices=self.tables,
            style=wx.CB_DROPDOWN | wx.CB_READONLY,
        )
        self.combo_box_column = wx.ComboBox(
            self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.text_ctrl_value = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_ctrl_condition = wx.TextCtrl(self, wx.ID_ANY, "")
        self.button_ok = wx.Button(self, wx.ID_OK, "Update")
        self.button_ok.Disable()
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.Bind(
            wx.EVT_COMBOBOX, self.table_ticker, id=self.combo_box_table.GetId()
        )
        self.Bind(
            wx.EVT_TEXT,
            self.condition_ticker,
            id=self.text_ctrl_condition.GetId(),
        )

        self.__set_properties()
        self.__do_layout()

        self.update_columns()

        self.run()

    def __set_properties(self):
        if self.initial_values:
            self.combo_box_table.SetValue(self.initial_values["table"])
            self.combo_box_column.SetValue(self.initial_values["column"])
            self.text_ctrl_value.SetValue(self.initial_values["value"])
            self.text_ctrl_condition.SetValue(self.initial_values["condition"])
        else:
            self.combo_box_table.SetValue("Plans")

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_wrapper_inner = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_condition = wx.BoxSizer(wx.VERTICAL)
        sizer_table_column_value = wx.BoxSizer(wx.HORIZONTAL)
        sizer_value = wx.BoxSizer(wx.VERTICAL)
        sizer_column = wx.BoxSizer(wx.VERTICAL)
        sizer_table = wx.BoxSizer(wx.VERTICAL)
        label_table = wx.StaticText(self, wx.ID_ANY, "Table:")
        sizer_table.Add(label_table, 0, 0, 0)
        sizer_table.Add(self.combo_box_table, 0, wx.EXPAND, 0)
        sizer_table_column_value.Add(sizer_table, 0, wx.ALL | wx.EXPAND, 5)
        label_column = wx.StaticText(self, wx.ID_ANY, "Column:")
        sizer_column.Add(label_column, 0, 0, 0)
        sizer_column.Add(self.combo_box_column, 0, 0, 0)
        sizer_table_column_value.Add(sizer_column, 0, wx.ALL | wx.EXPAND, 5)
        label_value = wx.StaticText(self, wx.ID_ANY, "Value:")
        sizer_value.Add(label_value, 0, 0, 0)
        sizer_value.Add(self.text_ctrl_value, 0, wx.EXPAND, 0)
        sizer_table_column_value.Add(sizer_value, 1, wx.ALL | wx.EXPAND, 5)
        sizer_input.Add(sizer_table_column_value, 1, wx.EXPAND, 0)
        label_condition = wx.StaticText(self, wx.ID_ANY, "Condition:")
        sizer_condition.Add(
            label_condition, 0, wx.BOTTOM | wx.RIGHT | wx.TOP, 5
        )
        sizer_condition.Add(self.text_ctrl_condition, 0, wx.EXPAND, 0)
        sizer_input.Add(
            sizer_condition, 1, wx.BOTTOM | wx.EXPAND | wx.LEFT | wx.RIGHT, 5
        )
        sizer_wrapper_inner.Add(
            sizer_input, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5
        )
        sizer_ok_cancel.Add(self.button_ok, 0, wx.ALL, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_wrapper_inner.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer_wrapper.Add(sizer_wrapper_inner, 0, wx.ALL | wx.EXPAND, 0)
        self.SetSizer(sizer_wrapper)
        sizer_wrapper.Fit(self)
        self.Layout()
        self.Center()

    @property
    def tables(self):
        with DVH_SQL() as cnx:
            tables = cnx.tables
        return tables

    @property
    def table(self):
        return self.combo_box_table.GetValue()

    @property
    def column(self):
        return self.combo_box_column.GetValue()

    @property
    def condition(self):
        return self.text_ctrl_condition.GetValue()

    @property
    def value(self):
        v = self.text_ctrl_value.GetValue()
        if v:
            return v
        return "NULL"

    def condition_ticker(self, evt):
        if self.condition:
            self.button_ok.Enable()
        else:
            self.button_ok.Disable()

    def update_columns(self):
        table = self.combo_box_table.GetValue()
        with DVH_SQL() as cnx:
            columns = cnx.get_column_names(table)
        self.combo_box_column.SetItems(columns)
        if self.combo_box_column.GetValue() not in columns:
            self.combo_box_column.SetValue(columns[0])

    def table_ticker(self, evt):
        self.update_columns()

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK:
            self.update_db()
        self.Destroy()
        if self.error:
            EditDatabaseDialog(inital_values=self.values)

    def update_db(self):
        with DVH_SQL() as cnx:
            try:
                cnx.update(self.table, self.column, self.value, self.condition)
            except SQLError as sql_exception:
                SQLErrorDialog(self, sql_exception)
                self.error = True

    @property
    def values(self):
        return {
            "table": self.combo_box_table.GetValue(),
            "column": self.combo_box_column.GetValue(),
            "value": self.text_ctrl_value.GetValue(),
            "condition": self.text_ctrl_condition.GetValue(),
        }


class ReimportDialog(wx.Dialog):
    """
    Reimport data from catalogued DICOM files for a given MRN or study instance uid
    """

    def __init__(self, roi_map, options, mrn=None, study_instance_uid=None):
        """
        :param mrn: optional initial value for mrn
        :type mrn: str
        :param study_instance_uid: options initial value for study instance uid
        :type study_instance_uid: str
        """
        wx.Dialog.__init__(self, None, title="Reimport from DICOM")
        self.roi_map = roi_map
        self.options = options
        self.initial_mrn = mrn
        self.initial_uid = study_instance_uid

        self.text_ctrl_mrn = wx.TextCtrl(self, wx.ID_ANY, "")
        self.radio_box_delete_from_db = wx.RadioBox(
            self,
            wx.ID_ANY,
            "Current Data",
            choices=["Delete from DB", "Keep in DB"],
            majorDimension=2,
            style=wx.RA_SPECIFY_ROWS,
        )
        self.combo_box_study_date = wx.ComboBox(
            self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.combo_box_uid = wx.ComboBox(
            self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY
        )
        self.button_reimport = wx.Button(self, wx.ID_OK, "Reimport")
        self.button_reimport.Disable()
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()
        self.__do_bind()
        self.__apply_initial_values()

        self.run()

    def __set_properties(self):
        self.radio_box_delete_from_db.SetSelection(0)
        self.combo_box_study_date.SetMinSize((200, 25))

    def __do_bind(self):
        self.Bind(wx.EVT_TEXT, self.mrn_ticker, id=self.text_ctrl_mrn.GetId())
        self.Bind(
            wx.EVT_COMBOBOX,
            self.study_date_ticker,
            id=self.combo_box_study_date.GetId(),
        )
        self.Bind(
            wx.EVT_COMBOBOX, self.uid_ticker, id=self.combo_box_uid.GetId()
        )

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, ""), wx.VERTICAL
        )
        sizer_input_date_uid = wx.BoxSizer(wx.HORIZONTAL)
        sizer_uid = wx.BoxSizer(wx.VERTICAL)
        sizer_input_date = wx.BoxSizer(wx.VERTICAL)
        sizer_input_mrn_db = wx.BoxSizer(wx.HORIZONTAL)
        sizer_mrn = wx.BoxSizer(wx.VERTICAL)
        label_mrn = wx.StaticText(self, wx.ID_ANY, "MRN:")
        sizer_mrn.Add(label_mrn, 0, wx.BOTTOM, 5)
        sizer_mrn.Add(self.text_ctrl_mrn, 0, wx.EXPAND | wx.RIGHT, 40)
        sizer_input_mrn_db.Add(sizer_mrn, 1, wx.TOP, 12)
        sizer_input_mrn_db.Add(self.radio_box_delete_from_db, 0, wx.ALL, 5)
        sizer_input.Add(sizer_input_mrn_db, 0, wx.EXPAND | wx.LEFT, 5)
        label_date = wx.StaticText(self, wx.ID_ANY, "Sim Study Date:")
        sizer_input_date.Add(label_date, 0, wx.BOTTOM, 5)
        sizer_input_date.Add(self.combo_box_study_date, 0, 0, 0)
        sizer_input_date_uid.Add(sizer_input_date, 0, wx.ALL | wx.EXPAND, 5)
        label_uid = wx.StaticText(self, wx.ID_ANY, "Study Instance UID:")
        sizer_uid.Add(label_uid, 0, wx.BOTTOM, 5)
        sizer_uid.Add(self.combo_box_uid, 0, wx.EXPAND, 0)
        sizer_input_date_uid.Add(sizer_uid, 1, wx.ALL | wx.EXPAND, 5)
        sizer_input.Add(sizer_input_date_uid, 0, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_input, 0, wx.ALL | wx.EXPAND, 5)
        sizer_ok_cancel.Add(self.button_reimport, 0, wx.ALL, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.ALL, 5)
        sizer_wrapper.Add(
            sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.RIGHT, 5
        )
        self.SetSizer(sizer_wrapper)
        sizer_wrapper.SetMinSize((700, 190))
        sizer_wrapper.Fit(self)
        self.Layout()
        self.Center()

    def __apply_initial_values(self):
        if self.initial_mrn is not None:
            self.text_ctrl_mrn.SetValue(self.initial_mrn)
        # if self.initial_uid is not None:
        #     self.combo_box_uid.SetSelection(self.initial_uid)

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK:
            if self.uid:
                self.action()
        self.Destroy()

    def mrn_ticker(self, evt):
        with DVH_SQL() as cnx:
            is_mrn_valid = cnx.is_mrn_imported(self.mrn)
        if is_mrn_valid:
            self.update_study_dates()
        else:
            self.combo_box_study_date.SetItems([])
            self.combo_box_uid.SetItems([])
            self.button_reimport.Disable()

    def study_date_ticker(self, evt):
        self.update_uids()

    def uid_ticker(self, evt):
        if self.combo_box_uid.GetValue():
            self.button_reimport.Enable()
        else:
            self.button_reimport.Disable()

    def update_study_dates(self):
        with DVH_SQL() as cnx:
            choices = cnx.get_unique_values(
                "Plans", "sim_study_date", "mrn = '%s'" % self.mrn
            )
        self.combo_box_study_date.SetItems(choices)
        if choices:
            self.combo_box_study_date.SetValue(choices[0])
        self.update_uids()

    def update_uids(self):

        date = ["is NULL", "= '%s'::date" % self.sim_study_date][
            self.sim_study_date != "None"
        ]
        with DVH_SQL() as cnx:
            if cnx.db_type == "sqlite":
                date = date.replace("::date", "")
            condition = "mrn = '%s' and sim_study_date %s" % (self.mrn, date)
            choices = cnx.get_unique_values(
                "Plans", "study_instance_uid", condition
            )
        self.combo_box_uid.SetItems(choices)
        if choices:
            self.combo_box_uid.SetValue(choices[0])
        else:
            self.combo_box_uid.SetValue(None)
        self.uid_ticker(None)

    @property
    def delete_from_db(self):
        return self.radio_box_delete_from_db.GetSelection() == 0

    @property
    def mrn(self):
        return self.text_ctrl_mrn.GetValue()

    @property
    def sim_study_date(self):
        return self.combo_box_study_date.GetValue()

    @property
    def uid(self):
        return self.combo_box_uid.GetValue()

    def action(self):
        with DVH_SQL() as cnx:
            dicom_files = cnx.get_dicom_file_paths(uid=self.uid)
            if self.delete_from_db:
                cnx.delete_rows("study_instance_uid = '%s'" % self.uid)
        inbox = self.options.INBOX_DIR
        move_imported_dicom_files(dicom_files, inbox)
        ImportDicomFrame(
            self.roi_map, self.options, inbox=inbox, auto_parse=True
        )


class SQLSettingsDialog(wx.Dialog):
    """
    Edit and validate SQL connection settings
    """

    def __init__(self, options, group=1):
        wx.Dialog.__init__(self, None)

        self.options = options
        self.group = group

        self.keys = ["host", "port", "dbname", "user", "password"]

        self.input = {"host": wx.ComboBox(self, wx.ID_ANY, "")}
        for key in self.keys:
            if key not in {"password", "host"}:
                self.input[key] = wx.TextCtrl(self, wx.ID_ANY, "")
        self.input["password"] = wx.TextCtrl(
            self, wx.ID_ANY, "", style=wx.TE_PASSWORD
        )

        self.db_type_radiobox = wx.RadioBox(
            self, wx.ID_ANY, "Database Type", choices=["SQLite", "Postgres"]
        )

        self.button = {
            "echo": wx.Button(self, wx.ID_ANY, "Echo"),
            "write_test": wx.Button(self, wx.ID_ANY, "Write Test"),
            "reload": wx.Button(self, wx.ID_ANY, "Reload Last Connection"),
            "ok": wx.Button(self, wx.ID_OK, "OK"),
            "cancel": wx.Button(self, wx.ID_CANCEL, "Cancel"),
        }

        self.db_types = ["sqlite", "pgsql"]

        self.ip_history = self.options.SQL_PGSQL_IP_HIST

        self.Bind(
            wx.EVT_BUTTON, self.button_echo, id=self.button["echo"].GetId()
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.button_write_test,
            id=self.button["write_test"].GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON, self.button_reload, id=self.button["reload"].GetId()
        )
        self.Bind(
            wx.EVT_RADIOBOX, self.on_db_radio, id=self.db_type_radiobox.GetId()
        )

        if self.group == 2:
            self.sync_groups = wx.CheckBox(self, wx.ID_ANY, "Sync to Group 1")
            self.Bind(
                wx.EVT_CHECKBOX,
                self.on_sync_groups,
                id=self.sync_groups.GetId(),
            )

        self.__set_properties()
        self.__do_layout()
        self.Center()

        self.load_sql_settings()

        if self.group == 2:
            self.on_sync_groups()

        self.run()

    def __set_properties(self):
        prepend = ["", "Group 2: "][self.group != 1]
        self.SetTitle("%sSQL Connection Settings" % prepend)

        # Set initial db_type_radiobox to loaded settings or pgsql if none found
        self.set_selected_db_type(self.options.DB_TYPE_GRPS[self.group])

        self.button["reload"].Enable(self.has_last_cnx)

        if self.group == 2:
            self.sync_groups.SetValue(self.options.SYNC_SQL_CNX)

    def set_host_items(self):
        if self.selected_db_type == "sqlite":
            db_files = [
                basename(f)
                for f in get_file_paths(DATA_DIR, extension=".db")
                if is_file_sqlite_db(f)
            ]
            db_files.sort()
            self.input["host"].SetItems(db_files)
        else:
            self.input["host"].SetItems(self.ip_history)

    def __do_layout(self):
        sizer_frame = wx.BoxSizer(wx.VERTICAL)
        sizer_echo = wx.BoxSizer(wx.HORIZONTAL)
        sizer_write_test = wx.BoxSizer(wx.HORIZONTAL)
        sizer_reload = wx.BoxSizer(wx.HORIZONTAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        grid_sizer = wx.GridSizer(5, 2, 5, 10)

        label_titles = [
            "Host:",
            "Port:",
            "Database Name:",
            "User Name:",
            "Password:",
        ]
        self.label = {
            key: wx.StaticText(self, wx.ID_ANY, label_titles[i])
            for i, key in enumerate(self.keys)
        }

        for key in self.keys:
            grid_sizer.Add(self.label[key], 0, wx.ALL, 0)
            grid_sizer.Add(self.input[key], 0, wx.ALL | wx.EXPAND, 0)

        if self.group == 2:
            note = wx.StaticText(
                self,
                wx.ID_ANY,
                "Optionally define an SQL connection for Group 2 queries. "
                "This connection is read-only. "
                "Your main SQL connection (i.e., Group 1) always applies to "
                "Database Administrator and Importing.",
            )
            sizer_frame.Add(note, 0, wx.ALL, 10)
            sizer_frame.Add(self.sync_groups, 0, wx.LEFT, 10)

        sizer_frame.Add(grid_sizer, 0, wx.ALL, 10)
        sizer_frame.Add(self.db_type_radiobox, 0, wx.EXPAND | wx.ALL, 5)
        sizer_buttons.Add(self.button["ok"], 1, wx.ALL | wx.EXPAND, 5)
        sizer_buttons.Add(self.button["cancel"], 1, wx.ALL | wx.EXPAND, 5)
        sizer_echo.Add(
            self.button["echo"], 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 5
        )
        sizer_write_test.Add(
            self.button["write_test"], 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 5
        )
        sizer_frame.Add(sizer_echo, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 5)
        sizer_frame.Add(sizer_write_test, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 5)
        sizer_reload.Add(
            self.button["reload"], 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 5
        )
        sizer_frame.Add(sizer_reload, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 5)
        sizer_frame.Add(sizer_buttons, 0, wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer_frame)
        self.Fit()
        if self.group == 2:
            note.Wrap(300)
            self.Fit()
        self.Layout()

    def load_sql_settings(self):
        self.set_host_items()

        if self.has_last_cnx:
            config = self.options.SQL_LAST_CNX_GRPS[self.group][
                self.selected_db_type
            ]
        else:
            config = self.options.DEFAULT_CNF[self.selected_db_type]

        self.clear_input()

        if self.selected_db_type == "sqlite":
            self.input["host"].SetValue(config["host"])
        else:
            for input_type in self.keys:
                if input_type in config:
                    self.input[input_type].SetValue(config[input_type])

    def button_echo(self, evt):
        if self.valid_sql_settings:
            wx.MessageBox(
                "Success!", "Echo SQL Database", wx.OK | wx.ICON_INFORMATION
            )
        else:
            wx.MessageBox(
                "Invalid credentials!",
                "Echo SQL Database",
                wx.OK | wx.ICON_WARNING,
            )

    def button_write_test(self, evt):
        results = self.write_test_results
        answers = {True: "Passed", False: "Failed", None: "N/A"}
        msg = "Write: %s\nDelete: %s" % (
            answers[results["write"]],
            answers[results["delete"]],
        )
        wx.MessageBox(msg, "SQL DB Write Test", wx.OK | wx.ICON_WARNING)

    def button_reload(self, evt):
        self.load_sql_settings()

    def write_successful_cnf(self):
        new_config = {
            key: self.input[key].GetValue()
            for key in self.keys
            if self.input[key].GetValue()
        }
        self.options.SQL_LAST_CNX_GRPS[self.group][
            self.selected_db_type
        ] = new_config
        self.options.DB_TYPE_GRPS[self.group] = self.selected_db_type

        if self.selected_db_type == "pgsql":
            new_host = self.input["host"].GetValue()
            if new_host in self.ip_history:
                self.ip_history.pop(self.ip_history.index(new_host))
            self.ip_history.insert(0, new_host)

        if self.group == 2:
            self.options.SYNC_SQL_CNX = bool(self.sync_groups.GetValue())

        self.options.save()

    @property
    def config(self):
        config = {
            key: self.input[key].GetValue()
            for key in self.keys
            if self.input[key].GetValue()
        }
        if self.selected_db_type == "pgsql":
            config["dbname"] = self.input["dbname"].GetValue()
        return config

    @property
    def valid_sql_settings(self):
        return echo_sql_db(self.config, db_type=self.selected_db_type)

    @property
    def write_test_results(self):
        return write_test(
            self.config, db_type=self.selected_db_type, group=self.group
        )

    def run(self):
        res = self.ShowModal()
        if res == wx.ID_OK:
            new_config = {
                key: self.input[key].GetValue()
                for key in self.keys
                if self.input[key].GetValue()
            }

            if echo_sql_db(new_config, db_type=self.selected_db_type):
                self.write_successful_cnf()
                with DVH_SQL(group=self.group) as cnx:
                    cnx.initialize_database()
            else:
                dlg = wx.MessageDialog(
                    self,
                    "Connection to database could not be established.",
                    "ERROR!",
                    wx.OK | wx.ICON_ERROR,
                )
                dlg.ShowModal()
        self.Destroy()

    def on_db_radio(self, *evt):
        self.load_sql_settings()
        self.button["reload"].Enable(self.has_last_cnx)

    @property
    def selected_db_type(self):
        return ["sqlite", "pgsql"][self.db_type_radiobox.GetSelection()]

    @property
    def unselected_db_type(self):
        return ["pgsql", "sqlite"][self.db_type_radiobox.GetSelection()]

    @property
    def has_last_cnx(self):
        return "host" in list(
            self.options.SQL_LAST_CNX_GRPS[self.group][self.selected_db_type]
        )

    def set_selected_db_type(self, db_type):
        self.db_type_radiobox.SetSelection({"sqlite": 0, "pgsql": 1}[db_type])

    def clear_input(self):
        for input_type in self.keys:
            self.input[input_type].SetValue("")
            if input_type != "host":
                self.input[input_type].Enable(self.selected_db_type == "pgsql")
                self.label[input_type].Enable(self.selected_db_type == "pgsql")

    def set_all_enable(self, status):
        for obj in self.input.values():
            obj.Enable(status)
        for obj in self.label.values():
            obj.Enable(status)

        for key in ["echo", "write_test", "reload"]:
            self.button[key].Enable(status)

        self.db_type_radiobox.Enable(status)

    def on_sync_groups(self, *evt):
        self.set_all_enable(not bool(self.sync_groups.GetValue()))
        self.load_sql_settings()


# ------------------------------------------------------
# Yes/No Dialogs based on tools.utilities.MessageDialog
#
# MessageDialog handles the layout and display, simply
# provide the wx parent, a message, and define over-ride
# action_yes and/or action_no for Yes/No button clicks
# ------------------------------------------------------
class DeleteAllData(MessageDialog):
    def __init__(self, parent, options):
        self.options = options
        MessageDialog.__init__(self, parent, "Delete All Data in Database")

    def action_yes(self):
        with DVH_SQL() as cnx:
            cnx.reinitialize_database()
        MoveFilesToInbox(
            self.parent, self.options.INBOX_DIR, self.options.IMPORTED_DIR
        )


class MoveFilesToInbox(MessageDialog):
    def __init__(self, parent, inbox_dir, imported_dir):
        self.parent = parent
        self.inbox_dir = inbox_dir
        self.imported_dir = imported_dir
        MessageDialog.__init__(self, parent, "Move files to inbox?")

    def action_yes(self):
        new_dir = join(
            self.inbox_dir,
            "previously_imported %s"
            % str(datetime.now())
            .split(".")[0]
            .replace(":", "-")
            .replace(" ", "_"),
        )
        rename(self.imported_dir, new_dir)
        mkdir(self.imported_dir)

    def action_no(self):
        DeleteImportedDirectory(self.parent, self.imported_dir)


class DeleteImportedDirectory(MessageDialog):
    def __init__(self, parent, directory):
        self.directory = directory
        MessageDialog.__init__(self, parent, "Delete Imported Directory?")

    def action_yes(self):
        delete_directory_contents(self.directory)


class MoveFiles(MessageDialog):
    def __init__(self, parent, files):
        self.parent = parent
        self.files = files
        MessageDialog.__init__(self, parent, "Move files to another location?")

    def action_yes(self):
        dlg = wx.DirDialog(
            self,
            "Choose directory",
            "",
            wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        if dlg.ShowModal() == wx.ID_OK:
            move_files_to_new_path(self.files, dlg.GetPath())
        dlg.Destroy()

    def action_no(self):
        DeleteFiles(self.parent, self.files)


class DeleteFiles(MessageDialog):
    def __init__(self, parent, files):
        self.files = files
        MessageDialog.__init__(self, parent, "Delete associated files?")

    def action_yes(self):
        for f in self.files:
            delete_file(f)


class DeleteFilesFromQuery(MessageDialog):
    def __init__(self, parent, dicom_file_query):
        self.dicom_file_query = dicom_file_query
        MessageDialog.__init__(self, parent, "Delete associated files?")

    def action_yes(self):
        delete_imported_dicom_files(self.dicom_file_query)

    def action_no(self):
        MoveFilesFromQuery(self.parent, self.dicom_file_query)


class MoveFilesFromQuery(MessageDialog):
    def __init__(self, parent, dicom_file_query):
        self.dicom_file_query = dicom_file_query
        MessageDialog.__init__(self, parent, "Move associated files?")

    def action_yes(self):
        dlg = wx.DirDialog(
            self.parent,
            "Choose directory",
            "",
            wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        )
        if dlg.ShowModal() == wx.ID_OK:
            move_imported_dicom_files(self.dicom_file_query, dlg.GetPath())
        dlg.Destroy()


class RebuildDB(MessageDialog):
    def __init__(self, parent, roi_map, options):
        self.roi_map = roi_map
        self.options = options
        MessageDialog.__init__(self, parent, "Rebuild Database from DICOM")

    def action_yes(self):
        with DVH_SQL() as cnx:
            cnx.reinitialize_database()

        ImportDicomFrame(
            self.roi_map,
            self.options,
            inbox=self.options.IMPORTED_DIR,
            auto_parse=True,
        )
