#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.dicom_tree_builder.py
"""Class and functions related to parsing a directory containing DICOM files and updating the GUI."""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import wx
import os
import pydicom as dicom
from dicompylercore import dicomparser
from pydicom.errors import InvalidDicomError
from pubsub import pub
from threading import Thread
from queue import Queue
from dvha.db.dicom_parser import DICOM_Parser
from dvha.paths import ICONS
from dvha.tools.utilities import get_file_paths
from time import sleep


SCRIPT_DIR = os.path.dirname(__file__)


class DicomTreeBuilder:
    """
    This class processes data for various UI objects from models.import_dicom.ImportDicomFrame
    """
    def __init__(self, start_path, tree_ctrl_files, tree_ctrl_rois, tree_ctrl_roi_root, tree_ctrl_rois_images,
                 roi_map, search_subfolders=True):
        """
        :param start_path: directory to be scanned
        :type start_path: str
        :param tree_ctrl_files: tree in GUI used to visualize DICOM files
        :type tree_ctrl_files: CustomTreeCtrl
        :param tree_ctrl_rois: tree in GUI that lists rois of currently selected plan
        :type tree_ctrl_rois: CustomTreeCtrl
        :param tree_ctrl_roi_root: pointer to  the root node
        :param tree_ctrl_rois_images: a dictionary of image list pointers
        :type tree_ctrl_rois_images: dict
        :param roi_map: the object manager ROI mapping
        :type roi_map: tools.roi_name_manager.DatabaseROIs
        :param search_subfolders: indicates if files within sub-directories should be included
        :type search_subfolders: bool
        """

        # Store passed parameters
        self.start_path = start_path
        self.tree_ctrl_files = tree_ctrl_files
        self.tree_ctrl_rois = tree_ctrl_rois
        self.root_rois = tree_ctrl_roi_root
        self.tree_ctrl_rois_images = tree_ctrl_rois_images
        self.roi_map = roi_map
        self.search_subfolders = search_subfolders

        self.root_files = None
        self.tree_ctrl_files.DeleteAllItems()

        # These dictionaries will be used for easy lookup of tree_ctrl_files nodes
        self.patient_nodes = {}  # key: mrn
        self.study_nodes = {}  # key: study_instance_uid
        self.plan_nodes = {}  # key: sop_instance_uid
        self.file_nodes = {}  # key: absolute file path

        self.dicom_file_paths = {}
        self.other_dicom_files = {}
        self.current_index = 0
        self.file_types = ['rtplan', 'rtstruct', 'rtdose']
        self.file_tree = {}
        self.roi_name_map = {}
        self.roi_nodes = {}

        self.__do_subscribe()
        self.__set_images()
        self.__initialize_file_tree_root()

        self.parse_directory()

    def __do_subscribe(self):
        pub.subscribe(self.set_file_tree, "dicom_directory_parser_set_file_tree")

    def __set_images(self):
        self.image_list = wx.ImageList(16, 16)
        keys = ['rtplan', 'rtstruct', 'rtdose', 'other', 'studies', 'study', 'plan', 'patient']
        self.images = {key: self.image_list.Add(wx.Image(ICONS[key], wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap())
                       for key in keys}

        self.tree_ctrl_files.AssignImageList(self.image_list)

    def __initialize_file_tree_root(self):
        self.root_files = self.tree_ctrl_files.AddRoot('Patients', ct_type=1)
        self.tree_ctrl_files.Expand(self.root_files)
        self.tree_ctrl_files.SetPyData(self.root_files, None)
        self.tree_ctrl_files.SetItemImage(self.root_files, self.images['studies'], wx.TreeItemIcon_Normal)

    def parse_directory(self):
        """
        Initiate directory parsing.  Creates a wx.Dialog, reads dicom headers and sorts files into dictionaries
        """
        PreImportParsingProgressFrame(self.start_path, search_subfolders=self.search_subfolders)

    def set_file_tree(self, tree, file_paths, other_dicom_files):
        """
        DicomDirectoryParserWorker subscribes to this function to initiate the tree_ctrl_files build
        :param tree: the plan_file_sets object from DicomDirectoryParserWorker
        :type tree: dict
        :param file_paths: the dicom_file_paths objet from DicomDirectoryParserWorker
        :type file_paths: dict
        """
        self.file_tree = tree
        self.dicom_file_paths = file_paths
        self.other_dicom_files = other_dicom_files
        wx.CallAfter(self.build_tree_ctrl_files)

    def get_file_type(self, dicom_dataset):
        """
        Get the file type of a DICOM dataset read by pydicom
        :param dicom_dataset: pydicom dataset
        :return: file_type among self.file_types or 'other'
        :rtype: str
        """
        file_type = dicom_dataset.Modality.lower()
        return [file_type, 'other'][file_type not in self.file_types]

    def build_tree_ctrl_files(self):
        """
        Build the tree for tree_ctrl_files and store their nodes using node adders.
        Then tell models.import_dicom.ImportDicomFrame to parse the data.
        """
        self.tree_ctrl_files.DeleteChildren(self.root_files)
        for key, patient in self.file_tree.items():
            self.add_patient_node(key)
            for study_uid, study in patient.items():
                self.add_study_node(key, study_uid)
                for plan_uid, plan in study.items():
                    self.add_plan_node(study_uid, plan_uid)
                    for file_type, file_list in self.dicom_file_paths[plan_uid].items():
                        if file_list:
                            for file_path in file_list:
                                if file_path not in self.file_nodes.keys():
                                    self.add_rt_file_node(plan_uid, file_type, file_path)
                                    break

        self.tree_ctrl_files.Expand(self.root_files)
        self.tree_ctrl_files.ExpandAllChildren(self.root_files)

        PreImportFileSetParserWorker(self.dicom_file_paths)

    def rebuild_tree_ctrl_rois(self, plan_uid):
        """
        Delete all nodes of current tree_ctrl_rois and build for the specified plan
        :param plan_uid: pydicom ds.SOPInstanceUID for the RT Plan of interest
        """
        self.tree_ctrl_rois.DeleteChildren(self.root_rois)
        if self.dicom_file_paths[plan_uid]['rtstruct'][0]:
            self.tree_ctrl_rois.SetItemBackgroundColour(self.root_rois, None)
            dicom_rt_struct = dicomparser.DicomParser(self.dicom_file_paths[plan_uid]['rtstruct'][0])
            structures = dicom_rt_struct.GetStructures()
            self.roi_name_map = {structures[key]['name']: {'key': key, 'type': structures[key]['type']}
                                 for key in list(structures) if structures[key]['type'] != 'MARKER'}
            self.roi_nodes = {}
            rois = list(self.roi_name_map)
            rois.sort()
            for roi in rois:
                self.roi_nodes[roi] = self.tree_ctrl_rois.AppendItem(self.root_rois, roi, ct_type=0)
                roi_type = [None, 'PTV'][self.roi_name_map[roi]['type'] == 'PTV']
                self.update_tree_ctrl_roi_with_roi_type(roi, roi_type=roi_type)
        else:
            self.tree_ctrl_rois.SetItemBackgroundColour(self.root_rois, wx.Colour(255, 0, 0))

    def update_tree_ctrl_roi_with_roi_type(self, roi, roi_type=None):
        if roi_type is not None:
            text = '%s ----- ROI Type: %s' % (roi, roi_type)
        else:
            text = roi
        self.tree_ctrl_rois.SetItemText(self.roi_nodes[roi], text)

    def add_patient_node(self, mrn):
        """
        Add a patient node to tree_ctrl_files
        :param mrn: pydicom's ds.PatientID
        :type mrn: str
        """
        if mrn not in list(self.patient_nodes):
            # TODO: get patient name for tree item title
            self.patient_nodes[mrn] = self.tree_ctrl_files.AppendItem(self.root_files, mrn, ct_type=1)
            # self.patient_nodes[mrn].Set3State(True)
            self.tree_ctrl_files.SetPyData(self.patient_nodes[mrn], None)
            self.tree_ctrl_files.SetItemImage(self.patient_nodes[mrn], self.images['patient'],
                                              wx.TreeItemIcon_Normal)

    def add_study_node(self, mrn, study_instance_uid):
        """
        Add a study node to tree_ctrl_files
        :param mrn: pydicom ds.PatientID
        :type mrn: str
        :param study_instance_uid: pydicom ds.StudyInstanceUID
        :type study_instance_uid: str
        """
        if study_instance_uid not in list(self.study_nodes):
            self.study_nodes[study_instance_uid] = self.tree_ctrl_files.AppendItem(self.patient_nodes[mrn],
                                                                                   study_instance_uid, ct_type=1)
            # self.study_nodes[uid].Set3State(True)
            self.tree_ctrl_files.SetPyData(self.study_nodes[study_instance_uid], None)
            self.tree_ctrl_files.SetItemImage(self.study_nodes[study_instance_uid], self.images['study'],
                                              wx.TreeItemIcon_Normal)

    def add_plan_node(self, study_instance_uid, plan_uid):
        """
        Add a plan node to tree_ctrl_files
        :param study_instance_uid: pydicom ds.StudyInstanceUID
        :type study_instance_uid: str
        :param plan_uid: pydicom ds.SOPInstanceUID of a RT Plan file
        :type plan_uid: str
        """
        if plan_uid not in list(self.plan_nodes):
            self.plan_nodes[plan_uid] = self.tree_ctrl_files.AppendItem(self.study_nodes[study_instance_uid], plan_uid, ct_type=1)
            # self.study_nodes[uid].Set3State(True)
            self.tree_ctrl_files.SetPyData(self.plan_nodes[plan_uid], None)
            self.tree_ctrl_files.SetItemImage(self.plan_nodes[plan_uid], self.images['plan'],
                                              wx.TreeItemIcon_Normal)

    def add_rt_file_node(self, plan_uid, file_type, file_path):
        """
        Add a file node to tree_ctrl_files
        :param plan_uid: pydicom ds.SOPInstanceUID of a RT Plan file
        :type plan_uid: str
        :param file_type: a type as specifed in self.file_types
        :type file_type: str
        :param file_path: the absolute file path of the DICOM file
        :type file_path: str
        """
        if file_path not in list(self.file_nodes):
            if file_type not in self.file_types:
                file_type = 'other'
            file_name = os.path.basename(file_path)
            self.file_nodes[file_path] = self.tree_ctrl_files.AppendItem(self.plan_nodes[plan_uid],
                                                                         "%s - %s" % (file_type, file_name), ct_type=0)
            # self.study_nodes[uid].Set3State(True)
            self.tree_ctrl_files.SetPyData(self.file_nodes[file_path], None)
            self.tree_ctrl_files.SetItemImage(self.file_nodes[file_path], self.images[file_type],
                                              wx.TreeItemIcon_Normal)

    def get_id_of_tree_ctrl_node(self, node):
        """
        :param node: item from of a wx.EVT_TREE_SEL_CHANGED on tree_ctrl_files
        :return: the node id and type if node found in the stored node dictionaries
        """
        for node_type in ['patient', 'study', 'plan', 'file']:
            for node_id, stored_node in getattr(self, "%s_nodes" % node_type).items():
                if node == stored_node:
                    return node_id, node_type
        return None, None

    def update_mapped_roi_status(self, physician, specific_roi=None):
        """
        Update the image next to the roi of the tree_ctrl_roi to indicate if the roi_name is found in the roi_map
        :param physician: name as stored in roi_map
        :type physician: str
        :param specific_roi: if specified, only this roi will be updated
        :type specific_roi: str
        """
        physician_is_valid = self.roi_map.is_physician(physician)
        if specific_roi is None:
            rois = self.roi_name_map.keys()
        else:
            rois = [specific_roi]  # wrap specific roi into a list
        for roi in rois:
            node = self.roi_nodes[roi]
            if physician_is_valid and self.roi_map.get_physician_roi(physician, roi) not in {'uncategorized'}:
                # self.tree_ctrl_rois.CheckItem(node, True)
                self.tree_ctrl_rois.SetItemImage(node, self.tree_ctrl_rois_images['yes'], wx.TreeItemIcon_Normal)
            else:
                # self.tree_ctrl_rois.CheckItem(node, False)
                self.tree_ctrl_rois.SetItemImage(node, self.tree_ctrl_rois_images['no'], wx.TreeItemIcon_Normal)

    def get_used_physician_rois(self, physician):
        """
        Get the physician rois that are used in the plan parsed by this object
        :param physician: name as stored in roi_map
        :type physician: str
        :return: used physician rois for this plan
        :rtype: list
        """
        if self.roi_map.is_physician(physician):
            return list(set([self.roi_map.get_physician_roi(physician, roi) for roi in self.roi_name_map.keys()]))
        return []

    @property
    def incomplete_plans(self):
        """
        Identify plans that do not include RT Structure and RT Dose files
        :return: the RT Plan SOP Instance UIDs of incomplete plans
        :rtype: list
        """
        incomplete_plan_uids = []
        for patient in self.file_tree.values():
            for study in patient.values():
                for plan_uid, plan in study.items():
                    files = [plan[file_type]['file_path'] for file_type in self.file_types]
                    if not all(files):
                        incomplete_plan_uids.append(plan_uid)
        return incomplete_plan_uids

    @property
    def checked_plans(self):
        """
        Identify the plans that are checked and return the abs_file_paths of their associated DICOM files
        :return: A dictionary with RT Plan SOP Instance UIDs for keys and dictionary of file_paths for values
        :rtype: dict
        """
        plans = {}
        for plan_node_uid, plan_node in self.plan_nodes.items():
            if self.tree_ctrl_files.IsItemChecked(plan_node):
                for mrn, study in self.file_tree.items():
                    for study_uid, plan in study.items():
                        for plan_uid, dicom_files in plan.items():
                            if plan_uid == plan_node_uid:
                                plans[plan_uid] = {file_type: file_obj['file_path']
                                                   for file_type, file_obj in dicom_files.items()}
        return plans


class PreImportParsingProgressFrame(wx.Dialog):
    """
    Create a window to display parsing progress and begin DicomDirectoryParserWorker. After thread completes,
    send message to begin DICOM parsing
    """
    def __init__(self, start_path, search_subfolders=True):
        """
        :param start_path: absolute path to begin parsing
        :type start_path: str
        :param search_subfolders: set to False to ignore sub-directories
        :type search_subfolders: bool
        """
        wx.Dialog.__init__(self, None)

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

    def pub_set_title(self, msg):
        wx.CallAfter(self.SetTitle, msg)

    def __do_subscribe(self):
        pub.subscribe(self.update, "pre_import_progress_update")
        pub.subscribe(self.pub_set_title, "pre_import_progress_set_title")
        pub.subscribe(self.close, "pre_import_progress_close")

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
        """
        Update the progress message and gauge
        :param msg: a dictionary with keys of 'label' and 'gauge' text and progress fraction, respectively
        :type msg: dict
        """
        wx.CallAfter(self.label.SetLabelText, msg['label'])
        wx.CallAfter(self.gauge.SetValue, int(100 * msg['gauge']))

    def run(self):
        """
        Initiate layout in GUI and begin dicom directory parser thread
        """
        self.Show()
        DicomDirectoryParserWorker(self.start_path, self.search_subfolders)

    def close(self):
        """
        Destroy layout in GUI and send message to being dicom parsing
        """
        pub.sendMessage("pre_import_complete")
        self.Destroy()


class DicomDirectoryParserWorker(Thread):
    """
    With a given start path, scan for RT DICOM files (plan, struct, dose) connected by SOPInstanceUID
    Previous versions strictly used StudyInstanceUID which was sufficient for Philips Pinnacle because
    it can export multiple prescriptions in a single RT Plan file, other TPS's export one file per plan
    """
    def __init__(self, start_path, search_subfolders):
        """
        :param start_path: initial directory path to scan for DICOM files
        :param search_subfolders: If true, files within all sub-directories will be included
        """
        Thread.__init__(self)
        self.start_path = start_path
        self.search_subfolders = search_subfolders
        self.file_types = ['rtplan', 'rtstruct', 'rtdose']
        self.req_tags = ['StudyInstanceUID', 'SOPInstanceUID', 'PatientName', 'PatientID']

        self.dicom_tag_values = {}
        self.dicom_files = {key: [] for key in self.file_types}
        self.plan_file_sets = {}
        self.uid_to_mrn = {}
        self.dicom_file_paths = {}
        self.other_dicom_files = {}

        self.start()  # begin thread

    def get_queue(self):
        file_paths = get_file_paths(self.start_path, search_subfolders=self.search_subfolders)
        file_count = len(file_paths)
        queue = Queue()

        for file_index, file_path in enumerate(file_paths):
            msg = {'label': "File Name: %s" % os.path.basename(file_path),
                   'gauge': file_index / file_count}
            queue.put((file_path, msg))

        return queue

    def run(self):
        """
        Begin the thread to parse directory. Returns plan_file_sets and dicom_file_paths through pubsub
        """

        queue = self.get_queue()
        worker = Thread(target=self.do_parse, args=[queue])
        worker.setDaemon(True)
        worker.start()
        queue.join()

        self.do_association()

        msg = {'label': "Complete",
               'gauge': 1.}
        wx.CallAfter(pub.sendMessage, "pre_import_progress_update", msg=msg)
        sleep(0.3)

        wx.CallAfter(pub.sendMessage, 'dicom_directory_parser_set_file_tree',
                     tree=self.plan_file_sets, file_paths=self.dicom_file_paths,
                     other_dicom_files=self.other_dicom_files)

    def do_parse(self, queue):
        while queue.qsize():
            parameters = queue.get()
            self.parser(*parameters)
            queue.task_done()

    def parser(self, file_path, msg):

        wx.CallAfter(pub.sendMessage, "pre_import_progress_update", msg=msg)

        try:
            ds = dicom.read_file(file_path, stop_before_pixels=True, force=True)
        except InvalidDicomError:
            ds = None
        except MemoryError as e:
            # MIM metacache files throw memory errors instead of InvalidDicomError
            if 'metacache.mim' in file_path:
                ds = None
            else:
                raise MemoryError

        if ds is not None:

            if not self.is_data_set_valid(ds):
                print('Cannot parse %s\nOne of these tags is missing: %s' % (file_path, ', '.join(self.req_tags)))
            else:
                modality = ds.Modality.lower()
                timestamp = os.path.getmtime(file_path)

                self.dicom_tag_values[file_path] = {'timestamp': timestamp,
                                                    'study_instance_uid': ds.StudyInstanceUID,
                                                    'sop_instance_uid': ds.SOPInstanceUID,
                                                    'patient_name': ds.PatientName,
                                                    'mrn': ds.PatientID}
                if modality not in self.file_types:
                    if ds.StudyInstanceUID not in self.other_dicom_files.keys():
                        self.other_dicom_files[ds.StudyInstanceUID] = []
                    self.other_dicom_files[ds.StudyInstanceUID].append(file_path)  # Store these to move after import
                else:
                    self.dicom_files[modality].append(file_path)

                    # All RT Plan files need to be found first
                    if modality == 'rtplan':
                        uid = ds.ReferencedStructureSetSequence[0].ReferencedSOPInstanceUID
                        mrn = self.dicom_tag_values[file_path]['mrn']
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
                                                                                    'sop_instance_uid': plan_uid},
                                                                         'rtstruct': {'file_path': None,
                                                                                      'sop_instance_uid': None},
                                                                         'rtdose': {'file_path': None,
                                                                                    'sop_instance_uid': None}}
                        if plan_uid not in self.dicom_file_paths.keys():
                            self.dicom_file_paths[plan_uid] = {key: [] for key in self.file_types + ['other']}
                        self.dicom_file_paths[plan_uid]['rtplan'] = [file_path]

                    elif modality == 'rtdose':
                        uid = ds.ReferencedRTPlanSequence[0].ReferencedSOPInstanceUID
                        self.dicom_tag_values[file_path]['ref_sop_instance'] = {'type': 'plan',
                                                                                'uid': uid}
                    else:
                        self.dicom_tag_values[file_path]['ref_sop_instance'] = {'type': None,
                                                                                'uid': None}

    def do_association(self):
        # associate appropriate rtdose files to plans
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
                    if 'rtdose' in self.dicom_file_paths[plan_uid].keys():
                        self.dicom_file_paths[plan_uid]['rtdose'].append(dose_file)
                    else:
                        self.dicom_file_paths[plan_uid]['rtdose'] = [dose_file]

        # associate appropriate rtstruct files to plans
        for mrn_index, mrn in enumerate(list(self.plan_file_sets)):
            for study_uid in list(self.plan_file_sets[mrn]):
                for plan_uid, plan_file_set in self.plan_file_sets[mrn][study_uid].items():
                    plan_file = plan_file_set['rtplan']['file_path']
                    ref_struct_uid = self.dicom_tag_values[plan_file]['ref_sop_instance']['uid']
                    for struct_file in self.dicom_files['rtstruct']:
                        struct_uid = self.dicom_tag_values[struct_file]['sop_instance_uid']
                        if struct_uid == ref_struct_uid:
                            plan_file_set['rtstruct'] = {'file_path': struct_file,
                                                         'sop_instance_uid': struct_uid}
                            if 'rtstruct' in self.dicom_file_paths[plan_uid].keys():
                                self.dicom_file_paths[plan_uid]['rtstruct'].append(struct_file)
                            else:
                                self.dicom_file_paths[plan_uid]['rtstruct'] = [struct_file]

    def is_data_set_valid(self, ds):
        for tag in self.req_tags:
            if not hasattr(ds, tag):
                return False
        return True


class PreImportFileSetParserWorker(Thread):
    def __init__(self, file_paths):
        Thread.__init__(self)

        pub.sendMessage("pre_import_progress_set_title", msg='Parsing File Sets')

        self.file_paths = file_paths
        self.total_plan_count = len(self.file_paths)

        self.start()

    def run(self):
        queue = self.get_queue()
        worker = Thread(target=self.do_parse, args=[queue])
        worker.setDaemon(True)
        worker.start()
        queue.join()
        sleep(0.3)  # Allow time for user to see final progress in GUI
        pub.sendMessage('pre_import_progress_close')

    def get_queue(self):
        queue = Queue()
        for plan_counter, uid in enumerate(list(self.file_paths)):
            if self.file_paths[uid]['rtplan'] and self.file_paths[uid]['rtstruct'] and self.file_paths[uid]['rtdose']:
                init_params = {'plan_file': self.file_paths[uid]['rtplan'][0],
                               'structure_file': self.file_paths[uid]['rtstruct'][0],
                               'dose_file': self.file_paths[uid]['rtdose'][0]}
                msg = {'label': 'Parsing File Set %s of %s' % (plan_counter+1, self.total_plan_count),
                       'gauge': plan_counter / self.total_plan_count}
                queue.put((uid, init_params, msg))
        return queue

    def do_parse(self, queue):
        while queue.qsize():
            parameters = queue.get()
            self.parser(*parameters)
            queue.task_done()

        plan_count = self.total_plan_count
        msg = {'label': 'Parsing Complete: %s fileset%s' % (plan_count, ['', 's'][plan_count != 1]),
               'gauge': 1.}
        pub.sendMessage("pre_import_progress_update", msg=msg)

    def parser(self, uid, init_params, msg):
        pub.sendMessage("pre_import_progress_update", msg=msg)

        pre_import_data = DICOM_Parser(**init_params).pre_import_data
        msg = {'uid': uid, 'init_params': pre_import_data}
        pub.sendMessage("set_pre_import_parsed_dicom_data", msg=msg)
