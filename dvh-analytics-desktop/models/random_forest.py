import wx
from threading import Thread
from pubsub import pub
from tools.stats import get_random_forest
from models.plot import PlotRandomForest


class RandomForestFrame(wx.Frame):
    def __init__(self, y, y_predict, mse, *args, **kwds):
        wx.Frame.__init__(self, None, *args, **kwds)

        self.y, self.y_predict = y, y_predict
        self.mse = mse

        self.plot = PlotRandomForest(self, y, y_predict, mse)

        self.SetSize((882, 749))
        self.spin_ctrl_trees = wx.SpinCtrl(self, wx.ID_ANY, "100", min=1, max=1000)
        self.spin_ctrl_features = wx.SpinCtrl(self, wx.ID_ANY, "2", min=2, max=100)

        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        self.SetTitle("Random Forest")
        self.spin_ctrl_trees.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ".SF NS Text"))
        self.spin_ctrl_trees.SetToolTip("n_estimators")
        self.spin_ctrl_features.SetToolTip("Maximum number of features when splitting")

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_input_and_plot = wx.BoxSizer(wx.VERTICAL)
        sizer_hyper_parameters = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Hyper-parameters:"), wx.HORIZONTAL)
        sizer_features = wx.BoxSizer(wx.HORIZONTAL)
        sizer_trees = wx.BoxSizer(wx.HORIZONTAL)
        label_trees = wx.StaticText(self, wx.ID_ANY, "Number of Trees:")
        sizer_trees.Add(label_trees, 0, wx.ALL, 5)
        sizer_trees.Add(self.spin_ctrl_trees, 0, wx.ALL, 5)
        sizer_hyper_parameters.Add(sizer_trees, 1, wx.EXPAND, 0)
        label_features = wx.StaticText(self, wx.ID_ANY, "Max feature count:")
        sizer_features.Add(label_features, 0, wx.ALL, 5)
        sizer_features.Add(self.spin_ctrl_features, 0, wx.ALL, 5)
        sizer_hyper_parameters.Add(sizer_features, 1, wx.EXPAND, 0)
        sizer_input_and_plot.Add(sizer_hyper_parameters, 0, wx.EXPAND, 0)
        sizer_input_and_plot.Add(self.plot.layout)
        sizer_wrapper.Add(sizer_input_and_plot, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer_wrapper)
        self.Layout()


class RandomForestWorker(Thread):
    def __init__(self, X, y, n_estimators=None, max_features=None):
        Thread.__init__(self)
        self.X, self.y = X, y

        self.kwargs = {}
        if n_estimators is not None:
            self.kwargs['n_estimators'] = n_estimators
        if max_features is not None:
            self.kwargs['max_features'] = max_features
        self.start()  # start the thread

    def run(self):
        print('begin random forest')
        y_predict, mse = get_random_forest(self.X, self.y, **self.kwargs)
        print('finished random forest')
        msg = {'y_predict': y_predict, 'mse': mse}
        print(msg)
        wx.CallAfter(pub.sendMessage, "random_forest_complete", msg=msg)
