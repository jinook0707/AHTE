'''
This is for analyzing the video data and calculating the head 
direction. (head turning experiment of common marmoset monkeys)

Requirements :
1) The current working directory should have 'results' directory,
which has directories containing relevant extracted frames from 
session video MP4 file.
This directory name has information segmented by underbar, '_'.
[Group]_[Individual-name]_[Trial#]_[Stimulus]_[Stim.numbering]
e.g.: G2_Kobold_01_BBBA_1
2) Template head image as named as with the group name and the
individual's name.
e.g.: G2_Kobold_head.jpg

This script will search for directories containing extracted frame
images and show the first frame of the first directory as it begins.
There is a grey horizontal line denoting where the feeding hole is.
It should be click-and-dragged to the bottom of the feeding hole,
once at the beginning.
Then spacebar should be pressed to start/stop video analysis.
It will go through all the directories in 'results' directory, 
generating a result CSV file for each directory,  named as same as 
the directory.

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
from math import degrees, radians, hypot, acos, sin, cos, atan2
from random import uniform
from datetime import datetime
from time import time
from shutil import rmtree
from sys import argv

import wx
import cv2
import cv2.cv as cv
import numpy as np
from scipy.cluster.hierarchy import fclusterdata
from scipy import polyfit, polyval

from common_funcs import GNU_notice, writeFile, get_time_stamp, PopupDialog


# --------------------------------------------------

def get_angle(pt1, pt2):
# calculates the angle of a straight line drawn between point one and two.
    dx = pt2[0] - pt1[0]
    dy = (pt2[1] - pt1[1]) * -1
    return degrees( atan2(dy, dx) )

# --------------------------------------------------

def rotate_line(frame_size, pt1, pt2, r_deg=90):
# for rotating a line between pt1 and pt2
# r_deg: angle to rotate
    y_list = [pt1[1], pt2[1]]
    dx = abs(pt1[0]-pt2[0])
    dy = abs(pt1[1]-pt2[1])
    line_len = 100 # max(dx, dy)
    cx = pt1[0] + dx/2 # center X
    cy = min(y_list) + dy/2 # center Y
    deg = get_angle(pt1, pt2)
    if deg < 0: deg = 360 + deg
    r_deg = ( deg + r_deg ) % 360 # rotate given degrees from the degrees of the line
    theta = radians(r_deg)
    r_pt1 = [cx, cy]
    r_pt2 = [ cx + int( line_len*cos(theta) - (1*sin(theta)) ), 
              cy - int( line_len*sin(theta) + (1*cos(theta)) ) ]
    return r_deg, tuple(r_pt1), tuple(r_pt2)

#====================================================

class MarmosetVideoAnalysis(wx.Frame):

    def __init__(self):
        if debug: print 'MarmosetVideoAnalysis.__init__'

        w_size = (1280, 770)
        self.w_size = w_size

        wx.Frame.__init__(self, None, -1, "MVA", pos = (0,20), size = (w_size[0],w_size[1]), style = wx.DEFAULT_FRAME_STYLE)
        #self.Center()
        self.posX = self.GetPosition()[0]
        self.posY = self.GetPosition()[1]

        self.panel = wx.Panel(self, pos = (0,0), size = (w_size[0],w_size[1]))

        self.last_movement_pos = None
        self.mov_th = 15 # threshold(width+height of the rect which surrounds one fragment of contours) to be accounted as valid contour fragment for movement
        self.m_th = 150 # upper-threshold for movement rect
        self.s_frag_th = 30 # lower-threshold for subject's fragment rect size
        self.s_rect_size_th = [40, 150]
        self.HSV_min_wht = (0, 0, 200)
        self.HSV_max_wht = (179, 50, 255)
        self.HSV_min_ear = (0,0,150) # for Marmoset's ear
        self.HSV_max_ear = (179,40,255) # for Marmoset's ear
        self.HSV_min_wood = (10, 50, 150) # wooden color
        self.HSV_max_wood = (30, 255, 255) # wooden color
        self.HSV_min_black = (0,0,0)
        self.HSV_max_black = (179,50,50)
        self.HSV_min_alli = (0,0,0)
        self.HSV_max_alli = (179, 80, 80) # to find the alligator's body
        self.HSV_max_alli2 = (179, 85, 85) # to find the tail tip
        self.HSV_max_alli3 = (179, 95, 95) # to rule out color pixels similar to alligator's color

        self.font = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, 0.5, 0.5, 0, 1, 8)
        self.dirname = None
        self.timer_proc_img = None
        self.flag_run = False
        self.flag_draw_SURF_dots = True
        self.dir_list = [] # sub-directory list of 'results' folder
        self.LED_rects = {}
        self.LED_base_cm = {}
        self.feeding_hole_Y = -1 # the limit position-Y due to the feeding hole (white colors above this line will be ignored)

        posX = 5
        posY = 5
        self.sTxt_fn = wx.StaticText(self.panel, id=-1, pos = (posX, posY), label = 'FolderName: ')
        posX += 300
        self.sTxt_fr = wx.StaticText(self.panel, id=-1, pos = (posX, posY), label = 'Frame: ')

        posX = 5
        posY += self.sTxt_fn.GetSize()[1] + 1
        self.loaded_img_pos = (posX, posY)
        self.loaded_img = wx.StaticBitmap( self.panel, -1, wx.NullBitmap, self.loaded_img_pos, (5,5) )
        self.loaded_img.Bind(wx.EVT_MOUSEWHEEL, self.onMouseWheel)
        self.loaded_img.Bind(wx.EVT_LEFT_DOWN, self.onMouseDown)
        self.loaded_img.Bind(wx.EVT_MOTION, self.onMouseMove)
        self.loaded_img.Bind(wx.EVT_LEFT_UP, self.onMouseUp)
        self.t_loaded_img = wx.StaticBitmap( self.panel, -1, wx.NullBitmap, self.loaded_img_pos, (5,5) )

        ### Connecting key-inputs with some functions
        exit_BtnID = wx.NewId()
        open_BtnID = wx.NewId()
        right_BtnID = wx.NewId()
        space_BtnID = wx.NewId()
        self.Bind(wx.EVT_MENU, self.onExit, id = exit_BtnID)
        self.Bind(wx.EVT_MENU, self.onRight, id = right_BtnID)
        self.Bind(wx.EVT_MENU, self.onSpace, id = space_BtnID)
        accel_tbl = wx.AcceleratorTable([ (wx.ACCEL_CMD,  ord('Q'), exit_BtnID ), 
                                          (wx.ACCEL_NORMAL,  wx.WXK_RIGHT, right_BtnID ), 
                                          (wx.ACCEL_NORMAL,  wx.WXK_SPACE, space_BtnID ) ])
        self.SetAcceleratorTable(accel_tbl)

        if not os.path.isdir(results_dir):
        # if output folder doesn't exist
            _msg = "Please make 'results' folder in the current working directory\n"
            _msg += " and put all the folders, containing JPG images obtained from the trial movies,"
            _msg += " into the 'results' folder."
            self.show_msg(_msg)
            self.Destroy()
        else:
            for f in glob( os.path.join(results_dir, "*") ):
                if os.path.isdir(f):
                    _jpg_img_file = os.path.join(f, "f000001.jpg")
                    if os.path.isfile(_jpg_img_file):
                        self.dir_list.append( os.path.split(f)[1] ) # store directory name
            if len(self.dir_list) == 0:
                _msg = "Please put all the folders, containing JPG images obtained from the trial movies,"
                _msg += " into the 'results' folder."
                self.show_msg(_msg)
                self.Destroy()
            else:
                self.dir_list = sorted(self.dir_list)
                self.init_video_analyzing()

    #------------------------------------------------

    def onRight(self, event):
    # right arrow key is pressed. go forward in the series of images
        if debug: print 'MarmosetVideoAnalysis.onRight'
        if self.flag_run == True: return
        '''
        ### reading LED signals are disabled 
        for key in self.LED_base_cm.iterkeys():
            if self.LED_base_cm[key] == -1:
                self.show_msg('[Base CM of LEDs] have to be set first.')
                return
        '''
        self.proc_img()

    #------------------------------------------------

    def onSpace(self, event):
    # space bar is pressed. 
    # this will toggle (keep running image processing) / (stop processing)
        if debug: print 'MarmosetVideoAnalysis.onSpace'
        '''
        for key in self.LED_base_cm.iterkeys():
            if self.LED_base_cm[key] == -1:
                self.show_msg('[Base CM of LEDs] have to be set first.')
                return
        '''
        if self.flag_run == True:
            self.timer_proc_img.Stop()
            self.timer_proc_img = None
            self.flag_run = False
        else:
            self.flag_run = True
            self.proc_img()

    #------------------------------------------------
    
    def cvImg_to_wxBMP(self, cvImg):
        if debug: print 'MarmosetVideoAnalysis.cvImg_to_wxBMP'

        cv.CvtColor(cvImg, cvImg, cv.CV_BGR2RGB)
        img = wx.EmptyImage(cvImg.width, cvImg.height)
        img.SetData(cvImg.tostring())
        bmp = img.ConvertToBitmap()
        return bmp

    #------------------------------------------------

    def load_jpg_file(self, filepath, flag='wx'):
        if debug: print 'MarmosetVideoAnalysis.load_jpg_file'

        ret_img = None
        if os.path.isfile(filepath): # if the file exist
            if flag == 'wx':
                img = wx.Image(filepath, wx.BITMAP_TYPE_ANY)
                bmp = img.ConvertToBitmap()
                ret_img = wx.StaticBitmap(self.panel, -1, bmp, self.loaded_img_pos)
            elif flag == 'cv':
                ret_img = cv.LoadImage(filepath)
        return ret_img

    #------------------------------------------------

    def onMouseDown(self, event):
        if debug: print 'MarmosetVideoAnalysis.onMouseDown'
        self.loaded_img.SetFocus()
        mp = event.GetPosition()
        if mp[1]-5 < self.feeding_hole_Y < mp[1]+5:
            self.selected_obj_key = 'feeding_hole_Y'
        else:
            for key in self.LED_rects.iterkeys(): # for each LED rects
                _x = self.LED_rects[key][0]; _y = self.LED_rects[key][1]
                _sz = self.LED_rects[key][2]
                if _x-_sz < mp[0] < _x+_sz and _y-_sz < mp[1] < _y+_sz:
                # if the event happened while the pointer is in a LED rect
                    self.selected_obj_key = key

    #------------------------------------------------

    def onMouseMove(self, event):
        if debug: print 'MarmosetVideoAnalysis.onMouseMove'
        mp = event.GetPosition()
        if self.selected_obj_key != -1:
            if self.selected_obj_key == 'feeding_hole_Y':
                self.feeding_hole_Y = mp[1]
                if self.flag_run == False: self.proc_img(self.orig_img) # reload the current frame
            else:
                self.LED_rects[self.selected_obj_key][0] = mp[0] - self.LED_rects[self.selected_obj_key][2]/2
                self.LED_rects[self.selected_obj_key][1] = mp[1] - self.LED_rects[self.selected_obj_key][3]/2
                if self.flag_run == False: self.proc_img(self.orig_img) # reload the current frame

    #------------------------------------------------

    def onMouseUp(self, event):
        if debug: print 'MarmosetVideoAnalysis.onMouseUp'
        self.selected_obj_key = -1

    #------------------------------------------------

    def onMouseWheel(self, event):
        if debug: print 'MarmosetVideoAnalysis.onMouseWheel'
        mp = event.GetPosition() # mouse position at the wheel event
        for key in self.LED_rects.iterkeys(): # for each LED rects
            _x = self.LED_rects[key][0]; _y = self.LED_rects[key][1]
            _sz = self.LED_rects[key][2]
            if _x-_sz < mp[0] < _x+_sz and _y-_sz < mp[1] < _y+_sz:
            # if the event happened while the pointer is in a rect
                ### increase or decrease the rect size
                if event.GetWheelRotation() < 0: _new_value = max(10, self.LED_rects[key][2] - 1) # minimum 10
                else: _new_value = min(50, self.LED_rects[key][2] + 1) # maximum 50
                self.LED_rects[key][2] = self.LED_rects[key][3] = _new_value
                if self.flag_run == False: self.proc_img(self.orig_img) # reload the current frame

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
        LED_on = [ False, False, False, False ]
        for key in self.LED_rects.iterkeys():
            self.find_color((self.LED_rects[key][0],self.LED_rects[key][1],self.LED_rects[key][2],self.LED_rects[key][3]), 
                            self.curr_frame, 
                            self.HSV_min_wht,  
                            self.HSV_max_wht, 
                            (0,0,0))
            img_mat = cv.GetMat(self.tmp_grey_img)
            moments = cv.Moments(img_mat)
            cm = cv.GetCentralMoment(moments, 0, 0)
            if self.LED_base_cm[key] != -1 and cm > self.LED_base_cm[key] + 300:
                LED_on[ self.LED_labels.index(key) ] = True
            #print self.LED_base_cm[i], cm
        return LED_on

    #------------------------------------------------
        
    def init_video_analyzing(self):
    # initialize variables for video image processing
        if debug: print 'MarmosetVideoAnalysis.init_video_analyzing'

        if len(self.dir_list) == 0: # there's no more directory
            self.flag_run = False
            return
        else:
            self.dirname = self.dir_list[0]
        ### for Marmoset's ear
        if 'Pooh' in self.dirname: self.HSV_min_ear = (0,0,120)
        elif 'Yara' in self.dirname: self.HSV_min_ear = (0,0,165)
        elif 'Kobold' in self.dirname: self.HSV_min_ear = (0,0,120)
        elif 'Smart' in self.dirname: self.HSV_min_ear = (0,0,160)
        elif 'Locri' in self.dirname: self.HSV_min_ear = (0,0,160)
        elif 'Augustina' in self.dirname: self.HSV_min_ear = (0,0,150)
        else: self.HSV_min_ear = (0,0,140)
        
        self.dir_list.pop(0)
        csv_file_path = os.path.join( results_dir, self.dirname + ".csv" )
        self.outputCSV = open(csv_file_path, 'w') # result output CSV file
        self.outputCSV.write('# Ear-rect : Ear1_UpperLeft_PT/Ear1_LowerRight_PT/Ear2_UpperLeft_PT/Ear2_LowerRight_PT\n')
        self.outputCSV.write('Frame-index, Ear-rect, Direction, Direction-line-start, Direction-line-end\n')
        self.sTxt_fn.SetLabel('FolderName: %s'%(self.dirname))
        self.fi = 1 # frame index; Marmoset frame files' indices are 1~1000
        _fp = os.path.join(results_dir, self.dirname, 'f%.6i.jpg'%self.fi)
        frame = cv.LoadImage(_fp) # load image
        self.frame_size = cv.GetSize(frame)
        self.SetSize( (self.frame_size[0]+10, self.frame_size[1]+50) )
        self.frame_cnt = len(glob( os.path.join(results_dir, self.dirname, '*.jpg') ))
        self.curr_frame = cv.CreateImage(self.frame_size, 8, 3)
        self.orig_img = cv.CreateImage(self.frame_size, 8, 3)
        self.HSV_img = cv.CreateImage(self.frame_size, 8, 3)
        self.tmp_col_img = cv.CreateImage(self.frame_size, 8, 3)
        self.grey_img = cv.CreateImage(self.frame_size, cv.IPL_DEPTH_8U, 1)
        self.grey_avg = cv.CreateImage(self.frame_size, cv.IPL_DEPTH_32F, 1)
        self.tmp_grey_img = cv.CreateImage(self.frame_size, cv.IPL_DEPTH_8U, 1)
        self.diff_grey_img = cv.CreateImage(self.frame_size, cv.IPL_DEPTH_8U, 1)
        self.grey_avg = cv.CreateImage(self.frame_size, cv.IPL_DEPTH_32F, 1)
        self.storage = cv.CreateMemStorage(0)
        self.mask_img = cv.CreateImage(self.frame_size, 8, 1)
        _tmp = self.dirname.split('_')
        _head_fn = '%s_%s_head.jpg'%(_tmp[0], _tmp[1])
        self.template_fp = os.path.join(results_dir, _head_fn)
        self.template_img = cv.LoadImage( self.template_fp )
        #cv.CvtColor(self.template_img, self.template_img, cv.CV_BGRA2BGR)
        self.first_run = True

        self.curr_frame = cv.CloneImage(frame)
        if self.feeding_hole_Y == -1: self.feeding_hole_Y = 240
        
        ### init LED related variables
        if len(self.LED_rects) == 0:
            self.LED_labels = ['UL', 'LL', 'UR', 'LR']
            _mx = self.w_size[0]/2; _my = self.w_size[1]/2
            for key in self.LED_labels:
                if key == 'UL': _x=_mx-180; _y=_my-100
                elif key == 'LL': _x=_mx-150; _y=_my-50
                elif key == 'UR': _x=_mx+100; _y=_my-100
                elif key == 'LR': _x=_mx+150; _y=_my-60
                self.LED_rects[key] = [_x, _y, 15, 15]  # [x, y, w, h]
                self.LED_base_cm[key] = -1 # base central moment
        self.LED_signal_start_fi = -1
        self.LED_num = [0, 0, 0, 0]
        self.LED_last_signal_fi = [-1, -1, -1, -1] # frame index when the last signal (white color) was on
        self.LED_prev_on = [False, False, False, False]
        self.selected_obj_key = -1
        
        self.prev_hd = [] # previous head directions
        self.prev_hd_last = -1 # frame number when the last head direction was updated
        self.proc_img(frame) # display the 1st frame

    #------------------------------------------------

    def proc_img(self, frame=None):
    # read a jpg image, computer vision process, then display it.
        if debug: print 'MarmosetVideoAnalysis.proc_img'

        if frame == None:
            self.fi += 1
            _fp = os.path.join(results_dir, self.dirname, 'f%.6i.jpg'%self.fi)
            if os.path.isfile(_fp) == False: # file doesn't exist
                self.init_video_analyzing() # move to the next trial folder
                return
            else:
                self.orig_img = cv.LoadImage(_fp) # load image
        else: 
            self.orig_img = frame
        cv.Copy(self.orig_img, self.curr_frame)

        cv.Line(self.curr_frame, (0,self.feeding_hole_Y-1), (self.frame_size[0],self.feeding_hole_Y-1), (50,50,50), 1) # bottom of feeding hole

        self.grey_img = self.preprocessing(self.orig_img)

        # ------------------------------------------------
        # SURF extraction starts
        # ------------------------------------------------
        t_img = cv2.imread(self.template_fp)
        cv.Zero(self.mask_img)
        cv.Zero(self.tmp_grey_img)
        cv.Rectangle(self.mask_img, (0,self.feeding_hole_Y), (self.frame_size[0], self.frame_size[1]), 255, -1)
        cv.Copy(self.grey_img, self.tmp_grey_img, self.mask_img) # copy only below feeding hole
        mat = cv.GetMat(self.tmp_grey_img)
        hgrey = np.asarray(mat)
        ngrey = cv2.cvtColor(t_img, cv2.COLOR_BGR2GRAY)

        # build feature detector and descriptor extractor
        hessian_threshold = 300
        detector = cv2.SURF(hessian_threshold)
        (hkeypoints, hdescriptors) = detector.detectAndCompute(hgrey, None, useProvidedKeypoints = False)
        (nkeypoints, ndescriptors) = detector.detectAndCompute(ngrey, None, useProvidedKeypoints = False)

        # extract vectors of size 64 from raw descriptors numpy arrays
        rowsize = len(hdescriptors) / len(hkeypoints)
        if rowsize > 1:
            hrows = np.array(hdescriptors, dtype = np.float32).reshape((-1, rowsize))
            nrows = np.array(ndescriptors, dtype = np.float32).reshape((-1, rowsize))
            #print hrows.shape, nrows.shape
        else:
            hrows = np.array(hdescriptors, dtype = np.float32)
            nrows = np.array(ndescriptors, dtype = np.float32)
            rowsize = len(hrows[0])

        # kNN training - learn mapping from hrow to hkeypoints index
        samples = hrows
        responses = np.arange(len(hkeypoints), dtype = np.float32)
        #print len(samples), len(responses)
        knn = cv2.KNearest()
        knn.train(samples,responses)

        # retrieve index and value through enumeration
        if self.flag_draw_SURF_dots == True: temp_img = cv.CloneImage(self.template_img)
        m_pts = [] # list of matched points
        for i, descriptor in enumerate(nrows):
            descriptor = np.array(descriptor, dtype = np.float32).reshape((1, rowsize))
            #print i, descriptor.shape, samples[0].shape
            retval, results, neigh_resp, dists = knn.find_nearest(descriptor, 1)
            res, dist =  int(results[0][0]), dists[0][0]
            #print res, dist

            if dist < 0.1:
                # draw matched keypoints in red color
                color = (0, 0, 255)
                x,y = hkeypoints[res].pt
                m_pts.append( (int(x),int(y)) )
            else:
                # draw unmatched in blue color
                color = (255, 0, 0)
            if self.flag_draw_SURF_dots == True:
                ### draw matched key points on haystack image
                x,y = hkeypoints[res].pt
                center = (int(x),int(y))
                cv.Circle(self.curr_frame, center, 2, color, -1)
                ### draw matched key points on needle image
                x,y = nkeypoints[i].pt
                center = (int(x),int(y))
                cv.Circle(temp_img, center, 2, color, -1)

        # ------------------------------------------------
        # SURF extraction ends
        # ------------------------------------------------

        if len(m_pts) >= 3:
        # there are, at least, 2 matched points after SURF
            number_of_mGroups, mGroups = self.clustering(m_pts, 100) # clustrering matched points
            len_mg = []
            for mg in mGroups: len_mg.append( len(mg) )
            idx = len_mg.index( max(len_mg) )
            mg_r = cv.BoundingRect( mGroups[idx] )
            if mg_r[2] + mg_r[3] > 75:
            # process only if the head rect size is big enough
                ### calculate the average x & y of the group as the center point of head
                _cx = 0; _cy = 0
                for mg in mGroups[idx]: _cx += mg[0]; _cy += mg[1]
                center = ( _cx/len(mGroups[idx]), _cy/len(mGroups[idx]) )
                #cv.Circle(self.curr_frame, center, 5, (0,255,255), -1)
                ### draw rectangle for head position
                h_rect = [center[0]-150, center[1]-100, center[0]+150, center[1]+100] # head rect (x1,y1,x2,y2 rect)
                if h_rect[1] <= self.feeding_hole_Y: h_rect[1] = self.feeding_hole_Y + 1
                cv.Rectangle(self.curr_frame, (h_rect[0],h_rect[1]), (h_rect[2],h_rect[3]), (0,255,255), 1)
                ### find ear color
                self.find_color((h_rect[0],h_rect[1],h_rect[2],h_rect[3]), 
                                self.curr_frame, 
                                self.HSV_min_ear, 
                                self.HSV_max_ear, 
                                (0,0,0))
                _pt1_list, _pt2_list, _min_pt1, _max_pt2, _center_pt_list = self.get_points(self.tmp_grey_img, self.s_frag_th)
                number_of_eGroups, eGroups = self.clustering(_center_pt_list, 55) # clustrering ear points
                pt1_list = []; pt2_list = []; center_pt_list = []; sz =  []
                for ept_group in eGroups:
                    ### group points with the grouped center points
                    _pts = []
                    for ept in ept_group:
                        _idx = _center_pt_list.index(ept)
                        _pts.append(_pt1_list[_idx])
                        _pts.append(_pt2_list[_idx])
                    er = cv.BoundingRect(_pts)
                    if er[2]+er[3] < 40: continue # exclude too small rects
                    ### calculate and store grouped rects
                    pt1_list.append( (er[0], er[1]) )
                    pt2_list.append( (er[0]+er[2], er[1]+er[3]) )
                    center_pt_list.append( (er[0]+er[2]/2, er[1]+er[3]/2) )
                    sz.append( er[2]+er[3] )
                    cv.Rectangle(self.curr_frame, pt1_list[-1], pt2_list[-1], (255,255,0), 1)
                if len(pt1_list) >= 2: 
                # there are, at least, 2 rects
                    ### get indices for the largest and the 2nd largest
                    ear1_idx = -1; ear2_idx = -1
                    for _ei in xrange(len(pt1_list)):
                        if ear1_idx == -1: ear1_idx = copy(_ei)
                        else:
                            if sz[_ei] > sz[ear1_idx]: ear1_idx = copy(_ei) 
                    for _ei in xrange(len(pt1_list)):
                        if _ei == ear1_idx: continue
                        if ear2_idx == -1: ear2_idx = copy(_ei)
                        else:
                            if sz[_ei] > sz[ear2_idx]: ear2_idx = copy(_ei)
                    if ear1_idx != -1 and ear2_idx != -1:
                    # if indices of both ears are determined.
                        ear1_center = center_pt_list[ear1_idx]
                        ear2_center = center_pt_list[ear2_idx]
                        ### draw ear rects and record it in CSV
                        cv.Rectangle(self.curr_frame, pt1_list[ear1_idx], pt2_list[ear1_idx], (255,0,0), 1)
                        cv.Rectangle(self.curr_frame, pt1_list[ear2_idx], pt2_list[ear2_idx], (255,0,0), 1) 
                        _earR = '%i/%i/%i/%i'%(pt1_list[ear1_idx][0], 
                                               pt2_list[ear1_idx][1], 
                                               pt1_list[ear2_idx][0], 
                                               pt2_list[ear2_idx][1])
                        ### left side point becomes pos1
                        if pt1_list[ear2_idx][0] < pt1_list[ear1_idx][0]:
                            tmp = copy(ear1_idx)
                            ear1_idx = copy(ear2_idx)
                            ear2_idx = tmp
                        ### display line connecting ears & head direction line
                        pos1 = [ pt1_list[ear1_idx][0] + abs(pt1_list[ear1_idx][0]-pt2_list[ear1_idx][0])/2, 
                                 pt1_list[ear1_idx][1] + abs(pt1_list[ear1_idx][1]-pt2_list[ear1_idx][1])/2 ]
                        pos2 = [ pt1_list[ear2_idx][0] + abs(pt1_list[ear2_idx][0]-pt2_list[ear2_idx][0])/2, 
                                 pt1_list[ear2_idx][1] + abs(pt1_list[ear2_idx][1]-pt2_list[ear2_idx][1])/2 ]
                        cv.Line(self.curr_frame, tuple(pos1), tuple(pos2), (255,0,0), 1) # line between ears
                        r_deg, r_p1, r_p2 = rotate_line(self.frame_size, pos1, pos2) # calculate head direction
                        if len(self.prev_hd) < 1: # collect some frames as previous head direction references
                            self.prev_hd.append( copy(r_deg) ) # store the direction
                            self.prev_hd_last = copy( self.fi ) # last frame when the head direction was collected
                        else:
                            #m_val = np.median(self.prev_hd)
                            m_val = self.prev_hd[0]
                            '''
                            m_val = self.prev_hd[1]
                            for hdi in xrange(1, len(self.prev_hd)):
                            diff = ((m_val - self.prev_hd[hdi] + 180 + 360) % 360) - 180
                            m_val = (360 + self.prev_hd[hdi] + (diff/2)) % 360
                            '''
                            alt_r_deg = (r_deg + 180) % 360 # alternate degree (opposite direction)
                            diff1 = abs(m_val - r_deg)
                            if diff1 > 180: diff1 = 180 - (diff1 % 180)
                            diff2 = abs(m_val - alt_r_deg)
                            if diff2 > 180: diff2 = 180 - (diff2 % 180)
                            #print self.fi, m_val, r_deg, alt_r_deg, diff1, diff2
                            #print self.prev_hd
                            if min([diff1, diff2]) < 45: # if minimum degree is bigger than 45, ignore this head direction
                                if diff1 > diff2: # if alternate degree has smaller difference
                                    r_deg, r_p1, r_p2 = rotate_line(self.frame_size, pos1, pos2, -90) # calculate the points again
                                self.prev_hd.append( copy(r_deg) ) # store the direction
                                self.prev_hd_last = copy( self.fi ) # last frame when the head direction was collected
                                if len(self.prev_hd) == 2: self.prev_hd.pop(0) # collect 1 frame
                                _fi = self.fi - 1 # Marmoset frame images have 1~1000 indices. Make it to 0~999
                                _output = '%i, %s, %i, %i/%i, %i/%i\n'%( _fi, # frame-index
                                                                         _earR, # ear-rect
                                                                         r_deg, # (head) direction
                                                                         r_p1[0], # direction line start point-X
                                                                         r_p1[1], # direction line start point-Y
                                                                         r_p2[0], # direction line end point-X
                                                                         r_p2[1] )# direction line end point-Y
                                self.outputCSV.write( _output ) 
                                cv.Line(self.curr_frame, r_p1, r_p2, (0,0,255), 1) # draw head direction line
                        if self.fi - self.prev_hd_last > 10: # if there was no head direction update for 10 frames
                            self.prev_hd = [] # initialize previous head directions
                            self.prev_hd_last = copy( self.fi ) # last frame when the head direction was collected

        #self.tmp_col_img = cv.CreateImage(self.frame_size, 8, 3)
        #cv.CvtColor(_tmp, self.tmp_col_img, cv.CV_GRAY2BGR)
        self.loaded_img.SetBitmap( self.cvImg_to_wxBMP(self.curr_frame) ) # display image
        if self.flag_draw_SURF_dots == True:
            self.t_loaded_img.SetBitmap( self.cvImg_to_wxBMP(temp_img) )

        ### show timestamp
        self.sTxt_fr.SetLabel('Frame: %i / %i'%(self.fi, self.frame_cnt))

        if self.flag_run == True:
            self.timer_proc_img = wx.FutureCall(5, self.proc_img)

    #------------------------------------------------

    def find_color(self, rect, inImage, HSV_min, HSV_max, bgcolor=(255,255,255)):
    # Find a color(range: 'HSV_min' ~ 'HSV_max') in an area('rect') of an image('inImage')
    # 'bgcolor' is a background color of the masked image
    # Result will be stored in self.tmp_grey_img
        if debug: print 'MarmosetVideoAnalysis.find_color'

        cv.Zero(self.mask_img)
        cv.Zero(self.tmp_grey_img)
        cv.Set(self.tmp_col_img, bgcolor)
        cv.Rectangle(self.mask_img, (rect[0], rect[1]), (rect[2], rect[3]), 255, cv.CV_FILLED)
        cv.Copy(inImage, self.tmp_col_img, self.mask_img)
        self.tmp_col_img = self.preprocessing_col(self.tmp_col_img)
        cv.CvtColor(self.tmp_col_img, self.HSV_img, cv.CV_BGR2HSV)
        cv.InRangeS(self.HSV_img, HSV_min, HSV_max, self.tmp_grey_img)     

    #------------------------------------------------

    def preprocessing(self, inImage):
        if debug: print 'MarmosetVideoAnalysis.preprocessing'
        cv.CvtColor(inImage, self.tmp_grey_img, cv.CV_RGB2GRAY)
        #cv.Smooth(self.tmp_grey_img, self.tmp_grey_img, cv.CV_GAUSSIAN, 3, 0)
        #cv.Dilate(self.tmp_grey_img, self.tmp_grey_img, None, 1)
        #cv.Erode(self.tmp_grey_img, self.tmp_grey_img, None, 1)
        return cv.CloneImage(self.tmp_grey_img)

    #------------------------------------------------
    
    def preprocessing_col(self, inImage):
        if debug: print 'MarmosetVideoAnalysis.preprocessing_col'
        cv.Smooth(inImage, inImage, cv.CV_GAUSSIAN, 5, 0)
        cv.Dilate(inImage, inImage, None, 3)
        cv.Erode(inImage, inImage, None, 3)
        return cv.CloneImage(inImage)

    #------------------------------------------------

    def get_points(self, inImage, threshold=15):
    # get the binary image after edge-detection and returns the some useful points of its contours
    # 'threshold' : threshold for a contour fragment
        if debug: print 'MarmosetVideoAnalysis.get_points'

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

    def clustering(self, pt_list, threshold):
        if debug: print 'MarmosetVideoAnalysis.clustering'

        pt_arr = np.asarray(pt_list)
        result = []
        try: result = list(fclusterdata(pt_arr, threshold, 'distance'))
        except: pass
        number_of_groups = 0
        groups = []
        if result != []:
            groups = []
            number_of_groups = max(result)
            for i in range(number_of_groups): groups.append([])
            for i in range(len(result)):
                groups[result[i]-1].append(pt_list[i])
        return number_of_groups, groups

    #------------------------------------------------

    def show_msg(self, msg):
        if debug: print 'MarmosetVideoAnalysis.show_msg'
        err_msg = PopupDialog(inString=msg, size=(300,200))
        err_msg.ShowModal()
        err_msg.Destroy()

    #------------------------------------------------

    def onExit(self, event):
        if debug: print 'MarmosetVideoAnalysis.onExit'
        if self.dirname != None: self.outputCSV.close()
        self.Destroy()

#====================================================

CWD = os.getcwd()
debug = False
results_dir = os.path.join(CWD, "results")

if __name__ == "__main__":      
    if len(argv) > 1:
        if argv[1] == '-w': GNU_notice(1)
        elif argv[1] == '-c': GNU_notice(2)
    else:
        GNU_notice(0)  
        MVAApp = wx.PySimpleApp()
        MVA_inst = MarmosetVideoAnalysis()
        MVA_inst.Show(True)
        MVAApp.MainLoop()
