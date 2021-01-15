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
import wx.html2 as webview
from datetime import datetime
from dateutil.parser import parse as parse_date
import linecache
import numpy as np
from os import walk, listdir, unlink, mkdir, rmdir, chdir, sep, environ
from os.path import (
    join,
    isfile,
    isdir,
    splitext,
    basename,
    dirname,
    realpath,
    pathsep,
)
import pickle
import pydicom
from pydicom.uid import ImplicitVRLittleEndian
import shutil
from subprocess import check_output
import sys
import tracemalloc
from dvha.db.sql_connector import DVH_SQL
from dvha.paths import (
    SQL_CNF_PATH,
    WIN_APP_ICON,
    PIP_LIST_PATH,
    DIRECTORIES,
    APP_DIR,
    BACKUP_DIR,
    DATA_DIR,
)
from dvha.tools.errors import push_to_log


IGNORED_FILES = [".ds_store"]

if environ.get("READTHEDOCS") == "True" or "sphinx" in sys.prefix:
    MSG_DLG_FLAGS = None
else:
    MSG_DLG_FLAGS = wx.ICON_WARNING | wx.YES | wx.NO | wx.NO_DEFAULT


def is_windows():
    """ """
    return wx.Platform == "__WXMSW__"


def set_msw_background_color(window_obj, color="lightgrey"):
    """

    Parameters
    ----------
    window_obj :

    color :
         (Default value = 'lightgrey')

    Returns
    -------

    """
    if is_windows():
        window_obj.SetBackgroundColour(color)


def is_linux():
    """ """
    return wx.Platform == "__WXGTK__"


def is_mac():
    """ """
    return wx.Platform == "__WXMAC__"


def initialize_directories():
    """Based on paths.py, create required directories if they do not exist"""
    for directory in DIRECTORIES.values():
        if not isdir(directory):
            mkdir(directory)


def write_sql_connection_settings(config):
    """Create a file storing the SQL login credentials

    Parameters
    ----------
    config : dict
        contains values for 'host', 'dbname', 'port' and optionally 'user' and 'password'

    Returns
    -------

    """
    # TODO: Make this more secure

    text = ["%s %s" % (key, value) for key, value in config.items() if value]
    text = "\n".join(text)

    with open(SQL_CNF_PATH, "w") as text_file:
        text_file.write(text)


def scale_bitmap(bitmap, width, height):
    """Used to scale tool bar images for MSW and GTK, MAC automatically scales

    Parameters
    ----------
    bitmap :
        bitmap to be scaled
        type bitmap: Bitmap
    width : int
        width of output bitmap
    height : int
        height of output bitmap

    Returns
    -------
    Bitmap
        scaled bitmap

    """
    image = wx.Bitmap.ConvertToImage(bitmap)
    image = image.Scale(width, height, wx.IMAGE_QUALITY_HIGH)
    return wx.Bitmap(image)


def get_tree_ctrl_image(
    file_path, file_type=wx.BITMAP_TYPE_PNG, width=16, height=16
):
    """Create an image top be used in the TreeCtrl from the provided file_path

    Parameters
    ----------
    file_path : str
        absolute file_path of image
    file_type :
        specify the image format (PNG by default)
    width : int
        width of output bitmap (16 default)
    height : int
        height of output bitmap (16 default)

    Returns
    -------
    Image
        scaled image for TreeCtrl

    """
    return (
        wx.Image(file_path, file_type).Scale(width, height).ConvertToBitmap()
    )


def get_file_paths(
    start_path, search_subfolders=False, extension=None, return_dict=False
):
    """Get a list of absolute file paths for a given directory

    Parameters
    ----------
    start_path : str
        initial directory
    search_subfolders : bool
        optionally search all sub folders (Default value = False)
    extension : str
        optionally include only files with specified extension (Default value = None)
    return_dict :
         (Default value = False)

    Returns
    -------
    list or dict
        absolute file paths

    """
    if isdir(start_path):
        file_paths = []
        file_paths_dict = {}
        if search_subfolders:
            for root, dirs, files in walk(start_path, topdown=False):
                for name in files:
                    if (
                        extension is None
                        or splitext(name)[1].lower() == extension.lower()
                    ):
                        if name.lower() not in IGNORED_FILES:
                            file_paths.append(join(root, name))
                            if return_dict:
                                if root not in file_paths_dict.keys():
                                    file_paths_dict[root] = []
                                file_paths_dict[root].append(name)
            if return_dict:
                return file_paths_dict
            return file_paths

        for f in listdir(start_path):
            if isfile(join(start_path, f)):
                if (
                    extension is None
                    or splitext(f)[1].lower() == extension.lower()
                ):
                    if f.lower() not in IGNORED_FILES:
                        file_paths.append(join(start_path, f))
        return file_paths
    return []


def get_study_instance_uids(**kwargs):
    """Get lists of study instance uids in the SQL database that meet provided conditions
    The values return in the 'common' key are used for the DVH class in models.dvh.py

    Parameters
    ----------
    kwargs :
        keys are SQL table names and the values are conditions in SQL syntax
    **kwargs :


    Returns
    -------
    dict
        study instance uids for each table, uids found in all tables, and a list of unique uids

    """
    with DVH_SQL() as cnx:
        uids = {
            table: cnx.get_unique_values(
                table, "study_instance_uid", condition
            )
            for table, condition in kwargs.items()
        }

    complete_list = flatten_list_of_lists(
        list(uids.values()), remove_duplicates=True
    )

    uids["common"] = [
        uid for uid in complete_list if is_uid_in_all_keys(uid, uids)
    ]
    uids["unique"] = complete_list

    return uids


def is_uid_in_all_keys(uid, uids):
    """Check if uid is found in each of the uid lists for each SQL table

    Parameters
    ----------
    uid : str
        study instance uid
    uids : dict
        lists of study instance uids organized by SQL table

    Returns
    -------
    bool
        True only if uid is found in each of the tables

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
        if table not in "unique":
            final_answer *= value
    return final_answer


def flatten_list_of_lists(some_list, remove_duplicates=False, sort=False):
    """Convert a list of lists into a list of all values

    Parameters
    ----------
    some_list : list: list
        a list such that each value is a list
    remove_duplicates : bool
        if True, return a unique list, otherwise keep duplicated values (Default value = False)
    sort : bool
        if True, sort the list (Default value = False)

    Returns
    -------
    type
        a new object containing all values in teh provided

    """
    data = [item for sublist in some_list for item in sublist]

    if remove_duplicates:
        if sort:
            return list(set(data))
        else:
            ans = []
            for value in data:
                if value not in ans:
                    ans.append(value)
            return ans
    elif sort:
        return sorted(data)

    return data


def collapse_into_single_dates(x, y):
    """Function used for a time plot to convert multiple values into one value, while retaining enough information
    to perform a moving average over time

    Parameters
    ----------
    x :
        a list of dates in ascending order
    y :
        a list of values and can use the '+' operator as a function of date

    Returns
    -------
    dict
        a unique list of dates, sum of y for that date, and number of original points for that date

    """

    # average daily data and keep track of points per day
    x_collapsed = [x[0]]
    y_collapsed = [y[0]]
    w_collapsed = [1]
    for n in range(1, len(x)):
        if x[n] == x_collapsed[-1]:
            y_collapsed[-1] = y_collapsed[-1] + y[n]
            w_collapsed[-1] += 1
        else:
            x_collapsed.append(x[n])
            y_collapsed.append(y[n])
            w_collapsed.append(1)

    return {"x": x_collapsed, "y": y_collapsed, "w": w_collapsed}


def moving_avg(xyw, avg_len):
    """Calculate a moving average for a given averaging length

    Parameters
    ----------
    xyw : dict
        output from collapse_into_single_dates
    avg_len : int
        average of these number of points, i.e., look-back window

    Returns
    -------
    tuple
        list of x values, list of y values

    """
    cumsum, moving_aves, x_final = [0], [], []

    for i, y in enumerate(xyw["y"], 1):
        cumsum.append(cumsum[i - 1] + y / xyw["w"][i - 1])
        if i >= avg_len:
            moving_ave = (cumsum[i] - cumsum[i - avg_len]) / avg_len
            moving_aves.append(moving_ave)
    x_final = [xyw["x"][i] for i in range(avg_len - 1, len(xyw["x"]))]

    return x_final, moving_aves


def convert_value_to_str(value, rounding_digits=2):
    """

    Parameters
    ----------
    value :

    rounding_digits :
         (Default value = 2)

    Returns
    -------

    """
    try:
        formatter = "%%0.%df" % rounding_digits
        return formatter % value
    except TypeError:
        return value


def get_selected_listctrl_items(list_control):
    """Get the indices of the currently selected items of a wx.ListCtrl object

    Parameters
    ----------
    list_control : ListCtrl
        any wx.ListCtrl object

    Returns
    -------
    list
        indices of selected items

    """
    selection = []

    index_current = -1
    while True:
        index_next = list_control.GetNextItem(
            index_current, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED
        )
        if index_next == -1:
            return selection

        selection.append(index_next)
        index_current = index_next


def print_run_time(start_time, end_time, calc_title):
    """

    Parameters
    ----------
    start_time : datetime
        start time of process
    end_time : datetime
        end time of process
    calc_title : str
        prepend the status message with this value

    Returns
    -------

    """
    total_time = end_time - start_time
    seconds = total_time.seconds
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        print(
            "%s. This took %dhrs %02dmin %02dsec to complete"
            % (calc_title, h, m, s)
        )
    elif m:
        print("%s. This took %02dmin %02dsec to complete" % (calc_title, m, s))
    else:
        print("%s. This took %02dsec to complete" % (calc_title, s))


def datetime_to_date_string(datetime_obj):
    """

    Parameters
    ----------
    datetime_obj :


    Returns
    -------

    """
    if isinstance(datetime_obj, str):
        datetime_obj = parse_date(datetime_obj)
    return "%s/%s/%s" % (
        datetime_obj.month,
        datetime_obj.day,
        datetime_obj.year,
    )


def change_angle_origin(angles, max_positive_angle):
    """Angles in DICOM are all positive values, but there is typically no mechanical continuity in across 180 degrees

    Parameters
    ----------
    angles : list
        angles to be converted
    max_positive_angle :
        the maximum positive angle, angles greater than this will be shifted to negative angles

    Returns
    -------
    list
        list of the same angles, but none exceed the max

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
    """Calculate a standard set of stats for DVHA

    Parameters
    ----------
    data : list
        a list or numpy 1D array of numbers

    Returns
    -------
    list
        max, 75%, median, mean, 25%, and min of data

    """
    data = [x for x in data if x != "None"]
    try:
        data_np = np.array(data)
        rtn_data = [
            np.max(data_np),
            np.percentile(data_np, 75),
            np.median(data_np),
            np.mean(data_np),
            np.percentile(data_np, 25),
            np.min(data_np),
        ]
    except Exception as e:
        rtn_data = [0, 0, 0, 0, 0, 0]
        msg = "tools.utilities.calc_stats: received non-numerical data"
        push_to_log(e, msg=msg)
    return rtn_data


def move_files_to_new_path(
    files, new_dir, copy_files=False, new_file_names=None, callback=None
):
    """Move all files provided to the new directory

    Parameters
    ----------
    files : list
        absolute file paths
    new_dir : str
        absolute directory path
    copy_files : bool
        Set to True to keep original files and copy to new_dir, False to remove original files (Default value = False)
    new_file_names : None or list of str
        optionally provide a list of new names (Default value = None)
    callback : callable
        optional function to call at the start of each iteration (Default value = None)

    Returns
    -------

    """
    for i, file_path in enumerate(files):
        if callback is not None:
            callback(i, len(files))
        if isfile(file_path):
            file_name = basename(file_path)
            old_dir = dirname(file_path)
            new_file_name = (
                file_name if new_file_names is None else new_file_names[i]
            )
            new = join(new_dir, new_file_name)
            if not isdir(new_dir):
                mkdir(new_dir)
            if old_dir != new_dir:
                if isfile(new):
                    if not copy_files:
                        delete_file(new)
                else:
                    [shutil.move, shutil.copy][copy_files](file_path, new)


def delete_directory_contents(dir_to_delete):
    """

    Parameters
    ----------
    dir_to_delete :


    Returns
    -------

    """
    # https://stackoverflow.com/questions/185936/how-to-delete-the-contents-of-a-folder-in-python
    for the_file in listdir(dir_to_delete):
        delete_file(join(dir_to_delete, the_file))


def delete_file(file_path):
    """

    Parameters
    ----------
    file_path :


    Returns
    -------

    """
    try:
        if isfile(file_path):
            unlink(file_path)
        elif isdir(file_path):
            shutil.rmtree(file_path)
    except Exception as e:
        push_to_log(e, msg="tools.utilities.delete_file: %s" % file_path)


def delete_imported_dicom_files(dicom_files):
    """delete imported dicom files

    Parameters
    ----------
    dicom_files : dict
        the return from DVH_SQL().get_dicom_file_paths

    Returns
    -------

    """
    for i, directory in enumerate(dicom_files["folder_path"]):
        # Delete associated plan, structure, and dose files
        for key in ["plan_file", "structure_file", "dose_file"]:
            delete_file(join(directory, dicom_files[key][i]))

        # Delete misc dicom files for given study instance uid
        remaining_files = listdir(directory)
        for f in remaining_files:
            try:
                uid = str(
                    pydicom.read_file(join(directory, f)).StudyInstanceUID
                )
                if uid == str(dicom_files["study_instance_uid"][i]):
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
    """move imported dicom files

    Parameters
    ----------
    dicom_files : dict
        the return from DVH_SQL().get_dicom_file_paths
    new_dir :


    Returns
    -------

    """
    for i, directory in enumerate(dicom_files["folder_path"]):
        files = [
            join(directory, dicom_files[key][i])
            for key in ["plan_file", "structure_file", "dose_file"]
        ]
        new_patient_dir = join(new_dir, dicom_files["mrn"][i])
        move_files_to_new_path(files, new_patient_dir)

        # Move misc dicom files for given study instance uid
        remaining_files = listdir(directory)
        files = []
        for f in remaining_files:
            try:
                uid = str(
                    pydicom.read_file(join(directory, f)).StudyInstanceUID
                )
                if uid == str(dicom_files["study_instance_uid"][i]):
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
    """

    Parameters
    ----------
    start_path :


    Returns
    -------

    """
    for (path, dirs, files) in walk(start_path, topdown=False):
        if files:
            continue
        try:
            if path != start_path:
                rmdir(path)
        except OSError:
            pass


def move_all_files(new_dir, old_dir):
    """This function will move all files from the old to new directory, it will ignore all files in subdirectories

    Parameters
    ----------
    new_dir :
        absolute directory path
    old_dir :
        absolute directory path

    Returns
    -------

    """
    initial_path = dirname(realpath(__file__))

    chdir(old_dir)

    file_paths = [f for f in listdir(old_dir) if isfile(join(old_dir, f))]

    misc_path = join(new_dir, "misc")
    if not isdir(misc_path):
        mkdir(misc_path)

    for f in file_paths:
        file_name = basename(f)
        new = join(misc_path, file_name)
        shutil.move(f, new)

    chdir(initial_path)


def get_elapsed_time(start_time, end_time):
    """

    Parameters
    ----------
    start_time :

    end_time :


    Returns
    -------

    """
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
    """

    Parameters
    ----------
    date :


    Returns
    -------

    """
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
    """Determine the order of provided PTVs by their D_95% values

    Parameters
    ----------
    ptvs : dict
        dvh, volume, index of PTVs

    Returns
    -------
    type
        ptv numbers in order of D_95%

    """
    doses_to_rank = get_dose_to_volume(ptvs["dvh"], ptvs["volume"], 0.95)
    return sorted(range(len(ptvs["dvh"])), key=lambda k: doses_to_rank[k])


def get_dose_to_volume(dvhs, volumes, roi_fraction):
    """

    Parameters
    ----------
    dvhs :

    volumes :

    roi_fraction :


    Returns
    -------

    """
    # Not precise (i.e., no interpolation) but good enough for sorting PTVs
    doses = []
    for i, dvh in enumerate(dvhs):
        abs_volume = volumes[i] * roi_fraction
        dvh_np = np.array(dvh.split(","), dtype=np.float)
        try:
            dose = next(x[0] for x in enumerate(dvh_np) if x[1] < abs_volume)
        except StopIteration:
            dose = dvh_np[-1]
        doses.append(dose)

    return doses


def float_or_none(value):
    """

    Parameters
    ----------
    value :


    Returns
    -------

    """
    try:
        return float(value)
    except ValueError:
        return "None"


class MessageDialog:
    """This is the base class for Yes/No Dialog boxes
    Inherit this class, then over-write action_yes and action_no functions with appropriate behaviors

    Parameters
    ----------

    Returns
    -------

    """

    def __init__(
        self,
        parent,
        caption,
        message="Are you sure?",
        action_yes_func=None,
        action_no_func=None,
        flags=MSG_DLG_FLAGS,
    ):
        if is_windows():
            message = "\n".join([caption, message])
            caption = " "
        self.dlg = wx.MessageDialog(parent, message, caption, flags)
        self.parent = parent
        self.action_yes_func = action_yes_func
        self.action_no_func = action_no_func
        self.run()

    def run(self):
        """ """
        res = self.dlg.ShowModal()
        [self.action_no, self.action_yes][res == wx.ID_YES]()
        self.dlg.Destroy()

    def action_yes(self):
        """ """
        if self.action_yes_func is not None:
            self.action_yes_func()

    def action_no(self):
        """ """
        if self.action_no_func is not None:
            self.action_no_func()


def save_object_to_file(obj, abs_file_path):
    """Save a python object acceptable for pickle to the provided file path

    Parameters
    ----------
    obj :

    abs_file_path :


    Returns
    -------

    """
    with open(abs_file_path, "wb") as outfile:
        pickle.dump(obj, outfile)


def load_object_from_file(abs_file_path):
    """Load a pickled object from the provided absolute file path

    Parameters
    ----------
    abs_file_path :


    Returns
    -------

    """
    if isfile(abs_file_path):
        with open(abs_file_path, "rb") as infile:
            obj = pickle.load(infile)
        return obj


def sample_list(some_list, max_size, n):
    """Reduce a list by given factor iteratively until list size less than max_size

    Parameters
    ----------
    some_list : list: list
        any list you like!
    max_size : int
        the maximum number of items in the returned list
    n : int
        remove every nth element

    Returns
    -------
    list
        sampled list

    """
    while len(some_list) > max_size:
        some_list = remove_every_nth_element(some_list, n)
    return some_list


def remove_every_nth_element(some_list, n):
    """

    Parameters
    ----------
    some_list :

    n :


    Returns
    -------

    """
    return [value for i, value in enumerate(some_list) if i % n != 0]


def sample_roi(roi_coord, max_point_count=5000, iterative_reduction=0.1):
    """Iteratively sample a list of 3D points by the iterative_reduction until the size of the list is < max_point_count
    This is used to reduce the number of points used in the ptv distance calculations because:
    1) Shapely returns a much large number of points when calculating total PTVs
    2) Users could easily run into memory issues using scip.dist if all points are used (particularly on MSW)

    Parameters
    ----------
    roi_coord : list
        a list of 3D points representing an roi
    max_point_count : int_count: int
        the maximum number of points in the returned roi_coord (Default value = 5000)
    iterative_reduction : float
        iteratively remove this fraction of points until len < max_point_count (Default value = 0.1)

    Returns
    -------
    list
        sampled roi

    """
    return sample_list(
        roi_coord, max_point_count, int(1 / iterative_reduction)
    )


def get_sorted_indices(some_list):
    """

    Parameters
    ----------
    some_list :


    Returns
    -------

    """
    try:
        return [i[0] for i in sorted(enumerate(some_list), key=lambda x: x[1])]
    except TypeError:  # can't sort if a mix of str and float
        try:
            temp_data = [
                [value, -float("inf")][value == "None"] for value in some_list
            ]
            return [
                i[0] for i in sorted(enumerate(temp_data), key=lambda x: x[1])
            ]
        except TypeError:
            temp_data = [str(value) for value in some_list]
            return [
                i[0] for i in sorted(enumerate(temp_data), key=lambda x: x[1])
            ]


def get_window_size(width, height):
    """Function used to adapt frames/windows for the user's resolution

    Parameters
    ----------
    width :
        fractional width of the user's screen
    height :
        fractional height of the user's screen

    Returns
    -------
    tuple
        window size

    """
    user_width, user_height = wx.GetDisplaySize()
    if user_width / user_height < 1.5:  # catch 4:3 or non-widescreen
        user_height = user_width / 1.6
    return tuple([int(width * user_width), int(height * user_height)])


def apply_resolution_limits(size, options):
    """Apply min and max limits to a window size

    Parameters
    ----------
    size : tuple
        window size (width, height)
    options : Options
        dvha.options.Options class object

    Returns
    -------
    tuple
        width, height
    """

    min_size = options.MIN_RESOLUTION_MAIN
    max_size = options.MAX_INIT_RESOLUTION_MAIN
    return tuple([min(max(size[i], min_size[i]), max_size[i]) for i in [0, 1]])


def set_frame_icon(frame):
    """

    Parameters
    ----------
    frame :


    Returns
    -------

    """
    if not is_mac():
        frame.SetIcon(wx.Icon(WIN_APP_ICON))


def trace_memory_alloc_pretty_top(snapshot, key_type="lineno", limit=10):
    """From https://docs.python.org/3/library/tracemalloc.html

    Parameters
    ----------
    snapshot :

    key_type :
         (Default value = 'lineno')
    limit :
         (Default value = 10)

    Returns
    -------

    """
    print("-----------------------------------------------------------------")
    snapshot = snapshot.filter_traces(
        (
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<unknown>"),
        )
    )
    top_stats = snapshot.statistics(key_type)

    print("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = sep.join(frame.filename.split(sep)[-2:])
        print(
            "#%s: %s:%s: %.1f KiB"
            % (index, filename, frame.lineno, stat.size / 1024)
        )
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print("    %s" % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f KiB" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f KiB" % (total / 1024))


def trace_memory_alloc_simple_stats(snapshot, key_type="lineno"):
    """From https://docs.python.org/3/library/tracemalloc.html

    Parameters
    ----------
    snapshot :

    key_type :
         (Default value = 'lineno')

    Returns
    -------

    """
    print("-----------------------------------------------------------------")
    print("[ Top 10 ]")
    top_stats = snapshot.statistics(key_type)
    for stat in top_stats[:10]:
        print(stat)


class PopupMenu:
    """ """

    def __init__(self, parent):
        self.parent = parent
        self.menus = []

    def add_menu_item(self, label, action):
        """

        Parameters
        ----------
        label :

        action :


        Returns
        -------

        """
        self.menus.append({"id": wx.NewId(), "label": label, "action": action})

    def run(self):
        """ """
        popup_menu = wx.Menu()
        for menu in self.menus:
            popup_menu.Append(menu["id"], menu["label"])
            self.parent.Bind(wx.EVT_MENU, menu["action"], id=menu["id"])

        self.parent.PopupMenu(popup_menu)
        popup_menu.Destroy()


def validate_transfer_syntax_uid(data_set):
    """

    Parameters
    ----------
    data_set :


    Returns
    -------

    """
    meta = pydicom.Dataset()
    meta.ImplementationClassUID = pydicom.uid.generate_uid()
    meta.TransferSyntaxUID = ImplicitVRLittleEndian
    new_data_set = pydicom.FileDataset(
        filename_or_obj=None,
        dataset=data_set,
        is_little_endian=True,
        file_meta=meta,
    )
    new_data_set.is_little_endian = True
    new_data_set.is_implicit_VR = True

    return new_data_set


def get_installed_python_libraries():
    """Use pip command line function 'list' to extract the currently installed libraries"""

    if isfile(PIP_LIST_PATH):  # Load a frozen list of packages if stored
        return load_object_from_file(PIP_LIST_PATH)
    try:  # If running from PyInstaller, this may fail, pickle a file prior to freezing with save_pip_list
        output = str(check_output(["pip", "list", "--local"]), "utf-8").split(
            "\n"
        )
    except Exception:
        return load_object_from_file(PIP_LIST_PATH)

    python_version = ".".join(str(i) for i in sys.version_info[:3])
    libraries = {"Library": ["python"], "Version": [python_version]}
    for row in output[
        2:
    ]:  # ignore first two rows which are column headers and a separator
        data = [v for v in row.strip().split(" ") if v]
        if data:
            libraries["Library"].append(data[0])
            libraries["Version"].append(data[1])
    return libraries


def save_pip_list():
    """ """
    save_object_to_file(get_installed_python_libraries(), PIP_LIST_PATH)


def get_wildcards(extensions):
    """

    Parameters
    ----------
    extensions :


    Returns
    -------

    """
    if type(extensions) is not list:
        extensions = [extensions]
    return "|".join(
        ["%s (*.%s)|*.%s" % (ext.upper(), ext, ext) for ext in extensions]
    )


FIG_WILDCARDS = get_wildcards(["svg", "html", "png"])


def set_phantom_js_in_path():
    """ """
    bundle_dir = getattr(sys, "_MEIPASS", None)
    phantom_js_path = APP_DIR if bundle_dir is None else bundle_dir

    if phantom_js_path not in environ["PATH"]:
        environ["PATH"] += pathsep + phantom_js_path


def backup_sqlite_db(options):
    """

    Parameters
    ----------
    options :


    Returns
    -------

    """
    if options.DB_TYPE == "sqlite":
        db_file_name = basename(options.DEFAULT_CNF["sqlite"]["host"])
        file_append = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        new_file_name = splitext(db_file_name)[0] + "_" + file_append + ".db"
        db_file_path = join(DATA_DIR, db_file_name)

        # check if stored file_path is an absolute path
        if not isfile(db_file_path):
            db_file_path = options.DEFAULT_CNF["sqlite"]["host"]
            if not isfile(db_file_path):
                db_file_path = None

        if db_file_path is not None:
            move_files_to_new_path(
                [db_file_path],
                BACKUP_DIR,
                copy_files=True,
                new_file_names=[new_file_name],
            )

            return [db_file_path, join(BACKUP_DIR, new_file_name)]


def main_is_frozen():
    """ """
    # https://pyinstaller.readthedocs.io/en/stable/runtime-information.html
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_xy_path_lengths(shapely_object):
    """Get the x and y path lengths of a a Shapely object

    Parameters
    ----------
    shapely_object :
        either 'GeometryCollection', 'MultiPolygon', or 'Polygon'

    Returns
    -------
    list
        path lengths in the x and y directions

    """
    path = np.array([0.0, 0.0])
    if shapely_object.type == "GeometryCollection":
        for geometry in shapely_object.geoms:
            if geometry.type in {"MultiPolygon", "Polygon"}:
                path = np.add(path, get_xy_path_lengths(geometry))
    elif shapely_object.type == "MultiPolygon":
        for shape in shapely_object:
            path = np.add(path, get_xy_path_lengths(shape))
    elif shapely_object.type == "Polygon":
        x, y = np.array(shapely_object.exterior.xy[0]), np.array(
            shapely_object.exterior.xy[1]
        )
        path = np.array(
            [np.sum(np.abs(np.diff(x))), np.sum(np.abs(np.diff(y)))]
        )

    return path.tolist()


def recalculate_plan_complexities_from_beams():
    """ """
    with DVH_SQL() as cnx:
        uids = cnx.get_unique_values("Plans", "study_instance_uid")

        for uid in uids:
            try:
                condition = "study_instance_uid = '%s'" % uid
                beam_complexities = cnx.query(
                    "Beams", "fx_count, complexity, fx_grp_number", condition
                )
                complexity = {}
                fx_counts = {}
                for row in beam_complexities:
                    fx_count, beam_complexity, fx_group_number = tuple(row)
                    if fx_group_number not in complexity:
                        complexity[fx_group_number] = 0.0
                        fx_counts[fx_group_number] = fx_count
                    complexity[fx_group_number] += beam_complexity

                total_fx = float(sum([fx for fx in fx_counts.values()]))
                plan_complexity = (
                    sum(
                        [
                            c * fx_counts[fx_grp]
                            for fx_grp, c in complexity.items()
                        ]
                    )
                    / total_fx
                )
            except Exception as e:
                msg = (
                    "tools.utilities.recalculate_plan_complexities_from_beams: failed on uid = %s"
                    % uid
                )
                push_to_log(e, msg=msg)
                plan_complexity = None

            if plan_complexity is not None:
                cnx.update("Plans", "complexity", plan_complexity, condition)


def get_new_uid(used_uids=None):
    """Get a new UID using pydicom

    Parameters
    ----------
    used_uids : list
        Do not return a UID that is in this list (Default value = None)

    Returns
    -------
    str
        A new UID not found in the current DVHA database or in the used_uids

    """
    uid_found = False
    used_uids = [] if used_uids is None else used_uids
    with DVH_SQL() as cnx:
        while not uid_found:
            uid = pydicom.uid.generate_uid()
            uid_found = not cnx.is_uid_imported(uid) and uid not in used_uids
    return uid


def get_new_uids_by_directory(start_path):
    """Generate new StudyInstanceUIDs, assuming all DICOM files in a directory are matched

    Parameters
    ----------
    start_path : str
        initial directory

    Returns
    -------
    dict, list
        New UIDs by directory, queue

    """
    file_paths = get_file_paths(
        start_path, search_subfolders=True, return_dict=True
    )
    study_uids = {}
    queue = []
    for directory, files in file_paths.items():
        uid = get_new_uid(used_uids=list(study_uids.values()))
        study_uids[directory] = uid
        for file in files:
            queue.append(
                {"abs_file_path": join(directory, file), "study_uid": uid}
            )

    return study_uids, queue


def edit_study_uid(abs_file_path, study_uid):
    """Change the StudyInstanceUID of a DICOM file

    Parameters
    ----------
    abs_file_path :
        absolute file path of the DICOM file
    study_uid :
        new StudyInstanceUID

    Returns
    -------

    """
    try:
        ds = pydicom.read_file(abs_file_path, force=True)
        ds.StudyInstanceUID = study_uid
        ds.save_as(abs_file_path)
    except Exception as e:
        push_to_log(e, abs_file_path)


def get_csv_row(data, columns, delimiter=","):
    """Convert a dictionary of data into a row for a csv file

    Parameters
    ----------
    data : dict
        a dictionary with values with str representations
    columns : list
        a list of keys dictating the order of the csv
    delimiter : str
        Optionally use the provided delimiter rather than a comma (Default value = ")
    " :


    Returns
    -------


    """
    str_data = [str(data[c]) for c in columns]
    clean_str_data = ['"%s"' % s if delimiter in s else s for s in str_data]
    clean_str_data = [s.replace("\n", "<>") for s in clean_str_data]
    return delimiter.join(clean_str_data)


def csv_to_list(csv_str, delimiter=","):
    """Split a CSV into a list

    Parameters
    ----------
    csv_str : str
        A comma-separated value string (with double quotes around values
        containing the delimiter)
    delimiter : str
        The str separator between values (Default value = ")
    " :


    Returns
    -------


    """
    if '"' not in csv_str:
        return csv_str.split(delimiter)

    # add an empty value with another ",", but ignore it
    # ensures next_csv_element always finds a ","
    next_value, csv_str = next_csv_element(csv_str + ",", delimiter)
    ans = [next_value.replace("<>", "\n")]
    while csv_str:
        next_value, csv_str = next_csv_element(csv_str, delimiter)
        ans.append(next_value.replace("<>", "\n"))

    return ans


def next_csv_element(csv_str, delimiter=","):
    """Helper function for csv_to_list

    Parameters
    ----------
    csv_str : str
        A comma-separated value string (with double quotes around values
        containing the delimiter)
    delimiter : str
        The str separator between values (Default value = ")
    " :


    Returns
    -------


    """
    if csv_str.startswith('"'):
        split = csv_str[1:].find('"') + 1
        return csv_str[1:split], csv_str[split + 2 :]

    next_delimiter = csv_str.find(delimiter)
    return csv_str[:next_delimiter], csv_str[next_delimiter + 1 :]


def get_windows_webview_backend(include_edge=False):
    """Get the wx.html2 backend for MSW

    Returns
    -------
    dict
        wx.html2 backend id and name. Returns None if not MSW.
    """
    if is_windows():
        # WebView Backends
        backends = [
            (webview.WebViewBackendEdge, "WebViewBackendEdge"),
            (webview.WebViewBackendIE, "WebViewBackendIE"),
            (webview.WebViewBackendWebKit, "WebViewBackendWebKit"),
            (webview.WebViewBackendDefault, "WebViewBackendDefault"),
        ]
        if not include_edge:
            backends.pop(0)
        webview.WebView.MSWSetEmulationLevel(webview.WEBVIEWIE_EMU_IE11)
        for id, name in backends:
            if webview.WebView.IsBackendAvailable(id):
                return {"id": id, "name": name}


def is_edge_backend_available():
    """Check if WebViewBackendEdge is available

    Returns
    -------
    bool
        True if wx.html2.WebViewBackendEdge is available
    """
    if is_windows():
        return webview.WebView.IsBackendAvailable(webview.WebViewBackendEdge)
    return False
