from datetime import datetime
import wx

#------------------------------------------------

def GNU_notice(idx=0):
    '''
      function for printing GNU copyright statements
    '''
    if idx == 0:
        print '''
Experimenter Copyright (c) 2014 Jinook Oh, W. Tecumseh Fitch.
This program comes with ABSOLUTELY NO WARRANTY; for details run this program with the option `-w'.
This is free software, and you are welcome to redistribute it under certain conditions; run this program with the option `-c' for details.
'''
    elif idx == 1:
        print '''
THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW. EXCEPT WHEN OTHERWISE STATED IN WRITING THE COPYRIGHT HOLDERS AND/OR OTHER PARTIES PROVIDE THE PROGRAM "AS IS" WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU. SHOULD THE PROGRAM PROVE DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR OR CORRECTION.
'''
    elif idx == 2:
        print '''
You can redistribute this program and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
'''

#------------------------------------------------

def writeFile(fileName, txt):
# Function for writing texts into a file
    if debug: print 'writeFile'
    file = open(fileName, 'a')
    if file:
        file.write(txt)
        file.close()
    else:
        raise Exception("unable to open [" + fileName + "]")

#------------------------------------------------

def get_time_stamp():
    if debug: print 'get_time_stamp'
    ts = datetime.now()
    ts = ('%.4i_%.2i_%.2i_%.2i_%.2i_%.2i_%.6i')%(ts.year, 
                                                 ts.month, 
                                                 ts.day, 
                                                 ts.hour, 
                                                 ts.minute, 
                                                 ts.second, 
                                                 ts.microsecond)
    return ts

# ===========================================================

class PopupDialog(wx.Dialog):
# Class for showing any message to the participant
    def __init__(self, parent = None, id = -1, title = "Message", inString = "", font = None, pos = None, size = (200, 150), cancel_btn = False):
        wx.Dialog.__init__(self, parent, id, title)
        self.SetSize(size)
        if pos == None: self.Center()
        else: self.SetPosition(pos)
        txt = wx.StaticText(self, -1, label = inString, pos = (20, 20))
        txt.SetSize(size)
        if font == None: font = wx.Font(12, wx.MODERN, wx.NORMAL, wx.FONTWEIGHT_NORMAL, False, "Arial", wx.FONTENCODING_SYSTEM)
        txt.SetFont(font)
        txt.Wrap(size[0]-30)
        okButton = wx.Button(self, wx.ID_OK, "OK")
        b_size = okButton.GetSize()
        okButton.SetPosition((size[0] - b_size[0] - 20, size[1] - b_size[1] - 40))
        okButton.SetDefault()
        if cancel_btn == True:
            cancelButton = wx.Button(self, wx.ID_CANCEL, "Cancel")
            b_size = cancelButton.GetSize()
            cancelButton.SetPosition((size[0] - b_size[0]*2 - 40, size[1] - b_size[1] - 40))
        self.Center()




