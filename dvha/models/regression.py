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
from dvha.models.plot import PlotRegression, PlotMultiVarRegression
from dvha.models.random_forest import RandomForestFrame, RandomForestWorker
from dvha.dialogs.export import save_data_to_file
from dvha.paths import ICONS, MODELS_DIR
from dvha.tools.utilities import set_msw_background_color, get_tree_ctrl_image


class RegressionFrame:
    """
    Object to be passed into notebook panel for the Regression tab
    """
    def __init__(self, parent, stats_data, options):
        """
        :param parent:  notebook panel in main view
        :type parent: Panel
        :param stats_data: object containing queried data applicable/parsed for statistical analysis
        :type stats_data: StatsData
        :param options: user options containing visual preferences
        :type options: Options
        """
        self.parent = parent
        self.options = options
        self.stats_data = stats_data
        self.choices = []

        self.y_variable_nodes = {}
        self.x_variable_nodes = {}

        self.__define_gui_objects()
        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        self.tree_ctrl_root = self.tree_ctrl.AddRoot('Regressions')

    def __define_gui_objects(self):
        self.window = wx.SplitterWindow(self.parent, wx.ID_ANY)
        self.pane_tree = wx.ScrolledWindow(self.window, wx.ID_ANY, style=wx.TAB_TRAVERSAL)
        self.tree_ctrl = wx.TreeCtrl(self.pane_tree, wx.ID_ANY)
        self.pane_plot = wx.Panel(self.window, wx.ID_ANY)
        self.combo_box_x_axis = wx.ComboBox(self.pane_plot, wx.ID_ANY, choices=[],
                                            style=wx.CB_DROPDOWN | wx.TE_READONLY)
        self.spin_button_x_axis = wx.SpinButton(self.pane_plot, wx.ID_ANY, style=wx.SP_WRAP)
        self.combo_box_y_axis = wx.ComboBox(self.pane_plot, wx.ID_ANY, choices=[],
                                            style=wx.CB_DROPDOWN | wx.TE_READONLY)
        self.spin_button_y_axis = wx.SpinButton(self.pane_plot, wx.ID_ANY, style=wx.SP_WRAP)
        self.checkbox = wx.CheckBox(self.pane_plot, wx.ID_ANY, "Include in Multi-Var\nRegression")
        self.plot = PlotRegression(self.pane_plot, self.options)
        self.button_multi_var_reg_model = wx.Button(self.pane_tree, wx.ID_ANY, 'Run Selected Model')
        self.button_multi_var_reg_model.Disable()
        self.button_single_var_export = wx.Button(self.pane_tree, wx.ID_ANY, 'Export Plot Data')
        self.button_single_var_plot_save = wx.Button(self.pane_tree, wx.ID_ANY, 'Save Plot')

    def __set_properties(self):
        self.pane_tree.SetScrollRate(20, 20)
        self.window.SetMinimumPaneSize(20)
        self.combo_box_x_axis.SetValue('ROI Volume')
        self.combo_box_y_axis.SetValue('ROI Max Dose')

        self.image_list = wx.ImageList(16, 16)
        self.images = {'y': self.image_list.Add(get_tree_ctrl_image(ICONS['custom_Y'])),
                       'x': self.image_list.Add(get_tree_ctrl_image(ICONS['custom_X']))}
        self.tree_ctrl.AssignImageList(self.image_list)

    def __do_bind(self):
        self.parent.Bind(wx.EVT_COMBOBOX, self.on_combo_box, id=self.combo_box_x_axis.GetId())
        self.parent.Bind(wx.EVT_COMBOBOX, self.on_combo_box, id=self.combo_box_y_axis.GetId())
        self.parent.Bind(wx.EVT_SPIN, self.spin_x, id=self.spin_button_x_axis.GetId())
        self.parent.Bind(wx.EVT_SPIN, self.spin_y, id=self.spin_button_y_axis.GetId())
        self.parent.Bind(wx.EVT_CHECKBOX, self.on_checkbox, id=self.checkbox.GetId())
        self.pane_tree.Bind(wx.EVT_BUTTON, self.on_regression, id=self.button_multi_var_reg_model.GetId())
        self.pane_tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_tree_select, id=self.tree_ctrl.GetId())

        self.pane_tree.Bind(wx.EVT_BUTTON, self.on_export, id=self.button_single_var_export.GetId())
        self.pane_tree.Bind(wx.EVT_BUTTON, self.on_save_plot, id=self.button_single_var_plot_save.GetId())

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_plot = wx.BoxSizer(wx.HORIZONTAL)
        sizer_plot_pane = wx.BoxSizer(wx.VERTICAL)
        sizer_plot_view = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.BoxSizer(wx.HORIZONTAL)

        sizer_y_axis = wx.BoxSizer(wx.VERTICAL)
        sizer_y_axis_select = wx.BoxSizer(wx.HORIZONTAL)
        sizer_x_axis = wx.BoxSizer(wx.VERTICAL)
        sizer_x_axis_select = wx.BoxSizer(wx.HORIZONTAL)

        sizer_single_var_export = wx.BoxSizer(wx.HORIZONTAL)

        sizer_tree = wx.BoxSizer(wx.VERTICAL)
        sizer_tree.Add(self.button_multi_var_reg_model, 0, wx.EXPAND | wx.ALL, 5)
        sizer_tree.Add(self.tree_ctrl, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_single_var_export.Add(self.button_single_var_export, 0, wx.EXPAND | wx.ALL, 5)
        sizer_single_var_export.Add(self.button_single_var_plot_save, 1, wx.EXPAND | wx.ALL, 5)
        sizer_tree.Add(sizer_single_var_export, 0, wx.EXPAND | wx.ALL, 5)
        self.pane_tree.SetSizer(sizer_tree)

        label_x_axis = wx.StaticText(self.pane_plot, wx.ID_ANY, "Independent Variable (x-axis):")
        sizer_x_axis.Add(label_x_axis, 0, 0, 0)
        sizer_x_axis_select.Add(self.combo_box_x_axis, 1, wx.EXPAND, 0)
        sizer_x_axis_select.Add(self.spin_button_x_axis, 0, 0, 0)
        sizer_x_axis.Add(sizer_x_axis_select, 1, wx.EXPAND, 0)
        sizer_input.Add(sizer_x_axis, 1, wx.ALL, 5)

        label_y_axis = wx.StaticText(self.pane_plot, wx.ID_ANY, "Dependent Variable (y-axis):")
        sizer_y_axis.Add(label_y_axis, 0, 0, 0)
        sizer_y_axis_select.Add(self.combo_box_y_axis, 1, wx.EXPAND, 0)
        sizer_y_axis_select.Add(self.spin_button_y_axis, 0, 0, 0)
        sizer_y_axis.Add(sizer_y_axis_select, 1, wx.EXPAND, 0)
        sizer_input.Add(sizer_y_axis, 1, wx.ALL, 5)

        sizer_input.Add(self.checkbox, 0, wx.ALL, 20)
        sizer_plot_pane.Add(sizer_input, 0, wx.EXPAND, 0)
        sizer_plot.Add(self.plot.layout, 1, wx.EXPAND, 0)
        sizer_plot_view.Add(sizer_plot, 1, wx.EXPAND, 10)
        sizer_plot_pane.Add(sizer_plot_view, 1, wx.EXPAND, 0)
        self.pane_plot.SetSizer(sizer_plot_pane)
        self.window.SplitVertically(self.pane_tree, self.pane_plot)
        sizer_wrapper.Add(self.window, 1, wx.EXPAND, 0)
        self.window.SetSashPosition(250)

        self.layout = sizer_wrapper

    @property
    def x_axis(self):
        return self.combo_box_x_axis.GetValue()

    @property
    def y_axis(self):
        return self.combo_box_y_axis.GetValue()

    def update_combo_box_choices(self):
        if self.stats_data:
            self.choices = self.stats_data.variables
            self.choices.sort()
            self.combo_box_x_axis.SetItems(self.choices)
            self.combo_box_y_axis.SetItems(self.choices)
            self.spin_button_x_axis.SetMax(len(self.choices)-1)
            self.spin_button_y_axis.SetMax(len(self.choices)-1)
            if 'ROI Volume' in self.choices and 'ROI Max Dose' in self.choices:
                initial_index_x = self.choices.index('ROI Volume')
                initial_index_y = self.choices.index('ROI Max Dose')
                self.spin_button_x_axis.SetValue(len(self.choices)-1-initial_index_x)
                self.spin_button_y_axis.SetValue(len(self.choices)-1-initial_index_y)
                self.combo_box_x_axis.SetValue(self.choices[initial_index_x])
                self.combo_box_y_axis.SetValue(self.choices[initial_index_y])
            self.update_plot()

    def on_combo_box(self, evt):
        self.sync_spin_buttons()
        self.update_plot()

    def update_plot(self):
        if self.combo_box_x_axis.GetValue() == self.combo_box_y_axis.GetValue():
            self.plot.clear_plot()
        else:
            self.plot.update_plot(self.stats_data.get_bokeh_data(self.x_axis, self.y_axis),
                                  self.combo_box_x_axis.GetValue(),
                                  self.stats_data.get_axis_title(self.x_axis),
                                  self.stats_data.get_axis_title(self.y_axis))

        if self.y_axis in list(self.y_variable_nodes) and self.x_axis in list(self.x_variable_nodes[self.y_axis]):
            self.checkbox.SetValue(True)
            self.tree_ctrl.SelectItem(self.x_variable_nodes[self.y_axis][self.x_axis])
        else:
            self.checkbox.SetValue(False)
            self.tree_ctrl.Unselect()
        if self.combo_box_x_axis.GetValue() == self.combo_box_y_axis.GetValue():
            self.checkbox.Disable()
        else:
            self.checkbox.Enable()

    def spin_x(self, evt):
        new_index = len(self.choices)-1 - int(self.spin_button_x_axis.GetValue())
        self.combo_box_x_axis.SetValue(self.choices[new_index])
        self.update_plot()

    def spin_y(self, evt):
        new_index = len(self.choices)-1 - int(self.spin_button_y_axis.GetValue())
        self.combo_box_y_axis.SetValue(self.choices[new_index])
        self.update_plot()

    def sync_spin_buttons(self):
        if self.x_axis:
            index = self.choices.index(self.x_axis)
            self.spin_button_x_axis.SetValue(len(self.choices)-1 - index)

            index = self.choices.index(self.y_axis)
            self.spin_button_y_axis.SetValue(len(self.choices)-1 - index)
        else:
            print('ERROR: x-axis choice is empty.')

    def on_checkbox(self, evt):
        y_value = self.combo_box_y_axis.GetValue()
        x_value = self.combo_box_x_axis.GetValue()
        [self.del_regression, self.add_regression][self.checkbox.GetValue()](y_value, x_value)

        self.button_multi_var_reg_model.Enable(bool(len(list(self.y_variable_nodes))))

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
            self.y_variable_nodes[y_var] = self.tree_ctrl.AppendItem(self.tree_ctrl_root, y_var)
            self.tree_ctrl.SetItemData(self.y_variable_nodes[y_var], None)
            self.tree_ctrl.SetItemImage(self.y_variable_nodes[y_var], self.images['y'], wx.TreeItemIcon_Normal)
        if y_var not in list(self.x_variable_nodes):
            self.x_variable_nodes[y_var] = {}
        if x_var not in self.x_variable_nodes[y_var]:
            self.x_variable_nodes[y_var][x_var] = self.tree_ctrl.AppendItem(self.y_variable_nodes[y_var], x_var)
            self.tree_ctrl.SetItemData(self.x_variable_nodes[y_var][x_var], None)
            self.tree_ctrl.SetItemImage(self.x_variable_nodes[y_var][x_var], self.images['x'],
                                        wx.TreeItemIcon_Normal)
        self.tree_ctrl.ExpandAll()
        if select_item and self.tree_ctrl.IsSelected(self.tree_ctrl_root):
            self.tree_ctrl.SelectItem(self.x_variable_nodes[self.y_axis][self.x_axis])

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
        Launch the multi-variable regression for the currently selected dependent variable
        """
        y_variable = self.combo_box_y_axis.GetValue()
        if y_variable in list(self.x_variable_nodes):
            x_variables = list(self.x_variable_nodes[y_variable])

            dlg = MultiVarResultsFrame(y_variable, x_variables, self.stats_data, self.options)
            dlg.Show()
        else:
            wx.MessageBox('No data has been selected for regression.', 'Regression Error',
                          wx.OK | wx.ICON_WARNING)

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

    def clear(self):
        self.plot.clear_plot()
        self.x_variable_nodes = {}
        self.y_variable_nodes = {}
        self.tree_ctrl.DeleteAllItems()
        self.tree_ctrl_root = self.tree_ctrl.AddRoot('Regressions')
        self.checkbox.SetValue(False)
        self.combo_box_x_axis.SetValue('ROI Volume')
        self.combo_box_y_axis.SetValue('ROI Max Dose')

    def get_y_vars(self):
        return list(self.y_variable_nodes)

    def get_x_vars(self, y_var):
        return list(self.x_variable_nodes[y_var])

    def get_save_data(self):
        return {y_var: [x_var for x_var in self.get_x_vars(y_var)] for y_var in self.get_y_vars()}

    def load_save_data(self, save_data):
        for y_var, x_vars in save_data.items():
            for x_var in x_vars:
                self.add_regression(y_var, x_var, select_item=False)

    @property
    def has_data(self):
        return bool(len(list(self.y_variable_nodes)))

    def on_save_plot(self, evt):
        save_data_to_file(self.pane_tree, 'Save linear regression plot', self.plot.html_str,
                          wildcard="HTML files (*.html)|*.html")

    def on_export(self, evt):
        save_data_to_file(self.pane_tree, 'Export linear regression data', self.plot.get_csv_data())


class MultiVarResultsFrame(wx.Frame):
    """
    Class to view multi-variable regression with data passed from RegressionFrame
    """
    def __init__(self, y_variable, x_variables, stats_data, options):
        """
        :param y_variable: dependent variable
        :type y_variable: str
        :param x_variables: independent variables
        :type x_variables: list
        :param stats_data: object containing queried data applicable/parsed for statistical analysis
        :type stats_data: StatsData
        :param options: user options containing visual preferences
        :type options: Options
        """
        wx.Frame.__init__(self, None, title="Multi-Variable Model for %s" % y_variable)

        set_msw_background_color(self)  # If windows, change the background color

        self.options = options

        self.plot = PlotMultiVarRegression(self, options)
        self.plot.update_plot(y_variable, x_variables, stats_data)

        algorithms = ['Random Forest', 'Support Vector Machines', 'Decision Trees', 'Gradient Boosted']
        self.button = {key: wx.Button(self, wx.ID_ANY, key) for key in algorithms}
        for key in algorithms:
            if key not in {'Random Forest'}:
                self.button[key].Disable()

        self.button_export = wx.Button(self, wx.ID_ANY, 'Export Plot Data')
        self.button_save_plot = wx.Button(self, wx.ID_ANY, 'Save Plot')
        self.button_save_model = wx.Button(self, wx.ID_ANY, 'Save Model')

        self.__do_bind()
        self.__do_subscribe()
        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        self.SetMinSize((825, 725))

    def __do_bind(self):
        self.Bind(wx.EVT_BUTTON, self.on_random_forest, id=self.button['Random Forest'].GetId())
        self.Bind(wx.EVT_BUTTON, self.on_export, id=self.button_export.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_save_plot, id=self.button_save_plot.GetId())
        self.Bind(wx.EVT_BUTTON, self.on_save_model, id=self.button_save_model.GetId())

    def __do_subscribe(self):
        pub.subscribe(self.show_plot, "random_forest_complete")

    def __do_layout(self):

        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_wrapper.Add(self.plot.layout, 1, wx.EXPAND | wx.ALL, 5)

        sizer_algo_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_algo_select = wx.BoxSizer(wx.HORIZONTAL)
        sizer_export_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_export_buttons.Add(self.button_export, 0, wx.ALL, 5)
        sizer_export_buttons.Add(self.button_save_plot, 0, wx.ALL, 5)
        sizer_export_buttons.Add(self.button_save_model, 0, wx.ALL, 5)
        sizer_algo_wrapper.Add(sizer_export_buttons, 0, wx.ALL, 5)
        text = wx.StaticText(self, wx.ID_ANY, "Compare with Machine Learning Module")
        sizer_algo_wrapper.Add(text, 0, wx.EXPAND | wx.ALL, 5)
        for key, button in self.button.items():
            sizer_algo_select.Add(button, 0, wx.EXPAND | wx.ALL, 5)
        sizer_algo_wrapper.Add(sizer_algo_select, 0, wx.ALL, 5)

        sizer_wrapper.Add(sizer_algo_wrapper, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer_wrapper)
        self.Fit()
        self.Layout()
        self.Center()

    def on_random_forest(self, evt):
        RandomForestWorker(self.plot.X, self.plot.y)

    def show_plot(self, msg):
        frame = RandomForestFrame(self.plot.y, msg['y_predict'], msg['mse'], self.options)
        frame.Show()

    def on_export(self, evt):
        save_data_to_file(self, 'Save multi-variable regression data to csv', self.plot.get_csv_data())

    def on_save_plot(self, evt):
        save_data_to_file(self, 'Save multi-variable regression plot', self.plot.html_str,
                          wildcard="HTML files (*.html)|*.html")

    def on_save_model(self, evt):
        data = {'y_variable': self.plot.y_variable,
                'regression': self.plot.reg}
        save_data_to_file(self, 'Save Model', data,
                          wildcard="MVR files (*.mvr)|*.mvr", data_type='pickle', initial_dir=MODELS_DIR)
        pub.sendMessage('control_chart_update_models')
