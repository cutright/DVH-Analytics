from bokeh.plotting import figure
from bokeh.io.export import get_layout_html
from options import load_options
from bokeh.models import Legend, HoverTool, ColumnDataSource, DataTable, TableColumn, NumberFormatter, Div
from bokeh.layouts import column
from bokeh.palettes import Colorblind8 as palette
import itertools
import default_options as options
import wx
import wx.html2
import numpy as np
from paths import PLOTS_PATH


options = load_options()


def get_base_plot(parent, x_axis_label='X Axis', y_axis_label='Y Axis', plot_width=800, plot_height=500,
                  frame_size=(900, 900), x_axis_type='linear'):

    wxlayout = wx.html2.WebView.New(parent, size=frame_size)

    fig = figure(plot_width=plot_width, plot_height=plot_height, x_axis_type=x_axis_type)
    fig.xaxis.axis_label = x_axis_label
    fig.yaxis.axis_label = y_axis_label

    fig.xaxis.axis_label_text_font_size = options.PLOT_AXIS_LABEL_FONT_SIZE
    fig.yaxis.axis_label_text_font_size = options.PLOT_AXIS_LABEL_FONT_SIZE
    fig.xaxis.major_label_text_font_size = options.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE
    fig.yaxis.major_label_text_font_size = options.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE
    fig.min_border_bottom = options.MIN_BORDER
    fig.yaxis.axis_label_text_baseline = "bottom"

    return fig, wxlayout


class PlotStatDVH:
    def __init__(self, parent, dvh):

        self.figure, self.layout = get_base_plot(parent, x_axis_label='Dose (cGy)', y_axis_label='Relative Volume',
                                                 plot_width=750, plot_height=400)

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
        legend_stats = Legend(items=[("Max", [stats_max]),
                                     ("Median", [stats_median]),
                                     ("Mean", [stats_mean]),
                                     ("Min", [stats_min]),
                                     ("IQR", [iqr])],
                              location=(10, 0))

        # Add the layout outside the plot, clicking legend item hides the line
        self.figure.add_layout(legend_stats, 'right')
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
        self.table = DataTable(source=self.source, columns=columns, height=275, width=750)

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

        bokeh_layout = column(self.figure, self.table)
        save_bokeh_layout(bokeh_layout)
        self.layout.LoadURL(PLOTS_PATH)


class PlotTimeSeries:
    def __init__(self, parent, x=[], y=[], mrn=[]):

        self.plot_width = 750

        self.figure, self.layout = get_base_plot(parent, x_axis_label='Simulation Date',
                                                 plot_width=self.plot_width, plot_height=300, x_axis_type='datetime')

        self.source = ColumnDataSource(data=dict(x=x, y=y, mrn=mrn))
        self.source_histogram = ColumnDataSource(data=dict(x=[], top=[], width=[]))

        self.figure.add_tools(HoverTool(show_arrow=True,
                                        tooltips=[('ID', '@mrn'),
                                                  ('Date', '@x{%F}'),
                                                  ('Value', '@y{0.2f}')],
                                        formatters={'x': 'datetime'}))

        self.figure.circle('x', 'y', source=self.source, size=options.TIME_SERIES_CIRCLE_SIZE,
                           alpha=options.TIME_SERIES_CIRCLE_ALPHA, color=options.PLOT_COLOR)

        tools = "pan,wheel_zoom,box_zoom,reset,crosshair,save"
        self.histograms = figure(plot_width=self.plot_width, plot_height=300, tools=tools, active_drag="box_zoom")
        self.histograms.xaxis.axis_label_text_font_size = options.PLOT_AXIS_LABEL_FONT_SIZE
        self.histograms.yaxis.axis_label_text_font_size = options.PLOT_AXIS_LABEL_FONT_SIZE
        self.histograms.xaxis.major_label_text_font_size = options.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE
        self.histograms.yaxis.major_label_text_font_size = options.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE
        self.histograms.min_border_left = options.MIN_BORDER
        self.histograms.min_border_bottom = options.MIN_BORDER
        self.vbar = self.histograms.vbar(x='x', width='width', bottom=0, top='top', source=self.source_histogram,
                                         color=options.PLOT_COLOR, alpha=options.HISTOGRAM_ALPHA)

        self.histograms.xaxis.axis_label = ""
        self.histograms.yaxis.axis_label = "Frequency"
        self.histograms.add_tools(HoverTool(show_arrow=True, line_policy='next',
                                            tooltips=[('x', '@x{0.2f}'),
                                                      ('Counts', '@top')]))

    def update_plot(self, x, y, mrn, y_axis_label='Y Axis'):
        self.figure.yaxis.axis_label = y_axis_label
        self.histograms.xaxis.axis_label = y_axis_label
        valid_indices = [i for i, value in enumerate(y) if value != 'None']
        self.source.data = {'x': [value for i, value in enumerate(x) if i in valid_indices],
                            'y': [value for i, value in enumerate(y) if i in valid_indices],
                            'mrn': [value for i, value in enumerate(mrn) if i in valid_indices]}

        # histograms
        bin_size = 20
        width_fraction = 0.9

        hist, bins = np.histogram(self.source.data['y'], bins=bin_size)
        width = [width_fraction * (bins[1] - bins[0])] * bin_size
        center = (bins[:-1] + bins[1:]) / 2.
        self.source_histogram.data = {'x': center, 'top': hist, 'width': width}

        bokeh_layout = column(self.figure, Div(text='<hr>', width=self.plot_width), self.histograms)
        save_bokeh_layout(bokeh_layout)
        self.layout.LoadURL(PLOTS_PATH)


def save_bokeh_layout(bokeh_layout):
    html = get_layout_html(bokeh_layout)
    with open(PLOTS_PATH, "w") as text_file:
        text_file.write(html)
