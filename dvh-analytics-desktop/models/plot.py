import wx.html2
from bokeh.plotting import figure
from bokeh.io.export import get_layout_html
from bokeh.models import Legend, HoverTool, ColumnDataSource, DataTable, TableColumn, NumberFormatter, Div
from bokeh.layouts import column, row
from bokeh.palettes import Colorblind8 as palette
import itertools
import numpy as np
from tools.utilities import collapse_into_single_dates, moving_avg, is_windows
from tools.stats import multi_variable_regression, get_control_limits


# TODO: have all plot classes load options with a function that runs on update_plot to get latest options
class Plot:
    def __init__(self, parent, options, x_axis_label='X Axis', y_axis_label='Y Axis',
                 plot_width=800, plot_height=500, frame_size=(900, 900), x_axis_type='linear'):

        self.options = options

        self.layout = wx.html2.WebView.New(parent, size=frame_size)
        self.bokeh_layout = None

        self.figure = figure(plot_width=plot_width, plot_height=plot_height, x_axis_type=x_axis_type)
        self.figure.xaxis.axis_label = x_axis_label
        self.figure.yaxis.axis_label = y_axis_label

        self.source = {}  # Will be a dictionary of bokeh ColumnDataSources

        self.__apply_default_figure_options()

    def __apply_default_figure_options(self):
        self.figure.xaxis.axis_label_text_font_size = self.options.PLOT_AXIS_LABEL_FONT_SIZE
        self.figure.yaxis.axis_label_text_font_size = self.options.PLOT_AXIS_LABEL_FONT_SIZE
        self.figure.xaxis.major_label_text_font_size = self.options.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE
        self.figure.yaxis.major_label_text_font_size = self.options.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE
        self.figure.min_border = self.options.MIN_BORDER
        self.figure.yaxis.axis_label_text_baseline = "bottom"

    def clear_plot(self):
        if self.bokeh_layout:
            self.clear_sources()
            self.figure.xaxis.axis_label = ''
            self.figure.yaxis.axis_label = ''
            self.update_bokeh_layout_in_wx_python()

    def clear_source(self, source_key):
        data = {data_key: [] for data_key in list(self.source[source_key].data)}
        self.source[source_key].data = data

    def clear_sources(self):
        for key in list(self.source):
            self.clear_source(key)

    def update_bokeh_layout_in_wx_python(self):
        html_str = get_layout_html(self.bokeh_layout)
        web_file = 'C:\\Users\\dcutright\\PycharmProjects\\DVH-Analytics-Desktop\\dvh-analytics-desktop\\test.html'
        with open(web_file, 'wb') as f:
            f.write(html_str.encode("utf-8"))
        # self.layout.SetPage(html_str, "")
        self.layout.LoadURL(web_file)

    @staticmethod
    def clean_data(*data, mrn=None, dates=None):
        bad_indices = []
        for var in data:
            bad_indices.extend([i for i, value in enumerate(var) if value == 'None'])
        bad_indices = list(set(bad_indices))

        ans = []
        for var in data:
            ans.append([value for i, value in enumerate(var) if i not in bad_indices])
        if mrn:
            ans.append([value for i, value in enumerate(mrn) if i not in bad_indices])
        if dates:
            ans.append([value for i, value in enumerate(dates) if i not in bad_indices])

        return tuple(ans)


class PlotStatDVH(Plot):
    def __init__(self, parent, dvh, options):
        Plot.__init__(self, parent, options, x_axis_label='Dose (cGy)', y_axis_label='Relative Volume',
                      plot_width=800, plot_height=400)

        self.options = options
        self.dvh = dvh
        self.source = {'dvh': ColumnDataSource(data=dict(x=[], y=[], mrn=[], roi_name=[], roi_type=[], rx_dose=[],
                                                         volume=[], min_dose=[], mean_dose=[], max_dose=[])),
                       'stats': ColumnDataSource(data=dict(x=[], min=[], mean=[], median=[], max=[], mrn=[])),
                       'patch': ColumnDataSource(data=dict(x=[], y=[]))}
        self.layout_done = False
        self.stat_dvhs = {key: np.array(0) for key in ['min', 'q1', 'mean', 'median', 'q3', 'max']}
        self.x = []

        self.__add_hover()
        self.__add_plot_data()
        self.__create_table()

        self.bokeh_layout = column(self.figure, self.table)

    def __add_hover(self):
        # Display only one tool tip (since many lines will overlap)
        # https://stackoverflow.com/questions/36434562/displaying-only-one-tooltip-when-using-the-hovertool-tool?rq=1
        custom_hover = HoverTool()
        custom_hover.tooltips = """
                    <style>
                        .bk-tooltip>div:not(:first-child) {display:none;}
                    </style>

                    <b>MRN: </b> @mrn <br>
                    <b>Dose: </b> $x{i} cGy <br>
                    <b>Volume: </b> $y
                """
        self.figure.add_tools(custom_hover)

    def __add_plot_data(self):
        self.figure.multi_line('x', 'y', source=self.source['dvh'], selection_color='color',
                               line_width=self.options.DVH_LINE_WIDTH,
                               alpha=0, line_dash=self.options.DVH_LINE_DASH, nonselection_alpha=0, selection_alpha=1)

        # Add statistical plots to figure
        self.stats_max = self.figure.line('x', 'max', source=self.source['stats'],
                                          line_width=self.options.STATS_MAX_LINE_WIDTH, color=self.options.PLOT_COLOR,
                                          line_dash=self.options.STATS_MAX_LINE_DASH, alpha=self.options.STATS_MAX_ALPHA)
        self.stats_median = self.figure.line('x', 'median', source=self.source['stats'],
                                             line_width=self.options.STATS_MEDIAN_LINE_WIDTH,
                                             color=self.options.PLOT_COLOR, line_dash=self.options.STATS_MEDIAN_LINE_DASH,
                                             alpha=self.options.STATS_MEDIAN_ALPHA)
        self.stats_mean = self.figure.line('x', 'mean', source=self.source['stats'],
                                           line_width=self.options.STATS_MEAN_LINE_WIDTH,
                                           color=self.options.PLOT_COLOR, line_dash=self.options.STATS_MEAN_LINE_DASH,
                                           alpha=self.options.STATS_MEAN_ALPHA)
        self.stats_min = self.figure.line('x', 'min', source=self.source['stats'],
                                          line_width=self.options.STATS_MIN_LINE_WIDTH, color=self.options.PLOT_COLOR,
                                          line_dash=self.options.STATS_MIN_LINE_DASH, alpha=self.options.STATS_MIN_ALPHA)

        # Shaded region between Q1 and Q3
        self.iqr = self.figure.patch('x', 'y', source=self.source['patch'], alpha=self.options.IQR_ALPHA,
                                     color=self.options.PLOT_COLOR)

    def __add_legend(self):
        # Set the legend (for stat dvhs only)
        legend_stats = Legend(items=[("Max  ", [self.stats_max]),
                                     ("Median  ", [self.stats_median]),
                                     ("Mean  ", [self.stats_mean]),
                                     ("Min  ", [self.stats_min]),
                                     ("IQR  ", [self.iqr])],
                              orientation='horizontal')

        # Add the layout outside the plot, clicking legend item hides the line
        self.figure.add_layout(legend_stats, 'above')
        self.figure.legend.click_policy = "hide"

    def __create_table(self):
        columns = [TableColumn(field="mrn", title="MRN", width=175),
                   TableColumn(field="roi_name", title="ROI Name"),
                   TableColumn(field="roi_type", title="ROI Type", width=80),
                   TableColumn(field="rx_dose", title="Rx Dose", width=100, formatter=NumberFormatter(format="0.00")),
                   TableColumn(field="volume", title="Volume", width=80, formatter=NumberFormatter(format="0.00")),
                   TableColumn(field="min_dose", title="Min Dose", width=80, formatter=NumberFormatter(format="0.00")),
                   TableColumn(field="mean_dose", title="Mean Dose", width=80,
                               formatter=NumberFormatter(format="0.00")),
                   TableColumn(field="max_dose", title="Max Dose", width=80,
                               formatter=NumberFormatter(format="0.00")), ]
        self.table = DataTable(source=self.source['dvh'], columns=columns, height=275, width=800)

    def update_plot(self, dvh):
        self.clear_sources()
        self.dvh = dvh
        self.x = list(range(dvh.bin_count))
        self.stat_dvhs = dvh.get_standard_stat_dvh()

        data = {'dvh': dvh.get_cds_data(),
                'stats': {key: self.stat_dvhs[key] for key in ['max', 'median', 'mean', 'min']},
                'patch': {'x': self.x + self.x[::-1],  # top + bottom in reverse
                          'y': self.stat_dvhs['q3'].tolist() + self.stat_dvhs['q1'][::-1].tolist()}}

        # Add additional data to dvh data
        data['dvh']['x'] = dvh.x_data
        data['dvh']['y'] = dvh.y_data
        data['dvh']['mrn'] = dvh.mrn
        data['dvh']['color'] = [color for j, color in zip(range(dvh.count), itertools.cycle(palette))]

        # Add x-axis to stats dvhs
        data['stats']['x'] = self.x

        # update bokeh CDS
        for key, obj in data.items():
            self.source[key].data = obj

        self.figure.xaxis.axis_label = 'Dose (cGy)'
        self.figure.yaxis.axis_label = 'Relative Volume'

        self.update_bokeh_layout_in_wx_python()


class PlotTimeSeries(Plot):
    def __init__(self, parent, options, plot_width=800):
        Plot.__init__(self, parent, options, x_axis_label='Simulation Date',
                      plot_width=plot_width, plot_height=325, x_axis_type='datetime')
        self.options = options
        self.source = {'plot': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'hist': ColumnDataSource(data=dict(x=[], top=[], width=[])),
                       'trend': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'bound': ColumnDataSource(data=dict(x=[], mrn=[], upper=[], avg=[], lower=[])),
                       'patch': ColumnDataSource(data=dict(x=[], y=[]))}
        self.plot_width = plot_width

        self.__add_plot_data()
        self.__add_histogram_data()
        self.__add_legend()
        self.__add_hover()
        self.__do_layout()

    def __add_plot_data(self):
        self.plot_data = self.figure.circle('x', 'y', source=self.source['plot'], size=self.options.TIME_SERIES_CIRCLE_SIZE,
                                            alpha=self.options.TIME_SERIES_CIRCLE_ALPHA, color=self.options.PLOT_COLOR)

        self.plot_trend = self.figure.line('x', 'y', color=self.options.PLOT_COLOR, source=self.source['trend'],
                                           line_width=self.options.TIME_SERIES_TREND_LINE_WIDTH,
                                           line_dash=self.options.TIME_SERIES_TREND_LINE_DASH)
        self.plot_avg = self.figure.line('x', 'avg', color=self.options.PLOT_COLOR, source=self.source['bound'],
                                         line_width=self.options.TIME_SERIES_AVG_LINE_WIDTH,
                                         line_dash=self.options.TIME_SERIES_AVG_LINE_DASH)
        self.plot_patch = self.figure.patch('x', 'y', color=self.options.PLOT_COLOR, source=self.source['patch'],
                                            alpha=self.options.TIME_SERIES_PATCH_ALPHA)

    def __add_histogram_data(self):
        tools = "pan,wheel_zoom,box_zoom,reset,crosshair,save"
        self.histogram = figure(plot_width=self.plot_width, plot_height=275, tools=tools, active_drag="box_zoom")
        self.histogram.xaxis.axis_label_text_font_size = self.options.PLOT_AXIS_LABEL_FONT_SIZE
        self.histogram.yaxis.axis_label_text_font_size = self.options.PLOT_AXIS_LABEL_FONT_SIZE
        self.histogram.xaxis.major_label_text_font_size = self.options.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE
        self.histogram.yaxis.major_label_text_font_size = self.options.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE
        self.histogram.min_border_left = self.options.MIN_BORDER
        self.histogram.min_border_bottom = self.options.MIN_BORDER
        self.vbar = self.histogram.vbar(x='x', width='width', bottom=0, top='top', source=self.source['hist'],
                                        color=self.options.PLOT_COLOR, alpha=self.options.HISTOGRAM_ALPHA)

        self.histogram.xaxis.axis_label = ""
        self.histogram.yaxis.axis_label = "Frequency"

    def __add_legend(self):
        # Set the legend
        legend_plot = Legend(items=[("Data  ", [self.plot_data]),
                                    ("Series Average  ", [self.plot_avg]),
                                    ("Rolling Average  ", [self.plot_trend]),
                                    ("Percentile Region  ", [self.plot_patch])],
                             orientation='horizontal')

        # Add the layout outside the plot, clicking legend item hides the line
        self.figure.add_layout(legend_plot, 'above')
        self.figure.legend.click_policy = "hide"

        self.histogram.add_tools(HoverTool(show_arrow=True, line_policy='next',
                                           tooltips=[('x', '@x{0.2f}'),
                                                     ('Counts', '@top')]))

    def __add_hover(self):
        self.figure.add_tools(HoverTool(show_arrow=True,
                                        tooltips=[('ID', '@mrn'),
                                                  ('Date', '@x{%F}'),
                                                  ('Value', '@y{0.2f}')],
                                        formatters={'x': 'datetime'}))

    def __do_layout(self):
        self.bokeh_layout = column(self.figure,
                                   Div(text='<hr>', width=self.plot_width),
                                   self.histogram)

    def update_plot(self, x, y, mrn, y_axis_label='Y Axis', avg_len=1, percentile=90., bin_size=10):
        self.clear_sources()
        self.figure.yaxis.axis_label = y_axis_label
        self.histogram.xaxis.axis_label = y_axis_label

        self.update_plot_data(x, y, mrn)
        self.update_histogram(bin_size=bin_size)
        self.update_trend(avg_len, percentile)

        self.update_bokeh_layout_in_wx_python()

    def update_plot_data(self, x, y, mrn):
        valid_indices = [i for i, value in enumerate(y) if value != 'None']
        self.source['plot'].data = {'x': [value for i, value in enumerate(x) if i in valid_indices],
                                    'y': [value for i, value in enumerate(y) if i in valid_indices],
                                    'mrn': [value for i, value in enumerate(mrn) if i in valid_indices]}

    def update_histogram(self, bin_size=10):
        width_fraction = 0.9
        hist, bins = np.histogram(self.source['plot'].data['y'], bins=bin_size)
        width = [width_fraction * (bins[1] - bins[0])] * bin_size
        center = (bins[:-1] + bins[1:]) / 2.
        self.source['hist'].data = {'x': center, 'top': hist, 'width': width}

    def update_trend(self, avg_len, percentile):

        x = self.source['plot'].data['x']
        y = self.source['plot'].data['y']
        if x and y:
            x_len = len(x)

            data_collapsed = collapse_into_single_dates(x, y)
            x_trend, y_trend = moving_avg(data_collapsed, avg_len)

            y_np = np.array(self.source['plot'].data['y'])
            upper_bound = float(np.percentile(y_np, 50. + percentile / 2.))
            average = float(np.percentile(y_np, 50))
            lower_bound = float(np.percentile(y_np, 50. - percentile / 2.))

            self.source['trend'].data = {'x': x_trend,
                                         'y': y_trend,
                                         'mrn': ['Avg'] * len(x_trend)}
            self.source['bound'].data = {'x': x,
                                         'mrn': ['Bound'] * x_len,
                                         'upper': [upper_bound] * x_len,
                                         'avg': [average] * x_len,
                                         'lower': [lower_bound] * x_len}
            self.source['patch'].data = {'x': [x[0], x[-1], x[-1], x[0]],
                                         'y': [upper_bound, upper_bound, lower_bound, lower_bound]}


class PlotRegression(Plot):
    def __init__(self, parent, options):
        Plot.__init__(self, parent, options, plot_width=550, plot_height=300)
        self.options = options
        self.source = {'plot': ColumnDataSource(data=dict(x=[], y=[], mrn=[], uid=[])),
                       'trend': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'residuals': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'residuals_zero': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'prob': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'prob_45': ColumnDataSource(data=dict(x=[], y=[])),
                       'table': ColumnDataSource(data=dict(var=[], coef=[], std_err=[], t_value=[], p_value=[],
                                                           spacer=[], fit_param=[]))}

        self.__create_additional_figures()
        self.__create_table()
        self.__add_plot_data()
        self.__add_hover()
        self.__do_layout()

    def __create_additional_figures(self):
        self.figure_residual_fits = figure(plot_width=275, plot_height=200)
        self.figure_residual_fits.xaxis.axis_label = 'Fitted Values'
        self.figure_residual_fits.yaxis.axis_label = 'Residuals'
        self.figure_prob_plot = figure(plot_width=275, plot_height=200)
        self.figure_prob_plot.xaxis.axis_label = 'Quantiles'
        self.figure_prob_plot.yaxis.axis_label = 'Ordered Values'

    def __create_table(self):
        columns = [TableColumn(field="var", title="", width=100),
                   TableColumn(field="coef", title="Coef", formatter=NumberFormatter(format="0.000"), width=50),
                   TableColumn(field="std_err", title="Std. Err.", formatter=NumberFormatter(format="0.000"), width=50),
                   TableColumn(field="t_value", title="t-value", formatter=NumberFormatter(format="0.000"), width=50),
                   TableColumn(field="p_value", title="p-value", formatter=NumberFormatter(format="0.000"), width=50),
                   TableColumn(field="spacer", title="", width=2),
                   TableColumn(field="fit_param", title="", width=75)]
        self.regression_table = DataTable(source=self.source['table'], columns=columns, width=500, height=100,
                                          index_position=None)

    def __add_plot_data(self):
        self.plot_data = self.figure.circle('x', 'y', source=self.source['plot'], size=self.options.REGRESSION_CIRCLE_SIZE,
                                            alpha=self.options.REGRESSION_ALPHA, color=self.options.PLOT_COLOR)
        self.plot_trend = self.figure.line('x', 'y', color=self.options.PLOT_COLOR, source=self.source['trend'],
                                           line_width=self.options.REGRESSION_LINE_WIDTH,
                                           line_dash=self.options.REGRESSION_LINE_DASH)
        self.plot_residuals = self.figure_residual_fits.circle('x', 'y', source=self.source['residuals'],
                                                               size=self.options.REGRESSION_RESIDUAL_CIRCLE_SIZE,
                                                               alpha=self.options.REGRESSION_RESIDUAL_ALPHA,
                                                               color=self.options.PLOT_COLOR)
        self.plot_residuals_zero = self.figure_residual_fits.line('x', 'y', source=self.source['residuals_zero'],
                                                                  line_width=self.options.REGRESSION_RESIDUAL_LINE_WIDTH,
                                                                  line_dash=self.options.REGRESSION_RESIDUAL_LINE_DASH,
                                                                  alpha=self.options.REGRESSION_RESIDUAL_ALPHA,
                                                                  color=self.options.REGRESSION_RESIDUAL_LINE_COLOR)
        self.plot_prob = self.figure_prob_plot.circle('x', 'y', source=self.source['prob'],
                                                      size=self.options.REGRESSION_RESIDUAL_CIRCLE_SIZE,
                                                      alpha=self.options.REGRESSION_RESIDUAL_ALPHA,
                                                      color=self.options.PLOT_COLOR)
        self.plot_prob_45 = self.figure_prob_plot.line('x', 'y', source=self.source['prob_45'],
                                                       line_width=self.options.REGRESSION_RESIDUAL_LINE_WIDTH,
                                                       line_dash=self.options.REGRESSION_RESIDUAL_LINE_DASH,
                                                       alpha=self.options.REGRESSION_RESIDUAL_ALPHA,
                                                       color=self.options.REGRESSION_RESIDUAL_LINE_COLOR)

    def __add_hover(self):
        self.figure.add_tools(HoverTool(show_arrow=True,
                                        tooltips=[('ID', '@mrn'),
                                                  ('x', '@x{0.2f}'),
                                                  ('y', '@y{0.2f}')]))

    def __do_layout(self):
        self.bokeh_layout = column(self.figure,
                                   self.regression_table,
                                   row(self.figure_residual_fits, self.figure_prob_plot))

    def update_plot(self, plot_data, x_var, x_axis_title, y_axis_title):
        self.clear_sources()
        self.source['plot'].data = plot_data
        self.update_trend(x_var)
        self.figure.xaxis.axis_label = x_axis_title
        self.figure.yaxis.axis_label = y_axis_title
        self.update_bokeh_layout_in_wx_python()

    def update_trend(self, x_var):
        x, y, mrn = self.clean_data(self.source['plot'].data['x'],
                                    self.source['plot'].data['y'],
                                    mrn=self.source['plot'].data['mrn'])

        data = np.array([y, x])
        clean_data = data[:, ~np.any(np.isnan(data), axis=0)]
        X = np.transpose(clean_data[1:])
        y = clean_data[0]

        reg = multi_variable_regression(X, y)

        x_trend = [min(x), max(x)]
        y_trend = np.add(np.multiply(x_trend, reg.slope), reg.y_intercept)

        self.source['residuals'].data = {'x': reg.predictions,
                                         'y': reg.residuals,
                                         'mrn': mrn}

        self.source['residuals_zero'].data = {'x': [min(reg.predictions), max(reg.predictions)],
                                              'y': [0, 0],
                                              'mrn': [None, None]}

        self.source['prob'].data = {'x': reg.norm_prob_plot[0],
                                    'y': reg.norm_prob_plot[1]}

        self.source['prob_45'].data = {'x': reg.x_trend_prob,
                                       'y': reg.y_trend_prob}

        self.source['table'].data = {'var': ['y-int', x_var],
                                     'coef': [reg.y_intercept, reg.slope],
                                     'std_err': reg.sd_b,
                                     't_value': reg.ts_b,
                                     'p_value': reg.p_values,
                                     'spacer': ['', ''],
                                     'fit_param': ["R²: %0.3f" % reg.r_sq, "MSE: %0.3f" % reg.mse]}

        self.source['trend'].data = {'x': x_trend,
                                     'y': y_trend,
                                     'mrn': ['Trend'] * 2}


class PlotMultiVarRegression(Plot):
    def __init__(self, parent, options):
        Plot.__init__(self, parent, options, plot_width=400, plot_height=400, frame_size=(900, 600))
        self.options = options
        self.X, self.y = None, None
        self.source = {'plot': ColumnDataSource(data=dict(x=[], y=[], mrn=[], uid=[])),
                       'trend': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'residuals': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'residuals_zero': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'prob': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'prob_45': ColumnDataSource(data=dict(x=[], y=[])),
                       'table': ColumnDataSource(data=dict(var=[], coef=[], std_err=[], t_value=[], p_value=[],
                                                           spacer=[], fit_param=[]))}

        self.__add_additional_figures()
        self.__add_plot_data()
        self.__create_table()
        self.__do_layout()

    def __add_additional_figures(self):
        self.figure_prob_plot = figure(plot_width=400, plot_height=400)
        self.figure_prob_plot.xaxis.axis_label = 'Quantiles'
        self.figure_prob_plot.yaxis.axis_label = 'Ordered Values'

    def __add_plot_data(self):
        self.plot_residuals = self.figure.circle('x', 'y', source=self.source['residuals'],
                                                 size=self.options.REGRESSION_RESIDUAL_CIRCLE_SIZE,
                                                 alpha=self.options.REGRESSION_RESIDUAL_ALPHA,
                                                 color=self.options.PLOT_COLOR)
        self.plot_residuals_zero = self.figure.line('x', 'y', source=self.source['residuals_zero'],
                                                    line_width=self.options.REGRESSION_RESIDUAL_LINE_WIDTH,
                                                    line_dash=self.options.REGRESSION_RESIDUAL_LINE_DASH,
                                                    alpha=self.options.REGRESSION_RESIDUAL_ALPHA,
                                                    color=self.options.REGRESSION_RESIDUAL_LINE_COLOR)
        self.plot_prob = self.figure_prob_plot.circle('x', 'y', source=self.source['prob'],
                                                      size=self.options.REGRESSION_RESIDUAL_CIRCLE_SIZE,
                                                      alpha=self.options.REGRESSION_RESIDUAL_ALPHA,
                                                      color=self.options.PLOT_COLOR)
        self.plot_prob_45 = self.figure_prob_plot.line('x', 'y', source=self.source['prob_45'],
                                                       line_width=self.options.REGRESSION_RESIDUAL_LINE_WIDTH,
                                                       line_dash=self.options.REGRESSION_RESIDUAL_LINE_DASH,
                                                       alpha=self.options.REGRESSION_RESIDUAL_ALPHA,
                                                       color=self.options.REGRESSION_RESIDUAL_LINE_COLOR)

    def __create_table(self):
        columns = [TableColumn(field="var", title="", width=100),
                   TableColumn(field="coef", title="Coef", formatter=NumberFormatter(format="0.000"), width=40),
                   TableColumn(field="std_err", title="Std. Err.", formatter=NumberFormatter(format="0.000"), width=40),
                   TableColumn(field="t_value", title="t-value", formatter=NumberFormatter(format="0.000"), width=40),
                   TableColumn(field="p_value", title="p-value", formatter=NumberFormatter(format="0.000"), width=40),
                   TableColumn(field="spacer", title="", width=5),
                   TableColumn(field="fit_param", title="", width=75)]
        self.regression_table = DataTable(source=self.source['table'], columns=columns, width=800, index_position=None)

    def __do_layout(self):
        self.bokeh_layout = column(row(self.figure_prob_plot, self.figure),
                                   self.regression_table)

    def update_plot(self, y_variable, x_variables, stats_data):
        self.clear_sources()
        x_len = len(x_variables)
        self.X, self.y = stats_data.get_X_and_y(y_variable, x_variables)
        reg = multi_variable_regression(self.X, self.y)

        self.source['residuals'].data = {'x': reg.predictions,
                                         'y': reg.residuals}

        self.source['residuals_zero'].data = {'x': [min(reg.predictions), max(reg.predictions)],
                                              'y': [0, 0],
                                              'mrn': [None, None]}

        self.source['prob'].data = {'x': reg.norm_prob_plot[0],
                                    'y': reg.norm_prob_plot[1]}

        self.source['prob_45'].data = {'x': reg.x_trend_prob,
                                       'y': reg.y_trend_prob}

        fit_param = [''] * (x_len + 1)
        fit_param[0] = "R²: %0.3f ----- MSE: %0.3f" % (reg.r_sq, reg.mse)
        fit_param[1] = "f stat: %0.3f ---- p value: %0.3f" % (reg.f_stat, reg.f_p_value)
        self.source['table'].data = {'var': ['y-int'] + x_variables,
                                     'coef': [reg.y_intercept] + reg.slope.tolist(),
                                     'std_err': reg.sd_b,
                                     't_value': reg.ts_b,
                                     'p_value': reg.p_values,
                                     'spacer': [''] * (x_len + 1),
                                     'fit_param': fit_param}

        self.figure.xaxis.axis_label = 'Fitted Values'
        self.figure.yaxis.axis_label = 'Residuals'

        self.update_bokeh_layout_in_wx_python()


class PlotControlChart(Plot):
    def __init__(self, parent, options, plot_width=800):
        Plot.__init__(self, parent, options, x_axis_label='Study', plot_width=plot_width, plot_height=325)
        self.options = options
        self.source = {'plot': ColumnDataSource(data=dict(x=[], y=[], mrn=[], color=[], alpha=[], dates=[])),
                       'center_line': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'ucl_line': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'lcl_line': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'bound': ColumnDataSource(data=dict(x=[], mrn=[], upper=[], avg=[], lower=[])),
                       'patch': ColumnDataSource(data=dict(x=[], y=[]))}

        self.__add_plot_data()
        self.__add_hover()
        self.__create_divs()
        self.__add_legend()
        self.__do_layout()

    def __add_plot_data(self):
        self.plot_data = self.figure.circle('x', 'y', source=self.source['plot'],
                                            size=self.options.CONTROL_CHART_CIRCLE_SIZE,
                                            alpha='alpha',
                                            color='color')
        self.plot_data_line = self.figure.line('x', 'y', source=self.source['plot'],
                                               line_width=self.options.CONTROL_CHART_LINE_WIDTH,
                                               color=self.options.CONTROL_CHART_LINE_COLOR,
                                               line_dash=self.options.CONTROL_CHART_LINE_DASH)
        self.plot_patch = self.figure.patch('x', 'y', color=self.options.PLOT_COLOR, source=self.source['patch'],
                                            alpha=self.options.CONTROL_CHART_PATCH_ALPHA)
        self.plot_center_line = self.figure.line('x', 'y', source=self.source['center_line'],
                                                 line_width=self.options.CONTROL_CHART_CENTER_LINE_WIDTH,
                                                 alpha=self.options.CONTROL_CHART_CENTER_LINE_ALPHA,
                                                 color=self.options.CONTROL_CHART_CENTER_LINE_COLOR,
                                                 line_dash=self.options.CONTROL_CHART_CENTER_LINE_DASH)
        self.plot_lcl_line = self.figure.line('x', 'y', source=self.source['lcl_line'],
                                              line_width=self.options.CONTROL_CHART_LCL_LINE_WIDTH,
                                              alpha=self.options.CONTROL_CHART_LCL_LINE_ALPHA,
                                              color=self.options.CONTROL_CHART_LCL_LINE_COLOR,
                                              line_dash=self.options.CONTROL_CHART_LCL_LINE_DASH)
        self.plot_ucl_line = self.figure.line('x', 'y', source=self.source['ucl_line'],
                                              line_width=self.options.CONTROL_CHART_UCL_LINE_WIDTH,
                                              alpha=self.options.CONTROL_CHART_UCL_LINE_ALPHA,
                                              color=self.options.CONTROL_CHART_UCL_LINE_COLOR,
                                              line_dash=self.options.CONTROL_CHART_UCL_LINE_DASH)

    def __add_hover(self):
        self.figure.add_tools(HoverTool(show_arrow=True,
                                        tooltips=[('ID', '@mrn'),
                                                  ('Date', '@dates{%F}'),
                                                  ('Study', '@x'),
                                                  ('Value', '@y{0.2f}')],
                                        formatters={'dates': 'datetime'}))

    def __add_legend(self):
        # Set the legend
        legend_plot = Legend(items=[("Charting Variable   ", [self.plot_data]),
                                    ("Charting Variable Line  ", [self.plot_data_line]),
                                    ('Center Line   ', [self.plot_center_line]),
                                    ('UCL  ', [self.plot_ucl_line]),
                                    ('LCL  ', [self.plot_lcl_line])],
                             orientation='horizontal')

        # Add the layout outside the plot, clicking legend item hides the line
        self.figure.add_layout(legend_plot, 'above')
        self.figure.legend.click_policy = "hide"

    def __create_divs(self):
        self.div_center_line = Div(text='', width=175)
        self.div_ucl = Div(text='', width=175)
        self.div_lcl = Div(text='', width=175)

    def __do_layout(self):
        self.bokeh_layout = column(self.figure,
                                   row(self.div_center_line, self.div_ucl, self.div_lcl))

    def update_plot(self, x, y, mrn, dates, y_axis_label='Y Axis'):
        self.clear_sources()
        self.figure.yaxis.axis_label = y_axis_label

        x, y, mrn, dates = self.clean_data(x, y, mrn=mrn, dates=dates)

        center_line, ucl, lcl = get_control_limits(y)

        colors = [self.options.CONTROL_CHART_OUT_OF_CONTROL_COLOR, self.options.PLOT_COLOR]
        alphas = [self.options.CONTROL_CHART_OUT_OF_CONTROL_ALPHA, self.options.CONTROL_CHART_CIRCLE_ALPHA]
        color = [colors[ucl > value > lcl] for value in y]
        alpha = [alphas[ucl > value > lcl] for value in y]

        self.source['plot'].data = {'x': x, 'y': y, 'mrn': mrn, 'color': color, 'alpha': alpha, 'dates': dates}

        self.source['patch'].data = {'x': [x[0], x[-1], x[-1], x[0]],
                                     'y': [ucl, ucl, lcl, lcl]}
        self.source['center_line'].data = {'x': [min(x), max(x)],
                                           'y': [center_line] * 2,
                                           'mrn': ['center line'] * 2}

        self.source['lcl_line'].data = {'x': [min(x), max(x)],
                                        'y': [lcl] * 2,
                                        'mrn': ['center line'] * 2}
        self.source['ucl_line'].data = {'x': [min(x), max(x)],
                                        'y': [ucl] * 2,
                                        'mrn': ['center line'] * 2}

        self.div_center_line.text = "<b>Center line</b>: %0.3f" % center_line
        self.div_ucl.text = "<b>UCL</b>: %0.3f" % ucl
        self.div_lcl.text = "<b>LCL</b>: %0.3f" % lcl

        self.update_bokeh_layout_in_wx_python()

    def clear_plot(self):
        self.clear_div()  # super class does not have these Div objects
        super().clear_plot()

    def clear_div(self):
        self.div_center_line.text = "<b>Center line</b>:"
        self.div_ucl.text = "<b>UCL</b>:"
        self.div_lcl.text = "<b>LCL</b>:"


class PlotRandomForest(Plot):
    def __init__(self, parent, options, y, y_predict, mse):
        Plot.__init__(self, parent, options, plot_width=400, plot_height=400, frame_size=(900, 600))
        self.options = options
        self.y = y
        self.y_predict = y_predict
        self.mse = mse
        self.x = list(range(1, len(self.y)+1))

        self.source = {'plot': ColumnDataSource(data=dict(x=self.x, y=self.y, y_predict=self.y_predict))}

        self.__add_plot_data()
        self.__do_layout()

        self.update_bokeh_layout_in_wx_python()

    def __add_plot_data(self):
        self.figure.circle('x', 'y', source=self.source['plot'], color='blue')
        self.figure.circle('x', 'y_predict', source=self.source['plot'], color='red')

    def __do_layout(self):
        self.bokeh_layout = column(self.figure)
