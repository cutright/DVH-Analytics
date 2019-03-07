import wx
from categories import Categories
from db.sql_connector import DVH_SQL


class QueryCategoryDialog(wx.Dialog):

    def __init__(self, *args, **kw):
        wx.Dialog.__init__(self, None, title=kw['title'])

        categories = Categories()
        self.selector_categories = categories.selector

        selector_options = list(self.selector_categories)
        selector_options.sort()

        self.combo_box_1 = wx.ComboBox(self, wx.ID_ANY, choices=selector_options, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.combo_box_2 = wx.ComboBox(self, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.checkbox_1 = wx.CheckBox(self, wx.ID_ANY, "Not")
        self.button_OK = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()

        self.combo_box_1.SetValue('ROI Institutional Category')
        self.update_category_2(None)
        self.Bind(wx.EVT_COMBOBOX, self.update_category_2, id=self.combo_box_1.GetId())

        self.SetSize((500, 160))
        self.Center()

    def __set_properties(self):
        # begin wxGlade: MyFrame.__set_properties
        self.SetTitle("Query by Categorical Data")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_vbox = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_widgets = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.HORIZONTAL)
        sizer_category_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_category_1 = wx.BoxSizer(wx.VERTICAL)
        label_category_1 = wx.StaticText(self, wx.ID_ANY, "Category 1:")
        sizer_category_1.Add(label_category_1, 0, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)
        sizer_category_1.Add(self.combo_box_1, 0, wx.ALL, 5)
        sizer_widgets.Add(sizer_category_1, 1, wx.EXPAND, 0)
        label_category_2 = wx.StaticText(self, wx.ID_ANY, "Category 2:")
        sizer_category_2.Add(label_category_2, 0, wx.ALIGN_CENTER | wx.ALL | wx.EXPAND, 5)
        sizer_category_2.Add(self.combo_box_2, 0, wx.EXPAND | wx.ALL, 5)
        sizer_widgets.Add(sizer_category_2, 1, wx.EXPAND, 0)
        sizer_widgets.Add(self.checkbox_1, 0, wx.ALL | wx.EXPAND, 5)
        sizer_vbox.Add(sizer_widgets, 0, wx.ALL | wx.EXPAND, 5)
        sizer_ok_cancel.Add(self.button_OK, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.LEFT | wx.RIGHT, 5)
        sizer_vbox.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer_wrapper.Add(sizer_vbox, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer_wrapper)

    def update_category_2(self, evt):
        cnx = DVH_SQL()
        key = self.combo_box_1.GetValue()
        table = self.selector_categories[key]['table']
        col = self.selector_categories[key]['var_name']
        options = cnx.get_unique_values(table, col)
        self.combo_box_2.Clear()
        self.combo_box_2.Clear()
        self.combo_box_2.Append(options)
        if options:
            self.combo_box_2.SetValue(options[0])
        cnx.close()

    def set_category_1(self, value):
        self.combo_box_1.SetValue(value)
        self.update_category_2(None)

    def set_category_2(self, value):
        self.combo_box_2.SetValue(value)

    def set_check_box_not(self, value):
        self.checkbox_1.SetValue(value)

    def set_values(self, values):
        self.set_category_1(values[0])
        self.set_category_2(values[1])
        self.set_check_box_not(bool(values[2]))

    def get_values(self):
        return [self.combo_box_1.GetValue(),
                self.combo_box_2.GetValue(),
                self.checkbox_1.GetValue()]


class QueryRangeDialog(wx.Dialog):

    def __init__(self, *args, **kw):
        wx.Dialog.__init__(self, None, title="Add Range Filter")

        categories = Categories()
        self.range_categories = categories.range

        selector_options = list(self.range_categories)
        selector_options.sort()

        self.combo_box_1 = wx.ComboBox(self, wx.ID_ANY, choices=selector_options, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.text_ctrl_min = wx.TextCtrl(self, wx.ID_ANY, "")
        self.text_ctrl_max = wx.TextCtrl(self, wx.ID_ANY, "")
        self.checkbox_1 = wx.CheckBox(self, wx.ID_ANY, "Not")
        self.button_OK = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.combo_box_1.SetValue("ROI Max Dose")
        self.update_range(None)

        self.Bind(wx.EVT_COMBOBOX, self.update_range, id=self.combo_box_1.GetId())

        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        # begin wxGlade: MyFrame.__set_properties
        self.SetTitle("Query by Numerical Data")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_vbox = wx.BoxSizer(wx.VERTICAL)
        sizer_ok_cancel = wx.BoxSizer(wx.HORIZONTAL)
        sizer_widgets = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.HORIZONTAL)
        sizer_max = wx.BoxSizer(wx.VERTICAL)
        sizer_min = wx.BoxSizer(wx.VERTICAL)
        sizer_category_1 = wx.BoxSizer(wx.VERTICAL)
        label_category = wx.StaticText(self, wx.ID_ANY, "Category:")
        sizer_category_1.Add(label_category, 0, wx.ALL | wx.EXPAND, 5)
        sizer_category_1.Add(self.combo_box_1, 0, wx.ALL, 5)
        sizer_widgets.Add(sizer_category_1, 1, wx.EXPAND, 0)
        label_min = wx.StaticText(self, wx.ID_ANY, "Min:")
        sizer_min.Add(label_min, 0, wx.ALL | wx.EXPAND, 5)
        sizer_min.Add(self.text_ctrl_min, 0, wx.ALL, 5)
        sizer_widgets.Add(sizer_min, 0, wx.EXPAND, 0)
        label_max = wx.StaticText(self, wx.ID_ANY, "Max:")
        sizer_max.Add(label_max, 0, wx.ALL | wx.EXPAND, 5)
        sizer_max.Add(self.text_ctrl_max, 0, wx.ALL, 5)
        sizer_widgets.Add(sizer_max, 0, wx.EXPAND, 0)
        sizer_widgets.Add(self.checkbox_1, 0, wx.ALL | wx.EXPAND, 5)
        sizer_vbox.Add(sizer_widgets, 0, wx.ALL | wx.EXPAND, 5)
        sizer_ok_cancel.Add(self.button_OK, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_ok_cancel.Add(self.button_cancel, 0, wx.LEFT | wx.RIGHT, 5)
        sizer_vbox.Add(sizer_ok_cancel, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer_wrapper.Add(sizer_vbox, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer_wrapper)

        self.SetSize((500, 160))
        self.Center()

    def update_range(self, evt):
        cnx = DVH_SQL()
        key = self.combo_box_1.GetValue()
        table = self.range_categories[key]['table']
        col = self.range_categories[key]['var_name']
        units = self.range_categories[key]['units']
        min_value = cnx.get_min_value(table, col)
        max_value = cnx.get_max_value(table, col)
        cnx.close()

        if units:
            self.text_ctrl_min.SetLabelText('Min (%s):' % units)
            self.text_ctrl_max.SetLabelText('Max (%s):' % units)
        else:
            self.text_ctrl_min.SetLabelText('Min:')
            self.text_ctrl_max.SetLabelText('Max:')
        self.set_min_value(min_value)
        self.set_max_value(max_value)

    def set_category(self, value):
        self.combo_box_1.SetValue(value)
        self.update_range(None)

    def set_min_value(self, value):
        self.text_ctrl_min.SetValue(str(value))

    def set_max_value(self, value):
        self.text_ctrl_max.SetValue(str(value))

    def set_check_box_not(self, value):
        self.checkbox_1.SetValue(value)

    def set_values(self, values):
        self.set_category(values[0])
        self.set_min_value(str(values[1]))
        self.set_max_value(str(values[2]))
        self.set_check_box_not(bool(values[3]))

    def get_values(self):
        return [self.combo_box_1.GetValue(),
                self.text_ctrl_min.GetValue(),
                self.text_ctrl_max.GetValue(),
                self.checkbox_1.GetValue()]

    def validated_text(self, input_type):
        old_value = {'min': self.text_ctrl_min.GetValue(), 'max': self.text_ctrl_max.GetValue()}[input_type]

        try:
            new_value = float(old_value)
        except ValueError:
            cnx = DVH_SQL()
            key = self.combo_box_1.GetValue()
            table = self.range_categories[key]['table']
            col = self.range_categories[key]['var_name']
            if input_type == 'min':
                new_value = cnx.get_min_value(table, col)
            else:
                new_value = cnx.get_max_value(table, col)
            cnx.close()
        return new_value
