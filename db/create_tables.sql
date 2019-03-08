CREATE TABLE IF NOT EXISTS Plans (mrn text, study_instance_uid text, birth_date date, age smallint, patient_sex char(1), sim_study_date date, physician varchar(50), tx_site varchar(50), rx_dose real, fxs int, patient_orientation varchar(3), plan_time_stamp timestamp, struct_time_stamp timestamp, dose_time_stamp timestamp, tps_manufacturer varchar(50), tps_software_name varchar(50), tps_software_version varchar(30), tx_modality varchar(30), tx_time time, total_mu real, dose_grid_res varchar(16), heterogeneity_correction varchar(30), baseline boolean, import_time_stamp timestamp);
CREATE TABLE IF NOT EXISTS DVHs (mrn text, study_instance_uid text, institutional_roi varchar(50), physician_roi varchar(50), roi_name varchar(50), roi_type varchar(20), volume real, min_dose real, mean_dose real, max_dose real, dvh_string text, roi_coord_string text, dist_to_ptv_min real, dist_to_ptv_mean real, dist_to_ptv_median real, dist_to_ptv_max real, surface_area real, ptv_overlap real, import_time_stamp timestamp);
CREATE TABLE IF NOT EXISTS Beams (mrn text, study_instance_uid text, beam_number int, beam_name varchar(30), fx_grp_number smallint, fx_count int, fx_grp_beam_count smallint, beam_dose real, beam_mu real, radiation_type varchar(30), beam_energy_min real, beam_energy_max real, beam_type varchar(30), control_point_count int, gantry_start real, gantry_end real, gantry_rot_dir varchar(5), gantry_range real, gantry_min real, gantry_max real, collimator_start real, collimator_end real, collimator_rot_dir varchar(5), collimator_range real, collimator_min real, collimator_max real, couch_start real, couch_end real, couch_rot_dir varchar(5), couch_range real, couch_min real, couch_max real, beam_dose_pt varchar(35), isocenter varchar(35), ssd real, treatment_machine varchar(30), scan_mode varchar(30), scan_spot_count real, beam_mu_per_deg real, beam_mu_per_cp real, import_time_stamp timestamp);
CREATE TABLE IF NOT EXISTS Rxs (mrn text, study_instance_uid text, plan_name varchar(50), fx_grp_name varchar(30), fx_grp_number smallint, fx_grp_count smallint, fx_dose real, fxs smallint, rx_dose real, rx_percent real, normalization_method varchar(30), normalization_object varchar(30), import_time_stamp timestamp);
CREATE TABLE IF NOT EXISTS DICOM_Files (mrn text, study_instance_uid text, folder_path text, plan_file text, structure_file text, dose_file text, import_time_stamp timestamp);
-- The following columns have been added as of DVH Analytics 0.4.4
ALTER TABLE DVHs ADD COLUMN IF NOT EXISTS centroid varchar(35);
ALTER TABLE DVHs ADD COLUMN IF NOT EXISTS dist_to_ptv_centroids real;
ALTER TABLE DVHs ADD COLUMN IF NOT EXISTS dth_string text;
ALTER TABLE DVHs ADD COLUMN IF NOT EXISTS spread_x real;
ALTER TABLE DVHs ADD COLUMN IF NOT EXISTS spread_y real;
ALTER TABLE DVHs ADD COLUMN IF NOT EXISTS spread_z real;
ALTER TABLE DVHs ADD COLUMN IF NOT EXISTS cross_section_max real;
ALTER TABLE DVHs ADD COLUMN IF NOT EXISTS cross_section_median real;
-- The following columns have been added as of DVH Analytics 0.5.2
ALTER TABLE Plans ADD COLUMN IF NOT EXISTS toxicity_scales text;
ALTER TABLE Plans ADD COLUMN IF NOT EXISTS toxicity_grades text;
ALTER TABLE DVHs ADD COLUMN IF NOT EXISTS toxicity_scale text;
ALTER TABLE DVHs ADD COLUMN IF NOT EXISTS toxicity_grade smallint;
ALTER TABLE Plans ADD COLUMN IF NOT EXISTS protocol text;
-- The following columns have been added as of DVH Analytics 0.5.3
ALTER TABLE Plans DROP COLUMN IF EXISTS toxicity_scales;
ALTER TABLE DVHs DROP COLUMN IF EXISTS toxicity_scale;
-- The following columns have been added as of DVH Analytics 0.5.4
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS area_min real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS area_mean real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS area_median real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS area_max real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS x_perim_min real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS x_perim_mean real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS x_perim_median real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS x_perim_max real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS y_perim_min real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS y_perim_mean real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS y_perim_median real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS y_perim_max real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS complexity_min real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS complexity_mean real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS complexity_median real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS complexity_max real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS cp_mu_min real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS cp_mu_mean real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS cp_mu_median real;
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS cp_mu_max real;
ALTER TABLE Plans ADD COLUMN IF NOT EXISTS complexity real;
-- The following columns have been added as of DVH Analytics 0.5.5
ALTER TABLE Beams ADD COLUMN IF NOT EXISTS complexity real;