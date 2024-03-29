#!/usr/bin/env python
# -*- coding: utf-8 -*-

# tools.roi_formatter.py
"""Formatting tools for roi data (dicompyler, Shapely, DVHA)"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

from shapely.geometry import Polygon, Point, MultiPolygon
from shapely.geometry.base import BaseGeometry
from shapely import speedups
import numpy as np
from dvha.tools.utilities import get_sorted_indices

# "sets of points" objects
#     dictionaries using str(z) as keys
#         where z is the slice or z in DICOM coordinates
#         each item is a list of points representing a polygon,
#         each point is a 3-item list [x, y, z]
#
# roi_coord_string from the SQL database
#     Each contour is delimited with a ':'
#         For example, ring ROIs will have an outer contour with a negative
#         inner contour
#     Each contour is a csv of of x,y,z values in the following format
#         z,x1,y1,x2,y2...xn,yn
#         Each contour has the same z coordinate for all points


MIN_SLICE_THICKNESS = 2  # Update method to pull from DICOM


# Enable shapely calculations using C, as opposed to the C++ default
if speedups.available:
    speedups.enable()


def get_planes_from_string(roi_coord_string):
    """

    Parameters
    ----------
    roi_coord_string : string: str
        roi string representation of an roi as formatted in the SQL database

    Returns
    -------
    dict
        a "sets of points" formatted dictionary

    """
    planes = {}
    contours = roi_coord_string.split(":")

    for contour in contours:
        contour = contour.split(",")
        z = contour.pop(0)
        z = round(float(z), 2)
        z_str = str(z)

        if z_str not in list(planes):
            planes[z_str] = []

        i, points = 0, []
        while i < len(contour):
            point = [float(contour[i]), float(contour[i + 1]), z]
            points.append(point)
            i += 2
        planes[z_str].append(points)

    return planes


def points_to_shapely_polygon(sets_of_points):
    """

    Parameters
    ----------
    sets_of_points : dict
        a "sets of points" formatted dictionary

    Returns
    -------
    BaseGeometry
        a composite polygon as a shapely object (either polygon or multipolygon)

    """

    composite_polygon = None
    for set_of_points in sets_of_points:
        if len(set_of_points) > 3:
            points = [(point[0], point[1]) for point in set_of_points]
            points.append(
                points[0]
            )  # Explicitly connect the final point to the first

            # if there are multiple sets of points in a slice, each set is a polygon,
            # interior polygons are subtractions, exterior are addition
            # Only need to check one point for interior vs exterior
            current_polygon = Polygon(points).buffer(0)  # clean stray points
            if composite_polygon:
                if Point((points[0][0], points[0][1])).disjoint(
                    composite_polygon
                ):
                    composite_polygon = composite_polygon.union(
                        current_polygon
                    )
                else:
                    composite_polygon = composite_polygon.symmetric_difference(
                        current_polygon
                    )
            else:
                composite_polygon = current_polygon

    return composite_polygon


def get_roi_coordinates_from_string(roi_coord_string):
    """

    Parameters
    ----------
    roi_coord_string : string: str
        roi string representation of an roi as formatted in the SQL database

    Returns
    -------
    list
        a list of numpy arrays, each array is the x, y, z coordinates of the given point

    """
    roi_coordinates = []
    contours = roi_coord_string.split(":")

    for contour in contours:
        contour = contour.split(",")
        z = contour.pop(0)
        z = float(z)
        i = 0
        while i < len(contour):
            roi_coordinates.append(
                np.array((float(contour[i]), float(contour[i + 1]), z))
            )
            i += 2

    return roi_coordinates


def get_roi_coordinates_from_planes(sets_of_points):
    """

    Parameters
    ----------
    sets_of_points : dict
        a "sets of points" formatted dictionary

    Returns
    -------
    list
        a list of numpy arrays, each array is the x, y, z coordinates of the given point

    """
    roi_coordinates = []

    for z in list(sets_of_points):
        for polygon in sets_of_points[z]:
            for point in polygon:
                roi_coordinates.append(
                    np.array((point[0], point[1], point[2]))
                )
    return roi_coordinates


def get_roi_coordinates_from_shapely(shapely_dict, sample_res=None):
    """

    Parameters
    ----------
    shapely_dict : dict
        output from get_shapely_from_sets_of_points
    sample_res : int, float
        If set to a numeric value, sample each polygon with this resolution (mm)

    Returns
    -------
    list
        a list of numpy arrays, each array is the x, y, z coordinates of the given point

    """
    roi_coordinates = []

    for i, shape in enumerate(shapely_dict["polygon"]):
        multi_polygon = shape if isinstance(shape, MultiPolygon) else [shape]
        for polygon in multi_polygon:
            if isinstance(sample_res, (int, float)):
                x, y = get_contour_sample(polygon, sample_res)
            else:
                x, y = polygon.exterior.coords.xy
            for j, point_x in enumerate(x):
                roi_coordinates.append(
                    np.array((point_x, y[j], shapely_dict["z"][i]))
                )
    return roi_coordinates


def dicompyler_roi_coord_to_db_string(coord):
    """

    Parameters
    ----------
    coord :
        dicompyler structure coordinates from GetStructureCoordinates()

    Returns
    -------
    str
        roi string representation of an roi as formatted in the SQL database (roi_coord_string)

    """
    contours = []
    for z in coord:
        for plane in coord[z]:
            points = [z]
            for point in plane["data"]:
                points.append(str(round(point[0], 3)))
                points.append(str(round(point[1], 3)))
            contours.append(",".join(points))
    return ":".join(contours)


def get_shapely_from_sets_of_points(sets_of_points, tolerance=None, preserve_topology=True):
    """

    Parameters
    ----------
    sets_of_points : dict
        a "sets of points" formatted dictionary
    tolerance : bool, optional
        If set to a number, will use Shapely's simplify on each contour with
        the given tolerance
    preserve_topology : bool, optional
        Passed to Shapely's simplify if ``simplify_tolerance`` is set

    Returns
    -------
    dict
        roi_slices which is a dictionary of lists of z, thickness, and a Shapely Polygon class object

    """

    roi_slices = {"z": [], "thickness": [], "polygon": []}

    sets_of_points_keys = list(sets_of_points)  # lock in for-loop order
    z_values = [float(key) for key in sets_of_points]

    # Get the thickness of each slice
    order = get_sorted_indices(z_values)
    thickness = np.abs(np.diff([z_values[i] for i in order]))
    if len(thickness):
        thickness = np.append(thickness, np.min(thickness))
    else:
        thickness = np.array([MIN_SLICE_THICKNESS])

    for i, z in enumerate(sets_of_points_keys):
        polygon = points_to_shapely_polygon(sets_of_points[z])
        if polygon:
            if tolerance is not None:
                polygon = polygon.simplify(tolerance, preserve_topology)
            roi_slices["z"].append(round(float(z), 2))
            roi_slices["thickness"].append(thickness[order[i]])
            roi_slices["polygon"].append(polygon)

    return roi_slices


def dicompyler_roi_to_sets_of_points(coord):
    """

    Parameters
    ----------
    coord :
        dicompyler structure coordinates from GetStructureCoordinates()

    Returns
    -------
    dict
        a "sets of points" formatted dictionary

    """
    all_points = {}
    for z in coord:
        all_points[z] = []
        for plane in coord[z]:
            plane_points = [
                [float(point[0]), float(point[1])] for point in plane["data"]
            ]
            for point in plane["data"]:
                plane_points.append([float(point[0]), float(point[1])])
            if len(plane_points) > 2:
                all_points[z].append(plane_points)
    return all_points


def get_contour_sample(polygon, dth_res=0.5) -> tuple:
    """Get 3D points uniformly distributed in the perimeter space

    Parameters
    ----------
    polygon : Polygon
        shapely object
    dth_res : int, float
        Sampling distance in perimeter space (mm)

    Returns
    -------
    np.ndarray
        x coordinates of sampled contour
    np.ndarray
        y coordinates of sampled contour

    """
    # Get coordinates of polygon and index array
    x, y = polygon.exterior.coords.xy
    indices = np.arange(len(x))

    # cumulative path length
    s = np.cumsum(np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2))
    num_samples = int(np.floor(s[-1] / dth_res))

    # path length space
    sample_s = np.arange(num_samples) * dth_res

    # path length space to index space
    sample_i = np.interp(sample_s, s, indices[1:])

    # Get x and y coordinates of sampled index space
    sample_x = np.interp(sample_i, indices, x)
    sample_y = np.interp(sample_i, indices, y)

    return sample_x, sample_y
