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
study_instance_uid        text           --       (0020, 000D)     Unique ID tied to planning image set
centroid                  varchar(35)    --       --               DVHA custom function
centroid_dist_to_iso_max  --             --       --               DVHA custom function
centroid_dist_to_iso_min  --             --       --               DVHA custom function
cross_section_max         real           cm²      --               DVHA custom function with Shapely
cross_section_median      real           cm²      --               DVHA custom function with Shapely
dist_to_ptv_centroids     real           cm       --               DVHA custom function
dist_to_ptv_max           real           cm       --               Calculated with scipy's cdist function
dist_to_ptv_75            real           cm       --               Calculated with scipy's cdist function
dist_to_ptv_mean          real           cm       --               Calculated with scipy's cdist function
dist_to_ptv_median        real           cm       --               Calculated with scipy's cdist function
dist_to_ptv_25            real           cm       --               Calculated with scipy's cdist function
dist_to_ptv_min           real           cm       --               Calculated with scipy's cdist function
dth_string                text           cm       --               numpy histogram of scipy cdist with PTV
dvh_string                text           cGy      --               CSV of DVH in 1 cGy bins
import_time_stamp         timestamp      --       --               Time per SQL at time of import
institutional_roi         varchar(50)    --       --               Standard ROI name for all physician
max_dose                  real           Gy       --               Max ROI dose per dicompyler
mean_dose                 real           Gy       --               Mean ROI dose per dicompyler
min_dose                  real           Gy       --               Min ROI dose per dicompyler
ovh_max                   real           cm       --               Custom DVHA overlap volume histogram calc
ovh_75                    real           cm       --               Custom DVHA overlap volume histogram calc
ovh_mean                  real           cm       --               Custom DVHA overlap volume histogram calc
ovh_median                real           cm       --               Custom DVHA overlap volume histogram calc
ovh_25                    real           cm       --               Custom DVHA overlap volume histogram calc
ovh_min                   real           cm       --               Custom DVHA overlap volume histogram calc
physician_roi             varchar(50)    --       --               Standard ROI name for patient's physician
ptv_overlap               real           cm³      --               DVHA custom function with Shapely
roi_coord_string          text           --       (3006, 0050)     Single string containing all ROI points
roi_name                  varchar(50)    --       (3006, 0026)     ROI name as in plan
roi_type                  varchar(20)    --       (3006, 00A4)     ROI categegoy (e.g., ORGAN, PTV)
spread_x                  real           cm       (3006, 0050)     Max distance in x-dim of ROI
spread_y                  real           cm       (3006, 0050)     Max distance in y-dim of ROI
spread_z                  real           cm       (3006, 0050)     Max distance in z-dim of ROI
surface_area              real           cm²      --               DVHA custom function, needs validation
toxicity_grade            smallint       --       --               Not yet implemented
volume                    real           cm³      --               ROI volume per dicompyler
integral_dose             real           Gy*cm³   --               ROI mean dose times volume per dicompyler
========================  =============  =======  ==============   ==========================================


Plans
-----

Storage of information applicable across an entire plan / StudyInstanceUID.

========================  =============  =======  ==============   ==========================================
Column                    Data Type       Units   DICOM Tag        Description
========================  =============  =======  ==============   ==========================================
mrn                       text           --       (0010, 0020)     Medical Record Number (PatientID)
study_instance_uid        text           --       (0020, 000D)     Unique ID tied to planning image set
age                       smallint       years    --               Patient age on day of simulation
baseline                  boolean        --       --               Not yet implemented
birth_date                date           --       (0010, 0030)     --
complexity                real           --       --               Plan complexity score
dose_grid_res             varchar(16)    mm       (0028, 0030)     Resolution of dose grid
--                        --             --       (0018, 0050)     --
dose_time_stamp           timestamp      --       (3006, 0012)     Timestamp for dose file
--                        --             --       (3006, 0013)     Timestamp for dose file
fxs                       int            --       (300a, 0078)     NumberOfFractionsPlanned
heterogeneity_correction  varchar(30)    --       (3004, 0014)     CSV of heterogeneity correction
import_time_stamp         timestamp      --       --               Time per SQL at time of import
patient_orientation       varchar(3)     --       (0018, 5100)     Acronym of patient's sim orientation
patient_sex               char(1)        --       (0010, 0040)     Patient's sex
physician                 varchar(50)    --       (0010, 0048)     PhysiciansOfRecord or
--                        --             --       (0008, 0090)     ReferringPhysiciansName
plan_time_stamp           timestamp      --       (300A, 0006)     Timestamp for plan
--                        --             --       (300A, 0007)     Timestamp for plan
protocol                  text           --       --               Not yet implemented
ptv_cross_section_max     real           cm²      --               Area of largest PTV slice for plan
ptv_cross_section_median  real           cm²      --               Median slice area of PTV for plan
ptv_max_dose              real           Gy       --               per dicompyler-core
ptv_min_dose              real           Gy       --               per dicompyler-core
ptv_spread_x              real           cm       --               Largest x-dim distance of PTV for plan
ptv_spread_y              real           cm       --               Largest y-dim distance of PTV for plan
ptv_spread_z              real           cm       --               Largest z-dim distance of PTV for plan
ptv_surface_area          real           cm²      --               Surface area of PTV for plan
ptv_volume                real           cm³      --               Volume of PTV for plan
rx_dose                   real           Gy       (300A, 0026)     TargetPrescriptionDose
sim_study_date            date           --       (0008, 0020)     Date of simulation imaging
struct_time_stamp         timestamp      --       (3006, 0008)     Timestamp for structure set
--                        --             --       (3006, 0009)     Timestamp for structure set
total_mu                  real           --       (300a, 0086)     Total MU to be delivered to the patient
toxicity_grades           text           --       --               Not yet implemented
tps_manufacturer          varchar(50)    --       (0008, 0070)     Manufacturer in RTPlan
tps_software_name         varchar(50)    --       (0008, 1090)     ManufacturerModelName in RTPlan
tps_software_version      varchar(30)    --       (0018, 1020)     CSV of SoftwareVersions in RTPlan
tx_modality               varchar(30)    --       (300A, 00C6)     Based on RadiationType, includes 3D or arc
--                        --             --       (300A, 011E)     --
tx_site                   varchar(50)    --       (300A, 0002)     RTPlanLabel
tx_time                   time           --       (300A, 0286)     For brachy plans
========================  =============  =======  ==============   ==========================================


Rxs
---

Storage of information for a given prescription.

======================  =============  =======  ==============   ==========================================
Column                  Data Type       Units   DICOM Tag        Description
======================  =============  =======  ==============   ==========================================
mrn                     text           --       (0010, 0020)     Medical Record Number (PatientID)
study_instance_uid      text           --       (0020, 000D)     Unique ID tied to planning image set
fx_dose                 real           --       --               rx_dose / fxs
fx_grp_count            smallint       --       --               Number of fraction groups in RTPlan
fx_grp_name             varchar(30)    --       (300A, 0071)     Primarily for Pinnacle with special POIs
fx_grp_number           smallint       --       (300A, 0071)     --
fxs                     smallint       --       (300A, 0078)     --
import_time_stamp       timestamp      --       --               Time per SQL at time of import
normalization_method    varchar(30)    --       (300A, 0014)     --
normalization_object    varchar(30)    --       --               Intended for special POIs
plan_name               varchar(50)    --       (300A, 0002)     --
rx_dose                 real           --       (300A, 0026)     Per dicompyler if not found
rx_percent              real           --       --               Currently only available with special POIs
======================  =============  =======  ==============   ==========================================


Beams
-----

Storage of information per beam.

======================  =============  =======  ==============   ==========================================
Column                  Data Type       Units   DICOM Tag        Description
======================  =============  =======  ==============   ==========================================
mrn                     text           --       (0010, 0020)     Medical Record Number (PatientID)
study_instance_uid      text           --       (0020, 000D)     Unique ID tied to planning image set
area_max                real           --       --               --
area_mean               real           --       --               --
area_median             real           --       --               --
area_min                real           --       --               --
beam_dose               real           --       (300A, 008B)     --
beam_dose_pt            varchar(35)    --       (300A, 0082)     --
beam_energy_max         real           --       (300A, 0114)     --
beam_energy_min         real           --       (300A, 0114)     --
beam_mu                 real           --       (300A, 0086)     --
beam_mu_per_cp          real           --       --               --
beam_mu_per_deg         real           --       --               --
beam_name               varchar(30)    --       (300A, 00C3)     Beam Description or
--                      --             --       (300A, 00C2)     Beam Name
beam_number             int            --       (300A, 00C0)     --
beam_type               varchar(30)    --       (300A, 00C4)     --
collimator_end          real           --       (300A, 0120)     --
collimator_max          real           --       (300A, 0120)     --
collimator_min          real           --       (300A, 0120)     --
collimator_range        real           --       (300A, 0120)     --
collimator_rot_dir      varchar(5)     --       (300A, 0121)     --
collimator_start        real           --       (300A, 0120)     --
complexity              real           --       --               --
complexity_max          real           --       --               --
complexity_mean         real           --       --               --
complexity_median       real           --       --               --
complexity_min          real           --       --               --
control_point_count     int            --       --               --
couch_end               real           --       (300A, 0120)     --
couch_max               real           --       (300A, 0120)     --
couch_min               real           --       (300A, 0120)     --
couch_range             real           --       (300A, 0120)     --
couch_rot_dir           varchar(5)     --       (300A, 0123)     --
couch_start             real           --       (300A, 0122)     --
cp_mu_max               real           --       --               --
cp_mu_mean              real           --       --               --
cp_mu_median            real           --       --               --
cp_mu_min               real           --       --               --
fx_count                int            --       --               See Rxs table
fx_grp_beam_count       smallint       --       --               See Rxs table
fx_grp_number           smallint       --       --               See Rxs table
gantry_end              real           --       (300A, 011E)     --
gantry_max              real           --       (300A, 011E)     --
gantry_min              real           --       (300A, 011E)     --
gantry_range            real           --       (300A, 011E)     --
gantry_rot_dir          varchar(5)     --       (300A, 011F)     --
gantry_start            real           --       (300A, 011E)     --
import_time_stamp       timestamp      --       --               Time per SQL at time of import
isocenter               varchar(35)    --       (300A, 012C)     --
perim_max               real           --       --               --
perim_mean              real           --       --               --
perim_median            real           --       --               --
perim_min               real           --       --               --
radiation_type          varchar(30)    --       (300A, 00C6)     --
scan_mode               varchar(30)    --       (300A, 0308)     --
scan_spot_count         real           --       (300A, 0392)     --
ssd                     real           --       (300A, 0130)     Average of these values
treatment_machine       varchar(30)    --       (300A, 00B2)     --
tx_modality             varchar(30)    --       --               --
x_perim_max             real           --       --               --
x_perim_mean            real           --       --               --
x_perim_median          real           --       --               --
x_perim_min             real           --       --               --
y_perim_max             real           --       --               --
y_perim_mean            real           --       --               --
y_perim_median          real           --       --               --
y_perim_min             real           --       --               --
======================  =============  =======  ==============   ==========================================


