from os.path import join, dirname, expanduser

SCRIPT_DIR = dirname(dirname(__file__))
APPS_DIR = join(expanduser('~'), 'Apps')
APP_DIR = join(APPS_DIR, 'dvh_analytics')
PREF_DIR = join(APP_DIR, 'preferences')
DATA_DIR = join(APP_DIR, 'data')
INBOX_DIR = join(DATA_DIR, 'inbox')
IMPORTED_DIR = join(DATA_DIR, 'imported')
REVIEW_DIR = join(DATA_DIR, 'review')
BACKUP_DIR = join(DATA_DIR, 'backup')
PLOTS_DIR = join(APP_DIR, 'plots')
PLOTS_PATH = join(PLOTS_DIR, 'plot.html')
