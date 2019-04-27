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
        # self.add_ptv_data()

    @property
    def uids(self):
        return self.dvhs.study_instance_uid

    @property
    def mrns(self):
        return self.dvhs.mrn

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
                                        temp.append(getattr(numpy, stat)(values))
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
                                    temp[stat].append(getattr(numpy, stat)(values))
                                else:
                                    temp[stat].append(None)

                        for stat in stats:
                            corr_key = "%s (%s)" % (var, stat.capitalize())
                            self.data[corr_key] = {'units': self.column_info[var]['units'],
                                                   'values': temp[stat]}

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

    def add_ptv_data(self):
        if self.dvhs:
            attr = ['cross_section_max', 'cross_section_median', 'max_dose', 'min_dose', 'spread_x', 'spread_y',
                    'spread_z', 'surface_area', 'volume']
            units = ['cm²', 'cm²', 'Gy', 'Gy', 'cm', 'cm', 'cm', 'cm²', 'cm³']

            for i, key in enumerate(attr):
                clean_key = ('PTV %s' % key.replace('_', ' ').title())
                self.data[clean_key] = {'values': getattr(self.dvhs, 'ptv_%s' % key), 'units': units[i]}


def str_starts_with_any_in_list(string_a, string_list):
    for string_b in string_list:
        if string_a.startswith(string_b):
            return True
    return False
