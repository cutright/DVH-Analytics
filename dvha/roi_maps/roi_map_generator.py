from dvha.paths import TG263_CSV


class ROIMapGenerator:
    def __init__(self):
        self.__load_tg_263()

    def __load_tg_263(self):
        with open(TG263_CSV, 'r') as doc:
            keys = doc.readline().split(',')
            keys = [key.strip() for key in keys]
            self.tg_263 = {key: [] for key in keys}
            for line in doc:
                values = line.split(',')
                values += [''] * (len(keys) - len(values))
                for col, value in enumerate(values):
                    self.tg_263[keys[col]].append(value.strip())
            self.keys = keys

    def get_group(self, key, value):
        """
        Get TG263 data with a filter
        :param key: column
        :param value: value of column
        :return: subset of tg_263 rows where column `key` equals `value`
        :type: dict
        """
        data = {key: [] for key in self.keys}
        for row in range(len(self.tg_263[self.keys[0]])):
            if self.tg_263[key][row] == value:
                for k in self.keys:
                    data[k].append(self.tg_263[k][row])
        return data

