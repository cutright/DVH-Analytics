#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import wx
from models.plot import PlotRegression, PlotMultiVarRegression
from scipy import stats
import numpy as np
from models.random_forest import RandomForestFrame, RandomForestWorker
from pubsub import pub


class RegressionFrame:
    def __init__(self, parent, data, *args, **kwds):
        self.parent = parent
        # self.dvh = dvh
        self.stats_data = data
        self.choices = []

        self.__define_gui_objects()
        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

    def __define_gui_objects(self):
        self.window = wx.SplitterWindow(self.parent, wx.ID_ANY)
        self.pane_tree = wx.ScrolledWindow(self.window, wx.ID_ANY, style=wx.TAB_TRAVERSAL)
        self.tree_ctrl = wx.TreeCtrl(self.pane_tree, wx.ID_ANY)
        self.pane_plot = wx.Panel(self.window, wx.ID_ANY)
        self.combo_box_x_axis = wx.ComboBox(self.pane_plot, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.TE_READONLY)
        self.spin_button_x_axis = wx.SpinButton(self.pane_plot, wx.ID_ANY, style=wx.SP_WRAP)
        self.combo_box_y_axis = wx.ComboBox(self.pane_plot, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.TE_READONLY)
        self.spin_button_y_axis = wx.SpinButton(self.pane_plot, wx.ID_ANY, style=wx.SP_WRAP)
        self.checkbox = wx.CheckBox(self.pane_plot, wx.ID_ANY, "Include in Multi-Var\nRegression")
        self.plot = PlotRegression(self.pane_plot)
        self.button_multi_var_reg_model = wx.Button(self.pane_tree, wx.ID_ANY, 'Run Model')

    def __set_properties(self):
        self.pane_tree.SetScrollRate(10, 10)
        self.window.SetMinimumPaneSize(20)
        self.combo_box_x_axis.SetValue('ROI Max Dose')
        self.combo_box_y_axis.SetValue('ROI Volume')

        self.tree_ctrl_root = self.tree_ctrl.AddRoot('Regressions')
        self.y_variable_nodes = {}
        self.x_variable_nodes = {}

        self.image_list = wx.ImageList(16, 16)
        self.images = {'y': self.image_list.Add(wx.Image("icons/iconfinder_r2d2_216973.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap()),
                       'x': self.image_list.Add( wx.Image("icons/iconfinder_x-wing_298963.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap())}
        self.tree_ctrl.AssignImageList(self.image_list)

    def __do_bind(self):
        self.parent.Bind(wx.EVT_COMBOBOX, self.on_combo_box, id=self.combo_box_x_axis.GetId())
        self.parent.Bind(wx.EVT_COMBOBOX, self.on_combo_box, id=self.combo_box_y_axis.GetId())
        self.parent.Bind(wx.EVT_SPIN, self.spin_x, id=self.spin_button_x_axis.GetId())
        self.parent.Bind(wx.EVT_SPIN, self.spin_y, id=self.spin_button_y_axis.GetId())
        self.parent.Bind(wx.EVT_CHECKBOX, self.on_checkbox, id=self.checkbox.GetId())
        self.pane_tree.Bind(wx.EVT_BUTTON, self.on_regression, id=self.button_multi_var_reg_model.GetId())

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

        sizer_tree = wx.BoxSizer(wx.VERTICAL)
        sizer_tree.Add(self.button_multi_var_reg_model, 0, wx.EXPAND, 5)
        sizer_tree.Add(self.tree_ctrl, 1, wx.EXPAND, 0)
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
        sizer_plot.Add(self.plot.layout)
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
            initial_index_x = self.choices.index('ROI Max Dose')
            initial_index_y = self.choices.index('ROI Volume')
            self.spin_button_x_axis.SetValue(len(self.choices)-1-initial_index_x)
            self.spin_button_y_axis.SetValue(len(self.choices)-1-initial_index_y)
            self.combo_box_x_axis.SetValue(self.choices[initial_index_x])
            self.combo_box_y_axis.SetValue(self.choices[initial_index_y])
            self.update_plot()

    def on_combo_box(self, evt):
        self.sync_spin_buttons()
        self.update_plot()

    def update_plot(self):
        self.plot.update_plot(self.stats_data.get_bokeh_data(self.x_axis, self.y_axis),
                              self.combo_box_x_axis.GetValue(),
                              self.stats_data.get_axis_title(self.x_axis),
                              self.stats_data.get_axis_title(self.y_axis))

        if self.y_axis in list(self.y_variable_nodes) and self.x_axis in list(self.x_variable_nodes[self.y_axis]):
                self.checkbox.SetValue(True)
        else:
            self.checkbox.SetValue(False)

    def spin_x(self, evt):
        new_index = len(self.choices)-1 - int(self.spin_button_x_axis.GetValue())
        self.combo_box_x_axis.SetValue(self.choices[new_index])
        self.update_plot()

    def spin_y(self, evt):
        new_index = len(self.choices)-1 - int(self.spin_button_y_axis.GetValue())
        self.combo_box_y_axis.SetValue(self.choices[new_index])
        self.update_plot()

    def sync_spin_buttons(self):
        index = self.choices.index(self.x_axis)
        self.spin_button_x_axis.SetValue(len(self.choices)-1 - index)

        index = self.choices.index(self.y_axis)
        self.spin_button_y_axis.SetValue(len(self.choices)-1 - index)

    def on_checkbox(self, evt):
        y_value = self.combo_box_y_axis.GetValue()
        x_value = self.combo_box_x_axis.GetValue()

        if self.checkbox.GetValue():
            if y_value not in list(self.y_variable_nodes):
                self.y_variable_nodes[y_value] = self.tree_ctrl.AppendItem(self.tree_ctrl_root, "y_var: %s" % y_value)
                self.tree_ctrl.SetItemData(self.y_variable_nodes[y_value], None)
                self.tree_ctrl.SetItemImage(self.y_variable_nodes[y_value], self.images['y'], wx.TreeItemIcon_Normal)
            if y_value not in list(self.x_variable_nodes):
                self.x_variable_nodes[y_value] = {}
            if x_value not in self.x_variable_nodes[y_value]:
                self.x_variable_nodes[y_value][x_value] = self.tree_ctrl.AppendItem(self.y_variable_nodes[y_value], "x_var: %s" % x_value)
                self.tree_ctrl.SetItemData(self.x_variable_nodes[y_value][x_value], None)
                self.tree_ctrl.SetItemImage(self.x_variable_nodes[y_value][x_value], self.images['x'], wx.TreeItemIcon_Normal)
            self.tree_ctrl.ExpandAll()
        else:
            if y_value in list(self.y_variable_nodes):
                if x_value in list(self.x_variable_nodes[y_value]):
                    self.tree_ctrl.Delete(self.x_variable_nodes[y_value][x_value])
                    self.x_variable_nodes[y_value].pop(x_value)
                    if not list(self.x_variable_nodes[y_value]):
                        self.x_variable_nodes.pop(y_value)
                        self.tree_ctrl.Delete(self.y_variable_nodes[y_value])
                        self.y_variable_nodes.pop(y_value)

    def on_regression(self, evt):
        self.multi_variable_regression(self.combo_box_y_axis.GetValue())

    def multi_variable_regression(self, y_variable):

        x_variables = list(self.x_variable_nodes[y_variable])

        dlg = MultiVarResultsFrame(y_variable, x_variables, self.stats_data)
        dlg.Show()


    @staticmethod
    def get_p_values(X, y, predictions, params):
        # https://stackoverflow.com/questions/27928275/find-p-value-significance-in-scikit-learn-linearregression
        newX = np.append(np.ones((len(X),1)), X, axis=1)
        MSE = (sum((y-predictions)**2))/(len(newX)-len(newX[0]))

        var_b = MSE * (np.linalg.inv(np.dot(newX.T, newX)).diagonal())
        sd_b = np.sqrt(var_b)
        ts_b = params / sd_b

        return [2 * (1 - stats.t.cdf(np.abs(i), (len(newX) - 1))) for i in ts_b], sd_b, ts_b


class MultiVarResultsFrame(wx.Frame):
    def __init__(self, y_variable, x_variables, stats_data, *args, **kw):
        wx.Frame.__init__(self, None, title="Multi-Variable Model for %s" % y_variable)

        self.plot = PlotMultiVarRegression(self)
        self.plot.update_plot(y_variable, x_variables, stats_data)

        algorithms = ['Random Forest', 'Support Vector Machines', 'Decision Trees', 'Gradient Boosted']
        self.button = {key: wx.Button(self, wx.ID_ANY, key) for key in algorithms}

        self.__do_bind()
        self.__do_subscribe()
        self.__do_layout()

    def __do_bind(self):
        self.Bind(wx.EVT_BUTTON, self.on_random_forest, id=self.button['Random Forest'].GetId())

    def __do_subscribe(self):
        pub.subscribe(self.show_plot, "random_forest_complete")

    def __do_layout(self):

        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_wrapper.Add(self.plot.layout, 0, wx.EXPAND | wx.ALL, 5)

        sizer_algo_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_algo_select = wx.BoxSizer(wx.HORIZONTAL)
        text = wx.StaticText(self, wx.ID_ANY, "Compare with Machine Learning Module")
        sizer_algo_wrapper.Add(text, 0, wx.EXPAND | wx.ALL | wx.ALIGN_CENTER, 5)
        for key, button in self.button.items():
            sizer_algo_select.Add(button, 0, wx.EXPAND | wx.ALL, 5)
        sizer_algo_wrapper.Add(sizer_algo_select, 0, wx.ALL, 5)

        sizer_wrapper.Add(sizer_algo_wrapper, 0, wx.EXPAND | wx.ALL | wx.ALIGN_CENTER, 10)

        self.SetSizer(sizer_wrapper)
        sizer_wrapper.Fit(self)
        self.Layout()
        self.Center()

    def on_random_forest(self, evt):
        RandomForestWorker(self.plot.X, self.plot.y)

    def show_plot(self, msg):
        frame = RandomForestFrame(self.plot.y, msg['y_predict'], msg['mse'])
        frame.Show()
