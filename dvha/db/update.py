#!/usr/bin/env python
# -*- coding: utf-8 -*-

# db.update.py
"""Functions to update various columns in the SQL database"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics


import numpy as np
from os.path import join as join_path
import pydicom as dicom
from dvha.db.sql_connector import DVH_SQL
from dvha.tools import roi_geometry as roi_geom
from dvha.tools import roi_formatter as roi_form
from dvha.tools.errors import push_to_log
from mlca.mlc_analyzer import Beam as BeamAnalyzer
from dvha.tools.utilities import calc_stats, sample_roi


def centroid(study_instance_uid, roi_name):
    """Recalculate the centroid of an roi based on data in the SQL DB.

    Parameters
    ----------
    study_instance_uid : str
        study instance uid
    roi_name : str
        name of roi
    """

    coordinates_string = query(
        "dvhs",
        "roi_coord_string",
        "study_instance_uid = '%s' and roi_name = '%s'"
        % (study_instance_uid, roi_name),
    )

    roi = roi_form.get_planes_from_string(coordinates_string[0][0])
    data = roi_geom.centroid(roi)

    data = [str(round(v, 3)) for v in data]

    update_dvhs_table(study_instance_uid, roi_name, "centroid", ",".join(data))


def cross_section(study_instance_uid, roi_name):
    """Recalculate the centroid of an roi based on data in the SQL DB.

    Parameters
    ----------
    study_instance_uid : str
        study instance uid
    roi_name : str
        name of roi

    """

    coordinates_string = query(
        "dvhs",
        "roi_coord_string",
        "study_instance_uid = '%s' and roi_name = '%s'"
        % (study_instance_uid, roi_name),
    )

    roi = roi_form.get_planes_from_string(coordinates_string[0][0])
    area = roi_geom.cross_section(roi)

    for key in ["max", "median"]:
        update_dvhs_table(
            study_instance_uid, roi_name, "cross_section_%s" % key, area[key]
        )


def spread(study_instance_uid, roi_name):
    """Recalculate the spread of an roi based on data in the SQL DB.

    Parameters
    ----------
    study_instance_uid : str
        study instance uid
    roi_name : str
        name of roi

    """

    coordinates_string = query(
        "dvhs",
        "roi_coord_string",
        "study_instance_uid = '%s' and roi_name = '%s'"
        % (study_instance_uid, roi_name),
    )

    roi = roi_form.get_planes_from_string(coordinates_string[0][0])
    data = roi_geom.spread(roi)

    data = [str(round(v / 10.0, 3)) for v in data]

    for i, column in enumerate(["spread_x", "spread_y", "spread_z"]):
        update_dvhs_table(study_instance_uid, roi_name, column, data[i])


def dist_to_ptv_centroids(study_instance_uid, roi_name, pre_calc=None):
    """Recalculate the OAR-to-PTV centroid distance based on data in the
    SQL DB. Optionally provide pre-calculated centroid of combined PTV

    Parameters
    ----------
    study_instance_uid : str
        study instance uid
    roi_name : str
        name of roi
    pre_calc : np.ndarray
        Return from get_treatment_volume_centroid

    """

    oar_centroid_string = query(
        "dvhs",
        "centroid",
        "study_instance_uid = '%s' and roi_name = '%s'"
        % (study_instance_uid, roi_name),
    )
    oar_centroid = np.array(
        [float(i) for i in oar_centroid_string[0][0].split(",")]
    )

    ptv_centroid = pre_calc
    if ptv_centroid is None:
        tv = get_total_treatment_volume_of_study(study_instance_uid)
        ptv_centroid = get_treatment_volume_centroid(tv)
    data = float(np.linalg.norm(ptv_centroid - oar_centroid)) / 10.0

    update_dvhs_table(
        study_instance_uid,
        roi_name,
        "dist_to_ptv_centroids",
        round(float(data), 3),
    )


def min_distances(study_instance_uid, roi_name, pre_calc=None):
    """Recalculate the min, mean, median, and max PTV distances an roi based
    on data in the SQL DB.

    Parameters
    ----------
    study_instance_uid : str
        study instance uid
    roi_name : str
        name of roi
    pre_calc : list, optional
        coordinates of combined PTV, return from get_treatment_volume_coord

    """

    oar_coordinates_string = query(
        "dvhs",
        "roi_coord_string",
        "study_instance_uid = '%s' and roi_name = '%s'"
        % (study_instance_uid, roi_name),
    )

    treatment_volume_roi = pre_calc
    treatment_volume_coord = get_treatment_volume_coord(pre_calc)
    if treatment_volume_coord is None:
        with DVH_SQL() as cnx:
            ptv_coordinates_strings = cnx.query(
                "dvhs",
                "roi_coord_string",
                "study_instance_uid = '%s' and roi_type like 'PTV%%'"
                % study_instance_uid,
            )

        ptvs = [
            roi_form.get_planes_from_string(ptv[0])
            for ptv in ptv_coordinates_strings
        ]
        treatment_volume_roi = roi_geom.union(ptvs)
        treatment_volume_coord = roi_form.get_roi_coordinates_from_planes(
            treatment_volume_roi
        )

    oar_coordinates = roi_form.get_roi_coordinates_from_string(
        oar_coordinates_string[0][0]
    )

    treatment_volume_coord = sample_roi(treatment_volume_coord)
    oar_coordinates = sample_roi(oar_coordinates)

    try:
        is_inside = [
            [1, -1][roi_geom.is_point_inside_roi(point, treatment_volume_roi)]
            for point in oar_coordinates
        ]
        data = roi_geom.min_distances_to_target(
            oar_coordinates, treatment_volume_coord, factors=is_inside
        )
    except Exception:
        try:
            treatment_volume_coord = sample_roi(
                treatment_volume_coord, max_point_count=3000
            )
            oar_coordinates = sample_roi(oar_coordinates, max_point_count=3000)
            is_inside = [
                [1, -1][
                    roi_geom.is_point_inside_roi(point, treatment_volume_roi)
                ]
                for point in oar_coordinates
            ]
            data = roi_geom.min_distances_to_target(
                oar_coordinates, treatment_volume_coord, factors=is_inside
            )
        except Exception as e:
            msg = (
                "db.update.min_distances: Error reported for %s with "
                "study_instance_uid %s\n"
                "Skipping PTV distance and DTH calculations for this ROI."
                % (roi_name, study_instance_uid)
            )
            push_to_log(e, msg=msg)
            data = None

    if data is not None:
        try:
            dth = roi_geom.dth(data)
            dth_string = ",".join(["%0.6f" % num for num in dth])

            data_map = {
                "dist_to_ptv_min": round(float(np.min(data)), 2),
                "dist_to_ptv_mean": round(float(np.mean(data)), 2),
                "dist_to_ptv_median": round(float(np.median(data)), 2),
                "dist_to_ptv_max": round(float(np.max(data)), 2),
                "dth_string": dth_string,
            }
        except MemoryError as e:
            msg = (
                "Error reported for %s with study_instance_uid %s\n"
                "Skipping PTV distance and DTH calculations for this ROI."
                % (roi_name, study_instance_uid)
            )
            push_to_log(e, msg=msg)
            data_map = None

        if data_map:
            for key, value in data_map.items():
                update_dvhs_table(study_instance_uid, roi_name, key, value)


def treatment_volume_overlap(study_instance_uid, roi_name, pre_calc=None):
    """Recalculate the PTV overlap of an roi based on data in the SQL DB.

    Parameters
    ----------
    study_instance_uid : str
        study instance uid
    roi_name : str
        name of roi
    pre_calc : dict, optional
        union of PTVs, return from get_total_treatment_volume_of_study

    """

    oar_coordinates_string = query(
        "dvhs",
        "roi_coord_string",
        "study_instance_uid = '%s' and roi_name = '%s'"
        % (study_instance_uid, roi_name),
    )
    oar = roi_form.get_planes_from_string(oar_coordinates_string[0][0])

    treatment_volume = pre_calc
    if treatment_volume is None:
        treatment_volume = get_total_treatment_volume_of_study(
            study_instance_uid
        )

    overlap = roi_geom.overlap_volume(oar, treatment_volume)
    update_dvhs_table(
        study_instance_uid, roi_name, "ptv_overlap", round(float(overlap), 2)
    )


def volumes(study_instance_uid, roi_name):
    """Recalculate the volume of an roi based on data in the SQL DB.

    Parameters
    ----------
    study_instance_uid : str
        study instance uid
    roi_name : str
        name of roi

    """

    coordinates_string = query(
        "dvhs",
        "roi_coord_string",
        "study_instance_uid = '%s' and roi_name = '%s'"
        % (study_instance_uid, roi_name),
    )

    roi = roi_form.get_planes_from_string(coordinates_string[0][0])

    data = roi_geom.volume(roi)

    update_dvhs_table(
        study_instance_uid, roi_name, "volume", round(float(data), 2)
    )


def surface_area(study_instance_uid, roi_name):
    """Recalculate the surface area of an roi based on data in the SQL DB.

    Parameters
    ----------
    study_instance_uid : str
        study instance uid
    roi_name : str
        name of roi

    """

    coordinates_string = query(
        "dvhs",
        "roi_coord_string",
        "study_instance_uid = '%s' and roi_name = '%s'"
        % (study_instance_uid, roi_name),
    )

    roi = roi_form.get_planes_from_string(coordinates_string[0][0])

    data = roi_geom.surface_area(roi, coord_type="sets_of_points")

    update_dvhs_table(
        study_instance_uid, roi_name, "surface_area", round(float(data), 2)
    )


def update_dvhs_table(study_instance_uid, roi_name, column, value):
    """Generic function to update a value in the DVHs table

    Parameters
    ----------
    study_instance_uid : str
        study instance uid in the SQL table
    roi_name : str
        the roi name associated with the value to be updated
    column : str
        the SQL column of the value to be updated
    value : str, int, float, datetime
        the value to be set, it's type should match the type as specified in
        the SQL table

    """
    with DVH_SQL() as cnx:
        cnx.update(
            "dvhs",
            column,
            value,
            "study_instance_uid = '%s' and roi_name = '%s'"
            % (study_instance_uid, roi_name),
        )


def update_plan_toxicity_grades(cnx, study_instance_uid):
    """Query the toxicities in the DVHs table and update the values in the
    associated plan row(s)

    Parameters
    ----------
    cnx : DVH_SQL
        connection to DVHA SQL database
    study_instance_uid : str
        study_instance_uid in SQL database

    """
    toxicities = cnx.get_unique_values(
        "DVHs",
        "toxicity_grade",
        "study_instance_uid = '%s'" % study_instance_uid,
    )
    toxicities = [t for t in toxicities if t.isdigit()]
    toxicities_str = ",".join(toxicities)
    cnx.update(
        "Plans",
        "toxicity_grades",
        toxicities_str,
        "study_instance_uid = '%s'" % study_instance_uid,
    )


def plan_complexity(cnx, study_instance_uid):
    """

    Parameters
    ----------
    cnx : DVH_SQL
        connection to DVHA SQL database
    study_instance_uid : str
        study_instance_uid in SQL database

    """
    condition = "study_instance_uid = '%s'" % study_instance_uid
    beam_data = query("Beams", "complexity, beam_mu", condition)
    scores = [row[0] for row in beam_data]
    include = [i for i, score in enumerate(scores) if score]
    scores = [score for i, score in enumerate(scores) if i in include]
    beam_mu = [row[1] for i, row in enumerate(beam_data) if i in include]
    plan_mu = np.sum(beam_mu)
    if plan_mu:
        complexity = np.sum(np.multiply(scores, beam_mu)) / plan_mu
        cnx.update(
            "Plans",
            "complexity",
            complexity,
            "study_instance_uid = '%s'" % study_instance_uid,
        )
    else:
        msg = (
            "db.update.plan_complexity: Zero plan MU detected for uid %s"
            % study_instance_uid
        )
        push_to_log(msg=msg)


def beam_complexity(cnx, study_instance_uid):
    """

    Parameters
    ----------
    cnx : DVH_SQL
        connection to DVHA SQL database
    study_instance_uid : str
        study_instance_uid in SQL database

    """

    rt_plan_query = cnx.query(
        "DICOM_Files",
        "folder_path, plan_file",
        "study_instance_uid = '%s'" % study_instance_uid,
    )[0]
    rt_plan_file_path = join_path(rt_plan_query[0], rt_plan_query[1])

    rt_plan = dicom.read_file(rt_plan_file_path)

    column_vars = {
        "area": "area",
        "x_perim": "x_perim",
        "y_perim": "y_perim",
        "complexity": "cmp_score",
        "cp_mu": "cp_mu",
    }
    stat_map = {"min": 5, "mean": 3, "median": 2, "max": 0}

    unit_factor = {
        "area": 100.0,
        "x_perim": 10.0,
        "y_perim": 10.0,
        "complexity": 1.0,
        "cp_mu": 1.0,
    }

    for beam_num, beam in enumerate(rt_plan.BeamSequence):
        try:
            condition = "study_instance_uid = '%s' and beam_number = '%s'" % (
                study_instance_uid,
                (beam_num + 1),
            )
            meterset = float(cnx.query("Beams", "beam_mu", condition)[0][0])
            mlca_data = BeamAnalyzer(beam, meterset, ignore_zero_mu_cp=True)
            mlc_keys = ["area", "x_perim", "y_perim", "cmp_score", "cp_mu"]
            summary_stats = {
                key: calc_stats(mlca_data.summary[key]) for key in mlc_keys
            }

            for c in list(column_vars):
                for s in list(stat_map):
                    value = (
                        summary_stats[column_vars[c]][stat_map[s]]
                        / unit_factor[c]
                    )
                    column = "%s_%s" % (c, s)
                    cnx.update("Beams", column, value, condition)
            cnx.update(
                "Beams",
                "complexity",
                np.sum(mlca_data.summary["cmp_score"]),
                condition,
            )
        except Exception as e:
            msg = (
                "db.update.beam_complexity: MLC Analyzer fail for beam number "
                "%s and uid %s" % ((beam_num + 1), study_instance_uid)
            )
            push_to_log(e, msg=msg)


def update_all_generic(table, func, condition):
    """Generic function to call ``func`` that accepts a DVH_SQL object and
    study_instance_uid. Intended for beam_complexities, plan_complexities,
    update_all_plan_toxicity_grades, etc.

    Parameters
    ----------
    table : str
        SQL table name
    func : callable
        the function to be called with parameters of DVH_SQL and
        study_instance_uid
    condition : str
        optional SQL condition to apply to the study_instance_uid list
        retrieval

    """
    if condition:
        condition = condition[0]
    with DVH_SQL() as cnx:
        uids = cnx.get_unique_values(
            table, "study_instance_uid", condition, return_empty=True
        )
        for uid in uids:
            func(cnx, uid)


def update_all_plan_toxicity_grades(condition=None):
    """Call update_plan_toxicity_grades on all Plan rows

    Parameters
    ----------
    condition : str
        SQL condition

    """
    update_all_generic("Plans", update_plan_toxicity_grades, condition)


def plan_complexities(condition=None):
    """Call plan_complexity on all Plan rows

    Parameters
    ----------
    condition : str
        SQL condition

    """
    update_all_generic("Plans", plan_complexity, condition)


def beam_complexities(condition=None):
    """Call beam_complexity on all Beams rows

    Parameters
    ----------
    condition : str
        SQL condition

    """
    update_all_generic("Beams", beam_complexity, condition)


def update_ptv_data(tv, study_instance_uid):
    """Update ptv related columns based on a total treatment volume

    Parameters
    ----------
    tv : dict
        treatment volume formatted as a "sets of points" object specified in
        tools.roi_geometry
    study_instance_uid : str
        study_instance_uid in SQL database

    """
    ptv_cross_section = roi_geom.cross_section(tv)
    ptv_spread = roi_geom.spread(tv)

    condition = (
        "study_instance_uid = '%s' and roi_type like 'PTV%%'"
        % study_instance_uid
    )
    with DVH_SQL() as cnx:
        max_dose = cnx.get_max_value("dvhs", "max_dose", condition=condition)
        min_dose = cnx.get_min_value("dvhs", "min_dose", condition=condition)

        ptv_data = {
            "ptv_cross_section_max": ptv_cross_section["max"],
            "ptv_cross_section_median": ptv_cross_section["median"],
            "ptv_max_dose": max_dose,
            "ptv_min_dose": min_dose,
            "ptv_spread_x": ptv_spread[0],
            "ptv_spread_y": ptv_spread[1],
            "ptv_spread_z": ptv_spread[2],
            "ptv_surface_area": roi_geom.surface_area(
                tv, coord_type="sets_of_points"
            ),
            "ptv_volume": roi_geom.volume(tv),
        }

        for key, value in ptv_data.items():
            cnx.update(
                "Plans",
                key,
                value,
                "study_instance_uid = '%s'" % study_instance_uid,
            )


def get_total_treatment_volume_of_study(study_instance_uid, ptvs=None):
    """Calculate combined PTV for the provided study_instance_uid

    Parameters
    ----------
    study_instance_uid : str
        study instance uid
    ptvs : list, optional
        names of ptvs (as stored in roi_name column)

    Returns
    -------
    dict
        a "sets of points" dictionary representing the total treatment volume

    """

    condition = (
        "study_instance_uid = '%s' and roi_type like 'PTV%%'"
        % study_instance_uid
    )
    if ptvs:
        condition += " and roi_name in ('%s')" % "','".join(ptvs)
    ptv_coordinates_strings = query("dvhs", "roi_coord_string", condition)

    ptvs = [
        roi_form.get_planes_from_string(ptv[0])
        for ptv in ptv_coordinates_strings
    ]

    return roi_geom.union(ptvs)


def get_treatment_volume_centroid(tv):
    """Get the centroid of a treatment volume

    Parameters
    ----------
    tv : dict
        treatment volume formatted as a "sets of points" object specified in
        tools.roi_geometry

    Returns
    -------
    np.ndarray
        DICOM coordinates of treatment volume centroid

    """
    return np.array(roi_geom.centroid(tv))


def get_treatment_volume_coord(tv):
    """Get the volume

    Parameters
    ----------
    tv : dict
        treatment volume formatted as a "sets of points" object specified in
        tools.roi_geometry

    Returns
    -------
    list
        The coordinates of the treatment volume, using
        tools.roi_formatter.get_roi_coordinates_from_planes

    """
    return roi_form.get_roi_coordinates_from_planes(tv)


def query(table, column, condition, unique=False):
    """Helper function, automatically creates connection for query

    Parameters
    ----------
    table : str
        DVHs', 'Plans', 'Rxs', 'Beams', or 'DICOM_Files'
    column : str: str
        a csv of SQL columns to be returned
    condition : str: str
        a condition in SQL syntax
    unique : bool, optional
        Call DVH_SQL.get_unique_values if true, DVH_SQL.query if false

    Returns
    -------
    list
        return of query

    """
    with DVH_SQL() as cnx:
        func = cnx.get_unique_values if unique else cnx.query
        ans = func(table, column, condition)
    return ans


def uid_has_ptvs(study_instance_uid):
    """Check if study instance uid has PTVs

    Parameters
    ----------
    study_instance_uid : str
        study instance uid

    Returns
    -------
    bool
        True if uid has any roi_name with an roi_type LIKE PTV%

    """
    with DVH_SQL() as cnx:
        condition = (
            "study_instance_uid = '%s' and roi_type LIKE 'PTV%%'"
            % study_instance_uid
        )
        ans = cnx.query("DVHs", "roi_type", condition)
    return bool(ans)


def update_roi_metric(
    roi_metric_calc, uid, callback=None, centroid_calc=False, ptv_calc=True
):
    """Call roi_metric_calc for ``uid``

    Parameters
    ----------
    roi_metric_calc : callable
        Function with parameters: study_insstance_uid, roi_name, precalc
    uid : str
        study instance uid
    callback : callable, optional
        Accepts a dict with keys of 'label' and 'gauge'
    centroid_calc : bool, optional
        Update pre_calc with get_treatment_volume_centroid
    ptv_calc : bool, optional
        roi_metric_calc involves getting a total treatment volume

    """
    pre_calc = None
    if ptv_calc:
        condition = "study_instance_uid = '%s' and roi_type like 'PTV%%'" % uid
        ptvs = [row[0] for row in query("DVHs", "roi_name", condition)]
        if len(ptvs):
            pre_calc = get_total_treatment_volume_of_study(uid, ptvs=ptvs)
            if centroid_calc:
                pre_calc = get_treatment_volume_centroid(pre_calc)

    if pre_calc is not None or not ptv_calc:
        condition = (
            "study_instance_uid = '%s' and roi_type not like 'PTV%%'" % uid
        )
        rois = [row[0] for row in query("DVHs", "roi_name", condition)]

        for i, roi in enumerate(rois):
            if pre_calc is None:
                roi_metric_calc(uid, roi)
            else:
                roi_metric_calc(uid, roi, pre_calc=pre_calc)
            if callback is not None:
                msg = {
                    "label": "Processing (%s of %s): %s"
                    % (i + 1, len(rois), roi),
                    "gauge": float(i / len(rois)),
                }
                callback(msg)


def update_ptv_dist_data(uid, callback=None):
    """Update PTV distance data with min_distances function

    Parameters
    ----------
    uid : str
        study instance uid
    callback : callable, optional
        Accepts a dict with keys of 'label' and 'gauge'

    """
    update_roi_metric(min_distances, uid, callback)


def update_ptv_overlap(uid, callback=None):
    """Update PTV overlap data with treatment_volume_overlap function

    Parameters
    ----------
    uid : str
        study instance uid
    callback : callable, optional
        Accepts a dict with keys of 'label' and 'gauge'

    """
    update_roi_metric(treatment_volume_overlap, uid, callback)


def update_ptv_centroid_distances(uid, callback=None):
    """Update PTV centroid distances with dist_to_ptv_centroids function

    Parameters
    ----------
    uid : str
        study instance uid
    callback : callable, optional
        Accepts a dict with keys of 'label' and 'gauge'

    """
    update_roi_metric(dist_to_ptv_centroids, uid, callback, centroid_calc=True)


def update_roi_centroid(uid, callback=None):
    """Update ROI centroids with centroid function

    Parameters
    ----------
    uid : str
        study instance uid
    callback : callable, optional
        Accepts a dict with keys of 'label' and 'gauge'

    """
    update_roi_metric(centroid, uid, callback, ptv_calc=False)


def update_roi_spread(uid, callback=None):
    """Update ROI spread values with spread function

    Parameters
    ----------
    uid : str
        study instance uid
    callback : callable, optional
        Accepts a dict with keys of 'label' and 'gauge'

    """
    update_roi_metric(spread, uid, callback, ptv_calc=False)


def update_roi_cross_section(uid, callback=None):
    """Update ROI cross section data with cross_section function

    Parameters
    ----------
    uid : str
        study instance uid
    callback : callable, optional
        Accepts a dict with keys of 'label' and 'gauge'

    """
    update_roi_metric(cross_section, uid, callback, ptv_calc=False)


def update_roi_surface_area(uid, callback=None):
    """Update ROI surface areas with surface_area function

    Parameters
    ----------
    uid : str
        study instance uid
    callback : callable, optional
        Accepts a dict with keys of 'label' and 'gauge'

    """
    update_roi_metric(surface_area, uid, callback, ptv_calc=False)


def update_roi_volume(uid, callback=None):
    """Update ROI volume with volumes function

    Parameters
    ----------
    uid : str
        study instance uid
    callback : callable, optional
        Accepts a dict with keys of 'label' and 'gauge'

    """
    update_roi_metric(volumes, uid, callback, ptv_calc=False)
