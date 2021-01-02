#!/usr/bin/env python
# -*- coding: utf-8 -*-

# tools.name_prediction.py
"""Implementation of rapidfuzz for ROI name prediction"""
# Copyright (c) 2016-2021 Dan Cutright
# This file is part of DVH Analytics, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVH-Analytics
from rapidfuzz import fuzz
from dvha.tools.roi_name_manager import clean_name


class ROINamePredictor:
    """ROI Name Prediction class object

    Parameters
    ----------
    roi_map : DatabaseROIs
        ROI map object
    weight_simple : float, optional
        Scaling factor for fuzz.ratio for combined score
    weight_partial : float, optional
        Scaling factor for fuzz.partial_ratio for combined score
    threshold : float, optional
        Set a minimum score for a prediction to be returned
    """

    def __init__(
        self, roi_map, weight_simple=1.0, weight_partial=0.6, threshold=0.0
    ):

        self.roi_map = roi_map
        norm_weight = weight_partial + weight_simple
        self.weight = {
            "simple": 2 * weight_simple / norm_weight,
            "partial": 2 * weight_partial / norm_weight,
        }
        self.threshold = threshold

    def get_best_roi_match(self, roi, physician, return_score=False):
        """Check all ROI variations for best match, return physician ROI

        Parameters
        ----------
        roi : str
            An ROI name
        physician : str
            Physician as stored in ROI Map
        return_score : bool, optional
             If true, return a tuple: prediction, score

        Returns
        -------
        str
            The physician ROI associated with the ROI variation that is has
            the highest combined fuzz score for ``roi``

        """
        physician_variations = self.roi_map.get_all_variations_of_physician(
            physician
        )
        fuzz_scores = self.get_combined_fuzz_scores(roi, physician_variations)
        if fuzz_scores:
            predicted_variation, score = fuzz_scores[0][1], fuzz_scores[0][0]
            prediction = self.roi_map.get_physician_roi(
                physician, predicted_variation
            )
            if score > self.threshold:
                if return_score:
                    return prediction, score
                return prediction

    def get_combined_fuzz_score(self, a, b, mode="geom_mean"):
        """Return ``combine_scores`` for strings ``a`` and ``b``

        Parameters
        ----------
        a : str
            Any string
        b : str
            Another string for comparison
        mode : str, optional
            Method for combining ``fuzz.ratio`` and ``fuzz.partial_ratio``.
            Options are 'geom_mean', 'product', and 'average'

        Returns
        -------
        float
            Results from ``combine_scores`` for ``a`` and ``b``

        """
        a, b = clean_name(a), clean_name(b)

        simple = float(fuzz.ratio(a, b) * self.weight["simple"])
        partial = float(fuzz.partial_ratio(a, b) * self.weight["partial"])

        return self.combine_scores(simple, partial, mode=mode)

    @staticmethod
    def combine_scores(score_1, score_2, mode="average"):
        """Get a combined fuzz score

        Parameters
        ----------
        score_1 : float
            A fuzz ratio score
        score_2 : float
            Another fuzz ratio score
        mode : str, optional
            Method for combining ``score_1`` and ``score_2``.
            Options are 'geom_mean', 'product', and 'average'

        Returns
        -------
        float
            Combined score

        """
        if mode == "geom_mean":
            return (score_1 * score_2) ** 0.5
        elif mode == "product":
            return score_1 * score_2 / 100.0
        else:  # average
            return (score_1 + score_2) / 2.0

    def get_combined_fuzz_scores(self, string, list_of_strings):
        """Compare a string against many

        Parameters
        ----------
        string : str
            A string to compare against each string in ``list_of_strings``
        list_of_strings : list
            A list of strings for comparison

        Returns
        -------
        list
            A list of tuples (score, string) in order of score

        """
        scores = [
            self.get_combined_fuzz_score(string, string_b)
            for string_b in list_of_strings
        ]
        if scores:
            order_index = sorted(range(len(scores)), key=lambda k: scores[k])
            return [(scores[i], list_of_strings[i]) for i in order_index[::-1]]
