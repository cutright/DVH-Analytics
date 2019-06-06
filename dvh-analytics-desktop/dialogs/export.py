import wx


def export_csv(frame, title, csv_data):
    # from https://wxpython.org/Phoenix/docs/html/wx.FileDialog.html

    with wx.FileDialog(frame, title, wildcard="CSV files (*.csv)|*.csv",
                       style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

        if fileDialog.ShowModal() == wx.ID_CANCEL:
            return

        pathname = fileDialog.GetPath()
        try:
            with open(pathname, 'w') as file:
                file.write(csv_data)
        except IOError:
            wx.LogError("Cannot save current data in file '%s'." % pathname)
