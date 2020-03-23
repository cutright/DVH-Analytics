from rapidfuzz import fuzz
from dvha.tools.roi_name_manager import clean_name


class ROINamePredictor:
    def __init__(self, roi_map, weight_simple=1., weight_partial=0.6, threshold=0):
        """
        :param roi_map: ROI map object
        :type roi_map: DatabaseROIs
        """
        self.roi_map = roi_map
        norm_weight = weight_partial + weight_simple
        self.weight = {'simple': 2 * weight_simple / norm_weight,
                       'partial': 2 * weight_partial / norm_weight}
        self.threshold = threshold

    def get_best_roi_match(self, roi, physician, return_score=False):
        physician_variations = self.roi_map.get_all_variations_of_physician(physician)
        fuzz_scores = self.get_combined_fuzz_scores(roi, physician_variations)
        if fuzz_scores:
            predicted_variation, score = fuzz_scores[0][1], fuzz_scores[0][0]
            prediction = self.roi_map.get_physician_roi(physician, predicted_variation)
            if score > self.threshold:
                if return_score:
                    return prediction, score
                return prediction

    def get_combined_fuzz_score(self, a, b, mode='geom_mean'):
        a, b = clean_name(a), clean_name(b)

        simple = float(fuzz.ratio(a, b) * self.weight['simple'])
        partial = float(fuzz.partial_ratio(a, b) * self.weight['partial'])

        return self.combine_scores(simple, partial, mode=mode)

    @staticmethod
    def combine_scores(score_1, score_2, mode='average'):
        if mode == 'geom_mean':
            return (score_1 * score_2) ** 0.5
        elif mode == 'product':
            return score_1 * score_2 / 100.
        else:  # average
            return (score_1 + score_2) / 2.

    def get_combined_fuzz_scores(self, string, list_of_strings):
        scores = [self.get_combined_fuzz_score(string, string_b) for string_b in list_of_strings]
        if scores:
            order_index = sorted(range(len(scores)), key=lambda k: scores[k])
            return [(scores[i], list_of_strings[i]) for i in order_index[::-1]]
