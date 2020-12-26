#!/usr/bin/env python
# -*- coding: utf-8 -*-

# threading_progress.py
"""
Generic classes to perform threading with a progress frame
"""
# Copyright (c) 2020 Dan Cutright
# This file is part of DVHA DICOM Editor, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVHA-DICOM-Editor

import wx
from pubsub import pub
from queue import Queue
from threading import Thread
from time import sleep


class ProgressFrame(wx.Dialog):
    """Create a window to display progress and begin provided worker"""

    def __init__(
        self,
        obj_list,
        action,
        close_msg=None,
        action_msg=None,
        action_gui_phrase="Processing",
        title="Progress",
        sub_gauge=False,
        kwargs=False,
        star_map=False,
    ):
        wx.Dialog.__init__(self, None)

        self.close_msg = close_msg
        self.worker_args = [
            obj_list,
            action,
            action_msg,
            action_gui_phrase,
            title,
            kwargs,
            star_map,
        ]
        self.action_gui_phrase = action_gui_phrase

        self.gauge = wx.Gauge(self, wx.ID_ANY, 100)
        self.sub_gauge = wx.Gauge(self, wx.ID_ANY, 100) if sub_gauge else None
        self.label = wx.StaticText(self, wx.ID_ANY, "Initializing...")
        self.sub_label = (
            wx.StaticText(self, wx.ID_ANY, "") if sub_gauge else None
        )

        self.__set_properties()
        self.__do_subscribe()
        self.__do_layout()

        self.run()

    def run(self):
        """Initiate layout in GUI and begin thread"""
        self.Show()
        ProgressFrameWorker(*self.worker_args)

    def __set_properties(self):
        self.SetMinSize((672, 100))

    def __do_subscribe(self):
        pub.subscribe(self.update, "progress_update")
        pub.subscribe(self.sub_update, "sub_progress_update")
        pub.subscribe(self.set_title, "progress_set_title")
        pub.subscribe(self.close, "progress_close")

    @staticmethod
    def __do_unsubscribe():
        pub.unsubAll(topicName="progress_update")
        pub.unsubAll(topicName="sub_progress_update")
        pub.unsubAll(topicName="progress_set_title")
        pub.unsubAll(topicName="progress_close")

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_objects = wx.BoxSizer(wx.VERTICAL)
        sizer_objects.Add(self.label, 0, 0, 0)
        sizer_objects.Add(self.gauge, 0, wx.EXPAND, 0)
        if self.sub_gauge is not None:
            sizer_objects.Add(self.sub_label, 0, 0, 0)
            sizer_objects.Add(self.sub_gauge, 0, wx.EXPAND, 0)
        sizer_wrapper.Add(sizer_objects, 0, wx.ALL | wx.EXPAND, 10)
        self.SetSizer(sizer_wrapper)
        self.Fit()
        self.Layout()
        self.Center()

    def set_title(self, msg):
        """

        Parameters
        ----------
        msg :


        Returns
        -------

        """
        wx.CallAfter(self.SetTitle, msg)

    def update(self, msg):
        """Update the progress message and gauge

        Parameters
        ----------
        msg : dict
            a dictionary with keys of 'label' and 'gauge' text and progress fraction, respectively

        Returns
        -------

        """
        label = msg["label"]
        wx.CallAfter(self.label.SetLabelText, label)
        wx.CallAfter(self.gauge.SetValue, int(100 * msg["gauge"]))

    def sub_update(self, msg):
        """

        Parameters
        ----------
        msg :


        Returns
        -------

        """
        label = msg["label"]
        wx.CallAfter(self.sub_label.SetLabelText, label)
        wx.CallAfter(self.sub_gauge.SetValue, int(100 * msg["gauge"]))

    def close(self):
        """Destroy layout in GUI and send message close message for parent"""
        if self.close_msg is not None:
            wx.CallAfter(pub.sendMessage, self.close_msg)
        self.__do_unsubscribe()
        wx.CallAfter(self.Destroy)


class ProgressFrameWorker(Thread):
    """Create a thread, perform action on each item in obj_list"""

    def __init__(
        self,
        obj_list,
        action,
        action_msg,
        action_gui_phrase,
        title,
        kwargs,
        star_map,
    ):
        Thread.__init__(self)

        pub.sendMessage("progress_set_title", msg=title)

        self.obj_list = obj_list
        self.obj_count = len(self.obj_list)
        self.action = action
        self.action_msg = action_msg
        self.action_gui_phrase = action_gui_phrase
        self.kwargs = kwargs
        self.star_map = star_map

        self.start()

    def run(self):
        """ """
        queue = self.get_queue()
        worker = Thread(target=self.target, args=[queue])
        worker.setDaemon(True)
        worker.start()
        queue.join()
        sleep(0.3)  # Allow time for user to see final progress in GUI
        pub.sendMessage("progress_close")

    def get_queue(self):
        """ """
        queue = Queue()
        for i, obj in enumerate(self.obj_list):
            msg = {
                "label": "%s (%s of %s)"
                % (self.action_msg, i + 1, len(self.obj_list)),
                "gauge": float(i / len(self.obj_list)),
            }
            queue.put((obj, msg))
        return queue

    def target(self, queue):
        """

        Parameters
        ----------
        queue :


        Returns
        -------

        """
        while queue.qsize():
            parameters = queue.get()
            self.do_action(*parameters)
            queue.task_done()

        msg = {"label": "Process Complete", "gauge": 1.0}
        wx.CallAfter(pub.sendMessage, "progress_update", msg=msg)

    def do_action(self, obj, msg):
        """

        Parameters
        ----------
        obj :

        msg :


        Returns
        -------

        """
        wx.CallAfter(pub.sendMessage, "progress_update", msg=msg)

        if self.kwargs:
            result = self.action(**obj)
        elif self.star_map:
            result = self.action(*obj)
        else:
            result = self.action(obj)
        if self.action_msg is not None:
            msg = {"obj": obj, "data": result}
            wx.CallAfter(pub.sendMessage, self.action_msg, msg=msg)
