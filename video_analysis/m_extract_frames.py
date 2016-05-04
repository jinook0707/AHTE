'''
This script should be called with two arguments; the 1st argument is 
LOG file path and the 2nd argument is MP4 file path.
This script is for extracting JPG images of -5 ~ +5 second around 
the onset of stimulus play.
(head turning experiment of common marmoset monkeys)

Requirements :
1) LOG file & corresponding MP4 file
2) LOG file should have the comment lines after the session start, 
looks like below.
------
# In the recorded movie, LED was on at 21.24 seconds.
# Thus, 21.356 seconds have to be added to the time after session-start in this log file 
# to get the time in the movie.
------

If MP4 file has the proper name (format: Group-name_Individual-name),
this script will generate directory named as following,
[Group]_[Individual-name]_[Trial#]_[Stimulus]_[Stim.numbering],
and extract relevant frame image (JPG) into the directory.

How it works :
LOG file has the information when the stimulus was played during a 
session. But the session LOG recording itself started some time after 
the movie recording started. With the aforementioned information 
(21.356 seconds from the above example. This time is obtained from 
running the script, 'm_chk_ss.py'), this script calculates the time 
when the stimulus was played in the movie file, then it writes the 
calculated time in LOG, and generates a directory containing JPG images 
of -5 ~ +5 seconds around the onset of stimulus play.
(It also crops the image to eliminate irrelevant surroundings.)

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

from os import path, mkdir, remove
from sys import argv
from subprocess import call

from common_funcs import GNU_notice

#------------------------------------------------

def main(log_path, movie_path):
    add_ts = -1
    mov_file_name = path.split(movie_path)[1].split('.')[0]
    trial_mov_cnt = 0
    f = open(log_path, 'r')
    orig_lines = f.readlines()
    f.close()
    f = open(log_path, 'w')
    for line in orig_lines:
        items = line.split(',')
        f.write(line)
        if 'seconds have to be added' in line:
            add_ts = float(line.split('seconds have to be added')[0].split(',')[1])
        if len(items) > 2 and items[2].strip().lower() == 'auditory stimulus starts':
            stim_fn = items[4].split(' ')[-1].replace('.wav','').strip()
            if add_ts == -1:
                print 'ERROR:: add_ts is -1'
                break
            _ts = float(items[1])
            _movie_ts = _ts + add_ts
            f.write('# %.3f\n'%_movie_ts)
            trial_mov_cnt += 1
            _trial_mov_folder_name = mov_file_name + "_%.2i_%s"%(trial_mov_cnt, stim_fn)
            ### Generate a tiral movie file 
            ### ( 10 seconds movie, -5 ~ +5 around the stimulus onset )
            _tmp_mov_name = _trial_mov_folder_name + '.mp4'
            mkdir(_trial_mov_folder_name)
            cmd = ['ffmpeg', 
                   '-r', '100', 
                   '-i', movie_path, 
                   '-vf', 'crop=640:540:320:100',
                   '-qscale:v', '3', 
                   '-ss', str(_movie_ts-5.27), 
                   '-t', '10', 
                   '-r', '100', 
                   path.join( _trial_mov_folder_name, 'f%06d.jpg' )]
            print 'Excuting %s'%cmd
            call(cmd)
    f.close()
            
#------------------------------------------------

if __name__ == '__main__':
    if len(argv) < 3: 
        if len(argv) == 2 and argv[1] == '-w': GNU_notice(1)
        elif len(argv) == 2 and argv[1] == '-c': GNU_notice(2)
        else:
            print '\nERROR:: Paths for log file and movie file have to be provided as arguments.\n'
    else:
        GNU_notice(0)
        log_path = argv[1]
        movie_path = argv[2]
        main(log_path, movie_path)
