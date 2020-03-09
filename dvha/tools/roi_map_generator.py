from os.path import join
from dvha.paths import TG263_CSV, PREF_DIR


class ROIMapGenerator:
    """Class to interact with the TG263 table and generate compliant ROI Name Maps"""
    def __init__(self):
        # Load TG263 table
        with open(TG263_CSV, 'r') as doc:
            keys = [key.strip() for key in doc.readline().split(',')]
            self.tg_263 = {key: [] for key in keys}
            for line in doc:
                if 'xx' not in line:  # ignore the rows with generic expansions
                    for col, value in enumerate(line.split(',')):
                        self.tg_263[keys[col]].append(value.strip().replace('^', ','))
            self.keys = keys

    def __call__(self, map_file_name, body_sites=None, data_filter=None, roi_uid_type='primary'):
        """
        Create a new ROI map file based on TG263
        :param map_file_name: save the file in PREF_DIR with this name
        :type map_file_name: str
        :param body_sites: automatically create a data_filter based on these body sites
        :type body_sites: list
        :param data_filter: used to write a subset of the TG263 data
        :type data_filter: dict
        :param roi_uid_type: either 'primary', 'reverse', or 'fmaid'
        :type roi_uid_type: str
        :return: file_path of new map file
        """
        if body_sites is not None:
            if type(body_sites) is not list:
                body_sites = [body_sites]
            data_filter = {'Anatomic Group': body_sites}
        data = self.tg_263 if data_filter is None else self.get_filtered_data(data_filter)

        lookup = {'primary': 'TG263-Primary Name',
                  'reverse': 'TG-263-Reverse Order Name',
                  'fmaid': 'FMAID'}
        roi_uids = self.get_unique_values(lookup[roi_uid_type], data)

        file_path = join(PREF_DIR, map_file_name)
        with open(file_path, 'w') as doc:
            for roi_uid in roi_uids:
                doc.write(": ".join([roi_uid] * 3) + '\n')
        return file_path

    ##########################################################
    # Generalized Tools
    ##########################################################
    def get_filtered_data(self, data_filter):
        """
        Get TG263 data with a filter
        :param data_filter: {column: list_allowed_values}
        :type data_filter: dict
        :return: subset of tg_263 with the data_filter applied
        :type: dict
        """

        data = {key: [] for key in self.keys}
        for row in range(len(self.tg_263[self.keys[0]])):
            is_included = [self.tg_263[col][row] in data_filter[col] for col in list(data_filter)]
            if all(is_included):
                for c in self.keys:
                    data[c].append(self.tg_263[c][row])
        return data

    def get_unique_values(self, column, data=None):
        """
        :param column: TG263 column
        :param data: optionally provide filtered data, default is entire TG263 table
        :return: list of unique values for the provided column
        """
        data = self.tg_263 if data is None else data
        values = [value for value in set(data[column]) if value]
        values.sort()
        return values

    def get_value_from_uid(self, roi_uid, output_type, reverse_name=False):
        """
        :param roi_uid: either a primary name or FMAID (auto-detects)
        :type roi_uid: str
        :param output_type: column name of output value
        :type output_type: str
        :param reverse_name: roi_uid is assumed to be reverse order name if True
        :type reverse_name: bool
        :return: another column value of the provided roi_uid
        """
        input_type = 'FMAID' if roi_uid.isdigit() else ['TG-263-Reverse Order Name', 'TG263-Primary Name'][reverse_name]
        return self._get_value_from_uid(roi_uid, input_type=input_type, output_type=output_type)

    def _get_value_from_uid(self, input_value, input_type, output_type):
        """Generic function to look up another column with a given input value and type"""
        if input_value in self.tg_263[input_type]:
            index = self.tg_263[input_type].index(input_value)
            return self.tg_263[output_type][index]

    ##########################################################
    # Properties for coding ease
    ##########################################################
    @property
    def anatomic_groups(self):
        return self.get_unique_values('Anatomic Group')

    @property
    def major_categories(self):
        return self.get_unique_values('Major Category')

    @property
    def minor_categories(self):
        return self.get_unique_values('Minor Category')

    @property
    def primary_names(self):
        return self.get_unique_values('TG263-Primary Name')

    @property
    def reverse_order_primary_names(self):
        return self.get_unique_values('TG-263-Reverse Order Name')

    @property
    def fmaids(self):
        return self.get_unique_values('FMAID')

    def get_primary_name(self, fmaid):
        return self._get_value_from_uid(fmaid, input_type='FMAID', output_type='TG263-Primary Name')

    def get_fmaid(self, primary_name):
        return self._get_value_from_uid(primary_name, input_type='TG263-Primary Name', output_type='FMAID')

    def get_target_type(self, roi_uid):
        return self.get_value_from_uid(roi_uid, output_type='Target Type')

    def get_major_category(self, roi_uid):
        return self.get_value_from_uid(roi_uid, output_type='Major Category')

    def get_minor_category(self, roi_uid):
        return self.get_value_from_uid(roi_uid, output_type='Minor Category')

    def get_anatomic_group(self, roi_uid):
        return self.get_value_from_uid(roi_uid, output_type='Anatomic Group')

    def get_reverse_order_name(self, roi_uid):
        return self.get_value_from_uid(roi_uid, output_type='TG-263-Reverse Order Name')

    def get_description(self, roi_uid):
        return self.get_value_from_uid(roi_uid, output_type='Description')

