#!/usr/bin/env python
# -*- coding: utf-8 -*-

# db.sql_to_python.py
"""Query a DVHA SQL table and parse the return into a python object"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

from dvha.db.sql_connector import DVH_SQL
from dateutil.parser import parse as date_parser
from dvha.tools.errors import push_to_log


class QuerySQL:
    """Object to generically query a specified table. Each column is stored as
    a property of the object

    For example, if you query 'dvhs' with condition string of
    "mrn = 'some_mrn'" you can access any column name 'some_column' with
    QuerySQL.some_column which will return a list of values for 'some_column'.
    All properties contain lists with the order of their values synced,
    unless unique=True

    Parameters
    ----------
    table_name : str
        Beams', 'DVHs', 'Plans', or 'Rxs'
    condition_str : str
        condition in SQL syntax
    unique : bool, optional
        If True, only unique values stored
    columns : list, optional
        A list of SQL column names to be included in the return. If left as
        ``None``, all columns will be returned
    group : int, optional
        either 1 or 2

    """

    def __init__(
        self, table_name, condition_str, unique=False, columns=None, group=1
    ):

        table_name = table_name.lower()

        if table_name in {"beams", "dvhs", "plans", "rxs"}:
            self.table_name = table_name
            self.condition_str = condition_str
            with DVH_SQL(group=group) as cnx:

                all_columns = cnx.get_column_names(table_name)
                if columns is not None:
                    columns = set(all_columns).intersection(
                        columns
                    )  # ensure provided columns exist in SQL table
                else:
                    columns = all_columns

                for column in columns:
                    if column not in {
                        "roi_coord_string",
                        "distances_to_ptv",
                    }:  # ignored for memory since not used here
                        self.cursor = cnx.query(
                            self.table_name, column, self.condition_str
                        )
                        force_date = cnx.is_sqlite_column_datetime(
                            self.table_name, column
                        )  # returns False for pgsql
                        rtn_list = self.cursor_to_list(force_date=force_date)
                        if unique:
                            rtn_list = get_unique_list(rtn_list)
                        # create property of QuerySQL based on SQL column name
                        setattr(self, column, rtn_list)
        else:
            push_to_log(
                msg="QuerySQL: Table name in valid. Please select from Beams, "
                "DVHs, Plans, or Rxs."
            )

    def cursor_to_list(self, force_date=False):
        """Convert a cursor return into a list of values

        Parameters
        ----------
        force_date : bool, optional
             Apply dateutil.parser to values

        Returns
        -------
        list
            queried data

        """
        rtn_list = []
        for row in self.cursor:
            if force_date:
                try:
                    if type(row[0]) is int:
                        rtn_list.append(str(date_parser(str(row[0]))))
                    else:
                        rtn_list.append(str(date_parser(row[0])))
                except Exception:
                    rtn_list.append("None")

            elif isinstance(row[0], (int, float)):
                rtn_list.append(row[0])
            else:
                rtn_list.append(str(row[0]))
        return rtn_list


def get_unique_list(input_list):
    """Remove duplicates in list and retain order

    Parameters
    ----------
    input_list : list
        any list of objects

    Returns
    -------
    list
        input_list without duplicates

    """
    rtn_list_unique = []
    for value in input_list:
        if value not in rtn_list_unique:
            rtn_list_unique.append(value)

    return rtn_list_unique


def get_database_tree():
    """Query SQL to get all columns of each table

    Parameters
    ----------

    Returns
    -------
    dict
        column data sorted by table

    """
    with DVH_SQL() as cnx:
        tree = {table: cnx.get_column_names(table) for table in cnx.tables}
    return tree
