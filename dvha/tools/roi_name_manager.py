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
from copy import deepcopy
import difflib
from dvha.db.sql_to_python import QuerySQL
from dvha.db.sql_connector import DVH_SQL
from dvha.paths import PREF_DIR
from dvha.tools.roi_map_generator import ROIMapGenerator
from dvha.tools.errors import push_to_log
from dvha.tools.utilities import (
    flatten_list_of_lists,
    initialize_directories,
    csv_to_list,
)


class PhysicianROI:
    """ """

    def __init__(self, physician_roi, institutional_roi=None, roi_type="NONE"):
        self.institutional_roi = (
            institutional_roi
            if institutional_roi is not None
            else "uncategorized"
        )
        self.physician_roi = physician_roi
        self.variations = [physician_roi]
        self.roi_type = roi_type
        self.roi_type_is_edited = False

        self.add_variations(self.institutional_roi)

    def __contains__(self, variation):
        return clean_name(variation) in self.clean_variations

    def add_variations(self, variations):
        """

        Parameters
        ----------
        variations :


        Returns
        -------

        """
        if type(variations) is not list:
            variations = [variations]
        variations = [v.replace('"', "`") for v in variations]
        clean_variations = self.clean_variations
        for variation in variations:
            if clean_name(
                variation
            ) not in clean_variations and variation.lower() not in {
                "uncategorized"
            }:
                self.variations.append(variation)

    def get_variation(self, variation):
        """

        Parameters
        ----------
        variation :


        Returns
        -------

        """
        clean_variation = variation
        clean_variations = self.clean_variations
        if clean_variation in clean_variations:
            index = clean_variations.index(clean_variation)
            return self.variations[index]

    @property
    def clean_variations(self):
        """ """
        return [clean_name(v) for v in self.variations]

    @property
    def clean_top_level(self):
        """ """
        return [
            clean_name(v) for v in [self.institutional_roi, self.physician_roi]
        ]

    def del_variation(self, variations):
        """

        Parameters
        ----------
        variations :


        Returns
        -------

        """
        if type(variations) is not list:
            variations = list(variations)

        for v in variations:
            cv = clean_name(v)
            if cv in self.clean_variations and cv not in self.clean_top_level:
                index = self.clean_variations.index(cv)
                self.variations.pop(index)

    def del_all_variations(self):
        """ """
        self.variations = [self.physician_roi]
        if self.institutional_roi.lower() != "uncategorized" and clean_name(
            self.institutional_roi
        ) != clean_name(self.physician_roi):
            self.variations.append(self.institutional_roi)

    def set_institutional_roi(self, new):
        """

        Parameters
        ----------
        new :


        Returns
        -------

        """
        clean_old = clean_name(self.institutional_roi)
        if clean_old in self.clean_variations and clean_old != clean_name(
            self.physician_roi
        ):
            index = self.clean_variations.index(clean_old)
            self.variations.pop(index)

        self.institutional_roi = new
        self.add_variations(new)


class Physician:
    """Represents a physician in the roi map

    Parameters
    ----------
    name : str
        the label to be used to represent the physician, should be all upper case

    Returns
    -------

    """

    def __init__(self, name):

        self.name = name
        self.rois = {}

    def __contains__(self, variation):
        return clean_name(variation) in self.all_clean_variations

    def add_physician_roi(
        self,
        institutional_roi,
        physician_roi,
        variations=None,
        roi_type="NONE",
    ):
        """

        Parameters
        ----------
        institutional_roi :

        physician_roi :

        variations :
             (Default value = None)
        roi_type :
             (Default value = 'NONE')

        Returns
        -------

        """
        physician_roi = physician_roi.replace(":", "^").replace('"', "'")
        self.rois[physician_roi] = PhysicianROI(
            physician_roi, institutional_roi, roi_type
        )
        if variations is not None:
            self.add_variations(physician_roi, variations)

    def del_physician_roi(self, physician_roi):
        """

        Parameters
        ----------
        physician_roi :


        Returns
        -------

        """
        clean_roi = clean_name(physician_roi)
        clean_rois_map = self.clean_physician_rois_map
        if clean_roi in list(clean_rois_map):
            self.rois.pop(clean_rois_map[clean_roi], None)

    def add_variations(self, physician_roi, variations):
        """

        Parameters
        ----------
        physician_roi :

        variations :


        Returns
        -------

        """
        if physician_roi in list(self.rois):
            self.rois[physician_roi].add_variations(variations)

    def del_variations(self, physician_roi, variations):
        """

        Parameters
        ----------
        physician_roi :

        variations :


        Returns
        -------

        """
        if physician_roi in list(self.rois):
            self.rois[physician_roi].del_variation(variations)

    def delete_all_variations(self, physician_roi=None):
        """

        Parameters
        ----------
        physician_roi :
             (Default value = None)

        Returns
        -------

        """
        physician_rois = (
            [physician_roi] if physician_roi is None else list(self.rois)
        )
        for physician_roi in physician_rois:
            self.rois[physician_roi].del_all_variations()

    @property
    def all_variations(self):
        """ """
        variations = []
        for physician_roi in self.rois.values():
            variations.extend(physician_roi.variations)
        return variations

    def get_variations(self, physician_roi):
        """

        Parameters
        ----------
        physician_roi :


        Returns
        -------

        """
        clean_physician_roi = clean_name(physician_roi)
        clean_map = self.clean_physician_rois_map
        if clean_physician_roi in list(clean_map):
            return self.rois[clean_map[clean_physician_roi]].variations

    @property
    def all_clean_variations(self):
        """ """
        return [clean_name(v) for v in self.all_variations]

    @property
    def institutional_rois(self):
        """ """
        return [
            physician_roi.institutional_roi
            for physician_roi in self.rois.values()
        ]

    @property
    def clean_institutional_rois_map(self):
        """ """
        return {clean_name(roi): roi for roi in self.institutional_rois}

    @property
    def clean_physician_rois(self):
        """ """
        return [clean_name(roi) for roi in list(self.rois)]

    @property
    def clean_physician_rois_map(self):
        """ """
        return {clean_name(roi): roi for roi in self.rois}

    def get_institutional_roi(self, variation, return_physician_roi=False):
        """

        Parameters
        ----------
        variation :

        return_physician_roi :
             (Default value = False)

        Returns
        -------

        """
        for physician_roi_str, physician_roi in self.rois.items():
            if variation in physician_roi:
                if return_physician_roi:
                    return physician_roi.institutional_roi, physician_roi_str
                return physician_roi.institutional_roi

        if return_physician_roi:
            return None, None

    def rename_institutional_roi(self, new, old):
        """

        Parameters
        ----------
        new :

        old :


        Returns
        -------

        """
        _, physician_roi_str = self.get_institutional_roi(
            old, return_physician_roi=True
        )
        if physician_roi_str is not None:
            self.rois[physician_roi_str].set_institutional_roi(new)

    def get_physician_roi(self, variation):
        """

        Parameters
        ----------
        variation :


        Returns
        -------

        """
        for physician_roi_str, physician_roi in self.rois.items():
            if variation in physician_roi:
                return physician_roi_str
        return "uncategorized"

    def is_physician_roi(self, physician_roi):
        """

        Parameters
        ----------
        physician_roi :


        Returns
        -------

        """
        return clean_name(physician_roi) in self.clean_physician_rois

    def rename_physician_roi(self, new, old):
        """

        Parameters
        ----------
        new :

        old :


        Returns
        -------

        """
        clean_old = clean_name(old)
        clean_rois = self.clean_physician_rois_map
        if clean_old in list(clean_rois):
            actual_old = clean_rois[clean_old]
            self.rois[new] = self.rois.pop(actual_old)
            self.rois[new].add_variations(new)
            self.rois[new].physician_roi = new

    def get_variation(self, variation):
        """

        Parameters
        ----------
        variation :


        Returns
        -------

        """
        for physician_roi in self.rois.values():
            ans = physician_roi.get_variation(variation)
            if ans is not None:
                return ans

    def get_roi_type(self, roi_name):
        """

        Parameters
        ----------
        roi_name :


        Returns
        -------

        """
        physician_roi = self.get_physician_roi(roi_name)
        if physician_roi == "uncategorized":
            return "NONE"
        return self.rois[physician_roi].roi_type

    def set_roi_type(self, roi_name, roi_type):
        """

        Parameters
        ----------
        roi_name :

        roi_type :


        Returns
        -------

        """
        physician_roi = self.get_physician_roi(roi_name)
        if physician_roi != "uncategorized":
            self.rois[physician_roi].roi_type = roi_type
            self.rois[physician_roi].roi_type_is_edited = True

    @property
    def physician_rois_with_edited_roi_type(self):
        """ """
        return [
            p_roi for p_roi, obj in self.rois.items() if obj.roi_type_is_edited
        ]


class DatabaseROIs:
    """The main class, creating an instance of this class will open a stored map, or create the default map"""

    def __init__(self):

        self.physicians = {}
        self.institutional_rois = []

        if not os.path.isdir(PREF_DIR):
            initialize_directories()

        self.physicians_from_file = None
        self.branched_institutional_rois = {}
        self.import_from_file()

    def import_from_file(self):
        """ """
        self.physicians_from_file = get_physicians_from_roi_files()
        self.physicians = {}
        self.institutional_rois = []

        if "DEFAULT" in self.physicians_from_file:
            abs_file_path = os.path.join(PREF_DIR, "physician_DEFAULT.roi")
            self.import_physician_roi_map(abs_file_path, "DEFAULT")
        else:
            self.institutional_rois = ROIMapGenerator().primary_names
            self.add_physician("DEFAULT")

        for physician in self.physicians_from_file:
            self.add_physician(physician)

        self.import_physician_roi_maps()

        if "uncategorized" not in self.institutional_rois:
            self.institutional_rois.append("uncategorized")

        self.branched_institutional_rois = {}

    ##############################################
    # Import from file functions
    ##############################################
    def import_physician_roi_maps(self):
        """ """

        for physician in get_physicians_from_roi_files():
            rel_path = "physician_%s.roi" % physician
            abs_file_path = os.path.join(PREF_DIR, rel_path)
            if os.path.isfile(abs_file_path):
                self.import_physician_roi_map(abs_file_path, physician)
            self.load_roi_types_from_file(physician)

    def import_physician_roi_map(self, abs_file_path, physician=None):
        """

        Parameters
        ----------
        abs_file_path :

        physician :
             (Default value = None)

        Returns
        -------

        """

        institutional_mode = physician == "DEFAULT"

        if physician is None:
            physician = os.path.splitext(os.path.basename(abs_file_path))[
                0
            ].split("physician_")[1]

        if physician not in list(self.physicians):
            self.add_physician(physician)

        with open(abs_file_path, "r") as document:
            for line in document:
                if not line:
                    continue
                line = (
                    str(line).strip().replace(":", ",", 1).replace(":", ",", 1)
                )
                line = csv_to_list(line)
                institutional_roi = line.pop(0)
                if institutional_mode:
                    self.add_institutional_roi(institutional_roi)
                else:
                    physician_roi = line.pop(0)
                    variations = [v.strip() for v in line]

                    self.add_physician_roi(
                        physician,
                        institutional_roi.strip(),
                        physician_roi.strip(),
                        variations,
                    )

    ###################################
    # Physician functions
    ###################################
    def get_physicians(self):
        """ """
        return ["DEFAULT"] + sorted(set(self.physicians) - {"DEFAULT"})

    def add_physician(self, physician):
        """

        Parameters
        ----------
        physician :


        Returns
        -------

        """
        physician = clean_name(physician, physician=True)
        if physician not in list(self.physicians):
            self.physicians[physician] = Physician(physician)

        if physician == "DEFAULT":
            for institutional_roi in self.institutional_rois:
                self.add_physician_roi(
                    physician, institutional_roi, institutional_roi
                )

    def copy_physician(
        self, new_physician, copy_from=None, include_variations=True
    ):
        """

        Parameters
        ----------
        new_physician :

        copy_from :
             (Default value = None)
        include_variations :
             (Default value = True)

        Returns
        -------

        """
        new_physician = clean_name(new_physician, physician=True)
        if copy_from is None or copy_from == "DEFAULT":
            self.add_physician(new_physician)
        elif copy_from in list(self.physicians):
            self.physicians[new_physician] = deepcopy(
                self.physicians[copy_from]
            )
            if not include_variations:
                self.physicians[new_physician].delete_all_variations()

    def delete_physician(self, physician):
        """

        Parameters
        ----------
        physician :


        Returns
        -------

        """
        if physician in list(self.physicians):
            self.physicians.pop(physician, None)

    def is_physician(self, physician):
        """

        Parameters
        ----------
        physician :


        Returns
        -------

        """
        return physician in list(self.physicians)

    def rename_physician(self, new_physician, physician):
        """

        Parameters
        ----------
        new_physician :

        physician :


        Returns
        -------

        """
        new_physician = clean_name(new_physician, physician=True)
        physician = clean_name(physician, physician=True)
        self.physicians[new_physician] = self.physicians.pop(physician)

    #################################
    # Institutional ROI functions
    #################################
    @property
    def clean_institutional_rois(self):
        """ """
        return [clean_name(roi) for roi in self.institutional_rois]

    def get_institutional_roi(self, physician, physician_roi):
        """

        Parameters
        ----------
        physician :

        physician_roi :


        Returns
        -------

        """
        if physician in list(self.physicians):
            if physician_roi in self.physicians[physician]:
                return self.physicians[physician].get_institutional_roi(
                    physician_roi
                )

    def add_institutional_roi(self, roi):
        """

        Parameters
        ----------
        roi :


        Returns
        -------

        """
        roi = roi.replace(":", "^").replace('"', "'")
        if clean_name(roi) not in self.clean_institutional_rois:
            self.institutional_rois.append(roi)
            self.add_physician_roi("DEFAULT", roi, roi)

    def rename_institutional_roi(self, new, old):
        """

        Parameters
        ----------
        new :

        old :


        Returns
        -------

        """
        if old in self.institutional_rois:
            index = self.institutional_rois.index(old)
            self.institutional_rois.pop(index)
            for physician in self.physicians.values():
                physician.rename_institutional_roi(new, old)
            if new != "uncategorized":
                self.add_institutional_roi(new)

    def set_linked_institutional_roi(
        self, new_institutional_roi, physician, physician_roi
    ):
        """

        Parameters
        ----------
        new_institutional_roi :

        physician :

        physician_roi :


        Returns
        -------

        """
        if physician in list(self.physicians) and physician_roi in list(
            self.physicians[physician].rois
        ):
            self.physicians[physician].rois[
                physician_roi
            ].set_institutional_roi(new_institutional_roi)

    def delete_institutional_roi(self, roi):
        """

        Parameters
        ----------
        roi :


        Returns
        -------

        """
        self.rename_institutional_roi("uncategorized", roi)
        self.delete_physician_roi("DEFAULT", roi)

    def is_institutional_roi(self, roi):
        """

        Parameters
        ----------
        roi :


        Returns
        -------

        """
        return clean_name(roi) in self.clean_institutional_rois

    def get_unused_institutional_rois(self, physician):
        """

        Parameters
        ----------
        physician :


        Returns
        -------

        """
        physician = clean_name(physician, physician=True)
        used_rois = []
        if physician in list(self.physicians):
            used_rois = self.physicians[physician].institutional_rois

        unused_rois = []
        for roi in self.institutional_rois:
            if roi not in used_rois:
                unused_rois.append(roi)
        if "uncategorized" not in unused_rois:
            unused_rois.append("uncategorized")

        return unused_rois

    ########################################
    # Physician ROI functions
    ########################################
    def get_physician_rois(self, physician):
        """

        Parameters
        ----------
        physician :


        Returns
        -------

        """
        physician = clean_name(physician, physician=True)
        if physician in list(self.physicians):
            return sorted(list(self.physicians[physician].rois))
        return []

    def get_physician_roi(self, physician, roi):
        """

        Parameters
        ----------
        physician :

        roi :


        Returns
        -------

        """
        physician = clean_name(physician, physician=True)
        if physician in self.physicians:
            ans = self.physicians[physician].get_physician_roi(roi)
            if ans:
                return ans
        return "uncategorized"

    def get_physician_roi_from_institutional_roi(
        self, physician, institutional_roi
    ):
        """

        Parameters
        ----------
        physician :

        institutional_roi :


        Returns
        -------

        """
        physician = clean_name(physician, physician=True)
        if physician in list(self.physicians):
            return self.physicians[physician].get_physician_roi(
                institutional_roi
            )

    def add_physician_roi(
        self, physician, institutional_roi, physician_roi, variations=None
    ):
        """

        Parameters
        ----------
        physician :

        institutional_roi :

        physician_roi :

        variations :
             (Default value = None)

        Returns
        -------

        """
        self.add_institutional_roi(
            institutional_roi
        )  # will skip if already exists
        if physician in list(self.physicians):
            self.physicians[physician].add_physician_roi(
                institutional_roi, physician_roi, variations
            )

    def rename_physician_roi(
        self, new_physician_roi, physician, physician_roi
    ):
        """

        Parameters
        ----------
        new_physician_roi :

        physician :

        physician_roi :


        Returns
        -------

        """
        if physician in list(self.physicians):
            self.physicians[physician].rename_physician_roi(
                new_physician_roi, physician_roi
            )

    def delete_physician_roi(self, physician, physician_roi):
        """

        Parameters
        ----------
        physician :

        physician_roi :


        Returns
        -------

        """
        physician = clean_name(physician, physician=True)
        if physician in list(self.physicians):
            self.physicians[physician].del_physician_roi(physician_roi)

    def is_physician_roi(self, roi, physician):
        """

        Parameters
        ----------
        roi :

        physician :


        Returns
        -------

        """
        physician = clean_name(physician, physician=True)
        if physician in list(self.physicians):
            return self.physicians[physician].is_physician_roi(roi)

    def get_unused_physician_rois(self, physician):
        """

        Parameters
        ----------
        physician :


        Returns
        -------

        """
        physician = clean_name(physician, physician=True)

        unused_rois = []
        for physician_roi in self.get_physician_rois(physician):
            if (
                self.get_institutional_roi(physician, physician_roi)
                == "uncategorized"
            ):
                unused_rois.append(physician_roi)

        return unused_rois

    def merge_physician_rois(
        self, physician, physician_rois, final_physician_roi
    ):
        """

        Parameters
        ----------
        physician :

        physician_rois :

        final_physician_roi :


        Returns
        -------

        """

        variation_lists = [
            self.get_variations(physician, physician_roi)
            for physician_roi in physician_rois
        ]
        variations = flatten_list_of_lists(
            variation_lists, remove_duplicates=True
        )
        self.add_variations(physician, final_physician_roi, variations)

        for physician_roi in physician_rois:
            if physician_roi != final_physician_roi:
                self.delete_physician_roi(physician, physician_roi)

    def set_roi_type(self, physician, roi, roi_type):
        """

        Parameters
        ----------
        physician :

        roi :

        roi_type :


        Returns
        -------

        """
        if self.is_physician(physician):
            self.physicians[physician].set_roi_type(roi, roi_type)

    def get_roi_type(self, physician, roi):
        """

        Parameters
        ----------
        physician :

        roi :


        Returns
        -------

        """
        if self.is_physician(physician):
            return self.physicians[physician].get_roi_type(roi)
        return "NONE"

    ###################################################
    # Variation-of-Physician-ROI functions
    ###################################################
    def get_variations(self, physician, physician_roi):
        """

        Parameters
        ----------
        physician :

        physician_roi :


        Returns
        -------

        """
        physician = clean_name(physician, physician=True)
        physician_roi = clean_name(physician_roi)
        if physician_roi == "uncategorized":
            return ["uncategorized"]

        if physician in list(self.physicians):
            variations = self.physicians[physician].get_variations(
                physician_roi
            )
            if variations:
                return variations
        return []

    def get_all_variations_of_physician(self, physician):
        """

        Parameters
        ----------
        physician :


        Returns
        -------

        """
        physician = clean_name(physician, physician=True)
        if physician in list(self.physicians):
            variations = self.physicians[physician].all_variations
            if variations:
                return variations
        return []

    def is_variation_used(self, physician, variation):
        """

        Parameters
        ----------
        physician :

        variation :


        Returns
        -------

        """
        if physician in list(self.physicians):
            return variation in self.physicians[physician]
        return False

    def add_variations(self, physician, physician_roi, variation):
        """

        Parameters
        ----------
        physician :

        physician_roi :

        variation :


        Returns
        -------

        """
        physician = clean_name(physician, physician=True)
        if physician in list(self.physicians):
            self.physicians[physician].add_variations(physician_roi, variation)

    def delete_variations(self, physician, physician_roi, variations):
        """

        Parameters
        ----------
        physician :

        physician_roi :

        variations :


        Returns
        -------

        """
        physician = clean_name(physician, physician=True)
        if physician in list(self.physicians):
            if type(variations) is not list:
                variations = [variations]
            self.physicians[physician].del_variations(
                physician_roi, variations
            )

    def set_variation(
        self, new_variation, physician, physician_roi, variation
    ):
        """

        Parameters
        ----------
        new_variation :

        physician :

        physician_roi :

        variation :


        Returns
        -------

        """
        physician = clean_name(physician, physician=True)
        if new_variation != variation:
            self.add_variations(physician, physician_roi, new_variation)
            self.delete_variations(physician, physician_roi, variation)

    def is_roi(self, roi):
        """

        Parameters
        ----------
        roi :


        Returns
        -------

        """
        if clean_name(roi) in self.clean_institutional_rois:
            return True
        for physician in self.physicians.values():
            if roi in physician:
                return True
        return False

    ########################
    # Export to file
    ########################
    def write_to_file(self):
        """ """
        for physician, data in self.physician_roi_file_data.items():
            self.write_physician_file(physician, data)
            self.write_roi_types_to_file(physician)
        self.remove_unused_roi_files()

    @property
    def physician_roi_file_data(self):
        """ """
        physicians_file_data = {}
        for physician in list(self.physicians) + ["DEFAULT"]:
            lines = []
            for physician_roi in self.get_physician_rois(physician):
                institutional_roi = '"%s"' % self.get_institutional_roi(
                    physician, physician_roi
                )
                variations = '"%s"' % '","'.join(
                    self.get_variations(physician, physician_roi)
                )
                lines.append(
                    ":".join(
                        [institutional_roi, '"%s"' % physician_roi, variations]
                    )
                )
            lines.sort()
            physicians_file_data[physician] = lines

        return physicians_file_data

    @staticmethod
    def write_physician_file(physician, lines):
        """Write the physician map to a .roi file

        Parameters
        ----------
        physician : str
            name of physicain
        lines : list of str
            the lines of data to be written to the file

        Returns
        -------

        """
        abs_file_path = os.path.join(
            PREF_DIR, "physician_" + physician + ".roi"
        )
        if lines:
            with open(abs_file_path, "w") as document:
                for line in lines:
                    document.write(line + "\n")

    def remove_unused_roi_files(self):
        """Delete any physician .roi or .rtype files that are no longer in the ROI map

        Parameters
        ----------

        Returns
        -------
        list
            the physicians that have been removed

        """
        for physician in self.deleted_physicians:
            for file_type in [".roi", ".rtype"]:
                file_name = "physician_%s%s" % (physician, file_type)
                abs_file_path = os.path.join(PREF_DIR, file_name)
                os.remove(abs_file_path)

    @property
    def deleted_physicians(self):
        """ """
        return list(
            set(get_physicians_from_roi_files()) - set(self.get_physicians())
        )

    @property
    def added_physicians(self):
        """ """
        return list(
            set(self.get_physicians()) - set(get_physicians_from_roi_files())
        )

    def get_roi_map_changes(self):
        """Use difflib to detect changes between current roi map and previously saved .roi file
        format of returned dict: diff[physician][physician_roi][delta] = {'institutional': i_roi, 'variations': list}
        where delta is either '+' or '-' based on difflib.unified_diff output

        Parameters
        ----------

        Returns
        -------
        dict
            a tiered dictionary of lines that changed in the proposed .roi file

        """
        new_data = self.physician_roi_file_data
        diff = {}
        for physician in list(self.physicians):
            abs_file_path = os.path.join(
                PREF_DIR, "physician_" + physician + ".roi"
            )
            if os.path.isfile(abs_file_path):
                old_lines = [
                    line.strip()
                    for line in open(abs_file_path, "r").readlines()
                ]

                include = False
                diff[physician] = {}
                for line in difflib.unified_diff(
                    old_lines, new_data[physician]
                ):
                    if include:
                        if line[0] in {"+", "-"}:
                            line_split = line.split(":")
                            i_roi, p_roi = (
                                line_split[0].strip(),
                                line_split[1].strip(),
                            )
                            variations = ":".join(line_split[2:])

                            if p_roi not in diff[physician]:
                                diff[physician][p_roi] = {
                                    "-": {
                                        "institutional": "",
                                        "variations": [],
                                    },
                                    "+": {
                                        "institutional": "",
                                        "variations": [],
                                    },
                                }
                            diff[physician][p_roi][line[0]] = {
                                "institutional": i_roi[1:],
                                "variations": variations.split(", "),
                            }
                    else:
                        include = (
                            line[0] == "@"
                        )  # + and - signs before the @@ line to be ignored

                # Check for Edited ROI Types, only needed if not included in previous for-loop
                for p_roi in self.physicians[
                    physician
                ].physician_rois_with_edited_roi_type:
                    if p_roi not in list(diff[physician]):
                        diff[physician][p_roi] = {
                            "-": {"institutional": "", "variations": []},
                            "+": {"institutional": "", "variations": []},
                        }
                        diff[physician][p_roi]["+"] = {
                            "institutional": self.get_institutional_roi(
                                physician, p_roi
                            ),
                            "variations": self.get_variations(
                                physician, p_roi
                            ),
                        }

                for p_roi, data in diff[physician].items():
                    new_pos = list(
                        set(data["+"]["variations"])
                        - set(data["-"]["variations"])
                    )
                    new_neg = list(
                        set(data["-"]["variations"])
                        - set(data["+"]["variations"])
                    )
                    if new_pos:
                        data["+"]["variations"] = new_pos
                    else:
                        data.pop("+")
                    if new_neg:
                        data["-"]["variations"] = new_neg
                    else:
                        data.pop("-")

        return diff

    @property
    def physicians_to_remap(self):
        """ """
        return list(set(self.deleted_physicians + self.added_physicians))

    @property
    def variations_to_update(self):
        """

        Parameters
        ----------

        Returns
        -------
        dict
            all variations that have changed physician or institutional rois, in a dict with physician for the key

        """
        changes = self.get_roi_map_changes()
        variations_to_update = {}
        for physician, physician_roi_data in changes.items():
            variations = []
            for p_roi_data in physician_roi_data.values():
                for delta_data in p_roi_data.values():
                    variations.extend(delta_data["variations"])
            variations_to_update[physician] = list(set(variations))

        for physician in list(variations_to_update):
            if not variations_to_update[physician]:
                variations_to_update.pop(physician)

        return variations_to_update

    def remap_rois(self):
        """ """

        with DVH_SQL() as cnx:
            for physician, variations in self.variations_to_update.items():
                for variation in variations:
                    new_physician_roi = self.get_physician_roi(
                        physician, variation
                    )
                    new_institutional_roi = self.get_institutional_roi(
                        physician, new_physician_roi
                    )

                    condition = (
                        "REPLACE(REPLACE(LOWER(roi_name), ''', '`'), '_', ' ') == '%s'"
                        % variation
                    )
                    sql_query = (
                        "SELECT DISTINCT study_instance_uid, roi_name FROM DVHs WHERE %s;"
                        % condition
                    )
                    uids_roi_names = cnx.query_generic(sql_query)
                    uids = [row[0] for row in uids_roi_names]
                    roi_names = [row[1] for row in uids_roi_names]

                    if uids:
                        for i, uid in enumerate(uids):
                            roi_name = roi_names[i]
                            condition = (
                                "roi_name = '%s' and study_instance_uid = '%s'"
                                % (roi_name, uid)
                            )
                            cnx.update(
                                "dvhs",
                                "physician_roi",
                                new_physician_roi,
                                condition,
                            )
                            cnx.update(
                                "dvhs",
                                "institutional_roi",
                                new_institutional_roi,
                                condition,
                            )

        self.write_to_file()

    ################
    # Plotting tools
    ################
    def get_physician_roi_visual_coordinates(
        self, physician, physician_roi, institutional_roi
    ):
        """

        Parameters
        ----------
        physician :

        physician_roi :

        institutional_roi :


        Returns
        -------

        """

        # All 0.5 subtractions due to a workaround of a Bokeh 0.12.9 bug

        # x and y are coordinates for the circles
        # x0, y0 is beginning of line segment, x1, y1 is end of line-segment
        if institutional_roi == "uncategorized":
            table = {
                "name": [physician_roi],
                "x": [1.5],
                "y": [0],
                "x0": [1.5],
                "y0": [0],
                "x1": [1.5],
                "y1": [0],
            }
        else:
            table = {
                "name": [institutional_roi, physician_roi],
                "x": [0.5, 1.5],
                "y": [0, 0],
                "x0": [0.5, 1.5],
                "y0": [0, 0],
                "x1": [1.5, 0.5],
                "y1": [0, 0],
            }

        variations = self.physicians[physician].rois[physician_roi].variations
        for i, variation in enumerate(variations):
            table["name"].append(variation)
            table["x"].append(2.5)
            table["y"].append(-i)
            table["x0"].append(1.5)
            table["y0"].append(0)
            table["x1"].append(2.5)
            table["y1"].append(-i)

        table_length = len(table["name"])
        table["color"] = ["#1F77B4"] * table_length
        table["institutional_roi"] = [institutional_roi] * table_length
        table["physician_roi"] = [physician_roi] * table_length

        return table

    def get_all_institutional_roi_visual_coordinates(
        self, physician, ignored_physician_rois=None
    ):
        """

        Parameters
        ----------
        physician :

        ignored_physician_rois :
             (Default value = None)

        Returns
        -------

        """
        # TODO: Although functional and faster, hard to follow
        # Still slowest part of ROI Map plot generation
        ignored_physician_rois = (
            [] if ignored_physician_rois is None else ignored_physician_rois
        )
        p_and_i = [
            (roi.physician_roi, roi.institutional_roi)
            for roi in self.physicians[physician].rois.values()
            if roi.physician_roi not in ignored_physician_rois
        ]

        i_rois = [roi[1] for roi in p_and_i]
        i_rois.sort()
        for i, i_roi in enumerate(i_rois):
            if i_roi == "uncategorized":
                i_rois[i] = "zzzzzzzzzzzzzzzzzzz"
        sorted_indices = [
            i[0] for i in sorted(enumerate(i_rois), key=lambda x: x[1])
        ]
        p_and_i = [p_and_i[i] for i in sorted_indices]

        tables = {
            roi[0]: self.get_physician_roi_visual_coordinates(
                physician, roi[0], roi[1]
            )
            for roi in p_and_i
        }
        heights = [3 - min(tables[p_roi[0]]["y"]) for p_roi in p_and_i]
        max_y_delta = (
            sum(heights) + 2
        )  # include 2 buffer to give space to read labels on plot
        for i, roi in enumerate(p_and_i):
            y_delta = sum(heights[i:])

            for key in ["y", "y0", "y1"]:
                for j in range(len(tables[roi[0]][key])):
                    tables[roi[0]][key][j] += y_delta - max_y_delta

        i_roi_map = {p_i[0]: p_i[1] for p_i in p_and_i}
        if p_and_i and p_and_i[0][0] in tables:
            table = tables[p_and_i[0][0]]
            for i in range(1, len(p_and_i)):
                for key in list(table):
                    table[key].extend(tables[p_and_i[i][0]][key])

            return self.update_duplicate_y_entries(table, physician, i_roi_map)
        return None

    @staticmethod
    def get_roi_visual_y_values(table):
        """

        Parameters
        ----------
        table :


        Returns
        -------

        """
        y_values = {}
        for i, x in enumerate(table["x"]):
            if x == 0.5:
                name = table["name"][i]
                if name not in list(y_values):
                    y_values[name] = []
                y_values[name].append(table["y"][i])
        for name in list(y_values):
            y_values[name] = sum(y_values[name]) / len(y_values[name])
        return y_values

    def update_duplicate_y_entries(self, table, physician, inst_map):
        """

        Parameters
        ----------
        table :

        physician :

        inst_map :


        Returns
        -------

        """

        y_values = self.get_roi_visual_y_values(table)

        self.branched_institutional_rois[physician] = []

        for i, name in enumerate(table["name"]):
            if table["x"][i] == 0.5 and table["y"][i] != y_values[name]:
                table["y"][i] = y_values[name]
                table["y0"][i] = y_values[name]
                table["color"][i] = "red"
                self.branched_institutional_rois[physician].append(name)
            if table["x"][i] == 1.5:
                inst_name = inst_map[name]
                if inst_name != "uncategorized":
                    table["y1"][i] = y_values[inst_name]

        if self.branched_institutional_rois[physician]:
            self.branched_institutional_rois[physician] = list(
                set(self.branched_institutional_rois[physician])
            )

        return table

    @property
    def tree(self):
        """ """
        return {
            physician: self.get_physician_tree(physician)
            for physician in self.get_physicians()
        }

    def get_physician_tree(self, physician):
        """

        Parameters
        ----------
        physician :


        Returns
        -------

        """
        phys_rois = self.get_physician_rois(physician)
        unused_inst_rois = self.get_unused_institutional_rois(physician)
        inst_rois = [
            roi
            for roi in self.institutional_rois
            if roi not in unused_inst_rois
        ]
        linked_phys_rois = [
            self.get_physician_roi_from_institutional_roi(physician, roi)
            for roi in inst_rois
        ]
        unlinked_phys_rois = [
            roi for roi in phys_rois if roi not in linked_phys_rois
        ]
        linked_phys_roi_tree = {
            roi: self.get_variations(physician, roi)
            for roi in linked_phys_rois
            if roi != "uncategorized"
        }
        unlinked_phys_roi_tree = {
            roi: self.get_variations(physician, roi)
            for roi in unlinked_phys_rois
            if roi != "uncategorized"
        }
        return {
            "Linked to Institutional ROI": linked_phys_roi_tree,
            "Unlinked to Institutional ROI": unlinked_phys_roi_tree,
        }

    ########################
    # Save and Load ROI Type
    ########################
    def write_roi_types_to_file(self, physician):
        """

        Parameters
        ----------
        physician :


        Returns
        -------

        """
        if self.is_physician(physician):
            rois = self.physicians[physician].rois
            roi_types = [
                "%s:%s" % (name, obj.roi_type)
                for name, obj in rois.items()
                if obj.roi_type != "NONE"
            ]
            if roi_types:
                file_path = os.path.join(
                    PREF_DIR, "physician_%s.rtype" % physician
                )
                with open(file_path, "w") as doc:
                    doc.write("\n".join(roi_types))

    def load_roi_types_from_file(self, physician):
        """

        Parameters
        ----------
        physician :


        Returns
        -------

        """
        if self.is_physician(physician):
            file_path = os.path.join(
                PREF_DIR, "physician_%s.rtype" % physician
            )
            if os.path.isfile(file_path):
                with open(file_path, "r") as doc:
                    for line in doc:
                        if not line:
                            continue
                        if line.count(":") == 1:
                            try:
                                physician_roi, roi_type = tuple(
                                    line.split(":")
                                )
                                self.physicians[physician].rois[
                                    physician_roi.strip()
                                ].roi_type = roi_type.strip()
                            except Exception as e:
                                msg = (
                                    "DatabaseROIs.load_roi_types_from_file: "
                                    "Could not import %s roi_type for physician %s"
                                    % (physician_roi, physician)
                                )
                                push_to_log(e, msg=msg)


def clean_name(name, physician=False):
    """

    Parameters
    ----------
    name :

    physician :
         (Default value = False)

    Returns
    -------

    """
    ans = (
        str(name).replace("'", "`").replace("_", " ").replace(":", ";").strip()
    )
    while "  " in ans:
        ans = ans.replace("  ", " ")

    if physician:
        return ans.replace(" ", "_").upper()
    return ans.lower()


def get_physicians_from_roi_files():
    """ """

    physicians = []
    for file_name in os.listdir(PREF_DIR):
        if file_name.startswith("physician_") and file_name.endswith(".roi"):
            physician = file_name.replace("physician_", "").replace(".roi", "")
            physician = clean_name(physician, physician=True)
            physicians.append(physician)

    return physicians


def get_physician_from_uid(uid):
    """

    Parameters
    ----------
    uid :


    Returns
    -------

    """
    with DVH_SQL() as cnx:
        results = cnx.query(
            "Plans", "physician", "study_instance_uid = '" + uid + "'"
        )

    if len(results) > 1:
        msg = (
            "roi_name_manager.get_physician_from_uid: multiple plans with this study_instance_uid exist: %s"
            % uid
        )
        push_to_log(msg=msg)

    return str(results[0][0])


def update_uncategorized_rois_in_database():
    """ """
    roi_map = DatabaseROIs()
    dvh_data = QuerySQL("DVHs", "physician_roi = 'uncategorized'")

    with DVH_SQL() as cnx:
        for i in range(len(dvh_data.roi_name)):
            uid = dvh_data.study_instance_uid[i]
            # mrn = dvh_data.mrn[i]
            physician = get_physician_from_uid(uid)
            roi_name = dvh_data.roi_name[i]

            new_physician_roi = roi_map.get_physician_roi(physician, roi_name)
            new_institutional_roi = roi_map.get_institutional_roi(
                physician, roi_name
            )

            if new_physician_roi != "uncategorized":
                # print(mrn, physician, new_institutional_roi, new_physician_roi, roi_name, sep=' ')
                condition = (
                    "study_instance_uid = '"
                    + uid
                    + "'"
                    + "and roi_name = '"
                    + roi_name
                    + "'"
                )
                cnx.update(
                    "DVHs", "physician_roi", new_physician_roi, condition
                )
                cnx.update(
                    "DVHs",
                    "institutional_roi",
                    new_institutional_roi,
                    condition,
                )
