from os.path import join
from dvha.paths import TG263_CSV, PREF_DIR


class ROIMapGenerator:
    """Class to interact with the TG263 table and generate compliant ROI Name Maps"""

    def __init__(self):
        # Load TG263 table
        with open(TG263_CSV, "r") as doc:
            keys = [key.strip() for key in doc.readline().split(",")]
            self.tg_263 = {key: [] for key in keys}
            for line in doc:
                if "xx" not in line:  # ignore the rows with generic expansions
                    for col, value in enumerate(line.split(",")):
                        if value == "":
                            value = "None"
                        self.tg_263[keys[col]].append(
                            value.strip().replace("^", ",")
                        )
            self.keys = keys
            self.keys.append(self.keys.pop(0))  # Move Target Type to the end

        self.key_map = {key: key for key in keys}

    def __call__(
        self,
        map_file_name,
        body_sites=None,
        data_filter=None,
        roi_uid_type="primary",
    ):
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
            data_filter = {"Anatomic Group": body_sites}
        data = (
            self.tg_263
            if data_filter is None
            else self.get_filtered_data(data_filter)
        )

        lookup = {
            "primary": "TG263-Primary Name",
            "reverse": "TG-263-Reverse Order Name",
            "fmaid": "FMAID",
        }
        roi_uids = self.get_unique_values(lookup[roi_uid_type], data)

        file_path = join(PREF_DIR, map_file_name)
        with open(file_path, "w") as doc:
            for roi_uid in roi_uids:
                doc.write(": ".join([roi_uid] * 3) + "\n")
        return file_path

    def prep_data_for_roi_map_gui(self):
        """ """
        ignored = [
            c
            for c in self.keys
            if "Reverse" in c or "Character" in c or "FMAID" in c
        ]
        for c in ignored:
            self.drop_column(c)

        str_map = {"Category": "Cat.", "Anatomic": "Anat.", "TG263-": ""}
        for c in self.keys:
            if any([key in c for key in list(str_map)]):
                new_key = c
                for key, value in str_map.items():
                    new_key = new_key.replace(key, value)
                self.key_map[c] = new_key
                key_index = self.keys.index(c)
                self.tg_263[new_key] = self.drop_column(c, return_data=True)
                self.keys.insert(key_index, new_key)

    ##########################################################
    # Generalized Tools
    ##########################################################
    def get_filtered_data(self, data_filter):
        """Get TG263 data with a filter

        Parameters
        ----------
        data_filter : dict
            column: list_allowed_values}

        Returns
        -------
        type
            subset of tg_263 with the data_filter applied

        """

        for key in list(data_filter):
            if (
                not isinstance(data_filter[key], list)
                and data_filter[key].lower() == "all"
            ):
                data_filter.pop(key)

        data = {key: [] for key in self.keys}
        for row in range(len(self.tg_263[self.keys[0]])):
            is_included = [
                self.tg_263[col][row] in data_filter[col]
                for col in list(data_filter)
            ]
            if all(is_included):
                for c in self.keys:
                    data[c].append(self.tg_263[c][row])
        return data

    def get_unique_values(self, column, data=None):
        """

        Parameters
        ----------
        column :
            TG263 column
        data :
            optionally provide filtered data, default is entire TG263 table

        Returns
        -------
        type
            list of unique values for the provided column

        """
        data = self.tg_263 if data is None else data
        return sorted([value for value in set(data[column]) if value])

    def get_value_from_uid(self, roi_uid, output_type, reverse_name=False):
        """

        Parameters
        ----------
        roi_uid : str
            either a primary name or FMAID (auto-detects)
        output_type : str
            column name of output value
        reverse_name : bool
            roi_uid is assumed to be reverse order name if True (Default value = False)

        Returns
        -------
        type
            another column value of the provided roi_uid

        """
        input_type = (
            "FMAID"
            if roi_uid.isdigit()
            else ["TG-263-Reverse Order Name", "TG263-Primary Name"][
                reverse_name
            ]
        )
        return self._get_value_from_uid(
            roi_uid,
            input_type=self.key_map[input_type],
            output_type=self.key_map[output_type],
        )

    def _get_value_from_uid(self, input_value, input_type, output_type):
        """Generic function to look up another column with a given input value and type

        Parameters
        ----------
        input_value :

        input_type :

        output_type :


        Returns
        -------

        """
        if input_value in self.tg_263[input_type]:
            index = self.tg_263[input_type].index(input_value)
            return self.tg_263[output_type][index]

    def drop_column(self, column, return_data=False):
        """Remove a column from tg_263 data and update keys

        Parameters
        ----------
        column :

        return_data :
             (Default value = False)

        Returns
        -------

        """
        if column in self.keys and column in list(self.tg_263):
            self.keys.pop(self.keys.index(column))
            popped_data = self.tg_263.pop(column)
        if return_data:
            return popped_data

    ##########################################################
    # Properties for coding ease
    ##########################################################
    @property
    def target_types(self):
        """ """
        return self.get_unique_values(self.key_map["Target Type"])

    @property
    def anatomic_groups(self):
        """ """
        return self.get_unique_values(self.key_map["Anatomic Group"])

    @property
    def major_categories(self):
        """ """
        return self.get_unique_values(self.key_map["Major Category"])

    @property
    def minor_categories(self):
        """ """
        return self.get_unique_values(self.key_map["Minor Category"])

    @property
    def primary_names(self):
        """ """
        return self.get_unique_values(self.key_map["TG263-Primary Name"])

    @property
    def reverse_order_primary_names(self):
        """ """
        return self.get_unique_values(
            self.key_map["TG-263-Reverse Order Name"]
        )

    @property
    def fmaids(self):
        """ """
        return self.get_unique_values(self.key_map["FMAID"])

    def get_primary_name(self, fmaid):
        """

        Parameters
        ----------
        fmaid :


        Returns
        -------

        """
        return self._get_value_from_uid(
            fmaid, input_type="FMAID", output_type="TG263-Primary Name"
        )

    def get_fmaid(self, primary_name):
        """

        Parameters
        ----------
        primary_name :


        Returns
        -------

        """
        return self._get_value_from_uid(
            primary_name, input_type="TG263-Primary Name", output_type="FMAID"
        )

    def get_target_type(self, roi_uid):
        """

        Parameters
        ----------
        roi_uid :


        Returns
        -------

        """
        return self.get_value_from_uid(roi_uid, output_type="Target Type")

    def get_major_category(self, roi_uid):
        """

        Parameters
        ----------
        roi_uid :


        Returns
        -------

        """
        return self.get_value_from_uid(roi_uid, output_type="Major Category")

    def get_minor_category(self, roi_uid):
        """

        Parameters
        ----------
        roi_uid :


        Returns
        -------

        """
        return self.get_value_from_uid(roi_uid, output_type="Minor Category")

    def get_anatomic_group(self, roi_uid):
        """

        Parameters
        ----------
        roi_uid :


        Returns
        -------

        """
        return self.get_value_from_uid(roi_uid, output_type="Anatomic Group")

    def get_reverse_order_name(self, roi_uid):
        """

        Parameters
        ----------
        roi_uid :


        Returns
        -------

        """
        return self.get_value_from_uid(
            roi_uid, output_type="TG-263-Reverse Order Name"
        )

    def get_description(self, roi_uid):
        """

        Parameters
        ----------
        roi_uid :


        Returns
        -------

        """
        return self.get_value_from_uid(roi_uid, output_type="Description")
