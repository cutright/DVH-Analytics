#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.regression.py
"""
Class to view and calculate linear regressions
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
from pubsub import pub
from dvha.tools.errors import ErrorDialog
from dvha.models.plot import PlotRegression, PlotMultiVarRegression
from dvha.models.machine_learning import (
    RandomForestFrame,
    GradientBoostingFrame,
    DecisionTreeFrame,
    SupportVectorRegressionFrame,
    MachineLearningModelViewer,
    MLPFrame,
)
from dvha.dialogs.export import save_data_to_file
from dvha.dialogs.main import SelectRegressionVariablesDialog
from dvha.options import DefaultOptions
from dvha.paths import ICONS, MODELS_DIR
from dvha.tools.errors import push_to_log
from dvha.tools.stats import MultiVariableRegression
from dvha.tools.utilities import (
    set_msw_background_color,
    get_tree_ctrl_image,
    get_window_size,
    load_object_from_file,
    set_frame_icon,
)


class RegressionFrame:
    """
    Object to be passed into notebook panel for the Regression tab
    """

    def __init__(self, main_app_frame):

        self.main_app_frame = main_app_frame
        self.parent = main_app_frame.notebook_tab["Regression"]
        self.options = main_app_frame.options
        self.group_data = main_app_frame.group_data
        self.group = 1
        self.choices = []

        self.y_variable_nodes = {}
        self.x_variable_nodes = {}

        self.__define_gui_objects()
        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        self.tree_ctrl_root = self.tree_ctrl.AddRoot("Regressions")

        self.mvr_frames = []

        set_msw_background_color(self.window, color="white")

    def __define_gui_objects(self):
        self.window = wx.SplitterWindow(self.parent, wx.ID_ANY)
        self.pane_tree = wx.ScrolledWindow(
            self.window, wx.ID_ANY, style=wx.TAB_TRAVERSAL
        )
        self.tree_ctrl = wx.TreeCtrl(self.pane_tree, wx.ID_ANY)
        self.pane_plot = wx.Panel(self.window, wx.ID_ANY)
        self.combo_box_x_axis = wx.ComboBox(
            self.pane_plot,
            wx.ID_ANY,
            choices=[],
            style=wx.CB_DROPDOWN | wx.TE_READONLY,
        )
        self.spin_button_x_axis = wx.SpinButton(
            self.pane_plot, wx.ID_ANY, style=wx.SP_WRAP
        )
        self.combo_box_y_axis = wx.ComboBox(
            self.pane_plot,
            wx.ID_ANY,
            choices=[],
            style=wx.CB_DROPDOWN | wx.TE_READONLY,
        )
        self.spin_button_y_axis = wx.SpinButton(
            self.pane_plot, wx.ID_ANY, style=wx.SP_WRAP
        )
        self.checkbox = wx.CheckBox(
            self.pane_plot, wx.ID_ANY, "Include", style=wx.ALIGN_RIGHT
        )
        self.plot = PlotRegression(self.pane_plot, self.options)
        self.button_multi_var_reg_model = wx.Button(
            self.pane_tree, wx.ID_ANY, "Run Multi-Variable Regressions"
        )
        self.button_multi_var_quick_select = wx.Button(
            self.pane_tree, wx.ID_ANY, "Variable Quick Select"
        )
        self.button_single_var_export = wx.Button(
            self.pane_tree, wx.ID_ANY, "Export CSV"
        )
        self.button_single_var_plot_save = wx.Button(
            self.pane_tree, wx.ID_ANY, "Save Figure"
        )

    def __set_properties(self):
        self.pane_tree.SetScrollRate(20, 20)
        self.window.SetMinimumPaneSize(20)
        self.combo_box_x_axis.SetValue("ROI Volume")
        self.combo_box_y_axis.SetValue("ROI Max Dose")

        self.image_list = wx.ImageList(16, 16)
        self.images = {
            "y": self.image_list.Add(get_tree_ctrl_image(ICONS["custom_Y"])),
            "x": self.image_list.Add(get_tree_ctrl_image(ICONS["custom_X"])),
        }
        self.tree_ctrl.AssignImageList(self.image_list)

    def __do_bind(self):
        self.parent.Bind(
            wx.EVT_COMBOBOX,
            self.on_combo_box,
            id=self.combo_box_x_axis.GetId(),
        )
        self.parent.Bind(
            wx.EVT_COMBOBOX,
            self.on_combo_box,
            id=self.combo_box_y_axis.GetId(),
        )
        self.parent.Bind(
            wx.EVT_SPIN, self.spin_x, id=self.spin_button_x_axis.GetId()
        )
        self.parent.Bind(
            wx.EVT_SPIN, self.spin_y, id=self.spin_button_y_axis.GetId()
        )
        self.parent.Bind(
            wx.EVT_CHECKBOX, self.on_checkbox, id=self.checkbox.GetId()
        )
        self.pane_tree.Bind(
            wx.EVT_BUTTON,
            self.on_regression,
            id=self.button_multi_var_reg_model.GetId(),
        )
        self.pane_tree.Bind(
            wx.EVT_BUTTON,
            self.on_quick_select,
            id=self.button_multi_var_quick_select.GetId(),
        )
        self.pane_tree.Bind(
            wx.EVT_TREE_SEL_CHANGED,
            self.on_tree_select,
            id=self.tree_ctrl.GetId(),
        )

        self.pane_tree.Bind(
            wx.EVT_BUTTON,
            self.on_export,
            id=self.button_single_var_export.GetId(),
        )
        self.pane_tree.Bind(
            wx.EVT_BUTTON,
            self.on_save_plot,
            id=self.button_single_var_plot_save.GetId(),
        )

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        self.sizer_plot = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_plot_pane = wx.BoxSizer(wx.VERTICAL)
        self.sizer_plot_view = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_check_box = wx.BoxSizer(wx.HORIZONTAL)

        sizer_y_axis = wx.BoxSizer(wx.VERTICAL)
        sizer_y_axis_select = wx.BoxSizer(wx.HORIZONTAL)
        sizer_x_axis = wx.BoxSizer(wx.VERTICAL)
        sizer_x_axis_select = wx.BoxSizer(wx.HORIZONTAL)

        sizer_single_var_export = wx.BoxSizer(wx.HORIZONTAL)

        sizer_tree = wx.BoxSizer(wx.VERTICAL)
        sizer_tree.Add(
            self.button_multi_var_reg_model,
            0,
            wx.EXPAND | wx.TOP | wx.LEFT | wx.RIGHT,
            5,
        )
        sizer_tree.Add(
            self.button_multi_var_quick_select,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
            5,
        )
        sizer_tree.Add(self.tree_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_single_var_export.Add(
            self.button_single_var_export,
            1,
            wx.EXPAND | wx.BOTTOM | wx.RIGHT,
            5,
        )
        sizer_single_var_export.Add(
            self.button_single_var_plot_save,
            1,
            wx.EXPAND | wx.LEFT | wx.BOTTOM,
            5,
        )
        sizer_tree.Add(sizer_single_var_export, 0, wx.EXPAND | wx.ALL, 5)
        self.pane_tree.SetSizer(sizer_tree)

        label_x_axis = wx.StaticText(
            self.pane_plot, wx.ID_ANY, "Independent Variable (x-axis):"
        )
        sizer_check_box.Add(label_x_axis, 1, wx.EXPAND, 0)
        sizer_check_box.Add(self.checkbox, 0, wx.LEFT | wx.RIGHT, 10)
        sizer_x_axis.Add(sizer_check_box, 1, wx.EXPAND, 0)
        sizer_x_axis_select.Add(self.combo_box_x_axis, 1, wx.EXPAND, 0)
        sizer_x_axis_select.Add(self.spin_button_x_axis, 0, wx.EXPAND, 0)
        sizer_x_axis.Add(sizer_x_axis_select, 1, wx.EXPAND, 0)
        sizer_input.Add(sizer_x_axis, 1, wx.ALL, 5)

        sizer_input.Add((30, 10), 0, 0, 0)

        label_y_axis = wx.StaticText(
            self.pane_plot, wx.ID_ANY, "Dependent Variable (y-axis):"
        )
        sizer_y_axis.Add(label_y_axis, 1, 0, 0)
        sizer_y_axis_select.Add(self.combo_box_y_axis, 1, wx.EXPAND, 0)
        sizer_y_axis_select.Add(self.spin_button_y_axis, 0, wx.EXPAND, 0)
        sizer_y_axis.Add(sizer_y_axis_select, 1, wx.EXPAND, 0)
        sizer_input.Add(sizer_y_axis, 1, wx.ALL, 5)

        self.sizer_plot_pane.Add(sizer_input, 0, wx.EXPAND, 0)
        # self.sizer_plot.Add(self.plot.layout, 1, wx.EXPAND, 0)
        self.sizer_plot_view.Add(self.sizer_plot, 1, wx.EXPAND, 10)
        self.sizer_plot_pane.Add(self.sizer_plot_view, 1, wx.EXPAND, 0)
        self.pane_plot.SetSizer(self.sizer_plot_pane)
        self.window.SplitVertically(self.pane_tree, self.pane_plot)
        sizer_wrapper.Add(self.window, 1, wx.EXPAND, 0)
        self.window.SetSashPosition(250)

        self.layout = sizer_wrapper

    def add_plot_to_layout(self):
        self.plot.init_layout()
        self.sizer_plot.Add(self.plot.layout, 1, wx.EXPAND, 0)
        self.update_plot()
        self.pane_plot.Layout()

    @property
    def x_axis(self):
        return self.combo_box_x_axis.GetValue()

    @property
    def y_axis(self):
        return self.combo_box_y_axis.GetValue()

    def update_combo_box_choices(self):
        if self.group_data[1]["stats_data"]:
            self.choices = self.group_data[1]["stats_data"].variables
            self.choices.sort()
            self.combo_box_x_axis.SetItems(self.choices)
            self.combo_box_y_axis.SetItems(self.choices)
            self.spin_button_x_axis.SetMax(len(self.choices) - 1)
            self.spin_button_y_axis.SetMax(len(self.choices) - 1)
            if "ROI Volume" in self.choices and "ROI Max Dose" in self.choices:
                initial_index_x = self.choices.index("ROI Volume")
                initial_index_y = self.choices.index("ROI Max Dose")
                self.spin_button_x_axis.SetValue(
                    len(self.choices) - 1 - initial_index_x
                )
                self.spin_button_y_axis.SetValue(
                    len(self.choices) - 1 - initial_index_y
                )
                self.combo_box_x_axis.SetValue(self.choices[initial_index_x])
                self.combo_box_y_axis.SetValue(self.choices[initial_index_y])
            self.update_plot()

    def on_combo_box(self, evt):
        self.sync_spin_buttons()
        self.update_plot()

    def update_plot(self):
        if (
            self.combo_box_x_axis.GetValue()
            == self.combo_box_y_axis.GetValue()
        ):
            self.plot.clear_plot()
        else:
            stats_data = {
                grp: self.group_data[grp]["stats_data"] for grp in [1, 2]
            }
            plot_data = {
                1: stats_data[1].get_bokeh_data(self.x_axis, self.y_axis)
            }
            if stats_data[2] is not None:
                plot_data[2] = stats_data[2].get_bokeh_data(
                    self.x_axis, self.y_axis
                )
            else:
                plot_data[2] = None
            self.plot.update_plot(
                plot_data,
                self.group,
                self.combo_box_x_axis.GetValue(),
                stats_data[1].get_axis_title(self.x_axis),
                stats_data[1].get_axis_title(self.y_axis),
            )

        if self.y_axis in list(self.y_variable_nodes) and self.x_axis in list(
            self.x_variable_nodes[self.y_axis]
        ):
            self.checkbox.SetValue(True)
            self.tree_ctrl.SelectItem(
                self.x_variable_nodes[self.y_axis][self.x_axis]
            )
        else:
            self.checkbox.SetValue(False)
            self.tree_ctrl.Unselect()
        if (
            self.combo_box_x_axis.GetValue()
            == self.combo_box_y_axis.GetValue()
        ):
            self.checkbox.Disable()
        else:
            self.checkbox.Enable()

    def spin_x(self, evt):
        new_index = (
            len(self.choices) - 1 - int(self.spin_button_x_axis.GetValue())
        )
        self.combo_box_x_axis.SetValue(self.choices[new_index])
        self.update_plot()

    def spin_y(self, evt):
        new_index = (
            len(self.choices) - 1 - int(self.spin_button_y_axis.GetValue())
        )
        self.combo_box_y_axis.SetValue(self.choices[new_index])
        self.update_plot()

    def sync_spin_buttons(self):
        if self.x_axis:
            index = self.choices.index(self.x_axis)
            self.spin_button_x_axis.SetValue(len(self.choices) - 1 - index)

            index = self.choices.index(self.y_axis)
            self.spin_button_y_axis.SetValue(len(self.choices) - 1 - index)
        else:
            msg = "RegressionFrame.sync_spin_buttons: x-axis choice is empty."
            push_to_log(msg=msg)

    def on_checkbox(self, *evt):
        y_value = self.combo_box_y_axis.GetValue()
        x_value = self.combo_box_x_axis.GetValue()
        [self.del_regression, self.add_regression][self.checkbox.GetValue()](
            y_value, x_value
        )

    def add_regression(self, y_var, x_var, select_item=True):
        """
        Add the currently plotted variables to the TreeCtrl to be available for multi-variable regression
        :param y_var: dependent variable
        :type y_var: str
        :param x_var: independent variable
        :type x_var: str
        :param select_item: If True, select the item in the TreeCtrl
        """

        if y_var not in list(self.y_variable_nodes):
            self.y_variable_nodes[y_var] = self.tree_ctrl.AppendItem(
                self.tree_ctrl_root, y_var
            )
            self.tree_ctrl.SetItemData(self.y_variable_nodes[y_var], None)
            self.tree_ctrl.SetItemImage(
                self.y_variable_nodes[y_var],
                self.images["y"],
                wx.TreeItemIcon_Normal,
            )
        if y_var not in list(self.x_variable_nodes):
            self.x_variable_nodes[y_var] = {}
        if x_var not in self.x_variable_nodes[y_var]:
            self.x_variable_nodes[y_var][x_var] = self.tree_ctrl.AppendItem(
                self.y_variable_nodes[y_var], x_var
            )
            self.tree_ctrl.SetItemData(
                self.x_variable_nodes[y_var][x_var], None
            )
            self.tree_ctrl.SetItemImage(
                self.x_variable_nodes[y_var][x_var],
                self.images["x"],
                wx.TreeItemIcon_Normal,
            )
        self.tree_ctrl.ExpandAll()
        if select_item and self.tree_ctrl.IsSelected(self.tree_ctrl_root):
            self.tree_ctrl.SelectItem(
                self.x_variable_nodes[self.y_axis][self.x_axis]
            )

    def del_regression(self, y_var, x_var):
        """
        Remove x_var from the independent variables of the y_var model, update the tree ctrl
        :param y_var: dependent variable
        :type y_var: str
        :param x_var: independent variable
        :type x_var: str
        """
        if y_var in list(self.y_variable_nodes):
            if x_var in list(self.x_variable_nodes[y_var]):
                self.tree_ctrl.Delete(self.x_variable_nodes[y_var][x_var])
                self.x_variable_nodes[y_var].pop(x_var)
                if not list(self.x_variable_nodes[y_var]):
                    self.x_variable_nodes.pop(y_var)
                    self.tree_ctrl.Delete(self.y_variable_nodes[y_var])
                    self.y_variable_nodes.pop(y_var)
        self.tree_ctrl.Unselect()

    def on_regression(self, evt):
        """
        Launch the multi-variable regression for all x_variable_nodes
        """
        if not list(self.x_variable_nodes):
            wx.MessageBox(
                "No data has been selected for regression.",
                "Regression Error",
                wx.OK | wx.ICON_WARNING,
            )
        else:
            for y_variable in list(self.x_variable_nodes):
                x_variables = list(self.x_variable_nodes[y_variable])

                try:
                    self.mvr_frames.append(
                        MultiVarResultsFrame(
                            self.main_app_frame,
                            y_variable,
                            x_variables,
                            self.group_data,
                            self.group,
                            self.options,
                        )
                    )
                    self.mvr_frames[-1].Show()
                except Exception as e:
                    msg = "Failed on regression for %s\n%s" % (
                        y_variable,
                        str(e),
                    )
                    ErrorDialog(
                        self.parent, msg, "Multi-Variable Regression Error"
                    )

    def on_tree_select(self, evt):
        selection = evt.GetItem()
        x_var, y_var = self.get_x_y_of_node(selection)
        if y_var is not None:
            self.combo_box_y_axis.SetValue(y_var)
        if x_var is not None:
            self.combo_box_x_axis.SetValue(x_var)

        if any([x_var, y_var]):
            self.update_plot()

        self.sync_spin_buttons()

    def get_x_y_of_node(self, node):
        for y_var in list(self.x_variable_nodes):
            if node == self.y_variable_nodes[y_var]:
                return None, y_var
            for x_var, x_node in self.x_variable_nodes[y_var].items():
                if node == x_node:
                    return x_var, y_var
        return None, None

    def clear(self, new_group_data):
        self.group_data = new_group_data
        self.group = 1
        self.plot.clear_plot()
        self.x_variable_nodes = {}
        self.y_variable_nodes = {}
        self.tree_ctrl.DeleteAllItems()
        self.tree_ctrl_root = self.tree_ctrl.AddRoot("Regressions")
        self.checkbox.SetValue(False)
        self.combo_box_x_axis.SetValue("ROI Volume")
        self.combo_box_y_axis.SetValue("ROI Max Dose")

    def get_y_vars(self):
        return list(self.y_variable_nodes)

    def get_x_vars(self, y_var):
        return list(self.x_variable_nodes[y_var])

    def get_save_data(self):
        return {
            y_var: [x_var for x_var in self.get_x_vars(y_var)]
            for y_var in self.get_y_vars()
        }

    def load_save_data(self, save_data):
        for y_var, x_vars in save_data.items():
            for x_var in x_vars:
                self.add_regression(y_var, x_var, select_item=False)

    @property
    def has_data(self):
        return bool(len(list(self.y_variable_nodes)))

    def on_save_plot(self, *evt):
        title = "Save Linear Regression Plot"
        export_frame = self.main_app_frame.export_figure
        attr_dicts = None if export_frame is None else export_frame.attr_dicts
        self.plot.save_figure_dlg(self.pane_tree, title, attr_dicts=attr_dicts)

    def on_export(self, evt):
        save_data_to_file(
            self.pane_tree,
            "Export linear regression data",
            self.plot.get_csv_data(),
        )

    def on_quick_select(self, evt):
        if self.y_axis in list(self.x_variable_nodes):
            selections = list(self.x_variable_nodes[self.y_axis])
        else:
            selections = None
        choices = [
            choice
            for choice in self.combo_box_x_axis.GetItems()
            if choice != self.y_axis
        ]
        choices.sort()
        dlg = SelectRegressionVariablesDialog(
            self.y_axis, choices, selections=selections
        )
        res = dlg.ShowModal()

        if res == wx.ID_OK:
            for value in dlg.independent_variable_choices:
                if value in dlg.selected_values:
                    if self.y_axis not in list(self.x_variable_nodes) or (
                        self.y_axis in list(self.x_variable_nodes)
                        and value
                        not in list(self.x_variable_nodes[self.y_axis])
                    ):
                        self.add_regression(
                            dlg.dependent_variable, value, select_item=False
                        )
                else:
                    if self.y_axis in list(
                        self.x_variable_nodes
                    ) and value in list(self.x_variable_nodes[self.y_axis]):
                        self.del_regression(dlg.dependent_variable, value)
            if (
                self.x_axis in dlg.selected_values
                and not self.checkbox.GetValue()
            ):
                self.checkbox.SetValue(True)
                self.on_checkbox()
        dlg.Destroy()

    def close_mvr_frames(self):
        for frame in self.mvr_frames:
            if type(frame) is MultiVarResultsFrame:
                frame.close_ml_frames()
                try:
                    frame.Close()
                except RuntimeError:
                    pass

    def apply_plot_options(self):
        self.plot.apply_options()
        for mvr_frame in self.mvr_frames:
            try:
                mvr_frame.apply_plot_options()
            except RuntimeError:
                pass


class MultiVarResultsFrame(wx.Frame):
    """
    Class to view multi-variable regression with data passed from RegressionFrame
    """

    def __init__(
        self,
        main_app_frame,
        y_variable,
        x_variables,
        group_data,
        group,
        options,
        auto_update_plot=True,
    ):
        """
        :param y_variable: dependent variable
        :type y_variable: str
        :param x_variables: independent variables
        :type x_variables: list
        :param group_data: dvhs, table, and stats_data
        :type group_data: dict
        :param options: user options containing visual preferences
        :type options: Options
        """
        wx.Frame.__init__(
            self,
            None,
            title="Multi-Variable Model for %s: Group %s"
            % (y_variable, group),
        )

        self.main_app_frame = main_app_frame
        self.y_variable = y_variable
        self.x_variables = x_variables
        self.group_data = group_data
        self.group = group
        self.stats_data = group_data[group]["stats_data"]

        set_msw_background_color(
            self
        )  # If windows, change the background color
        set_frame_icon(self)

        self.options = options

        self.plot = PlotMultiVarRegression(self, options, group)
        if auto_update_plot:
            self.plot.update_plot(y_variable, x_variables, self.stats_data)
            msg = {
                "y_variable": y_variable,
                "x_variables": x_variables,
                "regression": self.plot.reg,
                "group": group,
            }
            pub.sendMessage("control_chart_set_model", **msg)

        self.button_back_elimination = wx.Button(
            self, wx.ID_ANY, "Backward Elimination"
        )
        self.button_export = wx.Button(self, wx.ID_ANY, "Export CSV")
        self.button_save_figure = wx.Button(self, wx.ID_ANY, "Save Figure")
        self.button_save_model = wx.Button(self, wx.ID_ANY, "Save MVR Model")
        self.button_load_mlr_model = wx.Button(
            self, wx.ID_ANY, "Load ML Model"
        )
        algorithms = [
            "Random Forest",
            "Support Vector Machine",
            "Decision Tree",
            "Gradient Boosting",
            "Multilayer Perceptron",
        ]
        self.button = {
            key: wx.Button(self, wx.ID_ANY, key) for key in algorithms
        }
        self.radiobox_include_back_elim = wx.RadioBox(
            self, wx.ID_ANY, "Include all x-variables?", choices=["Yes", "No"]
        )

        self.__do_bind()
        self.__set_properties()
        self.__do_layout()

        self.ml_frames = []

    def __set_properties(self):
        self.SetMinSize(get_window_size(0.491, 0.690))
        self.radiobox_include_back_elim.SetSelection(0)
        self.radiobox_include_back_elim.Disable()
        self.radiobox_include_back_elim.SetToolTip(
            "Set to No if you want to the machine learning to only include "
            "variables that survived the backward elimination."
        )

    def __do_bind(self):
        self.Bind(
            wx.EVT_BUTTON,
            self.on_random_forest,
            id=self.button["Random Forest"].GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_gradient_boosting,
            id=self.button["Gradient Boosting"].GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_decision_tree,
            id=self.button["Decision Tree"].GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_support_vector_regression,
            id=self.button["Support Vector Machine"].GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_multilayer_perceptron,
            id=self.button["Multilayer Perceptron"].GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_back_elimination,
            id=self.button_back_elimination.GetId(),
        )
        self.Bind(wx.EVT_BUTTON, self.on_export, id=self.button_export.GetId())
        self.Bind(
            wx.EVT_BUTTON,
            self.on_save_figure,
            id=self.button_save_figure.GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_save_model,
            id=self.button_save_model.GetId(),
        )
        self.Bind(
            wx.EVT_BUTTON,
            self.on_load_mlr_model,
            id=self.button_load_mlr_model.GetId(),
        )
        self.Bind(wx.EVT_SIZE, self.on_resize)

    def __do_layout(self):

        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_wrapper.Add(self.plot.layout, 1, wx.EXPAND | wx.ALL, 5)

        sizer_algo_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_algo_select = wx.BoxSizer(wx.HORIZONTAL)
        sizer_export_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_export_buttons.Add(self.button_back_elimination, 0, wx.ALL, 5)
        sizer_export_buttons.Add(self.button_export, 0, wx.ALL, 5)
        sizer_export_buttons.Add(self.button_save_figure, 0, wx.ALL, 5)
        sizer_export_buttons.Add(self.button_save_model, 0, wx.ALL, 5)
        sizer_algo_wrapper.Add(sizer_export_buttons, 0, wx.ALL, 5)
        text = wx.StaticText(
            self, wx.ID_ANY, "Compare with Machine Learning Module"
        )
        sizer_algo_wrapper.Add(text, 0, wx.EXPAND | wx.ALL, 5)
        sizer_algo_select.Add(
            self.button_load_mlr_model, 0, wx.EXPAND | wx.ALL, 5
        )
        for key, button in self.button.items():
            sizer_algo_select.Add(button, 0, wx.EXPAND | wx.ALL, 5)
        sizer_algo_select.Add(
            self.radiobox_include_back_elim, 0, wx.EXPAND | wx.ALL, 5
        )
        sizer_algo_wrapper.Add(sizer_algo_select, 0, wx.ALL, 5)

        sizer_wrapper.Add(sizer_algo_wrapper, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer_wrapper)
        self.Fit()
        self.Layout()
        self.Center()

    @property
    def ml_include_all(self):
        return bool(1 - self.radiobox_include_back_elim.GetSelection())

    @property
    def final_stats_data(self):
        return self.plot.get_final_stats_data(include_all=self.ml_include_all)

    def on_random_forest(self, evt):
        self.ml_frames.append(
            RandomForestFrame(self.main_app_frame, self.final_stats_data)
        )

    def on_gradient_boosting(self, evt):
        self.ml_frames.append(
            GradientBoostingFrame(self.main_app_frame, self.final_stats_data)
        )

    def on_decision_tree(self, evt):
        self.ml_frames.append(
            DecisionTreeFrame(self.main_app_frame, self.final_stats_data)
        )

    def on_support_vector_regression(self, evt):
        self.ml_frames.append(
            SupportVectorRegressionFrame(
                self.main_app_frame, self.final_stats_data
            )
        )

    def on_multilayer_perceptron(self, evt):
        self.ml_frames.append(
            MLPFrame(self.main_app_frame, self.final_stats_data)
        )

    def on_export(self, evt):
        save_data_to_file(
            self,
            "Save multi-variable regression data to csv",
            self.plot.get_csv_data(),
        )

    def on_back_elimination(self, *evt):
        wait = wx.BusyInfo("Please Wait\nPerforming Backward Elimination")
        self.plot.backward_elimination()
        del wait
        self.radiobox_include_back_elim.Enable()

    def on_save_figure(self, *evt):
        title = "Save multi-variable regression plot"
        export_frame = self.main_app_frame.export_figure
        attr_dicts = None if export_frame is None else export_frame.attr_dicts
        self.plot.save_figure_dlg(self, title, attr_dicts=attr_dicts)

    def on_save_model(self, evt):
        data = {
            "y_variable": self.plot.y_variable,
            "regression": self.plot.reg,
            "x_variables": self.plot.x_variables,
            "regression_type": "multi-variable-linear",
            "version": DefaultOptions().VERSION,
        }
        save_data_to_file(
            self,
            "Save Model",
            data,
            wildcard="MVR files (*.mvr)|*.mvr",
            data_type="pickle",
            initial_dir=MODELS_DIR,
        )

    def on_load_mlr_model(self, evt):
        MachineLearningModelViewer(
            self, self.group_data, self.group, self.options, mvr=self.plot.reg
        )

    def redraw_plot(self):
        self.plot.redraw_plot()

    def on_resize(self, *evt):
        try:
            self.Refresh()
            self.Layout()
            wx.CallAfter(self.redraw_plot)
        except RuntimeError:
            pass

    def close_ml_frames(self):
        for frame in self.ml_frames:
            if hasattr(frame, "Close"):
                try:
                    frame.Close()
                except RuntimeError:
                    pass

    def apply_plot_options(self):
        self.plot.apply_options()
        self.plot.redraw_plot()
        for frame in self.ml_frames:
            try:
                frame.plot.apply_options()
                frame.plot.redraw_plot()
            except RuntimeError:
                pass


class LoadMultiVarModelFrame(MultiVarResultsFrame):
    def __init__(
        self, main_app_frame, model_file_path, group_data, group, options
    ):
        self.loaded_data = load_object_from_file(model_file_path)
        self.stats_data = group_data[group]["stats_data"]
        try:
            if self.is_valid:
                y_variable = self.loaded_data["y_variable"]
                x_variables = self.loaded_data["x_variables"]
                stats_data = group_data[group]["stats_data"]

                MultiVarResultsFrame.__init__(
                    self,
                    main_app_frame,
                    y_variable,
                    x_variables,
                    group_data,
                    group,
                    options,
                    auto_update_plot=False,
                )
                X, y = stats_data.get_X_and_y(y_variable, x_variables)

                reg = MultiVariableRegression(
                    X, y, saved_reg=self.loaded_data["regression"]
                )
                self.plot.update_plot(
                    y_variable, x_variables, self.stats_data, reg=reg
                )

                self.Show()
            else:
                if self.stats_data is None:
                    msg = "No data has been queried for Group %s." % group
                elif not self.is_mvr:
                    msg = "Selected file is not a valid multi-variable regression save file."
                elif not self.stats_data_has_y:
                    msg = (
                        "The model's dependent variable is not found in your queried data:\n%s"
                        % self.y_variable
                    )
                elif self.missing_x_variables:
                    msg = (
                        "Your queried data is missing the following independent variables:\n%s"
                        % ", ".join(self.missing_x_variables)
                    )
                else:
                    msg = "Unknown error."

                wx.MessageBox(
                    msg,
                    "Model Loading Error",
                    wx.OK | wx.OK_DEFAULT | wx.ICON_WARNING,
                )
        except Exception as e:
            msg = str(e)
            wx.MessageBox(
                msg,
                "Model Loading Error",
                wx.OK | wx.OK_DEFAULT | wx.ICON_WARNING,
            )

    @property
    def is_mvr(self):
        return (
            "regression_type" in list(self.loaded_data)
            and self.loaded_data["regression_type"] == "multi-variable-linear"
        )

    @property
    def is_valid(self):
        return (
            self.stats_data is not None
            and self.is_mvr
            and not self.missing_x_variables
            and self.stats_data_has_y
        )

    @property
    def missing_x_variables(self):
        return [
            x
            for x in self.loaded_data["x_variables"]
            if x not in list(self.stats_data.data)
        ]

    @property
    def stats_data_has_y(self):
        return self.loaded_data["y_variable"] in list(self.stats_data.data)
