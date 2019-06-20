#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import wx
import os
import pydicom as dicom
from dicompylercore import dicomparser
from pydicom.errors import InvalidDicomError
from tools.utilities import get_file_paths
from threading import Thread
from pubsub import pub


FILE_TYPES = {'rtplan', 'rtstruct', 'rtdose'}
SCRIPT_DIR = os.path.dirname(__file__)


# TODO: use DicomDirectoryParser from DVH-Check to match with SOP Instance UIDs
#  (https://github.com/cutright/DVH-Check/blob/master/dvh_check/utilities.py)
class DICOM_Importer:
    def __init__(self, start_path, tree_ctrl_files, tree_ctrl_rois, tree_ctrl_roi_root, tree_ctrl_rois_images,
                 roi_map, search_subfolders=True):
        self.start_path = start_path
        self.tree_ctrl_files = tree_ctrl_files
        self.tree_ctrl_files.DeleteAllItems()
        self.tree_ctrl_rois = tree_ctrl_rois
        self.tree_ctrl_rois_images = tree_ctrl_rois_images
        self.root_files = None
        self.root_rois = tree_ctrl_roi_root
        self.database_rois = roi_map
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
        self.images = {'rtplan': self.image_list.Add(wx.Image("icons/iconfinder_Clipboard-Plan_379537_zoom.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap()),
                       'rtstruct': self.image_list.Add(wx.Image("icons/iconfinder_Education-Filled_7_3672892.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap()),
                       'rtdose': self.image_list.Add(wx.Image("icons/iconfinder_package-supported_24220.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap()),
                       'other': self.image_list.Add( wx.Image("icons/error.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap()),
                       'studies': self.image_list.Add(wx.Image("icons/iconfinder_User_Customers_1218712.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap()),
                       'study': self.image_list.Add(wx.Image("icons/iconfinder_Travel-Filled-07_3671983.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap()),
                       'patient': self.image_list.Add(wx.Image("icons/iconfinder_User_Yuppie_3_1218716.png", wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap())}
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
                self.roi_nodes[roi] = self.tree_ctrl_rois.AppendItem(self.root_rois, roi, ct_type=0)
        else:
            self.tree_ctrl_rois.SetItemBackgroundColour(self.root_rois, wx.Colour(255, 0, 0))

    @property
    def checked_studies(self):
        studies = {}
        for uid, study_node in self.study_nodes.items():
            if self.tree_ctrl_files.IsItemChecked(study_node):
                studies[uid] = {file_type: file_path for file_type, file_path in self.rt_file_nodes[uid].items()}
        return studies

    def check_mapped_rois(self, physician, specific_roi=None):
        physician_is_valid = self.database_rois.is_physician(physician)
        if specific_roi is None:
            rois = self.roi_name_map.keys()
        else:
            rois = [specific_roi]
        for roi in rois:
            node = self.roi_nodes[roi]
            if physician_is_valid and self.database_rois.get_physician_roi(physician, roi) not in {'uncategorized'}:
                # self.tree_ctrl_rois.CheckItem(node, True)
                self.tree_ctrl_rois.SetItemImage(node, self.tree_ctrl_rois_images['yes'], wx.TreeItemIcon_Normal)
            else:
                # self.tree_ctrl_rois.CheckItem(node, False)
                self.tree_ctrl_rois.SetItemImage(node, self.tree_ctrl_rois_images['no'], wx.TreeItemIcon_Normal)

    def get_used_physician_rois(self, physician):
        if self.database_rois.is_physician(physician):
            return list(set([self.database_rois.get_physician_roi(physician, roi) for roi in self.roi_name_map.keys()]))
        return []


class DicomDirectoryParserFrame(wx.Frame):
    def __init__(self, start_path, search_subfolders=True):
        wx.Frame.__init__(self, None)

        self.start_path = start_path
        self.search_subfolders = search_subfolders
        self.file_tree = {}

        self.gauge = wx.Gauge(self, wx.ID_ANY, 100)

        self.__set_properties()
        self.__do_subscribe()
        self.__do_layout()

        self.run()

    def __set_properties(self):
        self.SetTitle("Reading DICOM Headers")
        self.SetMinSize((700, 100))

    def __do_subscribe(self):
        pub.subscribe(self.update, "dicom_directory_parser_update")
        pub.subscribe(self.set_file_tree, "dicom_directory_parser_set_file_tree")
        pub.subscribe(self.close, "dicom_directory_parser_close")

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_objects = wx.BoxSizer(wx.VERTICAL)
        self.label = wx.StaticText(self, wx.ID_ANY, "Progress Label:")
        sizer_objects.Add(self.label, 0, 0, 0)
        sizer_objects.Add(self.gauge, 0, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_objects, 0, wx.ALL | wx.EXPAND, 10)
        self.SetSizer(sizer_wrapper)
        self.Fit()
        self.Layout()
        self.Center()

    def update(self, msg):
        wx.CallAfter(self.label.SetLabelText, msg['label'])
        wx.CallAfter(self.gauge.SetValue, int(100 * msg['gauge']))

    def set_file_tree(self, tree):
        self.file_tree = tree

    def run(self):
        self.Show()
        DicomDirectoryParser(self.start_path, self.search_subfolders)

    def close(self):
        self.Destroy()


class DicomDirectoryParser(Thread):
    """
    With a given start path, scan for RT DICOM files (plan, struct, dose) connected by SOPInstanceUID
    Previous versions strictly used StudyInstanceUID which was sufficient for Philips Pinnacle because
    it can export multiple prescriptions in a single RT Plan file, other TPS's export one file per plan
    """
    def __init__(self, start_path, search_subfolders):
        Thread.__init__(self)
        self.start_path = start_path
        self.search_subfolders = search_subfolders
        self.file_types = ['rtplan', 'rtstruct', 'rtdose']

        self.dicom_tag_values = {}
        self.dicom_files = {key: [] for key in self.file_types}
        self.plan_file_sets = {}
        self.uid_to_mrn = {}

        self.start()

    def run(self):

        file_paths = get_file_paths(self.start_path, search_subfolders=self.search_subfolders)
        file_count = len(file_paths)
        plan_file_set = {}

        for file_index, file_path in enumerate(file_paths):
            msg = {'label': "File Name: %s" % os.path.basename(file_path),
                   'gauge': file_index / file_count}
            wx.CallAfter(pub.sendMessage, "dicom_directory_parser_update", msg=msg)
            ds = self.read_dicom_file(file_path)
            if ds is not None:
                modality = ds.Modality.lower()
                timestamp = os.path.getmtime(file_path)

                self.dicom_files[modality].append(file_path)

                self.dicom_tag_values[file_path] = {'timestamp': timestamp,
                                                    'study_instance_uid': ds.StudyInstanceUID,
                                                    'sop_instance_uid': ds.SOPInstanceUID,
                                                    'patient_name': ds.PatientName,
                                                    'mrn': ds.PatientID}

                if modality == 'rtplan':
                    uid = ds.ReferencedStructureSetSequence[0].ReferencedSOPInstanceUID
                    mrn = ds.PatientID
                    self.uid_to_mrn[uid] = ds.PatientID
                    self.dicom_tag_values[file_path]['ref_sop_instance'] = {'type': 'struct',
                                                                            'uid': uid}
                    study_uid = ds.StudyInstanceUID
                    plan_uid = ds.SOPInstanceUID
                    if mrn not in list(self.plan_file_sets):
                        self.plan_file_sets[mrn] = {}

                    if study_uid not in list(self.plan_file_sets[mrn]):
                        self.plan_file_sets[mrn][study_uid] = {}

                    self.plan_file_sets[mrn][study_uid][plan_uid] = {'rtplan': {'file_path': file_path,
                                                                                'sop_instance_uid': plan_uid}}
                elif modality == 'rtdose':
                    uid = ds.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID
                    self.dicom_tag_values[file_path]['ref_sop_instance'] = {'type': 'plan',
                                                                            'uid': uid}
                else:
                    self.dicom_tag_values[file_path]['ref_sop_instance'] = {'type': None,
                                                                            'uid': None}

        # associate appropriate rtdose files to plans
        dose_file_count = len(self.dicom_files['rtdose'])
        for file_index, dose_file in enumerate(self.dicom_files['rtdose']):
            dose_tag_values = self.dicom_tag_values[dose_file]
            ref_plan_uid = dose_tag_values['ref_sop_instance']['uid']
            study_uid = dose_tag_values['study_instance_uid']
            mrn = dose_tag_values['mrn']
            for plan_file_set in self.plan_file_sets[mrn][study_uid].values():
                plan_uid = plan_file_set['rtplan']['sop_instance_uid']
                if plan_uid == ref_plan_uid:
                    plan_file_set['rtdose'] = {'file_path': dose_file,
                                               'sop_instance_uid': dose_tag_values['sop_instance_uid']}
        # associate appropriate rtstruct files to plans
        mrn_count = len(list(self.plan_file_sets))
        for mrn_index, mrn in enumerate(list(self.plan_file_sets)):
            for study_uid in list(self.plan_file_sets[mrn]):
                for plan_file_set in self.plan_file_sets[mrn][study_uid].values():
                    plan_file = plan_file_set['rtplan']['file_path']
                    ref_struct_uid = self.dicom_tag_values[plan_file]['ref_sop_instance']['uid']
                    for struct_file in self.dicom_files['rtstruct']:
                        struct_uid = self.dicom_tag_values[struct_file]['sop_instance_uid']
                        if struct_uid == ref_struct_uid:
                            plan_file_set['rtstruct'] = {'file_path': struct_file,
                                                         'sop_instance_uid': struct_uid}

        pub.sendMessage('dicom_directory_parser_set_file_tree', tree=plan_file_set)
        pub.sendMessage('dicom_directory_parser_close')

    @staticmethod
    def read_dicom_file(file_path):
        try:
            return dicom.read_file(file_path, stop_before_pixels=True)
        except InvalidDicomError:
            return None
    #
    # def get_file_type(self, dicom_file):
    #     file_type = dicom_file.Modality.lower()
    #     if file_type not in self.file_types:
    #         return 'other'
    #     return file_type
    #
    # def get_plan_files(self, mrn, study_instance_uid, rt_plan_sop_uid):
    #     file_types = self.file_types + ['other']
    #     file_set = self.plan_file_sets[mrn][study_instance_uid][rt_plan_sop_uid]
    #     return {file_type: file_set[file_type]['file_path'] for file_type in file_types}

    # @property
    # def mrns(self):
    #     return list(self.plan_file_sets)
    #
    # @property
    # def study_instance_uids(self):
    #     study_uids = []
    #     for mrn in list(self.plan_file_sets):
    #         study_uids.extend(list(self.plan_file_sets[mrn]))
    #     return study_uids
    #
    # def get_mrn_from_study_instance_uid(self, study_instance_uid):
    #     for mrn in list(self.plan_file_sets):
    #         if study_instance_uid in list(self.plan_file_sets[mrn]):
    #             return mrn
    #
    # def get_dicom_file_path(self, study_instance_uid, plan_uid, file_type):
    #     mrn = self.get_mrn_from_study_instance_uid(study_instance_uid)
    #     if mrn:
    #         if study_instance_uid in list(self.plan_file_sets[mrn]):
    #             return self.plan_file_sets[mrn][study_instance_uid][plan_uid][file_type]['file_path']
    #
    # def get_study_dicom_file_paths(self, study_instance_uid):
    #     file_paths = {}
    #     mrn = self.get_mrn_from_study_instance_uid(study_instance_uid)
    #     for plan_uid, file_set in self.plan_file_sets[mrn][study_instance_uid].items():
    #         file_paths[plan_uid] = {file_type: file_obj['file_path'] for file_type, file_obj in file_set.items()}
    #     return file_paths
