from fuzzywuzzy import fuzz
from dvha.tools.roi_name_manager import clean_name, DatabaseROIs


class ROINamePredictor:
    def __init__(self, roi_map, weight_simple=1., weight_partial=0.6, threshold=0.3):
        """
        :param roi_map: ROI map object
        :type roi_map: DatabaseROIs
        """
        self.roi_map = roi_map
        self.weight = {'simple': weight_simple, 'partial': weight_partial}
        self.threshold = threshold

    def get_best_roi_match(self, roi, physician):
        physician_rois = self.roi_map.get_physician_rois(physician)
        fuzz_scores = self.get_combined_fuzz_scores(roi, physician_rois)
        if fuzz_scores:
            return fuzz_scores[0][1]

    def get_combined_fuzz_score(self, a, b):
        a = clean_name(a)
        b = clean_name(b)

        simple = fuzz.ratio(a, b) * self.weight['simple']
        partial = fuzz.partial_ratio(a, b) * self.weight['partial']
        combined = float(simple) * float(partial) / 10000.
        return combined

    def get_combined_fuzz_scores(self, string, list_of_strings):
        scores = [self.get_combined_fuzz_score(string, string_b) for string_b in list_of_strings]
        if scores:
            order_index = sorted(range(len(scores)), key=lambda k: scores[k])
            return [(scores[i], list_of_strings[i]) for i in order_index[::-1]]
