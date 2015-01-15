'''
script file for 'm_revision.py'

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

from os import path, mkdir
from glob import glob
import wx
import numpy as np

# ======================================================

class MarmosetSubjectRevision(wx.Panel):
    def __init__(self, parent, size, cwd, output_dir):
        self.main_frame = parent.GetParent()
        wx.Panel.__init__(self, parent, size=size)
        self.SetBackgroundColour( wx.Colour(120,120,120) )
        self.w_size = size
        self.cwd = cwd
        self.output_dir = output_dir
        self.stimuli = self.main_frame.stimuli

        posX = 10
        posY = 10
        _btn = wx.Button(self, -1, 'Reload subjects', pos=(posX, posY), size=(120, -1))
        _btn.Bind(wx.EVT_LEFT_UP, self.onReloadSubjects)
        posX += _btn.GetSize()[0] + 10
        self.cb_subject = wx.ComboBox(self, -1, '', pos=(posX, posY), size=(150,-1), style=wx.CB_READONLY)
        self.cb_subject.Bind(wx.EVT_COMBOBOX, self.onSelectSubject)
        posX += self.cb_subject.GetSize()[0] + 50
        self.sTxt_subj = wx.StaticText( self, -1, pos = (posX, posY+5), label='Selected Subject : ' )
        posX = size[0]-170
        _btn = wx.Button(self, -1, 'Export CSV data', pos=(posX, posY), size=(150, -1))
        _btn.Bind(wx.EVT_LEFT_UP, self.onExportCSV)

        posX = 10
        posY += self.cb_subject.GetSize()[1] + 10
        self.lc_data = wx.ListCtrl(self, 
                                   -1, 
                                   pos=(posX,posY), 
                                   size=(self.w_size[0]-20, self.w_size[1]-posY-55), 
                                   style=wx.LC_REPORT)
        self.lc_cols = ['Group', 'Test', 'Stimulus', 'StimType', 'Mov_B', 'Mov_A', 'H_turn_B', 'H_turn_A', 'H_turn_idx', 'H_turn_dur']
        for i in xrange(len(self.lc_cols)):
            self.lc_data.InsertColumn(i, self.lc_cols[i])
            if self.lc_cols[i] in ['Stimulus', 'StimType']:
                self.lc_data.SetColumnWidth(i, 120)
        self.lc_data.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onLCDataItemSelected)
        self.onReloadSubjects(None)
        
    #------------------------------------------------

    def onReloadSubjects(self, event):
        s_list = [] # list for the names of the subjects
        for f in glob(path.join(self.output_dir, '*.csv')):
            fn = path.split(f)[1]
            _str = fn.split('_')
            if len(_str) != 5: continue
            s_name = _str[2] # name of the subject
            if not s_name in s_list: s_list.append(s_name)
        self.cb_subject.Clear()
        self.cb_subject.AppendItems(s_list)

    #------------------------------------------------

    def onSelectSubject(self, event):
        self.lc_data.DeleteAllItems()
        idx = self.cb_subject.GetSelection()
        s_name = self.cb_subject.GetString(idx)
        self.sTxt_subj.SetLabel( 'Selected Subject : %s'%s_name )
        data = self.calcSubject(s_name=s_name)
        for di in data.iterkeys():
            ### update the listCtrl
            self.lc_data.Append( [ data[di]['Group'], 
                                   data[di]['Test'], 
                                   data[di]['Stimulus'], 
                                   data[di]['StimType'], 
                                   data[di]['movB'], 
                                   data[di]['movA'], 
                                   data[di]['htB'], 
                                   data[di]['htA'], 
                                   data[di]['htIdx'], 
                                   data[di]['htDur'] ] )

    #------------------------------------------------

    def calcSubject(self, s_name):
        data = {}
        for f in glob(path.join(self.output_dir, '*.csv')): # for each trial data
            fn = path.split(f)[1]
            _str = fn.split('_')
            if not s_name in fn: continue
            if len(_str) < 5: continue
            _di = len(data) # data index = trial index
            data[_di] = {}
            data[_di]['Group'] = _str[0]
            #data[_di]['Name'] = _str[2]
            data[_di]['Test'] = _str[1]
            _stim = _str[3] + '_' + _str[4]
            data[_di]['Stimulus'] = _stim
            data[_di]['StimType'] = None
            for key in self.stimuli.iterkeys():
                for _s in self.stimuli[key]:
                    if _s == _stim.replace('.csv', ''):
                        data[_di]['StimType'] = key
                        break
                if data[_di]['StimType'] != None: break
            a_idx_B = [] # angle index
            angles_B = [] # angles before the onset of stimulus
            a_idx_A = [] # angle index
            angles_A = [] # angles after the onset of stimulus
            _f = open(f, 'r')
            lines = _f.readlines()
            _f.close()
            ### get angle data
            for line in lines:
                try: _first = int(line.strip()[0])
                except: continue
                items = [ item.strip() for item in line.split(',') ]
                _fi = int(items[0])
                _a = int(items[1])
                if _fi < 500:
                    a_idx_B.append( _fi )
                    angles_B.append( _a )
                else:
                    a_idx_A.append( _fi )
                    angles_A.append( _a )
            ### calculate summary of the trial
            data[_di]['movB'] = 0
            data[_di]['movA'] = 0
            data[_di]['htB'] = False
            data[_di]['htA'] = False
            data[_di]['htIdx'] = -1
            data[_di]['htDur'] = 0
            _ab = np.asarray( angles_B )
            _aa = np.asarray( angles_A )
            _diff = np.abs(np.diff(_ab))
            _big_idx = _diff > 270
            _diff[_big_idx] = 360 - _diff[_big_idx]
            # when the subject turned the head toward right, 
            # the difference could be quite big between two frames.
            # such as 5 -> 355; diff = 350
            # In these cases, diff should be 360 - difference_angle
            data[_di]['movB'] = np.sum( _diff )
            _diff = np.abs(np.diff(_aa))
            _big_idx = _diff > 270
            _diff[_big_idx] = 360 - _diff[_big_idx]
            data[_di]['movA'] = np.sum( _diff )
            if np.count_nonzero( _ab > 180 ) > 0: data[_di]['htB'] = True
            if np.count_nonzero( _aa > 180 ) > 0: data[_di]['htA'] = True
            _idx = np.where( _aa > 180 )
            if len(_idx[0]) > 0: 
                _idx = _idx[0][0]
                data[_di]['htIdx'] = a_idx_A[_idx]
            data[_di]['htDur'] = np.count_nonzero( _aa > 180 ) 
        return data

    #------------------------------------------------

    def onExportCSV(self, event):
        export_dir = path.join( self.output_dir, '_subject_output' )
        if path.isdir(export_dir) == False: mkdir(export_dir)
        _cnt = self.cb_subject.GetCount()
        _s_names = []
        for i in xrange(_cnt):
            _sn = self.cb_subject.GetString(i)
            _s_names.append(_sn)
            data = self.calcSubject(s_name=_sn)
            f = open( path.join(export_dir, _sn + '.csv'), 'w' )
            _line = ''
            for _col in self.lc_cols: _line += '%s, '%(_col)
            _line = _line.rstrip(', ') + '\n'
            f.write( _line )
            for di in data.iterkeys():
                _line = ''
                _line = '%s, %s, %s, %s, %s, %s, %s, %s, %s, %s\n'%( data[di]['Group'], 
                                                                     data[di]['Test'], 
                                                                     data[di]['Stimulus'], 
                                                                     data[di]['StimType'], 
                                                                     data[di]['movB'], 
                                                                     data[di]['movA'], 
                                                                     data[di]['htB'], 
                                                                     data[di]['htA'], 
                                                                     data[di]['htIdx'], 
                                                                     data[di]['htDur'] )
                f.write( _line )
            f.close()
        _msg = 'Subjects data are saved.\n\n'
        for _sn in _s_names: _msg += '%s, '%(_sn)
        _msg = _msg.rstrip(', ')
        self.main_frame.show_msg(_msg)

    #------------------------------------------------

    def onLCDataItemSelected(self, event):
        pass

if __name__ == "__main__":
    print "\nPlease run 'm_revision.py' file to run the revision software.\n"