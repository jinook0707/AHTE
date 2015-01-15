# coding: UTF-8

'''
App for running a head turning experiment with common marmoset monkeys.
This app 
  shows webcam view for checking Marmoset, licking palatable food
  plays a set of auditory stimuli
  plays a white noise for screening the stimuli sound 
    with a specific audio output device using PyAudio
  turns a LED light briefly when a session starts to synchronize 
    with recordings with other camera(s) by using Arduino and pySerial.

----------------------------------------------------------------------
Copyright (C) 2014 Jinook Oh, W. Tecumseh Fitch
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

import wave, Queue, plistlib
from threading import Thread
from os import getcwd, path, mkdir
from copy import copy
from math import sqrt
from time import time, sleep
from glob import glob
from datetime import timedelta, datetime
from random import shuffle
from struct import pack
from sys import argv

import wx
import pyaudio
import cv2
import cv2.cv as cv
import numpy as np
import serial

# ----------------------------------------------------------------------------------------

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

# ----------------------------------------------------------------------------------------

def get_time_stamp():
    ts = datetime.now()
    ts = ('%.4i_%.2i_%.2i_%.2i_%.2i_%.2i_%.6i')%(ts.year, ts.month, ts.day, ts.hour, ts.minute, ts.second, ts.microsecond)
    return ts

# ----------------------------------------------------------------------------------------

def writeFile(file_path, txt, mode='a'):
    f = open(file_path, mode)
    f.write(txt)
    f.close()

# ----------------------------------------------------------------------------------------

def get_cam_idx():
# returns indices of attached usable webcams
    idx = []
    for i in xrange(3): # maximum three are attached
        tmp = cv.CaptureFromCAM(i)
        tmp_frame = cv.QueryFrame(tmp)
        del(tmp)
        if tmp_frame != None and tmp_frame.width != 1280: 
        # != 1280, webcams we intend to use will have 640 width
            idx.append(i)
        del(tmp_frame)
    return idx

# ----------------------------------------------------------------------------------------

def error_msg(msg, size):
    dlg = PopupDialog(inString=msg, size=size)
    dlg.ShowModal()
    dlg.Destroy()

# ======================================================

class Output_AudioData(object):
# class for playing sounds.
    def __init__(self, output_dev_keywords=['built-in'], sample_width=2, rate=44100, wav_buffer=1024, channels=1):
    # sample_width: desired sample width in bytes (1, 2, 3, or 4)
        self.pa = pyaudio.PyAudio()
        self.w_buffer = wav_buffer
        self.channels = channels
        self.sample_width = sample_width
        self.rate = rate
        self.ps_th = [] # play-sound thread
        self.ps_q = [] # play_sound queue
        self.init_sounds()
        
        for i in range(len(output_dev_keywords)): output_dev_keywords[i] = output_dev_keywords[i].lower()
        self.device_index_list, self.device_name_list = self.find_output_device(output_dev_keywords)

        self.streams = []
        self.open_output_streams()
        print '%i streams are open.'%len(self.streams)

    # --------------------------------------------------

    def init_sounds(self):
        self.wfs = []
        self.sound_lengths = []

    # --------------------------------------------------

    def load_sounds(self, snd_files=[]):
        if snd_files == []: return
        for snd_file in snd_files:
            self.wfs.append(wave.open(snd_file, 'rb'))
            numFrames = self.wfs[-1].getnframes() # this is accurate whether for stereo or mono
            sRate = float(self.wfs[-1].getframerate())
            self.sound_lengths.append(round(1000*numFrames/sRate)) # length in msecs

    # --------------------------------------------------

    def open_output_streams(self):
        for i in range(len(self.device_index_list)):
            try:
                self.streams.append( self.pa.open(format = self.pa.get_format_from_width(self.sample_width),
                                                channels = self.channels,
                                                rate = self.rate,
                                                output_device_index = self.device_index_list[i],
                                                output = True) )
                self.ps_th.append(None)
                self.ps_q.append(Queue.Queue())
            except:
                pass

    # --------------------------------------------------

    def close_output_streams(self):
        if len(self.streams) > 0:
            for i in range(len(self.streams)):
                self.streams[i].close()
        self.streams = []

    # --------------------------------------------------

    def find_output_device(self, output_dev_keywords):
        built_in_output_idx = -1
        device_index_list = []       
        device_name_list = []
        for i in range( self.pa.get_device_count() ):     
            devinfo = self.pa.get_device_info_by_index(i) 
            print "Device #%i: %s"%(i, devinfo["name"])
            for j in range(len(output_dev_keywords)):
                if output_dev_keywords[j] in devinfo["name"].lower():
                    if devinfo["maxOutputChannels"] > 0:
                        print( "Found an audio-output: device %d - %s"%(i,devinfo["name"]) )
                        device_index_list.append(i)
                        device_name_list.append(devinfo["name"])
        if device_index_list == []:
            print( "No preferred audio-output found" )
        return device_index_list, device_name_list

    # --------------------------------------------------

    def play_sound_run(self, snd_idx, stream_idx=0, volume=1.0):
        audio_output_data = self.wfs[snd_idx].readframes(self.w_buffer)
        '''
        if volume != 1.0:
            s = np.fromstring(audio_output_data, np.int16) * volume
            audio_output_data = pack('h'*len(s), *s)
        '''
        msg = ''
        while audio_output_data != '':
            self.streams[stream_idx].write(audio_output_data)
            audio_output_data = self.wfs[snd_idx].readframes(self.w_buffer)
            '''
            if volume != 1.0:
                s = np.fromstring(audio_output_data, np.int16) * volume
                audio_output_data = pack('h'*len(s), *s)
            '''
            try: msg = self.ps_q[stream_idx].get(False)
            except Queue.Empty: pass
            if msg == 'terminate': break
        self.wfs[snd_idx].rewind()
        self.ps_th[stream_idx] = None

    # --------------------------------------------------

    def play_sound(self, snd_idx=0, stream_idx=0, volume=1.0, stop_prev_snd=False):
    # This function works with 'play_sound_run'. Generate a thread and use it for playing a sound once.
    # stop_prev_snd = False; means that if the requested stream is busy, it ignores the request to play sound.
        if self.ps_th[stream_idx] != None:
            if stop_prev_snd == True:
                self.ps_q[stream_idx].put('terminate', True, None)
                self.ps_th[stream_idx].join()
                self.ps_th[stream_idx] = None
            else:
                return False
        self.ps_th[stream_idx] = Thread(target=self.play_sound_run, args=(snd_idx, stream_idx, volume))
        self.ps_th[stream_idx].start()
        return True        

# ======================================================

class Cam:
# class for displaying webcam view
    def __init__(self, parent, cam_idx, pos=(300, 25)):
        pos = list(pos)
        self.parent = parent
        self.font = cv.InitFont(cv.CV_FONT_HERSHEY_SIMPLEX, 0.5, 0.5, 0, 1, 8)
        self.cam_idx = cam_idx
        self.cap_cam = []
        w = 512; h = 384
        for i in xrange(len(self.cam_idx)):
            _ci = self.cam_idx[i]
            self.cap_cam.append(cv.CaptureFromCAM(_ci)) # capturing camera
            cv.SetCaptureProperty(self.cap_cam[-1], cv.CV_CAP_PROP_FRAME_WIDTH, w)
            cv.SetCaptureProperty(self.cap_cam[-1], cv.CV_CAP_PROP_FRAME_HEIGHT, h)
            cv.SetCaptureProperty(self.cap_cam[-1], cv.CV_CAP_PROP_FPS, 15)
            cv.NamedWindow('Marmoset_EXPMT_CAM%.2i'%i, cv.CV_WINDOW_NORMAL)
            cv.MoveWindow('Marmoset_EXPMT_CAM%.2i'%i, pos[0], pos[1])
            pos[1] += h
        self.rc_q = Queue.Queue()

    # --------------------------------------------------

    def run(self):
        msg = ''
        prev_fps_time = time()
        prev_fps = 0
        fps = 0
        while True:
            frame_start_time = time()
            ### check FPS
            if frame_start_time - prev_fps_time >= 1:
                prev_fps = copy(fps)
                fps = 0
                prev_fps_time = time()
            else:
                fps += 1

            for i in xrange(len(self.cap_cam)):
                frame = cv.QueryFrame(self.cap_cam[i]) # get image
                if frame == None: continue
                #cv.PutText( frame, str(prev_fps), (15, 15), self.font, (125,125,125) ) # write FPS
                cv.ShowImage("Marmoset_EXPMT_CAM%.2i"%i, frame)
            
            ### listen to the message to break.
            try: msg = self.rc_q.get(False)
            except Queue.Empty: pass
            if msg == 'quit': break

            cv.WaitKey(30)
        for i in xrange(len(self.cam_idx)):
            cv.DestroyWindow("Marmoset_EXPMT_CAM%.2i"%i)

# ======================================================

class Experiment(wx.Frame):
    def __init__(self):
        self.input_folder = 'input'
        self.Cam_inst = None
        self.session_start_time = -1
        self.audStim = []
        self.si = 1 # session index (starting from 1)
        self.white_noise_volume = 1.0

        ### output folder check
        output_folder = path.join(CWD, 'output')
        if path.isdir(output_folder) == False: mkdir(output_folder)

        ### determining experiment day & make a folder with it
        timestamp = get_time_stamp()[:-7]
        self.day_of_expmt = 1
        for f in glob(path.join(output_folder, '*')):
            if path.isdir(f) and path.basename(f).startswith('EXPMT_DAY_'):
                flag_match_ts = False
                for logF in sorted(glob(path.join(f, '*.log'))):
                    if path.basename(logF).startswith(timestamp[:10]) == True:
                    # if today's yyyy_mm_dd matches with the log file in already existing EXPMT_DAY folder
                        flag_match_ts = True # there's matching timestamped log file already (= will stop increasing EXPMT_DAY)
                        ### read the log file
                        _f = open(logF, 'r')
                        lines = _f.readlines()
                        _f.close()
                        for line in lines:
                            if 'Beginning of session-' in line: self.si += 1 # increase the session index
                if flag_match_ts == True: break # quit the for-loop
                else: self.day_of_expmt += 1
        expmt_day_folder_name = 'EXPMT_DAY_%.2i'%(self.day_of_expmt)
        log_output_folder = path.join( output_folder, expmt_day_folder_name )
        if path.isdir(log_output_folder) == False: mkdir( log_output_folder )
        
        ### opening log file
        self.log = ""
        self.log_file_path = path.join(log_output_folder, '%s.log'%(timestamp))
        self.write_log('%s, Begining of the program on EXPMT_DAY_%.2i'%(get_time_stamp(), self.day_of_expmt))

        self.w_size = (550, 370)
        self.loaded_img = None
        self.loaded_img_pos = (5, self.w_size[1]-480)
        self.last_play_time = -1 # time when the last stimulus was play

        wx.Frame.__init__(self, None, -1, 'Marmoset EXPMT', size=self.w_size)
        self.SetPosition( (5, 30) )
        self.Show(True)
        self.panel = wx.Panel(self, pos=(0,0), size=self.w_size)

        ### set an instance for audio output for white noise playing
        self.white_noise_output = Output_AudioData(rate=44100, output_dev_keywords=['USB Dongle'], wav_buffer=1024)
        self.write_log( '%s, a PyAudio instance for white noise output is set up with %s.'%(get_time_stamp(), str(self.white_noise_output.device_name_list)) )
        self.white_noise_output.load_sounds( [path.join(self.input_folder, '_white_noise.wav')] )

        ### user interface setup
        posX = 5
        posY = 10
        b_space = 30
        self.btn_cam = wx.Button(self.panel, -1, label='Toggle webcams', pos=(posX,posY), size=(120, -1))
        self.btn_cam.Bind(wx.EVT_LEFT_UP, self.onToggleCam)
        posY += b_space
        self.btn_session = wx.Button(self.panel, -1, label='Start session', pos=(posX,posY), size=(120, -1))
        self.btn_session.Bind(wx.EVT_LEFT_UP, self.onStartSession)
        posY += b_space
        self.btn_dir = wx.Button(self.panel, -1, label='Stimuli directory', pos=(posX,posY), size=(120, -1))
        self.btn_dir.Bind(wx.EVT_LEFT_UP, self.onChooseDir)
        self.btn_dir.Disable()
        posY += b_space + 10
        self.btn_white_noise = wx.Button(self.panel, -1, label='White noise', pos=(posX,posY), size=(90, -1))
        self.btn_white_noise.Bind(wx.EVT_LEFT_UP, self.onPlayWhiteNoise)
        self.white_noise_panel = wx.Panel(self.panel, -1, pos=(110, posY+5), size=(20, 20))
        self.white_noise_panel.SetBackgroundColour( wx.WHITE )
        #self.white_noise_panel.Bind(wx.EVT_LEFT_UP, self.onWhiteNoisePanelClick)
        self.white_noise_panel.Bind(wx.EVT_PAINT, self.onWhiteNoisePanelPaint)
        posY += b_space
        self.btn_play = wx.Button(self.panel, -1, label='Play a stimulus', pos=(posX,posY), size=(120, -1))
        self.btn_play.Bind(wx.EVT_LEFT_UP, self.onPlay)
        self.btn_play.Disable()
        posY += b_space + 10
        self.btn_end_s = wx.Button(self.panel, -1, label='End session', pos=(posX,posY), size=(120, -1))
        self.btn_end_s.Bind(wx.EVT_LEFT_UP, self.onEndSession)
        self.btn_end_s.Disable()
        posY += b_space
        wx.StaticText(self.panel, -1, label="Leave a note", pos=(posX+5,posY))
        posY += 20
        self.txt_notes = wx.TextCtrl(self.panel, -1, pos=(posX+5,posY), size=(120,-1), style=wx.TE_PROCESS_ENTER)
        self.txt_notes.Bind(wx.EVT_TEXT_ENTER, self.onEnterInTextCtrl)
        posY += b_space + 10
        self.btn_quit = wx.Button(self.panel, -1, label='QUIT', pos=(posX,posY), size=(120, -1))
        self.btn_quit.Bind(wx.EVT_LEFT_UP, self.onClose)
        
        posX = 140
        self.lb_stimuli = wx.ListBox(self.panel, -1, 
                                     pos=(posX, 10), 
                                     size=(150, self.w_size[1]-85), 
                                     choices=['Stimuli file list'], 
                                     style=wx.LB_EXTENDED|wx.LB_HSCROLL|wx.LB_NEEDED_SB)
        self.lb_stimuli.SetBackgroundColour('#999999')
        _lb_stimuli_btn_names = ['randomize', 'minus', 'up', 'down']
        self.lb_stimuli_btns = {}
        posX = 145
        posY = self.w_size[1]-75
        self.sTxt_stim_cnt = wx.StaticText(self.panel, -1, label='-1/-1', pos=(posX, posY)) # played stimuli / total stimuli
        posX += self.sTxt_stim_cnt.GetSize()[0]
        for b_name in _lb_stimuli_btn_names:
            self.lb_stimuli_btns[b_name] = {}
            _fp = path.join(self.input_folder, 'btn_%s.png'%b_name)
            self.lb_stimuli_btns[b_name]["bmp"] = self.load_bmp( filePath=_fp, 
                                                                 size=(20,20) ) # normal bmp
            _fp = path.join(self.input_folder, 'btn_%s_mo.png'%b_name)
            self.lb_stimuli_btns[b_name]["bmp_mo"] = self.load_bmp( filePath=_fp, 
                                                                    size=(20,20) ) # bmp when mouse is over
            self.lb_stimuli_btns[b_name]["sbm"] = wx.StaticBitmap(self.panel, -1, 
                                                                  self.lb_stimuli_btns[b_name]["bmp"], 
                                                                  pos=(posX, posY), 
                                                                  size=(20,20), 
                                                                  name=b_name)
            posX += 25
            self.lb_stimuli_btns[b_name]["sbm"].Bind(wx.EVT_ENTER_WINDOW, self.onLBStimBtnEnter)
            self.lb_stimuli_btns[b_name]["sbm"].Bind(wx.EVT_LEAVE_WINDOW, self.onLBStimBtnLeave)
            self.lb_stimuli_btns[b_name]["sbm"].Bind(wx.EVT_LEFT_UP, self.onLBStimBtnClick)
            self.lb_stimuli_btns[b_name]["sbm"].Hide()

        posX = 300
        self.sTxt_pr_time = wx.StaticText(self.panel, -1, label='0:00:00', pos=(posX, 5)) # time since program starts
        _x = self.sTxt_pr_time.GetPosition()[0] + self.sTxt_pr_time.GetSize()[0] + 5
        wx.StaticText(self.panel, -1, label='since program started', pos=(_x, 5))
        self.font14 = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL)
        self.sTxt_pr_time.SetFont(self.font14)
        self.sTxt_pr_time.SetBackgroundColour('#000000')
        self.sTxt_pr_time.SetForegroundColour('#00FF00')

        self.sTxt_s_time = wx.StaticText(self.panel, -1, label='0:00:00', pos=(posX, 30)) # time since session starts
        _x = self.sTxt_s_time.GetPosition()[0] + self.sTxt_s_time.GetSize()[0] + 5
        wx.StaticText(self.panel, -1, label='since session started', pos=(_x, 30))
        self.font14 = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL)
        self.sTxt_s_time.SetFont(self.font14)
        self.sTxt_s_time.SetBackgroundColour('#000000')
        self.sTxt_s_time.SetForegroundColour('#CCCCFF')

        self.sTxt_time = wx.StaticText(self.panel, -1, label='0:00:00', pos=(posX, 55))
        _x = self.sTxt_time.GetPosition()[0] + self.sTxt_time.GetSize()[0] + 5
        wx.StaticText(self.panel, -1, label='since last stimulus', pos=(_x, 55))
        self.sTxt_time.SetFont(self.font14)
        self.sTxt_time.SetBackgroundColour('#000000')
        self.sTxt_time.SetForegroundColour('#FFFF00')
        self.txt_log = wx.TextCtrl(self.panel, -1, 
                                   pos=(posX, 80), 
                                   size=(self.w_size[0]-posX-5, self.w_size[1]-80), 
                                   value='', 
                                   style=wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        self.txt_log.SetBackgroundColour('#999999')
        statbar = wx.StatusBar(self, -1)
        self.SetStatusBar(statbar)

        ### keyboard binding
        quit_btnId = wx.NewId()
        whiteNoise_btnId = wx.NewId()
        playStim_btnId = wx.NewId()
        self.Bind(wx.EVT_MENU, self.onClose, id=quit_btnId)
        self.Bind(wx.EVT_MENU, self.onPlayWhiteNoise, id=whiteNoise_btnId)
        self.Bind(wx.EVT_MENU, self.onPlay, id=playStim_btnId)
        accel_tbl = wx.AcceleratorTable([ (wx.ACCEL_CTRL, ord('Q'), quit_btnId), 
                                          (wx.ACCEL_CTRL, ord('W'), whiteNoise_btnId), 
                                          (wx.ACCEL_CTRL, ord('P'), playStim_btnId) ])
        self.SetAcceleratorTable(accel_tbl)

        ### set timer for checking time after last stimulus play time
        self.tasp_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onTASPTimer, self.tasp_timer)
        self.tasp_timer.Start(1000)

        ### connect with Arduino
        arduino_scan_str = "/dev/cu.usbmodem*"
        self.arduino_name = ""

        for aConn in self.serial_scan(arduino_scan_str):
            self.arduino_name = aConn.name
            self.aConn = aConn
        if self.arduino_name != "": print str(self.arduino_name) + " connected."


        self.Bind( wx.EVT_CLOSE, self.onClose )
        self.program_start_time = time()
        self.session_start_time = -1

    # --------------------------------------------------

    def try_open(self, port):
    # function for Arduino-chip connection
        try:
            port = serial.Serial(port, 9600, timeout = 0)
        except serial.SerialException:
            return None
        else:
            return port

    # --------------------------------------------------

    def serial_scan(self, arduino_scan_str):
    # Try to connect to Arduino-chip
        for fn in glob(arduino_scan_str):
            port = self.try_open(fn)
            if port is not None:
                yield port

    # --------------------------------------------------

    def mc_signal_send(self, signal='1111'):
    # Function for sending a signal to ARDUINO
        if self.arduino_name != "": # If the ARDUINO-chip is connected
            ### Sending a signal to the Arduino-chip
            self.aConn.write(signal) # send a signal to Arduino
            sleep(0.1)
            #print self.aConn.readline() # print a message from Arduino
            self.aConn.flush() # flush the serial connection
            e_time = time() - self.session_start_time
            self.write_log( '%s, %.3f, %s signal was sent to Arduino.'%(get_time_stamp(), e_time, signal) )

    # --------------------------------------------------

    def load_bmp(self, filePath, size=(-1,-1)):
    # load an image specified with parameters
        tmp_null_log = wx.LogNull() # this is for not seeing the tif Library warning
        img = wx.Image(filePath, wx.BITMAP_TYPE_ANY)
        if size != (-1, -1): img = img.Rescale( size[0], size[1] )
        del tmp_null_log # delete the null-log to restore the logging
        bmp = img.ConvertToBitmap()
        return bmp

    # --------------------------------------------------

    def onToggleCam(self, event):
    # Turn On/Off webcam
        if self.Cam_inst == None:
            cam_idx = get_cam_idx()
            if cam_idx == []:
                self.show_msg_in_statbar("No usable webcams are attached.")
                return
            _pos = self.GetPosition()
            self.Cam_inst = Cam( self, cam_idx, (_pos[0]+self.w_size[0], _pos[1]) )
            self.Cam_inst.cam_th = Thread(target=self.Cam_inst.run)
            self.Cam_inst.cam_th.start()
            self.write_log('%s, camera process is started.'%get_time_stamp())
        else:
            self.Cam_inst.rc_q.put('quit', True, None)
            self.Cam_inst.cam_th.join()
            self.write_log('%s, camera process is finished.'%get_time_stamp())
            self.Cam_inst = None

    # --------------------------------------------------

    def onStartSession(self, event):
        if self.btn_session.IsEnabled() == False: return
        self.session_start_time = time()
        e_time = time() - self.session_start_time
        self.write_log( '%s, %.3f, Beginning of session-%i.'%(get_time_stamp(), e_time, self.si) )
        signal = '%.2i%.2i'%(self.day_of_expmt, self.si)
        self.mc_signal_send(signal) # send an arduino to turn on LED light briefly
        self.si += 1 # increase session index
        self.btn_dir.Enable()
        self.btn_end_s.Enable()
        self.btn_session.Disable()

    # --------------------------------------------------

    def onEndSession(self, event):
        if self.btn_end_s.IsEnabled() == False: return
        e_time = time() - self.session_start_time
        self.write_log( '%s, %.3f, End of session.'%(get_time_stamp(), e_time) )
        self.session_start_time = -1
        self.last_play_time = -1 # time when the last stimulus was play
        self.sTxt_time.SetLabel('0:00:00')
        self.sTxt_s_time.SetLabel('0:00:00')
        self.aspil = []
        self.update_lb_stimuli()
        self.btn_dir.Disable()
        self.btn_play.Disable()
        self.btn_end_s.Disable()
        self.btn_session.Enable()

    # --------------------------------------------------

    def onChooseDir(self, event):
        if self.btn_dir.IsEnabled() == False: return
        dlg = wx.DirDialog(self, "Choose a folder containing auditory stimuli.", CWD, wx.OPEN)
        dlgResult = dlg.ShowModal()
        dlg.Destroy()

        if dlgResult == wx.ID_OK:
            self.stim_path = dlg.GetPath()
            ### load sounds
            self.audStim = []
            self.audStim_l_snd = []
            for f in glob( path.join(self.stim_path, '*.wav' ) ):
                self.audStim.append(f)
                self.audStim_l_snd.append( wx.Sound(f) )
            self.aspil = range(len(self.audStim)) # auditory stimuli play index list
            self.pl_cnt = 0 # counter for the play list (aspil)
            self.sTxt_stim_cnt.SetLabel( '%i/%i'%(self.pl_cnt, len(self.aspil)) )
            self.update_lb_stimuli()
            for b_name in self.lb_stimuli_btns.iterkeys():
                self.lb_stimuli_btns[b_name]["sbm"].Show()
            self.btn_play.Enable()
            self.btn_dir.Disable()

    # --------------------------------------------------

    def update_lb_stimuli(self):
    # update the stimuli file list box
        _sfn = [] # file names only without path
        for idx in self.aspil: _sfn.append( path.basename(self.audStim[idx]) )
        self.lb_stimuli.Set(_sfn)

    # --------------------------------------------------

    def onLBStimBtnClick(self, event):
        if hasattr(self, 'aspil') == False: return
        if self.aspil == []: return
        obj_name = event.GetEventObject().GetName()
        if obj_name in ['up', 'down']:
            lbs_selections = list(self.lb_stimuli.GetSelections())
        if obj_name == 'randomize':
        # shuffle the stimuli list
            shuffle(self.aspil) 
        elif obj_name == 'minus':
        # get rid of selected items
            for rem_idx in self.lb_stimuli.GetSelections(): self.aspil[rem_idx] = None
            while None in self.aspil: self.aspil.remove(None)
            self.sTxt_stim_cnt.SetLabel( '0/%i'%(len(self.aspil)) )
        elif obj_name == 'up':
            for i in xrange(len(lbs_selections)):
                up_idx = lbs_selections[i]
                new_idx = max(0, up_idx-1)
                if not new_idx in lbs_selections:
                    self.aspil.insert(new_idx, self.aspil[up_idx])
                    self.aspil.pop(up_idx+1)
                    lbs_selections[i] = copy(new_idx)
        elif obj_name == 'down':
            for i in xrange(len(lbs_selections)-1, -1, -1):
                down_idx = lbs_selections[i]
                new_idx = min(len(self.aspil), down_idx+2)
                if not (down_idx+1) in lbs_selections:
                    self.aspil.insert(new_idx, self.aspil[down_idx])
                    self.aspil.pop(down_idx)
                    lbs_selections[i] = min(len(self.aspil)-1, lbs_selections[i]+1)
        self.update_lb_stimuli() # update the listbox
        if obj_name in ['up', 'down']:
            for i in lbs_selections: self.lb_stimuli.SetSelection(i)

    # --------------------------------------------------

    def onLBStimBtnEnter(self, event):
        ### change the bitmap of the button so that it looks different when the cursor is over it.
        obj_name = event.GetEventObject().GetName()
        self.lb_stimuli_btns[obj_name]["sbm"].SetBitmap(self.lb_stimuli_btns[obj_name]["bmp_mo"])

    # --------------------------------------------------

    def onLBStimBtnLeave(self, event):
        ### change back to the original bitmap
        obj_name = event.GetEventObject().GetName()
        self.lb_stimuli_btns[obj_name]["sbm"].SetBitmap(self.lb_stimuli_btns[obj_name]["bmp"])

    # --------------------------------------------------

    def onPlay(self, event):
    # play an auditory stimulus
        if self.btn_play.IsEnabled() == False: return
        if self.pl_cnt >= len(self.aspil): # played all the stimuli
            _s = self.lb_stimuli.GetSelections() # current selected items
            if len(_s) > 0:
                if self.lb_stimuli.GetString(_s[0]).startswith('[BAD]'): # if it was bad trial
                    _fn = self.lb_stimuli.GetString(_s[0]).replace('[BAD]','').replace('[played]','').strip()
                    _snd_idx = self.audStim.index( path.join(self.stim_path, _fn) )
                else:
                    self.lb_stimuli.SetSelection(-1, select=False)
                    return
            else:
                self.lb_stimuli.SetSelection(-1, select=False)
                return
        else:
            _snd_idx = self.aspil[self.pl_cnt]
        wav = wave.open(self.audStim[_snd_idx], "r")
	numFrames = wav.getnframes()
	sRate = float(wav.getframerate())
	soundlength = round(1000*numFrames/sRate) # length in msecs

        self.mc_signal_send() # signal for beginning of the stimulus
        self.btn_play.Enable(False) # disable play button
        wx.FutureCall(soundlength, self.btn_play.Enable, True) # enable the play button when the stimulus is ended
        wx.FutureCall(soundlength, self.mc_signal_send) # signal for when the stimulus is ended
        self.audStim_l_snd[_snd_idx].Play(wx.SOUND_ASYNC) # play the stimulus
        e_time = time() - self.session_start_time
        self.write_log( '%s, %.3f, Auditory stimulus starts, Sound-idx #%i, Sound-file %s'%(get_time_stamp(), e_time, _snd_idx, path.basename(self.audStim[_snd_idx])) )
        if self.pl_cnt < len(self.aspil):
            self.lb_stimuli.SetString( self.pl_cnt, '[played] '+self.lb_stimuli.GetString(self.pl_cnt) )
        if self.pl_cnt == 0: # as soon as the 1st stimulus is played
            for b_name in self.lb_stimuli_btns.iterkeys():
                self.lb_stimuli_btns[b_name]["sbm"].Hide() # hide the buttons for modifying stimuli list
        self.last_play_time = time()
        if self.pl_cnt < len(self.aspil):
            self.pl_cnt += 1
            self.sTxt_stim_cnt.SetLabel( '%i/%i'%(self.pl_cnt, len(self.aspil)) )
        self.lb_stimuli.SetSelection(-1, select=False)

    # --------------------------------------------------

    def onPlayWhiteNoise(self, event):
        '''
            play white noise via another speaker than the speaker for actual stimuli
            White noise (total 10 secdons)
            <fade-in 2 seconds, play-in-full-amplitude 6.5 seconds, fade-out 1.5 seconds>         
        '''
        if len(self.white_noise_output.ps_th) == 0: return # there's no opened output for white noise
        self.white_noise_output.play_sound(snd_idx=0, 
                                           stream_idx=0, 
                                           stop_prev_snd=True, 
                                           volume=self.white_noise_volume)
        self.write_log('%s, White noise begins'%(get_time_stamp()))
        ### set up color indicator of
        ### fading in & out (pink)
        ### and full volume playing (red)
        self.white_noise_panel.SetBackgroundColour( (250,100,100) )
        self.white_noise_panel.Refresh()
        wx.FutureCall( 2000, self.white_noise_panel.SetBackgroundColour, wx.RED )
        wx.FutureCall( 2000, self.white_noise_panel.Refresh )
        wx.FutureCall( 8500, self.white_noise_panel.SetBackgroundColour, (250,100,100) )
        wx.FutureCall( 8500, self.white_noise_panel.Refresh )
        wx.FutureCall( 10000, self.white_noise_panel.SetBackgroundColour, wx.WHITE )        
        wx.FutureCall( 10000, self.white_noise_panel.Refresh )

    # --------------------------------------------------

    def onWhiteNoisePanelClick(self, event):
        '''
            set the volume of white noise by clicking the white_noise_panel
        '''
        posY = event.GetPosition()[1]
        _p_sz = self.white_noise_panel.GetSize()
        ratio = (_p_sz[1]-float(posY)) / _p_sz[1]
        self.white_noise_volume = max(0.1, ratio * 2.0) # adjustable volume range will be 0.1 ~ 2.0
        self.white_noise_panel.Refresh()

    # --------------------------------------------------

    def onWhiteNoisePanelPaint(self, event):
        '''
            display the volume bar with the value of changed volume
        '''
        dc = wx.PaintDC(self.white_noise_panel)
        dc.Clear()
        dc.SetPen(wx.Pen(wx.BLACK, 1))
        _p_sz = self.white_noise_panel.GetSize()
        posY = _p_sz[1] - (self.white_noise_volume/2.0*_p_sz[1])
        dc.DrawLine(0, posY, _p_sz[0], posY)
        event.Skip()

    # --------------------------------------------------

    def onTASPTimer(self, event):
    # update time after the last stimulus play
        e_time = time() - self.program_start_time
        self.sTxt_pr_time.SetLabel( str(timedelta(seconds=e_time)).split('.')[0] )
        if self.session_start_time != -1:
            e_time = time() - self.session_start_time
            self.sTxt_s_time.SetLabel( str(timedelta(seconds=e_time)).split('.')[0] )
        if self.last_play_time != -1:
            e_time = time() - self.last_play_time
            self.sTxt_time.SetLabel( str(timedelta(seconds=e_time)).split('.')[0] )

    # --------------------------------------------------

    def onEnterInTextCtrl(self, event):
        value = self.txt_notes.GetValue()
        if 'bad' in value:
            if hasattr(self, 'lb_stimuli') == True:
                _items = self.lb_stimuli.GetSelections() # current selected items in the stimuli list
            else: # no stimuli list box yet
                return
            if len(_items) > 0: # item is selected
                _str = self.lb_stimuli.GetString(_items[0])
                if _str.strip().startswith('[played]') or _str.strip().startswith('[BAD]'):
                    self.write_log( '%s, %s'%(get_time_stamp(), value) )
                    self.show_msg_in_statbar("'%s' is written in the log."%value)
                else:
                    self.show_msg_in_statbar("Stimulus not played yet can't be marked as a bad trial.", 5000)
            else:
                self.show_msg_in_statbar("Please select stimulus to be marked as a bad trial.", 5000)
        else: # other contents than 'bad'
            self.write_log( '%s, %s'%(get_time_stamp(), value) )
            self.show_msg_in_statbar("'%s' is written in the log."%value)
        self.txt_notes.SetValue('')

    # --------------------------------------------------

    def onLBStimClick(self, event):
        pass
        #self.lb_stimuli.SetItemBackgroundColour(, )

    # --------------------------------------------------

    def show_msg_in_statbar(self, msg, time=5000):
        self.SetStatusText(msg)
        wx.FutureCall(time, self.SetStatusText, "") # delete it after a while

    # --------------------------------------------------

    def write_log(self, line):
        
        line += '\n\n'
        self.log += line
        writeFile(self.log_file_path, line) # write in the file

        if hasattr(self, 'txt_log') == True:
            self.txt_log.AppendText(line) # update log window
            if 'bad' in line.lower(): # if it was a bad trial
                ### mark it in txt_log and lb_stimuli
                _col = wx.Colour(200, 0, 0)
                _attr = wx.TextAttr(_col)
                _end = len(self.txt_log.GetValue())
                _start = max( 0, _end-len(line) )
                '''
                if self.pl_cnt >= len(self.aspil): # played all the stimuli
                    _items = self.lb_stimuli.GetSelections() # current selected items
                    if len(_items) == 0: return
                    else: _row = _items[0] 
                else:
                    _row = self.pl_cnt - 1
                '''
                _row = self.lb_stimuli.GetSelections()[0]
                self.txt_log.SetStyle(_start, _end, _attr) # change the color to red
                if 0 <= _row <= len(self.aspil):
                    ### update the stimuli list box
                    self.lb_stimuli.SetString( _row, '[BAD] '+self.lb_stimuli.GetString(_row) )
                    self.lb_stimuli.Refresh()

    # --------------------------------------------------

    def onClose(self, event):
        if self.Cam_inst != None:
            ### close cam
            self.Cam_inst.rc_q.put('quit', True, None)
            self.Cam_inst.cam_th.join()
            self.write_log('%s, camera process is closed.\n'%get_time_stamp())
        self.white_noise_output.close_output_streams()
        self.write_log('%s, End of the program.\n'%get_time_stamp())
        self.Destroy()

# ======================================================

class E_App(wx.App):
    def OnInit(self):
        self.frame = Experiment()
        self.frame.Show()
        self.SetTopWindow(self.frame)
        return True

# ======================================================

if __name__ == '__main__':
    if len(argv) > 1:
        if argv[1] == '-w': GNU_notice(1)
        elif argv[1] == '-c': GNU_notice(2)
    else:
        GNU_notice(0)
        debug = False
        ### determine current working directory
        CWD = getcwd()
        IN_APP = False
        ### adjust CWD if a packaged app is running
        parent_dir = path.split(CWD)[0]
        info_plist_path = path.join(parent_dir, 'Info.plist')
        if path.isfile(info_plist_path):
            plist_data = plistlib.readPlist(info_plist_path)
            if plist_data["CFBundleDisplayName"] == 'm_run_expmt':
                IN_APP = True
                _tmp = CWD.split('/')
                CWD = '/'
                for i in range(len(_tmp)-3): CWD = path.join(CWD, _tmp[i])
        app = E_App(redirect = False)
        app.MainLoop()
