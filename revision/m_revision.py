'''
App for revising data after video analysis on the head turning experi-
ment of common marmoset monkeys.
This app 
  shows a graph of selected CSV file (head direction data)
    with browsing functionalities.
  shows a frame image of the current frame in a specified folder
  has three buttons for the revision, namely dropping data, rotating
    for 180 degrees, and liner interpolation.

----------------------------------------------------------------------
Copyright (C) 2014 Jinook Oh, W. Tecumseh Fitch for ERC Advanced Grant 
SOMACCA # 230604 
- Contact: jinook.oh@univie.ac.at, tecumseh.fitch@univie.ac.at

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import os, plistlib
from glob import glob
from copy import copy
from math import ceil
from random import uniform
from datetime import datetime
from time import time
from shutil import copyfile, rmtree
from sys import argv

import wx
from m_rev_subject import MarmosetSubjectRevision

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
    '''
        Function for writing texts into a file
    '''
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

# ======================================================

class MRA_Main_Frame(wx.Frame):
    def __init__(self):
        '''
        Main frame of the app.
        '''
        self.w_size = (1200, 700)
        self.stimuli = dict( repetition = ['ABA_1', 'ABBA_1', 'ABBBBA_1', 'ABBBBA_2'], 
                             extension = ['ABBBA_1', 'ABBBA_2', 'ABBBBBA_1', 'ABBBBBA_2'], 
                             missing_first = ['BA_1', 'BBA_1', 'BBBA_1', 'BBBBA_1'], 
                             missing_last = ['AB_1', 'ABB_1', 'ABBB_1', 'ABBBB_1'] )

        wx.Frame.__init__(self, None, -1, "M_Revision_&_Analysis", pos = (0,20), size = (self.w_size[0],self.w_size[1]), style = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        self.Center()
        self.panel = wx.Panel(self, pos = (0,0), size = self.w_size)
        self.panel.SetBackgroundColour( wx.BLACK )

        ### Connecting key-inputs with some functions
        help_BtnID = wx.NewId()
        exit_BtnID = wx.NewId()
        save_BtnID = wx.NewId()
        saveGraph_BtnID = wx.NewId()
        right_BtnID = wx.NewId()
        left_BtnID = wx.NewId()
        rj_BtnID = wx.NewId()
        lj_BtnID = wx.NewId()
        space_BtnID = wx.NewId()
        ts_BtnID = wx.NewId()
        del_BtnID = wx.NewId()
        rotate180_BtnID = wx.NewId()
        applyHD_BtnID = wx.NewId() # applyHD : make the hypothetical lines to the real data lines
        self.Bind(wx.EVT_MENU, self.onHelp, id = help_BtnID)
        self.Bind(wx.EVT_MENU, self.onExit, id = exit_BtnID)
        self.Bind(wx.EVT_MENU, self.onSave, id = save_BtnID)
        self.Bind(wx.EVT_MENU, self.onSaveGraph, id = saveGraph_BtnID)
        self.Bind(wx.EVT_MENU, self.onRight, id = right_BtnID)
        self.Bind(wx.EVT_MENU, self.onLeft, id = left_BtnID)
        self.Bind(wx.EVT_MENU, self.onRightJump, id = rj_BtnID)
        self.Bind(wx.EVT_MENU, self.onLeftJump, id = lj_BtnID)
        self.Bind(wx.EVT_MENU, self.onSpace, id = space_BtnID)
        self.Bind(wx.EVT_MENU, self.onToggleSelection, id = ts_BtnID)
        self.Bind(wx.EVT_MENU, self.onDeleteDataPoint, id = del_BtnID)
        self.Bind(wx.EVT_MENU, self.onRotate180, id = rotate180_BtnID)
        self.Bind(wx.EVT_MENU, self.onApplyHD, id = applyHD_BtnID)
        accel_tbl = wx.AcceleratorTable([ (wx.ACCEL_CMD, ord('H'), help_BtnID), 
                                          (wx.ACCEL_CMD, ord('Q'), exit_BtnID ), 
                                          (wx.ACCEL_CMD, ord('S'), save_BtnID ),
                                          (wx.ACCEL_CMD, ord('G'), saveGraph_BtnID ),
                                          (wx.ACCEL_NORMAL, wx.WXK_RIGHT, right_BtnID ), 
                                          (wx.ACCEL_NORMAL, wx.WXK_LEFT, left_BtnID ), 
                                          (wx.ACCEL_SHIFT, wx.WXK_RIGHT, rj_BtnID ), 
                                          (wx.ACCEL_SHIFT, wx.WXK_LEFT, lj_BtnID ),
                                          (wx.ACCEL_NORMAL, wx.WXK_SPACE, space_BtnID ),
                                          (wx.ACCEL_CMD, ord('T'), ts_BtnID ), 
                                          (wx.ACCEL_CMD, ord('D'), del_BtnID ), 
                                          (wx.ACCEL_CMD, ord('R'), rotate180_BtnID ), 
                                          (wx.ACCEL_CMD, ord('U'), applyHD_BtnID )])
        self.SetAcceleratorTable(accel_tbl)

        statbar = wx.StatusBar(self, -1)
        self.SetStatusBar(statbar)
        self.Bind(wx.EVT_CLOSE, self.onExit)

        wx.FutureCall(1, self.setup_notebook)

    #------------------------------------------------
        
    def setup_notebook(self):
        ### set up notebook 
        self.nb = wx.Notebook(self, size=(self.w_size[0],self.w_size[1]-30))
        self.page_trialRev = MarmosetTrialRevision(self.nb, 
                                                   size=(self.w_size[0]-20,self.w_size[1]-30))
        self.page_subjectRev = MarmosetSubjectRevision(self.nb, 
                                                       size=(self.w_size[0]-20,self.w_size[1]-30), 
                                                       cwd=CWD, 
                                                       output_dir=output_dir)
        self.nb.AddPage(self.page_trialRev, "Trial_Revision")
        self.nb.AddPage(self.page_subjectRev, "Subject_Review")

    #------------------------------------------------
        
    def show_msg_in_statbar(self, msg):
        self.SetStatusText(msg)
        wx.FutureCall(5000, self.SetStatusText, "") # delete it after a while

    #------------------------------------------------

    def show_msg(self, msg, size=(300,200)):
        err_msg = PopupDialog(inString=msg, size=size)
        err_msg.ShowModal()
        err_msg.Destroy()

    #------------------------------------------------

    def onSave(self, event):
        page = self.nb.GetPageText(self.nb.GetSelection())
        if page == 'Trial_Revision':
            self.page_trialRev.onSave()

    #------------------------------------------------

    def onSaveGraph(self, event):
        page = self.nb.GetPageText(self.nb.GetSelection())
        if page == 'Trial_Revision':
            self.page_trialRev.onSaveGraph()

    #------------------------------------------------

    def onRight(self, event):
        page = self.nb.GetPageText(self.nb.GetSelection())
        if page == 'Trial_Revision':
            self.page_trialRev.onRight(None)

    #------------------------------------------------

    def onLeft(self, event):
        page = self.nb.GetPageText(self.nb.GetSelection())
        if page == 'Trial_Revision':
            self.page_trialRev.onLeft()

    #------------------------------------------------

    def onRightJump(self, event):
        page = self.nb.GetPageText(self.nb.GetSelection())
        if page == 'Trial_Revision':
            self.page_trialRev.onRightJump()

    #------------------------------------------------

    def onLeftJump(self, event):
        page = self.nb.GetPageText(self.nb.GetSelection())
        if page == 'Trial_Revision':
            self.page_trialRev.onLeftJump()

    #------------------------------------------------

    def onSpace(self, event):
        page = self.nb.GetPageText(self.nb.GetSelection())
        if page == 'Trial_Revision':
            self.page_trialRev.onSpace()

    #------------------------------------------------

    def onToggleSelection(self, event):
        page = self.nb.GetPageText(self.nb.GetSelection())
        if page == 'Trial_Revision':
            self.page_trialRev.onToggleSelection()

    #------------------------------------------------

    def onDeleteDataPoint(self, event):
        page = self.nb.GetPageText(self.nb.GetSelection())
        if page == 'Trial_Revision':
            self.page_trialRev.onGraphBtnClick('minus')

    #------------------------------------------------

    def onRotate180(self, event):
        page = self.nb.GetPageText(self.nb.GetSelection())
        if page == 'Trial_Revision':
            self.page_trialRev.onGraphBtnClick('rotate180')

    #------------------------------------------------

    def onApplyHD(self, event):
        page = self.nb.GetPageText(self.nb.GetSelection())
        if page == 'Trial_Revision':
            self.page_trialRev.onGraphBtnClick('applyHD')

    #------------------------------------------------

    def onHelp(self, event):
        page = self.nb.GetPageText(self.nb.GetSelection())
        if page == 'Trial_Revision':
            _msg = "HELP - Trial_Revision\n\n\n"
            _msg += "Cmd + Q : Quit the program\n\n"
            _msg += "Cmd + S : Save the revised trial data\n\n"
            _msg += "Cmd + G : Save the trial data graph (as PNG file)\n\n"
            _msg += "Right arrow : Move forward for 1 frame\n\n"
            _msg += "Left arrow : Move backward for 1 frame\n\n"
            _msg += "Shift + Right arrow : Move forward for 50 frames\n\n"
            _msg += "Shift + Left arrow : Move backward for 50 frames\n\n"
            _msg += "Spacebar : Keep moving forward\n\n"
            _msg += "Cmd + T : Selection begin/end\n\n"
            _msg += "Cmd + D : Drop the data (becoming -1) of the selected frame(s)\n\n"
            _msg += "Cmd + R : Rotate the angle of the selected frame(s)\n\n"
            _msg += "Cmd + U : Make the interpolated data lines to the real data lines\n\n"
            self.show_msg(_msg, size=(500, 540))

    #------------------------------------------------

    def onExit(self, event):
        self.Destroy()

#====================================================

class MarmosetTrialRevision(wx.Panel):

    def __init__(self, parent, size):
        if debug: print 'MarmosetRevision.__init__'
        
        self.main_frame = parent.GetParent()
        self.w_size = size
        wx.Panel.__init__(self, parent, size=self.w_size)
        '''
        wx.Frame.__init__(self, None, -1, "M_Revision", pos = (0,20), size = (self.w_size[0],self.w_size[1]), style = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        self.Center()
        '''
        #self.panel = wx.Panel(self, pos = (0,0), size = (self.w_size[0],self.w_size[1]))
        self.SetBackgroundColour( wx.BLACK )
        
        img_p_pos = (10, 236)
        img_p_sz = (640/3*2, 540/3*2)
        self.img_p_sz = img_p_sz
        self.img_panel = wx.Panel(self, pos=img_p_pos, size=img_p_sz)
        self.img_panel.SetBackgroundColour( (50,50,50) )
        self.g_pos = (img_p_sz[0]+30-2, img_p_pos[1])
        self.g_size = (self.w_size[0]-img_p_sz[0]-30, img_p_sz[1])
        self.graph_panel = wx.Panel(self, pos=self.g_pos, size=(self.g_size[0], self.g_size[1]))
        self.graph_panel.SetBackgroundColour( (100,100,100) )

        self.default_frame_cnt = 1000
        self.timer1 = None
        self.flag_run = False
        self.new_CSV_fp = None
        self.dir_path = None
        self.direction_data = {}
        self.d_data_idx = [-1, -1] # [beginning, end]. range of indices of the displayed (on the graph) data
        self.d_selection = [-1, -1] # [beginning, end]. range of indices of selection
        self.font_small = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False)
        self.stimuli = self.main_frame.stimuli

        posX = 10; posY = 5
        sTxt = wx.StaticText( self, 
                              id=-1, 
                              pos = (posX, posY), 
                              label = 'Choose a CSV file to be revised' )
        sTxt.SetForegroundColour( wx.WHITE )
        '''
        self.chooseFile_btn = wx.Button( self, 
                                         100, 
                                         "Select File", 
                                         pos = (210, 0), 
                                         size = (100, 20) )
        self.chooseFile_btn.Bind(wx.EVT_LEFT_DOWN, self.onOpen)
        '''
        posY += 18
        self.dirCtrl = wx.GenericDirCtrl(self, 
                                         -1, 
                                         dir=CWD, 
                                         pos=(posX, posY), 
                                         size=(self.w_size[0]-20, 180))
        self.dirCtrl.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.onOpen)

        posY += self.dirCtrl.GetSize()[1] + 15
        self.sTxt_fn = wx.StaticText(self, id=-1, pos = (10, posY), label = 'FileName: ')
        self.sTxt_fr = wx.StaticText(self, id=-1, pos = (300, posY), label = 'Frame: ')
        self.sTxt_stat = wx.StaticText(self, id=-1, pos = (500, posY), label = '')
        self.sTxt_curr_dir = wx.StaticText(self, id=-1, pos = (-1, -1), label = '') # direction of the current frame
        self.sTxt_LED_data = wx.StaticText(self, id=-1, pos = (-1, -1), label = '')
        self.sTxt_fn.SetForegroundColour( wx.WHITE )
        self.sTxt_fr.SetForegroundColour( wx.WHITE )
        self.sTxt_stat.SetForegroundColour( wx.WHITE )
        self.sTxt_curr_dir.SetForegroundColour( wx.WHITE )
        self.sTxt_LED_data.SetForegroundColour( wx.WHITE )
        
        self.loaded_img = wx.StaticBitmap( self, -1, wx.NullBitmap, img_p_pos, (5,5) )

        _sTxt = wx.StaticText(self, id=-1, pos = (self.g_pos[0]-22, self.g_pos[1]), label = '360')
        _sTxt.SetFont(self.font_small)
        _sTxt.SetForegroundColour( wx.WHITE)
        _sTxt = wx.StaticText(self, id=-1, pos = (self.g_pos[0]-22, self.g_pos[1]+self.g_size[1]/4), label = '270')
        _sTxt.SetFont(self.font_small)
        _sTxt.SetForegroundColour( wx.WHITE)
        _sTxt = wx.StaticText(self, id=-1, pos = (self.g_pos[0]-22, self.g_pos[1]+self.g_size[1]/4*2), label = '180')
        _sTxt.SetFont(self.font_small)
        _sTxt.SetForegroundColour( wx.WHITE)
        _sTxt = wx.StaticText(self, id=-1, pos = (self.g_pos[0]-16, self.g_pos[1]+self.g_size[1]/4*3), label = '90')
        _sTxt.SetFont(self.font_small)
        _sTxt.SetForegroundColour( wx.WHITE)
        _sTxt = wx.StaticText(self, id=-1, pos = (self.g_pos[0]-10, self.g_pos[1]+self.g_size[1]), label = '0')
        _sTxt.SetFont(self.font_small)
        _sTxt.SetForegroundColour( wx.WHITE)

        ### graph buttons setup
        _graph_btn_names = ['minus', 'rotate180', 'applyHD']
        self.graph_btns = {}
        posX = self.w_size[0]-75
        for b_name in _graph_btn_names:
            self.graph_btns[b_name] = {}
            _fp = os.path.join('input', 'btn_%s.png'%b_name)
            self.graph_btns[b_name]["bmp"] = self.load_bmp( filePath=_fp, 
                                                            size=(20,20) ) # normal bmp
            _fp = os.path.join('input', 'btn_%s_mo.png'%b_name)
            self.graph_btns[b_name]["bmp_mo"] = self.load_bmp( filePath=_fp, 
                                                               size=(20,20) ) # bmp when mouse is over
            self.graph_btns[b_name]["sbm"] = wx.StaticBitmap(self, -1, 
                                                             self.graph_btns[b_name]["bmp"], 
                                                             pos=(posX, self.g_pos[1]+self.g_size[1]+2), 
                                                             size=(20,20), 
                                                             name=b_name)
            posX += 25
            self.graph_btns[b_name]["sbm"].Bind(wx.EVT_ENTER_WINDOW, self.onGraphBtnEnter)
            self.graph_btns[b_name]["sbm"].Bind(wx.EVT_LEAVE_WINDOW, self.onGraphBtnLeave)
            self.graph_btns[b_name]["sbm"].Bind(wx.EVT_LEFT_UP, self.onGraphBtnClick)

        self.graph_panel.Bind(wx.EVT_PAINT, self.onPaint)
        self.graph_panel.Bind(wx.EVT_LEFT_UP, self.onClickGraph)

    #------------------------------------------------

    def onPaint(self, event):
        '''
            draw graph panel
        '''
        if debug: print 'MarmosetRevision.onPaint'
        if hasattr(self, 'fi') == False: return
        
        ### init
        dc = wx.PaintDC(event.GetEventObject())
        dc.Clear()
        dc.SetPen(wx.Pen(wx.BLACK, 0, wx.TRANSPARENT))
        dc.SetBrush(wx.Brush(wx.Colour(250,250,250)))
        #dc.DrawRectangle(5,5,10,10)

        ### calculate the range of data to be displayed
        _middle = self.g_size[0]/2
        if self.fi - _middle/2 < 0:
            self.d_data_idx[0] = 0
            self.d_data_idx[1] = min( len(self.direction_data), self.g_size[0]/2 )
        else:
            self.d_data_idx[0] = self.fi - _middle/2
            self.d_data_idx[1] = min( len(self.direction_data), self.fi + _middle/2 )

        ### draw different background color for the last half
        ### (assuming the sound stimulus was played at the exactly half of the cropped trial video)
        if self.d_data_idx[1] >= len(self.direction_data)/2:
            dc.SetBrush(wx.Brush(wx.Colour(50,50,50)))
            _dist_from0 = max(0, 500 - self.d_data_idx[0]) * 2
            dc.DrawRectangle( _dist_from0, 0, self.g_size[0]-_dist_from0, self.g_size[1])

        ### draw reading guideline of angles
        dc.SetPen(wx.Pen(wx.Colour(150,50,50), 1))
        for i in xrange(1, 4):
            posY = self.g_size[1]/4 * i
            dc.DrawLine(0, posY, self.g_size[0], posY)
        dc.SetPen(wx.Pen(wx.WHITE, 1))

        ### draw selection area bgcolor
        if self.d_selection[0] != -1:
            dc.SetPen(wx.Pen((255,255,0,125), 1))
            idx0 = self.d_selection[0]
            if self.d_selection[1] == -1: idx1 = copy(self.fi)
            else: idx1 = self.d_selection[1]
            if idx1 < idx0:
                if idx1 < self.d_data_idx[1]:
                    posX0 = max(0, idx1 - self.d_data_idx[0])
                    posX1 = min(self.d_data_idx[1], idx0) - self.d_data_idx[0]
                else:
                    posX0 = None; posX1 = None
            else:
                if idx0 < self.d_data_idx[1]:
                    posX0 = max(0, idx0 - self.d_data_idx[0])
                    posX1 = min(self.d_data_idx[1], idx1) - self.d_data_idx[0]
                else:
                    posX0 = None; posX1 = None
            if posX0 != None and posX1 != None:
                posX0 *= 2; posX1 = (posX1+1)*2 # there's one pixel margin between lines
                for posX in xrange(posX0, posX1):
                    dc.DrawLine(posX, 0, posX, self.g_size[1])

        ### draw graph
        dc.SetPen(wx.Pen(wx.WHITE, 1))
        posX = 0
        self.sTxt_LED_data.SetLabel('')
        for i in xrange(self.d_data_idx[0], self.d_data_idx[1]):
            d = self.direction_data[i]["direction"]
            ### draw indicator line for the current frame
            if i == self.fi: 
                dc.SetPen(wx.Pen(wx.BLACK, 1))
                dc.DrawLine(posX, 0, posX, self.g_size[1])
                dc.SetPen(wx.Pen(wx.WHITE, 1))
                self.sTxt_curr_dir.SetLabel(str(d))
                self.sTxt_curr_dir.SetPosition( (self.g_pos[0]+posX, self.g_pos[1]+self.g_size[1]) )
            '''
            ### draw line and staticText for a LED signal
            if self.LED_data.has_key(i):
                dc.SetPen(wx.Pen(wx.RED, 1))
                dc.DrawLine(posX, 0, posX, self.g_size[1])
                dc.SetPen(wx.Pen(wx.WHITE, 1))
                self.sTxt_LED_data.SetLabel(self.LED_data[i])
                self.sTxt_LED_data.SetPosition( (self.g_pos[0]+posX, self.g_pos[1]) )
            '''
            ### draw data line
            if d == -1:
                dc.SetPen(wx.Pen((200,200,200), 1))
                rat = self.direction_data[i]["h_direction"] / 360.0
            else:
                rat = d/360.0
            posY = self.g_size[1] - self.g_size[1]*rat
            dc.DrawLine(posX, posY, posX, self.g_size[1])

            ### draw smooth line
            posY = self.g_size[1] - (self.g_size[1] * (self.direction_data[i]["s_direction"] / 360.0))
            dc.SetBrush(wx.Brush(wx.Colour(50,50,255)))
            dc.SetPen(wx.Pen(wx.BLACK, 0, wx.TRANSPARENT))
            dc.DrawCircle(posX, posY, 1)
            dc.SetPen(wx.Pen(wx.WHITE, 1))

            posX += 2 # 1 pixel is margin between two data lines
        event.Skip()

    #------------------------------------------------

    def onSave(self, flag=None):
        ''' Save the direction data
        If flag is 'init_save', don't show saving complete message.
        '''
        if debug: print "MarmosetRevision.onSave"
            
        fi = 0
        f = open(self.new_CSV_fp, 'w')
        f.write('Frame-index, Direction\n')
        for di in self.direction_data.iterkeys():
            d = self.direction_data[di]["direction"]
            f.write('%i, %i\n'%(fi, d))
            fi += 1
        f.close()
        if flag != 'init_save':
            app.frame.show_msg('CSV file is saved.')

    #------------------------------------------------

    def onSaveGraph(self):
        w = len(self.direction_data) * 3
        h = 360
        bmp = wx.EmptyBitmap(w, h, depth = -1)
        memDC = wx.MemoryDC()  #Create a memory DC that will be used to copy the screen
        memDC.SelectObject(bmp) # Associate the bitmap to the memoryDC
        memDC.SetPen(wx.Pen(wx.WHITE, 1))
        memDC.SetBrush(wx.Brush(wx.Colour(0,0,0)))
        memDC.DrawRectangle(0,0,w,h)
        memDC.DrawLine(0, 90, w, 90)
        memDC.DrawLine(0, 180, w, 180)
        memDC.DrawLine(0, 270, w, 270)
        posX = 0
        for di in self.direction_data.iterkeys():
            d = self.direction_data[di]["direction"]
            posY = 360 - d
            memDC.DrawLine(posX, posY, posX, 360)
            posX += 3
        # Select the Bitmap out of the memory DC by selecting a new uninitialized Bitmap
        memDC.SelectObject(wx.NullBitmap)
        img = bmp.ConvertToImage()
        fp = self.new_CSV_fp.replace('.csv', '.png')
        img.SaveFile(fp, wx.BITMAP_TYPE_PNG)
        app.frame.show_msg('PNG file is saved.')

    #------------------------------------------------

    def onGraphBtnEnter(self, event):
        '''
            change the bitmap of the button so that 
            it looks different when the cursor is over it.
        '''
        if debug: print 'MarmosetRevision.onGraphBtnEnter'
        obj_name = event.GetEventObject().GetName()
        self.graph_btns[obj_name]["sbm"].SetBitmap(self.graph_btns[obj_name]["bmp_mo"])

    #------------------------------------------------

    def onGraphBtnLeave(self, event):
        '''
            change back to the original bitmap
        '''
        if debug: print 'MarmosetRevision.onGraphBtnLeave'
        obj_name = event.GetEventObject().GetName()
        self.graph_btns[obj_name]["sbm"].SetBitmap(self.graph_btns[obj_name]["bmp"])

    #------------------------------------------------

    def onGraphBtnClick(self, event):
        '''There are some buttons right below the data graph
        to adjust the data. These buttons can be clicked with 
        mouse left button, or some of them can be operated with 
        keyboard input.
        '''
        if type(event) == str: obj_name = event
        else: obj_name = event.GetEventObject().GetName()

        if self.d_selection[0] != -1: # selection started
            if self.d_selection[1] == -1: # selection not finished
                self.onToggleSelection() # finish selection with the current frame index
            if self.d_selection[1] < self.d_selection[0]:
                idx0 = self.d_selection[1]
                idx1 = self.d_selection[0]
            else:
                idx0 = self.d_selection[0]
                idx1 = self.d_selection[1]
            self.d_selection = [-1, -1]
        else:
            idx0 = copy(self.fi)
            idx1 = idx0 + 1

        if obj_name == 'minus':
            for di in xrange(idx0, idx1):
                self.direction_data[di]["direction"] = -1
            app.frame.show_msg_in_statbar('Selected data are set to -1.')
            self.calc_hd() # calculate the hypothetical data again
        elif obj_name == 'rotate180':
            for di in xrange(idx0, idx1):
                if self.direction_data[di]["direction"] != -1:
                    self.direction_data[di]["direction"] = (self.direction_data[di]["direction"]+180) % 360
            app.frame.show_msg_in_statbar('Selected data are rotated by 180 degrees.')
            self.calc_hd() # calculate the hypothetical data again
        elif obj_name == 'applyHD': # apply Hypothetical data as real data
            for di in xrange(self.frame_cnt):
                if self.direction_data[di]["direction"] == -1:
                    self.direction_data[di]["direction"] = self.direction_data[di]["h_direction"]
        self.process_changed_fi()


    #------------------------------------------------

    def process_changed_fi(self):
    # process after the current frame-index (self.fi) is changed
        self.sTxt_fr.SetLabel('Frame: %i/%i'%(self.fi, self.frame_cnt-1))
        if self.dir_path == None:
            self.graph_panel.Refresh()
            return
        _fp = os.path.join(self.dir_path, 'f%.6i.jpg'%(self.fi+1))
        bmp = self.load_bmp(_fp, self.img_p_sz)
        memDC = wx.MemoryDC() 
        memDC.SelectObject(bmp)
        pt1 = ( int(self.direction_data[self.fi]["direction_line_start"][0]*self.img_ratio[0]), 
                int(self.direction_data[self.fi]["direction_line_start"][1]*self.img_ratio[1]) )
        pt2 = ( int(self.direction_data[self.fi]["direction_line_end"][0]*self.img_ratio[0]), 
                int(self.direction_data[self.fi]["direction_line_end"][1]*self.img_ratio[1]) )
        memDC.SetPen(wx.Pen(wx.Colour(255,255,0), 1))
        memDC.DrawLine(pt1[0], pt1[1], pt2[0], pt2[1])
        memDC.SetPen(wx.Pen(wx.BLACK, 0, wx.TRANSPARENT))
        memDC.SetBrush(wx.Brush(wx.Colour(255,0,0)))
        memDC.DrawCircle(pt1[0], pt1[1], 3)
        memDC.SelectObject(wx.NullBitmap)
        self.loaded_img.SetBitmap(bmp)
        self.graph_panel.Refresh()

    #------------------------------------------------

    def onLeft(self):
        if debug: print 'MarmosetRevision.onLeft'
        if self.new_CSV_fp == None: return
        self.fi = max(0, self.fi-1)
        self.process_changed_fi()

    #------------------------------------------------

    def onLeftJump(self):
        '''
            jump backward equivalent to one second
        '''
        if debug: print 'MarmosetRevision.onLeftJump'
        if self.new_CSV_fp == None: return
        self.fi = max(0, self.fi-50)
        self.process_changed_fi()

    #------------------------------------------------

    def onRight(self, event):
        '''
            right arrow key is pressed. go forward
        '''
        if debug: print 'MarmosetRevision.onRight'
        if self.new_CSV_fp == None: return
        self.fi = min( self.fi+1, len(self.direction_data)-1 )
        if self.fi >= len(self.direction_data)-1: # reached the end
            self.flag_run = False
            if self.timer1 != None: self.stop_timer()
        self.process_changed_fi()

    #------------------------------------------------
    
    def onRightJump(self):
        '''
            jump forward equivalent to one second
        '''
        if debug: print 'MarmosetRevision.onRightJump'
        if self.new_CSV_fp == None: return
        self.fi = min( self.fi+50, len(self.direction_data)-1 ) # jump 50 frames
        if self.fi == len(self.direction_data)-1 and self.timer1 != None: self.stop_timer()
        self.process_changed_fi()

    #------------------------------------------------

    def onClickGraph(self, event):
        '''
            Click happened inside of the graph
            Jump to where the click event happened
        '''
        if len(self.direction_data) == 0: return
        posX = event.GetPosition()[0]
        self.fi = self.d_data_idx[0] + posX/2
        self.process_changed_fi()

    #------------------------------------------------

    def onSpace(self):
        '''
            space bar is pressed. 
            this will toggle (keep running image processing) / (stop processing)
        '''
        if debug: print 'MarmosetRevision.onSpace'

        if self.new_CSV_fp == None: return
        self.flag_run = not self.flag_run
        if self.flag_run == True:
            self.timer1 = wx.Timer(self)
            self.Bind(wx.EVT_TIMER, self.onRight, self.timer1)
            self.timer1.Start(10) # about 100 fps
        else:
            if self.timer1 != None: self.stop_timer()

    #------------------------------------------------

    def stop_timer(self):
        '''
            Stop the timer of moving forward (by pressing Spacebar)
        '''
        if debug: print 'MarmosetRevision.stop_timer'
        self.timer1.Stop()
        self.timer1 = None

    #------------------------------------------------

    def onToggleSelection(self):
        '''
            toggle selection of the data on the graph
        '''
        if debug: print 'MarmosetRevision.onToggleSelection'
        if len(self.direction_data) == 0: return
        if self.d_selection == [-1, -1]:
            self.d_selection[0] = self.fi
        elif self.d_selection[0] != -1 and self.d_selection[1] == -1:
            if self.d_selection[0] <= self.fi:
                self.d_selection[1] = self.fi + 1
            else:
                self.d_selection[1] = copy(self.fi)
                self.d_selection[0] += 1
        elif self.d_selection[0] != -1 and self.d_selection[1] != -1:
            self.d_selection[0] = self.fi
            self.d_selection[1] = -1

    #------------------------------------------------

    def load_bmp(self, filePath, size=(-1,-1)):
        '''
            load an image specified with parameters
        '''
        if debug: print 'MarmosetRevision.load_bmp'
        tmp_null_log = wx.LogNull() # this is for not seeing the tif Library warning
        img = wx.Image(filePath, wx.BITMAP_TYPE_ANY)
        if size != (-1, -1): img = img.Rescale( size[0], size[1] )
        del tmp_null_log # delete the null-log to restore the logging
        bmp = img.ConvertToBitmap()
        return bmp

    #------------------------------------------------

    def onOpen(self, event):
        '''
            choosing a CSV file to revise
        '''
        if debug: print 'MarmosetRevision.onOpen'

        '''
        dlg = wx.FileDialog(self, "Choose a CSV file for revision.", CWD, "", "*.csv", wx.OPEN)
        dlgResult = dlg.ShowModal()
        if dlgResult == wx.ID_CANCEL: return
        CSV_file_name = dlg.GetFilename()
        d_path = dlg.GetDirectory()
        orig_CSV_fp = os.path.join( d_path, CSV_file_name )
        '''
        orig_fp =  self.dirCtrl.GetFilePath()
        if orig_fp[-4:].lower() != '.csv':
            self.main_frame.show_msg_in_statbar('Only CSV file can be opened.')
            return
        CSV_file_name = os.path.split(orig_fp)[1]
        d_path = os.path.split(orig_fp)[0]
        self.dir_path = os.path.join(d_path, CSV_file_name.replace(".csv", "")) # directory with jpg images for the csv file

        if os.path.isdir( self.dir_path ) == False: self.dir_path = None
        if self.dir_path == None:
            self.frame_cnt = self.default_frame_cnt
        else:
            self.frame_cnt = len(glob( os.path.join(self.dir_path, "*.jpg") ))
            
        if output_dir == d_path: # opening the revision program's output file
            self.new_CSV_fp = orig_fp
        else: # opening the video analysis program's output file
            _fn_str = CSV_file_name.split('_')
            _new_CSV_fn = '%s_%s_%s_%s_%s'%(_fn_str[0], 
                                            orig_fp.split('/')[-3].split('_')[-1], 
                                            _fn_str[1], 
                                            _fn_str[3], 
                                            _fn_str[4])
            self.new_CSV_fp = os.path.join( output_dir, _new_CSV_fn )
            #copyfile( orig_fp, self.new_CSV_fp ) # copy the data file as it's opened
        f = open(orig_fp, 'r') # output CSV file
        _csv = f.readlines()
        f.close()
        ### data init
        self.direction_data = {}
        self.LED_data = {}
        ### init direction data
        for ddi in xrange(self.frame_cnt):
            self.direction_data[ddi] = dict(ear_rect = [-1,-1,-1,-1], 
                                            direction = -1, 
                                            h_direction = -1, # hypothetical direction
                                            s_direction = -1, # smoothed data (Simple Moving Average)
                                            direction_line_start = [-1, -1],
                                            direction_line_end = [-1, -1])
        ### store all the data and put missing data for each frame
        ### ------------------------------------------------------
        for line in _csv:
            if line.startswith('Frame-'): continue
            elif line.startswith('# IR-LED-signal'):
                tmp = line.split(',')
                _sig = tmp[0].split('signal')[1].strip()
                _sig = _sig.strip('[]').split('/')
                signal = '%s%s/%s%s'%(_sig[0], _sig[1], _sig[2], _sig[3])
                frame_idx = int( tmp[1].split('index')[1].strip() )
                self.LED_data[frame_idx] = signal
            else:
                items = [ item.strip() for item in line.split(',') ]
                if len(items) <= 1: continue
                _fi = int(items[0])
                if output_dir == d_path: # opening the revision program's output file
                    self.direction_data[_fi]["direction"] = int(items[1])
                else: # opening the video analysis program's output file
                    self.direction_data[_fi]["ear_rect"] = [ int(x) for x in items[1].split('/') ]
                    self.direction_data[_fi]["direction"] = int(items[2])
                    self.direction_data[_fi]["h_direction"] = -1 # hypothetical direction
                    self.direction_data[_fi]["direction_line_start"] = [ int(x) for x in items[3].split('/') ]
                    self.direction_data[_fi]["direction_line_end"] = [ int(x) for x in items[4].split('/') ]
        self.calc_hd() # calculate the hypothetical direction of missing data (-1)
        ### ------------------------------------------------------
        '''
        ### init save DISABLED
        if output_dir != d_path: # opening the video analysis program's output file
            self.onSave(flag='init_save')
        '''
        self.sTxt_fn.SetLabel('FileName: %s'%(CSV_file_name))
        self.fi = 0 # frame index
        self.init_video()
        #dlg.Destroy()

    #------------------------------------------------

    def calc_hd(self):
    # calculate the hypothetical data of missing data (-1) with previous and next recorded data
        ddi = 0
        while ddi < self.frame_cnt:
            if self.direction_data[ddi]["direction"] == -1:
                pddi = ddi - 1 # prev index
                pd = -1 # previously recorded direction
                if pddi >= 0 and self.direction_data[pddi]["direction"] != -1:
                    pd = self.direction_data[pddi]["direction"]
                nddi = ddi + 1 # next index
                nd = -1 # next recorded direction
                while nd == -1 and nddi < self.frame_cnt:
                    if self.direction_data[nddi]["direction"] != -1:
                        nd = self.direction_data[nddi]["direction"]
                    nddi += 1
                if pd == -1 and nd != -1: # there's no previous data, but there's next data
                    while ddi < nddi:
                        ### fill the hypothetical direction with the next recorded data
                        self.direction_data[ddi]["h_direction"] = nd
                        ddi += 1
                elif pd != -1 and nd == -1: # there's no next data, but there's previous data
                    while ddi < nddi:
                        ### fill the hypothetical direction with the previous recorded data
                        self.direction_data[ddi]["h_direction"] = pd
                        ddi += 1
                elif pd != -1 and nd != -1: # there are both previous and next data
                    ### fill the hypothetical direction as it smoothly bridging the prev. and next data
                    f_diff = nddi - pddi # frame difference
                    d_diff = nd - pd # data difference
                    if abs(d_diff) > 180:
                        min_d_diff = min(abs(0-pd), (360-pd)) + min(abs(0-nd), (360-nd))
                        if d_diff > 0:
                            d_inc = float(min_d_diff) / f_diff * -1 # data increment per frame
                        else:
                            d_inc = float(min_d_diff) / f_diff # data increment per frame
                    else:
                        d_inc = float(d_diff) / f_diff # data increment per frame
                    while ddi < nddi:
                        _hd = pd + int( (ddi - pddi) * d_inc )
                        if _hd < 0 or _hd > 360: 
                            _hd = (360 + _hd) % 360
                        self.direction_data[ddi]["h_direction"] = _hd
                        ddi += 1
                ddi -= 1
            ddi += 1


        ### smoothing data (with modified Simple Moving Average)
        '''
        * Average was calculated with (previous n data + current data + next n data).
        * n was 10, thus, 21 data points (if applicable) were used for one average value.
        * In cases of abruptly big head direction changes, (mostly for 0 > 359 or 359 > 0)
          some data were excluded depending on the relative position of the big change to the current working data.
        '''
        for ddi in xrange(self.frame_cnt):
            _tmp = [] # data around the current data point(ddi)
            for i in xrange(ddi-10, ddi+11): 
            # iterate through plus/minus 10 data points around the current data point, 
            # therefore 21 data points will be collected
                if 0 <= i < self.frame_cnt:
                # if it's available, collecte either actual direction or h_direction
                    if self.direction_data[i]["direction"] != -1:
                        _tmp.append(self.direction_data[i]["direction"])
                    else:
                        _tmp.append(self.direction_data[i]["h_direction"])
                else:
                    _tmp.append(None)

            ### this part is for some abrupt big head direction change. (mostly 0 > 359 or 359 > 0)
            for i in xrange(len(_tmp)):
                if _tmp[i-1] == None or _tmp[i] == None: continue
                if i > 0 and abs(_tmp[i-1] - _tmp[i]) > 180:
                # the change from the previous frame to the current frame was abruptly big
                    if i < ceil(len(_tmp)/2.0): # if this happened before the current data point(ddi)
                        for _i in xrange(i): _tmp[_i] = None # erase data before this big change
                    else: # if this happened after the current data point(ddi)
                        for _i in xrange(i, len(_tmp)): _tmp[_i] = None # erase data after this big change
            while None in _tmp: _tmp.remove(None)

            self.direction_data[ddi]["s_direction"] = int(sum(_tmp) / len(_tmp)) # store the valid average value

    #------------------------------------------------
        
    def init_video(self):
        if debug: print 'MarmosetRevision.init_video'
        if self.dir_path == None:
            self.loaded_img.SetBitmap(wx.NullBitmap)
            self.process_changed_fi()
        else:
            _fp = os.path.join( self.dir_path, "f%.6i.jpg"%(self.fi+1) )
            bmp = self.load_bmp(_fp)
            orig_size = bmp.GetSize()
            self.img_ratio = ( self.img_p_sz[0]/float(orig_size[0]), 
                               self.img_p_sz[1]/float(orig_size[1]) )
            self.process_changed_fi()

# ======================================================

class MR_App(wx.App):
    def OnInit(self):
        self.frame = MRA_Main_Frame()
        self.frame.Show()
        self.SetTopWindow(self.frame)
        return True
        
#====================================================

class PopupDialog(wx.Dialog):
    def __init__(self, parent = None, id = -1, title = "MR_Dialog", inString = "", size = (200, 150)):
        if debug: print 'PopupDialog.__init__'

        wx.Dialog.__init__(self, parent, id, title)
        self.SetSize(size)
        self.Center()
        txt = wx.StaticText(self, -1, label = inString, pos = (20, 20))
        txt.SetSize(size)
        txt.SetFont(wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False))
        txt.Wrap(size[0]-25)
        okButton = wx.Button(self, wx.ID_OK, "OK")
        b_size = okButton.GetSize()
        okButton.Position = (size[0] - b_size[0] - 20, size[1] - b_size[1] - 40)
        okButton.SetDefault()

#====================================================


# define the current working directory depending on
# whether it's an app or not.
CWD = os.getcwd()
parent_dir = os.path.split(CWD)[0]
info_plist_path = os.path.join(parent_dir, 'Info.plist')
if os.path.isfile(info_plist_path):
    plist_data = plistlib.readPlist(info_plist_path)
    if plist_data["CFBundleDisplayName"] == 'm_revision':
        for i in xrange(3): CWD = os.path.split(CWD)[0]    

debug = False
output_dir = os.path.join(CWD, "output")
if not os.path.isdir(output_dir): os.mkdir(output_dir) # if output folder doesn't exist, make one

if __name__ == "__main__":
    if len(argv) > 1:
        if argv[1] == '-w': GNU_notice(1)
        elif argv[1] == '-c': GNU_notice(2)
    else:
        GNU_notice(0)
        app = MR_App(redirect = False)
        app.MainLoop()
