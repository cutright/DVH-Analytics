from bokeh.plotting import figure
from bokeh.io.export import get_layout_html
from options import Options
from bokeh.models import Legend, HoverTool, ColumnDataSource, DataTable, TableColumn, NumberFormatter, Div
from bokeh.layouts import column, row
from bokeh.palettes import Colorblind8 as palette
import itertools
import wx
import wx.html2
import numpy as np
from tools.utilities import collapse_into_single_dates, moving_avg
from tools.stats import multi_variable_regression, get_control_limits


options = Options()


def get_base_plot(parent, x_axis_label='X Axis', y_axis_label='Y Axis', plot_width=800, plot_height=500,
                  frame_size=(900, 900), x_axis_type='linear'):

    wxlayout = wx.html2.WebView.New(parent, size=frame_size)

    fig = figure(plot_width=plot_width, plot_height=plot_height, x_axis_type=x_axis_type)
    fig.xaxis.axis_label = x_axis_label
    fig.yaxis.axis_label = y_axis_label

    apply_default_options(fig)

    return fig, wxlayout


def apply_default_options(fig):
    fig.xaxis.axis_label_text_font_size = options.PLOT_AXIS_LABEL_FONT_SIZE
    fig.yaxis.axis_label_text_font_size = options.PLOT_AXIS_LABEL_FONT_SIZE
    fig.xaxis.major_label_text_font_size = options.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE
    fig.yaxis.major_label_text_font_size = options.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE
    fig.min_border_bottom = options.MIN_BORDER
    fig.yaxis.axis_label_text_baseline = "bottom"


class PlotStatDVH:
    def __init__(self, parent, dvh):

        self.figure, self.layout = get_base_plot(parent, x_axis_label='Dose (cGy)', y_axis_label='Relative Volume',
                                                 plot_width=800, plot_height=400)

        self.source = ColumnDataSource(data=dict(x=[], y=[], mrn=[], roi_name=[], roi_type=[], rx_dose=[], volume=[],
                                                 min_dose=[], mean_dose=[], max_dose=[]))

        self.source_stats = ColumnDataSource(data=dict(x=[], min=[], mean=[], median=[], max=[]))
        self.source_patch = ColumnDataSource(data=dict(x=[], y=[]))
        self.layout_done = False
        self.dvh = dvh
        self.stat_dvhs = {key: np.array(0) for key in ['min', 'q1', 'mean', 'median', 'q3', 'max']}
        self.x = []

        # Display only one tool tip (since many lines will overlap)
        # https://stackoverflow.com/questions/36434562/displaying-only-one-tooltip-when-using-the-hovertool-tool?rq=1
        custom_hover = HoverTool()
        custom_hover.tooltips = """
            <style>
                .bk-tooltip>div:not(:first-child) {display:none;}
            </style>

            <b>Dose: </b> $x{i} cGy <br>
            <b>Volume: </b> $y
        """
        self.figure.add_tools(custom_hover)

        self.figure.multi_line('x', 'y', source=self.source, selection_color='color', line_width=options.DVH_LINE_WIDTH,
                               alpha=0, line_dash=options.DVH_LINE_DASH, nonselection_alpha=0, selection_alpha=1)

        # Add statistical plots to figure
        stats_max = self.figure.line('x', 'max', source=self.source_stats, line_width=options.STATS_MAX_LINE_WIDTH,
                                     color=options.PLOT_COLOR, line_dash=options.STATS_MAX_LINE_DASH,
                                     alpha=options.STATS_MAX_ALPHA)
        stats_median = self.figure.line('x', 'median', source=self.source_stats,
                                        line_width=options.STATS_MEDIAN_LINE_WIDTH,
                                        color=options.PLOT_COLOR, line_dash=options.STATS_MEDIAN_LINE_DASH,
                                        alpha=options.STATS_MEDIAN_ALPHA)
        stats_mean = self.figure.line('x', 'mean', source=self.source_stats, line_width=options.STATS_MEAN_LINE_WIDTH,
                                      color=options.PLOT_COLOR, line_dash=options.STATS_MEAN_LINE_DASH,
                                      alpha=options.STATS_MEAN_ALPHA)
        stats_min = self.figure.line('x', 'min', source=self.source_stats, line_width=options.STATS_MIN_LINE_WIDTH,
                                     color=options.PLOT_COLOR, line_dash=options.STATS_MIN_LINE_DASH,
                                     alpha=options.STATS_MIN_ALPHA)

        # Shaded region between Q1 and Q3
        iqr = self.figure.patch('x', 'y', source=self.source_patch, alpha=options.IQR_ALPHA, color=options.PLOT_COLOR)

        # Set the legend (for stat dvhs only)
        legend_stats = Legend(items=[("Max  ", [stats_max]),
                                     ("Median  ", [stats_median]),
                                     ("Mean  ", [stats_mean]),
                                     ("Min  ", [stats_min]),
                                     ("IQR  ", [iqr])],
                              orientation='horizontal')

        # Add the layout outside the plot, clicking legend item hides the line
        self.figure.add_layout(legend_stats, 'above')
        self.figure.legend.click_policy = "hide"

        # DataTable
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
        self.table = DataTable(source=self.source, columns=columns, height=275, width=800)

        self.bokeh_layout = column(self.figure, self.table)

    def update_plot(self, dvh):
        self.dvh = dvh
        data = dvh.get_cds_data()
        data['x'] = dvh.x_data
        data['y'] = dvh.y_data
        data['mrn'] = dvh.mrn
        colors = itertools.cycle(palette)
        data['color'] = [color for j, color in zip(range(dvh.count), colors)]
        self.source.data = data
        self.x = list(range(dvh.bin_count))

        self.stat_dvhs = dvh.get_standard_stat_dvh()
        stats_data = {key: self.stat_dvhs[key] for key in ['max', 'median', 'mean', 'min']}
        stats_data['x'] = self.x
        self.source_stats.data = stats_data

        self.source_patch.data = {'x': self.x + self.x[::-1],
                                  'y': self.stat_dvhs['q3'].tolist() + self.stat_dvhs['q1'][::-1].tolist()}

        html_str = get_layout_html(self.bokeh_layout)
        self.layout.SetPage(html_str, "")

    def clear_plot(self):
        self.source.data = {key: [] for key in ['x', 'y', 'mrn', 'color']}
        self.source_stats.data = {key: [] for key in ['x', 'max', 'median', 'mean', 'min']}
        self.source_patch.data = {key: [] for key in ['x', 'y']}
        html_str = get_layout_html(self.bokeh_layout)
        self.layout.SetPage(html_str, "")


class PlotTimeSeries:
    def __init__(self, parent, x=[], y=[], mrn=[]):

        plot_width = 800  # store of histograms and divider bar

        self.figure, self.layout = get_base_plot(parent, x_axis_label='Simulation Date',
                                                 plot_width=plot_width, plot_height=325, x_axis_type='datetime')

        self.source = {'plot': ColumnDataSource(data=dict(x=x, y=y, mrn=mrn)),
                       'hist': ColumnDataSource(data=dict(x=[], top=[], width=[])),
                       'trend': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'bound': ColumnDataSource(data=dict(x=[], mrn=[], upper=[], avg=[], lower=[])),
                       'patch': ColumnDataSource(data=dict(x=[], y=[]))}

        self.figure.add_tools(HoverTool(show_arrow=True,
                                        tooltips=[('ID', '@mrn'),
                                                  ('Date', '@x{%F}'),
                                                  ('Value', '@y{0.2f}')],
                                        formatters={'x': 'datetime'}))

        self.plot_data = self.figure.circle('x', 'y', source=self.source['plot'], size=options.TIME_SERIES_CIRCLE_SIZE,
                                            alpha=options.TIME_SERIES_CIRCLE_ALPHA, color=options.PLOT_COLOR)

        self.plot_trend = self.figure.line('x', 'y', color=options.PLOT_COLOR, source=self.source['trend'],
                                           line_width=options.TIME_SERIES_TREND_LINE_WIDTH,
                                           line_dash=options.TIME_SERIES_TREND_LINE_DASH)
        self.plot_avg = self.figure.line('x', 'avg', color=options.PLOT_COLOR, source=self.source['bound'],
                                         line_width=options.TIME_SERIES_AVG_LINE_WIDTH,
                                         line_dash=options.TIME_SERIES_AVG_LINE_DASH)
        self.plot_patch = self.figure.patch('x', 'y', color=options.PLOT_COLOR, source=self.source['patch'],
                                            alpha=options.TIME_SERIES_PATCH_ALPHA)
        self.figure.add_tools(HoverTool(show_arrow=True,
                                        tooltips=[('ID', '@mrn'),
                                                  ('Date', '@x{%F}'),
                                                  ('Value', '@y{0.2f}')],
                                        formatters={'x': 'datetime'}))

        # Set the legend
        legend_plot = Legend(items=[("Data  ", [self.plot_data]),
                                    ("Series Average  ", [self.plot_avg]),
                                    ("Rolling Average  ", [self.plot_trend]),
                                    ("Percentile Region  ", [self.plot_patch])],
                             orientation='horizontal')

        # Add the layout outside the plot, clicking legend item hides the line
        self.figure.add_layout(legend_plot, 'above')
        self.figure.legend.click_policy = "hide"

        tools = "pan,wheel_zoom,box_zoom,reset,crosshair,save"
        self.histograms = figure(plot_width=plot_width, plot_height=275, tools=tools, active_drag="box_zoom")
        self.histograms.xaxis.axis_label_text_font_size = options.PLOT_AXIS_LABEL_FONT_SIZE
        self.histograms.yaxis.axis_label_text_font_size = options.PLOT_AXIS_LABEL_FONT_SIZE
        self.histograms.xaxis.major_label_text_font_size = options.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE
        self.histograms.yaxis.major_label_text_font_size = options.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE
        self.histograms.min_border_left = options.MIN_BORDER
        self.histograms.min_border_bottom = options.MIN_BORDER
        self.vbar = self.histograms.vbar(x='x', width='width', bottom=0, top='top', source=self.source['hist'],
                                         color=options.PLOT_COLOR, alpha=options.HISTOGRAM_ALPHA)

        self.histograms.xaxis.axis_label = ""
        self.histograms.yaxis.axis_label = "Frequency"
        self.histograms.add_tools(HoverTool(show_arrow=True, line_policy='next',
                                            tooltips=[('x', '@x{0.2f}'),
                                                      ('Counts', '@top')]))

        self.bokeh_layout = column(self.figure, Div(text='<hr>', width=plot_width), self.histograms)

    def update_plot(self, x, y, mrn, y_axis_label='Y Axis', avg_len=1, percentile=90., bin_size=10):
        self.figure.yaxis.axis_label = y_axis_label
        self.histograms.xaxis.axis_label = y_axis_label
        valid_indices = [i for i, value in enumerate(y) if value != 'None']
        self.source['plot'].data = {'x': [value for i, value in enumerate(x) if i in valid_indices],
                                    'y': [value for i, value in enumerate(y) if i in valid_indices],
                                    'mrn': [value for i, value in enumerate(mrn) if i in valid_indices]}

        # histograms
        width_fraction = 0.9
        hist, bins = np.histogram(self.source['plot'].data['y'], bins=bin_size)
        width = [width_fraction * (bins[1] - bins[0])] * bin_size
        center = (bins[:-1] + bins[1:]) / 2.
        self.source['hist'].data = {'x': center, 'top': hist, 'width': width}

        if x:
            self.update_trend(avg_len, percentile)
        else:
            self.clear_additional_plot_sources()

        html_str = get_layout_html(self.bokeh_layout)
        self.layout.SetPage(html_str, "")

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
        else:
            self.source['trend'].data = {'x': [], 'y': [], 'mrn': []}
            self.source['bound'].data = {'x': [], 'mrn': [], 'upper': [], 'avg': [], 'lower': []}
            self.source['patch'].data = {'x': [], 'y': []}

    def clear_additional_plot_sources(self):
        self.source['trend'].data = {'x': [], 'y': [], 'mrn': []}
        self.source['bound'].data = {'x': [], 'mrn': [], 'upper': [], 'avg': [], 'lower': []}
        self.source['patch'].data = {'x': [], 'y': []}


class PlotRegression:
    def __init__(self, parent):

        self.figure, self.layout = get_base_plot(parent, plot_width=550, plot_height=400)

        self.figure_residual_fits = figure(plot_width=275, plot_height=200)
        self.figure_residual_fits.xaxis.axis_label = 'Fitted Values'
        self.figure_residual_fits.yaxis.axis_label = 'Residuals'
        self.figure_prob_plot = figure(plot_width=275, plot_height=200)
        self.figure_prob_plot.xaxis.axis_label = 'Quantiles'
        self.figure_prob_plot.yaxis.axis_label = 'Ordered Values'

        self.source = {'plot': ColumnDataSource(data=dict(x=[], y=[], mrn=[], uid=[])),
                       'trend': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'residuals': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'residuals_zero': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'prob': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'prob_45': ColumnDataSource(data=dict(x=[], y=[])),
                       'table': ColumnDataSource(data=dict(var=[], coef=[], std_err=[], t_value=[], p_value=[],
                                                           spacer=[], fit_param=[]))}

        self.plot_data = self.figure.circle('x', 'y', source=self.source['plot'], size=options.REGRESSION_CIRCLE_SIZE,
                                            alpha=options.REGRESSION_ALPHA, color=options.PLOT_COLOR)
        self.plot_trend = self.figure.line('x', 'y', color=options.PLOT_COLOR, source=self.source['trend'],
                                           line_width=options.REGRESSION_LINE_WIDTH,
                                           line_dash=options.REGRESSION_LINE_DASH)
        self.plot_residuals = self.figure_residual_fits.circle('x', 'y', source=self.source['residuals'],
                                                               size=options.REGRESSION_RESIDUAL_CIRCLE_SIZE,
                                                               alpha=options.REGRESSION_RESIDUAL_ALPHA,
                                                               color=options.PLOT_COLOR)
        self.plot_residuals_zero = self.figure_residual_fits.line('x', 'y', source=self.source['residuals_zero'],
                                                                  line_width=options.REGRESSION_RESIDUAL_LINE_WIDTH,
                                                                  line_dash=options.REGRESSION_RESIDUAL_LINE_DASH,
                                                                  alpha=options.REGRESSION_RESIDUAL_ALPHA,
                                                                  color=options.REGRESSION_RESIDUAL_LINE_COLOR)
        self.plot_prob = self.figure_prob_plot.circle('x', 'y', source=self.source['prob'],
                                                      size=options.REGRESSION_RESIDUAL_CIRCLE_SIZE,
                                                      alpha=options.REGRESSION_RESIDUAL_ALPHA,
                                                      color=options.PLOT_COLOR)
        self.plot_prob_45 = self.figure_prob_plot.line('x', 'y', source=self.source['prob_45'],
                                                       line_width=options.REGRESSION_RESIDUAL_LINE_WIDTH,
                                                       line_dash=options.REGRESSION_RESIDUAL_LINE_DASH,
                                                       alpha=options.REGRESSION_RESIDUAL_ALPHA,
                                                       color=options.REGRESSION_RESIDUAL_LINE_COLOR)

        columns = [TableColumn(field="var", title="", width=100),
                   TableColumn(field="coef", title="Coef", formatter=NumberFormatter(format="0.000"), width=50),
                   TableColumn(field="std_err", title="Std. Err.", formatter=NumberFormatter(format="0.000"), width=50),
                   TableColumn(field="t_value", title="t-value", formatter=NumberFormatter(format="0.000"), width=50),
                   TableColumn(field="p_value", title="p-value", formatter=NumberFormatter(format="0.000"), width=50),
                   TableColumn(field="spacer", title="", width=2),
                   TableColumn(field="fit_param", title="", width=75)]
        self.regression_table = DataTable(source=self.source['table'], columns=columns, width=500, height=100,
                                          index_position=None)

        self.figure.add_tools(HoverTool(show_arrow=True,
                                        tooltips=[('ID', '@mrn'),
                                                  ('x', '@x{0.2f}'),
                                                  ('y', '@y{0.2f}')]))

        self.bokeh_layout = column(self.figure,
                                   self.regression_table,
                                   row(self.figure_residual_fits, self.figure_prob_plot))

    def update_plot(self, plot_data, x_var, x_axis_title, y_axis_title):
        self.source['plot'].data = plot_data
        self.update_trend(x_var)
        self.figure.xaxis.axis_label = x_axis_title
        self.figure.yaxis.axis_label = y_axis_title
        html_str = get_layout_html(self.bokeh_layout)
        self.layout.SetPage(html_str, "")

    def update_trend(self, x_var):
        x, y, mrn = self.clean_data(self.source['plot'].data['x'],
                                    self.source['plot'].data['y'],
                                    self.source['plot'].data['mrn'])

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

    @staticmethod
    def clean_data(x, y, mrn):
        bad_indices = [i for i, value in enumerate(x) if value == 'None']
        bad_indices.extend([i for i, value in enumerate(y) if value == 'None'])
        bad_indices = list(set(bad_indices))

        return [value for i, value in enumerate(x) if i not in bad_indices],\
               [value for i, value in enumerate(y) if i not in bad_indices], \
               [value for i, value in enumerate(mrn) if i not in bad_indices]


class PlotMultiVarRegression:
    def __init__(self, parent):

        self.X, self.y = None, None

        self.figure_residual_fits, self.layout = get_base_plot(parent, plot_width=400, plot_height=400,
                                                               frame_size=(900, 600))

        self.figure_residual_fits.xaxis.axis_label = 'Fitted Values'
        self.figure_residual_fits.yaxis.axis_label = 'Residuals'
        self.figure_prob_plot = figure(plot_width=400, plot_height=400)
        apply_default_options(self.figure_prob_plot)
        self.figure_prob_plot.xaxis.axis_label = 'Quantiles'
        self.figure_prob_plot.yaxis.axis_label = 'Ordered Values'

        self.source = {'plot': ColumnDataSource(data=dict(x=[], y=[], mrn=[], uid=[])),
                       'trend': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'residuals': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'residuals_zero': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'prob': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'prob_45': ColumnDataSource(data=dict(x=[], y=[])),
                       'table': ColumnDataSource(data=dict(var=[], coef=[], std_err=[], t_value=[], p_value=[],
                                                           spacer=[], fit_param=[]))}

        self.plot_residuals = self.figure_residual_fits.circle('x', 'y', source=self.source['residuals'],
                                                               size=options.REGRESSION_RESIDUAL_CIRCLE_SIZE,
                                                               alpha=options.REGRESSION_RESIDUAL_ALPHA,
                                                               color=options.PLOT_COLOR)
        self.plot_residuals_zero = self.figure_residual_fits.line('x', 'y', source=self.source['residuals_zero'],
                                                                  line_width=options.REGRESSION_RESIDUAL_LINE_WIDTH,
                                                                  line_dash=options.REGRESSION_RESIDUAL_LINE_DASH,
                                                                  alpha=options.REGRESSION_RESIDUAL_ALPHA,
                                                                  color=options.REGRESSION_RESIDUAL_LINE_COLOR)
        self.plot_prob = self.figure_prob_plot.circle('x', 'y', source=self.source['prob'],
                                                      size=options.REGRESSION_RESIDUAL_CIRCLE_SIZE,
                                                      alpha=options.REGRESSION_RESIDUAL_ALPHA,
                                                      color=options.PLOT_COLOR)
        self.plot_prob_45 = self.figure_prob_plot.line('x', 'y', source=self.source['prob_45'],
                                                       line_width=options.REGRESSION_RESIDUAL_LINE_WIDTH,
                                                       line_dash=options.REGRESSION_RESIDUAL_LINE_DASH,
                                                       alpha=options.REGRESSION_RESIDUAL_ALPHA,
                                                       color=options.REGRESSION_RESIDUAL_LINE_COLOR)

        columns = [TableColumn(field="var", title="", width=100),
                   TableColumn(field="coef", title="Coef", formatter=NumberFormatter(format="0.000"), width=40),
                   TableColumn(field="std_err", title="Std. Err.", formatter=NumberFormatter(format="0.000"), width=40),
                   TableColumn(field="t_value", title="t-value", formatter=NumberFormatter(format="0.000"), width=40),
                   TableColumn(field="p_value", title="p-value", formatter=NumberFormatter(format="0.000"), width=40),
                   TableColumn(field="spacer", title="", width=5),
                   TableColumn(field="fit_param", title="", width=75)]
        self.regression_table = DataTable(source=self.source['table'], columns=columns, width=800, index_position=None)

        self.bokeh_layout = column(row(self.figure_prob_plot, self.figure_residual_fits),
                                   self.regression_table)

    def update_plot(self, y_variable, x_variables, stats_data):

        self.X, self.y = self.get_X_and_y(y_variable, x_variables, stats_data)
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

        fit_param = [''] * (len(x_variables) + 1)
        fit_param[0] = "R²: %0.3f ----- MSE: %0.3f" % (reg.r_sq, reg.mse)
        fit_param[1] = "f stat: %0.3f ---- p value: %0.3f" % (reg.f_stat, reg.f_p_value)
        self.source['table'].data = {'var': ['y-int'] + x_variables,
                                     'coef': [reg.y_intercept] + reg.slope.tolist(),
                                     'std_err': reg.sd_b,
                                     't_value': reg.ts_b,
                                     'p_value': reg.p_values,
                                     'spacer': [''] * (len(x_variables) + 1),
                                     'fit_param': fit_param}

        html_str = get_layout_html(self.bokeh_layout)
        self.layout.SetPage(html_str, "")

    def get_X_and_y(self, y_variable, x_variables, stats_data):
        data = []
        y_var_data = []
        for value in stats_data.data[y_variable]['values']:
            y_var_data.append([value, np.nan][value == 'None'])
        data.append(y_var_data)
        for var in x_variables:
            x_var_data = []
            for value in stats_data.data[var]['values']:
                x_var_data.append([value, np.nan][value == 'None'])
            data.append(x_var_data)

        data = np.array(data)
        clean_data = data[:, ~np.any(np.isnan(data), axis=0)]
        X = np.transpose(clean_data[1:])
        y = clean_data[0]

        return X, y


class PlotControlChart:
    def __init__(self, parent, x=[], y=[], mrn=[]):

        plot_width = 800  # store of histograms and divider bar

        self.figure, self.layout = get_base_plot(parent, x_axis_label='Study',
                                                 plot_width=plot_width, plot_height=325)
        color = [options.PLOT_COLOR] * len(x)
        alpha = [options.CONTROL_CHART_CIRCLE_ALPHA] * len(x)
        self.source = {'plot': ColumnDataSource(data=dict(x=x, y=y, mrn=mrn, color=color, alpha=alpha)),
                       'center_line': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'ucl_line': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'lcl_line': ColumnDataSource(data=dict(x=[], y=[], mrn=[])),
                       'bound': ColumnDataSource(data=dict(x=[], mrn=[], upper=[], avg=[], lower=[])),
                       'patch': ColumnDataSource(data=dict(x=[], y=[]))}

        self.figure.add_tools(HoverTool(show_arrow=True,
                                        tooltips=[('ID', '@mrn'),
                                                  ('Date', '@x{%F}'),
                                                  ('Value', '@y{0.2f}')],
                                        formatters={'x': 'datetime'}))

        self.plot_data = self.figure.circle('x', 'y', source=self.source['plot'],
                                            size=options.CONTROL_CHART_CIRCLE_SIZE,
                                            alpha='alpha',
                                            color='color')
        self.plot_data_line = self.figure.line('x', 'y', source=self.source['plot'],
                                               line_width=options.CONTROL_CHART_LINE_WIDTH,
                                               color=options.CONTROL_CHART_LINE_COLOR,
                                               line_dash=options.CONTROL_CHART_LINE_DASH)
        self.plot_patch = self.figure.patch('x', 'y', color=options.PLOT_COLOR, source=self.source['patch'],
                                            alpha=options.CONTROL_CHART_PATCH_ALPHA)
        self.plot_center_line = self.figure.line('x', 'y', source=self.source['center_line'],
                                                 line_width=options.CONTROL_CHART_CENTER_LINE_WIDTH,
                                                 alpha=options.CONTROL_CHART_CENTER_LINE_ALPHA,
                                                 color=options.CONTROL_CHART_CENTER_LINE_COLOR,
                                                 line_dash=options.CONTROL_CHART_CENTER_LINE_DASH)
        self.plot_lcl_line = self.figure.line('x', 'y', source=self.source['lcl_line'],
                                              line_width=options.CONTROL_CHART_LCL_LINE_WIDTH,
                                              alpha=options.CONTROL_CHART_LCL_LINE_ALPHA,
                                              color=options.CONTROL_CHART_LCL_LINE_COLOR,
                                              line_dash=options.CONTROL_CHART_LCL_LINE_DASH)
        self.plot_ucl_line = self.figure.line('x', 'y', source=self.source['ucl_line'],
                                              line_width=options.CONTROL_CHART_UCL_LINE_WIDTH,
                                              alpha=options.CONTROL_CHART_UCL_LINE_ALPHA,
                                              color=options.CONTROL_CHART_UCL_LINE_COLOR,
                                              line_dash=options.CONTROL_CHART_UCL_LINE_DASH)

        self.figure.add_tools(HoverTool(show_arrow=True,
                                        tooltips=[('ID', '@mrn'),
                                                  ('Date', '@x{%F}'),
                                                  ('Value', '@y{0.2f}')],
                                        formatters={'x': 'datetime'}))

        self.div_center_line = Div(text='', width=175)
        self.div_ucl = Div(text='', width=175)
        self.div_lcl = Div(text='', width=175)

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

        self.bokeh_layout = column(self.figure,
                                   row(self.div_center_line, self.div_ucl, self.div_lcl))

    def update_plot(self, x, y, mrn, y_axis_label='Y Axis'):
        self.figure.yaxis.axis_label = y_axis_label
        valid_indices = [i for i, value in enumerate(y) if value != 'None']

        x = [value for i, value in enumerate(x) if i in valid_indices]
        y = [value for i, value in enumerate(y) if i in valid_indices]
        mrn = [value for i, value in enumerate(mrn) if i in valid_indices]

        center_line, ucl, lcl = get_control_limits(y)

        colors = [options.CONTROL_CHART_OUT_OF_CONTROL_COLOR, options.PLOT_COLOR]
        alphas = [options.CONTROL_CHART_OUT_OF_CONTROL_ALPHA, options.CONTROL_CHART_CIRCLE_ALPHA]
        color = [colors[ucl > value > lcl] for value in y]
        alpha = [alphas[ucl > value > lcl] for value in y]

        self.source['plot'].data = {'x': x, 'y': y, 'mrn': mrn, 'color': color, 'alpha': alpha}

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

        html_str = get_layout_html(self.bokeh_layout)
        self.layout.SetPage(html_str, "")


class PlotRandomForest:
    def __init__(self, parent, y, y_predict, mse):
        self.y, self.y_predict = y, y_predict
        self.mse = mse

        self.x = list(range(1, len(self.y)+1))

        self.figure_predictions, self.layout = get_base_plot(parent, plot_width=400, plot_height=400,
                                                             frame_size=(900, 600))

        self.source = ColumnDataSource(data=dict(x=self.x, y=self.y, y_predict=self.y_predict))

        self.figure_predictions.circle('x', 'y', source=self.source, color='blue')
        self.figure_predictions.circle('x', 'y_predict', source=self.source, color='red')

        self.bokeh_layout = column(self.figure_predictions)
        html_str = get_layout_html(self.bokeh_layout)
        self.layout.SetPage(html_str, "")
