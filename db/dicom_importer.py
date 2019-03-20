#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import pydicom as dicom
from pydicom.errors import InvalidDicomError
from db.sql_connector import DVH_SQL


FILE_TYPES = {'rtplan', 'rtstruct', 'rtdose'}
SCRIPT_DIR = os.path.dirname(__file__)


class DICOM_Directory:
    def __init__(self, start_path, wx_list_ctrl):
        self.wx_tree_ctrl = wx_list_ctrl
        self.wx_tree_ctrl.DeleteAllItems()
        self.root = self.wx_tree_ctrl.AddRoot('Studies')
        self.wx_tree_ctrl.Expand(self.root)
        self.study_nodes = {}
        self.rt_file_nodes = {}
        self.start_path = start_path
        self.file_paths = self.get_file_paths()
        self.current_index = 0
        self.file_count = len(self.file_paths)
        self.file_types = ['rtplan', 'rtstruct', 'rtdose']
        self.file_tree = {}

    def get_file_paths(self):
        file_paths = []
        for root, dirs, files in os.walk(self.start_path, topdown=False):
            for name in files:
                file_paths.append(os.path.join(root, name))
        return file_paths

    @staticmethod
    def get_base_study_file_set():
        base_file_dict = {key: [] for key in ['file_path', 'timestamp', 'latest_file_index']}
        return {key: base_file_dict for key in ['rtplan', 'rtstruct', 'rtdose', 'other']}

    def append_next_file_to_tree(self):
        if self.current_index < self.file_count:
            file_path = self.file_paths[self.current_index]
            try:
                dicom_file = dicom.read_file(file_path, specific_tags=['StudyInstanceUID', 'Modality', 'PatientID'])
            except InvalidDicomError:
                dicom_file = None

            if dicom_file:
                uid = dicom_file.StudyInstanceUID
                file_type = dicom_file.Modality.lower()  # rtplan, rtstruct, rtdose
                timestamp = os.path.getmtime(file_path)

                if file_type not in FILE_TYPES:
                    file_type = 'other'

                if uid not in list(self.file_tree):
                    self.file_tree[uid] = self.get_base_study_file_set()
                    self.file_tree[uid]['mrn'] = dicom_file.PatientID
                    self.file_tree[uid]['node_title'] = "%s: %s" % (dicom_file.PatientID, uid)

                self.file_tree[uid][file_type]['file_path'].append(file_path)
                self.file_tree[uid][file_type]['timestamp'].append(timestamp)

                self.append_file_to_tree(uid, dicom_file.PatientID, file_type)

            self.current_index += 1

    def process_remaining_files(self):
        while self.current_index < self.file_count:
            self.append_next_file_to_tree()

    def update_latest_index(self):
        for study in self.file_tree:
            for file_type in study:
                latest_time = None
                for i, ts in enumerate(file_type['timestamp']):
                    if not latest_time or ts > latest_time:
                        latest_time = ts
                        file_type['latest_file'] = file_type['file_path'][i]

    @property
    def incomplete_patients(self):
        return [uid for uid, study in self.file_tree.items() if not self.is_study_file_set_complete(study)]

    def is_study_file_set_complete(self, patient):
        for file_type in self.file_types:
            if not patient[file_type]:
                return False
        return True

    def append_file_to_tree(self, uid, mrn, file_type):
        if uid not in self.study_nodes:
            self.study_nodes[uid] = self.wx_tree_ctrl.AppendItem(self.root, "%s: %s" % (mrn, uid))

        if uid not in self.rt_file_nodes:
            self.rt_file_nodes[uid] = {}

        self.rt_file_nodes[uid][file_type] = self.wx_tree_ctrl.AppendItem(self.study_nodes[uid], file_type)

    def rebuild_wx_tree_ctrl(self):
        self.wx_tree_ctrl.DeleteAllItems()
        self.study_nodes = {uid: self.wx_tree_ctrl.AppendItem(self.root, study['node_title']) for uid, study in self.file_tree.items()}
        self.rt_file_nodes = {uid: {} for uid in list(self.file_tree)}
        for uid in list(self.file_tree):
            for rt_file in self.file_types:
                self.rt_file_nodes[uid][rt_file] = self.wx_tree_ctrl.AppendItem(self.study_nodes[uid], rt_file)

        self.wx_tree_ctrl.Expand(self.root)


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
