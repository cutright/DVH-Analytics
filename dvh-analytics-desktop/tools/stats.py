from db import sql_columns
import numpy


class StatsData:
    def __init__(self, dvhs, table_data):
        self.dvhs = dvhs
        self.table_data = table_data
        self.data = {}

        self.column_info = sql_columns.numerical
        self.correlation_variables = list(self.column_info)
        self.correlation_variables.sort()

        self.map_data()

    @property
    def uids(self):
        return self.dvhs.study_instance_uid

    @property
    def mrns(self):
        return self.dvhs.mrn

    def map_data(self):
        self.data = {}
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
                    stats = ['min', 'mean', 'median', 'max']
                    temp = {s: [] for s in stats}
                    for uid in self.uids:
                        for stat in stats:
                            values = self.get_src_values(src, var_name, uid)
                            values = [v for v in values if v != 'None']
                            if values:
                                temp[stat].append(getattr(numpy, stat)(values))
                            else:
                                temp[stat].append(None)

                    for stat in stats:
                        corr_key = "%s (%s)" % (var, stat.capitalize())
                        self.data[corr_key] = {'units': self.column_info[var]['units'],
                                               'values': temp[stat]}

    def get_plan_index(self, uid):
        return self.table_data['Plans'].study_instance_uid.index(uid)

    @staticmethod
    def get_src_values(src, var_name, uid):
        uid_indices = [i for i, x in enumerate(src.study_instance_uid) if x == uid]
        return [getattr(src, var_name)[i] for i in uid_indices]

    @property
    def variables(self):
        return list(self.data)

    def get_bokeh_data(self, x, y):
        return {'uid': self.uids,
                'mrn': self.mrns,
                'x': self.data[x]['values'],
                'y': self.data[y]['values']}


# def str_starts_with_any_in_list(string_a, string_list):
#     for string_b in string_list:
#         if string_a.startswith(string_b):
#             return True
#     return False
