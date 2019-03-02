from bokeh.plotting import figure, output_file, save
from paths import PLOTS_DIR
import os
import default_options as options
from bokeh.models import Legend, HoverTool, ColumnDataSource, DataTable, TableColumn, NumberFormatter
from bokeh.layouts import column
from bokeh.palettes import Colorblind8 as palette
import itertools


def plot(x, y, file_name=os.path.join(PLOTS_DIR, 'plot.html'),
         x_axis_label='X Axis', y_axis_label='Y Axis', title=''):

    p = figure(title=title, plot_width=600, plot_height=500)
    p.xaxis.axis_label = x_axis_label
    p.yaxis.axis_label = y_axis_label

    p.multi_line(x, y, line_alpha=0.5, line_width=2)

    output_file(file_name, title="Plot")

    save(p)

    return file_name


def plot_stat_dvh(dvh_obj, file_name=os.path.join(PLOTS_DIR, 'plot.html'), x_axis_label='X Axis',
                  y_axis_label='Y Axis', title=''):

    data = dvh_obj.get_cds_data()
    data['x'] = dvh_obj.x_data
    data['y'] = dvh_obj.y_data
    colors = itertools.cycle(palette)
    data['color'] = [color for j, color in zip(range(dvh_obj.count), colors)]
    source = ColumnDataSource(data=data)
    x = list(range(dvh_obj.bin_count))

    stat_dvhs = dvh_obj.get_standard_stat_dvh()
    stats_data = {key: stat_dvhs[key] for key in ['max', 'median', 'mean', 'min']}
    stats_data['x'] = x
    source_stats = ColumnDataSource(data=stats_data)

    tools = "pan,wheel_zoom,box_zoom,reset,crosshair,save"
    p = figure(plot_width=750, plot_height=400, tools=tools, active_drag="box_zoom")
    p.xaxis.axis_label = x_axis_label
    p.yaxis.axis_label = y_axis_label
    p.min_border_left = options.MIN_BORDER
    p.min_border_bottom = options.MIN_BORDER
    p.add_tools(HoverTool(show_arrow=False, line_policy='next',
                          tooltips=[('Label', '@mrn @roi_name'),
                                    ('Dose', '$x'),
                                    ('Volume', '$y')]))
    p.xaxis.axis_label_text_font_size = options.PLOT_AXIS_LABEL_FONT_SIZE
    p.yaxis.axis_label_text_font_size = options.PLOT_AXIS_LABEL_FONT_SIZE
    p.xaxis.major_label_text_font_size = options.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE
    p.yaxis.major_label_text_font_size = options.PLOT_AXIS_MAJOR_LABEL_FONT_SIZE
    p.yaxis.axis_label_text_baseline = "bottom"
    p.lod_factor = options.LOD_FACTOR  # level of detail during interactive plot events

    # Add all DVHs, but hide them until selected
    # p.multi_line('x', 'y', source=source, line_width=0.3, alpha=0.1,
    #              line_dash=options.DVH_LINE_DASH, color='black')
    p.multi_line('x', 'y', source=source, selection_color='color', line_width=options.DVH_LINE_WIDTH, alpha=0,
                 line_dash=options.DVH_LINE_DASH, nonselection_alpha=0, selection_alpha=1)

    # Add statistical plots to figure
    stats_max = p.line('x', 'max', source=source_stats, line_width=options.STATS_MAX_LINE_WIDTH,
                       color=options.GROUP_1_COLOR, line_dash=options.STATS_MAX_LINE_DASH,
                       alpha=options.STATS_MAX_ALPHA)
    stats_median = p.line('x', 'median', source=source_stats, line_width=options.STATS_MEDIAN_LINE_WIDTH,
                          color=options.GROUP_1_COLOR, line_dash=options.STATS_MEDIAN_LINE_DASH,
                          alpha=options.STATS_MEDIAN_ALPHA)
    stats_mean = p.line('x', 'mean', source=source_stats, line_width=options.STATS_MEAN_LINE_WIDTH,
                        color=options.GROUP_1_COLOR, line_dash=options.STATS_MEAN_LINE_DASH,
                        alpha=options.STATS_MEAN_ALPHA)
    stats_min = p.line('x', 'min', source=source_stats, line_width=options.STATS_MIN_LINE_WIDTH,
                       color=options.GROUP_1_COLOR, line_dash=options.STATS_MIN_LINE_DASH,
                       alpha=options.STATS_MIN_ALPHA)

    x_patch = x + x[::-1]
    y_patch = stat_dvhs['q3'].tolist() + stat_dvhs['q1'][::-1].tolist()

    # Shaded region between Q1 and Q3
    iqr = p.patch(x_patch, y_patch, alpha=options.IQR_1_ALPHA, color=options.GROUP_1_COLOR)

    # Set the legend (for stat dvhs only)
    legend_stats = Legend(items=[("Max", [stats_max]),
                                 ("Median", [stats_median]),
                                 ("Mean", [stats_mean]),
                                 ("Min", [stats_min]),
                                 ("IQR", [iqr])],
                          location=(25, 0))

    # Add the layout outside the plot, clicking legend item hides the line
    p.add_layout(legend_stats, 'right')
    p.legend.click_policy = "hide"

    # DataTable
    columns = [TableColumn(field="mrn", title="MRN", width=175),
               TableColumn(field="roi_name", title="ROI Name"),
               TableColumn(field="roi_type", title="ROI Type", width=80),
               TableColumn(field="rx_dose", title="Rx Dose", width=100, formatter=NumberFormatter(format="0.00")),
               TableColumn(field="volume", title="Volume", width=80, formatter=NumberFormatter(format="0.00")),
               TableColumn(field="min_dose", title="Min Dose", width=80, formatter=NumberFormatter(format="0.00")),
               TableColumn(field="mean_dose", title="Mean Dose", width=80, formatter=NumberFormatter(format="0.00")),
               TableColumn(field="max_dose", title="Max Dose", width=80, formatter=NumberFormatter(format="0.00")),]
    table = DataTable(source=source, columns=columns, height=200, width=750)

    output_file(file_name, title="Plot")

    save(column(p, table))

    return file_name
