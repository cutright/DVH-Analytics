from os.path import join, dirname, expanduser

SCRIPT_DIR = dirname(__file__)
ICONS_DIR = join(SCRIPT_DIR, 'icons')
LOGO_PATH = join(SCRIPT_DIR, 'logo.png')
APPS_DIR = join(expanduser('~'), 'Apps')
APP_DIR = join(APPS_DIR, 'dvh_analytics')
PREF_DIR = join(APP_DIR, 'preferences')
DATA_DIR = join(APP_DIR, 'data')
INBOX_DIR = join(DATA_DIR, 'inbox')
IMPORTED_DIR = join(DATA_DIR, 'imported')
REVIEW_DIR = join(DATA_DIR, 'review')
BACKUP_DIR = join(DATA_DIR, 'backup')

OPTIONS_PATH = join(PREF_DIR, '.options')
OPTIONS_CHECKSUM_PATH = join(PREF_DIR, '.options_checksum')
IMPORT_SETTINGS_PATH = join(PREF_DIR, 'import_settings.txt')
SQL_CNF_PATH = join(PREF_DIR, 'sql_connection.cnf')


def parse_settings_file(abs_file_path):
    with open(abs_file_path, 'r') as document:
        settings = {}
        for line in document:
            line = line.split()
            if not line:
                continue
            if len(line) > 1:
                settings[line[0]] = line[1:][0]
                # Convert strings to boolean
                if line[1:][0].lower() == 'true':
                    settings[line[0]] = True
                elif line[1:][0].lower() == 'false':
                    settings[line[0]] = False
            else:
                settings[line[0]] = ''
    return settings
