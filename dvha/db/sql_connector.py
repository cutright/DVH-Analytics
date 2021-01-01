#!/usr/bin/env python
# -*- coding: utf-8 -*-

# db.sql_connector.py
"""Tools used to communicate with the SQL database"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

from wx import CallAfter
import psycopg2
import sqlite3
from datetime import datetime
from dateutil.parser import parse as date_parser
from os.path import dirname, join, isfile
from dvha.db.sql_columns import categorical, numerical
from dvha.options import Options
from dvha.paths import CREATE_PGSQL_TABLES, CREATE_SQLITE_TABLES, DATA_DIR
from dvha.tools.errors import SQLError, push_to_log
import json


class DVH_SQL:
    """This class is used to communicate to the SQL database

    Parameters
    ----------
    config : dict
        optional SQL login credentials, stored values used if nothing provided.
        Allowed keys are 'host', 'port', 'dbname', 'user', 'password'
    db_type : str, optional
        either 'pgsql' or 'sqlite'
    group : int, optional
        use a group-specific connection, either 1 or 2
    """

    def __init__(self, *config, db_type=None, group=1):

        stored_options = Options()

        if config:
            self.db_type = db_type if db_type is not None else "pgsql"
            config = config[0]
        else:
            # Read SQL configuration file
            if group == 2 and stored_options.SYNC_SQL_CNX:
                group = 1
            self.db_type = (
                stored_options.DB_TYPE_GRPS[group]
                if db_type is None
                else db_type
            )
            config = stored_options.SQL_LAST_CNX_GRPS[group][self.db_type]

        if self.db_type == "sqlite":
            db_file_path = config["host"]
            if not dirname(
                db_file_path
            ):  # file_path has not directory, assume it lives in DATA_DIR
                db_file_path = join(DATA_DIR, db_file_path)
            self.db_name = None
            self.cnx = sqlite3.connect(db_file_path)
        else:
            self.db_name = config["dbname"]
            self.cnx = psycopg2.connect(**config)

        self.cursor = self.cnx.cursor()
        self.tables = ["DVHs", "Plans", "Rxs", "Beams", "DICOM_Files"]

    def __enter__(self):
        return self

    def __exit__(self, ctx_type, ctx_value, ctx_traceback):
        self.close()

    def close(self):
        """Close the SQL DB connection"""
        self.cnx.close()

    def execute_file(self, sql_file_name):
        """Executes lines within provided text file to SQL

        Parameters
        ----------
        sql_file_name : str
            absolute file path of a text file containing SQL commands

        """

        for line in open(sql_file_name):
            if not line.startswith("--"):  # ignore commented lines
                self.cursor.execute(line)
        self.cnx.commit()

    def execute_str(self, command_str):
        """Execute and commit a string in proper SQL syntax, can handle
        multiple lines split by \n

        Parameters
        ----------
        command_str : str
            command or commands to be executed and committed

        """
        for line in command_str.split("\n"):
            if line:
                self.cursor.execute(line)
        self.cnx.commit()

    def check_table_exists(self, table_name):
        """Check if a table exists

        Parameters
        ----------
        table_name : st
            the SQL table to check

        Returns
        -------
        bool
            True if ``table_name`` exists

        """

        self.cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = '{0}'
            """.format(
                table_name.replace("'", "''")
            )
        )
        return self.cursor.fetchone()[0] == 1

    def query(self, table_name, return_col_str, *condition_str, **kwargs):
        """A generalized query function for DVHA

        Parameters
        ----------
        table_name : str
            DVHs', 'Plans', 'Rxs', 'Beams', or 'DICOM_Files'
        return_col_str : str: str
            a csv of SQL columns to be returned
        condition_str : str: str
            a condition in SQL syntax
        kwargs :
            optional parameters order, order_by, and bokeh_cds

        Returns
        -------
        list, dict
            Returns a list of lists by default, or a dict of lists if
            bokeh_cds in kwargs and is true
        """
        order, order_by = None, None
        if kwargs:
            if "order" in kwargs:
                order = kwargs["order"]
            if "order_by" in kwargs:
                order_by = kwargs["order_by"]
                if not order:
                    order = "ASC"

        query = "Select %s from %s;" % (return_col_str, table_name)
        if condition_str and condition_str[0]:
            query = "Select %s from %s where %s;" % (
                return_col_str,
                table_name,
                condition_str[0],
            )
        if order and order_by:
            query = "%s Order By %s %s;" % (query[:-1], order_by, order)

        try:
            self.cursor.execute(query)
            results = self.cursor.fetchall()
        except Exception as e:
            raise SQLError(str(e), query)

        if "bokeh_cds" in kwargs and kwargs["bokeh_cds"]:
            keys = [c.strip() for c in return_col_str.split(",")]
            results = {
                key: [results[r][i] for r in range(len(results))]
                for i, key in enumerate(keys)
            }
            for key in list(results):
                if "time" in key or "date" in key:
                    results[key] = [str(value) for value in results[key]]

        return results

    def query_generic(self, query_str):
        """A generic query function that executes the provided string

        Parameters
        ----------
        query_str : str
            SQL command

        Returns
        -------
        list
            Results of ``cursor.fetchall()``

        """
        self.cursor.execute(query_str)
        return self.cursor.fetchall()

    @property
    def now(self):
        """Get a datetime object for now

        Returns
        -------
        datetime
            The current time reported by the database

        """
        return self.query_generic("SELECT %s" % self.sql_cmd_now)[0][0]

    @property
    def sql_cmd_now(self):
        """Get the SQL command for now, based on database type

        Returns
        -------
        str
            SQL command for now
        """
        if self.db_type == "sqlite":
            sql_cmd = "strftime('%Y-%m-%d %H:%M:%f', 'now', 'localtime')"
        else:
            sql_cmd = "NOW()"
        return sql_cmd

    def update(self, table_name, column, value, condition_str):
        """Change the data in the database

        Parameters
        ----------
        table_name : str
            DVHs', 'Plans', 'Rxs', 'Beams', or 'DICOM_Files'
        column : str
            SQL column to be updated
        value : str, float, int
            value to be set
        condition_str : str
            a condition in SQL syntax

        """

        try:
            float(value)
            value_is_numeric = True
        except ValueError:
            value_is_numeric = False

        if "::date" in str(value):
            amend_type = ["", "::date"][
                self.db_type == "pgsql"
            ]  # sqlite3 does not support ::date
            value = "'%s'%s" % (
                value.strip("::date"),
                amend_type,
            )  # augment value for postgresql date formatting
        elif value_is_numeric:
            value = str(value)
        elif "null" == str(value.lower()):
            value = "NULL"
        else:
            value = "'%s'" % str(value)  # need quotes to input a string

        update = "Update %s SET %s = %s WHERE %s" % (
            table_name,
            column,
            value,
            condition_str,
        )

        try:
            self.cursor.execute(update)
            self.cnx.commit()
        except Exception as e:
            push_to_log(e, msg="Database update failure!")

    def is_study_instance_uid_in_table(self, table_name, study_instance_uid):
        """Check if a study instance uid exists in the provided table

        Parameters
        ----------
        table_name : str
            SQL table name
        study_instance_uid : str
            study instance uid

        Returns
        -------
        bool
            True if ``study_instance_uid`` exists in the study_instance_uid
            column of ``table_name``
        """
        # As of DVH v0.7.5, study_instance_uid may end with _N where N is the
        # nth plan of a file set
        query = (
            "SELECT DISTINCT study_instance_uid FROM %s WHERE "
            "study_instance_uid LIKE '%s%%';"
            % (table_name, study_instance_uid)
        )
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        return bool(results)

    def is_mrn_in_table(self, table_name, mrn):
        """

        Parameters
        ----------
        table_name : str
            SQL table name
        mrn : str
            medical record number

        Returns
        -------
        bool
            True if ``mrn`` exists in the mrn column of ``table_name``
        """
        return self.is_value_in_table(table_name, mrn, "mrn")

    def is_value_in_table(self, table_name, value, column):
        """Check if a str value exists in a SQL table

        Parameters
        ----------
        table_name : sr
            SQL table name
        value : str
            value of interest (str only)
        column :
            SQL table column

        Returns
        -------
        bool
            True if ``value`` exists in ``table_name.column``

        """
        query = "Select Distinct %s from %s where %s = '%s';" % (
            column,
            table_name,
            column,
            value,
        )
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        return bool(results)

    def insert_row(self, table, row):
        """Generic function to import data to the database

        Parameters
        ----------
        table : str
            SQL table name
        row : dict
            data returned from DICOM_Parser.get_<table>_row()

        """
        columns = list(row)
        allowed_columns = self.get_column_names(table)
        used_columns = []

        values = []
        for column in columns:
            if column in allowed_columns:
                used_columns.append(column)
                if (
                    row[column] is None
                    or row[column][0] is None
                    or row[column][0] == ""
                ):
                    if column == "import_time_stamp":
                        values.append(self.sql_cmd_now)
                    else:
                        values.append("NULL")
                else:
                    value = row[column][0]
                    value_type = row[column][1]

                    if "varchar" in value_type:
                        max_length = int(
                            value_type.replace("varchar(", "").replace(")", "")
                        )
                        values.append(
                            "'%s'" % truncate_string(value, max_length)
                        )

                    elif value_type in {"time_stamp", "date"}:
                        date = date_parser(value)
                        value = date.date()
                        if value_type == "time_stamp":
                            value = "%s %s" % (value, date.time())
                        if (
                            self.db_type == "pgsql"
                        ):  # sqlite3 does not support ::date
                            values.append("'%s'::date" % value)
                        else:
                            values.append("'%s'" % value)

                    else:
                        values.append("'%s'" % value)
            else:
                msg = (
                    "Failed to update SQL column %s in table %s, "
                    "it does not exist" % (column, table)
                )
                push_to_log(msg=msg)

        cmd = "INSERT INTO %s (%s) VALUES (%s);\n" % (
            table,
            ",".join(used_columns),
            ",".join(values),
        )
        self.execute_str(cmd)

    def insert_data_set(self, data_set):
        """Insert an entire data set for a plan

        Parameters
        ----------
        data_set : dict
            a dictionary of data with table names for keys, and a list of row
            data for values

        """
        for key in list(data_set):
            for row in data_set[key]:
                self.insert_row(key, row)

    def get_dicom_file_paths(self, mrn=None, uid=None):
        """Lookup the dicom file paths of imported data

        Parameters
        ----------
        mrn : str, optional
            medical record number
        uid : str, optional
            study instance uid

        Returns
        -------
        list
            Query return from DICOM_Files table

        """
        condition = None
        if uid:
            condition = "study_instance_uid = '%s'" % uid
        elif mrn:
            condition = "mrn = '%s'" % mrn

        if condition is not None:
            columns = (
                "mrn, study_instance_uid, folder_path, plan_file, "
                "structure_file, dose_file"
            )
            return self.query(
                "DICOM_Files", columns, condition, bokeh_cds=True
            )

    def delete_rows(self, condition_str, ignore_tables=None):
        """Delete all rows from all tables not in ignore_table for a given
        condition. Useful when deleting a plan/patient

        Parameters
        ----------
        condition_str : str: str
            a condition in SQL syntax
        ignore_tables : list, optional
            tables to be excluded from row deletions

        """

        tables = set(self.tables)
        if ignore_tables:
            tables = tables - set(ignore_tables)

        for table in tables:
            self.cursor.execute(
                "DELETE FROM %s WHERE %s;" % (table, condition_str)
            )
            self.cnx.commit()

    def change_mrn(self, old, new):
        """Edit all mrns in database

        Parameters
        ----------
        old : str
            current mrn
        new : str
            new mrn

        """
        condition = "mrn = '%s'" % old
        for table in self.tables:
            self.update(table, "mrn", new, condition)

    def change_uid(self, old, new):
        """Edit study instance uids in database

        Parameters
        ----------
        old : str
            current study instance uid
        new : str
            new study instance uid

        """
        condition = "study_instance_uid = '%s'" % old
        for table in self.tables:
            self.update(table, "study_instance_uid", new, condition)

    def delete_dvh(self, roi_name, study_instance_uid):
        """Delete a specified DVHs table row

        Parameters
        ----------
        roi_name : str
            the roi name for the row to be deleted
        study_instance_uid : str
            the associated study instance uid

        """
        self.cursor.execute(
            "DELETE FROM DVHs WHERE roi_name = '%s' and "
            "study_instance_uid = '%s';" % (roi_name, study_instance_uid)
        )
        self.cnx.commit()

    def ignore_dvh(self, variation, study_instance_uid, unignore=False):
        """Change an uncategorized roi name to ignored so that it won't show
        up in the list of uncategorized rois, so that
        the user doesn't have to evaluate its need everytime they cleanup the
        misc rois imported

        Parameters
        ----------
        variation : str
            roi name
        study_instance_uid : str
            the associated study instance uid
        unignore : bool, optional
            if set to True, sets the variation to 'uncategorized'

        """
        physician_roi = ["ignored", "uncategorized"][unignore]
        self.update(
            "dvhs",
            "physician_roi",
            physician_roi,
            "roi_name = '%s' and study_instance_uid = '%s'"
            % (variation, study_instance_uid),
        )

    def drop_tables(self):
        """Delete all tables in the database if they exist"""
        for table in self.tables:
            self.cursor.execute("DROP TABLE IF EXISTS %s;" % table)
            self.cnx.commit()

    def drop_table(self, table):
        """Delete a table in the database if it exists

        Parameters
        ----------
        table : str
            SQL table

        """
        self.cursor.execute("DROP TABLE IF EXISTS %s;" % table)
        self.cnx.commit()

    def initialize_database(self):
        """Ensure that all of the latest SQL columns exist in the database"""
        create_tables_file = [CREATE_PGSQL_TABLES, CREATE_SQLITE_TABLES][
            self.db_type == "sqlite"
        ]
        self.execute_file(create_tables_file)

    def reinitialize_database(self):
        """Delete all data and create all tables with latest columns"""
        self.drop_tables()
        self.vacuum()
        self.initialize_database()

    def vacuum(self):
        """Call to reclaim space in the database"""
        if self.db_type == "sqlite":
            self.cnx.isolation_level = None
            self.cnx.execute("VACUUM")
            self.cnx.isolation_level = ""
        else:
            # TODO: PGSQL VACUUM needs testing
            # self.cnx.execute('VACUUM')
            pass

    def does_db_exist(self):
        """Check if database exists

        Returns
        -------
        bool
            True if the database exists

        """
        if self.db_name:
            line = (
                "SELECT datname FROM pg_catalog.pg_database WHERE "
                "lower(datname) = lower('%s');" % self.db_name
            )
            self.cursor.execute(line)

            return bool(len(self.cursor.fetchone()))
        else:
            return True

    def is_sql_table_empty(self, table):
        """Check if specified SQL table is empty

        Parameters
        ----------
        table : str
            SQL table

        Returns
        -------
        bool
            True if ``table`` is empty

        """
        line = "SELECT COUNT(*) FROM %s;" % table
        self.cursor.execute(line)
        count = self.cursor.fetchone()[0]
        return not (bool(count))

    def get_unique_values(self, table, column, *condition, **kwargs):
        """Uses SELECT DISTINCT to get distinct values in database

        Parameters
        ----------
        table : str
            SQL table
        column : str
            SQL column
        condition : str, optional
            Condition in SQL syntax
        kwargs :
            option to ignore null values in return


        Returns
        -------
        list
            Unique values in table.column

        """
        if condition and condition[0]:
            query = "select distinct %s from %s where %s;" % (
                column,
                table,
                str(condition[0]),
            )
        else:
            query = "select distinct %s from %s;" % (column, table)
        self.cursor.execute(query)
        cursor_return = self.cursor.fetchall()
        if "ignore_null" in kwargs and kwargs["ignore_null"]:
            unique_values = [str(uv[0]) for uv in cursor_return if str(uv[0])]
        else:
            unique_values = [str(uv[0]) for uv in cursor_return]

        unique_values.sort()
        return unique_values

    def get_column_names(self, table_name):
        """Get all of the column names for a specified table

        Parameters
        ----------
        table_name : str
            SQL table

        Returns
        -------
        list
            All columns names in ``table_name``

        """
        if self.db_type == "sqlite":
            query = "PRAGMA table_info(%s);" % table_name.lower()
            index = 1
        else:
            query = (
                "select column_name from information_schema.columns where "
                "table_name = '%s';" % table_name.lower()
            )
            index = 0
        self.cursor.execute(query)
        cursor_return = self.cursor.fetchall()
        columns = [str(c[index]) for c in cursor_return]
        columns.sort()
        return columns

    def is_sqlite_column_datetime(self, table_name, column):
        """Check if a sqlite column is a datetime data type

        Parameters
        ----------
        table_name : str
            SQL table
        column : str
            SQL column

        Returns
        -------
        bool
            True if the ``table_name.column`` store datetime data

        """
        if self.db_type == "sqlite":
            query = "PRAGMA table_info(%s);" % table_name.lower()
            self.cursor.execute(query)
            cursor_return = self.cursor.fetchall()
            columns = {str(c[1]): str(c[2]) for c in cursor_return}
            if column in list(columns):
                column_type = columns[column]
                return (
                    "time" in column_type.lower()
                    or "date" in column_type.lower()
                )
        return False

    def get_min_value(self, table, column, condition=None):
        """Get the minimum value in the database for a given table and column

        Parameters
        ----------
        table : str
            SQL table
        column : str
            SQL column
        condition : str, optional
            Condition in SQL syntax

        Returns
        -------
        any
            The minimum value for table.column

        """
        return self.get_sql_function_value(
            "MIN", table, column, condition=condition
        )

    def get_max_value(self, table, column, condition=None):
        """Get the maximum value in the database for a given table and column

        Parameters
        ----------
        table : str
            SQL table
        column : str
            SQL column
        condition : str, optional
            Condition in SQL syntax

        Returns
        -------
        any
            The maximum value for table.column

        """
        return self.get_sql_function_value(
            "MAX", table, column, condition=condition
        )

    def get_sql_function_value(
        self, func, table, column, condition=None, first_value_only=True
    ):
        """Helper function used by get_min_values and get_max_values

        Parameters
        ----------
        func :
            SQL compatible function
        table : str
            SQL table
        column : str
            SQL column
        condition : str, optional
            Condition in SQL syntax (Default value = None)
        first_value_only : bool, optional
            if true, only return the first value, otherwise all values returned

        Returns
        -------
        list, any
            Results of ``cursor.fetchone()`` or ``cursor.fetchone()[0]`` if
            ``first_value_only`` is True

        """
        if condition:
            query = "SELECT %s(%s) FROM %s WHERE %s;" % (
                func,
                column,
                table,
                condition,
            )
        else:
            query = "SELECT %s(%s) FROM %s;" % (func, column, table)
        self.cursor.execute(query)
        cursor_return = self.cursor.fetchone()
        if first_value_only:
            return cursor_return[0]
        return cursor_return

    def get_roi_count_from_query(self, uid=None, dvh_condition=None):
        """Counts the DVH rows that match the provided conditions

        Parameters
        ----------
        uid : str, optional
            study instance uid
        dvh_condition : str, optional
            condition in SQL syntax for the DVHs table

        Returns
        -------
        int
            Number of rows in the DVHs table matching the provided parameters

        """
        if uid:
            condition = "study_instance_uid in ('%s')" % "', '".join(
                dvh_condition
            )
            if dvh_condition:
                condition = " and " + condition
        else:
            condition = ""

        if dvh_condition:
            condition = dvh_condition + condition

        return len(self.query("DVHs", "mrn", condition))

    def is_uid_imported(self, uid):
        """Check all tables to see if study instance uid is used

        Parameters
        ----------
        uid : str
            study instance uid

        Returns
        -------
        bool
            True if ``uid`` exists in any table

        """
        for table in self.tables:
            if self.is_study_instance_uid_in_table(table, uid):
                return True
        return False

    def is_mrn_imported(self, mrn):
        """Check all tables to see if MRN is used

        Parameters
        ----------
        mrn : str
            medical record number

        Returns
        -------
        bool
            True if ``mrn`` exists in any table

        """
        for table in self.tables:
            if self.is_mrn_in_table(table, mrn):
                return True
        return False

    def is_roi_imported(self, roi_name, study_instance_uid):
        """Check if a study is already using a specified roi name

        Parameters
        ----------
        roi_name : str
            roi name to check
        study_instance_uid : str
            restrict search to this study_instance_uid

        Returns
        -------
        bool
            True if ``roi_name`` is used in the DVHs table for the given
            ``study_instance_uid``

        """
        condition = "roi_name = '%s' and study_instance_uid = '%s'" % (
            roi_name,
            study_instance_uid,
        )
        roi_names = self.get_unique_values("DVHs", "roi_name", condition)
        return bool(roi_names)

    def get_row_count(self, table, condition=None):
        """

        Parameters
        ----------
        table : str
            SQL table
        condition : str
            SQL condition

        Returns
        -------
        int
            Number of rows in ``table`` meeting ``condition``

        """
        ans = self.query(table, "COUNT(mrn)", condition)
        if ans:
            return ans[0][0]
        return 0

    def export_to_sqlite(self, file_path, callback=None, force=False):
        """Create a new SQLite database and import this database's data

        Parameters
        ----------
        file_path : str
            Path where the new SQLite database will be created
        callback : callable, optional
            optional function to be called on each row insertion. Should accept
            table (str), current row (int), total_row_count (int) as parameters
        force : bool, optional
            ignore duplicate StudyInstanceUIDs if False

        """
        config = {"host": file_path}
        new_cnx = DVH_SQL(config, db_type="sqlite")
        new_cnx.initialize_database()
        self.import_db(self, new_cnx, callback=callback, force=force)

    @staticmethod
    def import_db(cnx_src, cnx_dst, callback=None, force=False):
        """

        Parameters
        ----------
        cnx_src : DVH_SQL
            the source DVHA DB connection
        cnx_dst : DVH_SQL
            the destination DVHA DB connection
        callback : callable, optional
            optional function to be called on each row insertion. Should accept
            table (str), current row (int), total_row_count (int) as parameters
        force : bool, optional
            ignore duplicate StudyInstanceUIDs if False

        """
        for table in cnx_src.tables:
            columns = cnx_src.get_column_names(table)
            study_uids_1 = cnx_src.get_unique_values(
                table, "study_instance_uid"
            )

            condition = None
            if not force:
                study_uids_2 = cnx_dst.get_unique_values(
                    table, "study_instance_uid"
                )
                study_uids_1 = list(set(study_uids_1) - set(study_uids_2))
                condition = "study_instance_uid IN ('%s')" % "','".join(
                    study_uids_1
                )

            total_row_count = cnx_src.get_row_count(table, condition)

            counter = 0
            for uid in study_uids_1:
                study_data = cnx_src.query(
                    table, ",".join(columns), "study_instance_uid = '%s'" % uid
                )
                for row in study_data:
                    if callback is not None:
                        CallAfter(callback, table, counter, total_row_count)
                        counter += 1
                    row_str = "'" + "','".join([str(v) for v in row]) + "'"
                    row_str = row_str.replace("'None'", "NULL")
                    cmd = "INSERT INTO %s (%s) VALUES (%s);\n" % (
                        table,
                        ",".join(columns),
                        row_str,
                    )
                    cnx_dst.execute_str(cmd)

    def save_to_json(self, file_path, callback=None):
        """Export SQL database to a JSON file

        Parameters
        ----------
        file_path : str
            file_path to new JSON file
        callback : callable, optional
            optional function to be called on each table insertion. Should
            accept table_name (str), table (int), table_count (int) as
            parameters

        """
        json_data = {
            "columns": {"categorical": categorical, "numerical": numerical}
        }
        for i, table in enumerate(self.tables):
            if callback is not None:
                CallAfter(callback, table, i, len(self.tables))
            columns = self.get_column_names(table)
            json_data[table] = self.query(
                table, ",".join(columns), bokeh_cds=True
            )

        with open(file_path, "w") as fp:
            json.dump(json_data, fp)

    def get_ptv_counts(self):
        """Get number of PTVs for each study instance uid

        Returns
        -------
        dict
            PTV counts stored by ``study_instance_uid``

        """
        results = self.query(
            "DVHs", "study_instance_uid", "roi_type like 'PTV%'"
        )
        uids = [uid[0] for uid in results]
        return {uid: uids.count(uid) for uid in list(set(uids))}


def truncate_string(input_string, character_limit):
    """Used to truncate a string to ensure it may be imported into database

    Parameters
    ----------
    input_string : str
        string to be truncated
    character_limit : int
        the maximum number of allowed characters

    Returns
    -------
    str
        truncated string

    """
    if len(input_string) > character_limit:
        return input_string[0 : (character_limit - 1)]
    return input_string


def echo_sql_db(config=None, db_type="pgsql", group=1):
    """Echo the database using stored or provided credentials

    Parameters
    ----------
    config : dict, optional
        database login credentials
    db_type : str, optional
        either 'pgsql' or 'sqlite'
    group : int, optional
        either group 1 or 2

    Returns
    -------
    bool
        True if echo is successful

    """
    try:
        if config:
            if db_type == "pgsql" and (
                "dbname" not in list(config) or "port" not in list(config)
            ):
                return False
            cnx = DVH_SQL(config, db_type=db_type, group=group)
        else:
            cnx = DVH_SQL(group=group)
        cnx.close()
        return True
    except Exception as e:
        if type(e) not in [
            psycopg2.OperationalError,
            sqlite3.OperationalError,
        ]:
            push_to_log(e, msg="Unknown Error during SQL Echo")
        return False


def write_test(
    config=None, db_type="pgsql", group=1, table=None, column=None, value=None
):
    """Write test data to database, verify with a query

    Parameters
    ----------
    config : dict, optional
        database login credentials
    db_type : str, optional
        either 'pgsql' or 'sqlite'
    group : int, optional
        either group 1 or 2
    table : str, optional
        SQL table
    column : str, optional
        SQL column
    value : str, optional
        test value

    Returns
    -------
    dict
        Write and Read test statuses

    """

    try:
        if config:
            if db_type == "pgsql" and (
                "dbname" not in list(config) or "port" not in list(config)
            ):
                return None
            cnx = DVH_SQL(config, db_type=db_type, group=group)
        else:
            cnx = DVH_SQL(group=group)
    except Exception as e:
        push_to_log(
            e, msg="Write Test: Connection to SQL could not be established"
        )
        return {"write": False, "delete": False}

    try:
        cnx.initialize_database()
    except Exception as e:
        push_to_log(e, msg="Write Test: DVH_SQL.initialize_database failed")

    if table is None:
        table = cnx.tables[-1]

    if column is None:
        column = "mrn"

    if value is None:
        # Find a test value that does not exist in the database
        value_init = "SqlTest_"
        i = 0
        value = value_init + str(i)
        current_values = cnx.get_unique_values(table, column)
        while value in current_values:
            value = value_init + str(i)
            i += 1

    condition_str = "%s = '%s'" % (column, value)
    insert_cmd = "INSERT INTO %s (%s) VALUES ('%s');" % (table, column, value)
    delete_cmd = "DELETE FROM %s WHERE %s;" % (table, condition_str)

    try:
        cnx.execute_str(insert_cmd)
    except Exception as e:
        push_to_log(e, msg="Write Test: SQL test insert command failed")

    try:
        test_return = cnx.query(table, column, condition_str)
        write_test_success = len(test_return) > 0
    except Exception as e:
        write_test_success = False
        push_to_log(e, msg="Write Test: SQL query of test insert failed")

    if not write_test_success:
        delete_test_success = None
    else:
        try:
            cnx.execute_str(delete_cmd)
            test_return = cnx.query(table, column, condition_str)
            delete_test_success = len(test_return) == 0
        except Exception as e:
            delete_test_success = False
            push_to_log(
                e, msg="Write Test: SQL delete command of test insert failed"
            )

    try:
        cnx.close()
    except Exception as e:
        push_to_log(e, msg="Write Test: Failed to close SQL connection")

    return {"write": write_test_success, "delete": delete_test_success}


def initialize_db():
    """Initialize the database"""
    with DVH_SQL() as cnx:
        cnx.initialize_database()


def is_file_sqlite_db(sqlite_db_file):
    """Check if file is a sqlite database

    Parameters
    ----------
    sqlite_db_file : str
        path to file to be checked


    Returns
    -------
    bool
        True if ``sqlite_db_file`` is a sqlite database

    """
    if isfile(sqlite_db_file):
        try:
            cnx = sqlite3.connect(sqlite_db_file)
            cnx.close()
            return True
        except sqlite3.OperationalError:
            pass

    return False
