#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#


from tools.utilities import initialize_directories_and_settings, is_windows


def start():

    # Default webview emulation for wx.html2 in MS Windows is IE7 and javascript is not supported
    # Change IE emulation level to IE11
    if is_windows():
        from tools.windows_reg_edit import set_ie_emulation_level
        set_ie_emulation_level()

    initialize_directories_and_settings()

    from dvha_app import MainApp  # requires directories and settings to be initialized
    app = MainApp(0)
    app.MainLoop()


if __name__ == "__main__":
    start()
