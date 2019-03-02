import os

SCRIPT_DIR = os.path.dirname(os.path.dirname(__file__))
APPS_DIR = os.path.join(os.path.expanduser('~'), 'Apps')
APP_DIR = os.path.join(APPS_DIR, 'dvh_analytics')
PREF_DIR = os.path.join(APP_DIR, 'preferences')
DATA_DIR = os.path.join(APP_DIR, 'data')
INBOX_DIR = os.path.join(DATA_DIR, 'inbox')
IMPORTED_DIR = os.path.join(DATA_DIR, 'imported')
REVIEW_DIR = os.path.join(DATA_DIR, 'review')
BACKUP_DIR = os.path.join(DATA_DIR, 'backup')
PLOTS_DIR = os.path.join(APP_DIR, 'plots')
