#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Mar  2 22:15:52 2017

@author: nightowl
"""

import os
import shutil
from datetime import datetime
import pydicom as dicom
from db.dicom_parser import DVHTable, PlanRow, BeamTable, RxTable
from options import get_settings, parse_settings_file
from tools.utilities import print_run_time
from db.sql_connector import DVH_SQL


FILE_TYPES = {'rtplan', 'rtstruct', 'rtdose'}
SCRIPT_DIR = os.path.dirname(__file__)


def dicom_to_sql(start_path=None, force_update=False, move_files=True,
                 update_dicom_catalogue_table=True, import_latest_only=True):

    start_time = datetime.now()
    print(str(start_time), 'Beginning import', sep=' ')

    dicom_catalogue_update = []

    # Read SQL configuration file
    abs_file_path = get_settings('import')
    import_settings = parse_settings_file(abs_file_path)

    if start_path:
        abs_file_path = os.path.join(SCRIPT_DIR, start_path)
        import_settings['inbox'] = abs_file_path

    sqlcnx = DVH_SQL()

    file_paths = get_file_paths(import_settings['inbox'])

    for uid in list(file_paths):

        if is_uid_imported(uid):
            print("The UID from the following files is already imported.")
            if not force_update:
                print("Must delete content associated with this UID from database before reimporting.")
                print('WARNING: These files will remain in their current location.')
                for file_type in FILE_TYPES:
                    print(file_paths[uid][file_type]['file_path'])
                print("The UID is %s" % uid)
                continue

            else:
                print("Force Update set to True. Processing with import.")
                print("WARNING: This import may contain duplicate data already in the database.")

        dicom_catalogue_update.append(uid)

        # Collect and print the file paths
        plan_file = file_paths[uid]['rtplan']['latest_file']
        struct_file = file_paths[uid]['rtstruct']['latest_file']
        dose_file = file_paths[uid]['rtdose']['latest_file']
        if import_latest_only:
            print("plan file: %s" % plan_file)
        else:
            for f in file_paths[uid]['rtplan']['file_path']:
                print("plan file: %s" % f)
        print("struct file: %s" % struct_file)
        print("dose file: %s" % dose_file)

        # Process DICOM files into Python objects
        mp, ms, md = [], [], []
        if plan_file:
            try:
                mp = dicom.read_file(plan_file).ManufacturerModelName.lower()
            except AttributeError:
                mp = ''
        if struct_file:
            try:
                ms = dicom.read_file(struct_file).ManufacturerModelName.lower()
            except AttributeError:
                ms = ''
        if dose_file:
            try:
                md = dicom.read_file(dose_file).ManufacturerModelName.lower()
            except AttributeError:
                ''

        if 'gammaplan' in "%s %s %s" % (mp, ms, md):
            print("Leksell Gamma Plan is not currently supported. Skipping import.")
            continue

        if plan_file and struct_file and dose_file:
            if import_latest_only:
                plan = PlanRow(plan_file, struct_file, dose_file)
                sqlcnx.insert_plan(plan)
            else:
                for f in file_paths[uid]['rtplan']['file_path']:
                    plan = PlanRow(f, struct_file, dose_file)
                    sqlcnx.insert_plan(plan)
        else:
            print('WARNING: Missing complete set of plan, struct, and dose files for uid %s' % uid)
            if not force_update:
                print('WARNING: Skipping this import. If you wish to import an incomplete DICOM set, use Force Update')
                print('WARNING: Files with this UID will remain in their current location.')
                continue

        if plan_file:
            if not hasattr(dicom.read_file(plan_file), 'BrachyTreatmentType'):
                if import_latest_only:
                    beams = BeamTable(plan_file)
                    sqlcnx.insert_beams(beams)
                else:
                    for f in file_paths[uid]['rtplan']['file_path']:
                        sqlcnx.insert_beams(BeamTable(f))

        if struct_file and dose_file:
            dvhs = DVHTable(struct_file, dose_file)
            setattr(dvhs, 'ptv_number', rank_ptvs_by_D95(dvhs))
            sqlcnx.insert_dvhs(dvhs)
        if plan_file and struct_file:
            if import_latest_only:
                rxs = RxTable(plan_file, struct_file)
                sqlcnx.insert_rxs(rxs)
            else:
                for f in file_paths[uid]['rtplan']['file_path']:
                    sqlcnx.insert_rxs(RxTable(f, struct_file))

        # get mrn for folder name, can't assume a complete set of dose, plan, struct files
        mrn = []
        if dose_file:
            mrn = dicom.read_file(dose_file).PatientID
        elif plan_file:
            mrn = dicom.read_file(plan_file).PatientID
        elif struct_file:
            mrn = dicom.read_file(struct_file).PatientID
        if mrn:
            mrn = "".join(x for x in mrn if x.isalnum())  # remove any special characters
        else:
            mrn = 'NoMRN'

        # convert file_paths[uid] into a list of file paths
        new_folder = ''
        if move_files:
            files_to_move = []
            move_types = list(FILE_TYPES) + ['other']
            for file_type in move_types:
                files_to_move.extend(file_paths[uid][file_type]['file_path'])

            new_folder = os.path.join(import_settings['imported'], mrn)
            move_files_to_new_path(files_to_move, new_folder)

        if update_dicom_catalogue_table:
            if not import_latest_only:
                plan_file = ', '.join([os.path.basename(fp) for fp in file_paths[uid]['rtplan']['file_path']])
            if new_folder:
                if plan_file:
                    plan_file = os.path.basename(plan_file)
                if struct_file:
                    struct_file = os.path.basename(struct_file)
                if dose_file:
                    dose_file = os.path.basename(dose_file)
            update_dicom_catalogue(mrn, uid, new_folder, plan_file, struct_file, dose_file)

    # Move remaining files, if any
    if move_files:
        move_all_files(import_settings['imported'], import_settings['inbox'])
        remove_empty_folders(import_settings['inbox'])

    sqlcnx.close()

    end_time = datetime.now()
    print(str(end_time), 'Import complete', sep=' ')
    print_run_time(start_time, end_time, "This import")


def get_file_paths(start_path):
    print('Collecting DICOM file paths')
    start_time = datetime.now()
    f = []
    for root, dirs, files in os.walk(start_path, topdown=False):
        for name in files:
            f.append(os.path.join(root, name))

    # Collect all dicom files by UID, separate non-dicom files into misc
    file_paths = {}
    for file_path in f:
        try:
            dicom_file = dicom.read_file(file_path, defer_size='2KB', stop_before_pixels=True)
        except:
            dicom_file = False

        if dicom_file:
            uid = dicom_file.StudyInstanceUID
            file_type = dicom_file.Modality.lower()  # (rtplan, rtstruct, rtdose)
            timestamp = os.path.getmtime(file_path)

            if uid not in list(file_paths):
                file_paths[uid] = {'rtplan': {'file_path': [], 'timestamp': [], 'latest_file': []},
                                   'rtstruct': {'file_path': [], 'timestamp': [], 'latest_file': []},
                                   'rtdose': {'file_path': [], 'timestamp': [], 'latest_file': []},
                                   'other': {'file_path': [], 'timestamp': []}}

            if file_type not in FILE_TYPES:
                file_type = 'other'

            file_paths[uid][file_type]['file_path'].append(file_path)
            file_paths[uid][file_type]['timestamp'].append(timestamp)

    for uid in list(file_paths):
        for file_type in FILE_TYPES:
            latest_index, latest_time = [], []
            for i, ts in enumerate(file_paths[uid][file_type]['timestamp']):
                if not latest_time or ts > latest_time:
                    latest_index, latest_time = i, ts
            if isinstance(latest_index, int):
                file_paths[uid][file_type]['latest_file'] = file_paths[uid][file_type]['file_path'][latest_index]
            else:
                file_paths[uid][file_type]['latest_file'] = []
    end_time = datetime.now()
    print_run_time(start_time, end_time, 'DICOM file paths collected. This')
    return file_paths


def rebuild_database(start_path):

    DVH_SQL().reinitialize_database()
    print('Database reinitialized with no data.')
    print('Begin importing from data from %s' % start_path)
    dicom_to_sql(start_path=start_path)


def is_uid_imported(uid):

    for table in {'DVHs', 'Plans', 'Beams', 'Rxs'}:
        if DVH_SQL().is_study_instance_uid_in_table(table, uid):
            return True
    return False


def rank_ptvs_by_D95(dvhs):
    ptv_number_list = [0] * dvhs.count
    ptv_index = [i for i in range(dvhs.count) if dvhs.roi_type[i] == 'PTV']

    ptv_count = len(ptv_index)

    # Calculate D95 for each PTV
    doses_to_rank = get_dose_to_volume(dvhs, ptv_index, 0.95)
    order_index = sorted(range(ptv_count), key=lambda k: doses_to_rank[k])
    final_order = sorted(range(ptv_count), key=lambda k: order_index[k])

    for i in range(ptv_count):
        ptv_number_list[ptv_index[i]] = final_order[i] + 1

    return ptv_number_list


def get_dose_to_volume(dvhs, indices, roi_fraction):
    # Not precise (i.e., no interpolation) but good enough for sorting PTVs
    doses = []
    for x in indices:
        abs_volume = dvhs.volume[x] * roi_fraction
        dvh = dvhs.dvhs[x]
        dose = next(x[0] for x in enumerate(dvh) if x[1] < abs_volume)
        doses.append(dose)

    return doses


def move_files_to_new_path(files, new_dir):
    for file_path in files:
        file_name = os.path.basename(file_path)
        new = os.path.join(new_dir, file_name)
        try:
            shutil.move(file_path, new)
        except:
            os.mkdir(new_dir)
            shutil.move(file_path, new)


def remove_empty_folders(start_path):
    if start_path[0:2] == './':
        rel_path = start_path[2:]
        start_path = os.path.join(SCRIPT_DIR, rel_path)

    for (path, dirs, files) in os.walk(start_path, topdown=False):
        if files:
            continue
        try:
            if path != start_path:
                os.rmdir(path)
        except OSError:
            pass


def move_all_files(new_dir, old_dir):
    """
    This function will move all files from the old to new directory, it will ignore all files in subdirectories
    :param new_dir: absolute directory path
    :param old_dir: absolute directory path
    """
    initial_path = os.path.dirname(os.path.realpath(__file__))

    os.chdir(old_dir)

    file_paths = [f for f in os.listdir(old_dir) if os.path.isfile(os.path.join(old_dir, f))]

    misc_path = os.path.join(new_dir, 'misc')
    if not os.path.isdir(misc_path):
        os.mkdir(misc_path)

    for f in file_paths:
        file_name = os.path.basename(f)
        new = os.path.join(misc_path, file_name)
        shutil.move(f, new)

    os.chdir(initial_path)


def update_dicom_catalogue(mrn, uid, dir_path, plan_file, struct_file, dose_file):
    if not plan_file:
        plan_file = "(NULL)"
    if not plan_file:
        struct_file = "(NULL)"
    if not plan_file:
        dose_file = "(NULL)"
    DVH_SQL().insert_dicom_file_row(mrn, uid, dir_path, plan_file, struct_file, dose_file)
