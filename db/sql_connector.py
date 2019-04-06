#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Tools used to interact with SQL database
Created on Sat Mar  4 11:33:10 2017
@author: Dan Cutright, PhD
"""

import os
import psycopg2
from datetime import datetime
from paths import SCRIPT_DIR, DATA_DIR, SQL_CNF_PATH, parse_settings_file


class DVH_SQL:
    def __init__(self, *config):
        if config:
            config = config[0]
        else:
            # Read SQL configuration file
            config = parse_settings_file(SQL_CNF_PATH)

        self.dbname = config['dbname']

        cnx = psycopg2.connect(**config)

        self.cnx = cnx
        self.cursor = cnx.cursor()
        self.tables = ['DVHs', 'Plans', 'Rxs', 'Beams', 'DICOM_Files']

    def close(self):
        self.cnx.close()

    # Executes lines within text file named 'sql_file_name' to SQL
    def execute_file(self, sql_file_name):

        for line in open(sql_file_name):
            if not line.startswith('--'):  # ignore commented lines
                self.cursor.execute(line)
        self.cnx.commit()

    def execute_str(self, command_str):
        for line in command_str.split('\n'):
            if line:
                self.cursor.execute(line)
        self.cnx.commit()

    def check_table_exists(self, table_name):

        self.cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = '{0}'
            """.format(table_name.replace('\'', '\'\'')))
        if self.cursor.fetchone()[0] == 1:
            return True
        else:
            return False

    def query(self, table_name, return_col_str, *condition_str, **kwargs):
        order, order_by = None, None
        if kwargs:
            if 'order' in kwargs:
                order = kwargs['order']
            if 'order_by' in kwargs:
                order_by = kwargs['order_by']
                if not order:
                    order = 'ASC'

        query = "Select %s from %s;" % (return_col_str, table_name)
        if condition_str and condition_str[0]:
            query = "Select %s from %s where %s;" % (return_col_str, table_name, condition_str[0])
        if order and order_by:
            query = "%s Order By %s %s;" % (query[:-1], order_by, order)

        self.cursor.execute(query)
        results = self.cursor.fetchall()

        if 'bokeh_cds' in kwargs and kwargs['bokeh_cds']:
            keys = [c.strip() for c in return_col_str.split(',')]
            results = {key: [results[r][i] for r in range(len(results))] for i, key in enumerate(keys)}
            for key in list(results):
                if 'time' in key or 'date' in key:
                    results[key] = [str(value) for value in results[key]]

        return results

    def query_generic(self, query_str):
        self.cursor.execute(query_str)
        return self.cursor.fetchall()

    def update(self, table_name, column, value, condition_str):

        try:
            temp = float(value)
            value_is_numeric = True
        except ValueError:
            value_is_numeric = False

        if '::date' in str(value):
            value = "'%s'::date" % value.strip('::date')  # augment value string for postgresql date formatting
        elif value_is_numeric:
            value = str(value)
        elif 'null' == str(value.lower()):
            value = "NULL"
        else:
            value = "'%s'" % str(value)  # need quotes to input a string

        update = "Update %s SET %s = %s WHERE %s" % (table_name, column, value, condition_str)
        self.cursor.execute(update)
        self.cnx.commit()

    def is_study_instance_uid_in_table(self, table_name, study_instance_uid):
        query = "Select study_instance_uid from %s where study_instance_uid = '%s';" % (table_name, study_instance_uid)
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        return bool(results)

    def insert_dvhs(self, dvh_table):
        print('Inserting dvh_table')
        file_path = 'insert_values_DVHs.sql'

        if os.path.isfile(file_path):
            os.remove(file_path)

        col_names = ['mrn', 'study_instance_uid', 'institutional_roi', 'physician_roi', 'roi_name', 'roi_type',
                     'volume', 'min_dose', 'mean_dose', 'max_dose', 'dvh_string', 'roi_coord_string',
                     'dist_to_ptv_min', 'dist_to_ptv_mean', 'dist_to_ptv_median', 'dist_to_ptv_max', 'surface_area',
                     'ptv_overlap', 'centroid', 'spread_x', 'spread_y', 'spread_z', 'cross_section_max',
                     'cross_section_median', 'import_time_stamp', 'toxicity_grade']

        # Import each ROI from ROI_PyTable, append to output text file
        if max(dvh_table.ptv_number) > 1:
            multi_ptv = True
        else:
            multi_ptv = False
        for x in range(dvh_table.count):
            if multi_ptv and dvh_table.ptv_number[x] > 0:
                dvh_table.roi_type[x] = 'PTV' + str(dvh_table.ptv_number[x])

            values = [str(dvh_table.mrn[x]),
                      str(dvh_table.study_instance_uid[x]),
                      dvh_table.institutional_roi[x],
                      dvh_table.physician_roi[x],
                      dvh_table.roi_name[x].replace("'", "`"),
                      dvh_table.roi_type[x],
                      str(round(dvh_table.volume[x], 3)),
                      str(round(dvh_table.min_dose[x], 2)),
                      str(round(dvh_table.mean_dose[x], 2)),
                      str(round(dvh_table.max_dose[x], 2)),
                      dvh_table.dvh_str[x],
                      dvh_table.roi_coord[x],
                      '(NULL)',
                      '(NULL)',
                      '(NULL)',
                      '(NULL)',
                      str(round(dvh_table.surface_area[x], 2)),
                      '(NULL)',
                      dvh_table.centroid[x],
                      str(round(dvh_table.spread_x[x], 3)),
                      str(round(dvh_table.spread_y[x], 3)),
                      str(round(dvh_table.spread_z[x], 3)),
                      str(round(dvh_table.cross_section_max[x], 3)),
                      str(round(dvh_table.cross_section_median[x], 3)),
                      'NOW()',
                      'NULL']

            cmd = "INSERT INTO DVHs (%s) VALUES ('%s');\n" % \
                  (','.join(col_names), "','".join(values).replace("'(NULL)'", "(NULL)"))
            cmd = cmd.replace("'NULL'", "NULL")  # toxicity

            with open(file_path, "a") as text_file:
                text_file.write(cmd)

        self.execute_file(file_path)
        os.remove(file_path)
        print('DVHs imported')

        write_import_errors(dvh_table)

    # Used in DVHA >0.6
    def insert_row(self, table, row):
        """
        :param table: SQL table name
        :param row: data returned from DICOM_Parser.get_blank_row()
        """
        columns = list(row)

        values = []
        for column in columns:
            if row[column] is None or row[column][0] is None or row[column][0] == '':
                if 'date' in column or column == 'timestamp':
                    values.append("'%s'" % str(datetime.now()))
                else:
                    values.append("NULL")
            else:
                if 'varchar' in row[column][1]:
                    max_length = int(row[column][1].replace('varchar(', '').replace(')', ''))
                    values.append("'%s'" % truncate_string(row[column][0], max_length))
                else:
                    values.append("'%s'" % row[column][0])

        cmd = "INSERT INTO %s (%s) VALUES (%s);\n" % (table, ','.join(columns), ",".join(values))
        self.execute_str(cmd)

    def insert_plan(self, plan):
        file_path = 'insert_plan_' + plan.mrn + '.sql'

        if os.path.isfile(file_path):
            os.remove(file_path)

        # Import each ROI from ROI_PyTable, append to output text file
        col_names = ['mrn', 'study_instance_uid', 'birth_date', 'age', 'patient_sex', 'sim_study_date', 'physician',
                     'tx_site', 'rx_dose', 'fxs', 'patient_orientation', 'plan_time_stamp', 'struct_time_stamp',
                     'dose_time_stamp', 'tps_manufacturer', 'tps_software_name', 'tps_software_version', 'tx_modality',
                     'tx_time', 'total_mu', 'dose_grid_res', 'heterogeneity_correction', 'baseline',
                     'import_time_stamp', 'toxicity_grades', 'protocol']
        plan.physician = truncate_string(plan.physician, 50)
        plan.tx_site = truncate_string(plan.tx_site, 50)
        plan.tps_manufacturer = truncate_string(plan.tps_manufacturer, 50)
        plan.tps_software_name = truncate_string(plan.tps_software_name, 50)
        plan.tps_software_version = truncate_string(plan.tps_software_version, 30)
        values = [str(plan.mrn),
                  plan.study_instance_uid,
                  str(plan.birth_date),
                  str(plan.age),
                  plan.patient_sex,
                  str(plan.sim_study_date),
                  plan.physician,
                  plan.tx_site,
                  str(plan.rx_dose),
                  str(plan.fxs),
                  plan.patient_orientation,
                  str(plan.plan_time_stamp),
                  str(plan.struct_time_stamp),
                  str(plan.dose_time_stamp),
                  plan.tps_manufacturer,
                  plan.tps_software_name,
                  str(plan.tps_software_version),
                  plan.tx_modality,
                  str(plan.tx_time),
                  str(plan.total_mu),
                  plan.dose_grid_resolution,
                  plan.heterogeneity_correction,
                  'false',
                  'NOW()',
                  "(NULL)",
                  "(NULL)"]

        cmd = "INSERT INTO Plans (%s) VALUES ('%s');\n" % \
              (','.join(col_names), "','".join(values).replace("'(NULL)'", "(NULL)"))

        with open(file_path, "a") as text_file:
            text_file.write(cmd)

        self.execute_file(file_path)
        os.remove(file_path)
        print('Plan imported')

        write_import_errors(plan)

    def insert_beams(self, beams):
        file_path = 'insert_values_beams.sql'

        if os.path.isfile(file_path):
            os.remove(file_path)

        col_names = ['mrn', 'study_instance_uid', 'beam_number', 'beam_name', 'fx_grp_number', 'fx_count',
                     'fx_grp_beam_count', 'beam_dose', 'beam_mu', 'radiation_type', 'beam_energy_min',
                     'beam_energy_max', 'beam_type', 'control_point_count', 'gantry_start', 'gantry_end',
                     'gantry_rot_dir', 'gantry_range', 'gantry_min', 'gantry_max', 'collimator_start', 'collimator_end',
                     'collimator_rot_dir', 'collimator_range', 'collimator_min', 'collimator_max', 'couch_start',
                     'couch_end', 'couch_rot_dir', 'couch_range', 'couch_min', 'couch_max', 'beam_dose_pt', 'isocenter',
                     'ssd', 'treatment_machine', 'scan_mode', 'scan_spot_count', 'beam_mu_per_deg', 'beam_mu_per_cp',
                     'import_time_stamp', 'area_min', 'area_mean', 'area_median', 'area_max', 'x_perim_min',
                     'x_perim_mean', 'x_perim_median', 'x_perim_max', 'y_perim_min', 'y_perim_mean', 'y_perim_median',
                     'y_perim_max', 'complexity_min', 'complexity_mean', 'complexity_median', 'complexity_max',
                     'complexity', 'cp_mu_min', 'cp_mu_mean', 'cp_mu_median', 'cp_mu_max']

        # Import each ROI from ROI_PyTable, append to output text file
        for x in range(beams.count):

            if beams.beam_mu[x] > 0:
                values = [str(beams.mrn[x]),
                          str(beams.study_instance_uid[x]),
                          str(beams.beam_number[x]),
                          beams.beam_name[x].replace("'", "`"),
                          str(beams.fx_group[x]),
                          str(beams.fxs[x]),
                          str(beams.fx_grp_beam_count[x]),
                          str(round(beams.beam_dose[x], 3)),
                          str(beams.beam_mu[x]),
                          beams.radiation_type[x],
                          str(round(beams.beam_energy_min[x], 2)),
                          str(round(beams.beam_energy_max[x], 2)),
                          beams.beam_type[x],
                          str(beams.control_point_count[x]),
                          str(beams.gantry_start[x]),
                          str(beams.gantry_end[x]),
                          beams.gantry_rot_dir[x],
                          str(beams.gantry_range[x]),
                          str(beams.gantry_min[x]),
                          str(beams.gantry_max[x]),
                          str(beams.collimator_start[x]),
                          str(beams.collimator_end[x]),
                          beams.collimator_rot_dir[x],
                          str(beams.collimator_range[x]),
                          str(beams.collimator_min[x]),
                          str(beams.collimator_max[x]),
                          str(beams.couch_start[x]),
                          str(beams.couch_end[x]),
                          beams.couch_rot_dir[x],
                          str(beams.couch_range[x]),
                          str(beams.couch_min[x]),
                          str(beams.couch_max[x]),
                          beams.beam_dose_pt[x],
                          beams.isocenter[x],
                          str(beams.ssd[x]),
                          beams.treatment_machine[x],
                          beams.scan_mode[x],
                          str(beams.scan_spot_count[x]),
                          str(beams.beam_mu_per_deg[x]),
                          str(beams.beam_mu_per_cp[x]),
                          'NOW()',
                          str(beams.area_min[x]), str(beams.area_mean[x]), str(beams.area_median[x]), str(beams.area_max[x]),
                          str(beams.x_perim_min[x]), str(beams.x_perim_mean[x]), str(beams.x_perim_median[x]), str(beams.x_perim_max[x]),
                          str(beams.y_perim_min[x]), str(beams.y_perim_mean[x]), str(beams.y_perim_median[x]), str(beams.y_perim_max[x]),
                          str(beams.complexity_min[x]), str(beams.complexity_mean[x]), str(beams.complexity_median[x]), str(beams.complexity_max[x]), str(beams.complexity[x]),
                          str(beams.cp_mu_min[x]), str(beams.cp_mu_mean[x]), str(beams.cp_mu_median[x]), str(beams.cp_mu_max[x])]
                sql_input = "INSERT INTO Beams (%s) VALUES ('%s');\n" % \
                            (','.join(col_names), "','".join(values).replace("'(NULL)'", "(NULL)"))
                sql_input = sql_input.replace("'NULL'", "NULL")  # complexity related values if mlc_analyzer fails

                with open(file_path, "a") as text_file:
                    text_file.write(sql_input)

        if os.path.isfile(file_path):
            self.execute_file(file_path)
            os.remove(file_path)
        print('Beams imported')

        write_import_errors(beams)

    def insert_rxs(self, rx_table):

        file_path = 'insert_values_rxs.sql'

        if os.path.isfile(file_path):
            os.remove(file_path)

        col_names = ['mrn', 'study_instance_uid', 'plan_name', 'fx_grp_name', 'fx_grp_number', 'fx_grp_count',
                     'fx_dose', 'fxs', 'rx_dose', 'rx_percent', 'normalization_method', 'normalization_object',
                     'import_time_stamp']

        rx_table.plan_name = truncate_string(rx_table.plan_name, 50)
        rx_table.fx_grp_name = truncate_string(rx_table.fx_grp_name, 30)

        for x in range(rx_table.count):
            values = [str(rx_table.mrn[x]),
                      str(rx_table.study_instance_uid[x]),
                      str(rx_table.plan_name[x]).replace("'", "`"),
                      str(rx_table.fx_grp_name[x]),
                      str(rx_table.fx_grp_number[x]),
                      str(rx_table.fx_grp_count[x]),
                      str(round(rx_table.fx_dose[x], 2)),
                      str(int(float(rx_table.fxs[x]))),
                      str(round(rx_table.rx_dose[x], 2)),
                      str(round(rx_table.rx_percent[x], 1)),
                      str(rx_table.normalization_method[x]),
                      str(rx_table.normalization_object[x]).replace("'", "`"),
                      'NOW()']
            sql_input = "INSERT INTO Rxs (%s) VALUES ('%s');\n" % (','.join(col_names), "','".join(values))

            with open(file_path, "a") as text_file:
                text_file.write(sql_input)

        self.execute_file(file_path)
        os.remove(file_path)
        print('Rxs imported')

        write_import_errors(rx_table)

    def insert_dicom_file_row(self, mrn, uid, dir_name, plan_file, struct_file, dose_file):

        col_names = ['mrn', 'study_instance_uid', 'folder_path', 'plan_file', 'structure_file', 'dose_file',
                     'import_time_stamp']
        values = [mrn, uid, dir_name, plan_file, struct_file, dose_file]
        sql_cmd = "INSERT INTO DICOM_Files (%s) VALUES ('%s', NOW());\n" % \
                  (','.join(col_names), "','".join(values).replace("'(NULL)'", "(NULL)"))
        self.cursor.execute(sql_cmd)
        self.cnx.commit()

    def delete_rows(self, condition_str, ignore_table=[]):
        tables = [t for t in self.tables if t not in ignore_table]
        for table in tables:
            self.cursor.execute("DELETE FROM %s WHERE %s;" % (table, condition_str))
            self.cnx.commit()

    def change_mrn(self, old, new):
        condition = "mrn = '%s'" % old
        for table in self.tables:
            self.update(table, 'mrn', new, condition)

    def change_uid(self, old, new):
        condition = "study_instance_uid = '%s'" % old
        for table in self.tables:
            self.update(table, 'study_instance_uid', new, condition)

    def delete_dvh(self, roi_name, study_instance_uid):
        self.cursor.execute("DELETE FROM DVHs WHERE roi_name = '%s' and study_instance_uid = '%s';"
                            % (roi_name, study_instance_uid))
        self.cnx.commit()

    def drop_tables(self):
        print('Dropping tables')
        for table in self.tables:
            self.cursor.execute("DROP TABLE IF EXISTS %s;" % table)
            self.cnx.commit()

    def drop_table(self, table):
        print("Dropping table: %s" % table)
        self.cursor.execute("DROP TABLE IF EXISTS %s;" % table)
        self.cnx.commit()

    def initialize_database(self):
        abs_file_path = os.path.join(SCRIPT_DIR, 'preferences', 'create_tables.sql')
        self.execute_file(abs_file_path)

    def reinitialize_database(self):
        self.drop_tables()
        self.initialize_database()

    def does_db_exist(self):
        # Check if database exists
        line = "SELECT datname FROM pg_catalog.pg_database WHERE lower(datname) = lower('%s');" % self.dbname
        self.cursor.execute(line)

        return bool(len(self.cursor.fetchone()))

    def is_sql_table_empty(self, table):
        line = "SELECT COUNT(*) FROM %s;" % table
        self.cursor.execute(line)
        count = self.cursor.fetchone()[0]
        return not(bool(count))

    def get_unique_values(self, table, column, *condition, **kwargs):
        if condition and condition[0]:
            query = "select distinct %s from %s where %s;" % (column, table, str(condition[0]))
        else:
            query = "select distinct %s from %s;" % (column, table)
        self.cursor.execute(query)
        cursor_return = self.cursor.fetchall()
        if 'ignore_null' in kwargs and kwargs['ignore_null']:
            unique_values = [str(uv[0]) for uv in cursor_return if str(uv[0])]
        else:
            unique_values = [str(uv[0]) for uv in cursor_return]

        unique_values.sort()
        return unique_values

    def get_column_names(self, table_name):
        query = "select column_name from information_schema.columns where table_name = '%s';" % table_name.lower()
        self.cursor.execute(query)
        cursor_return = self.cursor.fetchall()
        columns = [str(c[0]) for c in cursor_return]
        columns.sort()
        return columns

    def get_min_value(self, table, column):
        query = "SELECT MIN(%s) FROM %s;" % (column, table)
        self.cursor.execute(query)
        cursor_return = self.cursor.fetchone()
        return cursor_return[0]

    def get_max_value(self, table, column):
        query = "SELECT MAX(%s) FROM %s;" % (column, table)
        self.cursor.execute(query)
        cursor_return = self.cursor.fetchone()
        return cursor_return[0]

    def get_roi_count_from_query(self, uid=None, dvh_condition=None):
        if uid:
            condition = "study_instance_uid in ('%s')" % "', '".join(dvh_condition)
            if dvh_condition:
                condition = " and " + condition
        else:
            condition = ''

        if dvh_condition:
            condition = dvh_condition + condition

        return len(self.query('DVHs', 'mrn', condition))

    def update_sql_tables(self):
        self.get_column_names('DVHs')

    def is_uid_imported(self, uid):
        for table in self.tables:
            if self.is_study_instance_uid_in_table(table, uid):
                return True
        return False


def write_import_errors(obj):
    detail_col = [c for c in ['beam_name', 'roi_name', 'plan_name'] if hasattr(obj, c)]
    file_path = os.path.join(DATA_DIR, 'import_warning_log.txt')
    with open(file_path, "a") as warning_log:
        for key, value in obj.__dict__.items():
            if not key.startswith("__"):
                if type(value) == list:  # beams, rxs, and dvhs tables will be lists here
                    for i in range(len(value)):
                        if getattr(obj, key)[i] == '(NULL)':
                            detail = "%s %s" % (detail_col[0], getattr(obj, detail_col[0])[i])
                            line = "%s %s: %s: %s is NULL\n" % (str(datetime.now()).split('.')[0],
                                                                obj.mrn[i], detail, key)
                            warning_log.write(line)

                else:  # this only occurs if obj is plans table data
                    if value == '(NULL)':
                        line = "%s %s: plan %s: %s is NULL\n" % (str(datetime.now()).split('.')[0],
                                                                 obj.mrn, obj.tx_site, key)
                        warning_log.write(line)


def truncate_string(input_string, character_limit):
    if len(input_string) > character_limit:
        return input_string[0:(character_limit-1)]
    return input_string
