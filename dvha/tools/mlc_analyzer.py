#!/usr/bin/env python
# -*- coding: utf-8 -*-

# tools.mlc_analyzer.py
"""
Tools for analyzing beam and control point information from DICOM files
Hierarchy of classes:
    Plan -> FxGroup -> Beam -> ControlPoint
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

from dicompylercore import dicomparser
import numpy as np
from shapely.geometry import Polygon
from shapely import speedups
from dvha.tools.utilities import flatten_list_of_lists as flatten
from dvha.options import Options


options = Options()

# Enable shapely calculations using C, as opposed to the C++ default
if speedups.available:
    speedups.enable()


class Plan:
    """
    Collect plan information from an RT Plan DICOM file.
    Automatically parses fraction data with FxGroup class
    """
    def __init__(self, rt_plan_file):
        """
        :param rt_plan_file: absolute file path of a DICOM RT Plan file
        """
        rt_plan = dicomparser.read_file(rt_plan_file)

        beam_seq = rt_plan.BeamSequence
        fx_grp_seq = rt_plan.FractionGroupSequence
        self.fx_group = [FxGroup(fx_grp, beam_seq) for fx_grp in fx_grp_seq]

        self.plan_name = rt_plan.RTPlanLabel
        self.patient_name = rt_plan.PatientName
        self.patient_id = rt_plan.PatientID
        self.study_instance_uid = rt_plan.StudyInstanceUID
        self.tps = '%s %s' % (rt_plan.Manufacturer, rt_plan.ManufacturerModelName)

    def __str__(self):
        summary = ['Patient Name:       %s' % self.patient_name,
                   'Patient MRN:        %s' % self.patient_id,
                   'Study Instance UID: %s' % self.study_instance_uid,
                   'TPS:                %s' % self.tps,
                   'Plan name:          %s' % self.plan_name,
                   '# of Fx Groups:     %s' % len(self.fx_group)]
        return '\n'.join(summary)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        for i, fx_group in enumerate(self.fx_group):
            if not fx_group == other.fx_group[i]:
                return False
        return True


class FxGroup:
    """
    Collect fraction group information from fraction group and beam sequences of a pydicom RT Plan dataset
    Automatically parses beam data with Beam class
    """
    def __init__(self, fx_grp_seq, plan_beam_sequences):
        """
        :param fx_grp_seq: fraction group sequence object
        :type fx_grp_seq: Sequence
        :param plan_beam_sequences: beam sequence object
        :type plan_beam_sequences: Sequence
        """
        self.fxs = fx_grp_seq.NumberOfFractionsPlanned

        meter_set = {}
        for ref_beam in fx_grp_seq.ReferencedBeamSequence:
            ref_beam_num = str(ref_beam.ReferencedBeamNumber)
            meter_set[ref_beam_num] = float(ref_beam.BeamMeterset)

        self.beam = []
        for beam_seq in plan_beam_sequences:
            beam_num = str(beam_seq.BeamNumber)
            if beam_num in meter_set:
                self.beam.append(Beam(beam_seq, meter_set[beam_num]))
        self.beam_count = len(self.beam)
        self.beam_names = [b.name for b in self.beam]

        self.beam = update_missing_jaws(self.beam)

    def __eq__(self, other):
        for i, beam in enumerate(self.beam):
            status_str = 'beam %s\n\t%%s with other beam %s' % (self.beam_names[i], other.beam_names[i])
            if not beam == other.beam[i]:
                print(status_str % 'failed')
                return False
            else:
                print(status_str % 'passed')
        return True


class Beam:
    """
    Collect beam information from a beam in a beam sequence of a pydicom RT Plan dataset
    Automatically parses control point data with ControlPoint class
    """
    def __init__(self, beam_dataset, meter_set, ignore_zero_mu_cp=False):
        """
        :param beam_dataset: a pydicom beam sequence object
        :type beam_dataset: Dataset
        :param meter_set: the monitor units for the beam_dataset
        :type meter_set: float
        :param ignore_zero_mu_cp: If True, skip over zero MU control points (e.g., as in Step-N-Shoot beams)
        :type ignore_zero_mu_cp: bool
        """

        cp_seq = beam_dataset.ControlPointSequence
        self.control_point = [ControlPoint(cp) for cp in cp_seq]
        self.control_point_count = len(self.control_point)

        for bld_seq in beam_dataset.BeamLimitingDeviceSequence:
            if hasattr(bld_seq, 'LeafPositionBoundaries'):
                self.leaf_boundaries = bld_seq.LeafPositionBoundaries

        self.jaws = [get_jaws(cp) for cp in self.control_point]
        self.aperture = [get_shapely_from_cp(cp, self.leaf_boundaries) for cp in self.control_point]
        self.mlc_borders = [get_mlc_borders(cp, self.leaf_boundaries) for cp in self.control_point]

        self.gantry_angle = [float(cp.GantryAngle) for cp in cp_seq if hasattr(cp, 'GantryAngle')]
        self.collimator_angle = [float(cp.BeamLimitingDeviceAngle) for cp in cp_seq if hasattr(cp, 'BeamLimitingDeviceAngle')]
        self.couch_angle = [float(cp.PatientSupportAngle) for cp in cp_seq if hasattr(cp, 'PatientSupportAngle')]

        self.meter_set = meter_set
        self.control_point_meter_set = np.append([0], np.diff(np.array([cp.cum_mu for cp in self.control_point])))

        if hasattr(beam_dataset, 'BeamDescription'):
            self.name = beam_dataset.BeamDescription
        else:
            self.name = beam_dataset.BeamName

        cum_mu = [cp.cum_mu * self.meter_set for cp in self.control_point]
        cp_mu = np.diff(np.array(cum_mu)).tolist() + [0]
        x_paths = np.array([get_xy_path_lengths(cp)[0] for cp in self.aperture])
        y_paths = np.array([get_xy_path_lengths(cp)[1] for cp in self.aperture])
        area = [cp.area for cp in self.aperture]
        c1, c2 = options.COMPLEXITY_SCORE_X_WEIGHT, options.COMPLEXITY_SCORE_Y_WEIGHT
        complexity_scores = np.divide(np.multiply(np.add(c1*x_paths, c2*y_paths), cp_mu), area) / self.meter_set
        # Complexity score based on:
        # Younge KC, Matuszak MM, Moran JM, McShan DL, Fraass BA, Roberts DA. Penalization of aperture
        # complexity in inversely planned volumetric modulated arc therapy. Med Phys. 2012;39(11):7160–70.

        self.summary = {'cp': range(1, len(self.control_point)+1),
                        'cum_mu_frac': [cp.cum_mu for cp in self.control_point],
                        'cum_mu': cum_mu,
                        'cp_mu': cp_mu,
                        'gantry': self.gantry_angle,
                        'collimator': self.collimator_angle,
                        'couch': self.couch_angle,
                        'jaw_x1': [j['x_min']/10 for j in self.jaws],
                        'jaw_x2': [j['x_max']/10 for j in self.jaws],
                        'jaw_y1': [j['y_min']/10 for j in self.jaws],
                        'jaw_y2': [j['y_max']/10 for j in self.jaws],
                        'area': np.divide(area, 100.).tolist(),
                        'x_perim': np.divide(x_paths, 10.).tolist(),
                        'y_perim': np.divide(y_paths, 10.).tolist(),
                        'perim': np.divide(np.add(x_paths, y_paths), 10.).tolist(),
                        'cmp_score': complexity_scores.tolist()}

        for key in self.summary:
            if len(self.summary[key]) == 1:
                self.summary[key] = self.summary[key] * len(self.summary['cp'])

        if ignore_zero_mu_cp:
            non_zero_indices = [i for i, value in enumerate(self.summary['cp_mu']) if value != 0]
            for key in list(self.summary):
                self.summary[key] = [self.summary[key][i] for i in non_zero_indices]

    def __eq__(self, other):
        for i, cp in enumerate(self.control_point):
            if not cp == other.control_point[i]:
                print('cp %s failed' % i)
                return False
        return True


class ControlPoint:
    """
    Collect control point information from a ControlPointSequence in a beam dataset of a pydicom RT Plan dataset
    """
    def __init__(self, cp_seq):
        """
        :param cp_seq: control point sequence object
        :type cp_seq: Sequence
        """
        cp = {'cum_mu': float(cp_seq.CumulativeMetersetWeight)}
        for device_position_seq in cp_seq.BeamLimitingDevicePositionSequence:
            leaf_jaw_type = str(device_position_seq.RTBeamLimitingDeviceType).lower()
            if leaf_jaw_type.startswith('mlc'):
                cp['leaf_type'] = leaf_jaw_type
                leaf_jaw_type = 'mlc'

            positions = np.array(list(map(float, device_position_seq.LeafJawPositions)))
            mid_index = int(len(positions) / 2)
            cp[leaf_jaw_type] = [positions[:mid_index],
                                 positions[mid_index:]]

        if 'leaf_type' not in list(cp):
            cp['leaf_type'] = False

        for key in cp:
            setattr(self, key, cp[key])

    def __eq__(self, other):
        if abs(self.cum_mu - other.cum_mu) > 0.00001:
            return False
        for side in [0, 1]:
            for i, pos in enumerate(self.mlc[side]):
                if abs(pos - other.mlc[side][i]) > 0.0001:
                    print(abs(pos - other.mlc[side][i]))
        return True


def get_mlc_borders(control_point, leaf_boundaries):
    """
    This function returns the boundaries of each MLC leaf for purposes of displaying a beam's eye view using
    bokeh's quad() glyph
    :param control_point: a ControlPoint from a pydicom ControlPoint Sequence
    :type control_point: Dataset
    :param leaf_boundaries: a LeafPositionBoundaries object from the BeamLimitingDeviceSequence
    :type leaf_boundaries: MultiValue
    :return: the boundaries of each leaf within the control point
    :rtype: dict
    """
    top = leaf_boundaries[0:-1] + leaf_boundaries[0:-1]
    top = [float(i) for i in top]
    bottom = leaf_boundaries[1::] + leaf_boundaries[1::]
    bottom = [float(i) for i in bottom]
    left = [- options.MAX_FIELD_SIZE_X / 2] * len(control_point.mlc[0])
    left.extend(control_point.mlc[1])
    right = control_point.mlc[0].tolist()
    right.extend([options.MAX_FIELD_SIZE_X / 2] * len(control_point.mlc[1]))

    return {'top': top,
            'bottom': bottom,
            'left': left,
            'right': right}


def get_shapely_from_cp(control_point, leaf_boundaries):
    """
    This function will return the outline of MLCs within jaws
    :param control_point: a ControlPoint from a pydicom ControlPoint Sequence
    :type control_point: Dataset
    :param leaf_boundaries: a LeafPositionBoundaries object from the BeamLimitingDeviceSequence
    :type leaf_boundaries: MultiValue
    :return: a shapely object of the complete MLC aperture as one shape (including MLC overlap)
    :rtype: Polygon
    """
    lb = leaf_boundaries
    mlc = control_point.mlc
    jaws = get_jaws(control_point)
    x_min, x_max = jaws['x_min'], jaws['x_max']
    y_min, y_max = jaws['y_min'], jaws['y_max']

    jaw_points = [(x_min, y_min), (x_min, y_max), (x_max, y_max), (x_max, y_min)]
    jaw_shapely = Polygon(jaw_points)

    if control_point.leaf_type == 'mlcx':
        a = flatten([[(m, lb[i]), (m, lb[i+1])] for i, m in enumerate(mlc[0])])
        b = flatten([[(m, lb[i]), (m, lb[i+1])] for i, m in enumerate(mlc[1])])
    elif control_point.leaf_type == 'mlcy':
        a = flatten([[(lb[i], m), (lb[i + 1], m)] for i, m in enumerate(mlc[0])])
        b = flatten([[(lb[i], m), (lb[i + 1], m)] for i, m in enumerate(mlc[1])])
    else:
        return jaw_shapely

    mlc_points = a + b[::-1]  # concatenate a and reverse(b)
    mlc_aperture = Polygon(mlc_points).buffer(0)

    # This function is very slow, since jaws are rectangular, perhaps there's a more efficient method?
    aperture = mlc_aperture.intersection(jaw_shapely)

    return aperture


def get_jaws(control_point):
    """
    Get the jaw positions of a control point
    :param control_point: a ControlPoint from a pydicom ControlPoint Sequence
    :type control_point: Dataset
    :return: jaw positions (or max field size in lieu of a jaw)
    :rtype: dict
    """

    cp = control_point

    # Determine jaw opening
    if hasattr(cp, 'asymy'):
        y_min = min(cp.asymy)
        y_max = max(cp.asymy)
    else:
        y_min = -options.MAX_FIELD_SIZE_Y / 2.
        y_max = options.MAX_FIELD_SIZE_Y / 2.
    if hasattr(cp, 'asymx'):
        x_min = min(cp.asymx)
        x_max = max(cp.asymx)
    else:
        x_min = -options.MAX_FIELD_SIZE_X / 2.
        x_max = options.MAX_FIELD_SIZE_X / 2.

    jaws = {'x_min': float(x_min),
            'x_max': float(x_max),
            'y_min': float(y_min),
            'y_max': float(y_max)}

    return jaws


def get_xy_path_lengths(shapely_object):
    """
    Get the x and y path lengths of a a Shapely object
    :param shapely_object: either 'GeometryCollection', 'MultiPolygon', or 'Polygon'
    :return: path lengths in the x and y directions
    :rtype: list
    """
    path = np.array([0., 0.])
    if shapely_object.type == 'GeometryCollection':
        for geometry in shapely_object.geoms:
            if geometry.type in {'MultiPolygon', 'Polygon'}:
                path = np.add(path, get_xy_path_lengths(geometry))
    elif shapely_object.type == 'MultiPolygon':
        for shape in shapely_object:
            path = np.add(path, get_xy_path_lengths(shape))
    elif shapely_object.type == 'Polygon':
        x, y = np.array(shapely_object.exterior.xy[0]), np.array(shapely_object.exterior.xy[1])
        path = np.array([np.sum(np.abs(np.diff(x))), np.sum(np.abs(np.diff(y)))])

    return path.tolist()


def update_missing_jaws(beam_list):
    """
    In plans with static jaws throughout the beam, jaw positions may not be found in each control point
    :param beam_list: a list of Beam Class objects
    :return: a list of Beam Class objects, but any control point where jaws are set to max will be replaced by the
    first control point jaw settings
    :rtype: list
    """

    for i, beam in enumerate(beam_list):
        for j, cp in enumerate(beam.jaws):
            if cp['x_min'] == -options.MAX_FIELD_SIZE_X / 2 and \
                            cp['x_max'] == options.MAX_FIELD_SIZE_X / 2 and \
                            cp['y_min'] == -options.MAX_FIELD_SIZE_Y / 2 and \
                            cp['y_max'] == options.MAX_FIELD_SIZE_Y / 2:
                beam_list[i].jaws[j] = beam.jaws[0]

    return beam_list
