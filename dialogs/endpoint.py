#!/usr/bin/env python3
# -*- coding: UTF-8 -*-


import wx


class EndpointDialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        wx.Dialog.__init__(self, None, title=kwds['title'])

        self.combo_box_output = wx.ComboBox(self, wx.ID_ANY,
                                            choices=["Dose (Gy)", "Dose(%)", "Volume (cc)", "Volume (%)"],
                                            style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.text_input = wx.TextCtrl(self, wx.ID_ANY, "")
        self.radio_box_units = wx.RadioBox(self, wx.ID_ANY, "", choices=["cc ", "% "], majorDimension=1,
                                           style=wx.RA_SPECIFY_ROWS)
        self.button_ok = wx.Button(self, wx.ID_OK, "OK")
        self.button_cancel = wx.Button(self, wx.ID_CANCEL, "Cancel")

        self.Bind(wx.EVT_COMBOBOX, self.combo_box_ticker, id=self.combo_box_output.GetId())
        self.Bind(wx.EVT_TEXT, self.text_input_ticker, id=self.text_input.GetId())
        self.Bind(wx.EVT_RADIOBOX, self.radio_box_ticker, id=self.radio_box_units.GetId())

        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        self.radio_box_units.SetSelection(0)

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons_wrapper = wx.BoxSizer(wx.HORIZONTAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, ""), wx.HORIZONTAL)
        sizer_input_units = wx.BoxSizer(wx.VERTICAL)
        sizer_input_value = wx.BoxSizer(wx.VERTICAL)
        sizer_output = wx.BoxSizer(wx.VERTICAL)
        label_ouput = wx.StaticText(self, wx.ID_ANY, "Output:")
        sizer_output.Add(label_ouput, 0, wx.BOTTOM | wx.EXPAND, 8)
        sizer_output.Add(self.combo_box_output, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_output, 1, wx.ALL | wx.EXPAND, 5)
        self.label_input_value = wx.StaticText(self, wx.ID_ANY, "Input Volume (cc):")
        sizer_input_value.Add(self.label_input_value, 0, wx.BOTTOM | wx.EXPAND, 8)
        sizer_input_value.Add(self.text_input, 0, wx.EXPAND | wx.LEFT, 5)
        sizer_input.Add(sizer_input_value, 1, wx.ALL | wx.EXPAND, 5)
        label_input_units = wx.StaticText(self, wx.ID_ANY, "Input Units:")
        sizer_input_units.Add(label_input_units, 0, wx.BOTTOM | wx.EXPAND, 3)
        sizer_input_units.Add(self.radio_box_units, 0, wx.EXPAND, 0)
        sizer_input.Add(sizer_input_units, 1, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper.Add(sizer_input, 0, wx.ALL | wx.EXPAND, 10)
        self.text_short_hand = wx.StaticText(self, wx.ID_ANY, "\tShort-hand: ")
        sizer_wrapper.Add(self.text_short_hand, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_ok, 0, wx.ALL, 5)
        sizer_buttons.Add(self.button_cancel, 0, wx.ALL | wx.EXPAND, 5)
        sizer_buttons_wrapper.Add(sizer_buttons, 0, wx.ALL | wx.EXPAND, 5)
        sizer_wrapper.Add(sizer_buttons_wrapper, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        self.SetSizer(sizer_wrapper)
        sizer_wrapper.Fit(self)
        self.Layout()
        self.Center()

    def combo_box_ticker(self, evt):
        self.update_radio_box_choices()
        self.update_label_input()
        self.update_short_hand()

    def text_input_ticker(self, evt):
        self.update_short_hand()

    def radio_box_ticker(self, evt):
        self.update_label_input()
        self.update_short_hand()

    def update_label_input(self):
        new_label = "%s (%s):" % (['Input Dose', 'Input Volume']['Dose' in self.combo_box_output.GetValue()],
                                  self.radio_box_units.GetItemLabel(self.radio_box_units.GetSelection()))
        self.label_input_value.SetLabelText(new_label)

    def update_radio_box_choices(self):
        choice_1 = ['Gy', 'cc']['Dose' in self.combo_box_output.GetValue()]
        self.radio_box_units.SetItemLabel(0, choice_1)

    def update_short_hand(self):
        short_hand = ['\tShort-hand: ']
        if self.text_input.GetValue():
            try:
                str(float(self.text_input.GetValue()))
                short_hand.extend([['V_', 'D_']['Dose' in self.combo_box_output.GetValue()],
                                   self.text_input.GetValue(),
                                   self.radio_box_units.GetItemLabel(self.radio_box_units.GetSelection()).strip()])
            except ValueError:
                pass
        self.text_short_hand.SetLabelText(''.join(short_hand))

    @property
    def is_endpoint_valid(self):
        return bool(len(self.short_hand_label))

    @property
    def short_hand_label(self):
        return self.text_short_hand.GetLabel().replace('\tShort-hand: ', '').strip()

    @property
    def output_type(self):
        return ['absolute', 'relative']['%' in self.combo_box_output.GetValue()]

    @property
    def input_type(self):
        return ['absolute', 'relative'][self.radio_box_units.GetSelection()]

    @property
    def units_in(self):
        return self.radio_box_units.GetItemLabel(self.radio_box_units.GetSelection()).replace('%', '').strip()

    @property
    def units_out(self):
        return self.combo_box_output.GetValue().split('(')[1][:-1].replace('%', '').strip()

    @property
    def input_value(self):
        try:
            return float(self.text_input.GetValue())
        except ValueError:
            return 0.

    @property
    def endpoint_row(self):
        return [self.short_hand_label,
                self.output_type,
                self.input_type,
                self.input_value,
                self.units_in,
                self.units_out]
