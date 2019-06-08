import wx


class SQLError(Exception):
    def __init__(self, error_message, failed_sql_command):
        """
        Custom exception class to catch query and update failures in database editor
        :param error_message: The message to be displayed in the SQLErrorDialog
        :type error_message: str
        :param failed_sql_command: the SQL command that failed
        :type failed_sql_command: str
        """
        try:
            self.message = error_message.split('\n')[0]
        except Exception as e:
            print(e)
            self.message = error_message
        self.sql_command = failed_sql_command

    def __str__(self):
        return self.message


class ROIVariationError(Exception):
    def __init__(self, error_message):
        self.message = error_message

    def __str__(self):
        return self.message


class ErrorDialog:
    def __init__(self, parent, message, caption, flags=wx.ICON_ERROR | wx.OK | wx.OK_DEFAULT):
        """
        This class allows error messages to be called with a one-liner else-where
        :param parent: wx parent object
        :param message: error message
        :param caption: error title
        :param flags: flags for wx.MessageDialog
        """
        self.dlg = wx.MessageDialog(parent, message, caption, flags)
        self.dlg.Center()
        self.dlg.ShowModal()
        self.dlg.Destroy()


class SQLErrorDialog(ErrorDialog):
    def __init__(self, parent, dvh_sql_error):
        """
        Error dialog using custom SQLError class
        :param parent: the wx parent object
        :param dvh_sql_error: SQLError exception class
        :type dvh_sql_error: SQLError
        """
        ErrorDialog.__init__(self, parent, str(dvh_sql_error), "SQL Syntax Error")


class ROIVariationErrorDialog(ErrorDialog):
    def __init__(self, parent, roi_variation_error):
        """
        Error dialog using custom ROIVariationError class
        :param parent: the wx parent object
        :param roi_variation_error: ROIVariationError exception class
        :type roi_variation_error: ROIVariationError
        """
        ErrorDialog.__init__(self, parent, str(roi_variation_error), "ROI Variation Error")
