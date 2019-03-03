import wx
from categories import Categories
from models.widgets import Text, DropDown, TextInput
from db.sql_connector import DVH_SQL
from models.layout import row, column


class QueryCategoryDialog(wx.Dialog):

    def __init__(self, *args, **kw):
        wx.Dialog.__init__(self, None, title=kw['title'])

        self.title_selector = Text(self, value='Query by Categorical Data\t\t\t\t\t\t')

        categories = Categories()
        self.selector_categories = categories.selector

        selector_options = list(self.selector_categories)
        selector_options.sort()

        self.button_ok = wx.Button(self, label='OK', id=wx.ID_OK)
        self.button_close = wx.Button(self, label='Cancel', id=wx.ID_CANCEL)

        self.select_category_1 = DropDown(self, title='Category 1:', options=selector_options, id=13,
                                          value='ROI Institutional Category')
        self.select_category_2 = DropDown(self, title='Category 2:')
        self.update_category_2(None)

        self.Bind(wx.EVT_COMBOBOX, self.update_category_2, id=self.select_category_1.id)

        self.check_box_not = wx.CheckBox(self, label='Not')

        layout = column(row(self.title_selector, self.check_box_not),
                        row(self.select_category_1, self.select_category_2),
                        row(self.button_ok, self.button_close))

        self.SetSizer(layout)
        self.SetSize((500, 200))
        self.Center()

    def update_category_2(self, evt):
        cnx = DVH_SQL()
        key = self.select_category_1.get_value()
        table = self.selector_categories[key]['table']
        col = self.selector_categories[key]['var_name']
        options = cnx.get_unique_values(table, col)
        self.select_category_2.set_options(options)
        if options:
            self.select_category_2.set_value(options[0])
        cnx.close()

    def set_category_1(self, value):
        self.select_category_1.set_value(value)
        self.update_category_2(None)

    def set_category_2(self, value):
        self.select_category_2.set_value(value)

    def set_check_box_not(self, value):
        self.check_box_not.SetValue(value)

    def set_values(self, values):
        self.set_category_1(values[0])
        self.set_category_2(values[1])
        self.set_check_box_not(bool(values[2]))

    def get_values(self):
        return [self.select_category_1.get_value(),
                self.select_category_2.get_value(),
                self.check_box_not.GetValue()]


class QueryRangeDialog(wx.Dialog):

    def __init__(self, *args, **kw):
        wx.Dialog.__init__(self, None, title="Add Range Filter")

        self.title_selector = Text(self, value='Query by Numerical Data\t\t\t\t\t\t')

        categories = Categories()
        self.range_categories = categories.range

        selector_options = list(self.range_categories)
        selector_options.sort()

        self.button_ok = wx.Button(self, label='OK', id=wx.ID_OK)
        self.button_close = wx.Button(self, label='Cancel', id=wx.ID_CANCEL)

        self.select_category = DropDown(self, title='Category:', options=selector_options, id=14, value='Rx Dose')
        self.text_min = TextInput(self, title='Min', id=15)
        self.text_max = TextInput(self, title='Max')
        self.update_range(None)

        self.Bind(wx.EVT_COMBOBOX, self.update_range, id=self.select_category.id)

        self.check_box_not = wx.CheckBox(self, label='Not')

        layout = column(row(self.title_selector, self.check_box_not),
                        row(self.select_category, self.text_min, self.text_max),
                        row(self.button_ok, self.button_close))

        self.SetSizer(layout)
        self.SetSize((500, 200))
        self.Center()

    def update_range(self, evt):
        cnx = DVH_SQL()
        key = self.select_category.get_value()
        table = self.range_categories[key]['table']
        col = self.range_categories[key]['var_name']
        units = self.range_categories[key]['units']
        min_value = cnx.get_min_value(table, col)
        max_value = cnx.get_max_value(table, col)
        cnx.close()

        if units:
            self.text_min.set_title('Min (%s)' % units)
            self.text_max.set_title('Max (%s)' % units)
        else:
            self.text_min.set_title('Min')
            self.text_max.set_title('Max')
        self.set_min_value(min_value)
        self.set_max_value(max_value)

    def set_category(self, value):
        self.select_category.set_value(value)
        self.update_range(None)

    def set_min_value(self, value):
        self.text_min.set_value(value)

    def set_max_value(self, value):
        self.text_max.set_value(value)

    def set_check_box_not(self, value):
        self.check_box_not.SetValue(value)

    def set_values(self, values):
        self.set_category(values[0])
        self.set_min_value(values[1])
        self.set_max_value(values[2])
        self.set_check_box_not(bool(values[3]))

    def get_values(self):
        return [self.select_category.get_value(),
                self.text_min.get_value(),
                self.text_max.get_value(),
                self.check_box_not.GetValue()]

    def validated_text(self, input_type):
        old_value = {'min': self.text_min.get_value(), 'max': self.text_max.get_value()}[input_type]

        try:
            new_value = float(old_value)
        except ValueError:
            cnx = DVH_SQL()
            key = self.select_category.get_value()
            table = self.range_categories[key]['table']
            col = self.range_categories[key]['var_name']
            if input_type == 'min':
                new_value = cnx.get_min_value(table, col)
            else:
                new_value = cnx.get_max_value(table, col)
            cnx.close()
        return new_value
