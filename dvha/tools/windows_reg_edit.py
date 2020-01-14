# https://stackoverflow.com/questions/15128225/python-script-to-read-and-write-a-path-to-registry
# Accessed on May 31, 2019


import winreg
import sys
from os.path import basename


def set_reg(name, reg_path, value):
    try:
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, reg_path)
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(registry_key, name, 0, winreg.REG_DWORD, value)
        winreg.CloseKey(registry_key)
        return True
    except WindowsError:
        return False


def get_reg(name, reg_path):
    try:
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ)
        value, regtype = winreg.QueryValueEx(registry_key, name)
        winreg.CloseKey(registry_key)
        return value
    except WindowsError:
        return None


def set_ie_emulation_level(value=11001):
    # See this site for information on which values to use
    # https://docs.microsoft.com/en-us/previous-versions/windows/internet-explorer/ie-developer/general-info/ee330730(v=vs.85)#browser_emulation
    reg_path = r"Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION"
    set_reg(basename(sys.executable), reg_path, value)


def set_ie_lockdown_level(value=0):
    # Based on info from Venkatakrishnan at
    # https://stackoverflow.com/questions/44513580/powershell-how-to-allow-blocked-content-in-internet-explorer/44514051
    reg_path = r"Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_LOCALMACHINE_LOCKDOWN"
    set_reg(basename(sys.executable), reg_path, value)
