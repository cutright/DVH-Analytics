.. _datadictionary:

Data Dictionary
===============

Each table below describes a SQL table (of the same name as the section header).
This is manually generated, so best to check out ``dvha.db.create_tables.sql`` and
``dvha.db.create_tables_sqlite.sql`` for any changes.

DVHs
----
Storage of DVHs and other ROI specific data.

========================  =============  =======  ==============   ==========================================
Column                    Data Type       Units   DICOM Tag        Description
========================  =============  =======  ==============   ==========================================
mrn                       text           --       (0010, 0020)     Medical Record Number (PatientID)
study_instance_uid        text           --       (0020, 000d)     Unique ID tied to planning image set
institutional_roi         varchar(50)    --       --               Standard ROI name for all physician
physician_roi             varchar(50)    --       --               Standard ROI name for patient's physician
roi_name                  varchar(50)    --       (3006, 0026)     ROI name as in plan
roi_type                  varchar(20)    --       (3006, 00a4)     ROI categegoy (e.g., ORGAN, PTV)
volume                    real           cm³      --               ROI volume per dicompyler
min_dose                  real           Gy       --               Min ROI dose per dicompyler
mean_dose                 real           Gy       --               Mean ROI dose per dicompyler
max_dose                  real           Gy       --               Max ROI dose per dicompyler
dvh_string                text           cGy      --               CSV of DVH in 1 $cGy$ bins
roi_coord_string          text           --       (3006, 0050)     Single string containing all ROI points
dist_to_ptv_min           real           cm       --               Calculated with scipy's cdist function
dist_to_ptv_mean          real           cm       --               Calculated with scipy's cdist function
dist_to_ptv_median        real           cm       --               Calculated with scipy's cdist function
dist_to_ptv_max           real           cm       --               Calculated with scipy's cdist function
surface_area              real           cm²      --               DVHA custom function, needs validation
ptv_overlap               real           cm³      --               DVHA custom function with Shapely
import_time_stamp         timestamp      --       --               Time per SQL at time of import
centroid                  varchar(35)    --       --               DVHA custom function
dist_to_ptv_centroids     real           cm       --               DVHA custom function
dth_string                text           cm       --               numpy histogram of scipy cdist with PTV
spread_x                  real           cm       (3006, 0050)     Max distance in x-dim of ROI
spread_y                  real           cm       (3006, 0050)     Max distance in y-dim of ROI
spread_z                  real           cm       (3006, 0050)     Max distance in z-dim of ROI
cross_section_max         real           cm²      --               DVHA custom function with Shapely
cross_section_median      real           cm²      --               DVHA custom function with Shapely
toxicity_grade            smallint       --       --               Not yet implemented
centroid_dist_to_iso_min  --             --       --               DVHA custom function
centroid_dist_to_iso_max  --             --       --               DVHA custom function
========================  =============  =======  ==============   ==========================================


Plans
-----

Storage of information applicable across an entire plan / StudyInstanceUID.

========================  =============  =======  ==============   ==========================================
Column                    Data Type       Units   DICOM Tag        Description
========================  =============  =======  ==============   ==========================================
mrn                       text           --       (0010, 0020)     Medical Record Number (PatientID)
study_instance_uid        text           --       (0020, 000d)     Unique ID tied to planning image set
birth_date                date           --       (0010, 0030)     --
age                       smallint       years    --               Patient age on day of simulation
patient_sex               char(1)        --       (0010, 0040)     Patient's sex
sim_study_date            date           --       (0008, 0020)     Date of simulation imaging
physician                 varchar(50)    --       (0010, 0048)     PhysiciansOfRecord or
--                        --             --       (0008, 0090)     ReferringPhysiciansName
tx_site                   varchar(50)    --       (300a, 0002)     RTPlanLabel
rx_dose                   real           Gy       (300a, 0026)     TargetPrescriptionDose
fxs                       int            --       (300a, 0078)     NumberOfFractionsPlanned
patient_orientation       varchar(3)     --       (0018, 5100)     Acronym of patient's sim orientation
plan_time_stamp           timestamp      --       (300a, 0006)     Timestamp for plan
--                        --             --       (300a, 0007)     Timestamp for plan
struct_time_stamp         timestamp      --       (3006, 0008)     Timestamp for structure set
--                        --             --       (3006, 0009)     Timestamp for structure set
dose_time_stamp           timestamp      --       (3006, 0012)     Timestamp for dose file
--                        --             --       (3006, 0013)     Timestamp for structure set
tps_manufacturer          varchar(50)    --       (0008, 0070)     Manufacturer in RTPlan
tps_software_name         varchar(50)    --       (0008, 1090)     ManufacturerModelName in RTPlan
tps_software_version      varchar(30)    --       (0018, 1020)     CSV of SoftwareVersions in RTPlan
tx_modality               varchar(30)    --       (300a, 00c6)     Based on RadiationType, includes 3D or arc
--                        --             --       (300a, 011e)     --
tx_time                   time           --       (300a, 0286)     For brachy plans
total_mu                  real           --       (300a, 0086)     Total MU to be delivered to the patient
dose_grid_res             varchar(16)    mm       (0028, 0030)     Resolution of dose grid
--                        --             --       (0018, 0050)     --
heterogeneity_correction  varchar(30)    --       (3004, 0014)     CSV of heterogeneity correction
baseline                  boolean        --       --               Not yet implemented
import_time_stamp         timestamp      --       --               Time per SQL at time of import
toxicity_grades           text           --       --               Not yet implemented
protocol                  text           --       --               Not yet implemented
complexity                real           --       --               Plan complexity score
ptv_cross_section_max     real           cm²      --               Area of largest PTV slice for plan
ptv_cross_section_median  real           cm²      --               Median slice area of PTV for plan
ptv_spread_x              real           cm       --               Largest x-dim distance of PTV for plan
ptv_spread_y              real           cm       --               Largest y-dim distance of PTV for plan
ptv_spread_z              real           cm       --               Largest z-dim distance of PTV for plan
ptv_surface_area          real           cm²      --               Surface area of PTV for plan
ptv_volume                real           cm³      --               Volume of PTV for plan
ptv_max_dose              real           Gy       --               per dicompyler-core
ptv_min_dose              real           Gy       --               per dicompyler-core
========================  =============  =======  ==============   ==========================================


Rxs
---

Storage of information for a given prescription.

======================  =============  =======  ==============   ==========================================
Column                  Data Type       Units   DICOM Tag        Description
======================  =============  =======  ==============   ==========================================
mrn                     text           --       (0010, 0020)     Medical Record Number (PatientID)
study_instance_uid      text           --       (0020, 000d)     Unique ID tied to planning image set
plan_name               varchar(50)    --       (300A, 0002)     --
fx_grp_name             varchar(30)    --       (300A, 0071)     Primarily for Pinnacle with special POIs
fx_grp_number           smallint       --       (300A, 0071)     --
fx_grp_count            smallint       --       --               Number of fraction groups in RTPlan
fx_dose                 real           --       --               rx_dose / fxs
fxs                     smallint       --       (300A, 0078)     --
rx_dose                 real           --       (300A, 0026)     Per dicompyler if not found
rx_percent              real           --       --               Currently only available with special POIs
normalization_method    varchar(30)    --       (300A, 0014)     --
normalization_object    varchar(30)    --       --               Intended for special POIs
import_time_stamp       timestamp      --       --               Time per SQL at time of import
======================  =============  =======  ==============   ==========================================


Beams
-----

Storage of information per beam.

======================  =============  =======  ==============   ==========================================
Column                  Data Type       Units   DICOM Tag        Description
======================  =============  =======  ==============   ==========================================
mrn                     text           --       (0010, 0020)     Medical Record Number (PatientID)
study_instance_uid      text           --       (0020, 000d)     Unique ID tied to planning image set
beam_number             int            --       (300A, 00C0)     --
beam_name               varchar(30)    --       (300A, 00C3)     Beam Description or
--                      --             --       (300A, 00C2)     Beam Name
fx_grp_number           smallint       --       --               See Rxs table
fx_count                int            --       --               See Rxs table
fx_grp_beam_count       smallint       --       --               See Rxs table
beam_dose               real           --       (300A, 008B)     --
beam_mu                 real           --       (300A, 0086)     --
radiation_type          varchar(30)    --       (300A, 00C6)     --
beam_energy_min         real           --       (300A, 0114)     --
beam_energy_max         real           --       (300A, 0114)     --
beam_type               varchar(30)    --       (300A, 00C4)     --
control_point_count     int            --       --               --
gantry_start            real           --       (300A, 011E)     --
gantry_end              real           --       (300A, 011E)     --
gantry_range            real           --       (300A, 011E)     --
gantry_min              real           --       (300A, 011E)     --
gantry_max              real           --       (300A, 011E)     --
gantry_rot_dir          varchar(5)     --       (300A, 011F)     --
collimator_start        real           --       (300A, 0120)     --
collimator_end          real           --       (300A, 0120)     --
collimator_range        real           --       (300A, 0120)     --
collimator_min          real           --       (300A, 0120)     --
collimator_max          real           --       (300A, 0120)     --
collimator_rot_dir      varchar(5)     --       (300A, 0121)     --
couch_start             real           --       (300A, 0122)     --
couch_end               real           --       (300A, 0120)     --
couch_range             real           --       (300A, 0120)     --
couch_min               real           --       (300A, 0120)     --
couch_max               real           --       (300A, 0120)     --
couch_rot_dir           varchar(5)     --       (300A, 0123)     --
beam_dose_pt            varchar(35)    --       (300A, 0082)     --
isocenter               varchar(35)    --       (300A, 012C)     --
ssd                     real           --       (300A, 0130)     Average of these values
treatment_machine       varchar(30)    --       (300A, 00B2)     --
scan_mode               varchar(30)    --       (300A, 0308)     --
scan_spot_count         real           --       (300A, 0392)     --
beam_mu_per_deg         real           --       --               --
beam_mu_per_cp          real           --       --               --
import_time_stamp       timestamp      --       --               Time per SQL at time of import
area_min                real           --       --               --
area_mean               real           --       --               --
area_median             real           --       --               --
area_max                real           --       --               --
x_perim_min             real           --       --               --
x_perim_mean            real           --       --               --
x_perim_median          real           --       --               --
x_perim_max             real           --       --               --
y_perim_min             real           --       --               --
y_perim_mean            real           --       --               --
y_perim_median          real           --       --               --
y_perim_max             real           --       --               --
complexity_min          real           --       --               --
complexity_mean         real           --       --               --
complexity_median       real           --       --               --
complexity_max          real           --       --               --
cp_mu_min               real           --       --               --
cp_mu_mean              real           --       --               --
cp_mu_median            real           --       --               --
cp_mu_max               real           --       --               --
complexity              real           --       --               --
tx_modality             varchar(30)    --       --               --
perim_min               real           --       --               --
perim_mean              real           --       --               --
perim_median            real           --       --               --
perim_max               real           --       --               --
======================  =============  =======  ==============   ==========================================


