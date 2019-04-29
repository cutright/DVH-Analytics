from db import sql_columns
from db.sql_connector import DVH_SQL
import numpy as np
from scipy import stats
from sklearn import linear_model
from sklearn.metrics import mean_squared_error, r2_score
from regressors import stats as regressors_stats
from sklearn.ensemble import RandomForestRegressor


class StatsData:
    def __init__(self, dvhs, table_data):
        self.dvhs = dvhs
        self.table_data = table_data
        self.data = {}

        self.column_info = sql_columns.numerical
        self.correlation_variables = list(self.column_info)
        self.correlation_variables.sort()

        self.map_data()
        # self.add_ptv_data()

    @property
    def uids(self):
        return self.dvhs.study_instance_uid

    @property
    def mrns(self):
        return self.dvhs.mrn

    @property
    def sim_study_dates(self):
        # print(self.data['Simulation Date'])
        # uids = self.dvhs.study_instance_uid
        # sim_study_dates = []
        # cnx = DVH_SQL()
        # for uid in uids:
        #     sim_study_dates.append(cnx.query('Plans', 'sim_study_date', "study_instance_uid = '%s'" % uid)[0])
        # cnx.close()
        # return sim_study_dates
        return self.data['Simulation Date']['values']

    def map_data(self):
        self.data = {}
        stats = ['min', 'mean', 'median', 'max']
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

                    if str_starts_with_any_in_list(var, ['Beam Complexity', 'Beam Area', 'CP MU',
                                                         'Beam Perimeter', 'Beam Energy']):
                        # stats of these four variable types have min, mean, median, and max types in DB
                        # The following will take min, mean, median, or max of all values for a UID based on var type
                        # Example, if var_name == Beam Complexity (Max), the following will return the Max of these
                        temp = []
                        for uid in self.uids:
                            indices = self.get_beam_indices(uid)
                            beam_data = getattr(self.table_data['Beams'], var_name)
                            values = [beam_data[i] for i in indices if beam_data[i] != 'None']
                            for stat in stats:
                                if stat in var.lower():
                                    if values:
                                        temp.append(getattr(np, stat)(values))
                                    else:
                                        temp.append(None)
                        self.data[var] = {'units': self.column_info[var]['units'],
                                          'values': temp}
                    else:
                        temp = {s: [] for s in stats}
                        for uid in self.uids:
                            for stat in stats:
                                values = self.get_src_values(src, var_name, uid)
                                values = [v for v in values if v != 'None']
                                if values:
                                    temp[stat].append(getattr(np, stat)(values))
                                else:
                                    temp[stat].append(None)

                        for stat in stats:
                            corr_key = "%s (%s)" % (var, stat.capitalize())
                            self.data[corr_key] = {'units': self.column_info[var]['units'],
                                                   'values': temp[stat]}
        self.validate_data()

    def get_plan_index(self, uid):
        return self.table_data['Plans'].study_instance_uid.index(uid)

    def get_beam_indices(self, uid):
        return [i for i, x in enumerate(self.table_data['Beams'].study_instance_uid) if x == uid]

    @staticmethod
    def get_src_values(src, var_name, uid):
        uid_indices = [i for i, x in enumerate(src.study_instance_uid) if x == uid]
        return [getattr(src, var_name)[i] for i in uid_indices]

    @property
    def variables(self):
        return [var for var in list(self.data) if var != 'Simulation Date']

    @property
    def control_chart_variables(self):
        return list(self.data)

    def get_bokeh_data(self, x, y):
        return {'uid': self.uids,
                'mrn': self.mrns,
                'x': self.data[x]['values'],
                'y': self.data[y]['values']}

    def get_axis_title(self, variable):
        if self.data[variable]['units']:
            return "%s (%s)" % (variable, self.data[variable]['units'])
        return variable

    def update_endpoints_and_radbio(self):
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

    def add_ptv_data(self):
        if self.dvhs:
            attr = ['cross_section_max', 'cross_section_median', 'max_dose', 'min_dose', 'spread_x', 'spread_y',
                    'spread_z', 'surface_area', 'volume']
            units = ['cm²', 'cm²', 'Gy', 'Gy', 'cm', 'cm', 'cm', 'cm²', 'cm³']

            for i, key in enumerate(attr):
                clean_key = ('PTV %s' % key.replace('_', ' ').title())
                self.data[clean_key] = {'values': getattr(self.dvhs, 'ptv_%s' % key), 'units': units[i]}

    def validate_data(self):
        bad_vars = []
        for var_name, var_obj in self.data.items():
            if var_name != 'Simulation Date':
                values = [float(val) for val in var_obj['values'] if val != 'None' and val is not None]
                if not any(np.diff(values).tolist()):
                    bad_vars.append(var_name)
        for var in bad_vars:
            self.data.pop(var)


def str_starts_with_any_in_list(string_a, string_list):
    for string_b in string_list:
        if string_a.startswith(string_b):
            return True
    return False


def get_p_values(X, y, predictions, params):
    # https://stackoverflow.com/questions/27928275/find-p-value-significance-in-scikit-learn-linearregression
    newX = np.append(np.ones((len(X), 1)), X, axis=1)
    MSE = (sum((y - predictions) ** 2)) / (len(newX) - len(newX[0]))

    var_b = MSE * (np.linalg.inv(np.dot(newX.T, newX)).diagonal())
    sd_b = np.sqrt(var_b)
    ts_b = params / sd_b

    return [2 * (1 - stats.t.cdf(np.abs(i), (len(newX) - 1))) for i in ts_b], sd_b, ts_b


def multi_variable_regression(X, y):
    output = {}

    reg = linear_model.LinearRegression()
    ols = reg.fit(X, y)

    output['y_intercept'] = reg.intercept_
    output['slope'] = reg.coef_
    params = np.append(output['y_intercept'],
                       output['slope'])
    output['predictions'] = reg.predict(X)

    output['r_sq'] = r2_score(y,  output['predictions'])
    output['mse'] = mean_squared_error(y,  output['predictions'])

    output['p_values'], output['sd_b'], output['ts_b'] = get_p_values(X, y,  output['predictions'], params)

    output['residuals'] = np.subtract(y, output['predictions'])

    output['norm_prob_plot'] = stats.probplot(output['residuals'], dist='norm', fit=False, plot=None, rvalue=False)

    reg_prob = linear_model.LinearRegression()
    reg_prob.fit([[val] for val in output['norm_prob_plot'][0]], output['norm_prob_plot'][1])
    output['y_intercept_prob'] = reg_prob.intercept_
    output['slope_prob'] = reg_prob.coef_
    output['x_trend_prob'] = [min(output['norm_prob_plot'][0]), max(output['norm_prob_plot'][0])]
    output['y_trend_prob'] = np.add(np.multiply(output['x_trend_prob'],  output['slope_prob']),
                                    output['y_intercept_prob'])

    output['f_stat'] = regressors_stats.f_stat(ols, X, y)
    output['df_error'] = len(X[:, 0]) - len(X[0, :]) - 1
    output['df_model'] = len(X[0, :])

    output['f_p_value'] = stats.f.cdf(output['f_stat'], output['df_model'], output['df_error'])

    answer = Obj()
    for key in list(output):
        setattr(answer, key, output[key])

    return answer


class Obj:
    pass


def get_control_limits(y):
    y = np.array(y)

    center_line = np.mean(y)
    avg_moving_range = np.mean(np.absolute(np.diff(y)))

    scalar_d = 1.128

    ucl = center_line + 3 * avg_moving_range / scalar_d
    lcl = center_line - 3 * avg_moving_range / scalar_d

    return center_line, ucl, lcl


def get_random_forest(X, y, n_estimators=100, max_features=None):
    if max_features is None:
        max_features = len(X[0, :])
    regressor = RandomForestRegressor(n_estimators=n_estimators, max_features=max_features)
    regressor.fit(X, y)
    y_pred = regressor.predict(X)

    mse = np.mean(np.square(np.subtract(y_pred, y)))

    return y_pred, mse
