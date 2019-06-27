#!/usr/bin/env python
# -*- coding: utf-8 -*-

# db.sql_connector.py
"""
Tools used to communicate with the SQL database
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import psycopg2
from psycopg2 import OperationalError
from datetime import datetime
from dvha.paths import SQL_CNF_PATH, CREATE_SQL_TABLES, parse_settings_file
from dvha.tools.errors import SQLError


class DVH_SQL:
    """
    This class is used to communicate to the SQL database to limit the need for syntax in other files
    """
    def __init__(self, *config):
        """
        :param config: optional SQL login credentials, stored values used if nothing provided
        """
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
        """
        Close the SQL DB connection
        """
        self.cnx.close()

    def execute_file(self, sql_file_name):
        """
        Executes lines within provided text file to SQL
        :param sql_file_name: absolute file path of a text file containing SQL commands
        :type sql_file_name: str
        """

        for line in open(sql_file_name):
            if not line.startswith('--'):  # ignore commented lines
                self.cursor.execute(line)
        self.cnx.commit()

    def execute_str(self, command_str):
        """
        Execute and commit a string in proper SQL syntax, can handle multiple lines split by \n
        :param command_str: command or commands to be executed and committed
        :type command_str: str
        """
        for line in command_str.split('\n'):
            if line:
                self.cursor.execute(line)
        self.cnx.commit()

    def check_table_exists(self, table_name):
        """
        :param table_name: the SQL table to check
        :return: existence of specified table
        :rtype: bool
        """

        self.cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = '{0}'
            """.format(table_name.replace('\'', '\'\'')))
        return self.cursor.fetchone()[0] == 1

    def query(self, table_name, return_col_str, *condition_str, **kwargs):
        """
        A generalized query function for DVHA
        :param table_name: 'DVHs', 'Plans', 'Rxs', 'Beams', or 'DICOM_Files'
        :type table_name: str
        :param return_col_str: a csv of SQL columns to be returned
        :type return_col_str: str
        :param condition_str: a condition in SQL syntax
        :type condition_str: str
        :param kwargs: optional parameters order, order_by, and bokeh_cds
        :return: results of the query

        kwargs:
            order: specify order direction (ASC or DESC)
            order_by: the column order is applied to
            bokeh_cds: structure data into a format readily accepted by bokeh's ColumnDataSource.data
        """
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
        """
        A generic query function that executes the provided string
        :param query_str: SQL command
        :type query_str: str
        :return: query results
        """
        self.cursor.execute(query_str)
        return self.cursor.fetchall()

    @property
    def now(self):
        """
        This function is useful for store a timestamp to be used for deleting all data since this return
        For example, a user canceling an import
        :return: The current time as seen by the SQL database
        :rtype: datetime
        """
        return self.query_generic("Select NOW()")[0][0]

    def update(self, table_name, column, value, condition_str):
        """
        Change the data in the database.
        :param table_name: 'DVHs', 'Plans', 'Rxs', 'Beams', or 'DICOM_Files'
        :type table_name: str
        :param column: SQL column to be updated
        :type column: str
        :param value: value to be set
        :type value: str
        :param condition_str: a condition in SQL syntax
        :type condition_str: str
        """

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
        except Exception as e:
            raise SQLError(str(e), update)

    def is_study_instance_uid_in_table(self, table_name, study_instance_uid):
        return self.is_value_in_table(table_name, study_instance_uid, 'study_instance_uid')

    def is_mrn_in_table(self, table_name, mrn):
        return self.is_value_in_table(table_name, mrn, 'mrn')

    def is_value_in_table(self, table_name, value, column):
        query = "Select Distinct %s from %s where %s = '%s';" % (column, table_name, column, value)
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        return bool(results)

    def insert_row(self, table, row):
        """
        Generic function to import data to the database
        :param table: SQL table name
        :type table: str
        :param row: data returned from DICOM_Parser.get_<table>_row()
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

    def insert_data_set(self, data_set):
        """
        Insert an entire data set for a plan
        :param data_set: a dication of data with table names for keys, and a list of row data for values
        :type data_set: dict
        """
        for key in list(data_set):
            for row in data_set[key]:
                self.insert_row(key, row)

    def get_dicom_file_paths(self, mrn=None, uid=None):
        """
        Lookup the dicom file paths of imported data
        :param mrn: MRN
        :type mrn: str
        :param uid: study instance uid
        :type uid: str
        :return: dicom_file_paths as returned from self.query()
        """
        condition = None
        if uid:
            condition = "study_instance_uid = '%s'" % uid
        elif mrn:
            condition = "mrn = '%s'" % mrn

        if condition is not None:
            columns = 'mrn, study_instance_uid, folder_path, plan_file, structure_file, dose_file'
            return self.query('DICOM_Files', columns, condition, bokeh_cds=True)

    def delete_rows(self, condition_str, ignore_tables=None):
        """
        Delete all rows from all tables not in ignore_table for a given condition. Useful when deleting a plan/patient
        :param condition_str: a condition in SQL syntax
        :type condition_str: str
        :param ignore_tables: tables to be excluded from row deletions
        :type ignore_tables: list
        """

        tables = set(self.tables)
        if ignore_tables:
            tables = tables - set(ignore_tables)

        for table in tables:
            self.cursor.execute("DELETE FROM %s WHERE %s;" % (table, condition_str))
            self.cnx.commit()

    def change_mrn(self, old, new):
        """
        Edit all mrns in database
        :param old: current mrn
        :type old: str
        :param new: new mrn
        :type new: str
        """
        condition = "mrn = '%s'" % old
        for table in self.tables:
            self.update(table, 'mrn', new, condition)

    def change_uid(self, old, new):
        """
        Edit study instance uids in database
        :param old: current study instance uid
        :type old: str
        :param new: new study instance uid
        :type new: str
        """
        condition = "study_instance_uid = '%s'" % old
        for table in self.tables:
            self.update(table, 'study_instance_uid', new, condition)

    def delete_dvh(self, roi_name, study_instance_uid):
        """
        Delete a specified DVHs table row
        :param roi_name: the roi name for the row to be deleted
        :type roi_name: str
        :param study_instance_uid: the associated study instance uid
        :type study_instance_uid: str
        """
        self.cursor.execute("DELETE FROM DVHs WHERE roi_name = '%s' and study_instance_uid = '%s';"
                            % (roi_name, study_instance_uid))
        self.cnx.commit()

    def ignore_dvh(self, variation, study_instance_uid, unignore=False):
        """
        Change an uncategorized roi name to ignored so that it won't show up in the list of uncategorized rois, so that
        the user doesn't have to evaluate its need everytime they cleanup the misc rois imported
        :param variation: roi name
        :type variation: str
        :param study_instance_uid: the associated study instance uid
        :type study_instance_uid: str
        :param unignore: if set to True, sets the variation to 'uncategorized'
        :type unignore: bool
        """
        physician_roi = ['ignored', 'uncategorized'][unignore]
        self.update('dvhs', 'physician_roi', physician_roi,
                    "roi_name = '%s' and study_instance_uid = '%s'" % (variation, study_instance_uid))

    def drop_tables(self):
        """
        Delete all tables in the database if they exist
        """
        for table in self.tables:
            self.cursor.execute("DROP TABLE IF EXISTS %s;" % table)
            self.cnx.commit()

    def drop_table(self, table):
        """
        Delete a table in the database if it exists
        :param table: SQL table
        :type table: str
        """
        self.cursor.execute("DROP TABLE IF EXISTS %s;" % table)
        self.cnx.commit()

    def initialize_database(self):
        """
        Ensure that all of the latest SQL columns exist in the user's database
        """
        self.execute_file(CREATE_SQL_TABLES)

    def reinitialize_database(self):
        """
        Delete all data and create all tables with latest columns
        """
        self.drop_tables()
        self.initialize_database()

    def does_db_exist(self):
        """
        Check if database exists
        :return: existence of database
        :rtype: bool
        """
        line = "SELECT datname FROM pg_catalog.pg_database WHERE lower(datname) = lower('%s');" % self.dbname
        self.cursor.execute(line)

        return bool(len(self.cursor.fetchone()))

    def is_sql_table_empty(self, table):
        """
        Check if specifed SQL table is empty
        :param table: SQL table
        :type table: str
        :return: True if specified table has no data
        :rtype: bool
        """
        line = "SELECT COUNT(*) FROM %s;" % table
        self.cursor.execute(line)
        count = self.cursor.fetchone()[0]
        return not(bool(count))

    def get_unique_values(self, table, column, *condition, **kwargs):
        """
        Uses SELECT DISTINCT to get distinct values in database
        :param table: SQL table
        :type table: str
        :param column: SQL column
        :type column: str
        :param condition: optional condition in SQL syntax
        :type condition: str
        :param kwargs: option to ignore null values in return
        :return: unique values from database, sorted alphabetically
        :rtype: list
        """
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
        """
        Get all of the column names for a specified table
        :param table_name: SQL table
        :type table_name: str
        :return: column names of specified table, sorted alphabetically
        :rtype: list
        """
        query = "select column_name from information_schema.columns where table_name = '%s';" % table_name.lower()
        self.cursor.execute(query)
        cursor_return = self.cursor.fetchall()
        columns = [str(c[0]) for c in cursor_return]
        columns.sort()
        return columns

    def get_min_value(self, table, column, condition=None):
        """
        Get the minimum value in the database for a given table and column
        :param table: SQL table
        :type table: str
        :param column: SQL column
        :type column: str
        :param condition: optional condition in SQL syntax
        :type condition: str
        :return: single minimum value in database
        """
        return self.get_sql_function_value('MIN', table, column, condition=condition)

    def get_max_value(self, table, column, condition=None):
        """
        Get the maximum value in the database for a given table and column
        :param table: SQL table
        :type table: str
        :param column: SQL column
        :type column: str
        :param condition: optional condition in SQL syntax
        :type condition: str
        :return: single maximum value in database
        """
        return self.get_sql_function_value('MAX', table, column, condition=condition)

    def get_sql_function_value(self, func, table, column, condition=None, first_value_only=True):
        """
        Used by get_min_values and get_max_values
        :param func: SQL compatible function
        :param table: SQL table
        :type table: str
        :param column: SQL column
        :type column: str
        :param condition: optional condition in SQL syntax
        :type condition: str
        :param first_value_only: if true, only return the first value, otherwise all values returned
        :type first_value_only: bool
        :return: value returned by specified function
        """
        if condition:
            query = "SELECT %s(%s) FROM %s WHERE %s;" % (func, column, table, condition)
        else:
            query = "SELECT %s(%s) FROM %s;" % (func, column, table)
        self.cursor.execute(query)
        cursor_return = self.cursor.fetchone()
        if first_value_only:
            return cursor_return[0]
        return cursor_return

    def get_roi_count_from_query(self, uid=None, dvh_condition=None):
        """
        Counts the DVH rows that match the provided conditions
        :param uid: study instance uid
        :type uid: str
        :param dvh_condition: condition in SQL syntax for the DVHs table
        :type dvh_condition: str
        :return: number of DVH rows
        :rtype: int
        """
        if uid:
            condition = "study_instance_uid in ('%s')" % "', '".join(dvh_condition)
            if dvh_condition:
                condition = " and " + condition
        else:
            condition = ''

        if dvh_condition:
            condition = dvh_condition + condition

        return len(self.query('DVHs', 'mrn', condition))

    def is_uid_imported(self, uid):
        """
        Check all tables to see if study instance uid is used
        :param uid: study instance uid
        :type uid: str
        :return: True if study instance uid exists in any table
        :rtype: bool
        """
        for table in self.tables:
            if self.is_study_instance_uid_in_table(table, uid):
                return True
        return False

    def is_mrn_imported(self, mrn):
        """
        Check all tables to see if MRN is used
        :param mrn: MRN
        :type mrn: str
        :return: True if MRN exists in any table
        :rtype: bool
        """
        for table in self.tables:
            if self.is_mrn_in_table(table, mrn):
                return True
        return False

    def is_roi_imported(self, roi_name, study_instance_uid):
        """
        Check if a study is already using a specified roi name
        :param roi_name: roi name to check
        :type roi_name: str
        :param study_instance_uid: restrict search to this study_instance_uid
        :type study_instance_uid: str
        :return: True if the roi name provided has been used in the specified study
        :rtype: bool
        """
        condition = "roi_name = '%s' and study_instance_uid = '%s'" % (roi_name, study_instance_uid)
        roi_names = self.get_unique_values('DVHs', 'roi_name', condition)
        return bool(roi_names)


def truncate_string(input_string, character_limit):
    """
    Used to truncate a string to ensure it may be imported into database
    :param input_string: string to be truncated
    :type input_string: str
    :param character_limit: the maximum number of allowed characters
    :type character_limit: int
    :return: truncated string (removing the trailing characters)
    :rtype: str
    """
    if len(input_string) > character_limit:
        return input_string[0:(character_limit-1)]
    return input_string


def echo_sql_db(config=None):
    """
    Echo the database using stored or provided credentials
    :param config: database login credentials
    :type config: dict
    :return: True if connection could be established
    :rtype: bool
    """
    try:
        if config:
            cnx = DVH_SQL(config)
        else:
            cnx = DVH_SQL()
        cnx.close()
        return True
    except OperationalError:
        return False
