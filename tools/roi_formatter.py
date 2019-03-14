from shapely.geometry import Polygon, Point
from shapely import speedups
import numpy as np


MIN_SLICE_THICKNESS = 2  # Update method to pull from DICOM


# Enable shapely calculations using C, as opposed to the C++ default
if speedups.available:
    speedups.enable()


def get_planes_from_string(roi_coord_string):
    """
    :param roi_coord_string: roi string represntation of an roi as formatted in the SQL database
    :return: a "sets of points" formatted list
    :rtype: list
    """
    planes = {}
    contours = roi_coord_string.split(':')

    for contour in contours:
        contour = contour.split(',')
        z = contour.pop(0)
        z = round(float(z), 2)
        z_str = str(z)

        if z_str not in list(planes):
            planes[z_str] = []

        i, points = 0, []
        while i < len(contour):
            point = [float(contour[i]), float(contour[i+1]), z]
            points.append(point)
            i += 2
        planes[z_str].append(points)

    return planes


def points_to_shapely_polygon(sets_of_points):
    """
    :param sets_of_points: sets of points is a dictionary of lists using str(z) as keys
    :return: a composite polygon as a shapely object (eith polygon or multipolygon)
    """
    # sets of points are lists using str(z) as keys
    # each item is an ordered list of points representing a polygon, each point is a 3-item list [x, y, z]
    # polygon n is inside polygon n-1, then the current accumulated polygon is
    #    polygon n subtracted from the accumulated polygon up to and including polygon n-1
    #    Same method DICOM uses to handle rings and islands

    composite_polygon = []
    for set_of_points in sets_of_points:
        if len(set_of_points) > 3:
            points = [(point[0], point[1]) for point in set_of_points]
            points.append(points[0])  # Explicitly connect the final point to the first

            # if there are multiple sets of points in a slice, each set is a polygon,
            # interior polygons are subtractions, exterior are addition
            # Only need to check one point for interior vs exterior
            current_polygon = Polygon(points).buffer(0)  # clean stray points
            if composite_polygon:
                if Point((points[0][0], points[0][1])).disjoint(composite_polygon):
                    composite_polygon = composite_polygon.union(current_polygon)
                else:
                    composite_polygon = composite_polygon.symmetric_difference(current_polygon)
            else:
                composite_polygon = current_polygon

    return composite_polygon


def get_roi_coordinates_from_string(roi_coord_string):
    """
    :param roi_coord_string: the string reprentation of an roi in the SQL database
    :return: a list of numpy arrays, each array is the x, y, z coordinates of the given point
    :rtype: list
    """
    roi_coordinates = []
    contours = roi_coord_string.split(':')

    for contour in contours:
        contour = contour.split(',')
        z = contour.pop(0)
        z = float(z)
        i = 0
        while i < len(contour):
            roi_coordinates.append(np.array((float(contour[i]), float(contour[i + 1]), z)))
            i += 2

    return roi_coordinates


def get_roi_coordinates_from_planes(planes):
    """
    :param planes: a "sets of points" formatted list
    :return: a list of numpy arrays, each array is the x, y, z coordinates of the given point
    :rtype: list
    """
    roi_coordinates = []

    for z in list(planes):
        for polygon in planes[z]:
            for point in polygon:
                roi_coordinates.append(np.array((point[0], point[1], point[2])))
    return roi_coordinates


def dicompyler_roi_coord_to_db_string(coord):
    """
    :param coord: dicompyler structure coordinates from GetStructureCoordinates()
    :return: string representation of roi, <z1>: <x1 y1 x2 y2... xn yn>, <zn>: <x1 y1 x2 y2... xn yn>
    :rtype: str
    """
    contours = []
    for z in coord:
        for plane in coord[z]:
            points = [z]
            for point in plane['data']:
                points.append(str(round(point[0], 3)))
                points.append(str(round(point[1], 3)))
            contours.append(','.join(points))
    return ':'.join(contours)


def get_shapely_from_sets_of_points(sets_of_points):
    """
    :param sets_of_points: a dictionary of slices with key being a str representation of z value, value is a list
    of points defining a polygon in the slice.  point[0] is x and point[1] is y
    :return: roi_slice which is a dictionary of lists of z, thickness, and a Shapely Polygon class object
    :rtype: list
    """

    roi_slice = {'z': [], 'thickness': [], 'polygon': []}

    sets_of_points_keys = list(sets_of_points)
    sets_of_points_keys.sort()

    all_z_values = [round(float(z), 2) for z in sets_of_points_keys]
    thicknesses = np.abs(np.diff(all_z_values))
    if len(thicknesses):
        thicknesses = np.append(thicknesses, np.min(thicknesses))
    else:
        thicknesses = np.array([MIN_SLICE_THICKNESS])

    for z in sets_of_points:
        thickness = thicknesses[all_z_values.index(round(float(z), 2))]
        shapely_roi = points_to_shapely_polygon(sets_of_points[z])
        if shapely_roi:
            roi_slice['z'].append(round(float(z), 2))
            roi_slice['thickness'].append(thickness)
            roi_slice['polygon'].append(shapely_roi)

    return roi_slice


def dicompyler_roi_to_sets_of_points(coord):
    """
    :param coord: dicompyler structure coordinates from GetStructureCoordinates()
    :return: a dictionary of lists of points that define contours in each slice z
    :rtype: dict
    """
    all_points = {}
    for z in coord:
        all_points[z] = []
        for plane in coord[z]:
            plane_points = [[float(point[0]), float(point[1])] for point in plane['data']]
            for point in plane['data']:
                plane_points.append([float(point[0]), float(point[1])])
            if len(plane_points) > 2:
                all_points[z].append(plane_points)
    return all_points
