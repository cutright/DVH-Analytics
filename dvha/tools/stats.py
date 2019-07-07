#!/usr/bin/env python
# -*- coding: utf-8 -*-

# tools.stats.py
"""
Take numerical data from main app and convert to a format suitable for statistical analysis
in Regression and Control Chart tabs

"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

import numpy as np
from scipy import stats
from sklearn import linear_model
from sklearn.metrics import mean_squared_error, r2_score
from regressors import stats as regressors_stats
from dvha.db import sql_columns


class StatsData:
    def __init__(self, dvhs, table_data):
        """
        Class used to to collect data for Regression and Control Chart
        This process is different than for Time Series since regressions require all variables to be the same length
        :param dvhs: data from DVH query
        :type dvhs: DVH
        :param table_data: table data other than from DVHs
        :type table_data: dict
        """
        self.dvhs = dvhs
        self.table_data = table_data

        self.column_info = sql_columns.numerical
        self.correlation_variables = list(self.column_info)
        self.correlation_variables.sort()

        self.__map_data()

    def __map_data(self):
        self.data = {}
        stat_types = ['min', 'mean', 'median', 'max']
        for var in self.correlation_variables:
            if var in self.column_info.keys():
                var_name = self.column_info[var]['var_name']
                table = self.column_info[var]['table']

                if table == 'DVHs':
                    self.data[var] = {'units': self.column_info[var]['units'],
                                      'values': getattr(self.dvhs, var_name)}

                # single value variables
                elif table == 'Plans':
                    src = self.table_data[table]
                    self.data[var] = {'units': self.column_info[var]['units'],
                                      'values': [getattr(src, var_name)[self.get_plan_index(uid)] for uid in self.uids]}

                # multi value variables
                elif table == 'Beams':
                    src = self.table_data[table]

                    if str_starts_with_any_in_list(var, ['Beam Complexity', 'Beam Area', 'Control Point MU',
                                                         'Beam Perimeter', 'Beam Energy']):
                        # stats of these four variable types have min, mean, median, and max types in DB
                        # The following will take min, mean, median, or max of all values for a UID based on var type
                        # Example, if var_name == Beam Complexity (Max), the following will return the Max of these
                        temp = []
                        for uid in self.uids:
                            indices = self.get_beam_indices(uid)
                            beam_data = getattr(self.table_data['Beams'], var_name)
                            values = [beam_data[i] for i in indices if beam_data[i] != 'None']
                            for stat in stat_types:
                                if stat in var.lower():
                                    if values:
                                        temp.append(getattr(np, stat)(values))
                                    else:
                                        temp.append(None)
                        self.data[var] = {'units': self.column_info[var]['units'],
                                          'values': temp}
                    else:
                        temp = {s: [] for s in stat_types}
                        for uid in self.uids:
                            for stat in stat_types:
                                values = self.get_src_values(src, var_name, uid)
                                values = [v for v in values if v != 'None']
                                if values:
                                    temp[stat].append(getattr(np, stat)(values))
                                else:
                                    temp[stat].append(None)

                        for stat in stat_types:
                            corr_key = "%s (%s)" % (var, stat.capitalize())
                            self.data[corr_key] = {'units': self.column_info[var]['units'],
                                                   'values': temp[stat]}
        self.validate_data()

    def validate_data(self):
        """
        Remove any variables that are constant to avoid crash on regression
        """
        bad_vars = []
        for var_name, var_obj in self.data.items():
            if 'Date' in var_name:
                if var_name != 'Simulation Date':
                    bad_vars.append(var_name)
            else:
                values = [float(val) for val in var_obj['values'] if val != 'None' and val is not None]
                if not any(np.diff(values).tolist()):
                    bad_vars.append(var_name)

        for var in bad_vars:
            self.data.pop(var)

    def update_endpoints_and_radbio(self):
        """
        Update endpoint and radbio data in self.data. This function is needed since all of these values are calcualted
        after a query and user may change these values.
        """
        if self.dvhs:
            if self.dvhs.endpoints['defs']:
                for var in self.dvhs.endpoints['defs']['label']:
                    if var not in self.variables:
                        self.data[var] = {'units': '',
                                          'values': self.dvhs.endpoints['data'][var]}

                for var in self.variables:
                    if var[0:2] in {'D_', 'V_'}:
                        if var not in self.dvhs.endpoints['defs']['label']:
                            self.data.pop(var)

            if self.dvhs.eud:
                self.data['EUD'] = {'units': 'Gy',
                                    'values': self.dvhs.eud}
            if self.dvhs.ntcp_or_tcp:
                self.data['NTCP or TCP'] = {'units': '',
                                            'values': self.dvhs.ntcp_or_tcp}
            self.validate_data()

    @staticmethod
    def get_src_values(src, var_name, uid):
        uid_indices = [i for i, x in enumerate(src.study_instance_uid) if x == uid]
        return [getattr(src, var_name)[i] for i in uid_indices]

    def get_plan_index(self, uid):
        return self.table_data['Plans'].study_instance_uid.index(uid)

    def get_beam_indices(self, uid):
        return [i for i, x in enumerate(self.table_data['Beams'].study_instance_uid) if x == uid]

    def get_bokeh_data(self, x, y):
        """
        Get data in a format compatible with bokeh's ColumnDataSource.data
        :param x: x-variable name
        :type x: str
        :param y: y-variable name
        :type y: str
        :return: x and y data
        :rtype: dict
        """
        return {'uid': self.uids,
                'mrn': self.mrns,
                'date': self.sim_study_dates,
                'x': self.data[x]['values'],
                'y': self.data[y]['values']}

    @property
    def uids(self):
        return self.dvhs.study_instance_uid

    @property
    def mrns(self):
        return self.dvhs.mrn

    @property
    def sim_study_dates(self):
        return self.data['Simulation Date']['values']

    @property
    def variables(self):
        return [var for var in list(self.data) if var != 'Simulation Date']

    @property
    def control_chart_variables(self):
        return list(self.data)

    def get_axis_title(self, variable):
        if self.data[variable]['units']:
            return "%s (%s)" % (variable, self.data[variable]['units'])
        return variable

    def get_X_and_y(self, y_variable, x_variables, include_patient_info=False):
        """
        Collect data for input into multi-variable regression
        :param y_variable: dependent variable
        :type y_variable: str
        :param x_variables: independent variables
        :type x_variables: list
        :param include_patient_info: If True, return mrn, uid, dates with X and y
        :type include_patient_info: bool
        :return: X, y or X, y, mrn, uid, dates
        """
        data, mrn, uid, dates = [], [], [], []
        y_var_data = []
        for i, value in enumerate(self.data[y_variable]['values']):
            y_var_data.append([value, np.nan][value == 'None'])
            if value != 'None':
                mrn.append(self.mrns[i])
                uid.append(self.uids[i])
                dates.append(self.sim_study_dates[i])

        data.append(y_var_data)
        for var in x_variables:
            x_var_data = []
            for value in self.data[var]['values']:
                x_var_data.append([value, np.nan][value == 'None'])
            data.append(x_var_data)

        data = np.array(data)
        bad_indices = get_index_of_nan(data)

        for bad_index in bad_indices[::-1]:
            data = np.delete(data, bad_index, 1)
            mrn.pop(bad_index)
            uid.pop(bad_index)
            dates.pop(bad_index)

        X = np.transpose(data[1:])
        y = data[0]

        if not include_patient_info:
            return X, y
        return X, y, mrn, uid, dates


def get_index_of_nan(numpy_array):
    bad_indices = []
    nan_data = np.isnan(numpy_array)
    for var_data in nan_data:
        indices = np.where(var_data)[0].tolist()
        if indices:
            bad_indices.extend(indices)
    bad_indices = list(set(bad_indices))
    bad_indices.sort()
    return bad_indices


def str_starts_with_any_in_list(string_a, string_list):
    """
    Check if string_a starts with any string the provided list of strings
    """
    for string_b in string_list:
        if string_a.startswith(string_b):
            return True
    return False


def get_p_values(X, y, predictions, params):
    """
    Get p-values using sklearn
    based on https://stackoverflow.com/questions/27928275/find-p-value-significance-in-scikit-learn-linearregression
    :param X: independent data
    :type X: np.array
    :param y: dependent data
    :type y: np.array
    :param predictions: output from linear_model.LinearRegression.predict
    :param params: np.array([y_incercept, slope])
    :return: p-values
    :rtype: list
    """

    newX = np.append(np.ones((len(X), 1)), X, axis=1)
    MSE = (sum((y - predictions) ** 2)) / (len(newX) - len(newX[0]))

    var_b = MSE * (np.linalg.inv(np.dot(newX.T, newX)).diagonal())
    sd_b = np.sqrt(var_b)
    ts_b = params / sd_b

    return [2 * (1 - stats.t.cdf(np.abs(i), (len(newX) - 1))) for i in ts_b], sd_b, ts_b


class MultiVariableRegression:
    """
    Perform a multi-variable regression using sklearn
    """
    def __init__(self, X, y):
        """
        :param X: independent data
        :type X: np.array
        :param y: dependent data
        :type y: list
        """

        self.reg = linear_model.LinearRegression()
        ols = self.reg.fit(X, y)

        self.y_intercept = self.reg.intercept_
        self.slope = self.reg.coef_
        params = np.append(self.y_intercept, self.slope)
        self.predictions = self.reg.predict(X)

        self.r_sq = r2_score(y,  self.predictions)
        self.mse = mean_squared_error(y,  self.predictions)

        self.p_values, self.sd_b, self.ts_b = get_p_values(X, y,  self.predictions, params)

        self.residuals = np.subtract(y, self.predictions)

        self.norm_prob_plot = stats.probplot(self.residuals, dist='norm', fit=False, plot=None, rvalue=False)

        reg_prob = linear_model.LinearRegression()
        reg_prob.fit([[val] for val in self.norm_prob_plot[0]], self.norm_prob_plot[1])

        self.y_intercept_prob = reg_prob.intercept_
        self.slope_prob = reg_prob.coef_
        self.x_trend_prob = [min(self.norm_prob_plot[0]), max(self.norm_prob_plot[0])]
        self.y_trend_prob = np.add(np.multiply(self.x_trend_prob, self.slope_prob), self.y_intercept_prob)

        self.f_stat = regressors_stats.f_stat(ols, X, y)
        self.df_error = len(X[:, 0]) - len(X[0, :]) - 1
        self.df_model = len(X[0, :])

        self.f_p_value = stats.f.cdf(self.f_stat, self.df_model, self.df_error)


def get_control_limits(y):
    """
    Calculate control limits for Control Chart
    :param y: data
    :type y: list
    :return: center line, upper control limit, and lower control limit
    """
    y = np.array(y)

    center_line = np.mean(y)
    avg_moving_range = np.mean(np.absolute(np.diff(y)))

    scalar_d = 1.128

    ucl = center_line + 3 * avg_moving_range / scalar_d
    lcl = center_line - 3 * avg_moving_range / scalar_d

    return center_line, ucl, lcl
