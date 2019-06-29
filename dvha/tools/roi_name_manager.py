#!/usr/bin/env python
# -*- coding: utf-8 -*-

# tools.roi_name_manager.py
"""
Code to create and edit a the roi name mapping, calculate data used to plot map

"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import os
from shutil import copyfile
from copy import deepcopy
import difflib
from dvha.db.sql_to_python import QuerySQL
from dvha.db.sql_connector import DVH_SQL
from dvha.paths import PREF_DIR, SCRIPT_DIR
from dvha.tools.utilities import flatten_list_of_lists, initialize_directories_and_settings
from dvha.tools.errors import ROIVariationError


class Physician:
    """
    Represents a physician in the roi map
    """
    def __init__(self, initials):
        """
        :param initials: the label to be used to represent the physician, should be all upper case
        """
        self.initials = initials

        self.physician_rois = {}

    def add_physician_roi(self, institutional_roi, physician_roi):
        institutional_roi = clean_name(institutional_roi)
        physician_roi = clean_name(physician_roi)
        self.physician_rois[physician_roi] = {'institutional_roi': institutional_roi,
                                              'variations': [physician_roi]}

    def add_physician_roi_variation(self, physician_roi, variation):
        physician_roi = clean_name(physician_roi)
        variation = clean_name(variation)
        if physician_roi in list(self.physician_rois):
            if variation not in self.physician_rois[physician_roi]['variations']:
                self.physician_rois[physician_roi]['variations'].append(variation)
                self.physician_rois[physician_roi]['variations'].sort()

    def delete_physician_roi_variations(self, physician_roi):
        self.physician_rois[physician_roi]['variations'] = [physician_roi]

    def delete_all_physician_roi_variations(self):
        for physician_roi in list(self.physician_rois):
            self.delete_physician_roi_variations(physician_roi)


class DatabaseROIs:
    """
    The main class, creating an instance of this class will open a stored map, or create the default map
    """
    def __init__(self):

        self.physicians = {}
        self.institutional_rois = []

        # Copy default ROI files to user folder if they do not exist
        if not os.path.isfile(os.path.join(PREF_DIR, 'institutional.roi')):
            initialize_directories_and_settings()
            initialize_roi_preference_file('institutional.roi')
            initialize_roi_preference_file('physician_BBM.roi')

        self.branched_institutional_rois = {}
        self.import_from_file()

    def import_from_file(self):
        self.physicians = {}
        self.institutional_rois = []
        # Import institutional roi names
        abs_file_path = os.path.join(PREF_DIR, 'institutional.roi')
        if os.path.isfile(abs_file_path):
            with open(abs_file_path, 'r') as document:
                for line in document:
                    if not line:
                        continue
                    line = clean_name(str(line))
                    self.institutional_rois.append(line)

        physicians = get_physicians_from_roi_files()
        for physician in physicians:
            self.add_physician(physician, add_institutional_rois=(physician == 'DEFAULT'))

        self.import_physician_roi_maps()

        if 'uncategorized' not in self.institutional_rois:
            self.institutional_rois.append('uncategorized')

        self.branched_institutional_rois = {}

    ##############################################
    # Import from file functions
    ##############################################
    def import_physician_roi_maps(self):

        for physician in list(self.physicians):
            rel_path = 'physician_%s.roi' % physician
            abs_file_path = os.path.join(PREF_DIR, rel_path)
            if os.path.isfile(abs_file_path):
                self.import_physician_roi_map(abs_file_path, physician)

    def import_physician_roi_map(self, abs_file_path, physician):

        with open(abs_file_path, 'r') as document:
            for line in document:
                if not line:
                    continue
                line = str(line).lower().strip().replace(':', ',').split(',')
                institutional_roi = line[0].strip()
                physician_roi = line[1].strip()

                self.add_institutional_roi(institutional_roi)
                self.add_physician_roi(physician, institutional_roi, physician_roi)

                for i in range(2, len(line)):
                    variation = clean_name(line[i])
                    if variation != physician_roi:
                        self.add_variation(physician, physician_roi, variation)

    ###################################
    # Physician functions
    ###################################
    def add_physician(self, physician, add_institutional_rois=True):
        physician = clean_name(physician).upper()
        if physician not in self.get_physicians():
            self.physicians[physician] = Physician(physician)

        if add_institutional_rois:
            for institutional_roi in self.institutional_rois:
                self.add_physician_roi(physician, institutional_roi, institutional_roi)

    def copy_physician(self, new_physician, copy_from=None, include_variations=True):
        new_physician = clean_name(new_physician).upper()
        if copy_from is None or copy_from == 'DEFAULT':
            self.add_physician(new_physician)
        elif copy_from in self.get_physicians():
            self.physicians[new_physician] = deepcopy(self.physicians[copy_from])
            if not include_variations:
                self.physicians[new_physician].delete_all_physician_roi_variations()

    def delete_physician(self, physician):
        physician = clean_name(physician).upper()
        self.physicians.pop(physician, None)

    def get_physicians(self):
        physicians = list(self.physicians)
        physicians.sort()
        if 'DEFAULT' in physicians:
            physicians.pop(physicians.index('DEFAULT'))
            physicians.insert(0, 'DEFAULT')
        return physicians

    def get_physician(self, physician):
        return self.physicians[physician]

    def is_physician(self, physician):
        physician = clean_name(physician).upper()
        for initials in self.get_physicians():
            if physician == initials:
                return True
        return False

    def rename_physician(self, new_physician, physician):
        new_physician = clean_name(new_physician).upper()
        physician = clean_name(physician).upper()
        self.physicians[new_physician] = self.physicians.pop(physician)

    def rebuild_default_physician(self):
        self.delete_physician('DEFAULT')
        self.add_physician('DEFAULT', add_institutional_rois=True)

    #################################
    # Institutional ROI functions
    #################################
    def get_institutional_rois(self):
        return self.institutional_rois

    def get_institutional_roi(self, physician, physician_roi):
        physician = clean_name(physician).upper()
        physician_roi = clean_name(physician_roi)
        if physician == 'DEFAULT':
            return physician_roi
        else:
            return self.physicians[physician].physician_rois[physician_roi]['institutional_roi']

    def add_institutional_roi(self, roi):
        roi = clean_name(roi)
        if roi not in self.institutional_rois:
            self.institutional_rois.append(roi)
            self.institutional_rois.sort()

    def rename_institutional_roi(self, new_institutional_roi, institutional_roi):
        new_institutional_roi = clean_name(new_institutional_roi)
        institutional_roi = clean_name(institutional_roi)
        index = self.institutional_rois.index(institutional_roi)
        self.institutional_rois.pop(index)
        self.add_institutional_roi(new_institutional_roi)
        for physician in self.get_physicians():
            if physician != 'DEFAULT':
                for physician_roi in self.get_physician_rois(physician):
                    physician_roi_obj = self.physicians[physician].physician_rois[physician_roi]
                    if physician_roi_obj['institutional_roi'] == institutional_roi:
                        physician_roi_obj['institutional_roi'] = new_institutional_roi
        self.rebuild_default_physician()

    def set_linked_institutional_roi(self, new_institutional_roi, physician, physician_roi):
        self.physicians[physician].physician_rois[physician_roi]['institutional_roi'] = new_institutional_roi

    def delete_institutional_roi(self, roi):
        self.rename_institutional_roi('uncategorized', roi)

    def is_institutional_roi(self, roi):
        roi = clean_name(roi)
        for institutional_roi in self.institutional_rois:
            if roi == institutional_roi:
                return True
        return False

    def get_unused_institutional_rois(self, physician):
        physician = clean_name(physician).upper()
        used_rois = []
        if self.get_physician_rois(physician)[0] != '':
            for physician_roi in self.get_physician_rois(physician):
                used_rois.append(self.get_institutional_roi(physician, physician_roi))

        unused_rois = []
        for roi in self.institutional_rois:
            if roi not in used_rois:
                unused_rois.append(roi)
        if 'uncategorized' not in unused_rois:
            unused_rois.append('uncategorized')

        return unused_rois

    ########################################
    # Physician ROI functions
    ########################################
    def get_physician_rois(self, physician):
        physician = clean_name(physician).upper()
        if self.is_physician(physician):
            physician_rois = list(self.physicians[physician].physician_rois)
            if physician_rois:
                physician_rois = list(set(physician_rois) - {'uncategorized'})
                physician_rois.sort()
                return physician_rois

        return []

    def get_physician_roi(self, physician, roi):
        physician = clean_name(physician).upper()
        roi = clean_name(roi)
        for physician_roi in self.get_physician_rois(physician):
            for variation in self.get_variations(physician, physician_roi):
                if roi == variation:
                    return physician_roi
        return 'uncategorized'

    def get_physician_roi_from_institutional_roi(self, physician, institutional_roi):
        physician = clean_name(physician).upper()
        institutional_roi = clean_name(institutional_roi)
        if institutional_roi == 'uncategorized':
            return institutional_roi
        for physician_roi in self.get_physician_rois(physician):
            if institutional_roi == self.get_institutional_roi(physician, physician_roi):
                return physician_roi
        return institutional_roi

    def add_physician_roi(self, physician, institutional_roi, physician_roi):
        physician = clean_name(physician).upper()
        institutional_roi = clean_name(institutional_roi)
        physician_roi = clean_name(physician_roi)
        if physician_roi not in self.get_physician_rois(physician):
            if institutional_roi in self.institutional_rois:
                self.physicians[physician].add_physician_roi(institutional_roi, physician_roi)

    def rename_physician_roi(self, new_physician_roi, physician, physician_roi):
        new_physician_roi = clean_name(new_physician_roi)
        physician = clean_name(physician).upper()
        physician_roi = clean_name(physician_roi)
        if new_physician_roi != physician_roi:
            self.physicians[physician].physician_rois[new_physician_roi] = \
                self.physicians[physician].physician_rois.pop(physician_roi, None)
        self.add_variation(physician, new_physician_roi, new_physician_roi)
        # self.delete_variation(physician, new_physician_roi, physician_roi)

    def delete_physician_roi(self, physician, physician_roi):
        physician = clean_name(physician).upper()
        physician_roi = clean_name(physician_roi)
        if physician_roi in self.get_physician_rois(physician):
            self.physicians[physician].physician_rois.pop(physician_roi, None)

    def is_physician_roi(self, roi, physician):
        roi = clean_name(roi)
        for physician_roi in self.get_physician_rois(physician):
            if roi == physician_roi:
                return True
        return False

    def get_unused_physician_rois(self, physician):
        physician = clean_name(physician).upper()

        unused_rois = []
        for physician_roi in self.get_physician_rois(physician):
            if self.get_institutional_roi(physician, physician_roi) == 'uncategorized':
                unused_rois.append(physician_roi)
        if not unused_rois:
            unused_rois = []

        return unused_rois

    def merge_physician_rois(self, physician, physician_rois, final_physician_roi):

        variation_lists = [self.get_variations(physician, physician_roi) for physician_roi in physician_rois]
        variations = flatten_list_of_lists(variation_lists, remove_duplicates=True)
        for variation in variations:
            self.add_variation(physician, final_physician_roi, variation, force=True)

        for physician_roi in physician_rois:
            if physician_roi != final_physician_roi:
                self.delete_physician_roi(physician, physician_roi)

    ###################################################
    # Variation-of-Physician-ROI functions
    ###################################################
    def get_variations(self, physician, physician_roi):
        physician = clean_name(physician).upper()
        physician_roi = clean_name(physician_roi)
        if physician_roi == 'uncategorized':
            return ['uncategorized']

        if self.is_physician_roi(physician_roi, physician):
            variations = self.physicians[physician].physician_rois[physician_roi]['variations']
            if variations:
                return variations
        return []

    def get_all_variations_of_physician(self, physician):
        physician = clean_name(physician).upper()
        variations = []
        for physician_roi in self.get_physician_rois(physician):
            for variation in self.get_variations(physician, physician_roi):
                variations.append(variation)
        if variations:
            variations.sort()
        else:
            variations = []
        return variations

    def is_variation_used(self, physician, variation):
        variation = clean_name(variation)
        return variation in self.get_all_variations_of_physician(physician)

    def add_variation(self, physician, physician_roi, variation, force=False):
        physician = clean_name(physician).upper()
        physician_roi = clean_name(physician_roi)
        variation = clean_name(variation)

        current_physician_roi = self.get_physician_roi(physician, variation)
        if force or current_physician_roi == 'uncategorized':
            self.physicians[physician].add_physician_roi_variation(physician_roi, variation)
        else:
            raise ROIVariationError("'%s' is already a variation of %s for %s" %
                                    (variation, current_physician_roi, physician))

    def delete_variation(self, physician, physician_roi, variation):
        physician = clean_name(physician).upper()
        physician_roi = clean_name(physician_roi)
        variation = clean_name(variation)
        if variation in self.get_variations(physician, physician_roi):
            index = self.physicians[physician].physician_rois[physician_roi]['variations'].index(variation)
            self.physicians[physician].physician_rois[physician_roi]['variations'].pop(index)
            self.physicians[physician].physician_rois[physician_roi]['variations'].sort()

    def delete_variations(self, physician, physician_roi, variations):
        for variation in variations:
            self.delete_variation(physician, physician_roi, variation)
        if not self.get_variations(physician, physician_roi):
            self.add_variation(physician, physician_roi, physician_roi)

    def set_variation(self, new_variation, physician, physician_roi, variation):
        new_variation = clean_name(new_variation)
        physician = clean_name(physician).upper()
        physician_roi = clean_name(physician_roi)
        variation = clean_name(variation)
        if new_variation != variation:
            self.add_variation(physician, physician_roi, new_variation)
            self.delete_variation(physician, physician_roi, variation)

    def is_roi(self, roi):
        roi = clean_name(roi)
        for physician in self.get_physicians():
            for physician_roi in self.get_physician_rois(physician):
                for variation in self.get_variations(physician, physician_roi):
                    if roi == variation:
                        return True
        return False

    ########################
    # Export to file
    ########################
    def write_to_file(self):
        self.write_institutional_file()
        for physician, data in self.physician_roi_file_data.items():
            self.write_physician_file(physician, data)
        self.remove_unused_roi_files()

    def write_institutional_file(self):
        file_name = 'institutional.roi'
        abs_file_path = os.path.join(PREF_DIR, file_name)
        with open(abs_file_path, 'w') as document:
            lines = self.institutional_rois
            lines.sort()
            lines = '\n'.join(lines)
            for line in lines:
                document.write(line)

    @property
    def physician_roi_file_data(self):
        physicians_file_data = {}
        for physician in self.get_physicians():
            if physician != 'DEFAULT':
                lines = []
                for physician_roi in self.get_physician_rois(physician):
                    institutional_roi = self.get_institutional_roi(physician, physician_roi)
                    variations = ', '.join(self.get_variations(physician, physician_roi))
                    lines.append(': '.join([institutional_roi, physician_roi, variations]))
                lines.sort()
                physicians_file_data[physician] = lines

        return physicians_file_data

    @staticmethod
    def write_physician_file(physician, lines):
        """
        Write the physician map to a .roi file
        :param physician: name of physicain
        :type physician: str
        :param lines: the lines of data to be written to the file
        :type lines: list of str
        """
        abs_file_path = os.path.join(PREF_DIR, 'physician_' + physician + '.roi')
        if lines:
            with open(abs_file_path, 'w') as document:
                for line in lines:
                    document.write(line + '\n')

    def remove_unused_roi_files(self):
        """
        Delete any physician .roi files that are no longer in the ROI map
        :return: the physicians that have been removed
        :rtype: list
        """
        for physician in self.deleted_physicians:
            file_name = 'physician_' + physician + '.roi'
            abs_file_path = os.path.join(PREF_DIR, file_name)
            os.remove(abs_file_path)

    @property
    def deleted_physicians(self):
        return list(set(get_physicians_from_roi_files()) - set(self.get_physicians()) - {'DEFAULT'})

    @property
    def added_physicians(self):
        return list(set(self.get_physicians()) - set(get_physicians_from_roi_files()) - {'DEFAULT'})

    def get_roi_map_changes(self):
        """
        Use difflib to detect changes between current roi map and previously saved .roi file
        format of returned dict: diff[physician][physician_roi][delta] = {'institutional': i_roi, 'variations': list}
        where delta is either '+' or '-' based on difflib.unified_diff output
        :return: a tiered dictionary of lines that changed in the proposed .roi file
        :rtype: dict
        """
        new_data = self.physician_roi_file_data
        diff = {}
        for physician in self.get_physicians():
            abs_file_path = os.path.join(PREF_DIR, 'physician_' + physician + '.roi')
            if os.path.isfile(abs_file_path):
                old_lines = [line.strip() for line in open(abs_file_path, 'r').readlines()]

                include = False
                diff[physician] = {}
                for line in difflib.unified_diff(old_lines, new_data[physician]):
                    if include:
                        if line[0] in {'+', '-'}:
                            i_roi, p_roi, variations = tuple(i for i in line.split(': '))
                            if p_roi not in diff[physician]:
                                diff[physician][p_roi] = {'-': {'institutional': '', 'variations': []},
                                                          '+': {'institutional': '', 'variations': []}}
                            diff[physician][p_roi][line[0]] = {'institutional': i_roi[1:],
                                                               'variations': variations.split(', ')}
                    else:
                        include = line[0] == '@'  # + and - signs before the @@ line to be ignored

                for p_roi, data in diff[physician].items():
                    new_pos = list(set(data['+']['variations']) - set(data['-']['variations']))
                    new_neg = list(set(data['-']['variations']) - set(data['+']['variations']))
                    if new_pos:
                        data['+']['variations'] = new_pos
                    else:
                        data.pop('+')
                    if new_neg:
                        data['-']['variations'] = new_neg
                    else:
                        data.pop('-')

        return diff

    @property
    def physicians_to_remap(self):
        return list(set(self.deleted_physicians + self.added_physicians))

    @property
    def variations_to_update(self):
        """
        :return: all variations that have changed physician or institutional rois, in a dict with physician for the key
        :rtype: dict
        """
        changes = self.get_roi_map_changes()
        variations_to_update = {}
        for physician, physician_roi_data in changes.items():
            variations = []
            for p_roi_data in physician_roi_data.values():
                for delta_data in p_roi_data.values():
                    variations.extend(delta_data['variations'])
            variations_to_update[physician] = list(set(variations))

        for physician in list(variations_to_update):
            if not variations_to_update[physician]:
                variations_to_update.pop(physician)

        return variations_to_update

    def remap_rois(self):

        with DVH_SQL() as cnx:
            for physician, variations in self.variations_to_update.items():
                for variation in variations:
                    new_physician_roi = self.get_physician_roi(physician, variation)
                    new_institutional_roi = self.get_institutional_roi(physician, new_physician_roi)

                    condition = "REPLACE(REPLACE(LOWER(roi_name), '\'', '`'), '_', ' ') == '%s'" % variation
                    sql_query = "SELECT DISTINCT study_instance_uid, roi_name FROM DVHs WHERE %s;" % condition
                    uids_roi_names = cnx.query_generic(sql_query)
                    uids = [row[0] for row in uids_roi_names]
                    roi_names = [row[1] for row in uids_roi_names]

                    if uids:
                        for i, uid in enumerate(uids):
                            roi_name = roi_names[i]
                            condition = "roi_name = '%s' and study_instance_uid = '%s'" % (roi_name, uid)
                            cnx.update('dvhs', 'physician_roi', new_physician_roi, condition)
                            cnx.update('dvhs', 'institutional_roi', new_institutional_roi, condition)

        self.write_to_file()

    ################
    # Plotting tools
    ################
    def get_physician_roi_visual_coordinates(self, physician, physician_roi):

        # All 0.5 subtractions due to a workaround of a Bokeh 0.12.9 bug

        institutional_roi = self.get_institutional_roi(physician, physician_roi)

        # x and y are coordinates for the circles
        # x0, y0 is beggining of line segment, x1, y1 is end of line-segment
        if institutional_roi == 'uncategorized':
            table = {'name': [physician_roi],
                     'x': [2 - 0.5],
                     'y': [0],
                     'x0': [2 - 0.5],
                     'y0': [0],
                     'x1': [2 - 0.5],
                     'y1': [0]}
        else:
            table = {'name': [institutional_roi, physician_roi],
                     'x': [1 - 0.5, 2 - 0.5],
                     'y': [0, 0],
                     'x0': [1 - 0.5, 2 - 0.5],
                     'y0': [0, 0],
                     'x1': [2 - 0.5, 1 - 0.5],
                     'y1': [0, 0]}

        variations = self.get_variations(physician, physician_roi)
        for i, variation in enumerate(variations):
            y = -i
            table['name'].append(variation)
            table['x'].append(3 - 0.5)
            table['y'].append(y)
            table['x0'].append(2 - 0.5)
            table['y0'].append(0)
            table['x1'].append(3 - 0.5)
            table['y1'].append(y)

        table_length = len(table['name'])
        table['color'] = ['#1F77B4'] * table_length
        table['institutional_roi'] = [institutional_roi] * table_length
        table['physician_roi'] = [physician_roi] * table_length

        return table

    def get_all_institutional_roi_visual_coordinates(self, physician, ignored_physician_rois=None):
        if ignored_physician_rois is None:
            ignored_physician_rois = []

        p_rois = [roi for roi in self.get_physician_rois(physician) if roi not in ignored_physician_rois]
        i_rois = [self.get_institutional_roi(physician, p_roi) for p_roi in p_rois]
        for i, i_roi in enumerate(i_rois):
            if i_roi == 'uncategorized':
                i_rois[i] = 'zzzzzzzzzzzzzzzzzzz'
        sorted_indices = [i[0] for i in sorted(enumerate(i_rois), key=lambda x:x[1])]
        p_rois_sorted = [p_rois[i] for i in sorted_indices]
        p_rois = p_rois_sorted

        tables = {p_roi: self.get_physician_roi_visual_coordinates(physician, p_roi) for p_roi in p_rois}
        heights = [3 - min(tables[p_roi]['y']) for p_roi in p_rois]

        max_y_delta = sum(heights) + 2  # include 2 buffer to give space to read labels on plot
        for i, p_roi in enumerate(p_rois):
            y_delta = sum(heights[i:])

            for key in ['y', 'y0', 'y1']:
                for j in range(len(tables[p_roi][key])):
                    tables[p_roi][key][j] += y_delta - max_y_delta

        if p_rois and p_rois[0] in tables:
            table = tables[p_rois[0]]
            for i in range(1, len(p_rois)):
                for key in list(table):
                    table[key].extend(tables[p_rois[i]][key])

            return self.update_duplicate_y_entries(table, physician)
        return None

    @staticmethod
    def get_roi_visual_y_values(table):
        y_values = {}
        for i, x in enumerate(table['x']):
            if x == 1 - 0.5:
                name = table['name'][i]
                y = table['y'][i]
                if name not in list(y_values):
                    y_values[name] = []
                y_values[name].append(y)
        for name in list(y_values):
            y_values[name] = sum(y_values[name]) / len(y_values[name])
        return y_values

    def update_duplicate_y_entries(self, table, physician):

        y_values = self.get_roi_visual_y_values(table)

        self.branched_institutional_rois[physician] = []

        for i, name in enumerate(table['name']):
            if table['x'][i] == 1 - 0.5 and table['y'][i] != y_values[name]:
                table['y'][i] = y_values[name]
                table['y0'][i] = y_values[name]
                table['color'][i] = 'red'
                self.branched_institutional_rois[physician].append(name)
            if table['x'][i] == 2 - 0.5:
                inst_name = self.get_institutional_roi(physician, name)
                if inst_name != 'uncategorized':
                    table['y1'][i] = y_values[inst_name]

        if self.branched_institutional_rois[physician]:
            self.branched_institutional_rois[physician] = list(set(self.branched_institutional_rois[physician]))

        return table

    @property
    def tree(self):
        return {physician: self.get_physician_tree(physician) for physician in self.get_physicians()}

    def get_physician_tree(self, physician):
        phys_rois = self.get_physician_rois(physician)
        unused_inst_rois = self.get_unused_institutional_rois(physician)
        all_inst_rois = self.get_institutional_rois()
        inst_rois = [roi for roi in all_inst_rois if roi not in unused_inst_rois]
        linked_phys_rois = [self.get_physician_roi_from_institutional_roi(physician, roi) for roi in inst_rois]
        unlinked_phys_rois = [roi for roi in phys_rois if roi not in linked_phys_rois]
        linked_phys_roi_tree = {roi: self.get_variations(physician, roi) for roi in linked_phys_rois
                                if roi != 'uncategorized'}
        unlinked_phys_roi_tree = {roi: self.get_variations(physician, roi) for roi in unlinked_phys_rois
                                  if roi != 'uncategorized'}
        return {'Linked to Institutional ROI': linked_phys_roi_tree,
                'Unlinked to Institutional ROI': unlinked_phys_roi_tree}


def clean_name(name):
    return str(name).lower().strip().replace('\'', '`').replace('_', ' ')


def get_physicians_from_roi_files():

    physicians = ['DEFAULT']
    for file_name in os.listdir(PREF_DIR):
        if file_name.startswith("physician_") and file_name.endswith(".roi"):
            physician = file_name.replace('physician_', '').replace('.roi', '')
            physician = clean_name(physician).upper()
            physicians.append(physician)

    return physicians


def get_physician_from_uid(uid):
    with DVH_SQL() as cnx:
        results = cnx.query('Plans', 'physician', "study_instance_uid = '" + uid + "'")

    if len(results) > 1:
        print('Warning: multiple plans with this study_instance_uid exist')

    return str(results[0][0])


def update_uncategorized_rois_in_database():
    roi_map = DatabaseROIs()
    dvh_data = QuerySQL('DVHs', "physician_roi = 'uncategorized'")

    with DVH_SQL() as cnx:
        for i in range(len(dvh_data.roi_name)):
            uid = dvh_data.study_instance_uid[i]
            mrn = dvh_data.mrn[i]
            physician = get_physician_from_uid(uid)
            roi_name = dvh_data.roi_name[i]

            new_physician_roi = roi_map.get_physician_roi(physician, roi_name)
            new_institutional_roi = roi_map.get_institutional_roi(physician, roi_name)

            if new_physician_roi != 'uncategorized':
                print(mrn, physician, new_institutional_roi, new_physician_roi, roi_name, sep=' ')
                condition = "study_instance_uid = '" + uid + "'" + "and roi_name = '" + roi_name + "'"
                cnx.update('DVHs', 'physician_roi', new_physician_roi, condition)
                cnx.update('DVHs', 'institutional_roi', new_institutional_roi, condition)


def initialize_roi_preference_file(rel_file_name):
    roi_files_user = [f for f in os.listdir(PREF_DIR) if '.roi' in f]
    if rel_file_name not in roi_files_user:
        src = os.path.join(SCRIPT_DIR, 'db', rel_file_name)
        dest = os.path.join(PREF_DIR, rel_file_name)
        copyfile(src, dest)
