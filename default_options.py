"""
Various options for DVH Analytics
Created on Sat Oct 28 2017
@author: Dan Cutright, PhD
"""

import os
import paths

VERSION = '0.6'

MIN_BORDER = 5

# These colors propagate to all tabs that visualize your two groups
PLOT_COLOR = 'blue'

# The line width and style of selected DVHs in the DVH plot
DVH_LINE_WIDTH = 2
DVH_LINE_DASH = 'solid'

# Adjusts the opacity of the inner-quartile ranges
IQR_ALPHA = 0.075

# Adjust the plot font sizes
PLOT_AXIS_LABEL_FONT_SIZE = "12pt"
PLOT_AXIS_MAJOR_LABEL_FONT_SIZE = "10pt"

# Number of data points are reduced by this factor during dynamic plot interaction to speed-up visualizations
# This is only applied to the DVH plot since it has a large amount of data
LOD_FACTOR = 100

# Options for the group statistical DVHs in the DVHs tab
STATS_MEDIAN_LINE_WIDTH = 1
STATS_MEDIAN_LINE_DASH = 'solid'
STATS_MEDIAN_ALPHA = 0.6
STATS_MEAN_LINE_WIDTH = 2
STATS_MEAN_LINE_DASH = 'dashed'
STATS_MEAN_ALPHA = 0.5
STATS_MAX_LINE_WIDTH = 1
STATS_MAX_LINE_DASH = 'dotted'
STATS_MAX_ALPHA = 1
STATS_MIN_LINE_WIDTH = 1
STATS_MIN_LINE_DASH = 'dotted'
STATS_MIN_ALPHA = 1


# Options for the time-series plot
TIME_SERIES_CIRCLE_SIZE = 10
TIME_SERIES_CIRCLE_ALPHA = 0.3
TIME_SERIES_TREND_LINE_WIDTH = 1
TIME_SERIES_TREND_LINE_DASH = 'solid'
TIME_SERIES_AVG_LINE_WIDTH = 1
TIME_SERIES_AVG_LINE_DASH = 'dotted'
TIME_SERIES_PATCH_ALPHA = 0.1

# Adjust the opacity of the histograms
HISTOGRAM_ALPHA = 0.3

# Options for the plot in the Multi-Variable Regression tab
REGRESSION_CIRCLE_SIZE = 10
REGRESSION_ALPHA = 0.5
REGRESSION_LINE_WIDTH = 2
REGRESSION_LINE_DASH = 'dashed'

# This is the number of bins up do 100% used when resampling a DVH to fractional dose
RESAMPLED_DVH_BIN_COUNT = 5000

COMPLEXITY_SCORE_X_WEIGHT = 1.
COMPLEXITY_SCORE_Y_WEIGHT = 1.
COMPLEXITY_SCORE_GLOBAL_SCALING_FACTOR = 1000.

ROI_TYPES = ['ORGAN', 'PTV', 'ITV', 'CTV', 'GTV', 'EXTERNAL',
             'FIDUCIAL', 'IMPLANT', 'OPTIMIZATION', 'PRV', 'SUPPORT', 'NONE']

# Note that docker paths are absolute, default will be treated as relative to script directory
SETTINGS_PATHS = {'import': os.path.join(paths.PREF_DIR, 'import_settings.txt'),
                  'sql': os.path.join(paths.PREF_DIR, 'sql_connection.cnf')}
