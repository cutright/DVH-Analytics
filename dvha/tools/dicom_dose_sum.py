#!/usr/bin/env python
# -*- coding: utf-8 -*-

# tools.dicom_dose_sum.py
"""
Class for summing dose grids
"""
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import numpy as np
from os.path import isfile
import pydicom
from scipy.ndimage import map_coordinates
from scipy.interpolate import RegularGridInterpolator


class DoseGrid:
    """
    Class to easily access commonly used attributes of a DICOM dose grid and perform summations

    Example: Add two dose grids
        grid_1 = DoseGrid(dose_file_1)
        grid_2 = DoseGrid(dose_file_2)
        grid_1.add(grid_2)
        grid_1.save_dcm(some_file_path)

    """
    def __init__(self, rt_dose):
        """
        :param rt_dose: an RT Dose dicom dataset or file_path
        :type rt_dose: pydicom.FileDataset
        """

        self.ds = self.__validate_input(rt_dose)
        if self.ds:
            self.x_axis = np.arange(self.ds.Columns) * self.ds.PixelSpacing[0] + self.ds.ImagePositionPatient[0]
            self.y_axis = np.arange(self.ds.Rows) * self.ds.PixelSpacing[1] + self.ds.ImagePositionPatient[1]
            self.z_axis = np.array(self.ds.GridFrameOffsetVector) + self.ds.ImagePositionPatient[2]

            # x and z are swapped in the pixel_array
            self.dose_grid = np.swapaxes(self.ds.pixel_array * self.ds.DoseGridScaling, 0, 2)

    @staticmethod
    def __validate_input(rt_dose):
        """Ensure provided input is either an RT Dose pydicom.FileDataset or a file_path to one"""
        if type(rt_dose) is pydicom.FileDataset:
            if rt_dose.Modality.lower() == 'rtdose':
                return rt_dose
            print("The provided pydicom.FileDataset is not RTDOSE")
            return
        elif isfile(rt_dose):
            try:
                rt_dose_ds = pydicom.read_file(rt_dose)
                if rt_dose_ds.Modality.lower() == 'rtdose':
                    return rt_dose_ds
                print('The provided file_path points to a DICOM file, but it is not an RT Dose file.')
            except Exception as e:
                print(e)
                print('The provided input is neither a pydicom.FileDataset nor could it be read by pydicom.')
        return

    ####################################################
    # Basic properties
    ####################################################
    @property
    def shape(self):
        """Get the x, y, z dimensions of the dose grid"""
        return tuple([self.ds.Columns, self.ds.Rows, len(self.ds.GridFrameOffsetVector)])

    @property
    def axes(self):
        """Get the x, y, z axes of the dose grid (in mm)"""
        return [self.x_axis, self.y_axis, self.z_axis]

    @property
    def scale(self):
        """Get the dose grid resolution (xyz)"""
        return np.array([self.ds.PixelSpacing[0],
                         self.ds.PixelSpacing[1],
                         self.ds.GridFrameOffsetVector[1] - self.ds.GridFrameOffsetVector[0]])

    @property
    def offset(self):
        """Get the coordinates of the dose grid origin (mm)"""
        return np.array(self.ds.ImagePositionPatient, dtype='float')

    @property
    def points(self):
        """Get all of the points in the dose grid"""
        # points = []
        # for x in self.x_axis:
        #     for y in self.y_axis:
        #         for z in self.z_axis:
        #             points.append([x, y, z])
        # return points

        # This is equivalent to above, but more memory efficient
        y, x, z = np.meshgrid(self.y_axis, self.x_axis, self.z_axis)
        points = np.vstack((x.ravel(), y.ravel(), z.ravel()))
        return points.transpose()

    ####################################################
    # Tools
    ####################################################
    def is_coincident(self, other):
        """Check dose grid coincidence, if True a direct summation is appropriate"""
        return self.ds.ImagePositionPatient == other.ds.ImagePositionPatient and \
               self.ds.pixel_array.shape == other.ds.pixel_array.shape and \
               self.ds.PixelSpacing == other.ds.PixelSpacing and \
               self.ds.GridFrameOffsetVector == other.ds.GridFrameOffsetVector

    def set_pixel_data(self, pixel_data):
        """
        Update the PixelData in the pydicom.FileDataset
        :param pixel_data: a 3D numpy array with the same dimensions as self.ds.pixel_array
        :type pixel_data: np.array
        """
        self.ds.BitsAllocated = 32
        self.ds.BitsStored = 32
        self.ds.HighBit = 31
        self.ds.PixelData = np.uint32(pixel_data / self.ds.DoseGridScaling).tostring()

    def save_dcm(self, file_path):
        """Save the pydicom.FileDataset to file"""
        self.ds.save_as(file_path)

    ####################################################
    # Dose Summation
    ####################################################
    def add(self, other):
        """
        Add another 3D dose grid to this 3D dose grid, with interpolation if needed
        :param other: another DoseGrid
        :type other: DoseGrid
        """
        if self.is_coincident(other):
            self.direct_sum(other)
        else:
            self.interp_sum_by_chunk(other)

    def direct_sum(self, other):
        """Directly sum two dose grids (only works if both are coincident)"""
        dose_sum = self.ds.pixel_array * self.ds.DoseGridScaling + other.ds.pixel_array * other.ds.DoseGridScaling
        self.set_pixel_data(dose_sum)

    def interp_sum(self, other):
        """
        Interpolate the other dose grid to this dose grid's axes, then directly sum
        :param other: another DoseGrid
        :type other: DoseGrid
        """
        interpolator = RegularGridInterpolator(points=other.axes, values=other.dose_grid,
                                               bounds_error=False, fill_value=0)
        other_grid = interpolator(self.points).reshape(self.shape)
        self.dose_grid += other_grid
        self.set_pixel_data(np.swapaxes(self.dose_grid, 0, 2))

    def interp_sum_by_chunk(self, other):
        """
        Interpolate the other dose grid to this dose grid's axes, then directly sum
        :param other: another DoseGrid
        :type other: DoseGrid
        """
        interpolator = RegularGridInterpolator(points=other.axes, values=other.dose_grid,
                                               bounds_error=False, fill_value=0)
        points = self.points
        point_count = np.product(self.shape)
        other_grid = np.zeros(point_count)
        patch_count = 100
        patch_len = int(np.floor(point_count / float(patch_count)))
        for i in range(patch_count):
            start = i * patch_len
            end = (i+1) * patch_len if i + 1 < patch_count else -1
            other_grid[start:end] = interpolator(points[start:end])
        other_grid = other_grid.reshape(self.shape)
        self.dose_grid += other_grid
        self.set_pixel_data(np.swapaxes(self.dose_grid, 0, 2))
