#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Tools used to interact with SQL database
Created on Sat Mar  4 11:33:10 2017
@author: Dan Cutright, PhD
"""

import os
import psycopg2
from psycopg2 import OperationalError
from datetime import datetime
from paths import SCRIPT_DIR, DATA_DIR, SQL_CNF_PATH, parse_settings_file
from tools.errors import SQLError


class DVH_SQL:
    """
    To ensure SQL connection is closed on every use, best practice is to use this class like so:
    with DVH_SQL() as cnx:
        something = cnx.function()
        some_more_code_here
    """
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

    def __enter__(self):
        return self

    def __exit__(self, ctx_type, ctx_value, ctx_traceback):
        self.close()

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

        try:
            self.cursor.execute(query)
            results = self.cursor.fetchall()
        except Exception as e:
            raise SQLError(str(e), query)

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

        try:
            self.cursor.execute(update)
            self.cnx.commit()
            return None
        except Exception as e:
            raise SQLError(str(e), update)

    def is_study_instance_uid_in_table(self, table_name, study_instance_uid):
        return self.is_value_in_table(table_name, study_instance_uid, 'study_instance_uid')

    def is_mrn_in_table(self, table_name, mrn):
        return self.is_value_in_table(table_name, mrn, 'mrn')

    def is_value_in_table(self, table_name, value, column):
        query = "Select %s from %s where %s = '%s';" % (column, table_name, column, value)
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        return bool(results)

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
                if column == 'import_time_stamp':
                    values.append("NOW()")
                else:
                    values.append("NULL")
            else:
                if 'varchar' in row[column][1]:
                    max_length = int(row[column][1].replace('varchar(', '').replace(')', ''))
                    values.append("'%s'" % truncate_string(row[column][0], max_length))
                elif 'time_stamp' in row[column][1]:
                    values.append("'%s'::date" % row[column][0])
                else:
                    values.append("'%s'" % row[column][0])

        cmd = "INSERT INTO %s (%s) VALUES (%s);\n" % (table, ','.join(columns), ",".join(values))
        self.execute_str(cmd)

    def insert_dicom_file_row(self, mrn, uid, dir_name, plan_file, struct_file, dose_file):

        col_names = ['mrn', 'study_instance_uid', 'folder_path', 'plan_file', 'structure_file', 'dose_file',
                     'import_time_stamp']
        values = [mrn, uid, dir_name, plan_file, struct_file, dose_file]
        sql_cmd = "INSERT INTO DICOM_Files (%s) VALUES ('%s', NOW());\n" % \
                  (','.join(col_names), "','".join(values).replace("'(NULL)'", "(NULL)"))
        self.cursor.execute(sql_cmd)
        self.cnx.commit()

    def get_dicom_file_paths(self, mrn=None, uid=None):
        condition = None
        if uid:
            condition = "study_instance_uid = '%s'" % uid
        elif mrn:
            condition = "mrn = '%s'" % mrn

        if condition is not None:
            columns = 'mrn, study_instance_uid, folder_path, plan_file, structure_file, dose_file'
            return self.query('DICOM_Files', columns, condition, bokeh_cds=True)
        return None

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
        for table in self.tables:
            self.cursor.execute("DROP TABLE IF EXISTS %s;" % table)
            self.cnx.commit()

    def drop_table(self, table):
        self.cursor.execute("DROP TABLE IF EXISTS %s;" % table)
        self.cnx.commit()

    def initialize_database(self):
        abs_file_path = os.path.join(SCRIPT_DIR, 'db', 'create_tables.sql')
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

    def get_min_value(self, table, column, condition=None):
        return self.get_sql_function_value('MIN', table, column, condition=condition)

    def get_max_value(self, table, column, condition=None):
        return self.get_sql_function_value('MAX', table, column, condition=condition)

    def get_sql_function_value(self, func, table, column, condition=None):
        if condition:
            query = "SELECT %s(%s) FROM %s WHERE %s;" % (func, column, table, condition)
        else:
            query = "SELECT %s(%s) FROM %s;" % (func, column, table)
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

    def is_mrn_imported(self, mrn):
        for table in self.tables:
            if self.is_mrn_in_table(table, mrn):
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


def echo_sql_db(config=None):
    try:
        if config:
            cnx = DVH_SQL(config)
        else:
            cnx = DVH_SQL()
        cnx.close()
        return True
    except OperationalError:
        return False
