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


class DVHRow:
    def __init__(self, mrn, study_instance_uid, institutional_roi, physician_roi, roi_name, roi_type, volume,
                 min_dose, mean_dose, max_dose, dvh_str, roi_coord, surface_area, centroid, spread_x, spread_y,
                 spread_z, cross_section_max, cross_section_median):

        for key, value in listitems(locals()):
            if key != 'self':
                setattr(self, key, value)


class BeamRow:
    def __init__(self, mrn, study_instance_uid, beam_number, beam_name,
                 fx_group, fxs, fx_grp_beam_count, beam_dose,
                 beam_mu, radiation_type, beam_energy_min, beam_energy_max, beam_type, control_point_count,
                 gantry_start, gantry_end, gantry_rot_dir,
                 gantry_range, gantry_min, gantry_max,
                 collimator_start, collimator_end, collimator_rot_dir,
                 collimator_range, collimator_min, collimator_max,
                 couch_start, couch_end, couch_rot_dir,
                 couch_range, couch_min, couch_max,
                 beam_dose_pt, isocenter, ssd, treatment_machine, scan_mode, scan_spot_count,
                 beam_mu_per_deg, beam_mu_per_cp, area_min, area_mean, area_median, area_max, x_perim_min,
                 x_perim_mean, x_perim_median, x_perim_max, y_perim_min, y_perim_mean, y_perim_median,
                 y_perim_max, complexity_min, complexity_mean, complexity_median, complexity_max, complexity, cp_mu_min,
                 cp_mu_mean, cp_mu_median, cp_mu_max):

        for key, value in listitems(locals()):
            if key != 'self':
                setattr(self, key, value)


class RxRow:
    def __init__(self, mrn, study_instance_uid, plan_name, fx_grp_name, fx_grp_number, fx_grp_count,
                 fx_dose, fxs, rx_dose, rx_percent, normalization_method, normalization_object):

        for key, value in listitems(locals()):
            if key != 'self':
                setattr(self, key, value)


# Each Plan class object contains data to fill an entire row of the SQL table 'Plans'
# There will be a Plan class per structure of a Plan
class PlanRow:
    def __init__(self, plan_file, structure_file, dose_file):
        # Read DICOM files
        rt_plan = dicom.read_file(plan_file)
        dicompyler_plan = dicomparser.DicomParser(plan_file).GetPlan()
        rt_structure = dicom.read_file(structure_file)
        rt_dose = dicom.read_file(dose_file)

        # Heterogeneity
        if hasattr(rt_dose, 'TissueHeterogeneityCorrection'):
            if isinstance(rt_dose.TissueHeterogeneityCorrection, basestring):
                heterogeneity_correction = rt_dose.TissueHeterogeneityCorrection
            else:
                heterogeneity_correction = ','.join(rt_dose.TissueHeterogeneityCorrection)
        else:
            heterogeneity_correction = 'IMAGE'

        # Record Medical Record Number
        mrn = rt_plan.PatientID

        # Record gender
        patient_sex = rt_plan.PatientSex.upper()
        if patient_sex not in {'M', 'F'}:
            patient_sex = '-'

        # Parse and record sim date
        sim_study_date = rt_plan.StudyDate
        if sim_study_date:
            sim_study_date_obj = date_str_to_obj(sim_study_date)
        else:
            sim_study_date = '(NULL)'

        # Calculate patient age at time of sim
        # Set to NULL birthday is not in DICOM file
        birth_date = rt_plan.PatientBirthDate
        if not birth_date:
            birth_date = '(NULL)'
            age = '(NULL)'
        else:
            birth_date_obj = date_str_to_obj(birth_date)
            if sim_study_date == '(NULL)':
                age = '(NULL)'
            else:
                age = relativedelta(sim_study_date_obj, birth_date_obj).years
                if age <= 0:
                    age = '(NULL)'

        # Record physician initials
        # In Pinnacle, PhysiciansOfRecord refers to the Radiation Oncologist field
        if hasattr(rt_plan, 'PhysiciansOfRecord'):
            physician = rt_plan.PhysiciansOfRecord.upper()
        elif hasattr(rt_plan, 'ReferringPhysicianName'):
            physician = rt_plan.ReferringPhysicianName.upper()
        else:
            physician = '(NULL)'

        # Initialize fx and MU counters, iterate over all rx's
        fxs = 0
        total_mu = 0
        fx_grp_seq = rt_plan.FractionGroupSequence  # just to limit characters for later reference
        # Count number of fxs and total MUs
        # Note these are total fxs, not treatment days
        for fx_grp in fx_grp_seq:
            fxs += int(float(fx_grp.NumberOfFractionsPlanned))
            fx_mu = 0
            for Beam in range(fx_grp.NumberOfBeams):
                if hasattr(fx_grp.ReferencedBeamSequence[Beam], 'BeamMeterset'):
                    fx_mu += float(fx_grp.ReferencedBeamSequence[Beam].BeamMeterset)
            total_mu += int(float(fx_grp.NumberOfFractionsPlanned)) * fx_mu
        total_mu = round(total_mu, 1)

        # This UID must be in all DICOM files associated with this sim study
        study_instance_uid = rt_plan.StudyInstanceUID

        # Record patient position (e.g., HFS, HFP, FFS, or FFP)
        if hasattr(rt_plan, 'PatientSetupSequence'):
            patient_orientation = rt_plan.PatientSetupSequence[0].PatientPosition
        else:
            patient_orientation = 'UKN'

        # Context self-evident, their utility is not (yet)
        try:
            plan_time_stamp = datetime_str_to_obj(rt_plan.RTPlanDate + rt_plan.RTPlanTime)
        except:
            plan_time_stamp = '(NULL)'
        try:
            struct_time_stamp = datetime_str_to_obj(rt_structure.StructureSetDate + rt_structure.StructureSetTime)
        except:
            struct_time_stamp = '(NULL)'

        if hasattr(rt_dose, 'InstanceCreationDate'):
            dose_time_stamp = datetime_str_to_obj(rt_dose.InstanceCreationDate +
                                                  rt_dose.InstanceCreationTime.split('.')[0])
        else:
            dose_time_stamp = '(NULL)'

        # Record treatment planning system vendor, name, and version
        if hasattr(rt_plan, 'Manufacturer'):
            tps_manufacturer = rt_plan.Manufacturer
        else:
            tps_manufacturer = '(NULL)'
        if hasattr(rt_plan, 'ManufacturerModelName'):
            tps_software_name = rt_plan.ManufacturerModelName
        else:
            tps_software_name = '(NULL)'
        if hasattr(rt_plan, 'SoftwareVersions'):
            tps_software_version = rt_plan.SoftwareVersions[0]
        else:
            tps_software_version = '(NULL)'

        # Because Pinnacle's DICOM does not contain Rx's explicitly, the user must create
        # a point in the RT Structure file called 'rx: '
        # If multiple Rx found, sum will be reported
        # Record tx site from 'tx:' point or RTPlanLabel if no point
        tx_site = rt_plan.RTPlanLabel  # tx_site defaults to plan name if not tx in a tx point
        tx_found = False
        rx_dose = 0
        roi_counter = 0
        roi_seq = rt_structure.StructureSetROISequence  # just limit num characters in code
        roi_count = len(roi_seq)
        fx_reset = False
        while (not tx_found) and (roi_counter < roi_count):
            roi_name = roi_seq[roi_counter].ROIName.lower()
            if len(roi_name) > 2:
                temp = roi_name.split(' ')
                if temp[0][0:2] == 'rx':
                    if not fx_reset:
                        fxs = 0
                        fx_reset = True
                    fx_dose = float(temp[temp.index('cgy')-1]) / 100.
                    fxs += int(temp[temp.index('x') + 1])
                    rx_dose += fx_dose * float((temp[temp.index('x') + 1]))
                elif temp[0] == 'tx:':
                    temp.remove('tx:')
                    tx_site = ' '.join(temp)
                    tx_found = True
            roi_counter += 1

        # if rx_dose point not found, use dose in DICOM file
        if rx_dose == 0:
            rx_dose = float(dicompyler_plan['rxdose']) / 100.

        # This assumes that Plans are either 100% Arc plans or 100% Static Angle
        # Note that the beams class will have this information on a per beam basis
        tx_modality = ''
        tx_energies = ' '
        temp = ''

        # Brachytherapy
        if dicompyler_plan['brachy']:
            if hasattr(rt_plan, 'BrachyTreatmentType'):
                tx_modality = rt_plan.BrachyTreatmentType + ' '
            else:
                tx_modality = 'Brachy '

        # Protons
        elif hasattr(rt_plan, 'IonBeamSequence'):
            beam_seq = rt_plan.IonBeamSequence
            for beam in beam_seq:
                temp += beam.RadiationType + ' '
                first_cp = beam.IonControlPointSequence[0]
                if first_cp.GantryRotationDirection in {'CW', 'CC'}:
                    temp += 'Arc '
                else:
                    temp += '3D '
                energy_str = str(round(float(first_cp.NominalBeamEnergy))).split('.')[0]
                energy_temp = ' ' + energy_str + 'MeV '
                if energy_temp not in tx_energies:
                    tx_energies += energy_temp

            tx_modality += 'Proton '

        # Photons and electrons
        elif hasattr(rt_plan, 'BeamSequence'):
            beam_seq = rt_plan.BeamSequence
            for beam in beam_seq:
                temp += beam.RadiationType + ' '
                first_cp = beam.ControlPointSequence[0]
                if first_cp.GantryRotationDirection in {'CW', 'CC'}:
                    temp += 'Arc '
                else:
                    temp += '3D '
                energy_temp = ' ' + str(first_cp.NominalBeamEnergy)
                if beam.RadiationType.lower() == 'photon':
                    energy_temp += 'MV '
                elif beam.RadiationType.lower() == 'electron':
                    energy_temp += 'MeV '
                if tx_energies.find(energy_temp) < 0:
                    tx_energies += energy_temp

            temp = temp.lower()
            if 'photon' in temp:
                if 'photon arc' in temp:
                    tx_modality += 'Photon Arc '
                else:
                    tx_modality += 'Photon 3D '
            if 'electron' in temp:
                if 'electron arc' in temp:
                    tx_modality += 'Electron Arc '
                else:
                    tx_modality += 'Electron 3D '

        tx_modality = tx_modality.strip()

        # Will require a yet to be named function to determine this
        # Applicable for brachy and Gamma Knife, not yet supported
        tx_time = '00:00:00'
        if hasattr(rt_plan, 'BrachyTreatmentType'):
            seconds = 0
            for app_seq in rt_plan.ApplicationSetupSequence:
                for chan_seq in app_seq.ChannelSequence:
                    seconds += chan_seq.ChannelTotalTime
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            tx_time = "%02d:%02d:%02d" % (h, m, s)

        # Record resolution of dose grid
        dose_grid_resolution = [str(round(float(rt_dose.PixelSpacing[0]), 1)),
                                str(round(float(rt_dose.PixelSpacing[1]), 1))]
        if hasattr(rt_dose, 'SliceThickness') and rt_dose.SliceThickness:
            dose_grid_resolution.append(str(round(float(rt_dose.SliceThickness), 1)))
        dose_grid_resolution = ', '.join(dose_grid_resolution)

        # Set object values
        self.mrn = mrn
        self.birth_date = birth_date
        self.age = age
        self.patient_sex = patient_sex
        self.sim_study_date = sim_study_date
        self.physician = physician
        self.tx_site = tx_site
        self.rx_dose = rx_dose
        self.fxs = fxs
        self.study_instance_uid = study_instance_uid
        self.patient_orientation = patient_orientation
        self.plan_time_stamp = plan_time_stamp
        self.struct_time_stamp = struct_time_stamp
        self.dose_time_stamp = dose_time_stamp
        self.tps_manufacturer = tps_manufacturer
        self.tps_software_name = tps_software_name
        self.tps_software_version = tps_software_version
        self.tx_modality = tx_modality
        self.tx_time = tx_time
        self.total_mu = total_mu
        self.dose_grid_resolution = dose_grid_resolution
        self.heterogeneity_correction = heterogeneity_correction


class DVHTable:
    def __init__(self, structure_file, dose_file):
        # Get ROI Category Map
        database_rois = DatabaseROIs()

        # Import RT Structure and RT Dose files using dicompyler
        rt_structure_dicom = dicom.read_file(structure_file)
        mrn = rt_structure_dicom.PatientID
        study_instance_uid = rt_structure_dicom.StudyInstanceUID

        rt_structure = dicomparser.DicomParser(structure_file)
        rt_structures = rt_structure.GetStructures()

        if hasattr(rt_structure_dicom, 'PhysiciansOfRecord'):
            physician = rt_structure_dicom.PhysiciansOfRecord.upper()
        elif hasattr(rt_structure_dicom, 'ReferringPhysicianName'):
            physician = rt_structure_dicom.ReferringPhysicianName.upper()
        else:
            physician = '(NULL)'

        values = {}
        row_counter = 0
        self.dvhs = {}
        for key in rt_structures:
            # Import DVH from RT Structure and RT Dose files
            if rt_structures[key]['type'] != 'MARKER':

                current_dvh_calc = dvhcalc.get_dvh(structure_file, dose_file, key)
                self.dvhs[row_counter] = current_dvh_calc.counts
                if current_dvh_calc.volume > 0:
                    print('Importing', current_dvh_calc.name, sep=' ')
                    if rt_structures[key]['name'].lower().find('itv') == 0:
                        roi_type = 'ITV'
                    else:
                        roi_type = rt_structures[key]['type']
                    current_roi_name = clean_name(rt_structures[key]['name'])

                    if database_rois.is_roi(current_roi_name):
                        if database_rois.is_physician(physician):
                            physician_roi = database_rois.get_physician_roi(physician, current_roi_name)
                            institutional_roi = database_rois.get_institutional_roi(physician, physician_roi)
                        else:
                            if current_roi_name in database_rois.institutional_rois:
                                institutional_roi = current_roi_name
                            else:
                                institutional_roi = 'uncategorized'
                            physician_roi = 'uncategorized'
                    else:
                        institutional_roi = 'uncategorized'
                        physician_roi = 'uncategorized'

                    coord = rt_structure.GetStructureCoordinates(key)
                    roi_coord_str = dicompyler_roi_coord_to_db_string(rt_structure.GetStructureCoordinates(key))
                    try:
                        surface_area = roi_calc.surface_area(coord)
                    except:
                        print("Surface area calculation failed for key, name: %s, %s" % (key, current_dvh_calc.name))
                        surface_area = '(NULL)'

                    planes = get_planes_from_string(roi_coord_str)
                    centroid = roi_calc.centroid(planes)
                    spread = roi_calc.spread(planes)
                    cross_sections = roi_calc.cross_section(planes)

                    current_dvh_row = DVHRow(mrn,
                                             study_instance_uid,
                                             institutional_roi,
                                             physician_roi,
                                             current_roi_name,
                                             roi_type,
                                             current_dvh_calc.volume,
                                             current_dvh_calc.min,
                                             current_dvh_calc.mean,
                                             current_dvh_calc.max,
                                             ','.join(['%.2f' % num for num in current_dvh_calc.counts]),
                                             roi_coord_str,
                                             surface_area,
                                             ','.join(['%.3f' % num for num in centroid]),
                                             spread[0],
                                             spread[1],
                                             spread[2],
                                             cross_sections['max'],
                                             cross_sections['median'])
                    values[row_counter] = current_dvh_row
                    row_counter += 1

        self.count = row_counter
        dvh_range = range(self.count)

        for attr in dir(values[0]):
            if not attr.startswith('_'):
                setattr(self, attr, [getattr(values[x], attr) for x in dvh_range])


class BeamTable:
    def __init__(self, plan_file):
        beam_num = 0
        values = {}
        # Import RT Dose files using dicompyler
        rt_plan = dicom.read_file(plan_file)

        mrn = rt_plan.PatientID
        study_instance_uid = rt_plan.StudyInstanceUID

        fx_grp = 0
        for fx_grp_seq in rt_plan.FractionGroupSequence:
            fx_grp += 1
            fxs = int(float(fx_grp_seq.NumberOfFractionsPlanned))
            fx_grp_beam_count = int(fx_grp_seq.NumberOfBeams)

            for fx_grp_beam in range(fx_grp_beam_count):

                if hasattr(rt_plan, 'BeamSequence'):
                    beam_seq = rt_plan.BeamSequence[beam_num]  # Photons and electrons
                    beam_number = rt_plan.BeamSequence[beam_num].BeamNumber
                else:
                    beam_seq = rt_plan.IonBeamSequence[beam_num]  # Protons
                    beam_number = rt_plan.IonBeamSequence[beam_num].BeamNumber

                if 'BeamDescription' in beam_seq:
                    beam_name = beam_seq.BeamDescription
                else:
                    beam_name = beam_seq.BeamName

                ref_beam_seq_index = self.get_referenced_beam_sequence_index(fx_grp_seq, beam_number)
                if ref_beam_seq_index is None:
                    ref_beam_seq_index = fx_grp_beam  # This shouldn't ever occur, but just to be safe
                ref_beam_seq = fx_grp_seq.ReferencedBeamSequence[ref_beam_seq_index]

                if hasattr(beam_seq, 'TreatmentMachineName'):
                    treatment_machine = beam_seq.TreatmentMachineName
                else:
                    treatment_machine = '(NULL)'

                if hasattr(ref_beam_seq, 'BeamDose'):
                    beam_dose = float(ref_beam_seq.BeamDose)
                else:
                    beam_dose = 0.
                if hasattr(ref_beam_seq, 'BeamMeterset'):
                    beam_mu = float(ref_beam_seq.BeamMeterset)
                else:
                    beam_mu = 0

                if hasattr(ref_beam_seq, 'BeamDoseSpecificationPoint'):
                    beam_dose_pt = [str(round(ref_beam_seq.BeamDoseSpecificationPoint[0], 2)),
                                    str(round(ref_beam_seq.BeamDoseSpecificationPoint[1], 2)),
                                    str(round(ref_beam_seq.BeamDoseSpecificationPoint[2], 2))]
                    beam_dose_pt = ','.join(beam_dose_pt)
                else:
                    beam_dose_pt = '(NULL)'

                radiation_type = beam_seq.RadiationType
                if hasattr(beam_seq, 'ControlPointSequence'):
                    cp_seq = beam_seq.ControlPointSequence
                else:
                    cp_seq = beam_seq.IonControlPointSequence

                if hasattr(cp_seq[0], 'IsocenterPosition'):
                    isocenter = [str(round(cp_seq[0].IsocenterPosition[0], 2)),
                                 str(round(cp_seq[0].IsocenterPosition[1], 2)),
                                 str(round(cp_seq[0].IsocenterPosition[2], 2))]
                    isocenter = ','.join(isocenter)
                else:
                    isocenter = '(NULL)'

                beam_type = beam_seq.BeamType

                if hasattr(beam_seq, 'ScanMode'):
                    scan_mode = beam_seq.ScanMode
                else:
                    scan_mode = '(NULL)'

                scan_spot_count = 0
                if hasattr(cp_seq[0], 'NumberOfScanSpotPositions'):
                    for cp in cp_seq:
                        scan_spot_count += int(cp.NumberOfScanSpotPositions)
                    scan_spot_count /= 2

                energies = []
                gantry_angles = []
                collimator_angles = []
                couch_angles = []
                gantry_rot_dir = []
                collimator_rot_dir = []
                couch_rot_dir = []
                for cp in cp_seq:
                    if hasattr(cp, 'NominalBeamEnergy'):
                        energies.append(cp.NominalBeamEnergy)
                    if hasattr(cp, 'GantryAngle'):
                        gantry_angles.append(cp.GantryAngle)
                    if hasattr(cp, 'BeamLimitingDeviceAngle'):
                        collimator_angles.append(cp.BeamLimitingDeviceAngle)
                    if hasattr(cp, 'PatientSupportAngle'):
                        couch_angles.append(cp.PatientSupportAngle)
                    if hasattr(cp, 'GantryRotationDirection'):
                        if cp.GantryRotationDirection.upper() in {'CC', 'CW'}:
                            gantry_rot_dir.append(cp.GantryRotationDirection.upper())
                    if hasattr(cp, 'BeamLimitingDeviceRotationDirection'):
                        if cp.BeamLimitingDeviceRotationDirection.upper() in {'CC', 'CW'}:
                            collimator_rot_dir.append(cp.BeamLimitingDeviceRotationDirection.upper())
                    if hasattr(cp, 'PatientSupportRotationDirection'):
                        if cp.PatientSupportRotationDirection.upper() in {'CC', 'CW'}:
                            couch_rot_dir.append(cp.PatientSupportRotationDirection.upper())
                if not collimator_angles:
                    collimator_angles = [0]
                if not couch_angles:
                    couch_angles = [0]
                if not gantry_rot_dir:
                    gantry_rot_dir = ['-']
                if not collimator_rot_dir:
                    collimator_rot_dir = ['-']
                if not couch_rot_dir:
                    couch_rot_dir = ['-']

                max_angle = 180
                gantry_angles = change_angle_origin(gantry_angles, max_angle)
                collimator_angles = change_angle_origin(collimator_angles, max_angle)
                couch_angles = change_angle_origin(couch_angles, max_angle)

                if len(set(gantry_rot_dir)) == 1:
                    gantry_rot_dir = gantry_rot_dir[0]
                else:
                    if gantry_rot_dir[0] == 'CC':
                        gantry_rot_dir = 'CC/CW'
                    else:
                        gantry_rot_dir = 'CW/CC'
                if len(set(collimator_rot_dir)) == 1:
                    collimator_rot_dir = collimator_rot_dir[0]
                else:
                    if collimator_rot_dir[0] == 'CC':
                        collimator_rot_dir = 'CC/CW'
                    else:
                        collimator_rot_dir = 'CW/CC'
                if len(set(couch_rot_dir)) == 1:
                    couch_rot_dir = couch_rot_dir[0]
                else:
                    if couch_rot_dir[0] == 'CC':
                        couch_rot_dir = 'CC/CW'
                    else:
                        couch_rot_dir = 'CW/CC'

                gantry = {'start': gantry_angles[0],
                          'end': gantry_angles[-1],
                          'rot_dir': gantry_rot_dir,
                          'range': round(float(np.sum(np.abs(np.diff(gantry_angles)))), 1),
                          'min': min(gantry_angles),
                          'max': max(gantry_angles)}

                collimator = {'start': collimator_angles[0],
                              'end': collimator_angles[-1],
                              'rot_dir': collimator_rot_dir,
                              'range': round(float(np.sum(np.abs(np.diff(collimator_angles)))), 1),
                              'min': min(collimator_angles),
                              'max': max(collimator_angles)}

                couch = {'start': couch_angles[0],
                         'end': couch_angles[-1],
                         'rot_dir': couch_rot_dir,
                         'range': round(float(np.sum(np.abs(np.diff(couch_angles)))), 1),
                         'min': min(couch_angles),
                         'max': max(couch_angles)}

                control_point_count = beam_seq.NumberOfControlPoints
                # If beam is an arc, return average SSD, otherwise
                if hasattr(cp_seq[0], 'SourceToSurfaceDistance'):
                    if gantry_rot_dir != '-':
                        ssd = []
                        for cp in cp_seq:
                            if hasattr(cp, 'SourceToSurfaceDistance'):
                                ssd.append(round(float(cp.SourceToSurfaceDistance) / 10., 2))
                        ssd = round(float(np.average(ssd)), 2)

                    else:
                        ssd = round(float(cp_seq[0].SourceToSurfaceDistance) / 10., 2)
                else:
                    ssd = '(NULL)'

                if gantry['range'] > 0:
                    beam_mu_per_deg = round(beam_mu / gantry['range'], 2)
                else:
                    beam_mu_per_deg = '(NULL)'

                beam_mu_per_cp = round(beam_mu / float(control_point_count), 2)

                mlc_keys = ['area', 'x_perim', 'y_perim', 'cmp_score', 'cp_mu']
                try:
                    mlc_summary_data = mlca(beam_seq, beam_mu, ignore_zero_mu_cp=True).summary
                    mlca_stat_data = {key: calc_stats(mlc_summary_data[key]) for key in mlc_keys}
                    complexity = np.sum(mlc_summary_data['cmp_score'])
                except:
                    mlca_stat_data = {key: ['NULL'] * 6 for key in mlc_keys}
                    complexity = 'NULL'

                current_beam = BeamRow(mrn, study_instance_uid, beam_num + 1,
                                       beam_name, fx_grp, fxs,
                                       fx_grp_beam_count, beam_dose, beam_mu, radiation_type,
                                       round(min(energies), 2), round(min(energies), 2), beam_type, control_point_count,
                                       gantry['start'], gantry['end'], gantry['rot_dir'],
                                       gantry['range'], gantry['min'], gantry['max'],
                                       collimator['start'], collimator['end'], collimator['rot_dir'],
                                       collimator['range'], collimator['min'], collimator['max'],
                                       couch['start'], couch['end'], couch['rot_dir'],
                                       couch['range'], couch['min'], couch['max'],
                                       beam_dose_pt, isocenter, ssd, treatment_machine, scan_mode, scan_spot_count,
                                       beam_mu_per_deg, beam_mu_per_cp,
                                       mlca_stat_data['area'][5], mlca_stat_data['area'][3], mlca_stat_data['area'][2], mlca_stat_data['area'][0],
                                       mlca_stat_data['x_perim'][5], mlca_stat_data['x_perim'][3], mlca_stat_data['x_perim'][2], mlca_stat_data['x_perim'][0],
                                       mlca_stat_data['y_perim'][5], mlca_stat_data['y_perim'][3], mlca_stat_data['y_perim'][2], mlca_stat_data['y_perim'][0],
                                       mlca_stat_data['cmp_score'][5], mlca_stat_data['cmp_score'][3], mlca_stat_data['cmp_score'][2], mlca_stat_data['cmp_score'][0], complexity,
                                       mlca_stat_data['cp_mu'][5], mlca_stat_data['cp_mu'][3], mlca_stat_data['cp_mu'][2], mlca_stat_data['cp_mu'][0])

                values[beam_num] = current_beam
                beam_num += 1

        self.count = beam_num
        beam_range = range(self.count)

        # Rearrange values into separate attributes
        for attr in dir(values[0]):
            if not attr.startswith('_'):
                new_list = []
                for x in beam_range:
                    new_list.append(getattr(values[x], attr))
                setattr(self, attr, new_list)

    @staticmethod
    def get_referenced_beam_sequence_index(fx_grp_seq, beam_number):
        for i, ref_beam_seq in enumerate(fx_grp_seq.ReferencedBeamSequence):
            if ref_beam_seq.ReferencedBeamNumber == beam_number:
                return i
        print('ERROR: Failed to find a matching reference beam in '
              'ReferencedBeamSequence for beam number %s' % beam_number)
        return None


class RxTable:
    def __init__(self, plan_file, structure_file):
        values = {}
        rt_plan = dicom.read_file(plan_file)
        dicompyler_plan = dicomparser.DicomParser(plan_file).GetPlan()
        rt_structure = dicom.read_file(structure_file)
        fx_grp_seq = rt_plan.FractionGroupSequence

        # Record Medical Record Number
        mrn = rt_plan.PatientID

        # This UID must be in all DICOM files associated with this sim study
        study_instance_uid = rt_plan.StudyInstanceUID

        fx_group_count = len(fx_grp_seq)

        for i in range(fx_group_count):
            rx_dose = 0
            rx_pt_found = False
            normalization_method = 'default'
            normalization_object = 'unknown'
            rx_percent = 100.
            fx_grp_number = i + 1
            fx_dose = 0
            fx_grp_name = "FxGrp " + str(i + 1)
            plan_name = rt_plan.RTPlanLabel

            if hasattr(rt_plan, 'DoseReferenceSequence'):
                if hasattr(rt_plan.DoseReferenceSequence[i], 'TargetPrescriptionDose'):
                    rx_dose = rt_plan.DoseReferenceSequence[i].TargetPrescriptionDose
                if hasattr(rt_plan.DoseReferenceSequence[i], 'DoseReferenceStructureType'):
                    normalization_method = rt_plan.DoseReferenceSequence[i].DoseReferenceStructureType
                if normalization_method.lower() == 'coordinates':
                    normalization_object_found = True
                    normalization_object = 'COORDINATE'
                elif normalization_method.lower() == 'site':
                    normalization_object_found = True
                    if hasattr(rt_plan, 'ManufacturerModelName'):
                        normalization_object = rt_plan.ManufacturerModelName
                    else:
                        normalization_object = '(NULL)'
                else:
                    ref_roi_num = rt_plan.DoseReferenceSequence[i].ReferencedROINumber
                    normalization_object_found = False
                    j = 0
                while not normalization_object_found:
                    if rt_structure.ROIContourSequence[j].ReferencedROINumber == ref_roi_num:
                            normalization_object = rt_structure.StructureSetROISequence[j].ROIName
                            normalization_object_found = True
                    j += 1

                rx_pt_found = True

            if hasattr(fx_grp_seq, 'ReferencedBeamSequence'):
                for ref_beam_seq in fx_grp_seq[i].ReferencedBeamSequence:
                    fx_dose += float(ref_beam_seq.BeamDose)
            elif hasattr(fx_grp_seq, 'ReferencedBrachyApplicationSetupSequence'):
                for ref_app_seq in fx_grp_seq[i].ReferencedBrachyApplicationSetupSequence:
                    fx_dose += float(ref_app_seq.BrachyApplicationSetupDose)

            fxs = fx_grp_seq[i].NumberOfFractionsPlanned

            if rx_dose == 0:
                rx_dose = float(dicompyler_plan['rxdose']) / 100.

            if fx_dose == 0:
                if float(fxs):
                    fx_dose = round(rx_dose / float(fxs), 2)

            # Because DICOM does not contain Rx's explicitly, the user must create
            # a point in the RT Structure file called 'rx [#]: ' per rx
            roi_counter = 0
            roi_seq = rt_structure.StructureSetROISequence  # just limit num characters in code
            roi_count = len(roi_seq)
            # set defaults in case rx and tx points are not found
            while roi_counter < roi_count and not rx_pt_found:
                roi_name = roi_seq[roi_counter].ROIName.lower()
                if len(roi_name) > 2:
                    temp = roi_name.split(':')

                    if temp[0][0:3] == 'rx ' and int(temp[0].strip('rx ')) == i + 1:
                        fx_grp_number = int(temp[0].strip('rx '))

                        fx_grp_name = temp[1].strip()

                        fx_dose = float(temp[2].split('cgy')[0]) / 100.
                        fxs = int(temp[2].split('x ')[1].split(' to')[0])
                        rx_dose = fx_dose * float(fxs)

                        rx_percent = float(temp[2].strip().split(' ')[5].strip('%'))
                        normalization_method = temp[3].strip()

                        if normalization_method != 'plan_max':
                            normalization_object = temp[4].strip()
                        else:
                            normalization_object = 'plan_max'
                        rx_pt_found = True

                roi_counter += 1

            current_fx_grp_row = RxRow(mrn, study_instance_uid, plan_name, fx_grp_name, fx_grp_number,
                                       fx_group_count, fx_dose, fxs, rx_dose, rx_percent, normalization_method,
                                       normalization_object)
            values[i] = current_fx_grp_row

        fx_group_range = range(fx_group_count)
        self.count = fx_group_count
        # Rearrange values into separate attributes
        for attr in dir(values[0]):
            if not attr.startswith('_'):
                new_list = []
                for x in fx_group_range:
                    new_list.append(getattr(values[x], attr))
                setattr(self, attr, new_list)


def get_tables(structure_file, dose_file, plan_file):
    dvh_table = DVHTable(structure_file, dose_file)
    plan_table = PlanRow(plan_file, structure_file, dose_file)
    rx_table = RxTable(plan_file, structure_file)
    beam_table = BeamTable(plan_file)

    return dvh_table, plan_table, rx_table, beam_table
