#!/usr/bin/env python
# -*- coding: utf-8 -*-

# tools.utilties.py
"""
General utilities for DVHA

"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
from datetime import datetime
from dateutil.parser import parse as parse_date
import linecache
import numpy as np
from os import walk, listdir, unlink, mkdir, rmdir, chdir, sep, environ
from os.path import join, isfile, isdir, splitext, basename, dirname, realpath, pathsep
import pickle
import pydicom
from pydicom.uid import ImplicitVRLittleEndian
import shutil
from subprocess import check_output
import sys
import tracemalloc
from dvha.db.sql_connector import DVH_SQL
from dvha.paths import SQL_CNF_PATH, WIN_APP_ICON, PIP_LIST_PATH, DIRECTORIES, APP_DIR, BACKUP_DIR, DATA_DIR


IGNORED_FILES = ['.ds_store']


def is_windows():
    return wx.Platform == '__WXMSW__'


def set_msw_background_color(window_obj, color='lightgrey'):
    if is_windows():
        window_obj.SetBackgroundColour(color)


def is_linux():
    return wx.Platform == '__WXGTK__'


def is_mac():
    return wx.Platform == '__WXMAC__'


def initialize_directories():
    """Based on paths.py, create required directories if they do not exist"""
    for directory in DIRECTORIES.values():
        if not isdir(directory):
            mkdir(directory)
    initialize_protocols()


def initialize_protocols():
    """If no protocols are found in PROTOCOL_DIR, copy defaults"""
    current_protocols = [f for f in listdir(DIRECTORIES['PROTOCOL']) if splitext(f)[1].lower() == '.scp']
    if not current_protocols:
        file_names = [f for f in listdir(DIRECTORIES['PROTOCOL_DEFAULT']) if splitext(f)[1].lower() == '.scp']
        file_paths = [join(DIRECTORIES['PROTOCOL_DEFAULT'], f) for f in file_names]
        move_files_to_new_path(file_paths, DIRECTORIES['PROTOCOL'], copy_files=True)


def write_sql_connection_settings(config):
    """
    Create a file storing the SQL login credentials
    :param config: contains values for 'host', 'dbname', 'port' and optionally 'user' and 'password'
    :type config: dict
    """
    # TODO: Make this more secure

    text = ["%s %s" % (key, value) for key, value in config.items() if value]
    text = '\n'.join(text)

    with open(SQL_CNF_PATH, "w") as text_file:
        text_file.write(text)


def scale_bitmap(bitmap, width, height):
    """
    Used to scale tool bar images for MSW and GTK, MAC automatically scales
    :param bitmap: bitmap to be scaled
    type bitmap: Bitmap
    :param width: width of output bitmap
    :type width: int
    :param height: height of output bitmap
    :type height: int
    :return: scaled bitmap
    :rtype: Bitmap
    """
    image = wx.Bitmap.ConvertToImage(bitmap)
    image = image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
    return wx.Bitmap(image)


def get_tree_ctrl_image(file_path, file_type=wx.BITMAP_TYPE_PNG, width=16, height=16):
    """
    Create an image top be used in the TreeCtrl from the provided file_path
    :param file_path: absolute file_path of image
    :type file_path: str
    :param file_type: specify the image format (PNG by default)
    :param width: width of output bitmap (16 default)
    :type width: int
    :param height: height of output bitmap (16 default)
    :type height: int
    :return: scaled image for TreeCtrl
    :rtype: Image
    """
    return wx.Image(file_path, file_type).Scale(width, height).ConvertToBitmap()


def get_file_paths(start_path, search_subfolders=False, extension=None):
    """
    Get a list of absolute file paths for a given directory
    :param start_path: initial directory
    :type start_path str
    :param search_subfolders: optionally search all sub folders
    :type search_subfolders: bool
    :param extension: optionally include only files with specified extension
    :type extension: str
    :return: absolute file paths
    :rtype: list
    """
    if isdir(start_path):
        if search_subfolders:
            file_paths = []
            for root, dirs, files in walk(start_path, topdown=False):
                for name in files:
                    if extension is None or splitext(name)[1].lower() == extension.lower():
                        if name.lower() not in IGNORED_FILES:
                            file_paths.append(join(root, name))
            return file_paths

        file_paths = []
        for f in listdir(start_path):
            if isfile(join(start_path, f)):
                if extension is None or splitext(f)[1].lower() == extension.lower():
                    if f.lower() not in IGNORED_FILES:
                        file_paths.append(join(start_path, f))
        return file_paths
    return []


def get_study_instance_uids(**kwargs):
    """
    Get lists of study instance uids in the SQL database that meet provided conditions
    The values return in the 'common' key are used for the DVH class in models.dvh.py
    :param kwargs: keys are SQL table names and the values are conditions in SQL syntax
    :return: study instance uids for each table, uids found in all tables, and a list of unique uids
    :rtype: dict
    """
    with DVH_SQL() as cnx:
        uids = {table: cnx.get_unique_values(table, 'study_instance_uid', condition)
                for table, condition in kwargs.items()}

    complete_list = flatten_list_of_lists(list(uids.values()), remove_duplicates=True)

    uids['common'] = [uid for uid in complete_list if is_uid_in_all_keys(uid, uids)]
    uids['unique'] = complete_list

    return uids


def is_uid_in_all_keys(uid, uids):
    """
    Check if uid is found in each of the uid lists for each SQL table
    :param uid: study instance uid
    :type uid: str
    :param uids: lists of study instance uids organized by SQL table
    :type uids: dict
    :return: True only if uid is found in each of the tables
    :rtype: bool
    """

    table_answer = {}
    # Initialize a False value for each key
    for table in list(uids):
        table_answer[table] = False
    # search for uid in each keyword fof uid_kwlist
    for table, value in uids.items():
        if uid in value:
            table_answer[table] = True

    final_answer = True
    # Product of all answer[key] values (except 'unique')
    for table, value in table_answer.items():
        if table not in 'unique':
            final_answer *= value
    return final_answer


def flatten_list_of_lists(some_list, remove_duplicates=False, sort=False):
    """
    Convert a list of lists into a list of all values
    :param some_list: a list such that each value is a list
    :type some_list: list
    :param remove_duplicates: if True, return a unique list, otherwise keep duplicated values
    :type remove_duplicates: bool
    :param sort: if True, sort the list
    :type sort: bool
    :return: a new object containing all values in teh provided
    """
    data = [item for sublist in some_list for item in sublist]
    if sort:
        data.sort()
    if remove_duplicates:
        return list(set(data))
    return data


def collapse_into_single_dates(x, y):
    """
    Function used for a time plot to convert multiple values into one value, while retaining enough information
    to perform a moving average over time
    :param x: a list of dates in ascending order
    :param y: a list of values and can use the '+' operator as a function of date
    :return: a unique list of dates, sum of y for that date, and number of original points for that date
    :rtype: dict
    """

    # average daily data and keep track of points per day
    x_collapsed = [x[0]]
    y_collapsed = [y[0]]
    w_collapsed = [1]
    for n in range(1, len(x)):
        if x[n] == x_collapsed[-1]:
            y_collapsed[-1] = (y_collapsed[-1] + y[n])
            w_collapsed[-1] += 1
        else:
            x_collapsed.append(x[n])
            y_collapsed.append(y[n])
            w_collapsed.append(1)

    return {'x': x_collapsed, 'y': y_collapsed, 'w': w_collapsed}


def moving_avg(xyw, avg_len):
    """
    Calculate a moving average for a given averaging length
    :param xyw: output from collapse_into_single_dates
    :type xyw: dict
    :param avg_len: average of these number of points, i.e., look-back window
    :type avg_len: int
    :return: list of x values, list of y values
    :rtype: tuple
    """
    cumsum, moving_aves, x_final = [0], [], []

    for i, y in enumerate(xyw['y'], 1):
        cumsum.append(cumsum[i - 1] + y / xyw['w'][i - 1])
        if i >= avg_len:
            moving_ave = (cumsum[i] - cumsum[i - avg_len]) / avg_len
            moving_aves.append(moving_ave)
    x_final = [xyw['x'][i] for i in range(avg_len - 1, len(xyw['x']))]

    return x_final, moving_aves


def convert_value_to_str(value, rounding_digits=2):
    try:
        formatter = "%%0.%df" % rounding_digits
        return formatter % value
    except TypeError:
        return value


def get_selected_listctrl_items(list_control):
    """
    Get the indices of the currently selected items of a wx.ListCtrl object
    :param list_control: any wx.ListCtrl object
    :type list_control: ListCtrl
    :return: indices of selected items
    :rtype: list
    """
    selection = []

    index_current = -1
    while True:
        index_next = list_control.GetNextItem(index_current, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        if index_next == -1:
            return selection

        selection.append(index_next)
        index_current = index_next


def print_run_time(start_time, end_time, calc_title):
    """
    :param start_time: start time of process
    :type start_time: datetime
    :param end_time: end time of process
    :type end_time: datetime
    :param calc_title: prepend the status message with this value
    :type calc_title: str
    :return:
    """
    total_time = end_time - start_time
    seconds = total_time.seconds
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        print("%s. This took %dhrs %02dmin %02dsec to complete" % (calc_title, h, m, s))
    elif m:
        print("%s. This took %02dmin %02dsec to complete" % (calc_title, m, s))
    else:
        print("%s. This took %02dsec to complete" % (calc_title, s))


def datetime_to_date_string(datetime_obj):
    if isinstance(datetime_obj, str):
        datetime_obj = parse_date(datetime_obj)
    return "%s/%s/%s" % (datetime_obj.month, datetime_obj.day, datetime_obj.year)


def change_angle_origin(angles, max_positive_angle):
    """
    Angles in DICOM are all positive values, but there is typically no mechanical continuity in across 180 degrees
    :param angles: angles to be converted
    :type angles list
    :param max_positive_angle: the maximum positive angle, angles greater than this will be shifted to negative angles
    :return: list of the same angles, but none exceed the max
    :rtype: list
    """
    if len(angles) == 1:
        if angles[0] > max_positive_angle:
            return [angles[0] - 360]
        else:
            return angles
    new_angles = []
    for angle in angles:
        if angle > max_positive_angle:
            new_angles.append(angle - 360)
        elif angle == max_positive_angle:
            if angle == angles[0] and angles[1] > max_positive_angle:
                new_angles.append(angle - 360)
            elif angle == angles[-1] and angles[-2] > max_positive_angle:
                new_angles.append(angle - 360)
            else:
                new_angles.append(angle)
        else:
            new_angles.append(angle)
    return new_angles


def calc_stats(data):
    """
    Calculate a standard set of stats for DVHA
    :param data: a list or numpy 1D array of numbers
    :type data: list
    :return:  max, 75%, median, mean, 25%, and min of data
    :rtype: list
    """
    data = [x for x in data if x != 'None']
    try:
        data_np = np.array(data)
        rtn_data = [np.max(data_np),
                    np.percentile(data_np, 75),
                    np.median(data_np),
                    np.mean(data_np),
                    np.percentile(data_np, 25),
                    np.min(data_np)]
    except Exception:
        rtn_data = [0, 0, 0, 0, 0, 0]
        print("calc_stats() received non-numerical data")
    return rtn_data


def move_files_to_new_path(files, new_dir, copy_files=False, new_file_names=None):
    """
    Move all files provided to the new directory
    :param files: absolute file paths
    :type files: list
    :param new_dir: absolute directory path
    :type new_dir: str
    :param copy_files: Set to True to keep original files and copy to new_dir, False to remove original files
    :type copy_files: bool
    :param new_file_names: optionally provide a list of new names
    :type new_file_names: None or list of str
    """
    for i, file_path in enumerate(files):
        if isfile(file_path):
            file_name = basename(file_path)
            old_dir = dirname(file_path)
            new_file_name = file_name if new_file_names is None else new_file_names[i]
            new = join(new_dir, new_file_name)
            if not isdir(new_dir):
                mkdir(new_dir)
            if old_dir != new_dir:
                [shutil.move, shutil.copy][copy_files](file_path, new)


def delete_directory_contents(dir_to_delete):
    # https://stackoverflow.com/questions/185936/how-to-delete-the-contents-of-a-folder-in-python
    for the_file in listdir(dir_to_delete):
        delete_file(join(dir_to_delete, the_file))


def delete_file(file_path):
    try:
        if isfile(file_path):
            unlink(file_path)
        elif isdir(file_path):
            shutil.rmtree(file_path)
    except Exception as e:
        print(e)


def delete_imported_dicom_files(dicom_files):
    """
    delete imported dicom files
    :param dicom_files: the return from DVH_SQL().get_dicom_file_paths
    :type dicom_files: dict
    """
    for i, directory in enumerate(dicom_files['folder_path']):
        # Delete associated plan, structure, and dose files
        for key in ['plan_file', 'structure_file', 'dose_file']:
            delete_file(join(directory, dicom_files[key][i]))

        # Delete misc dicom files for given study instance uid
        remaining_files = listdir(directory)
        for f in remaining_files:
            try:
                uid = str(pydicom.read_file(join(directory, f)).StudyInstanceUID)
                if uid == str(dicom_files['study_instance_uid'][i]):
                    delete_file(f)
            except Exception:
                pass

        # Directory is empty, delete it
        # Directories are by patient mrn, so it might contain files for a different study for the same patient
        if not listdir(directory):
            try:
                rmdir(directory)
            except Exception:
                pass


def move_imported_dicom_files(dicom_files, new_dir):
    """
    move imported dicom files
    :param dicom_files: the return from DVH_SQL().get_dicom_file_paths
    :type dicom_files: dict
    """
    for i, directory in enumerate(dicom_files['folder_path']):
        files = [join(directory, dicom_files[key][i]) for key in ['plan_file', 'structure_file', 'dose_file']]
        new_patient_dir = join(new_dir, dicom_files['mrn'][i])
        move_files_to_new_path(files, new_patient_dir)

        # Move misc dicom files for given study instance uid
        remaining_files = listdir(directory)
        files = []
        for f in remaining_files:
            try:
                uid = str(pydicom.read_file(join(directory, f)).StudyInstanceUID)
                if uid == str(dicom_files['study_instance_uid'][i]):
                    files.append(f)
            except Exception:
                pass
        move_files_to_new_path(files, new_patient_dir)

        # Directory is empty, delete it
        # Directories are by patient mrn, so it might contain files for a different study for the same patient
        if not listdir(directory):
            try:
                rmdir(directory)
            except Exception:
                pass


def remove_empty_sub_folders(start_path):
    for (path, dirs, files) in walk(start_path, topdown=False):
        if files:
            continue
        try:
            if path != start_path:
                rmdir(path)
        except OSError:
            pass


def move_all_files(new_dir, old_dir):
    """
    This function will move all files from the old to new directory, it will ignore all files in subdirectories
    :param new_dir: absolute directory path
    :param old_dir: absolute directory path
    """
    initial_path = dirname(realpath(__file__))

    chdir(old_dir)

    file_paths = [f for f in listdir(old_dir) if isfile(join(old_dir, f))]

    misc_path = join(new_dir, 'misc')
    if not isdir(misc_path):
        mkdir(misc_path)

    for f in file_paths:
        file_name = basename(f)
        new = join(misc_path, file_name)
        shutil.move(f, new)

    chdir(initial_path)


def get_elapsed_time(start_time, end_time):
    total_time = end_time - start_time
    seconds = total_time.seconds
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return "%d hrs %d min %d sec" % (h, m, s)
    if m:
        return "%d min %d sec" % (m, s)
    return "%d sec" % s


def is_date(date):
    if isinstance(date, datetime):
        return True

    if isinstance(date, str):
        try:
            parse_date(date)
            return True
        except Exception:
            return False

    return False


def rank_ptvs_by_D95(ptvs):
    """
    Determine the order of provided PTVs by their D_95% values
    :param ptvs: dvh, volume, index of PTVs
    :type ptvs: dict
    :return: ptv numbers in order of D_95%
    """
    doses_to_rank = get_dose_to_volume(ptvs['dvh'], ptvs['volume'], 0.95)
    return sorted(range(len(ptvs['dvh'])), key=lambda k: doses_to_rank[k])


def get_dose_to_volume(dvhs, volumes, roi_fraction):
    # Not precise (i.e., no interpolation) but good enough for sorting PTVs
    doses = []
    for i, dvh in enumerate(dvhs):
        abs_volume = volumes[i] * roi_fraction
        dvh_np = np.array(dvh.split(','), dtype=np.float)
        try:
            dose = next(x[0] for x in enumerate(dvh_np) if x[1] < abs_volume)
        except StopIteration:
            dose = dvh_np[-1]
        doses.append(dose)

    return doses


def float_or_none(value):
    try:
        return float(value)
    except ValueError:
        return 'None'


class MessageDialog:
    """
    This is the base class for Yes/No Dialog boxes
    Inherit this class, then over-write action_yes and action_no functions with appropriate behaviors
    """
    def __init__(self, parent, caption, message="Are you sure?", action_yes_func=None, action_no_func=None,
                 flags=wx.ICON_WARNING | wx.YES | wx.NO | wx.NO_DEFAULT):
        if is_windows():
            message = '\n'.join([caption, message])
            caption = ' '
        self.dlg = wx.MessageDialog(parent, message, caption, flags)
        self.parent = parent
        self.action_yes_func = action_yes_func
        self.action_no_func = action_no_func
        self.run()

    def run(self):
        res = self.dlg.ShowModal()
        [self.action_no, self.action_yes][res == wx.ID_YES]()
        self.dlg.Destroy()

    def action_yes(self):
        if self.action_yes_func is not None:
            self.action_yes_func()

    def action_no(self):
        if self.action_no_func is not None:
            self.action_no_func()


def save_object_to_file(obj, abs_file_path):
    """
    Save a python object acceptable for pickle to the provided file path
    """
    with open(abs_file_path, 'wb') as outfile:
        pickle.dump(obj, outfile)


def load_object_from_file(abs_file_path):
    """
    Load a pickled object from the provided absolute file path
    """
    if isfile(abs_file_path):
        with open(abs_file_path, 'rb') as infile:
            obj = pickle.load(infile)
        return obj


def sample_list(some_list, max_size, n):
    """
    Reduce a list by given factor iteratively until list size less than max_size
    :param some_list: any list you like!
    :type some_list: list
    :param max_size: the maximum number of items in the returned list
    :type max_size: int
    :param n: remove every nth element
    :type n: int
    :return: sampled list
    :rtype: list
    """
    while len(some_list) > max_size:
        some_list = remove_every_nth_element(some_list, n)
    return some_list


def remove_every_nth_element(some_list, n):
    return [value for i, value in enumerate(some_list) if i % n != 0]


def sample_roi(roi_coord, max_point_count=5000, iterative_reduction=0.1):
    """
    Iteratively sample a list of 3D points by the iterative_reduction until the size of the list is < max_point_count
    This is used to reduce the number of points used in the ptv distance calculations because:
        1) Shapely returns a much large number of points when calculating total PTVs
        2) Users could easily run into memory issues using scip.dist if all points are used (particularly on MSW)
    :param roi_coord: a list of 3D points representing an roi
    :type roi_coord: list
    :param max_point_count: the maximum number of points in the returned roi_coord
    :type max_point_count: int
    :param iterative_reduction: iteratively remove this fraction of points until len < max_point_count
    :type iterative_reduction: float
    :return: sampled roi
    :rtype: list
    """
    return sample_list(roi_coord, max_point_count, int(1 / iterative_reduction))


def get_sorted_indices(some_list):
    try:
        return [i[0] for i in sorted(enumerate(some_list), key=lambda x: x[1])]
    except TypeError:  # can't sort if a mix of str and float
        try:
            temp_data = [[value, -float('inf')][value == 'None'] for value in some_list]
            return [i[0] for i in sorted(enumerate(temp_data), key=lambda x: x[1])]
        except TypeError:
            temp_data = [str(value) for value in some_list]
            return [i[0] for i in sorted(enumerate(temp_data), key=lambda x: x[1])]


def get_window_size(width, height):
    """
    Function used to adapt frames/windows for the user's resolution
    :param width: fractional width of the user's screen
    :param height: fractional height of the user's screen
    :return: window size
    :rtype: tuple
    """
    user_width, user_height = wx.GetDisplaySize()
    if user_width / user_height < 1.5:  # catch 4:3 or non-widescreen
        user_height = user_width / 1.6
    return tuple([int(width * user_width), int(height * user_height)])


def set_frame_icon(frame):
    if not is_mac():
        frame.SetIcon(wx.Icon(WIN_APP_ICON))


def trace_memory_alloc_pretty_top(snapshot, key_type='lineno', limit=10):
    """From https://docs.python.org/3/library/tracemalloc.html"""
    print('-----------------------------------------------------------------')
    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<unknown>"),
    ))
    top_stats = snapshot.statistics(key_type)

    print("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = sep.join(frame.filename.split(sep)[-2:])
        print("#%s: %s:%s: %.1f KiB"
              % (index, filename, frame.lineno, stat.size / 1024))
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print('    %s' % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f KiB" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f KiB" % (total / 1024))


def trace_memory_alloc_simple_stats(snapshot, key_type='lineno'):
    """From https://docs.python.org/3/library/tracemalloc.html"""
    print('-----------------------------------------------------------------')
    print("[ Top 10 ]")
    top_stats = snapshot.statistics(key_type)
    for stat in top_stats[:10]:
        print(stat)


class PopupMenu:
    def __init__(self, parent):
        self.parent = parent
        self.menus = []

    def add_menu_item(self, label, action):
        self.menus.append({'id': wx.NewId(), 'label': label, 'action': action})

    def run(self):
        popup_menu = wx.Menu()
        for menu in self.menus:
            popup_menu.Append(menu['id'], menu['label'])
            self.parent.Bind(wx.EVT_MENU, menu['action'], id=menu['id'])

        self.parent.PopupMenu(popup_menu)
        popup_menu.Destroy()


def validate_transfer_syntax_uid(data_set):
    meta = pydicom.Dataset()
    meta.ImplementationClassUID = pydicom.uid.generate_uid()
    meta.TransferSyntaxUID = ImplicitVRLittleEndian
    new_data_set = pydicom.FileDataset(filename_or_obj=None, dataset=data_set, is_little_endian=True,
                                       file_meta=meta)
    new_data_set.is_little_endian = True
    new_data_set.is_implicit_VR = True

    return new_data_set


def get_installed_python_libraries():
    """Use pip command line function 'list' to extract the currently installed libraries"""

    try:
        output = str(check_output(['pip', 'list', '--local']), 'utf-8').split('\n')
    except Exception:
        # If running from PyInstaller, this will fail, pickle a file prior to freezing with save_pip_list
        return load_object_from_file(PIP_LIST_PATH)

    python_version = '.'.join(str(i) for i in sys.version_info[:3])
    libraries = {'Library': ['python'], 'Version': [python_version]}
    for row in output[2:]:  # ignore first two rows which are column headers and a separator
        data = [v for v in row.strip().split(' ') if v]
        if data:
            libraries['Library'].append(data[0])
            libraries['Version'].append(data[1])
    return libraries


def save_pip_list():
    save_object_to_file(get_installed_python_libraries(), PIP_LIST_PATH)


def get_wildcards(extensions):
    if type(extensions) is not list:
        extensions = [extensions]
    return '|'.join(["%s (*.%s)|*.%s" % (ext.upper(), ext, ext) for ext in extensions])


FIG_WILDCARDS = get_wildcards(['svg', 'html', 'png'])


def set_phantom_js_in_path():
    bundle_dir = getattr(sys, '_MEIPASS', None)
    phantom_js_path = APP_DIR if bundle_dir is None else bundle_dir

    if phantom_js_path not in environ["PATH"]:
        environ["PATH"] += pathsep + phantom_js_path


def backup_sqlite_db(options):
    if options.DB_TYPE == 'sqlite':
        db_file_name = basename(options.DEFAULT_CNF['sqlite']['host'])
        file_append = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        new_file_name = splitext(db_file_name)[0] + '_' + file_append + '.db'
        db_file_path = join(DATA_DIR, db_file_name)

        # check if stored file_path is an absolute path
        if not isfile(db_file_path):
            db_file_path = options.DEFAULT_CNF['sqlite']['host']
            if not isfile(db_file_path):
                db_file_path = None

        if db_file_path is not None:
            move_files_to_new_path([db_file_path], BACKUP_DIR, copy_files=True, new_file_names=[new_file_name])

            return [db_file_path, join(BACKUP_DIR, new_file_name)]
