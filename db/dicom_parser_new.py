#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# DICOM_to_Python.py
"""
Import DICOM RT Dose, Structure, and Plan files into Python objects
Created on Sun Feb 26 11:06:28 2017
@author: Dan Cutright, PhD
"""

from dicompylercore import dicomparser, dvhcalc
from dateutil.relativedelta import relativedelta  # python-dateutil
import numpy as np
import pydicom as dicom
from tools.roi_name_manager import DatabaseROIs, clean_name
from tools.utilities import datetime_str_to_obj, change_angle_origin, date_str_to_obj, calc_stats
from tools.roi_formatter import dicompyler_roi_coord_to_db_string, get_planes_from_string
from tools import roi_geometry as roi_calc
from tools.mlc_analyzer import Beam as mlca


class DICOM_Parser:
    def __init__(self, plan=None, structure=None, dose=None):

        self.rt_data = {key: None for key in ['plan', 'structure', 'dose']}
        self.dicompyler_data = {key: None for key in ['plan', 'structure', 'dose']}
        if plan:
            self.rt_data['plan'] = dicom.read_file(plan)
            self.dicompyler_data['plan'] = dicomparser.DicomParser(plan)
            self.dicompyler_rt_plan = self.dicompyler_data['plan'].GetPlan()
        if structure:
            self.rt_data['structure'] = dicom.read_file(structure)
            self.dicompyler_data['structure'] = dicomparser.DicomParser(structure)
            self.dicompyler_rt_structures = self.dicompyler_data['structure'].GetStructures()
        if dose:
            self.rt_data['dose'] = dicom.read_file(dose)
            self.dicompyler_data['dose'] = dicomparser.DicomParser(dose)

        self.database_rois = DatabaseROIs()

        self.rx_data = []
        self.beam_data = {}
        for i, fx_grp in enumerate(self.rt_data['plan'].FractionGroupSequence):
            self.rx_data.append(RxParser(self.rt_data['plan'],
                                         self.dicompyler_rt_plan,
                                         self.rt_data['structure'], i))
            self.beam_data[i] = []
            for j, beam in enumerate(self.beam_sequence):
                self.beam_data[i].append(BeamParser(self.rt_data['plan'], i, j))

    @property
    def mrn(self):
        return self.rt_data['plan'].PatientID

    @property
    def uid(self):
        return self.rt_data['plan'].StudyInstanceUID

    # ------------------------------------------------------------------------------
    # Plan table data
    # ------------------------------------------------------------------------------
    @property
    def heterogeneity_correction(self):
        if hasattr(self.rt_data['dose'], 'TissueHeterogeneityCorrection'):
            if isinstance(self.rt_data['dose'].TissueHeterogeneityCorrection, str):
                heterogeneity_correction = self.rt_data['dose'].TissueHeterogeneityCorrection
            else:
                heterogeneity_correction = ','.join(self.rt_data['dose'].TissueHeterogeneityCorrection)
        else:
            heterogeneity_correction = 'IMAGE'

        return heterogeneity_correction

    @property
    def patient_sex(self):
        return self.get_attribute('plan', 'PatientSex')

    @property
    def sim_study_date(self):
        return self.get_date('plan', 'StudyDate')

    @property
    def birth_date(self):
        return self.get_date('plan', 'PatientBirthDate')

    @property
    def age(self):
        if self.sim_study_date and self.birth_date:
            age = relativedelta(self.sim_study_date, self.birth_date).years
            if age <= 0:
                return None
            return age

    @property
    def physician(self):
        return self.get_attribute('plan', ['PhysiciansOfRecord', 'ReferringPhysicianName'])

    @property
    def fxs(self):
        try:
            fx_grp_seq = self.rt_data['plan'].FractionGroupSequence
            return [int(float(fx_grp.NumberOfFractionsPlanned)) for fx_grp in fx_grp_seq]
        except ValueError:
            return None

    @property
    def fxs_total(self):
        fxs = self.fxs
        if fxs:
            return sum(fxs)
        return None

    @property
    def patient_orientation(self):
        return ','.join(self.get_attribute('plan', 'PatientSetupSequence'))

    @property
    def plan_time_stamp(self):
        return self.get_time_stamp('plan', 'RTPlanDate', 'RTPlanTime')

    @property
    def structure_time_stamp(self):
        return self.get_time_stamp('structure', 'StructureSetDate', 'StructureSetTime')

    @property
    def dose_time_stamp(self):
        return self.get_time_stamp('dose', 'InstanceCreationDate', 'InstanceCreationTime', round_seconds=True)

    @property
    def tps_manufacturer(self):
        return self.get_attribute('plan', 'Manufacturer')

    @property
    def tps_software_name(self):
        return self.get_attribute('plan', 'ManufacturerModelName')

    @property
    def tps_software_version(self):
        return ','.join(self.get_attribute('plan', 'SoftwareVersions'))

    @property
    def tx_site(self):
        return self.get_attribute('plan', 'RTPlanLabel')

    @property
    def brachy(self):
        return hasattr(self.rt_data['plan'], 'BrachyTreatmentType')

    @property
    def brachy_type(self):
        return self.get_attribute('plan', 'BrachyTreatmentType')

    @property
    def proton(self):
        return hasattr(self.rt_data['plan'], 'IonBeamSequence')

    @property
    def beam_sequence(self):
        if hasattr(self.rt_data['plan'], 'BeamSequence'):
            return self.rt_data['plan'].BeamSequence
        elif hasattr(self.rt_data['plan'], 'IonBeamSequence'):
            return self.rt_data['plan'].IonBeamSequence
        return None

    @property
    def photon(self):
        return self.is_photon_or_electron('photon')

    @property
    def electron(self):
        return self.is_photon_or_electron('electron')

    @property
    def tx_time(self):
        if hasattr(self.rt_data['plan'], 'BrachyTreatmentType') and \
                hasattr(self.rt_data['plan'], 'ApplicationSetupSequence'):
            seconds = 0
            for app_seq in self.rt_data['plan'].ApplicationSetupSequence:
                for chan_seq in app_seq.ChannelSequence:
                    seconds += chan_seq.ChannelTotalTime
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            return "%02d:%02d:%02d" % (h, m, s)
        return '00:00:00'

    @property
    def dose_grid_resolution(self):
        try:
            dose_grid_resolution = [str(round(float(self.rt_data['dose'].PixelSpacing[0]), 1)),
                                    str(round(float(self.rt_data['dose'].PixelSpacing[1]), 1))]
            if hasattr(self.rt_data['dose'], 'SliceThickness') and self.rt_data['dose'].SliceThickness:
                dose_grid_resolution.append(str(round(float(self.rt_data['dose'].SliceThickness), 1)))
            return ', '.join(dose_grid_resolution)
        except:
            return None

    # ------------------------------------------------------------------------------
    # DVH table data
    # ------------------------------------------------------------------------------
    def get_dvh(self, key):
        dvhcalc.get_dvh(self.rt_data['structure'], self.rt_data['dose'], key)

    def get_roi_type(self, key):
        # ITV is not currently in any TPS as an ROI type.  If the ROI begins with ITV, DVH assumes
        # a ROI type of ITV
        if self.dicompyler_rt_structures[key]['name'].lower()[0:3] == 'itv':
            return 'ITV'
        else:
            return self.dicompyler_rt_structures[key]['type'].upper()

    def get_roi_name(self, key):
        return clean_name(self.dicompyler_rt_structures[key]['name'])

    def get_physician_roi(self, key):
        roi_name = self.get_roi_name(key)
        if self.database_rois.is_roi(roi_name):
            if self.database_rois.is_physician(self.physician):
                return self.database_rois.get_physician_roi(self.physician, roi_name)
        return 'uncategorized'

    def get_institutional_roi(self, key):
        roi_name = self.get_roi_name(key)
        if self.database_rois.is_roi(roi_name):
            if self.database_rois.is_physician(self.physician):
                return self.database_rois.get_institutional_roi(self.physician, self.get_physician_roi(key))
            if roi_name in self.database_rois.institutional_rois:
                return roi_name
        return 'uncategorized'

    def get_surface_area(self, key):
        coord = self.dicompyler_data['structure'].GetStructureCoordinates(key)
        try:
            return roi_calc.surface_area(coord)
        except:
            print("Surface area calculation failed for key, name: %s, %s" % (key, self.get_roi_name(key)))
            return None

    def get_dvh_geometries(self, key):
        structure_coord = self.dicompyler_data['structure'].GetStructureCoordinates(key)
        roi_coord_str = dicompyler_roi_coord_to_db_string(structure_coord)
        planes = get_planes_from_string(roi_coord_str)
        coord = self.dicompyler_data['structure'].GetStructureCoordinates(key)

        try:
            surface_area = roi_calc.surface_area(coord)
        except:
            print("Surface area calculation failed for key, name: %s, %s" % (key, self.get_roi_name(key)))
            surface_area = None

        centroid = roi_calc.centroid(planes)
        spread = roi_calc.spread(planes)
        cross_sections = roi_calc.cross_section(planes)

        return {'roi_coord_str': roi_coord_str,
                'surface_area': surface_area,
                'centroid': centroid,
                'spread': spread,
                'cross_sections': cross_sections}

    # ------------------------------------------------------------------------------
    # Generic tools
    # ------------------------------------------------------------------------------
    def get_attribute(self, rt_type, pydicom_attribute):
        """
        :param rt_type: plan. dose, or structure
        :type rt_type: str
        :param pydicom_attribute: attribute as specified in pydicom
        :type pydicom_attribute: str or list of str
        :return: pydicom value or None
        """
        if isinstance(pydicom_attribute, str):
            pydicom_attribute = [pydicom_attribute]

        for attribute in pydicom_attribute:
            if hasattr(self.rt_data[rt_type], attribute):
                return getattr(self.rt_data[rt_type], attribute)
        return None

    def get_date(self, rt_type, pydicom_attribute, include_time=False):
        """
        :param rt_type: plan. dose, or structure
        :type rt_type: str
        :param pydicom_attribute: attribute as specified in pydicom
        :type pydicom_attribute: str
        :param include_time: if true, include timestamp, otherwise year, month, date
        :type include_time: bool
        :return: datetime object of pydicom string
        :rtype: datetime
        """
        ans = self.get_attribute(rt_type, pydicom_attribute)
        if ans:
            try:
                if include_time:
                    return datetime_str_to_obj(ans)
                return date_str_to_obj(ans)
            except ValueError:
                print('ValueError: Could not parse %s to datetime' % ans)
            finally:
                print('Could not parse %s to datetime' % ans)
        return None

    def get_time_stamp(self, rt_type, date_attribute, time_attribute, round_seconds=False):
        date = self.get_attribute(rt_type, date_attribute)
        time = self.get_attribute(rt_type, time_attribute)
        try:
            if round_seconds:
                date = date.split('.')[0]
            return datetime_str_to_obj(date + time)
        except ValueError:
            return date_str_to_obj(date)
        finally:
            return None

    def is_photon_or_electron(self, rad_type):
        if hasattr(self.rt_data['plan'], 'BeamSequence'):
            for beam in self.rt_data['plan'].BeamSequence:
                if rad_type in beam.RadiationType:
                    return True
        return False


class BeamParser:
    def __init__(self, rt_plan, fx_grp_index, beam_index):
        self.rt_plan = rt_plan
        self.fx_grp_index = fx_grp_index
        self.fx_grp_data = rt_plan.FractionGroupSequence[fx_grp_index]
        self.beam_index = beam_index
        self.ref_beam_index = self.get_ref_beam_index()

        self.cp_seq = None
        if hasattr(rt_plan, 'BeamSequence'):
            self.beam_data = rt_plan.BeamSequence[beam_index]  # Photons and electrons
            if hasattr(self.beam_data, 'ControlPointSequence'):
                self.cp_seq = self.beam_data.ControlPointSequence
        elif hasattr(rt_plan, 'IonBeamSequence'):
            self.beam_data = rt_plan.IonBeamSequence[beam_index]  # Protons
            if hasattr(self.beam_data, 'IonControlPointSequence'):
                self.cp_seq = self.beam_data.IonControlPointSequence
        else:
            print('ERROR: BeamSequence nor IonBeamSequence found in fx_grp_number %s, beam_index %s' %
                  (fx_grp_index, beam_index))
            self.beam_data = None

        self.ref_beam_data = self.fx_grp_data.ReferencedBeamSequence[self.ref_beam_index]

    @property
    def beam_number(self):
        return self.beam_data.BeamNumber

    def get_ref_beam_index(self):
        ref_beam_seq = self.rt_plan.FractionGroupSequence[self.fx_grp_index].ReferencedBeamSequence
        for i, ref_beam in enumerate(ref_beam_seq):
            if ref_beam.ReferencedBeamNumber == self.beam_number:
                return i
        print('ERROR: Failed to find a matching reference beam in '
              'ReferencedBeamSequence for beam number %s' % self.beam_number)
        print('WARNING: Assuming reference beam index is equal to beam number may lead to incorrect'
              ' MUs and beam doses reported in SQL database.  Please verify')
        return self.beam_number

    @property
    def treatment_machine(self):
        return self.get_data_attribute(self.beam_data, 'TreatmentMachineName')

    @property
    def beam_dose(self):
        return self.get_data_attribute(self.ref_beam_data, 'BeamDose', default=0., data_type='float')

    @property
    def beam_mu(self):
        return self.get_data_attribute(self.ref_beam_data, 'BeamMeterset', default=0., data_type='float')

    @property
    def beam_dose_pt(self):
        return self.get_point_attribute(self.ref_beam_data, 'BeamDoseSpecificationPoint')

    @property
    def isocenter(self):
        return self.get_point_attribute(self.cp_seq[0], 'IsocenterPosition')

    @property
    def beam_type(self):
        return self.get_data_attribute(self.beam_data, 'BeamType')

    @property
    def scan_mode(self):
        return self.get_data_attribute(self.beam_data, 'ScanMode')

    @property
    def scan_spot_count(self):
        if hasattr(self.cp_seq[0], 'NumberOfScanSpotPositions'):
            return sum([int(cp.NumberOfScanSpotPositions) for cp in self.cp_seq]) / 2
        return None

    @property
    def energies(self):
        return self.get_cp_attributes('NominalBeamEnergy')

    @property
    def gantry_angles(self):
        return self.get_cp_attributes('GantryAngle')

    @property
    def collimator_angles(self):
        return self.get_cp_attributes('BeamLimitingDeviceAngle')

    @property
    def couch_angles(self):
        return self.get_cp_attributes('PatientSupportAngle')

    @property
    def gantry_rot_dirs(self):
        return self.get_cp_attributes('GantryRotationDirection')

    @property
    def collimator_rot_dirs(self):
        return self.get_cp_attributes('BeamLimitingDeviceRotationDirection')

    @property
    def couch_rot_dirs(self):
        return self.get_cp_attributes('PatientSupportRotationDirection')

    @staticmethod
    def get_rotation_direction(rotation_list):
        if len(set(rotation_list)) == 1:  # Only one direction found
            return rotation_list[0]
        return ['CC/CW', 'CW/CC'][rotation_list[0] == 'CW']

    @property
    def gantry_values(self):
        return self.get_angle_values('gantry')

    @property
    def collimator_values(self):
        return self.get_angle_values('collimator')

    @property
    def couch_values(self):
        return self.get_angle_values('couch')

    def get_angle_values(self, angle_type):
        angles = getattr(self, '%s_angle' % angle_type)
        return {'start': angles[0],
                'end': angles[-1],
                'rot_dir': self.get_rotation_direction(getattr(self, '%s_rot_dirs' % angle_type)),
                'range': round(float(np.sum(np.abs(np.diff(angles)))), 1),
                'min': min(angles),
                'max': max(angles)}

    @property
    def control_point_count(self):
        return self.get_data_attribute(self.beam_data, 'NumberOfControlPoints')

    @property
    def ssd(self):
        ssds = self.get_cp_attributes('SourceToSurfaceDistance')
        if ssds:
            return round(float(np.average(ssds))/10., 2)
        return None

    @property
    def beam_mu_per_deg(self):
        try:
            return round(self.beam_mu / self.gantry_values['range'], 2)
        except:
            return None

    @property
    def mlc_stat_data(self):
        mlc_keys = ['area', 'x_perim', 'y_perim', 'cmp_score', 'cp_mu']
        try:
            mlc_summary_data = mlca(self.beam_data, self.beam_mu, ignore_zero_mu_cp=True).summary
            mlca_stat_data = {key: calc_stats(mlc_summary_data[key]) for key in mlc_keys}
            mlca_stat_data['complexity'] = np.sum(mlc_summary_data['cmp_score'])
        except:
            mlca_stat_data = {key: ['NULL'] * 6 for key in mlc_keys}
            mlca_stat_data['complexity'] = None
        return mlca_stat_data

    @staticmethod
    def get_data_attribute(data_obj, pydicom_attr, default=None, data_type=None):
        if hasattr(data_obj, pydicom_attr):
            value = getattr(data_obj, pydicom_attr)
            if data_type == 'float':
                return float(value)
            elif data_type == 'int':
                return int(float(value))
            return value
        return default

    def get_point_attribute(self, data_obj, pydicom_attr):
        point = self.get_data_attribute(data_obj, pydicom_attr)
        if point:
            return ','.join([str(round(dim_value, 2)) for dim_value in point])
        return None

    def get_cp_attributes(self, pydicom_attr):
        values = []
        for cp in self.cp_seq:
            if hasattr(cp, pydicom_attr):
                if 'Rotation' in pydicom_attr:
                    if getattr(cp, pydicom_attr).upper() in {'CC', 'CW'}:
                        values.append(getattr(cp, pydicom_attr).upper())
                else:
                    values.append(getattr(cp, pydicom_attr))
        if pydicom_attr[-5:] == 'Angle':
            values = change_angle_origin(values, 180)
        return values


class RxParser:
    def __init__(self, rt_plan, dicompyler_plan, rt_structure, fx_grp_index):
        self.rt_plan = rt_plan
        self.dicompyler_plan = dicompyler_plan
        self.rt_structure = rt_structure
        self.fx_grp_data = rt_plan.FractionGroupSequence[fx_grp_index]
        self.dose_ref_index = self.get_dose_ref_seq_index()

    @property
    def fx_grp_number(self):
        return self.fx_grp_data.FractionGroupNumber

    @property
    def has_dose_ref(self):
        return hasattr(self.rt_plan, 'DoseReferenceSequence')

    def get_dose_ref_seq_index(self):
        for i, dose_ref in enumerate(self.rt_plan.DoseReferenceSequence):
            if dose_ref.DoseReferenceNumber == self.fx_grp_number:
                return i
        print('WARNING: DoseReference not found, verification of rx dose attributes recommended')
        return None

    @property
    def rx_dose(self):
        ans = self.get_dose_ref_attr('TargetPrescriptionDose')
        if ans is None:
            ans = float(self.dicompyler_plan['rxdose']) / 100.
        return ans

    @property
    def fx_count(self):
        return self.fx_grp_data.NumberOfFractionsPlanned

    @property
    def fx_dose(self):
        try:
            return round(self.rx_dose / float(self.fx_count), 2)
        except:
            print('WARNING: Unable to calculate fx_dose')
            return None

    @property
    def normalization_method(self):
        return self.get_dose_ref_attr('DoseReferenceStructureType')

    def get_dose_ref_attr(self, pydicom_attr):
        if self.has_dose_ref and self.dose_ref_index is not None:
            dose_ref_data = self.rt_plan.DoseReferenceSequence[self.dose_ref_index]
            if hasattr(dose_ref_data, pydicom_attr):
                return getattr(dose_ref_data, pydicom_attr)
        return None

    @property
    def normalization_object(self):
        if self.normalization_method:
            if self.normalization_method.lower() == 'coordinates':
                return 'COORDINATE'
            elif self.normalization_method.lower() == 'site':
                if hasattr(self.rt_plan, 'ManufacturerModelName'):
                    return self.rt_plan.ManufacturerModelName
        return None

    @property
    def beam_count(self):
        if hasattr(self.fx_grp_data, 'NumberOfBeams'):
            return self.fx_grp_data.NumberOfBeams
        return None
