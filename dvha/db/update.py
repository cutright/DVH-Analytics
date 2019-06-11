#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
functions to update various columns in the SQL database
Created on Fri Dec 28 2018
@author: Dan Cutright, PhD
"""

import numpy as np
from db.sql_connector import DVH_SQL
from tools import roi_geometry as roi_geom
from tools import roi_formatter as roi_form
from os.path import join as join_path
from tools.mlc_analyzer import Beam as mlca
from tools.utilities import calc_stats
import pydicom as dicom


def centroid(study_instance_uid, roi_name):
    """
    This function will recalculate the centroid of an roi based on data in the SQL DB.
    :param study_instance_uid: uid as specified in SQL DB
    :param roi_name: roi_name as specified in SQL DB
    """

    coordinates_string = query('dvhs', 'roi_coord_string',
                               "study_instance_uid = '%s' and roi_name = '%s'" % (study_instance_uid, roi_name))

    roi = roi_form.get_planes_from_string(coordinates_string[0][0])
    data = roi_geom.centroid(roi)

    data = [str(round(v, 3)) for v in data]

    update_dvhs_table(study_instance_uid, roi_name, 'centroid', ','.join(data))


def cross_section(study_instance_uid, roi_name):
    """
    This function will recalculate the centoid of an roi based on data in the SQL DB.
    :param study_instance_uid: uid as specified in SQL DB
    :param roi_name: roi_name as specified in SQL DB
    """

    coordinates_string = query('dvhs', 'roi_coord_string',
                               "study_instance_uid = '%s' and roi_name = '%s'" % (study_instance_uid, roi_name))

    roi = roi_form.get_planes_from_string(coordinates_string[0][0])
    area = roi_geom.cross_section(roi)

    for key in ['max', 'median']:
        update_dvhs_table(study_instance_uid, roi_name, 'cross_section_%s' % key, area[key])


def spread(study_instance_uid, roi_name):
    """
    This function will recalculate the spread of an roi based on data in the SQL DB.
    :param study_instance_uid: uid as specified in SQL DB
    :param roi_name: roi_name as specified in SQL DB
    """

    coordinates_string = query('dvhs', 'roi_coord_string',
                               "study_instance_uid = '%s' and roi_name = '%s'" % (study_instance_uid, roi_name))

    roi = roi_form.get_planes_from_string(coordinates_string[0][0])
    data = roi_geom.spread(roi)

    data = [str(round(v/10., 3)) for v in data]

    for i, column in enumerate(['spread_x', 'spread_y', 'spread_z']):
        update_dvhs_table(study_instance_uid, roi_name, column, data[i])


def dist_to_ptv_centroids(study_instance_uid, roi_name, pre_calc=None):
    """
    This function will recalculate the OARtoPTV centroid distance based on data in the SQL DB.
    :param study_instance_uid: uid as specified in SQL DB
    :param roi_name: roi_name as specified in SQL DB
    :param pre_calc: centroid of combined PTV, return from get_ptv_centroid
    """

    oar_centroid_string = query('dvhs', 'centroid',
                                "study_instance_uid = '%s' and roi_name = '%s'" % (study_instance_uid, roi_name))
    oar_centroid = np.array([float(i) for i in oar_centroid_string[0][0].split(',')])

    ptv_centroid = pre_calc
    if ptv_centroid is None:
        tv = get_treatment_volume(study_instance_uid)
        ptv_centroid = get_treatment_volume_centroid(tv)

    data = float(np.linalg.norm(ptv_centroid - oar_centroid)) / 10.

    update_dvhs_table(study_instance_uid, roi_name, 'dist_to_ptv_centroids', round(float(data), 3))


def get_treatment_volume_centroid(tv):
    return np.array(roi_geom.centroid(tv))


def min_distances(study_instance_uid, roi_name, pre_calc=None):
    """
    This function will recalculate the min, mean, median, and max PTV distances an roi based on data in the SQL DB.
    :param study_instance_uid: uid as specified in SQL DB
    :param roi_name: roi_name as specified in SQL DB
    :param pre_calc: coordinates of combined PTV, return from get_treatment_volume_coord
    """

    oar_coordinates_string = query('dvhs', 'roi_coord_string',
                                   "study_instance_uid = '%s' and roi_name = '%s'" % (study_instance_uid, roi_name))

    treatment_volume_coord = pre_calc
    if treatment_volume_coord is None:
        treatment_volume_coord = get_treatment_volume_coord(study_instance_uid)

    oar_coordinates = roi_form.get_roi_coordinates_from_string(oar_coordinates_string[0][0])

    try:
        data = roi_geom.min_distances_to_target(oar_coordinates, treatment_volume_coord)
    except MemoryError:
        print('Memory error reported for %s with study_instance_uid %s' % (roi_name, study_instance_uid))
        print('Skipping PTV distance and DTH calculations for this ROI.')
        data = None

    if data is not None:
        dth = roi_geom.dth(data)
        dth_string = ','.join(['%.3f' % num for num in dth])

        data_map = {'dist_to_ptv_min': round(float(np.min(data)), 2),
                    'dist_to_ptv_mean': round(float(np.mean(data)), 2),
                    'dist_to_ptv_median': round(float(np.median(data)), 2),
                    'dist_to_ptv_max': round(float(np.max(data)), 2),
                    'dth_string': dth_string}

        for key, value in data_map.items():
            update_dvhs_table(study_instance_uid, roi_name, key, value)


def get_treatment_volume_coord(tv):
    return roi_form.get_roi_coordinates_from_planes(tv)


def treatment_volume_overlap(study_instance_uid, roi_name, pre_calc=None):
    """
    This function will recalculate the PTV overlap of an roi based on data in the SQL DB.
    :param study_instance_uid: uid as specified in SQL DB
    :param roi_name: roi_name as specified in SQL DB
    :param pre_calc: union of PTVs, return from get_treatment_volume
    """

    oar_coordinates_string = query('dvhs', 'roi_coord_string',
                                   "study_instance_uid = '%s' and roi_name = '%s'" % (study_instance_uid, roi_name))
    oar = roi_form.get_planes_from_string(oar_coordinates_string[0][0])

    treatment_volume = pre_calc
    if treatment_volume is None:
        treatment_volume = get_treatment_volume(study_instance_uid)

    overlap = roi_geom.overlap_volume(oar, treatment_volume)
    update_dvhs_table(study_instance_uid, roi_name, 'ptv_overlap', round(float(overlap), 2))


def get_treatment_volume(study_instance_uid):
    ptv_coordinates_strings = query('dvhs', 'roi_coord_string',
                                    "study_instance_uid = '%s' and roi_type like 'PTV%%'" % study_instance_uid)

    ptvs = [roi_form.get_planes_from_string(ptv[0]) for ptv in ptv_coordinates_strings]

    return roi_geom.union(ptvs)


def volumes(study_instance_uid, roi_name):
    """
    This function will recalculate the volume of an roi based on data in the SQL DB.
    :param study_instance_uid: uid as specified in SQL DB
    :param roi_name: roi_name as specified in SQL DB
    """

    coordinates_string = query('dvhs', 'roi_coord_string',
                               "study_instance_uid = '%s' and roi_name = '%s'" % (study_instance_uid, roi_name))

    roi = roi_form.get_planes_from_string(coordinates_string[0][0])

    data = roi_geom.volume(roi)

    update_dvhs_table(study_instance_uid, roi_name, 'volume', round(float(data), 2))


def surface_area(study_instance_uid, roi_name):
    """
    This function will recalculate the surface area of an roi based on data in the SQL DB.
    :param study_instance_uid: uid as specified in SQL DB
    :param roi_name: roi_name as specified in SQL DB
    """

    coordinates_string = query('dvhs', 'roi_coord_string',
                               "study_instance_uid = '%s' and roi_name = '%s'" % (study_instance_uid, roi_name))

    roi = roi_form.get_planes_from_string(coordinates_string[0][0])

    data = roi_geom.surface_area(roi, coord_type="sets_of_points")

    update_dvhs_table(study_instance_uid, roi_name, 'surface_area', round(float(data), 2))


def update_dvhs_table(study_instance_uid, roi_name, column, value):
    with DVH_SQL() as cnx:
        cnx.update('dvhs', column, value,
                   "study_instance_uid = '%s' and roi_name = '%s'" % (study_instance_uid, roi_name))


def update_plan_toxicity_grades(cnx, study_instance_uid):
    toxicities = cnx.get_unique_values('DVHs', 'toxicity_grade', "study_instance_uid = '%s'" % study_instance_uid)
    toxicities = [t for t in toxicities if t.isdigit()]
    toxicities_str = ','.join(toxicities)
    cnx.update('Plans', 'toxicity_grades', toxicities_str, "study_instance_uid = '%s'" % study_instance_uid)


def update_all_plan_toxicity_grades(*condition):
    if condition:
        condition = condition[0]
    with DVH_SQL() as cnx:
        uids = cnx.get_unique_values('Plans', 'study_instance_uid', condition, return_empty=True)
        for uid in uids:
            update_plan_toxicity_grades(cnx, uid)


def plan_complexity(cnx, study_instance_uid):
    condition = "study_instance_uid = '%s'" % study_instance_uid
    beam_data = query('Beams', 'complexity, beam_mu', condition)
    scores = [row[0] for row in beam_data]
    include = [i for i, score in enumerate(scores) if score]
    scores = [score for i, score in enumerate(scores) if i in include]
    beam_mu = [row[1] for i, row in enumerate(beam_data) if i in include]
    plan_mu = np.sum(beam_mu)
    if plan_mu:
        complexity = np.sum(np.multiply(scores, beam_mu)) / plan_mu
        cnx.update('Plans', 'complexity', complexity, "study_instance_uid = '%s'" % study_instance_uid)
    else:
        print('Zero plan MU detected for uid %s' % study_instance_uid)


def plan_complexities(*condition):
    if condition:
        condition = condition[0]
    with DVH_SQL() as cnx:
        uids = cnx.get_unique_values('Plans', 'study_instance_uid', condition, return_empty=True)
        for uid in uids:
            plan_complexity(cnx, uid)


def beam_complexity(cnx, study_instance_uid):

    rt_plan_query = cnx.query('DICOM_Files', 'folder_path, plan_file',
                              "study_instance_uid = '%s'" % study_instance_uid)[0]
    rt_plan_file_path = join_path(rt_plan_query[0], rt_plan_query[1])

    rt_plan = dicom.read_file(rt_plan_file_path)

    for beam_num, beam in enumerate(rt_plan.BeamSequence):
        try:
            condition = "study_instance_uid = '%s' and beam_number = '%s'" % (study_instance_uid, (beam_num + 1))
            meterset = float(cnx.query('Beams', 'beam_mu', condition)[0][0])
            mlca_data = mlca(beam, meterset, ignore_zero_mu_cp=True)
            mlc_keys = ['area', 'x_perim', 'y_perim', 'cmp_score', 'cp_mu']
            summary_stats = {key: calc_stats(mlca_data.summary[key]) for key in mlc_keys}

            column_vars = {'area': 'area', 'x_perim': 'x_perim', 'y_perim': 'y_perim', 'complexity': 'cmp_score',
                           'cp_mu': 'cp_mu'}
            stat_map = {'min': 5, 'mean': 3, 'median': 2, 'max': 0}

            for c in list(column_vars):
                for s in list(stat_map):
                    value = summary_stats[column_vars[c]][stat_map[s]]
                    column = "%s_%s" % (c, s)
                    cnx.update('Beams', column, value, condition)
            cnx.update('Beams', 'complexity', np.sum(mlca_data.summary['cmp_score']), condition)
        except:
            print('MLC Analyzer fail for beam number %s and uid %s' % ((beam_num+1), study_instance_uid))


def beam_complexities(*condition):
    if condition:
        condition = condition[0]
    with DVH_SQL() as cnx:
        uids = cnx.get_unique_values('Beams', 'study_instance_uid', condition, return_empty=True)
        for uid in uids:
            beam_complexity(cnx, uid)


def update_ptv_data(tv, study_instance_uid):
        ptv_cross_section = roi_geom.cross_section(tv)
        ptv_spread = roi_geom.spread(tv)

        condition = "study_instance_uid = '%s' and roi_type like 'PTV%%'" % study_instance_uid
        with DVH_SQL() as cnx:
            max_dose = cnx.get_max_value('dvhs', 'max_dose', condition=condition)
            min_dose = cnx.get_min_value('dvhs', 'min_dose', condition=condition)

            ptv_data = {'ptv_cross_section_max': ptv_cross_section['max'],
                        'ptv_cross_section_median': ptv_cross_section['median'],
                        'ptv_max_dose': max_dose,
                        'ptv_min_dose': min_dose,
                        'ptv_spread_x': ptv_spread[0],
                        'ptv_spread_y': ptv_spread[1],
                        'ptv_spread_z': ptv_spread[2],
                        'ptv_surface_area': roi_geom.surface_area(tv, coord_type='sets_of_points'),
                        'ptv_volume': roi_geom.volume(tv)}

            for key, value in ptv_data.items():
                cnx.update('Plans', key, value, "study_instance_uid = '%s'" % study_instance_uid)


def query(table, column, condition):
    with DVH_SQL() as cnx:
        ans = cnx.query(table, column, condition)
    return ans

