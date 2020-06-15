#!/usr/bin/env python
# -*- coding: utf-8 -*-

# tools.utilities.mlc_analyzer.py
"""
Tools for analyzing beam and control point information from DICOM files
Hierarchy of classes:
    Plan -> FxGroup -> Beam -> ControlPoint
"""
# Copyright (c) 2016-2020 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import pydicom
import numpy as np
from shapely.geometry import Polygon
from shapely import speedups
from dvha.tools.utilities import flatten_list_of_lists as flatten, get_xy_path_lengths


DEFAULT_OPTIONS = {'max_field_size_x': 400.,
                   'max_field_size_y': 400.,
                   'complexity_weight_x': 1.,
                   'complexity_weight_y': 1.}

COLUMNS = ['Patient Name', 'Patient MRN', 'Study Instance UID', 'TPS', 'Plan name', '# of Fx Group(s)', 'Fx Group #',
           'Fractions', 'Plan MUs', 'Beam Count(s)', 'Control Point(s)', 'Complexity Score(s)', 'File Name']


def get_options(over_rides):
    options = {k: v for k, v in DEFAULT_OPTIONS.items()}
    for key, value in over_rides.items():
        if key in list(options):
            options[key] = value
    return options


# Enable shapely calculations using C, as opposed to the C++ default
if speedups.available:
    speedups.enable()


class Plan:
    """
    Collect plan information from an RT Plan DICOM file.
    Automatically parses fraction data with FxGroup class
    """
    def __init__(self, rt_plan_file, **kwargs):
        """
        :param rt_plan_file: absolute file path of a DICOM RT Plan file
        """
        self.rt_plan_file = rt_plan_file
        rt_plan = pydicom.read_file(rt_plan_file)

        self.options = get_options(kwargs)

        beam_seq = rt_plan.BeamSequence
        fx_grp_seq = rt_plan.FractionGroupSequence
        self.fx_group = [FxGroup(fx_grp, beam_seq) for fx_grp in fx_grp_seq]

        self.plan_name = '"%s"' % rt_plan.RTPlanLabel
        self.patient_name = '"%s"' % rt_plan.PatientName
        self.patient_id = '"%s"' % rt_plan.PatientID
        self.study_instance_uid = '"%s"' % rt_plan.StudyInstanceUID
        self.tps = '"%s %s"' % (rt_plan.Manufacturer, rt_plan.ManufacturerModelName)

        self.complexity_scores = [float(fx_grp.complexity_score) for fx_grp in self.fx_group]

        self.summary = [{'Patient Name': self.patient_name,
                         'Patient MRN': self.patient_id,
                         'Study Instance UID': self.study_instance_uid,
                         'TPS': self.tps,
                         'Plan name': self.plan_name,
                         '# of Fx Group(s)': str(len(self.fx_group)),
                         'Fx Group #': str(f+1),
                         'Fractions': str(fx_grp.fxs),
                         'Plan MUs': "%0.1f" % fx_grp.fx_mu,
                         'Beam Count(s)': str(fx_grp.beam_count),
                         'Control Point(s)': str(sum(fx_grp.cp_counts)),
                         'Complexity Score(s)': "%0.3f" % self.complexity_scores[f],
                         'File Name': '"%s"' % self.rt_plan_file}
                        for f, fx_grp in enumerate(self.fx_group)]

    def __str__(self):
        summary = ['Patient Name:        %s' % self.patient_name,
                   'Patient MRN:         %s' % self.patient_id,
                   'Study Instance UID:  %s' % self.study_instance_uid,
                   'TPS:                 %s' % self.tps,
                   'Plan name:           %s' % self.plan_name,
                   '# of Fx Group(s):    %s' % len(self.fx_group),
                   'Plan MUs:            %s' % ', '.join(["%0.1f" % fx_grp.fx_mu for fx_grp in self.fx_group]),
                   'Beam Count(s):       %s' % ', '.join([str(fx_grp.beam_count) for fx_grp in self.fx_group]),
                   'Control Point(s):    %s' % ', '.join([str(sum(fx_grp.cp_counts)) for fx_grp in self.fx_group]),
                   'Complexity Score(s): %s' % ', '.join(["%0.3f" % cs for cs in self.complexity_scores])]
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
    def __init__(self, fx_grp_seq, plan_beam_sequences, **kwargs):
        """
        :param fx_grp_seq: fraction group sequence object
        :type fx_grp_seq: Sequence
        :param plan_beam_sequences: beam sequence object
        :type plan_beam_sequences: Sequence
        """
        self.fxs = getattr(fx_grp_seq, 'NumberOfFractionsPlanned', 'UNKNOWN')

        self.options = get_options(kwargs)

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
        self.beam_mu = [b.meter_set for b in self.beam]
        self.fx_mu = np.sum(self.beam_mu)
        self.cp_counts = [b.control_point_count for b in self.beam]

        self.update_missing_jaws()

        self.complexity_score = np.sum(np.array([np.sum(beam.complexity_scores) for beam in self.beam]))

    def __eq__(self, other):
        for i, beam in enumerate(self.beam):
            status_str = 'beam %s\n\t%%s with other beam %s' % (self.beam_names[i], other.beam_names[i])
            if not beam == other.beam[i]:
                print(status_str % 'failed')
                return False
            else:
                print(status_str % 'passed')
        return True

    def update_missing_jaws(self):
        """In plans with static jaws throughout the beam, jaw positions may not be found in each control point"""
        for i, beam in enumerate(self.beam):
            for j, cp in enumerate(beam.jaws):
                if cp['x_min'] == -self.options['max_field_size_x'] / 2 and \
                        cp['x_max'] == self.options['max_field_size_x'] / 2 and \
                        cp['y_min'] == -self.options['max_field_size_y'] / 2 and \
                        cp['y_max'] == self.options['max_field_size_y'] / 2:
                    beam.jaws[j] = beam.jaws[0]


class Beam:
    """
    Collect beam information from a beam in a beam sequence of a pydicom RT Plan dataset
    Automatically parses control point data with ControlPoint class
    """
    def __init__(self, beam_dataset, meter_set, ignore_zero_mu_cp=False, **kwargs):
        """
        :param beam_dataset: a pydicom beam sequence object
        :type beam_dataset: Dataset
        :param meter_set: the monitor units for the beam_dataset
        :type meter_set: float
        :param ignore_zero_mu_cp: If True, skip over zero MU control points (e.g., as in Step-N-Shoot beams)
        :type ignore_zero_mu_cp: bool
        """

        self.options = get_options(kwargs)

        self.cp_seq = beam_dataset.ControlPointSequence

        for bld_seq in beam_dataset.BeamLimitingDeviceSequence:
            if hasattr(bld_seq, 'LeafPositionBoundaries'):
                self.leaf_boundaries = bld_seq.LeafPositionBoundaries

        self.control_point = [ControlPoint(cp, self.leaf_boundaries) for cp in self.cp_seq]
        self.control_point_count = len(self.control_point)

        self.jaws = [cp.jaws for cp in self.control_point]
        self.aperture = [cp.aperture for cp in self.control_point]

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
        c1, c2 = self.options['complexity_weight_x'], self.options['complexity_weight_y']
        self.complexity_scores = np.divide(np.multiply(np.add(c1*x_paths, c2*y_paths), cp_mu), area) / self.meter_set
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
                        'cmp_score': self.complexity_scores.tolist()}

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

    @property
    def mlc_borders(self):
        return [cp.mlc_borders for cp in self.control_point]

    @property
    def gantry_angle(self):
        return [float(cp.GantryAngle) for cp in self.cp_seq if hasattr(cp, 'GantryAngle')]

    @property
    def collimator_angle(self):
        return [float(cp.BeamLimitingDeviceAngle) for cp in self.cp_seq if hasattr(cp, 'BeamLimitingDeviceAngle')]

    @property
    def couch_angle(self):
        return [float(cp.PatientSupportAngle) for cp in self.cp_seq if hasattr(cp, 'PatientSupportAngle')]


class ControlPoint:
    """
    Collect control point information from a ControlPointSequence in a beam dataset of a pydicom RT Plan dataset
    """
    def __init__(self, cp_seq, leaf_boundaries, **kwargs):
        """
        :param cp_seq: control point sequence object
        :type cp_seq: Sequence
        """

        self.leaf_boundaries = leaf_boundaries
        self.options = get_options(kwargs)

        self.cum_mu = float(cp_seq.CumulativeMetersetWeight)

        if hasattr(cp_seq, 'BeamLimitingDevicePositionSequence'):
            for device_position_seq in cp_seq.BeamLimitingDevicePositionSequence:
                if hasattr(device_position_seq, 'RTBeamLimitingDeviceType') and \
                        hasattr(device_position_seq, 'LeafJawPositions'):
                    leaf_jaw_type = str(device_position_seq.RTBeamLimitingDeviceType).lower()
                    positions = np.array(list(map(float, device_position_seq.LeafJawPositions)))
                    mid_index = int(len(positions) / 2)
                    setattr(self, leaf_jaw_type, [positions[:mid_index],
                                                  positions[mid_index:]])

        self.mlc = None
        self.leaf_type = False
        for leaf_type in ['mlcx', 'mlcy']:
            if getattr(self, leaf_type, None) is not None:
                self.mlc = getattr(self, leaf_type)
                self.leaf_type = leaf_type

    def __eq__(self, other):
        if abs(self.cum_mu - other.cum_mu) > 0.00001:
            return False
        for side in [0, 1]:
            for i, pos in enumerate(self.mlc[side]):
                if abs(pos - other.mlc[side][i]) > 0.0001:
                    print(abs(pos - other.mlc[side][i]))
        return True

    @property
    def mlc_borders(self):
        """
        This function returns the boundaries of each MLC leaf for purposes of displaying a beam's eye view using
        bokeh's quad() glyph
        :return: the boundaries of each leaf within the control point
        :rtype: dict
        """
        if self.mlc is not None:
            top = self.leaf_boundaries[0:-1] + self.leaf_boundaries[0:-1]
            top = [float(i) for i in top]
            bottom = self.leaf_boundaries[1::] + self.leaf_boundaries[1::]
            bottom = [float(i) for i in bottom]
            left = [- self.options['max_field_size_x'] / 2] * len(self.mlc[0])
            left.extend(self.mlc[1])
            right = self.mlc[0].tolist()
            right.extend([self.options['max_field_size_x'] / 2] * len(self.mlc[1]))

            return {'top': top,
                    'bottom': bottom,
                    'left': left,
                    'right': right}

    @property
    def aperture(self):
        """
        This function will return the outline of MLCs within jaws
        :return: a shapely object of the complete MLC aperture as one shape (including MLC overlap)
        :rtype: Polygon
        """
        lb = self.leaf_boundaries
        mlc = self.mlc

        jaws = self.jaws
        jaw_points = [(jaws['x_min'], jaws['y_min']),
                      (jaws['x_min'], jaws['y_max']),
                      (jaws['x_max'], jaws['y_max']),
                      (jaws['x_max'], jaws['y_min'])]
        jaw_shapely = Polygon(jaw_points)

        if self.leaf_type == 'mlcx':
            a = flatten([[(m, lb[i]), (m, lb[i + 1])] for i, m in enumerate(mlc[0])])
            b = flatten([[(m, lb[i]), (m, lb[i + 1])] for i, m in enumerate(mlc[1])])
        elif self.leaf_type == 'mlcy':
            a = flatten([[(lb[i], m), (lb[i + 1], m)] for i, m in enumerate(mlc[0])])
            b = flatten([[(lb[i], m), (lb[i + 1], m)] for i, m in enumerate(mlc[1])])
        else:
            return jaw_shapely

        mlc_points = a + b[::-1]  # concatenate a and reverse(b)
        mlc_aperture = Polygon(mlc_points).buffer(0)

        # This function is very slow, since jaws are rectangular, perhaps there's a more efficient method?
        aperture = mlc_aperture.intersection(jaw_shapely)

        return aperture

    @property
    def jaws(self):
        """
        Get the jaw positions of a control point
        :return: jaw positions (or max field size in lieu of a jaw)
        :rtype: dict
        """

        jaws = {}

        for dim in ['x', 'y']:
            half = self.options['max_field_size_%s' % dim] / 2.
            values = getattr(self, 'asym%s' % dim, [-half, half])
            jaws['%s_min' % dim] = min(values)
            jaws['%s_max' % dim] = max(values)

        return jaws
