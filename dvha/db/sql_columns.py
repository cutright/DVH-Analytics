#!/usr/bin/env python
# -*- coding: utf-8 -*-

# db.sql_columns.py
"""
These objects are largely used for designing queries in the GUI to easily
connect UI friendly variable names with their associated SQL tables column
names
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

# This is a maps categorical data type selections to SQL columns and SQL tables
categorical = {
    "ROI Institutional Category": {
        "var_name": "institutional_roi",
        "table": "DVHs",
    },
    "ROI Physician Category": {"var_name": "physician_roi", "table": "DVHs"},
    "ROI Name": {"var_name": "roi_name", "table": "DVHs"},
    "ROI Type": {"var_name": "roi_type", "table": "DVHs"},
    "Beam Type": {"var_name": "beam_type", "table": "Beams"},
    "Collimator Rotation Direction": {
        "var_name": "collimator_rot_dir",
        "table": "Beams",
    },
    "Couch Rotation Direction": {
        "var_name": "couch_rot_dir",
        "table": "Beams",
    },
    "Dose Grid Resolution": {"var_name": "dose_grid_res", "table": "Plans"},
    "Gantry Rotation Direction": {
        "var_name": "gantry_rot_dir",
        "table": "Beams",
    },
    "Radiation Type": {"var_name": "radiation_type", "table": "Beams"},
    "Patient Orientation": {
        "var_name": "patient_orientation",
        "table": "Plans",
    },
    "Patient Sex": {"var_name": "patient_sex", "table": "Plans"},
    "Physician": {"var_name": "physician", "table": "Plans"},
    "Tx Modality": {"var_name": "tx_modality", "table": "Plans"},
    "Tx Site": {"var_name": "tx_site", "table": "Plans"},
    "Normalization": {"var_name": "normalization_method", "table": "Rxs"},
    "Treatment Machine": {"var_name": "treatment_machine", "table": "Beams"},
    "Heterogeneity Correction": {
        "var_name": "heterogeneity_correction",
        "table": "Plans",
    },
    "Scan Mode": {"var_name": "scan_mode", "table": "Beams"},
    "MRN": {"var_name": "mrn", "table": "Plans"},
    "UID": {"var_name": "study_instance_uid", "table": "Plans"},
    "Baseline": {"var_name": "baseline", "table": "Plans"},
    "Protocol": {"var_name": "protocol", "table": "Plans"},
}

# This is a maps quantitative data type selections to SQL columns and SQL
# tables, and the bokeh source
numerical = {
    "Age": {"var_name": "age", "table": "Plans", "units": ""},
    "Beam Energy Min": {
        "var_name": "beam_energy_min",
        "table": "Beams",
        "units": "",
    },
    "Beam Energy Max": {
        "var_name": "beam_energy_max",
        "table": "Beams",
        "units": "",
    },
    "Birth Date": {"var_name": "birth_date", "table": "Plans", "units": ""},
    "Planned Fractions": {"var_name": "fxs", "table": "Plans", "units": ""},
    "Rx Dose": {"var_name": "rx_dose", "table": "Plans", "units": "Gy"},
    "Rx Isodose": {"var_name": "rx_percent", "table": "Rxs", "units": "%"},
    "Simulation Date": {
        "var_name": "sim_study_date",
        "table": "Plans",
        "units": "",
    },
    "Total Plan MU": {"var_name": "total_mu", "table": "Plans", "units": "MU"},
    "Fraction Dose": {"var_name": "fx_dose", "table": "Rxs", "units": "Gy"},
    "Beam Dose": {"var_name": "beam_dose", "table": "Beams", "units": "Gy"},
    "Beam MU": {"var_name": "beam_mu", "table": "Beams", "units": ""},
    "Control Point Count": {
        "var_name": "control_point_count",
        "table": "Beams",
        "units": "",
    },
    "SSD": {"var_name": "ssd", "table": "Beams", "units": "cm"},
    "ROI Min Dose": {"var_name": "min_dose", "table": "DVHs", "units": "Gy"},
    "ROI Mean Dose": {"var_name": "mean_dose", "table": "DVHs", "units": "Gy"},
    "ROI Max Dose": {"var_name": "max_dose", "table": "DVHs", "units": "Gy"},
    "ROI Volume": {"var_name": "volume", "table": "DVHs", "units": "cm³"},
    "ROI Surface Area": {
        "var_name": "surface_area",
        "table": "DVHs",
        "units": "cm²",
    },
    "ROI Spread X": {"var_name": "spread_x", "table": "DVHs", "units": "cm"},
    "ROI Spread Y": {"var_name": "spread_y", "table": "DVHs", "units": "cm"},
    "ROI Spread Z": {"var_name": "spread_z", "table": "DVHs", "units": "cm"},
    "PTV Distance (Min)": {
        "var_name": "dist_to_ptv_min",
        "table": "DVHs",
        "units": "cm",
    },
    "PTV Distance (Mean)": {
        "var_name": "dist_to_ptv_mean",
        "table": "DVHs",
        "units": "cm",
    },
    "PTV Distance (Median)": {
        "var_name": "dist_to_ptv_median",
        "table": "DVHs",
        "units": "cm",
    },
    "PTV Distance (Max)": {
        "var_name": "dist_to_ptv_max",
        "table": "DVHs",
        "units": "cm",
    },
    "PTV Distance (Centroids)": {
        "var_name": "dist_to_ptv_centroids",
        "table": "DVHs",
        "units": "cm",
    },
    "PTV Overlap": {
        "var_name": "ptv_overlap",
        "table": "DVHs",
        "units": "cm³",
    },
    "Scan Spots": {
        "var_name": "scan_spot_count",
        "table": "Beams",
        "units": "",
    },
    "Beam MU per deg": {
        "var_name": "beam_mu_per_deg",
        "table": "Beams",
        "units": "",
    },
    "Beam MU per control point": {
        "var_name": "beam_mu_per_cp",
        "table": "Beams",
        "units": "",
    },
    "ROI Cross-Section Max": {
        "var_name": "cross_section_max",
        "table": "DVHs",
        "units": "cm²",
    },
    "ROI Cross-Section Median": {
        "var_name": "cross_section_median",
        "table": "DVHs",
        "units": "cm²",
    },
    "Toxicity Grade": {
        "var_name": "toxicity_grade",
        "table": "DVHs",
        "units": "",
    },
    "ROI Centroid to Isocenter (Min)": {
        "var_name": "centroid_dist_to_iso_min",
        "table": "DVHs",
        "units": "cm",
    },
    "ROI Centroid to Isocenter (Max)": {
        "var_name": "centroid_dist_to_iso_max",
        "table": "DVHs",
        "units": "cm",
    },
    "Plan Complexity": {
        "var_name": "complexity",
        "table": "Plans",
        "units": "",
    },
    "Beam Complexity (Min)": {
        "var_name": "complexity_min",
        "table": "Beams",
        "units": "",
    },
    "Beam Complexity (Mean)": {
        "var_name": "complexity_mean",
        "table": "Beams",
        "units": "",
    },
    "Beam Complexity (Median)": {
        "var_name": "complexity_median",
        "table": "Beams",
        "units": "",
    },
    "Beam Complexity (Max)": {
        "var_name": "complexity_max",
        "table": "Beams",
        "units": "",
    },
    "Beam Area (Min)": {
        "var_name": "area_min",
        "table": "Beams",
        "units": "cm²",
    },
    "Beam Area (Mean)": {
        "var_name": "area_mean",
        "table": "Beams",
        "units": "cm²",
    },
    "Beam Area (Median)": {
        "var_name": "area_median",
        "table": "Beams",
        "units": "cm²",
    },
    "Beam Area (Max)": {
        "var_name": "area_max",
        "table": "Beams",
        "units": "cm²",
    },
    "Beam Perimeter X (Min)": {
        "var_name": "x_perim_min",
        "table": "Beams",
        "units": "cm",
    },
    "Beam Perimeter X (Mean)": {
        "var_name": "x_perim_mean",
        "table": "Beams",
        "units": "cm",
    },
    "Beam Perimeter X (Median)": {
        "var_name": "x_perim_median",
        "table": "Beams",
        "units": "cm",
    },
    "Beam Perimeter X (Max)": {
        "var_name": "x_perim_max",
        "table": "Beams",
        "units": "cm",
    },
    "Beam Perimeter Y (Min)": {
        "var_name": "y_perim_min",
        "table": "Beams",
        "units": "cm",
    },
    "Beam Perimeter Y (Mean)": {
        "var_name": "y_perim_mean",
        "table": "Beams",
        "units": "cm",
    },
    "Beam Perimeter Y (Median)": {
        "var_name": "y_perim_median",
        "table": "Beams",
        "units": "cm",
    },
    "Beam Perimeter Y (Max)": {
        "var_name": "y_perim_max",
        "table": "Beams",
        "units": "cm",
    },
    "Beam Perimeter (Min)": {
        "var_name": "perim_min",
        "table": "Beams",
        "units": "cm",
    },
    "Beam Perimeter (Mean)": {
        "var_name": "perim_mean",
        "table": "Beams",
        "units": "cm",
    },
    "Beam Perimeter (Median)": {
        "var_name": "perim_median",
        "table": "Beams",
        "units": "cm",
    },
    "Beam Perimeter (Max)": {
        "var_name": "perim_max",
        "table": "Beams",
        "units": "cm",
    },
    "Fx Group Beam Count": {
        "var_name": "fx_grp_beam_count",
        "table": "Beams",
        "units": "",
    },
    "Control Point MU (Min)": {
        "var_name": "cp_mu_min",
        "table": "Beams",
        "units": "",
    },
    "Control Point MU (Mean)": {
        "var_name": "cp_mu_mean",
        "table": "Beams",
        "units": "",
    },
    "Control Point MU (Median)": {
        "var_name": "cp_mu_median",
        "table": "Beams",
        "units": "",
    },
    "Control Point MU (Max)": {
        "var_name": "cp_mu_max",
        "table": "Beams",
        "units": "",
    },
    "PTV Cross-Section Max": {
        "var_name": "ptv_cross_section_max",
        "table": "Plans",
        "units": "cm²",
    },
    "PTV Cross-Section Median": {
        "var_name": "ptv_cross_section_median",
        "table": "Plans",
        "units": "cm²",
    },
    "PTV Spread X": {
        "var_name": "ptv_spread_x",
        "table": "Plans",
        "units": "cm",
    },
    "PTV Spread Y": {
        "var_name": "ptv_spread_y",
        "table": "Plans",
        "units": "cm",
    },
    "PTV Spread Z": {
        "var_name": "ptv_spread_z",
        "table": "Plans",
        "units": "cm",
    },
    "PTV Surface Area": {
        "var_name": "ptv_surface_area",
        "table": "Plans",
        "units": "cm²",
    },
    "PTV Volume": {"var_name": "ptv_volume", "table": "Plans", "units": "cm³"},
    "PTV Max Dose": {
        "var_name": "ptv_max_dose",
        "table": "Plans",
        "units": "Gy",
    },
    "PTV Min Dose": {
        "var_name": "ptv_min_dose",
        "table": "Plans",
        "units": "Gy",
    },
}

# Removed these variables from UI as they may be overkill?
numerical_detailed = {
    "Collimator Start Angle": {
        "var_name": "collimator_start",
        "table": "Beams",
        "units": "deg",
    },
    "Collimator End Angle": {
        "var_name": "collimator_end",
        "table": "Beams",
        "units": "deg",
    },
    "Collimator Min Angle": {
        "var_name": "collimator_min",
        "table": "Beams",
        "units": "deg",
    },
    "Collimator Max Angle": {
        "var_name": "collimator_max",
        "table": "Beams",
        "units": "deg",
    },
    "Collimator Range": {
        "var_name": "collimator_range",
        "table": "Beams",
        "units": "deg",
    },
    "Couch Start Angle": {
        "var_name": "couch_start",
        "table": "Beams",
        "units": "deg",
    },
    "Couch End Angle": {
        "var_name": "couch_end",
        "table": "Beams",
        "units": "deg",
    },
    "Couch Min Angle": {
        "var_name": "couch_min",
        "table": "Beams",
        "units": "deg",
    },
    "Couch Max Angle": {
        "var_name": "couch_max",
        "table": "Beams",
        "units": "deg",
    },
    "Couch Range": {
        "var_name": "couch_range",
        "table": "Beams",
        "units": "deg",
    },
    "Gantry Start Angle": {
        "var_name": "gantry_start",
        "table": "Beams",
        "units": "deg",
    },
    "Gantry End Angle": {
        "var_name": "gantry_end",
        "table": "Beams",
        "units": "deg",
    },
    "Gantry Min Angle": {
        "var_name": "gantry_min",
        "table": "Beams",
        "units": "deg",
    },
    "Gantry Max Angle": {
        "var_name": "gantry_max",
        "table": "Beams",
        "units": "deg",
    },
    "Gantry Range": {
        "var_name": "gantry_range",
        "table": "Beams",
        "units": "deg",
    },
}
numerical_detailed.update(numerical)

all_columns = {}
all_columns.update(categorical)
all_columns.update(numerical_detailed)
