#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pydicom as dicom
from dicompylercore import dicomparser
from pydicom.errors import InvalidDicomError
from db.sql_connector import DVH_SQL
import wx
from tools.utilities import get_file_paths
from tools.roi_name_manager import DatabaseROIs


FILE_TYPES = {'rtplan', 'rtstruct', 'rtdose'}
SCRIPT_DIR = os.path.dirname(__file__)


class DICOM_Importer:
    def __init__(self, start_path, tree_ctrl_files, tree_ctrl_rois, tree_ctrl_roi_root, search_subfolders=True):
        self.start_path = start_path
        self.tree_ctrl_files = tree_ctrl_files
        self.tree_ctrl_files.DeleteAllItems()
        self.tree_ctrl_rois = tree_ctrl_rois
        self.root_files = None
        self.root_rois = tree_ctrl_roi_root
        self.count = {key: 0 for key in ['patient', 'study', 'file']}
        self.patient_nodes = {}
        self.study_nodes = {}
        self.rt_file_nodes = {}
        self.file_paths = get_file_paths(start_path, search_subfolders)
        self.dicom_file_paths = {}
        self.current_index = 0
        self.file_count = len(self.file_paths)
        self.file_types = ['rtplan', 'rtstruct', 'rtdose']
        self.file_tree = {}

        self.image_list = wx.ImageList(16, 16)
        self.images = {'rtplan': self.image_list.Add(wx.Image("icons/chart_bar.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap()),
                       'rtstruct': self.image_list.Add(wx.Image("icons/pencil.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap()),
                       'rtdose': self.image_list.Add(wx.Image("icons/chart_curve.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap()),
                       'other': self.image_list.Add( wx.Image("icons/error.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap()),
                       'studies': self.image_list.Add(wx.Image("icons/group.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap()),
                       'study': self.image_list.Add(wx.Image("icons/book.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap()),
                       'patient': self.image_list.Add(wx.Image("icons/user.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap())}
        self.tree_ctrl_files.AssignImageList(self.image_list)

        self.roi_name_map = {}
        self.roi_nodes = {}

    def initialize_file_tree_root(self):
        self.root_files = self.tree_ctrl_files.AddRoot('Patients', ct_type=1)
        # self.root.Set3State(True)
        self.tree_ctrl_files.Expand(self.root_files)
        self.tree_ctrl_files.SetPyData(self.root_files, None)
        self.tree_ctrl_files.SetItemImage(self.root_files, self.images['studies'], wx.TreeItemIcon_Normal)

    @staticmethod
    def get_base_file_dict():
        return {key: [] for key in ['file_path', 'timestamp', 'latest_file_index']}

    def get_base_study_file_set(self):
        base_study_file_set = {key: self.get_base_file_dict() for key in ['rtplan', 'rtstruct', 'rtdose', 'other']}

        return base_study_file_set

    @staticmethod
    def read_dicom_file(file_path):
        try:
            return dicom.read_file(file_path, specific_tags=['StudyInstanceUID', 'Modality', 'StudyDate',
                                                             'PatientID', 'PatientName'])
        except InvalidDicomError:
            return None

    @staticmethod
    def get_file_type(dicom_file):
        file_type = dicom_file.Modality.lower()
        if file_type not in FILE_TYPES:
            return 'other'
        return file_type

    def append_next_file_to_tree(self):
        if self.current_index < self.file_count:
            file_path = self.file_paths[self.current_index]
            file_name = os.path.basename(file_path)
            dicom_file = self.read_dicom_file(file_path)

            if dicom_file:
                uid = dicom_file.StudyInstanceUID
                mrn = dicom_file.PatientID
                name = dicom_file.PatientName
                file_type = self.get_file_type(dicom_file)  # rtplan, rtstruct, rtdose
                timestamp = os.path.getmtime(file_path)

                if uid not in self.dicom_file_paths:
                    self.dicom_file_paths[uid] = {ft: {'file_path': None, 'timestamp': None} for ft in self.file_types + ['other']}

                # patient level
                if mrn not in list(self.file_tree):
                    self.file_tree[mrn] = {}
                if mrn not in self.patient_nodes:
                    self.add_patient_node(mrn, name)

                # study level
                if uid not in list(self.file_tree[mrn]):
                    self.file_tree[mrn][uid] = self.get_base_study_file_set()
                if uid not in self.study_nodes:
                    self.add_study_node(mrn, uid, dicom_file.StudyDate)
                if uid not in self.rt_file_nodes:
                    self.rt_file_nodes[uid] = {}

                # file level
                if self.dicom_file_paths[uid][file_type]['file_path'] is None:
                    self.dicom_file_paths[uid][file_type]['file_path'] = file_path
                    self.dicom_file_paths[uid][file_type]['timestamp'] = timestamp
                    self.add_rt_file_node(uid, file_type, file_name)
                    self.append_file(mrn, uid, file_type, file_path, timestamp)

                elif self.dicom_file_paths[uid][file_type]['timestamp'] < timestamp:
                    self.dicom_file_paths[uid][file_type]['file_path'] = file_path
                    self.dicom_file_paths[uid][file_type]['timestamp'] = timestamp
                    study_date = dicom_file.StudyDate
                    if study_date and len(study_date) == 8:
                        title = "%s.%s.%s - %s" % (study_date[0:4], study_date[4:6], study_date[6:], uid)
                    else:
                        title = "Date Unknown - %s" % uid
                    self.tree_ctrl_files.SetItemText(self.rt_file_nodes[uid][file_type], title)

            self.current_index += 1

    def append_file(self, mrn, uid, file_type, file_path, timestamp):
        self.file_tree[mrn][uid][file_type]['file_path'].append(file_path)
        self.file_tree[mrn][uid][file_type]['timestamp'].append(timestamp)

    def add_rt_file_node(self, uid, file_type, file_name):
        self.count['file'] += 1

        self.rt_file_nodes[uid][file_type] = self.tree_ctrl_files.AppendItem(self.study_nodes[uid],
                                                                             "%s - %s" % (file_type, file_name))

        self.tree_ctrl_files.SetPyData(self.rt_file_nodes[uid][file_type], None)
        self.tree_ctrl_files.SetItemImage(self.rt_file_nodes[uid][file_type], self.images[file_type],
                                          wx.TreeItemIcon_Normal)
        self.tree_ctrl_files.SortChildren(self.study_nodes[uid])

    def add_patient_node(self, mrn, name):
        self.count['patient'] += 1
        self.patient_nodes[mrn] = self.tree_ctrl_files.AppendItem(self.root_files, "%s - %s" % (name, mrn), ct_type=1)
        # self.patient_nodes[mrn].Set3State(True)
        self.tree_ctrl_files.SetPyData(self.patient_nodes[mrn], None)
        self.tree_ctrl_files.SetItemImage(self.patient_nodes[mrn], self.images['patient'],
                                          wx.TreeItemIcon_Normal)
        self.tree_ctrl_files.SortChildren(self.root_files)
        self.tree_ctrl_files.Expand(self.patient_nodes[mrn])

    def add_study_node(self, mrn, uid, study_date):
        self.count['study'] += 1
        if study_date and len(study_date) == 8:
            title = "%s.%s.%s - %s" % (study_date[0:4], study_date[4:6], study_date[6:], uid)
        else:
            title = "Date Unknown - %s" % uid
        self.study_nodes[uid] = self.tree_ctrl_files.AppendItem(self.patient_nodes[mrn], title, ct_type=1)
        # self.study_nodes[uid].Set3State(True)
        self.tree_ctrl_files.SetPyData(self.study_nodes[uid], None)
        self.tree_ctrl_files.SetItemImage(self.study_nodes[uid], self.images['study'],
                                          wx.TreeItemIcon_Normal)
        self.tree_ctrl_files.SortChildren(self.patient_nodes[mrn])

    # def update_latest_index(self):
    #     for study in self.file_tree:
    #         for file_type in study:
    #             latest_time = None
    #             for i, ts in enumerate(file_type['timestamp']):
    #                 if not latest_time or ts > latest_time:
    #                     latest_time = ts
    #                     file_type['latest_file'] = file_type['file_path'][i]

    @property
    def incomplete_studies(self):
        uids = []
        for patient in self.file_tree.values():
            for uid in list(patient):
                files = [patient[uid][file_type]['file_path'] for file_type in self.file_types]
                if not all(files):
                    uids.append(uid)
        return uids

    def is_study_file_set_complete(self, mrn, uid):
        for file_type in self.file_types:
            if not self.file_tree[mrn][uid][file_type]['file_path']:
                return False
        return True

    def is_patient_file_set_complete(self, mrn, uids):
        for uid in uids:
            if not self.is_study_file_set_complete(mrn, uid):
                return False
        return True

    def rebuild_tree_ctrl_files(self):
        self.tree_ctrl_files.DeleteChildren(self.root_files)
        self.study_nodes = {uid: self.tree_ctrl_files.AppendItem(self.root_files, study['node_title'])
                            for uid, study in self.file_tree.items()}
        self.rt_file_nodes = {uid: {} for uid in list(self.file_tree)}
        for uid in list(self.file_tree):
            for rt_file in self.file_types:
                self.rt_file_nodes[uid][rt_file] = self.tree_ctrl_files.AppendItem(self.study_nodes[uid], rt_file)

        self.tree_ctrl_files.Expand(self.root_files)

    def rebuild_tree_ctrl_rois(self, uid):
        self.tree_ctrl_rois.DeleteChildren(self.root_rois)
        if self.dicom_file_paths[uid]['rtstruct']['file_path']:
            self.tree_ctrl_rois.SetItemBackgroundColour(self.root_rois, None)
            dicom_rt_struct = dicomparser.DicomParser(self.dicom_file_paths[uid]['rtstruct']['file_path'])
            structures = dicom_rt_struct.GetStructures()
            self.roi_name_map = {structures[key]['name']: {'key': key, 'type': structures[key]['type']}
                                 for key in list(structures) if structures[key]['type'] != 'MARKER'}
            self.roi_nodes = {}
            rois = list(self.roi_name_map)
            rois.sort()
            for roi in rois:
                self.roi_nodes[roi] = self.tree_ctrl_rois.AppendItem(self.root_rois, roi, ct_type=1)
        else:
            self.tree_ctrl_rois.SetItemBackgroundColour(self.root_rois, wx.Colour(255, 0, 0))

    @property
    def checked_studies(self):
        studies = {}
        for uid, study_node in self.study_nodes.items():
            if self.tree_ctrl_files.IsItemChecked(study_node):
                studies[uid] = {file_type: file_path for file_type, file_path in self.rt_file_nodes[uid].items()}
        return studies

    def check_mapped_rois(self, physician):
        roi_map = DatabaseROIs()
        physician_is_valid = roi_map.is_physician(physician)
        for roi in self.roi_name_map.keys():
            node = self.roi_nodes[roi]
            if physician_is_valid and roi_map.get_physician_roi(physician, roi) not in {'uncategorized'}:
                self.tree_ctrl_rois.CheckItem(node, True)
            else:
                self.tree_ctrl_rois.CheckItem(node, False)


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


def update_dicom_catalogue(mrn, uid, dir_path, plan_file, struct_file, dose_file):
    if not plan_file:
        plan_file = "(NULL)"
    if not plan_file:
        struct_file = "(NULL)"
    if not plan_file:
        dose_file = "(NULL)"
    with DVH_SQL() as cnx:
        cnx.insert_dicom_file_row(mrn, uid, dir_path, plan_file, struct_file, dose_file)
