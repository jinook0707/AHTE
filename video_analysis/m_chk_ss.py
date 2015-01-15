'''
This is for calculating the exact time of session start via checking 
LED color. (head turning experiment of common marmoset monkeys)

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
from math import degrees, radians, hypot, acos, sin, cos, atan2, pi
from random import uniform
from datetime import datetime
from time import time
from shutil import rmtree
from sys import platform, argv

import wx
import cv2
import cv2.cv as cv
import numpy as np

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

#====================================================

class MChkSessionStart(wx.Frame):

    def __init__(self):
        if debug: print 'MChkSessionStart.__init__'

        w_size = (1280, 770)
        self.w_size = w_size

        wx.Frame.__init__(self, None, -1, "M_CHK_SS", pos = (0,20), size = (w_size[0],w_size[1]), style=wx.DEFAULT_FRAME_STYLE^(wx.RESIZE_BORDER|wx.MAXIMIZE_BOX))
        #self.Center()
        self.posX = self.GetPosition()[0]
        self.posY = self.GetPosition()[1]

        self.panel = wx.Panel(self, pos = (0,0), size = (w_size[0],w_size[1]))

        self.HSV_min_wht = (0, 0, 200)
        self.HSV_max_wht = (179, 50, 255)

        self.font = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, 0.5, 0.5, 0, 1, 8)
        self.video = None
        self.video_file_name = None
        self.selected_LED_key = -1 # key of LED rectangle where the mouse was pressed down
        self.flag_run = False

        self.fps = 0
        self.last_fps_chk_time = -1

        posX = 5; posY = 10
        btn_choose_file = wx.Button( self.panel, 
                                     -1, 
                                     "Choose video file", 
                                     pos = (posX, posY-5), 
                                     size = (150, 20) )
        btn_choose_file.Bind(wx.EVT_LEFT_DOWN, self.onOpenFile)
        posX += btn_choose_file.GetSize()[0] + 20
        btn_base_cm = wx.Button( self.panel, 
                                 -1, 
                                 "Base CM of LEDs", 
                                 pos = (posX, posY-5), 
                                 size = (150, 20) )
        btn_base_cm.Bind(wx.EVT_LEFT_DOWN, self.onStoreLEDBaseCM)
        posX += btn_base_cm.GetSize()[0] + 20
        self.sTxt_fn = wx.StaticText(self.panel, id=-1, pos = (posX, posY), label = 'Name: ')
        posX = w_size[0] - 200
        sTxt_fr = wx.StaticText(self.panel, id=-1, pos = (posX, posY), label = 'Frame: ')
        posX += sTxt_fr.GetSize()[0] + 10
        self.sTxt_frames = wx.StaticText(self.panel, id=-1, pos = (posX, posY), label = '-1 / -1')

        posX = 0
        posY += 25
        self.loaded_img_pos = (posX, posY)
        self.loaded_img = wx.StaticBitmap( self.panel, -1, wx.NullBitmap, self.loaded_img_pos, (5,5) )
        self.loaded_img.Bind(wx.EVT_MOUSEWHEEL, self.onMouseWheel)
        self.loaded_img.Bind(wx.EVT_LEFT_DOWN, self.onMouseDown)
        self.loaded_img.Bind(wx.EVT_MOTION, self.onMouseMove)
        self.loaded_img.Bind(wx.EVT_LEFT_UP, self.onMouseUp)

        ### Connecting key-inputs with some functions
        exit_BtnID = wx.NewId()
        space_BtnID = wx.NewId()
        right_BtnID = wx.NewId()
        self.Bind(wx.EVT_MENU, self.onExit, id = exit_BtnID)
        self.Bind(wx.EVT_MENU, self.onSpace, id = space_BtnID)
        self.Bind(wx.EVT_MENU, self.onRight, id = right_BtnID)
        accel_tbl = wx.AcceleratorTable([ (wx.ACCEL_CMD,  ord('Q'), exit_BtnID), 
                                          (wx.ACCEL_NORMAL, wx.WXK_RIGHT, right_BtnID), 
                                          (wx.ACCEL_NORMAL,  wx.WXK_SPACE, space_BtnID) ])
        self.SetAcceleratorTable(accel_tbl)
        
        statbar = wx.StatusBar(self, -1)
        self.SetStatusBar(statbar)

    #------------------------------------------------

    def show_msg_in_statbar(self, msg, timeout=5000):
        if debug: print 'MChkSessionStart.show_msg_in_statbar'
        self.SetStatusText(msg)
        if timeout != -1:
            wx.FutureCall(timeout, self.SetStatusText, "") # delete it after a while

    #------------------------------------------------

    def onRight(self, event):
        if debug: print 'MChkSessionStart.onRight'
        if self.flag_run == True: return
        self.proc_img()

    #------------------------------------------------

    def onSpace(self, event):
    # space bar is pressed. 
    # this will toggle (keep running image processing) / (stop processing)
        if debug: print 'MChkSessionStart.onSpace'

        if self.video == None: return
        for key in self.LED_base_cm.iterkeys():
            if self.LED_base_cm[key] == -1:
                self.show_msg('[Base CM of LEDs] have to be set first.')
                return
        self.flag_run = not self.flag_run
        self.proc_img()

    #------------------------------------------------
    
    def cvImg_to_wxBMP(self, cvImg):
        if debug: print 'MChkSessionStart.cvImg_to_wxBMP'

        cv.CvtColor(cvImg, cvImg, cv.CV_BGR2RGB)
        img = wx.EmptyImage(cvImg.width, cvImg.height)
        img.SetData(cvImg.tostring())
        bmp = img.ConvertToBitmap()
        return bmp
        '''
        wxBMP = wx.StaticBitmap( self.panel, 
                                 -1, 
                                 bmp, 
                                 self.loaded_img_pos, 
                                 (img.GetWidth(), img.GetHeight()) )
        return wxBMP
        '''

    #------------------------------------------------

    def load_jpg_file(self, filepath, flag='wx'):
        if debug: print 'MChkSessionStart.load_jpg_file'

        ret_img = None
        if os.path.isfile(filepath): # if the file exist
            if flag == 'wx':
                img = wx.Image(filepath, wx.BITMAP_TYPE_ANY)
                ret_img = img.ConvertToBitmap()
                ret_img = wx.StaticBitmap(self.panel, -1, bmp, self.loaded_img_pos)
            elif flag == 'cv':
                ret_img = cv.LoadImage(filepath)
        return ret_img

    #------------------------------------------------

    def onMouseDown(self, event):
        if debug: print 'MChkSessionStart.onMouseDown'
        self.loaded_img.SetFocus()
        mp = event.GetPosition()
        for key in self.LED_rects.iterkeys(): # for each LED rects
            _x = self.LED_rects[key][0]; _y = self.LED_rects[key][1]
            _sz = self.LED_rects[key][2]
            if _x-_sz < mp[0] < _x+_sz and _y-_sz < mp[1] < _y+_sz:
            # if the event happened while the pointer is in a LED rect
                self.selected_LED_key = key

    #------------------------------------------------

    def onMouseMove(self, event):
        if debug: print 'MChkSessionStart.onMouseMove'
        mp = event.GetPosition()
        if self.selected_LED_key != -1:
            self.LED_rects[self.selected_LED_key][0] = mp[0] - self.LED_rects[self.selected_LED_key][2]/2
            self.LED_rects[self.selected_LED_key][1] = mp[1] - self.LED_rects[self.selected_LED_key][3]/2
            if self.flag_run == False: self.proc_img(self.orig_img) # reload the current frame

    #------------------------------------------------

    def onMouseUp(self, event):
        if debug: print 'MChkSessionStart.onMouseUp'
        self.selected_LED_key = -1

    #------------------------------------------------

    def onMouseWheel(self, event):
        if debug: print 'MChkSessionStart.onMouseWheel'
        mp = event.GetPosition() # mouse position at the wheel event
        for i in xrange(len(self.LED_rects)): # for each LED rects
            _x = self.LED_rects[i][0]; _y = self.LED_rects[i][1]
            _sz = self.LED_rects[i][2]
            if _x-_sz < mp[0] < _x+_sz and _y-_sz < mp[1] < _y+_sz:
            # if the event happened while the pointer is in a rect
                ### increase or decrease the rect size
                if event.GetWheelRotation() < 0: self.LED_rects[i][2] = max(10, self.LED_rects[i][2] - 1) # minimum 10
                else: self.LED_rects[i][2] = min(50, self.LED_rects[i][2] + 1) # maximum 50
                if self.flag_run == False: self.proc_img(self.orig_img) # reload the current frame

    #------------------------------------------------

    def onOpenFile(self, event):
    # choosing a file to be analyzed
        if debug: print 'MChkSessionStart.onOpen'

        dlg = wx.FileDialog(self, "Choose a MP4 file for extraction.", CWD, "", "*.MP4", wx.OPEN)
        dlgResult = dlg.ShowModal()
        if dlgResult == wx.ID_OK:
            self.video_file_name = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            self.init_video_analyzing()
        dlg.Destroy()

    #------------------------------------------------
        
    def init_video_analyzing(self):
        if debug: print 'MChkSessionStart.init_video_analyzing'

        if self.video_file_name == None: return
        file_path = os.path.join(self.dirname, self.video_file_name)
        self.video = cv2.VideoCapture(file_path)
        self.frame_cnt = self.video.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT)

        frame = self.video.read()[1]
        self.frame_size = (frame.shape[1], frame.shape[0])
        self.fi = 0
        self.sTxt_frames.SetLabel('0/%i'%self.frame_cnt)
        self.sTxt_fn.SetLabel( 'Name: %s'%(self.video_file_name) )
        ### init LED rect data
        _mx = self.w_size[0]/2; _my = self.w_size[1]/2
        self.LED_rects = dict( UL = [_mx-150, _my-100, 15, 15],
                               UR = [_mx+150, _my-100, 15, 15],
                               LL = [_mx-150, _my-50, 15, 15],
                               LR = [_mx+150, _my-50, 15, 15] ) # [x, y, w, h]
        self.LED_base_cm = dict (UL = -1, UR = -1, LL = -1, LR = -1) # base central moment

        ### init openCV related variables
        self.curr_frame = cv.CreateImage(self.frame_size, 8, 3)
        self.orig_img = cv.CreateImage(self.frame_size, 8, 3)
        self.HSV_img = cv.CreateImage(self.frame_size, 8, 3)
        self.tmp_col_img = cv.CreateImage(self.frame_size, 8, 3)
        self.init_grey_img = cv.CreateImage(self.frame_size, cv.IPL_DEPTH_8U, 1)
        self.grey_img = cv.CreateImage(self.frame_size, cv.IPL_DEPTH_8U, 1)
        self.grey_avg = cv.CreateImage(self.frame_size, cv.IPL_DEPTH_32F, 1)
        self.tmp_grey_img = cv.CreateImage(self.frame_size, cv.IPL_DEPTH_8U, 1)
        self.diff_grey_img = cv.CreateImage(self.frame_size, cv.IPL_DEPTH_8U, 1)
        self.grey_avg = cv.CreateImage(self.frame_size, cv.IPL_DEPTH_32F, 1)
        self.storage = cv.CreateMemStorage(0)
        self.mask_img = cv.CreateImage(self.frame_size, 8, 1)
        self.first_run = True
        self.flag_run = False

        self.proc_img(cv.fromarray(frame)) # display the 1st frame

    #------------------------------------------------

    def onStoreLEDBaseCM(self, event):
    # check each LED's base central moments
        for key in self.LED_rects.iterkeys():
            self.find_color((self.LED_rects[key][0],self.LED_rects[key][1],self.LED_rects[key][2],self.LED_rects[key][3]), 
                            self.orig_img, 
                            self.HSV_min_wht, 
                            self.HSV_max_wht, 
                            (0,0,0))
            img_mat = cv.GetMat(self.tmp_grey_img)
            moments = cv.Moments(img_mat)
            cm = cv.GetCentralMoment(moments, 0, 0)
            self.LED_base_cm[key] = cm
        self.show_msg('Central moment of each LED is stored.')

    #------------------------------------------------

    def chk_LED(self):
    # check LED whether white light is on or not
        LED_on = False
        for key in self.LED_rects.iterkeys():
            self.find_color((self.LED_rects[key][0],self.LED_rects[key][1],self.LED_rects[key][2],self.LED_rects[key][3]), 
                            self.orig_img, 
                            self.HSV_min_wht,  
                            self.HSV_max_wht, 
                            (0,0,0))
            img_mat = cv.GetMat(self.tmp_grey_img)
            moments = cv.Moments(img_mat)
            cm = cv.GetCentralMoment(moments, 0, 0)
            if self.LED_base_cm[key] != -1 and cm > self.LED_base_cm[key] + 300:
                LED_on = True
                print key, self.LED_rects[key], self.LED_base_cm[key], cm
        return LED_on
    
    #------------------------------------------------

    def proc_img(self, frame = None):
        if debug: print 'MChkSessionStart.proc_img'
        if self.video == None: return

        if frame == None:
            self.orig_img = cv.fromarray(self.video.read()[1])
            self.fi += 1
            self.sTxt_frames.SetLabel('%i/%i'%(self.fi, self.frame_cnt))
        else:
            self.orig_img = frame
        cv.Copy(self.orig_img, self.curr_frame)
        LED_on = self.chk_LED()
        if LED_on == True:
            cv.Circle(self.curr_frame, (self.w_size[0]/2,self.w_size[1]/2), 50, (0,0,200), -1)
            _etime = float(self.fi+1) / 100
            _msg = 'The movie recording started %.3f seconds before the experiment software started.\n'%(_etime)
            _msg += '(Assumption: FPS of movie recording was 100)'
            self.show_msg(_msg)
            self.flag_run = False

        for key in self.LED_rects.iterkeys():
            _r = self.LED_rects[key]
            cv.Rectangle(self.curr_frame, (_r[0], _r[1]), (_r[0]+_r[2], _r[1]+_r[3]), (0,0,255), 1)

        self.loaded_img.SetBitmap( self.cvImg_to_wxBMP(self.curr_frame) )

        if self.flag_run == True:
            wx.FutureCall(1, self.proc_img)

        if self.last_fps_chk_time == -1: self.last_fps_chk_time = time()
        if time()-self.last_fps_chk_time >= 1:
            print "FPS: %i"%self.fps
            self.fps = 0
            self.last_fps_chk_time = time()
        else:
            self.fps += 1

    #------------------------------------------------

    def find_color(self, rect, inImage, HSV_min, HSV_max, bgcolor=(255,255,255)):
    # Find a color(range: 'HSV_min' ~ 'HSV_max') in an area('rect:[x,y,w,h]') of an image('inImage')
    # 'bgcolor' is a background color of the masked image
    # Result will be stored in self.tmp_grey_img
        if debug: print 'MChkSessionStart.find_color'

        cv.Zero(self.mask_img)
        cv.Zero(self.tmp_grey_img)
        cv.Set(self.tmp_col_img, bgcolor)
        cv.Rectangle(self.mask_img, (rect[0], rect[1]), (rect[0]+rect[2], rect[1]+rect[3]), 255, cv.CV_FILLED)
        cv.Copy(inImage, self.tmp_col_img, self.mask_img)
        cv.CvtColor(self.tmp_col_img, self.HSV_img, cv.CV_BGR2HSV)
        cv.InRangeS(self.HSV_img, HSV_min, HSV_max, self.tmp_grey_img)     

    #------------------------------------------------

    def get_points(self, inImage, threshold=15):
    # get the binary image after edge-detection and returns the some useful points of its contours
    # 'threshold' : threshold for a contour fragment
        if debug: print 'MChkSessionStart.get_points'

        contour = cv.FindContours(inImage, self.storage, cv.CV_RETR_CCOMP, cv.CV_CHAIN_APPROX_SIMPLE)
        pt1_list = []
        pt2_list = []
        min_pt1 = []
        max_pt2 = []
        center_pt_list = []
        while contour:
            contour_list = list(contour)
            contour = contour.h_next()
            bound_rect = cv.BoundingRect(contour_list)
            pt1 = (bound_rect[0], bound_rect[1])
            pt2 = (bound_rect[0] + bound_rect[2], bound_rect[1] + bound_rect[3])

            if bound_rect[2] + bound_rect[3] > threshold:
                pt1_list.append(pt1)
                pt2_list.append(pt2)
                center_pt_list.append((bound_rect[0]+bound_rect[2]/2, bound_rect[1]+bound_rect[3]/2))
                if len(min_pt1) == 0:
                    min_pt1 = list(pt1)
                    max_pt2 = list(pt2)
                else:
                    if min_pt1[0] > pt1[0]: min_pt1[0] = int(pt1[0])
                    if min_pt1[1] > pt1[1]: min_pt1[1] = int(pt1[1])
                    if max_pt2[0] < pt2[0]: max_pt2[0] = int(pt2[0])
                    if max_pt2[1] < pt2[1]: max_pt2[1] = int(pt2[1])
        return pt1_list, pt2_list, tuple(min_pt1), tuple(max_pt2), center_pt_list

    #------------------------------------------------

    def show_msg(self, msg):
        if debug: print 'MChkSessionStart.show_msg'
        err_msg = PopupDialog(inString=msg, size=(300,200))
        err_msg.ShowModal()
        err_msg.Destroy()

    #------------------------------------------------

    def onExit(self, event):
        if debug: print 'MChkSessionStart.onExit'
        self.Destroy()
        

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

#====================================================

class MFE_App(wx.App):
    def OnInit(self):
        self.frame = MChkSessionStart()
        self.frame.Show()
        self.SetTopWindow(self.frame)
        return True

#====================================================

# define the current working directory depending on
# whether it's an app or not.
CWD = os.getcwd()
parent_dir = os.path.split(CWD)[0]
info_plist_path = os.path.join(parent_dir, 'Info.plist')
if os.path.isfile(info_plist_path):
    plist_data = plistlib.readPlist(info_plist_path)
    if plist_data["CFBundleDisplayName"] == 'm_ef':
        for i in xrange(3): CWD = os.path.split(CWD)[0]    

debug = False

if __name__ == "__main__":
    if len(argv) > 1:
        if argv[1] == '-w': GNU_notice(1)
        elif argv[1] == '-c': GNU_notice(2)
    else:
        GNU_notice(0)
        app = MFE_App(redirect = False)
        app.MainLoop()
