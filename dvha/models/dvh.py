#!/usr/bin/env python
# -*- coding: utf-8 -*-

# models.dvh.py
"""
Class to retrieve DVH data from SQL, calculate parameters dependent on DVHs, and extract plotting data
"""
# Copyright (c) 2016-2019 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics

from copy import deepcopy
from dateutil.parser import parse as date_parser
import numpy as np
from dvha.db.sql_connector import DVH_SQL
from dvha.db.sql_to_python import QuerySQL
from dvha.options import Options


MAX_DOSE_VOLUME = Options().MAX_DOSE_VOLUME


# This class retrieves DVH data from the SQL database and calculates statistical DVHs (min, max, quartiles)
# It also provides some inspection tools of the retrieved data
class DVH:
    """This class will retrieve DVHs and other data in the DVH SQL table meeting the given constraints,
    it will also parse the DVH_string into python lists and retrieve the associated Rx dose

    Parameters
    ----------
    uid : list
        study_instance_uid's to be included in results
    dvh_condition : str
        a string in SQL syntax applied to a DVH Table query
    dvh_bin_width : int
        retrieve every nth value from dvh_string in SQL
    group : int
        either 1 or 2

    """

    def __init__(self, uid=None, dvh_condition=None, dvh_bin_width=5, group=1):
        self.dvh_bin_width = dvh_bin_width

        if uid:
            constraints_str = "study_instance_uid in ('%s')" % "', '".join(uid)
            if dvh_condition:
                constraints_str = "(%s) and %s" % (
                    dvh_condition,
                    constraints_str,
                )
        else:
            constraints_str = ""

        # Get DVH data from SQL and set as attributes
        dvh_data = QuerySQL("DVHs", constraints_str, group=group)
        if dvh_data.mrn:
            ignored_keys = {
                "cnx",
                "cursor",
                "table_name",
                "constraints_str",
                "condition_str",
            }
            self.keys = []
            for key, value in dvh_data.__dict__.items():
                if not key.startswith("__") and key not in ignored_keys:
                    if key == "dvh_string":
                        dvh_split = [
                            dvh.split(",")[:: self.dvh_bin_width]
                            for dvh in value
                        ]
                    setattr(self, key, value)
                    if "_string" not in key:
                        self.keys.append(key)

            # Move mrn to beginning of self.keys
            if "mrn" in self.keys:
                self.keys.pop(self.keys.index("mrn"))
                self.keys.insert(0, "mrn")

            # uid passed into DVH init is a unique list for querying and it is not in order of query results
            self.uid = self.study_instance_uid

            # Add these properties to dvh_data since they aren't in the DVHs SQL table
            self.count = len(self.mrn)
            self.study_count = len(set(self.uid))
            self.rx_dose = self.get_plan_values("rx_dose")
            self.sim_study_date = self.get_plan_values("sim_study_date")
            self.keys.append("rx_dose")
            self.endpoints = {"data": None, "defs": None}
            self.eud = None
            self.ntcp_or_tcp = None

            self.bin_count = max([len(dvh) for dvh in dvh_split])

            self.dvh = np.zeros([self.bin_count, self.count])

            # Get needed values not in DVHs table
            for i in range(self.count):
                # Process dvh_string to numpy array, and pad with zeros at the end
                # so that all dvhs are the same length
                current_dvh = np.array(dvh_split[i], dtype=np.float)
                current_dvh_max = np.max(current_dvh)
                if current_dvh_max > 0:
                    current_dvh = np.divide(current_dvh, current_dvh_max)
                zero_fill = np.zeros(self.bin_count - len(current_dvh))
                self.dvh[:, i] = np.concatenate((current_dvh, zero_fill))

            self.dth = []
            for i in range(self.count):
                # Process dth_string to numpy array
                try:
                    self.dth.append(
                        np.array(self.dth_string[i].split(","), dtype=np.float)
                    )
                except Exception:
                    self.dth.append(np.array([0]))

            # Store these now so they can be saved in DVH object without needing to query later
            with DVH_SQL() as cnx:
                self.physician_count = len(
                    cnx.get_unique_values(
                        "Plans",
                        "physician",
                        "study_instance_uid in ('%s')" % "','".join(self.uid),
                    )
                )
            self.total_fxs = self.get_plan_values("fxs")
            self.fx_dose = self.get_rx_values("fx_dose")
        else:
            self.count = 0

    def get_plan_values(self, plan_column):
        """Get values from the Plans table and store in order matching mrn / study_instance_uid

        Parameters
        ----------
        plan_column : str
            name of the SQL column to be returned

        Returns
        -------
        list
            values from the Plans table for the DVHs stored in this class

        """
        with DVH_SQL() as cnx:
            condition = "study_instance_uid in ('%s')" % "','".join(
                self.study_instance_uid
            )
            data = cnx.query(
                "Plans", "study_instance_uid, %s" % plan_column, condition
            )
            force_date = cnx.is_sqlite_column_datetime(
                "Plans", plan_column
            )  # returns False for pgsql

        uids = [row[0] for row in data]
        values = [row[1] for row in data]
        if force_date:  # sqlite does not have date or time like variables
            for i, value in enumerate(values):
                try:
                    if type(value) is int:
                        values[i] = str(date_parser(str(value)))
                    else:
                        values[i] = str(date_parser(value))
                except Exception:
                    values[i] = "None"
        return [values[uids.index(uid)] for uid in self.study_instance_uid]

    def get_rx_values(self, rx_column):
        """Get values from the Rxs table and store in order matching mrn / study_instance_uid

        Parameters
        ----------
        rx_column : str
            name of the SQL column to be returned

        Returns
        -------
        list
            values from the Rxs table for the DVHs stored in this class

        """
        with DVH_SQL() as cnx:
            condition = "study_instance_uid in ('%s')" % "','".join(
                self.study_instance_uid
            )
            data = cnx.query(
                "Rxs", "study_instance_uid, %s" % rx_column, condition
            )

        uids = [row[0] for row in data]
        values = [row[1] for row in data]
        final_values = {}
        for i, uid in enumerate(uids):
            if uid in list(values):
                final_values[uid] = "%s,%s" % (final_values[uid], values[i])
            else:
                final_values[uid] = str(values[i])
        return [final_values[uid] for uid in self.study_instance_uid]

    @property
    def x_axis(self):
        """Get the x-axis for plotting

        Returns
        -------
        list
            Dose axis
        """
        bins, width = self.bin_count, self.dvh_bin_width
        return np.multiply(np.array(range(bins)) + width / 2.0, width).tolist()

    @property
    def x_data(self):
        """Get the x-axes for plotting (one row per DVH)

        Returns
        -------
        list
            x data for plotting

        """
        bins, width, num_dvhs = self.bin_count, self.dvh_bin_width, self.count
        return [
            np.multiply(np.array(range(bins)) + width / 2.0, width).tolist()
        ] * num_dvhs

    @property
    def y_data(self):
        """Get y-values of the DVHs

        Returns
        -------
        list
            all DVHs in order (i.e., same as mrn, study_instance_uid)

        """
        return [self.dvh[:, i].tolist() for i in range(self.count)]

    def get_cds_data(self, keys=None):
        """Get data from this class in a format compatible with bokeh's ColumnDataSource.data

        Parameters
        ----------
        keys : list, optional
            Specify a list of DVH properties to be included

        Returns
        -------
        dict
            data from this class

        """
        if not keys:
            keys = self.keys

        # TODO: Is deepcopy needed here?
        return deepcopy({key: getattr(self, key) for key in keys})

    def get_percentile_dvh(self, percentile):
        """Get a population DVH based on percentile

        Parameters
        ----------
        percentile : float
            the percentile to calculate for each dose-bin. Passed into
            np.percentile()

        Returns
        -------
        np.ndarray
            a single DVH such that each bin is the given percentile of each
            bin over the whole sample

        """
        return np.percentile(self.dvh, percentile, 1)

    def get_dose_to_volume(
        self, volume, volume_scale="absolute", dose_scale="absolute"
    ):
        """Get the minimum dose to a specified volume

        Parameters
        ----------
        volume : int, float
            the specified volume in cm^3
        volume_scale : str, optional
            either 'relative' or 'absolute'
        dose_scale : str, optional
            either 'relative' or 'absolute'

        Returns
        -------
        list
            the dose in Gy to the specified volume

        """
        doses = np.zeros(self.count)
        for x in range(self.count):
            dvh = np.zeros(len(self.dvh))
            for y in range(len(self.dvh)):
                dvh[y] = self.dvh[y][x]
            if volume_scale == "relative":
                doses[x] = dose_to_volume(
                    dvh, volume, dvh_bin_width=self.dvh_bin_width
                )
            else:
                if self.volume[x]:
                    doses[x] = dose_to_volume(
                        dvh,
                        volume / self.volume[x],
                        dvh_bin_width=self.dvh_bin_width,
                    )
                else:
                    doses[x] = 0
        if dose_scale == "relative":
            if self.rx_dose[0]:
                doses = np.divide(doses * 100, self.rx_dose[0 : self.count])
            else:
                self.rx_dose[
                    0
                ] = 1  # if review dvh isn't defined, the following line would crash
                doses = np.divide(doses * 100, self.rx_dose[0 : self.count])
                self.rx_dose[0] = 0
                doses[0] = 0

        return doses.tolist()

    def get_volume_of_dose(
        self, dose, dose_scale="absolute", volume_scale="absolute"
    ):
        """Get the volume of an isodose contour defined by ``dose``

        Parameters
        ----------
        dose : int, float
            input dose use to calculate a volume of dose for entire sample
        dose_scale : str, optional
            either 'absolute' or 'relative'
        volume_scale : str, optional
            either 'absolute' or 'relative'

        Returns
        -------
        list
            a list of V_dose

        """
        volumes = np.zeros(self.count)
        for x in range(self.count):

            dvh = np.zeros(len(self.dvh))
            for y in range(len(self.dvh)):
                dvh[y] = self.dvh[y][x]
            if dose_scale == "relative":
                if isinstance(self.rx_dose[x], str):
                    volumes[x] = 0
                else:
                    volumes[x] = volume_of_dose(
                        dvh,
                        dose * self.rx_dose[x],
                        dvh_bin_width=self.dvh_bin_width,
                    )
            else:
                volumes[x] = volume_of_dose(
                    dvh, dose, dvh_bin_width=self.dvh_bin_width
                )

        if volume_scale == "absolute":
            volumes = np.multiply(volumes, self.volume[0 : self.count])
        else:
            volumes = np.multiply(volumes, 100.0)

        return volumes.tolist()

    def get_resampled_x_axis(self, resampled_bin_count=5000):
        """Get the x_axis of a resampled dvh

        Parameters
        ----------
        resampled_bin_count : int, optional
            Specify the number of bins used

        Returns
        -------
        np.ndarray
            the x axis of a resampled dvh
        """
        x_axis, dvhs = self.resample_dvh(
            resampled_bin_count=resampled_bin_count
        )
        return x_axis

    def get_stat_dvh(
        self, stat_type="mean", dose_scale="absolute", volume_scale="relative"
    ):
        """Get population DVH by statistical function

        Parameters
        ----------
        stat_type : str
            either 'min', 'mean', 'median', 'max', or 'std'
        dose_scale : str, optional
            either 'absolute' or 'relative'
        volume_scale : str, optional
            either 'absolute' or 'relative'

        Returns
        -------
        np.ndarray
            a single dvh where each bin is the stat_type of each bin for the
            entire sample

        """
        if dose_scale == "relative":
            x_axis, dvhs = self.resample_dvh()
        else:
            dvhs = self.dvh

        if volume_scale == "absolute":
            dvhs = self.dvhs_to_abs_vol(dvhs)

        stat_function = {
            "min": np.min,
            "mean": np.mean,
            "median": np.median,
            "max": np.max,
            "std": np.std,
        }
        dvh = stat_function[stat_type](dvhs, 1)

        return dvh

    def get_standard_stat_dvh(
        self, dose_scale="absolute", volume_scale="relative"
    ):
        """Get a min, mean, median, max, and quartiles DVHs

        Parameters
        ----------
        dose_scale : str, optional
            either 'absolute' or 'relative'
        volume_scale : str, optional
            either 'absolute' or 'relative'

        Returns
        -------
        dict
            a standard set of statistical dvhs ('min', 'q1', 'mean', 'median',
            'q1', and 'max')

        """
        if dose_scale == "relative":
            x_axis, dvhs = self.resample_dvh()
        else:
            dvhs = self.dvh

        if volume_scale == "absolute":
            dvhs = self.dvhs_to_abs_vol(dvhs)

        standard_stat_dvh = {
            "min": np.min(dvhs, 1),
            "q1": np.percentile(dvhs, 25, 1),
            "mean": np.mean(dvhs, 1),
            "median": np.median(dvhs, 1),
            "q3": np.percentile(dvhs, 75, 1),
            "max": np.max(dvhs, 1),
        }

        return standard_stat_dvh

    def dvhs_to_abs_vol(self, dvhs):
        """Get DVHs in absolute volume

        Parameters
        ----------
        dvhs : np.ndarray
            relative DVHs (dvh[bin, roi_index])

        Returns
        -------
        np.ndarray
            absolute DVHs

        """
        return np.multiply(dvhs, self.volume)

    def resample_dvh(self, resampled_bin_count=5000):
        """Resample DVHs with a new bin count

        Parameters
        ----------
        resampled_bin_count : int
             Number of bins in reampled DVH

        Returns
        -------
        tuple
            x-axis, y-axis of resampled DVHs
        """

        min_rx_dose = np.min(self.rx_dose) * 100.0
        new_bin_count = int(
            np.divide(float(self.bin_count), min_rx_dose) * resampled_bin_count
        )

        x1 = np.linspace(0, self.bin_count, self.bin_count)
        y2 = np.zeros([new_bin_count, self.count])
        for i in range(self.count):
            x2 = np.multiply(
                np.linspace(0, new_bin_count, new_bin_count),
                self.rx_dose[i] * 100.0 / resampled_bin_count,
            )
            y2[:, i] = np.interp(x2, x1, self.dvh[:, i])
        x2 = np.divide(
            np.linspace(0, new_bin_count - 1, new_bin_count) + 0.5,
            resampled_bin_count,
        )
        return x2, y2

    def get_summary(self):
        """Get a summary of the data in this class. Used in bottom left of
        main GUI

        Returns
        -------
        str
            Summary data
        """

        summary = [
            "Study count: %s" % self.study_count,
            "DVH count: %s" % self.count,
            "Institutional ROI count: %s" % len(set(self.institutional_roi)),
            "Physician ROI count: %s" % len(set(self.physician_roi)),
            "ROI type count: %s" % len(set(self.roi_type)),
            "Physician count: %s" % self.physician_count,
            "\nMin, Mean, Max",
            "Rx dose (Gy): %0.2f, %0.2f, %0.2f"
            % (
                min(self.rx_dose),
                sum(self.rx_dose) / self.count,
                max(self.rx_dose),
            ),
            "Volume (cc): %0.2f, %0.2f, %0.2f"
            % (
                min(self.volume),
                sum(self.volume) / self.count,
                max(self.volume),
            ),
            "Min dose (Gy): %0.2f, %0.2f, %0.2f"
            % (
                min(self.min_dose),
                sum(self.min_dose) / self.count,
                max(self.min_dose),
            ),
            "Mean dose (Gy): %0.2f, %0.2f, %0.2f"
            % (
                min(self.mean_dose),
                sum(self.mean_dose) / self.count,
                max(self.mean_dose),
            ),
            "Max dose (Gy): %0.2f, %0.2f, %0.2f"
            % (
                min(self.max_dose),
                sum(self.max_dose) / self.count,
                max(self.max_dose),
            ),
        ]
        return "\n".join(summary)

    @property
    def has_data(self):
        """Check that this class has queried data

        Returns
        -------
        bool
            True if there is data returned from SQL
        """
        return bool(len(self.mrn))


# Returns the isodose level outlining the given volume
def dose_to_volume(dvh, rel_volume, dvh_bin_width=1):
    """Calculate the minimum dose to a relative volume for one DVH

    Parameters
    ----------
    dvh : np.ndarray
        a single dvh
    rel_volume : float
        fractional volume
    dvh_bin_width : int, optional
        dose bin width of dvh

    Returns
    -------
    float
        minimum dose in Gy of specified volume

    """

    # Return the maximum dose instead of extrapolating
    if rel_volume < dvh[-1]:
        return len(dvh) * dvh_bin_width * 0.01

    dose_high = np.argmax(dvh < rel_volume)
    y = rel_volume
    x_range = [dose_high - 1, dose_high]
    y_range = [dvh[dose_high - 1], dvh[dose_high]]
    dose = np.interp(y, y_range, x_range) * dvh_bin_width * 0.01

    return dose


def volume_of_dose(dvh, dose, dvh_bin_width=1):
    """Calculate the relative volume of an isodose line definted by ``dose``
    for one DVH

    Parameters
    ----------
    dvh : np.ndarray
        a single dvh
    dose : float
        dose in cGy
    dvh_bin_width : int, optional
        dose bin width of dvh

    Returns
    -------
    float
        volume in cm^3 of roi receiving at least the specified dose

    """

    x = [
        int(np.floor(dose / dvh_bin_width * 100)),
        int(np.ceil(dose / dvh_bin_width * 100)),
    ]
    if len(dvh) < x[1]:
        return dvh[-1]
    y = [dvh[x[0]], dvh[x[1]]]
    roi_volume = np.interp(float(dose) / dvh_bin_width, x, y)

    return roi_volume


def calc_eud(dvh, a, dvh_bin_width=1):
    """EUD = sum[ v(i) * D(i)^a ] ^ [1/a]

    Parameters
    ----------
    dvh : np.ndarray
        a single DVH as a list of numpy 1D array with 1cGy bins
    a : float
        standard a-value for EUD calculations, organ and dose fractionation specific
    dvh_bin_width : int, optional
        dose bin width of dvh

    Returns
    -------
    float
        equivalent uniform dose

    """
    v = -np.gradient(dvh)

    dose_bins = np.linspace(0, np.size(dvh), np.size(dvh))
    dose_bins = np.round(dose_bins, 3) * dvh_bin_width
    bin_centers = dose_bins - (dvh_bin_width / 2.0)
    eud = np.power(
        np.sum(np.multiply(v, np.power(bin_centers, a))), 1.0 / float(a)
    )
    eud = np.round(eud, 2) * 0.01

    return eud


def calc_tcp(gamma, td_tcd, eud):
    """Tumor Control Probability / Normal Tissue Complication Probability
    1.0 / (1.0 + (``td_tcd`` / ``eud``) ^ (4.0 * ``gamma``))

    Parameters
    ----------
    gamma : float
        Gamma_50

    td_tcd : float
        Either TD_50 or TCD_50

    eud : float
        equivalent uniform dose

    Returns
    -------
    float
        TCP or NTCP

    """
    return 1.0 / (1.0 + (td_tcd / eud) ** (4.0 * gamma))
