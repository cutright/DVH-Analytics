import wx


def data_table_to_csv(frame, title, data_table):
    # from https://wxpython.org/Phoenix/docs/html/wx.FileDialog.html

    with wx.FileDialog(frame, title, wildcard="CSV files (*.csv)|*.csv",
                       style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fileDialog:

        if fileDialog.ShowModal() == wx.ID_CANCEL:
            return

        pathname = fileDialog.GetPath()
        try:
            with open(pathname, 'w') as file:
                file.write(data_table.csv)
        except IOError:
            wx.LogError("Cannot save current data in file '%s'." % pathname)
