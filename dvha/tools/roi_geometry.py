#!/usr/bin/env python
# -*- coding: utf-8 -*-

# tools.roi_geometry.py
"""
Tools for geometric calculations
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

from scipy.spatial.distance import cdist
import numpy as np
from math import ceil
from shapely.geometry import Point
from dvha.tools.roi_formatter import (
    points_to_shapely_polygon,
    dicompyler_roi_to_sets_of_points,
    get_shapely_from_sets_of_points,
)


# "sets of points" objects
#     dictionaries using str(z) as keys
#         where z is the slice or z in DICOM coordinates
#         each item is a list of points representing a polygon,
#         each point is a 3-item list [x, y, z]


def union(rois):
    """Calculate the geometric union of the provided rois

    Parameters
    ----------
    rois : list
        rois formatted as "sets of points" dictionaries

    Returns
    -------
    dict
        a "sets of points" dictionary representing the union of the rois

    """

    new_roi = {}

    all_z_values = []
    for roi in rois:
        for z in list(roi):
            if z not in all_z_values:
                all_z_values.append(z)

    for z in all_z_values:

        if z not in list(new_roi):
            new_roi[z] = []

        # Convert to shapely objects
        current_slice = None
        for roi in rois:
            # Make sure current roi has at least 3 points in z plane
            if z in list(roi) and len(roi[z][0]) > 2:
                if not current_slice:
                    current_slice = points_to_shapely_polygon(roi[z])
                else:
                    current_slice = current_slice.union(
                        points_to_shapely_polygon(roi[z])
                    )

        if current_slice:
            if current_slice.type != "MultiPolygon":
                current_slice = [current_slice]

            for polygon in current_slice:
                xy = polygon.exterior.xy
                x_coord = xy[0]
                y_coord = xy[1]
                points = []
                for i in range(len(x_coord)):
                    points.append([x_coord[i], y_coord[i], round(float(z), 2)])
                new_roi[z].append(points)

                if hasattr(polygon, "interiors"):
                    for interior in polygon.interiors:
                        xy = interior.coords.xy
                        x_coord = xy[0]
                        y_coord = xy[1]
                        points = []
                        for i in range(len(x_coord)):
                            points.append(
                                [x_coord[i], y_coord[i], round(float(z), 2)]
                            )
                        new_roi[z].append(points)
        else:
            # print('WARNING: no contour found for slice %s' % z)
            pass
    return new_roi


def min_distances_to_target(oar_coordinates, target_coordinates, factors=None):
    """Calculate all OAR-point-to-Target-point euclidean distances

    Parameters
    ----------
    oar_coordinates : list
        numpy arrays of 3D points defining the surface of the OAR
    target_coordinates : list
        numpy arrays of 3D points defining the surface of the PTV
    factors :
         (Default value = None)

    Returns
    -------
    list
        min_distances: all minimum distances (cm) of OAR-point-to-Target-point pairs

    """
    # TODO: This very computationally expensive, needs a sampling method prior to calling cdist
    min_distances = []
    all_distances = cdist(oar_coordinates, target_coordinates, "euclidean")
    for i, oar_point in enumerate(all_distances):
        min_distances.append(float(np.min(oar_point) / 10.0))
        if factors is not None:
            min_distances[i] *= factors[i]

    return min_distances


def is_point_inside_roi(point, roi):
    """Check if a point is within an ROI

    Parameters
    ----------
    point : list
        x, y, z
    roi : dict
        roi: a "sets of points" formatted dictionary

    Returns
    -------
    bool
        Whether or not the poin is within the roi

    """
    z_keys = list(roi.keys())
    roi_z = np.array([float(z) for z in z_keys])
    if np.max(roi_z) > point[2] > np.min(roi_z):
        nearest_z_index = (np.abs(roi_z - point[2])).argmin()
        nearest_z_key = z_keys[nearest_z_index]
        if (
            abs(float(nearest_z_key) - point[2]) < 0.5
        ):  # make sure point is within 0.5mm
            if (
                len(roi[nearest_z_key]) > 2
            ):  # make sure there are 3 points to make a polygon
                shapely_roi = points_to_shapely_polygon(roi[nearest_z_key])
                shapely_point = Point(point[0], point[1])
                return shapely_point.within(shapely_roi)
    return False


def cross_section(roi):
    """Calculate the cross section of a given roi

    Parameters
    ----------
    roi : dict
        a "sets of points" formatted dictionary

    Returns
    -------
    dict
        max and median cross-sectional area of all slices in cm^2

    """
    areas = []

    for z in list(roi):
        shapely_roi = points_to_shapely_polygon(roi[z])
        if shapely_roi and shapely_roi.area > 0:
            slice_centroid = shapely_roi.centroid
            polygon_count = len(slice_centroid.xy[0])
            for i in range(polygon_count):
                if polygon_count > 1:
                    areas.append(shapely_roi[i].area)
                else:
                    areas.append(shapely_roi.area)

    areas = np.array(areas)

    area = {
        "max": float(np.max(areas) / 100.0),
        "median": float(np.median(areas) / 100.0),
    }

    return area


def surface_area(coord, coord_type="dicompyler"):
    """Calculate the surface of a given roi

    Parameters
    ----------
    coord :
        dicompyler structure coordinates from GetStructureCoordinates() or a sets_of_points dictionary
    coord_type :
        either 'dicompyler' or 'sets_of_points' (Default value = 'dicompyler')

    Returns
    -------
    float
        surface_area in cm^2

    """
    # TODO: This surface area method needs validation, but likely needs to be corrected

    if coord_type == "sets_of_points":
        sets_of_points = coord
    else:
        sets_of_points = dicompyler_roi_to_sets_of_points(coord)

    shapely_roi = get_shapely_from_sets_of_points(sets_of_points)

    slice_count = len(shapely_roi["z"])

    area = 0.0
    polygon = shapely_roi["polygon"]
    z = shapely_roi["z"]
    thickness = min(shapely_roi["thickness"])

    for i in range(slice_count):
        for j in [-1, 1]:  # -1 for bottom area and 1 for top area
            # ensure bottom of first slice and top of last slice are fully added
            # if prev/next slice is not adjacent, assume non-contiguous ROI
            if (
                (i == 0 and j == -1)
                or (i == slice_count - 1 and j == 1)
                or abs(z[i] - z[i + j]) > 2 * thickness
            ):
                area += polygon[i].area
            else:
                area += polygon[i].difference(polygon[i + j]).area

        area += polygon[i].length * thickness

    return round(area / 100, 3)


def overlap_volume(oar, tv):
    """Calculate the overlap volume of two rois

    Parameters
    ----------
    oar : dict
        organ-at-risk as a "sets of points" formatted dictionary
    tv : dict
        treatment volume as a "sets of points" formatted dictionary

    Returns
    -------

    """

    intersection_volume = 0.0
    all_z_values = [round(float(z), 2) for z in list(tv)]
    all_z_values = np.sort(all_z_values)
    thicknesses = np.abs(np.diff(all_z_values))
    if len(thicknesses) > 0:
        thicknesses = np.append(thicknesses, np.min(thicknesses))
        all_z_values = all_z_values.tolist()

        for z in list(tv):
            # z in coord will not necessarily go in order of z, convert z to float to lookup thickness
            # also used to check for top and bottom slices, to add area of those contours

            if z in list(oar):
                thickness = thicknesses[all_z_values.index(round(float(z), 2))]
                shapely_tv = points_to_shapely_polygon(tv[z])
                shapely_oar = points_to_shapely_polygon(oar[z])
                if shapely_oar and shapely_tv:
                    intersection_volume += (
                        shapely_tv.intersection(shapely_oar).area * thickness
                    )

        return round(intersection_volume / 1000.0, 2)
    return 0.0


def volume(roi):
    """

    Parameters
    ----------
    roi :
        a "sets of points" formatted dictionary

    Returns
    -------
    float
        volume in cm^3 of roi

    """

    # oar and ptv are lists using str(z) as keys
    # each item is an ordered list of points representing a polygon
    # polygon n is inside polygon n-1, then the current accumulated polygon is
    #    polygon n subtracted from the accumulated polygon up to and including polygon n-1
    #    Same method DICOM uses to handle rings and islands

    vol = 0.0
    all_z_values = [round(float(z), 2) for z in list(roi)]
    all_z_values = np.sort(all_z_values)
    thicknesses = np.abs(np.diff(all_z_values))
    thicknesses = np.append(thicknesses, np.min(thicknesses))
    all_z_values = all_z_values.tolist()

    for z in list(roi):
        # z in coord will not necessarily go in order of z, convert z to float to lookup thickness
        # also used to check for top and bottom slices, to add area of those contours

        thickness = thicknesses[all_z_values.index(round(float(z), 2))]
        shapely_roi = points_to_shapely_polygon(roi[z])
        if shapely_roi:
            vol += shapely_roi.area * thickness

    return round(vol / 1000.0, 2)


def centroid(roi):
    """

    Parameters
    ----------
    roi :
        a "sets of points" formatted dictionary

    Returns
    -------
    list
        centroid or the roi in x, y, z dicom coordinates (mm)

    """
    centroids = {"x": [], "y": [], "z": [], "area": []}

    for z in list(roi):
        shapely_roi = points_to_shapely_polygon(roi[z])
        if shapely_roi and shapely_roi.area > 0:
            slice_centroid = shapely_roi.centroid
            polygon_count = len(slice_centroid.xy[0])
            for i in range(polygon_count):
                centroids["x"].append(slice_centroid.xy[0][i])
                centroids["y"].append(slice_centroid.xy[1][i])
                centroids["z"].append(float(z))
                if polygon_count > 1:
                    centroids["area"].append(shapely_roi[i].area)
                else:
                    centroids["area"].append(shapely_roi.area)

    x = np.array(centroids["x"])
    y = np.array(centroids["y"])
    z = np.array(centroids["z"])
    w = np.array(centroids["area"])
    w_sum = np.sum(w)

    volumetric_centroid = [
        float(np.sum(x * w) / w_sum),
        float(np.sum(y * w) / w_sum),
        float(np.sum(z * w) / w_sum),
    ]

    return volumetric_centroid


def spread(roi):
    """

    Parameters
    ----------
    roi :
        a "sets of points" formatted dictionary

    Returns
    -------
    list
        x, y, z dimensions of a rectangular prism encompassing roi

    """
    all_points = {"x": [], "y": [], "z": []}

    for z in list(roi):
        for polygon in roi[z]:
            for point in polygon:
                all_points["x"].append(point[0])
                all_points["y"].append(point[1])
                all_points["z"].append(point[2])

    all_points = {
        "x": np.array(all_points["x"]),
        "y": np.array(all_points["y"]),
        "z": np.array(all_points["z"]),
    }

    if len(all_points["x"] > 1):
        data = [
            abs(float(np.max(all_points[dim]) - np.min(all_points[dim])))
            / 10.0
            for dim in ["x", "y", "z"]
        ]
    else:
        data = [0, 0, 0]

    return data


def dth(min_distances):
    """

    Parameters
    ----------
    min_distances :
        the output from min_distances_to_target

    Returns
    -------
    numpy.array
        histogram of distances in 1mm bin widths

    """
    min_distances = 10.0 * np.array(min_distances)
    max_abs_value = int(ceil(np.max(np.abs(min_distances))))
    data, bins = np.histogram(
        min_distances,
        bins=max_abs_value * 2 + 1,
        range=(-max_abs_value - 1, max_abs_value),
    )

    return np.divide(data, np.sum(data))


def process_dth_string(dth_string):
    """Convert a dth_string from the database into data and bins
    DVHA stores 1-mm binned surface DTHs with an odd number of bins, middle bin is 0.

    Parameters
    ----------
    dth_string :
        a value from the dth_string column

    Returns
    -------
    type
        counts, bin positions (mm)

    """
    counts = np.array(dth_string.split(","), dtype=np.float)
    max_bin = (len(counts) - 1) / 2
    bins = np.linspace(-max_bin, max_bin, len(counts))
    return bins, counts
