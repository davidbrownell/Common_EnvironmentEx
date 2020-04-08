# This file is generated by wxPython's SIP generator.  Do not edit by hand.
#
# Copyright: (c) 2018 by Total Control Software
# License:   wxWindows License

"""
The ``wx.adv`` module contains classes which are more advanced and/or less
commonly used than those in the core namespace. They are provided in a
separate module to help reduce overhead and dependencies for those
applications which do not need any of these classes.
"""

from ._adv import *

import wx

AboutDialogInfo.HasLicense = AboutDialogInfo.HasLicence
AboutDialogInfo.GetLicense = AboutDialogInfo.GetLicence
AboutDialogInfo.License = AboutDialogInfo.Licence

def _DateEvent_PyGetDate(self):
    """
    Return the date as a Python datetime.date object.
    """
    return wx.wxdate2pydate(self.GetDate())
DateEvent.PyGetDate = wx.deprecated(_DateEvent_PyGetDate, "Use GetDate instead.")
del _DateEvent_PyGetDate
DateEvent.PySetDate = wx.deprecated(DateEvent.SetDate, 'Use SetDate instead.')

EVT_DATE_CHANGED = wx.PyEventBinder( wxEVT_DATE_CHANGED, 1 )
EVT_TIME_CHANGED = wx.PyEventBinder( wxEVT_TIME_CHANGED, 1 )

def _CalendarCtrl_PyGetDate(self):
    """
    Return the date as a Python datetime.date object.
    """
    return wx.wxdate2pydate(self.GetDate())
CalendarCtrl.PyGetDate = wx.deprecated(_CalendarCtrl_PyGetDate, "Use GetDate instead.")
del _CalendarCtrl_PyGetDate
CalendarCtrl.PySetDate = wx.deprecated(CalendarCtrl.SetDate, 'Use SetDate instead.')
CalendarCtrl.PySetDateRange = wx.deprecated(CalendarCtrl.SetDateRange, 'Use SetDateRange instead.')

def _GenericCalendarCtrl_PyGetDate(self):
    """
    Return the date as a Python datetime.date object.
    """
    return wx.wxdate2pydate(self.GetDate())
GenericCalendarCtrl.PyGetDate = wx.deprecated(_GenericCalendarCtrl_PyGetDate, "Use GetDate instead.")
del _GenericCalendarCtrl_PyGetDate
GenericCalendarCtrl.PySetDate = wx.deprecated(GenericCalendarCtrl.SetDate, 'Use SetDate instead.')
GenericCalendarCtrl.PySetDateRange = wx.deprecated(GenericCalendarCtrl.SetDateRange, 'Use SetDateRange instead.')

EVT_CALENDAR =                 wx.PyEventBinder( wxEVT_CALENDAR_DOUBLECLICKED, 1)
EVT_CALENDAR_SEL_CHANGED =     wx.PyEventBinder( wxEVT_CALENDAR_SEL_CHANGED, 1)
EVT_CALENDAR_WEEKDAY_CLICKED = wx.PyEventBinder( wxEVT_CALENDAR_WEEKDAY_CLICKED, 1)
EVT_CALENDAR_PAGE_CHANGED =    wx.PyEventBinder( wxEVT_CALENDAR_PAGE_CHANGED, 1)
EVT_CALENDAR_WEEK_CLICKED =    wx.PyEventBinder( wxEVT_CALENDAR_WEEK_CLICKED, 1)

# These are deprecated, will be removed later...
EVT_CALENDAR_DAY =             wx.PyEventBinder( wxEVT_CALENDAR_DAY_CHANGED, 1)
EVT_CALENDAR_MONTH =           wx.PyEventBinder( wxEVT_CALENDAR_MONTH_CHANGED, 1)
EVT_CALENDAR_YEAR =            wx.PyEventBinder( wxEVT_CALENDAR_YEAR_CHANGED, 1)

EVT_HYPERLINK = wx.PyEventBinder( wxEVT_HYPERLINK, 1 )

# deprecated wxEVT alias
wxEVT_COMMAND_HYPERLINK  = wxEVT_HYPERLINK

EVT_TASKBAR_MOVE = wx.PyEventBinder (         wxEVT_TASKBAR_MOVE )
EVT_TASKBAR_LEFT_DOWN = wx.PyEventBinder (    wxEVT_TASKBAR_LEFT_DOWN )
EVT_TASKBAR_LEFT_UP = wx.PyEventBinder (      wxEVT_TASKBAR_LEFT_UP )
EVT_TASKBAR_RIGHT_DOWN = wx.PyEventBinder (   wxEVT_TASKBAR_RIGHT_DOWN )
EVT_TASKBAR_RIGHT_UP = wx.PyEventBinder (     wxEVT_TASKBAR_RIGHT_UP )
EVT_TASKBAR_LEFT_DCLICK = wx.PyEventBinder (  wxEVT_TASKBAR_LEFT_DCLICK )
EVT_TASKBAR_RIGHT_DCLICK = wx.PyEventBinder ( wxEVT_TASKBAR_RIGHT_DCLICK )
EVT_TASKBAR_CLICK =  wx.PyEventBinder (       wxEVT_TASKBAR_CLICK )
EVT_TASKBAR_BALLOON_TIMEOUT = wx.PyEventBinder ( wxEVT_TASKBAR_BALLOON_TIMEOUT )
EVT_TASKBAR_BALLOON_CLICK = wx.PyEventBinder ( wxEVT_TASKBAR_BALLOON_CLICK )

SPLASH_CENTER_ON_PARENT = SPLASH_CENTRE_ON_PARENT
SPLASH_CENTER_ON_SCREEN = SPLASH_CENTRE_ON_SCREEN
SPLASH_NO_CENTER = SPLASH_NO_CENTRE

EVT_SASH_DRAGGED = wx.PyEventBinder( wxEVT_SASH_DRAGGED, 1 )
EVT_SASH_DRAGGED_RANGE = wx.PyEventBinder( wxEVT_SASH_DRAGGED, 2 )

EVT_QUERY_LAYOUT_INFO = wx.PyEventBinder( wxEVT_QUERY_LAYOUT_INFO )
EVT_CALCULATE_LAYOUT = wx.PyEventBinder( wxEVT_CALCULATE_LAYOUT )

PyWizardPage = wx.deprecated(WizardPage, 'Use WizardPage instead.')

EVT_WIZARD_BEFORE_PAGE_CHANGED  = wx.PyEventBinder( wxEVT_WIZARD_BEFORE_PAGE_CHANGED, 1)
EVT_WIZARD_PAGE_CHANGED  = wx.PyEventBinder( wxEVT_WIZARD_PAGE_CHANGED, 1)
EVT_WIZARD_PAGE_CHANGING = wx.PyEventBinder( wxEVT_WIZARD_PAGE_CHANGING, 1)
EVT_WIZARD_CANCEL        = wx.PyEventBinder( wxEVT_WIZARD_CANCEL, 1)
EVT_WIZARD_HELP          = wx.PyEventBinder( wxEVT_WIZARD_HELP, 1)
EVT_WIZARD_FINISHED      = wx.PyEventBinder( wxEVT_WIZARD_FINISHED, 1)
EVT_WIZARD_PAGE_SHOWN    = wx.PyEventBinder( wxEVT_WIZARD_PAGE_SHOWN, 1)

PseudoDC.BeginDrawing = wx.deprecated(lambda *args: None, 'BeginDrawing has been removed.')
PseudoDC.EndDrawing = wx.deprecated(lambda *args: None, 'EndDrawing has been removed.')
PseudoDC.FloodFillPoint = wx.deprecated(PseudoDC.FloodFill, 'Use FloodFill instead.')
PseudoDC.DrawLinePoint = wx.deprecated(PseudoDC.DrawLine, 'Use DrawLine instead.')
PseudoDC.CrossHairPoint = wx.deprecated(PseudoDC.CrossHair, 'Use CrossHair instead.')
PseudoDC.DrawArcPoint = wx.deprecated(PseudoDC.DrawArc, 'Use DrawArc instead.')
PseudoDC.DrawCheckMarkRect = wx.deprecated(PseudoDC.DrawCheckMark, 'Use DrawArc instead.')
PseudoDC.DrawEllipticArcPointSize = wx.deprecated(PseudoDC.DrawEllipticArc, 'Use DrawEllipticArc instead.')
PseudoDC.DrawPointPoint = wx.deprecated(PseudoDC.DrawPoint, 'Use DrawPoint instead.')
PseudoDC.DrawRectangleRect = wx.deprecated(PseudoDC.DrawRectangle, 'Use DrawRectangle instead.')
PseudoDC.DrawRectanglePointSize = wx.deprecated(PseudoDC.DrawRectangle, 'Use DrawRectangle instead.')
PseudoDC.DrawRoundedRectangleRect = wx.deprecated(PseudoDC.DrawRoundedRectangle, 'Use DrawRectangle instead.')
PseudoDC.DrawRoundedRectanglePointSize = wx.deprecated(PseudoDC.DrawRoundedRectangle, 'Use DrawRectangle instead.')
PseudoDC.DrawCirclePoint = wx.deprecated(PseudoDC.DrawCircle, 'Use DrawCircle instead.')
PseudoDC.DrawEllipseRect = wx.deprecated(PseudoDC.DrawEllipse, 'Use DrawEllipse instead.')
PseudoDC.DrawEllipsePointSize = wx.deprecated(PseudoDC.DrawEllipse, 'Use DrawEllipse instead.')
PseudoDC.DrawIconPoint = wx.deprecated(PseudoDC.DrawIcon, 'Use DrawIcon instead.')
PseudoDC.DrawBitmapPoint = wx.deprecated(PseudoDC.DrawBitmap, 'Use DrawBitmap instead.')
PseudoDC.DrawTextPoint = wx.deprecated(PseudoDC.DrawText, 'Use DrawText instead.')
PseudoDC.DrawRotatedTextPoint = wx.deprecated(PseudoDC.DrawRotatedText, 'Use DrawRotatedText instead.')
PseudoDC.DrawImageLabel = wx.deprecated(PseudoDC.DrawLabel, 'Use DrawLabel instead.')

