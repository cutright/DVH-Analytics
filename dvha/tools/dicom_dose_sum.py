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
from scipy.interpolate import RegularGridInterpolator
from copy import deepcopy


class DoseGrid:
    """
    Class to easily access commonly used attributes of a DICOM dose grid and perform summations

    Example: Add two dose grids
        grid_1 = DoseGrid(dose_file_1)
        grid_2 = DoseGrid(dose_file_2)
        grid_sum = grid_1 + grid_2
        grid_sum.save_dcm(some_file_path)

    """
    def __init__(self, rt_dose, try_full_interp=True, interp_block_size=50000):
        """
        :param rt_dose: an RT Dose DICOM dataset or file_path
        :type rt_dose: pydicom.FileDataset
        :param try_full_interp: If true, will attempt to interpolate the entire grid at once before calculating one
                                block at a time (block size defined in self.interp_by_block)
        :type try_full_interp: bool
        :param interp_block_size: calculate this many points at a time if not try_full_interp or MemoryError
        :type interp_block_size: int
        """

        self.ds = self.__validate_input(rt_dose)
        self.try_full_interp = try_full_interp
        self.interp_block_size = interp_block_size

        if self.ds:
            self.__set_axes()

    def __set_axes(self):
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
        y, x, z = np.meshgrid(self.y_axis, self.x_axis, self.z_axis)
        points = np.vstack((x.ravel(), y.ravel(), z.ravel()))
        return points.transpose()

    ####################################################
    # Tools
    ####################################################
    def __add__(self, other):
        """Addition in this fashion will not alter either DoseGrid, but it is more expensive with memory"""
        new = deepcopy(self)
        new.add(other)
        return new

    def is_coincident(self, other):
        """Check dose grid coincidence, if True a direct summation is appropriate"""
        return self.ds.ImagePositionPatient == other.ds.ImagePositionPatient and \
               self.ds.pixel_array.shape == other.ds.pixel_array.shape and \
               self.ds.PixelSpacing == other.ds.PixelSpacing and \
               self.ds.GridFrameOffsetVector == other.ds.GridFrameOffsetVector

    def set_pixel_data(self):
        """
        Update the PixelData in the pydicom.FileDataset with the current self.dose_grid
        """
        self.ds.BitsAllocated = 32
        self.ds.BitsStored = 32
        self.ds.HighBit = 31
        self.ds.DoseGridScaling = 1. / np.max(self.dose_grid)
        pixel_data = np.swapaxes(self.dose_grid, 0, 2) / self.ds.DoseGridScaling
        self.ds.PixelData = np.uint32(pixel_data).tostring()

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
            self.interp_sum(other)

    def direct_sum(self, other, other_factor=1):
        """Directly sum two dose grids (only works if both are coincident)"""
        self.dose_grid += other.dose_grid * other_factor
        self.set_pixel_data()

    def interp_sum(self, other):
        """
        Interpolate the other dose grid to this dose grid's axes, then directly sum
        :param other: another DoseGrid
        :type other: DoseGrid
        """

        # TODO: Try scipy.ndimage.map_coordinates again, may be faster?
        interpolator = RegularGridInterpolator(points=other.axes, values=other.dose_grid,
                                               bounds_error=False, fill_value=0)

        other_grid = None
        if self.try_full_interp:
            try:
                other_grid = self.interp_entire_grid(interpolator)
            except MemoryError as e:
                pass
        if other_grid is None:
            other_grid = self.interp_by_block(interpolator)

        self.dose_grid += other_grid
        self.set_pixel_data()

    def interp_entire_grid(self, interpolator):
        """Interpolate the other dose grid to this dose grid's axes"""
        return interpolator(self.points).reshape(self.shape)

    def interp_by_block(self, interpolator):
        """
        Interpolate the other dose grid to this dose grid's axes, calculating one block at a time
        The block is defined at the init of this class, default is 50,000 points at a time
        :param interpolator: object to perform interpolation
        :type interpolator: RegularGridInterpolator
        """
        points = self.points
        point_count = np.product(self.shape)
        other_grid = np.zeros(point_count)

        block_count = int(np.floor(point_count / self.interp_block_size))

        for i in range(block_count):
            start = i * self.interp_block_size
            end = (i+1) * self.interp_block_size if i + 1 < block_count else -1
            other_grid[start:end] = interpolator(points[start:end])

        return other_grid.reshape(self.shape)
