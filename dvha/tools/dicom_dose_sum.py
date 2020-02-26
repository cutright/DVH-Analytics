#!/usr/bin/env python
# -*- coding: utf-8 -*-

# tools.dicom_dose_sum.py
"""
Functions for summing dose grids
"""
# Largely borrowed from https://github.com/dicompyler/dicompyler-plugins/blob/master/plugins/plansum/plansum.py
# Original code written by Stephen Terry
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import numpy as np
import pydicom
from scipy.interpolate import RegularGridInterpolator
# from dolo.numeric.interpolation.smolyak import SmolyakGrid


# Slightly modified from https://github.com/dicompyler/dicompyler-plugins/blob/master/plugins/plansum/plansum.py
def sum_two_dose_grids(old, new):
    """ Given two Dicom RTDose objects, returns a summed RTDose object"""
    """The summed RTDose object will consist of pixels inside the region of 
    overlap between the two pixel_arrays.  The pixel spacing will be the 
    coarser of the two objects in each direction.  The new DoseGridScaling
    tag will be the sum of the tags of the two objects.

    interp_method: A string that is one of ['scipy','weave','python'].  
        This forces SumPlan to use a particular interpolation method, even if 
        the dose objects could be directly summed.  Used for unit testing."""

    # Recycle the new Dicom object to store the summed dose values
    sum_dcm = new

    # Test if dose grids are coincident.  If so, we can directly sum the
    # pixel arrays.

    if (old.ImagePositionPatient == new.ImagePositionPatient and
            old.pixel_array.shape == new.pixel_array.shape and
            old.PixelSpacing == new.PixelSpacing and
            old.GridFrameOffsetVector == new.GridFrameOffsetVector):
        print("PlanSum: Using direct summation")
        dose_sum = old.pixel_array * old.DoseGridScaling + new.pixel_array * new.DoseGridScaling

    else:
        # Compute mapping from xyz (physical) space to ijk (index) space
        scale_old = np.array([old.PixelSpacing[0], old.PixelSpacing[1],
                              old.GridFrameOffsetVector[1] - old.GridFrameOffsetVector[0]])

        scale_new = np.array([new.PixelSpacing[0], new.PixelSpacing[1],
                              new.GridFrameOffsetVector[1] - new.GridFrameOffsetVector[0]])

        scale_sum = np.maximum(scale_old, scale_new)

        # Find region of overlap
        xmin = np.array([old.ImagePositionPatient[0], new.ImagePositionPatient[0]])
        ymin = np.array([old.ImagePositionPatient[1], new.ImagePositionPatient[1]])
        zmin = np.array([old.ImagePositionPatient[2], new.ImagePositionPatient[2]])
        xmax = np.array([old.ImagePositionPatient[0] + old.PixelSpacing[0] * old.Columns,
                         new.ImagePositionPatient[0] + new.PixelSpacing[0] * new.Columns])
        ymax = np.array([old.ImagePositionPatient[1] + old.PixelSpacing[1] * old.Rows,
                         new.ImagePositionPatient[1] + new.PixelSpacing[1] * new.Rows])
        zmax = np.array([old.ImagePositionPatient[2] + scale_old[2] * len(old.GridFrameOffsetVector),
                         new.ImagePositionPatient[2] + scale_new[2] * len(new.GridFrameOffsetVector)])
        x0 = xmin[np.argmin(abs(xmin))]
        x1 = xmax[np.argmin(abs(xmax))]
        y0 = ymin[np.argmin(abs(ymin))]
        y1 = ymax[np.argmin(abs(ymax))]
        z0 = zmin[np.argmin(abs(zmin))]
        z1 = zmax[np.argmin(abs(zmax))]

        sum_ip = np.array([x0, y0, z0])

        # Create index grid for the sum array
        i, j, k = np.mgrid[0:int((x1 - x0) / scale_sum[0]),
                           0:int((y1 - y0) / scale_sum[1]),
                           0:int((z1 - z0) / scale_sum[2])]

        # x_vals = np.arange(x0, x1, scale_sum[0])
        # y_vals = np.arange(y0, y1, scale_sum[1])
        z_vals = np.arange(z0, z1, scale_sum[2])

        # Create a 3 x i x j x k array of xyz coordinates for the interpolation.
        sum_xyz_coords = np.array([i * scale_sum[0] + sum_ip[0],
                                   j * scale_sum[1] + sum_ip[1],
                                   k * scale_sum[2] + sum_ip[2]])

        # Dicom pixel_array objects seem to have the z axis in the first index
        # (zyx).  The x and z axes are swapped before interpolation to coincide
        # with the xyz ordering of ImagePositionPatient
        dose_sum = interpolate_image(np.swapaxes(old.pixel_array, 0, 2), scale_old,
                                     old.ImagePositionPatient, sum_xyz_coords) * old.DoseGridScaling
        dose_interp_2 = interpolate_image(np.swapaxes(new.pixel_array, 0, 2), scale_new,
                                          new.ImagePositionPatient, sum_xyz_coords) * new.DoseGridScaling
        dose_sum += dose_interp_2

        # Swap the x and z axes back
        dose_sum = np.swapaxes(dose_sum, 0, 2)
        sum_dcm.ImagePositionPatient = list(sum_ip)
        sum_dcm.Rows = dose_sum.shape[2]
        sum_dcm.Columns = dose_sum.shape[1]
        sum_dcm.NumberOfFrames = dose_sum.shape[0]
        sum_dcm.PixelSpacing = [scale_sum[0], scale_sum[1]]
        sum_dcm.GridFrameOffsetVector = list(z_vals - sum_ip[2])

    sum_scaling = old.DoseGridScaling + new.DoseGridScaling

    dose_sum = dose_sum / sum_scaling
    dose_sum = np.uint32(dose_sum)

    # sum_dcm.pixel_array = sum
    sum_dcm.BitsAllocated = 32
    sum_dcm.BitsStored = 32
    sum_dcm.HighBit = 31
    sum_dcm.PixelData = dose_sum.tostring()
    sum_dcm.DoseGridScaling = sum_scaling


def interpolate_image(input_array, scale, offset, xyz_coords):
    """Interpolates an array at the xyz coordinates given"""
    """Parameters:
        input_array: a 3D numpy array

        scale: a list of 3 floats which give the pixel spacing in xyz

        offset: the xyz coordinates of the origin of the input_array

        xyz_coordinates: the coordinates at which the input is evaluated. 


    The purpose of this function is to convert the xyz coordinates to
    index space, which trilinear_interp
    requires.  Following the scipy convention, the xyz_coordinates array is
    an array of three  i x j x k element arrays.  The first element contains 
    the x axis value for each of the i x j x k elements, the second contains
    the y axis value, etc."""

    indices = np.empty(xyz_coords.shape)
    indices[0] = (xyz_coords[0] - offset[0]) / scale[0]
    indices[1] = (xyz_coords[1] - offset[1]) / scale[1]
    indices[2] = (xyz_coords[2] - offset[2]) / scale[2]

    return trilinear_interp(input_array, indices)
    # return RegularGridInterpolator(indices, input_array)


def trilinear_interp(input_array, indices):
    """Evaluate the input_array data at the indices given"""

    # output = np.empty(indices[0].shape)
    x_indices = indices[0]
    y_indices = indices[1]
    z_indices = indices[2]

    x0 = x_indices.astype(np.integer)
    y0 = y_indices.astype(np.integer)
    z0 = z_indices.astype(np.integer)
    # Check if xyz0 is beyond array boundary:
    x0[np.where(x0 >= input_array.shape[0])] = np.shape(input_array)[0] - 1
    y0[np.where(y0 >= input_array.shape[1])] = np.shape(input_array)[1] - 1
    z0[np.where(z0 >= input_array.shape[2])] = np.shape(input_array)[2] - 1

    x1 = x0 + 1
    y1 = y0 + 1
    z1 = z0 + 1
    # Check if xyz1 is beyond array boundary:
    x1[np.where(x1 >= input_array.shape[0])] = x0.max()
    y1[np.where(y1 >= input_array.shape[1])] = y0.max()
    z1[np.where(z1 >= input_array.shape[2])] = z0.max()

    x = x_indices - x0
    y = y_indices - y0
    z = z_indices - z0

    output = input_array[x0, y0, z0] * tri_linear_factor(x, y, z, 0, 0, 0)
    for zi, zz in enumerate([z0, z1]):
        for yi, yy in enumerate([y0, y1]):
            for xi, xx in enumerate([x0, x1]):
                if xi + yi + zi:  # ignore 0 0 0 since it was created before loops
                    output += input_array[xx, yy, zz] * tri_linear_factor(x, y, z, xi, yi, zi)

    return output


def tri_linear_factor(x, y, z, xi, yi, zi):
    ans = x if xi else (1 - x)
    ans = ans * y if yi else ans * (1 - y)
    ans = ans * z if zi else ans * (1 - z)
    return ans


class DoseGrid:
    def __init__(self, ds):
        self.ds = ds
        self.__set_axes()

        # x and z are swapped in the pixel_array
        self.dose_grid = np.swapaxes(self.ds.pixel_array * self.ds.DoseGridScaling, 0, 2)

    def __set_axes(self):
        pixel_spacing = self.ds.PixelSpacing
        image_position = self.ds.ImagePositionPatient

        self.x_axis = np.arange(self.ds.Columns) * pixel_spacing[0] + image_position[0]
        self.y_axis = np.arange(self.ds.Rows) * pixel_spacing[1] + image_position[1]
        self.z_axis = np.array(self.ds.GridFrameOffsetVector) + image_position[2]

    def is_point_inside_grid(self, xyz):
        for a, axis in enumerate(self.axes):
            if not (np.min(axis) <= xyz[a] <= np.max(axis)):
                return False
        return True

    @property
    def grid_size(self):
        return [self.ds.Columns, self.ds.Rows, len(self.ds.GridFrameOffsetVector)]

    @property
    def axes(self):
        return [self.x_axis, self.y_axis, self.z_axis]

    def get_xyz(self, ijk):
        """Convert an ijk coordinate into xyz space"""
        i, j, k = ijk[0], ijk[1], ijk[2]
        return np.array([self.x_axis[i], self.y_axis[j], self.z_axis[k]])

    def get_ijk(self, xyz):
        """Convert an xyz coordinate into ijk space"""
        return [int(np.interp(xyz[a], axis, np.arange(self.grid_size[a]))) for a, axis in enumerate(self.axes)]

    def add_dose(self, xyz, dose):
        ijk = self.get_ijk(xyz)
        self.dose_grid[ijk[0], ijk[1], ijk[2]] += dose

    def update_pixel_array(self):
        scaling = 1 / np.max(self.dose_grid)

        self.ds.BitsAllocated = 32
        self.ds.BitsStored = 32
        self.ds.HighBit = 31
        self.ds.DoseGridScaling = scaling

        # swap x and z back
        self.ds.PixelData = np.uint32(np.swapaxes(self.dose_grid, 0, 2) / scaling).tostring()


class DoseInterpolator(DoseGrid):
    """Inherit DoseGrid, separate class so a RegularGridInterpolator isn't created for every DoseGrid"""
    def __init__(self, ds):
        DoseGrid.__init__(self, ds)
        self.interpolator = RegularGridInterpolator(points=self.axes, values=self.dose_grid, bounds_error=False)

    def get_dose(self, xyz):
        return self.get_doses([xyz])[0]

    def get_doses(self, list_of_xyz):
        list_of_xyz = [xyz for xyz in list_of_xyz if self.is_point_inside_grid(xyz)]
        return self.interpolator(list_of_xyz)


def add_dose_grids(ds1, ds2, file_path='dose_sum.dcm'):
    if type(ds1) is not pydicom.FileDataset:
        ds1 = pydicom.read_file(ds1)
    if type(ds2) is not pydicom.FileDataset:
        ds2 = pydicom.read_file(ds2)

    dose_1 = DoseGrid(ds1)
    dose_2 = DoseInterpolator(ds2)

    for zz, z in enumerate(dose_1.z_axis):
        print("%0.1f%%" % (100 * float(zz) / float(len(dose_1.z_axis))))
        points = []
        for x in dose_1.x_axis:
            for y in dose_1.y_axis:
                points.append([x, y, z])
        doses = dose_2.get_doses(points)
        for p, point in enumerate(points):
            dose_1.add_dose(point, doses[p])

    dose_1.update_pixel_array()

    return dose_1.ds
