# This file is generated by wxPython's SIP generator.  Do not edit by hand.
#
# Copyright: (c) 2018 by Total Control Software
# License:   wxWindows License

"""
The ``wx.html2`` module includes a widget class and supporting classes that
wraps native browser components on the system, therefore providing a fully
featured HTML rendering component including the latest HTML, Javascript and
CSS standards. Since platform-specific back-ends are used (Microsoft Trident,
WebKit webView, etc.) there will be some difference in ability and behaviors,
but these classes will minimize those differences as much as possible.
"""

from ._html2 import *

import wx

EVT_WEBVIEW_NAVIGATING = wx.PyEventBinder( wxEVT_WEBVIEW_NAVIGATING, 1 )
EVT_WEBVIEW_NAVIGATED = wx.PyEventBinder( wxEVT_WEBVIEW_NAVIGATED, 1 )
EVT_WEBVIEW_LOADED = wx.PyEventBinder( wxEVT_WEBVIEW_LOADED, 1 )
EVT_WEBVIEW_ERROR = wx.PyEventBinder( wxEVT_WEBVIEW_ERROR, 1 )
EVT_WEBVIEW_NEWWINDOW = wx.PyEventBinder( wxEVT_WEBVIEW_NEWWINDOW, 1 )
EVT_WEBVIEW_TITLE_CHANGED = wx.PyEventBinder( wxEVT_WEBVIEW_TITLE_CHANGED, 1 )

# deprecated wxEVT aliases
wxEVT_COMMAND_WEBVIEW_NAVIGATING     = wxEVT_WEBVIEW_NAVIGATING
wxEVT_COMMAND_WEBVIEW_NAVIGATED      = wxEVT_WEBVIEW_NAVIGATED
wxEVT_COMMAND_WEBVIEW_LOADED         = wxEVT_WEBVIEW_LOADED
wxEVT_COMMAND_WEBVIEW_ERROR          = wxEVT_WEBVIEW_ERROR
wxEVT_COMMAND_WEBVIEW_NEWWINDOW      = wxEVT_WEBVIEW_NEWWINDOW
wxEVT_COMMAND_WEBVIEW_TITLE_CHANGED  = wxEVT_WEBVIEW_TITLE_CHANGED

