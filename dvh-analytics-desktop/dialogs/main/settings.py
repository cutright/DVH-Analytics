#!/usr/bin/env python3
# -*- coding: UTF-8 -*-


import wx
import matplotlib.colors as plot_colors
from options import Options
from os.path import isdir
from paths import IMPORT_SETTINGS_PATH, parse_settings_file


class UserSettings(wx.Dialog):
    def __init__(self, *args, **kw):
        wx.Dialog.__init__(self, None, title="User Settings")

        self.options = Options()

        colors = list(plot_colors.cnames)
        colors.sort()

        color_variables = self.get_option_choices('COLOR')
        size_variables = self.get_option_choices('SIZE')
        width_variables = self.get_option_choices('LINE_WIDTH')
        line_dash_variables = self.get_option_choices('LINE_DASH')
        alpha_variables = self.get_option_choices('ALPHA')

        line_style_options = ['solid', 'dashed', 'dotted', 'dotdash', 'dashdot']

        self.SetSize((500, 580))
        self.text_ctrl_inbox = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_DONTWRAP)
        self.button_inbox = wx.Button(self, wx.ID_ANY, u"…")
        self.text_ctrl_imported = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_DONTWRAP)
        self.button_imported = wx.Button(self, wx.ID_ANY, u"…")
        self.combo_box_colors_category = wx.ComboBox(self, wx.ID_ANY, choices=color_variables,
                                                     style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.combo_box_colors_selection = wx.ComboBox(self, wx.ID_ANY, choices=colors,
                                                      style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.combo_box_sizes_category = wx.ComboBox(self, wx.ID_ANY, choices=size_variables,
                                                    style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.spin_ctrl_sizes_input = wx.SpinCtrl(self, wx.ID_ANY, "0", min=6, max=20, style=wx.SP_ARROW_KEYS)
        self.combo_box_line_widths_category = wx.ComboBox(self, wx.ID_ANY, choices=width_variables,
                                                          style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.spin_ctrl_line_widths_input = wx.SpinCtrl(self, wx.ID_ANY, "0", min=1, max=5, style=wx.SP_ARROW_KEYS)
        self.combo_box_line_styles_category = wx.ComboBox(self, wx.ID_ANY, choices=line_dash_variables,
                                                          style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.combo_box_line_styles_selection = wx.ComboBox(self, wx.ID_ANY, choices=line_style_options,
                                                           style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.combo_box_alpha_category = wx.ComboBox(self, wx.ID_ANY, choices=alpha_variables,
                                                    style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.spin_ctrl_alpha_input = wx.SpinCtrlDouble(self, wx.ID_ANY, "0", min=0.1, max=1.0, style=wx.SP_ARROW_KEYS)
        self.button_ok = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()
        self.__do_bind()

        self.load_options()
        self.load_paths()

        self.Center()

    def __set_properties(self):
        self.text_ctrl_inbox.SetToolTip("Default directory for batch processing of incoming DICOM files")
        self.text_ctrl_inbox.SetMinSize((100, 21))
        self.button_inbox.SetMinSize((40, 21))
        self.text_ctrl_imported.SetToolTip("Directory for post-processed DICOM files")
        self.text_ctrl_imported.SetMinSize((100, 21))
        self.button_imported.SetMinSize((40, 21))
        self.combo_box_colors_category.SetMinSize((250, 25))
        self.combo_box_colors_selection.SetMinSize((145, 25))
        self.combo_box_sizes_category.SetMinSize((250, 25))
        self.spin_ctrl_sizes_input.SetMinSize((50, 22))
        self.combo_box_line_widths_category.SetMinSize((250, 25))
        self.spin_ctrl_line_widths_input.SetMinSize((50, 22))
        self.combo_box_line_styles_category.SetMinSize((250, 25))
        self.combo_box_line_styles_selection.SetMinSize((145, 25))
        self.combo_box_alpha_category.SetMinSize((250, 25))
        self.spin_ctrl_alpha_input.SetMinSize((50, 22))

        self.spin_ctrl_alpha_input.SetIncrement(0.1)

        # Windows needs this done explicitly or the value will be an empty string
        self.combo_box_alpha_category.SetSelection(0)
        self.combo_box_colors_category.SetSelection(0)
        self.combo_box_line_styles_category.SetSelection(0)
        self.combo_box_line_widths_category.SetSelection(0)
        self.combo_box_sizes_category.SetSelection(0)

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_plot_options = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Plot Options"), wx.VERTICAL)
        sizer_alpha = wx.BoxSizer(wx.VERTICAL)
        sizer_alpha_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_line_styles = wx.BoxSizer(wx.VERTICAL)
        sizer_line_styles_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_line_widths = wx.BoxSizer(wx.VERTICAL)
        sizer_line_widths_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_sizes = wx.BoxSizer(wx.VERTICAL)
        sizer_sizes_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_colors = wx.BoxSizer(wx.VERTICAL)
        sizer_colors_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_dicom_directories = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "DICOM Directories"), wx.VERTICAL)
        sizer_imported_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_imported = wx.BoxSizer(wx.VERTICAL)
        sizer_imported_input = wx.BoxSizer(wx.HORIZONTAL)
        sizer_inbox_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_inbox = wx.BoxSizer(wx.VERTICAL)
        sizer_inbox_input = wx.BoxSizer(wx.HORIZONTAL)
        label_inbox = wx.StaticText(self, wx.ID_ANY, "Inbox:")
        label_inbox.SetToolTip("Default directory for batch processing of incoming DICOM files")
        sizer_inbox.Add(label_inbox, 0, 0, 5)
        sizer_inbox_input.Add(self.text_ctrl_inbox, 1, wx.ALL, 5)
        sizer_inbox_input.Add(self.button_inbox, 0, wx.ALL, 5)
        sizer_inbox.Add(sizer_inbox_input, 1, wx.EXPAND, 0)
        sizer_inbox_wrapper.Add(sizer_inbox, 1, wx.EXPAND, 0)
        sizer_dicom_directories.Add(sizer_inbox_wrapper, 1, wx.EXPAND, 0)
        label_imported = wx.StaticText(self, wx.ID_ANY, "Imported:")
        label_imported.SetToolTip("Directory for post-processed DICOM files")
        sizer_imported.Add(label_imported, 0, 0, 5)
        sizer_imported_input.Add(self.text_ctrl_imported, 1, wx.ALL, 5)
        sizer_imported_input.Add(self.button_imported, 0, wx.ALL, 5)
        sizer_imported.Add(sizer_imported_input, 1, wx.EXPAND, 0)
        sizer_imported_wrapper.Add(sizer_imported, 1, wx.EXPAND, 0)
        sizer_dicom_directories.Add(sizer_imported_wrapper, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_dicom_directories, 0, wx.ALL | wx.EXPAND, 10)
        label_colors = wx.StaticText(self, wx.ID_ANY, "Colors:")
        sizer_colors.Add(label_colors, 0, 0, 0)
        sizer_colors_input.Add(self.combo_box_colors_category, 0, 0, 0)
        sizer_colors_input.Add((20, 20), 0, 0, 0)
        sizer_colors_input.Add(self.combo_box_colors_selection, 0, 0, 0)
        sizer_colors.Add(sizer_colors_input, 1, wx.EXPAND, 0)
        sizer_plot_options.Add(sizer_colors, 1, wx.EXPAND, 0)
        label_sizes = wx.StaticText(self, wx.ID_ANY, "Sizes:")
        sizer_sizes.Add(label_sizes, 0, 0, 0)
        sizer_sizes_input.Add(self.combo_box_sizes_category, 0, 0, 0)
        sizer_sizes_input.Add((20, 20), 0, 0, 0)
        sizer_sizes_input.Add(self.spin_ctrl_sizes_input, 0, 0, 0)
        sizer_sizes.Add(sizer_sizes_input, 1, wx.EXPAND, 0)
        sizer_plot_options.Add(sizer_sizes, 1, wx.EXPAND, 0)
        label_line_widths = wx.StaticText(self, wx.ID_ANY, "Line Widths:")
        sizer_line_widths.Add(label_line_widths, 0, 0, 0)
        sizer_line_widths_input.Add(self.combo_box_line_widths_category, 0, 0, 0)
        sizer_line_widths_input.Add((20, 20), 0, 0, 0)
        sizer_line_widths_input.Add(self.spin_ctrl_line_widths_input, 0, 0, 0)
        sizer_line_widths.Add(sizer_line_widths_input, 1, wx.EXPAND, 0)
        sizer_plot_options.Add(sizer_line_widths, 1, wx.EXPAND, 0)
        label_line_styles = wx.StaticText(self, wx.ID_ANY, "Line Styles:")
        sizer_line_styles.Add(label_line_styles, 0, 0, 0)
        sizer_line_styles_input.Add(self.combo_box_line_styles_category, 0, 0, 0)
        sizer_line_styles_input.Add((20, 20), 0, 0, 0)
        sizer_line_styles_input.Add(self.combo_box_line_styles_selection, 0, 0, 0)
        sizer_line_styles.Add(sizer_line_styles_input, 1, wx.EXPAND, 0)
        sizer_plot_options.Add(sizer_line_styles, 1, wx.EXPAND, 0)
        label_alpha = wx.StaticText(self, wx.ID_ANY, "Alpha:")
        sizer_alpha.Add(label_alpha, 0, 0, 0)
        sizer_alpha_input.Add(self.combo_box_alpha_category, 0, 0, 0)
        sizer_alpha_input.Add((20, 20), 0, 0, 0)
        sizer_alpha_input.Add(self.spin_ctrl_alpha_input, 0, 0, 0)
        sizer_alpha.Add(sizer_alpha_input, 1, wx.EXPAND, 0)
        sizer_plot_options.Add(sizer_alpha, 1, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_plot_options, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
        sizer_ok_cancel.Add(self.button_ok, 0, wx.LEFT | wx.RIGHT, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.LEFT | wx.RIGHT, 5)
        sizer_wrapper.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.ALL, 10)
        self.SetSizer(sizer_wrapper)
        self.Layout()

    def __do_bind(self):
        self.Bind(wx.EVT_BUTTON, self.inbox_dir_dlg, id=self.button_inbox.GetId())
        self.Bind(wx.EVT_BUTTON, self.imported_dir_dlg, id=self.button_imported.GetId())

        self.Bind(wx.EVT_COMBOBOX, self.update_input_colors_var, id=self.combo_box_colors_category.GetId())
        self.Bind(wx.EVT_COMBOBOX, self.update_size_var, id=self.combo_box_sizes_category.GetId())
        self.Bind(wx.EVT_COMBOBOX, self.update_line_width_var, id=self.combo_box_line_widths_category.GetId())
        self.Bind(wx.EVT_COMBOBOX, self.update_line_style_var, id=self.combo_box_line_styles_category.GetId())
        self.Bind(wx.EVT_COMBOBOX, self.update_alpha_var, id=self.combo_box_alpha_category.GetId())

        self.Bind(wx.EVT_COMBOBOX, self.update_input_colors_val, id=self.combo_box_colors_selection.GetId())
        self.Bind(wx.EVT_TEXT, self.update_size_val, id=self.spin_ctrl_sizes_input.GetId())
        self.Bind(wx.EVT_TEXT, self.update_line_width_val, id=self.spin_ctrl_line_widths_input.GetId())
        self.Bind(wx.EVT_COMBOBOX, self.update_line_style_val, id=self.combo_box_line_styles_selection.GetId())
        self.Bind(wx.EVT_TEXT, self.update_alpha_val, id=self.spin_ctrl_alpha_input.GetId())

    def inbox_dir_dlg(self, evt):
        starting_dir = self.text_ctrl_inbox.GetValue()
        if not isdir(starting_dir):
            starting_dir = ""
        dlg = wx.DirDialog(self, "Select inbox directory", starting_dir, wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.text_ctrl_inbox.SetValue(dlg.GetPath())
        dlg.Destroy()

    def imported_dir_dlg(self, evt):
        starting_dir = self.text_ctrl_imported.GetValue()
        if not isdir(starting_dir):
            starting_dir = ""
        dlg = wx.DirDialog(self, "Select imported directory", starting_dir, wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.text_ctrl_imported.SetValue(dlg.GetPath())
        dlg.Destroy()

    def get_option_choices(self, category):
        choices = [self.clean_option_variable(c) for c in self.options.option_attr if c.find(category) > -1]
        choices.sort()
        return choices

    @staticmethod
    def clean_option_variable(option_variable, inverse=False):
        if inverse:
            return option_variable.upper().replace(' ', '_')
        else:
            return option_variable.replace('_', ' ').title().replace('Dvh', 'DVH').replace('Iqr', 'IQR')

    def save_options(self):
        self.options.save()

    def update_input_colors_var(self, evt):
        var = self.clean_option_variable(self.combo_box_colors_category.GetValue(), inverse=True)
        val = getattr(self.options, var)
        self.combo_box_colors_selection.SetValue(val)

    def update_input_colors_val(self, evt):
        var = self.clean_option_variable(self.combo_box_colors_category.GetValue(), inverse=True)
        val = self.combo_box_colors_selection.GetValue()
        self.options.set_option(var, val)

    def update_size_var(self, evt):
        var = self.clean_option_variable(self.combo_box_sizes_category.GetValue(), inverse=True)
        try:
            val = getattr(self.options, var).replace('pt', '')
        except AttributeError:
            val = str(getattr(self.options, var))
        try:
            val = int(float(val))
        except ValueError:
            pass
        self.spin_ctrl_sizes_input.SetValue(val)

    def update_size_val(self, evt):
        new = self.spin_ctrl_sizes_input.GetValue()
        if 'Font' in self.combo_box_sizes_category.GetValue():
            try:
                val = str(int(new)) + 'pt'
            except ValueError:
                val = '10pt'
        else:
            try:
                val = float(new)
            except ValueError:
                val = 1.

        var = self.clean_option_variable(self.combo_box_sizes_category.GetValue(), inverse=True)
        self.options.set_option(var, val)

    def update_line_width_var(self, evt):
        var = self.clean_option_variable(self.combo_box_line_widths_category.GetValue(), inverse=True)
        val = str(getattr(self.options, var))
        try:
            val = int(val)
        except ValueError:
            pass
        self.spin_ctrl_line_widths_input.SetValue(val)

    def update_line_width_val(self, evt):
        new = self.spin_ctrl_line_widths_input.GetValue()
        try:
            val = float(new)
        except ValueError:
            val = 1.
        var = self.clean_option_variable(self.combo_box_line_widths_category.GetValue(), inverse=True)
        self.options.set_option(var, val)

    def update_line_style_var(self, evt):
        var = self.clean_option_variable(self.combo_box_line_styles_category.GetValue(), inverse=True)
        self.combo_box_line_styles_selection.SetValue(getattr(self.options, var))

    def update_line_style_val(self, evt):
        var = self.clean_option_variable(self.combo_box_line_styles_category.GetValue(), inverse=True)
        val = self.combo_box_line_styles_selection.GetValue()
        self.options.set_option(var, val)

    def update_alpha_var(self, evt):
        var = self.clean_option_variable(self.combo_box_alpha_category.GetValue(), inverse=True)
        self.spin_ctrl_alpha_input.SetValue(str(getattr(self.options, var)))

    def update_alpha_val(self, evt):
        new = self.spin_ctrl_alpha_input.GetValue()
        try:
            val = float(new)
        except ValueError:
            val = 1.
        var = self.clean_option_variable(self.combo_box_alpha_category.GetValue(), inverse=True)
        self.options.set_option(var, val)

    def load_options(self):
        self.update_alpha_var(None)
        self.update_input_colors_var(None)
        self.update_line_style_var(None)
        self.update_line_width_var(None)
        self.update_size_var(None)

    def load_paths(self):
        paths = parse_settings_file(IMPORT_SETTINGS_PATH)
        self.text_ctrl_inbox.SetValue(paths['inbox'])
        self.text_ctrl_imported.SetValue(paths['imported'])
