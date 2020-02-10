#!/usr/bin/env python
# -*- coding: utf-8 -*-

# tools.roi_geometry.py
"""
Tools for geometric calculations

"sets of points" objects
    dictionaries using str(z) as keys
        where z is the slice or z in DICOM coordinates
        each item is a list of points representing a polygon, each point is a 3-item list [x, y, z]

"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

from scipy.spatial.distance import cdist
import numpy as np
from math import ceil
from dvha.tools.roi_formatter import points_to_shapely_polygon, dicompyler_roi_to_sets_of_points,\
    get_shapely_from_sets_of_points


def union(rois):
    """
    Calculate the geometric union of the provided rois
    :param rois: rois formatted as "sets of points" dictionaries
    :type rois: list
    :return: a "sets of points" dictionary representing the union of the rois
    :rtype: dict
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
                    current_slice = current_slice.union(points_to_shapely_polygon(roi[z]))

        if current_slice:
            if current_slice.type != 'MultiPolygon':
                current_slice = [current_slice]

            for polygon in current_slice:
                xy = polygon.exterior.xy
                x_coord = xy[0]
                y_coord = xy[1]
                points = []
                for i in range(len(x_coord)):
                    points.append([x_coord[i], y_coord[i], round(float(z), 2)])
                new_roi[z].append(points)

                if hasattr(polygon, 'interiors'):
                    for interior in polygon.interiors:
                        xy = interior.coords.xy
                        x_coord = xy[0]
                        y_coord = xy[1]
                        points = []
                        for i in range(len(x_coord)):
                            points.append([x_coord[i], y_coord[i], round(float(z), 2)])
                        new_roi[z].append(points)
        else:
            print('WARNING: no contour found for slice %s' % z)

    return new_roi


def min_distances_to_target(oar_coordinates, target_coordinates):
    """
    Calculate all OAR-point-to-Target-point euclidean distances
    :param oar_coordinates: numpy arrays of 3D points defining the surface of the OAR
    :type oar_coordinates: list
    :param target_coordinates: numpy arrays of 3D points defining the surface of the PTV
    :type target_coordinates: list
    :return: min_distances: all minimum distances (cm) of OAR-point-to-Target-point pairs
    :rtype: list
    """
    # TODO: This very computationally expensive, needs a sampling method prior to calling cdist
    min_distances = []
    all_distances = cdist(oar_coordinates, target_coordinates, 'euclidean')
    for oar_point in all_distances:
        min_distances.append(float(np.min(oar_point)/10.))

    return min_distances


def cross_section(roi):
    """
    Calculate the cross section of a given roi
    :param roi: a "sets of points" formatted dictionary
    :type roi: dict
    :return: max and median cross-sectional area of all slices in cm^2
    :rtype: dict
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

    area = {'max': float(np.max(areas) / 100.),
            'median': float(np.median(areas) / 100.)}

    return area


def surface_area(coord, coord_type='dicompyler'):
    """
    Calculate the surface of a given roi
    :param coord: dicompyler structure coordinates from GetStructureCoordinates() or a sets_of_points dictionary
    :param coord_type: either 'dicompyler' or 'sets_of_points'
    :return: surface_area in cm^2
    :rtype: float
    """
    # TODO: This surface area method needs validation, but likely needs to be corrected

    if coord_type == "sets_of_points":
        sets_of_points = coord
    else:
        sets_of_points = dicompyler_roi_to_sets_of_points(coord)

    shapely_roi = get_shapely_from_sets_of_points(sets_of_points)

    slice_count = len(shapely_roi['z'])

    area = 0.
    polygon = shapely_roi['polygon']
    z = shapely_roi['z']
    thickness = min(shapely_roi['thickness'])

    for i in range(slice_count):
        for j in [-1, 1]:  # -1 for bottom area and 1 for top area
            # ensure bottom of first slice and top of last slice are fully added
            # if prev/next slice is not adjacent, assume non-contiguous ROI
            if (i == 0 and j == -1) or (i == slice_count-1 and j == 1) or abs(z[i] - z[i+j]) > 2*thickness:
                area += polygon[i].area
            else:
                area += polygon[i].difference(polygon[i+j]).area

        area += polygon[i].length * thickness

    return round(area/100, 3)


def overlap_volume(oar, tv):
    """
    Calculate the overlap volume of two rois
    :param oar: organ-at-risk as a "sets of points" formatted dictionary
    :type oar: dict
    :param tv: treatment volume as a "sets of points" formatted dictionary
    :type tv: dict
    :rtype: float
    """

    intersection_volume = 0.
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
                    intersection_volume += shapely_tv.intersection(shapely_oar).area * thickness

        return round(intersection_volume / 1000., 2)
    return 0.


def volume(roi):
    """
    :param roi: a "sets of points" formatted dictionary
    :return: volume in cm^3 of roi
    :rtype: float
    """

    # oar and ptv are lists using str(z) as keys
    # each item is an ordered list of points representing a polygon
    # polygon n is inside polygon n-1, then the current accumulated polygon is
    #    polygon n subtracted from the accumulated polygon up to and including polygon n-1
    #    Same method DICOM uses to handle rings and islands

    vol = 0.
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

    return round(vol / 1000., 2)


def centroid(roi):
    """
    :param roi: a "sets of points" formatted dictionary
    :return: centroid or the roi in x, y, z dicom coordinates (mm)
    :rtype: list
    """
    centroids = {'x': [], 'y': [], 'z': [], 'area': []}

    for z in list(roi):
        shapely_roi = points_to_shapely_polygon(roi[z])
        if shapely_roi and shapely_roi.area > 0:
            slice_centroid = shapely_roi.centroid
            polygon_count = len(slice_centroid.xy[0])
            for i in range(polygon_count):
                centroids['x'].append(slice_centroid.xy[0][i])
                centroids['y'].append(slice_centroid.xy[1][i])
                centroids['z'].append(float(z))
                if polygon_count > 1:
                    centroids['area'].append(shapely_roi[i].area)
                else:
                    centroids['area'].append(shapely_roi.area)

    x = np.array(centroids['x'])
    y = np.array(centroids['y'])
    z = np.array(centroids['z'])
    w = np.array(centroids['area'])
    w_sum = np.sum(w)

    volumetric_centroid = [float(np.sum(x * w) / w_sum),
                           float(np.sum(y * w) / w_sum),
                           float(np.sum(z * w) / w_sum)]

    return volumetric_centroid


def spread(roi):
    """
    :param roi: a "sets of points" formatted dictionary
    :return: x, y, z dimensions of a rectangular prism encompassing roi
    :rtype: list
    """
    all_points = {'x': [], 'y': [], 'z': []}

    for z in list(roi):
        for polygon in roi[z]:
            for point in polygon:
                all_points['x'].append(point[0])
                all_points['y'].append(point[1])
                all_points['z'].append(point[2])

    all_points = {'x': np.array(all_points['x']),
                  'y': np.array(all_points['y']),
                  'z': np.array(all_points['z'])}

    if len(all_points['x'] > 1):
        data = [abs(float(np.max(all_points[dim]) - np.min(all_points[dim]))) for dim in ['x', 'y', 'z']]
    else:
        data = [0, 0, 0]

    return data


def dth(min_distances):
    """
    :param min_distances: the output from min_distances_to_target
    :return: histogram of distances in 0.1mm bin widths
    :rtype: numpy.array
    """

    bin_count = int(ceil(np.max(min_distances) * 10.))
    data, bins = np.histogram(min_distances, bins=bin_count)

    return data
