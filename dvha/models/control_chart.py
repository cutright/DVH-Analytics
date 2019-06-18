import wx
from models.plot import PlotControlChart
from db import sql_columns
from dialogs.export import save_string_to_file


class ControlChartFrame:
    def __init__(self, parent, dvh, stats_data, options):
        self.parent = parent
        self.dvhs = dvh
        self.stats_data = stats_data
        self.choices = []

        self.y_axis_options = sql_columns.numerical

        self.combo_box_y_axis = wx.ComboBox(self.parent, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        self.combo_box_model = wx.ComboBox(self.parent, wx.ID_ANY, choices=[], style=wx.CB_DROPDOWN)
        # self.button_update_plot = wx.Button(self.parent, wx.ID_ANY, "Update Plot")
        self.button_export = wx.Button(self.parent, wx.ID_ANY, "Export")
        self.button_save_plot = wx.Button(self.parent, wx.ID_ANY, "Save Plot")
        self.plot = PlotControlChart(self.parent, options)

        self.__set_properties()
        self.__do_bind()
        self.__do_layout()
        # end wxGlade

    def __do_bind(self):
        self.parent.Bind(wx.EVT_COMBOBOX, self.on_combo_box_y, id=self.combo_box_y_axis.GetId())
        # self.parent.Bind(wx.EVT_BUTTON, self.update_plot_ticker, id=self.button_update_plot.GetId())
        self.parent.Bind(wx.EVT_BUTTON, self.on_save_plot, id=self.button_save_plot.GetId())
        self.parent.Bind(wx.EVT_BUTTON, self.export_csv, id=self.button_export.GetId())

    def __set_properties(self):
        pass

    def __do_layout(self):

        # begin wxGlade: MyFrame.__do_layout
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_plot = wx.BoxSizer(wx.HORIZONTAL)
        sizer_widgets = wx.StaticBoxSizer(wx.StaticBox(self.parent, wx.ID_ANY, ""), wx.HORIZONTAL)
        sizer_lookback_units = wx.BoxSizer(wx.VERTICAL)
        sizer_y_axis = wx.BoxSizer(wx.VERTICAL)
        label_y_axis = wx.StaticText(self.parent, wx.ID_ANY, "Charting Variable:")
        sizer_y_axis.Add(label_y_axis, 0, wx.LEFT, 5)
        sizer_y_axis.Add(self.combo_box_y_axis, 0, wx.ALL | wx.EXPAND, 5)
        sizer_widgets.Add(sizer_y_axis, 1, wx.EXPAND, 0)
        label_lookback_units = wx.StaticText(self.parent, wx.ID_ANY, "Adjustment Model:")
        sizer_lookback_units.Add(label_lookback_units, 0, wx.LEFT, 5)
        sizer_lookback_units.Add(self.combo_box_model, 0, wx.ALL | wx.EXPAND, 5)
        sizer_widgets.Add(sizer_lookback_units, 1, wx.EXPAND, 0)
        sizer_widgets.Add(self.button_export, 0, wx.ALL | wx.EXPAND, 5)
        sizer_widgets.Add(self.button_save_plot, 0, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper.Add(sizer_widgets, 0, wx.ALL | wx.EXPAND, 5)
        sizer_plot.Add(self.plot.layout, 1, wx.EXPAND, 5)
        sizer_wrapper.Add(sizer_plot, 1, wx.EXPAND, 0)

        self.layout = sizer_wrapper

    def update_combo_box_choices(self):
        if self.stats_data:
            self.choices = self.stats_data.control_chart_variables
            self.choices.sort()
            self.combo_box_y_axis.SetItems(self.choices)
            self.combo_box_y_axis.SetValue('ROI Volume')

    def on_combo_box_y(self, evt):
        self.update_plot()

    def update_plot_ticker(self, evt):
        self.update_plot()

    def update_plot(self):

        y_axis_selection = self.combo_box_y_axis.GetValue()

        dates = self.stats_data.sim_study_dates
        y_data = self.stats_data.data[y_axis_selection]['values']
        mrn_data = self.stats_data.mrns
        uid_data = self.stats_data.uids

        sort_index = sorted(range(len(dates)), key=lambda k: dates[k])
        dates_sorted, y_values_sorted, mrn_sorted, uid_sorted = [], [], [], []

        for s in range(len(dates)):
            dates_sorted.append(dates[sort_index[s]])
            y_values_sorted.append(y_data[sort_index[s]])
            mrn_sorted.append(mrn_data[sort_index[s]])
            uid_sorted.append(uid_data[sort_index[s]])

        x = list(range(1, len(dates)+1))

        self.plot.update_plot(x, y_values_sorted, mrn_sorted, uid_sorted, dates_sorted, y_axis_label=y_axis_selection)

    def update_data(self, dvh, stats_data):
        self.dvhs = dvh
        self.stats_data = stats_data
        try:
            self.update_plot()
        except KeyError:
            # TODO: Print error in GUI
            pass

    @property
    def variables(self):
        return list(self.stats_data)

    def update_endpoints_and_radbio(self):
        if self.dvhs:
            if self.dvhs.endpoints['defs']:
                for var in self.dvhs.endpoints['defs']['label']:
                    if var not in self.variables:
                        self.stats_data[var] = {'units': '',
                                          'values': self.dvhs.endpoints['data'][var]}

                for var in self.variables:
                    if var[0:2] in {'D_', 'V_'}:
                        if var not in self.dvhs.endpoints['defs']['label']:
                            self.stats_data.pop(var)

            if self.dvhs.eud:
                self.stats_data['EUD'] = {'units': 'Gy',
                                    'values': self.dvhs.eud}
            if self.dvhs.ntcp_or_tcp:
                self.stats_data['NTCP or TCP'] = {'units': '',
                                            'values': self.dvhs.ntcp_or_tcp}

    def initialize_y_axis_options(self):
        for i in range(len(self.choices))[::-1]:
            c = self.choices[i]
            if c[0:2] in {'D_', 'V_'} or c in {'EUD', 'NTCP or TCP'}:
                self.choices.pop(i)
        self.choices.sort()
        self.combo_box_y_axis.SetItems(self.choices)
        self.combo_box_y_axis.SetValue('ROI Max Dose')

    def clear_data(self):
        pass

    def get_csv(self, selection=None):
        # TODO: Update to export specified variables
        return self.plot.get_csv()

    def export_csv(self, evt):
        save_string_to_file(self.parent, "Export control chart data to CSV", self.plot.get_csv())

    def on_save_plot(self, evt):
        save_string_to_file(self.parent, 'Save control chart', self.plot.html_str,
                            wildcard="HTML files (*.html)|*.html")

    @property
    def has_data(self):
        return self.combo_box_y_axis.IsEnabled()
