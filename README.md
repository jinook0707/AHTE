# Marmoset_headturn_experiment

This set of codes were developed and used in a head turning experiment of marmoset monkeys in 2014.
An MP4 movie and a log file from an exepriment session were proprocessed first, then automatically measured the head direction of each video frame with computer vision algorithms, using openCV library. These processed data could be quickly revised with a revision program.

All the software are under the GNU GPL v3 license.

Developing the software for the exerpiment was supported by ERC Advanced Grant SOMACCA # 230604. 

---
Video analysis procedure

Required files: Session video file (MP4) and corresponding LOG file (from expmt/m_run_expmt.py)

1. Run m_chk_ss.py

 This is for calculating the exact time of session start via checking LED color. (head turning experiment of common marmoset monkeys)

 There will be 4 squares in a frame when a movie file was opened.

  1) These 4 squares should be clicked and dragged to where 4 LED light bulbs are so that these squares become bounding rects for each 4 LEDs.

  2) "Base ZM of LEDs" buttons should be clicked to store the zeroth moment of each rect in the first frame.

  3) Press Spabebar key.

   The script will go through each frame until it detects any LED light is turned on.
   The time delay will be written in a popup window.
   This information should be written in the corresponding log file.
   ( e.g.: \# In the recorded movie, LED was on at 21.24 seconds. Thus, 21.356 seconds have to be added to the time after session-start in this log file to get the time in the movie.

2. Run m_extract_frames.py

 This script is for extracting JPG images of -5 ~ +5 second around the onset of stimulus play.

  1) This script should be called with two arguments; the 1st argument is LOG file path and the 2nd argument is MP4 file path.

   If MP4 file has the proper name (format: Group-name_Individual-name), this script will generate directory named as following, \[Group\]\_\[Individual-name\]\_\[Trial\#\]\_\[Stimulus\]\_\[Stim.numbering\], and extract relevant frame image (JPG) into the directory.

 How it works :
 LOG file has the information when the stimulus was played during a session. But the session LOG recording itself started some time after the movie recording started. With the aforementioned information (21.356 seconds from the above example. This time is obtained from running the script, 'm_chk_ss.py'), this script calculates the time when the stimulus was played in the movie file, then it writes the calculated time in LOG, and generates a directory containing JPG images of -5 ~ +5 seconds around the onset of stimulus play. (It also crops the image to eliminate irrelevant surroundings.)

3. Run mva_surf.py

 This is for analyzing the video data and calculating the head direction.

 Requirements :
  * The current working directory should have 'results' directory, which has directories containing relevant extracted frames from session video MP4 file.
  * This directory name has information segmented by underbar, '\_'.
  \[Group\]\_\[Individual-name\]\_\[Trial\#\]\_\[Stimulus\]\_\[Stim.numbering\] (e.g.: G2_Kobold_01_BBBA_1)

  Template head image as named as with the group name and the individual's name. (e.g.: G2_Kobold_head.jpg)

 This script will search for directories containing extracted frame images and show the first frame of the first directory as it begins.

  1) There is a grey horizontal line denoting where the feeding hole is. It should be click-and-dragged to the bottom of the feeding hole, once at the beginning.

  2) Then spacebar should be pressed to start/stop video analysis.
 It will go through all the directories in 'results' directory, generating a result CSV file for each directory,  named as same as the directory.


