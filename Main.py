#!/usr/bin/env python
# encoding: utf=8
'''
Created on Oct 15, 2012
@author: jordanhawkins
'''
import echonest.audio as audio
import echonest.action as action
import echonest.selection as selection
import os
import plistlib
import shutil
import urllib
import numpy.matlib as matlib
import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as pyplot

workingDirectory = '/Users/jordanhawkins/Documents/workspace/Automatic DJ/src/root/nested'
lib = plistlib.readPlist('/Users/jordanhawkins/Music/iTunes/iTunes Music Library.xml')
LOUDNESS_THRESH = -8 # per capsule_support module
MIX_LENGTH = 4 # defines the length, in beats, of fades between songs
  
"""
Copy audio files listed in the "Automatic DJ Input" iTunes playlist 
into the project directory.
"""                 
def getAudioFiles():
    for count in range(len(lib['Playlists'])):
        if lib['Playlists'][count]['Name'] == 'Automatic DJ Input':
            playlistItems = lib['Playlists'][count]['Playlist Items']
            trackIDs = [i['Track ID'] for i in playlistItems]
            for i in range(len(trackIDs)):
                location = lib['Tracks'][str(trackIDs[i])]['Location']
                location = urllib.unquote(location)
                try:
                    shutil.copy(location[16:], workingDirectory)
                except:
                    print "exception in getAudioFiles"
            break
    
"""
Find the longest consistently loud region of the song.
window is the approximate number of segments in a 16 beat span.
lpf is a 16-beat-long rectangular window convolved with the loudness 
values to smoothen them the while loop tries to find a loud region 
of the song that's at least 60 seconds long. If such a region cannot
be found the first time, the LOUDNESS_FLOOR value is increased to 
tolerate slightly softer loud regions for the sake of a longer 
song duration.
*To better understand the mathematics involved, note that loudness 
is measured in negative decibels, so a small negative number is 
louder than a large negative number.
"""
def findLoudestRegion(segments,tempos):
    segmentMarkers = []
    for segs,tempo in zip(segments,tempos):
        LOUDNESS_CEILING = .8
        LOUDNESS_FLOOR = 1.2
        window = int((16.0/tempo)*60.0/(matlib.mean(matlib.array(segs.durations))))
        lpf = np.convolve(segs.loudness_max,np.ones(window)/window)[window/2:-(window/2)]
        lpf[0:window/2] = lpf[window/2]
        lpf[-(window/2):] = lpf[-(window/2)]
        mean = matlib.mean(matlib.array(lpf))
        marker1 = 0
        finalMarkers = (0,0)
        foundFirstMarker = 0
        while((sum([s.duration for s in segs[finalMarkers[0]:finalMarkers[1]]]) < 60.0)
              and LOUDNESS_FLOOR < 2.0):
            for i,l in enumerate(lpf):
                if(foundFirstMarker):
                    if l < mean*LOUDNESS_FLOOR or i == len(lpf)-1:
                        foundFirstMarker = 0
                        if((i-marker1) > (finalMarkers[1]-finalMarkers[0])):
                            finalMarkers = (marker1,i)                         
                elif l > mean*LOUDNESS_CEILING: 
                    foundFirstMarker = 1
                    marker1 = i
            # adjust thresholds to allow for longer region to be chosen, if necessary
            LOUDNESS_FLOOR = LOUDNESS_FLOOR + .05
            LOUDNESS_CEILING = LOUDNESS_CEILING + .05
        segmentMarkers.append(finalMarkers)
    return segmentMarkers         
    
"""
This method was used during development to visualize the data.
timeMarkers contains a tuple of start and end values (in seconds) for each song in my training set.
"""            
def generateSegmentGraphs(segments, filenames, segmentMarkers, tempos):
    # training set timeMarkers = [(26.516,131.312),(4.746,172.450),(41.044,201.012),(82.312,175.997),(15.370,46.003),(122.042,213.469),(30.887,122.294),(0.000,272.304),(37.785,195.357),(15.230,195.357),(37.539,172.498),(67.721,157.716),(37.282,125.899),(147.876,325.127),(14.775,192.008),(213.437,298.800),(29.553,86.022),(238.297,294.371),(21.150,193.356),(41.625,138.350)]
    # validation set timeMarkers = [(4.0,141.0),(25.0,177.0),(17.0,188.0),(16.0,129.0),(17.0,177.0),(15.0,136.0),(87.0,149.0),(98.0,173.0),(106.0,212.0),(0.0,104.0)]
    timeMarkers = [(37,125)]
    myMarkers = [(j.index(min(j.that(selection.start_during_range(i[0], i[0]+1.0)))),j.index(min(j.that(selection.start_during_range(i[1], i[1]+10.0))))) for j,i in zip(segments,timeMarkers)]    
    for i in range(len(segments)):
        pyplot.figure(i,(16,9))
        windowLen3 = int((16.0/tempos[i])*60.0/(matlib.mean(matlib.array(segments[i].durations))))
        lpf3 = signal.lfilter(np.ones(windowLen3)/windowLen3,1,segments[i].loudness_max) + signal.lfilter(np.ones(windowLen3)/windowLen3,1,segments[i].loudness_max[::-1])[::-1]
        lpf3 = np.convolve(segments[i].loudness_max,np.ones(windowLen3)/windowLen3)[windowLen3/2:-(windowLen3/2)]
        lpf3[0:windowLen3/2] = lpf3[windowLen3/2]
        lpf3[-(windowLen3/2):] = lpf3[-(windowLen3/2)]
        pyplot.plot(lpf3)
        pyplot.xlabel('Segment Number')
        pyplot.ylabel('Loudness (dB)')
        #pyplot.vlines(segmentMarkers[i][0], min(lpf3), max(segments[i].loudness_max), 'g')
        #pyplot.vlines(segmentMarkers[i][1], min(lpf3), max(segments[i].loudness_max), 'g')
        pyplot.vlines(myMarkers[i][0], min(lpf3), max(segments[i].loudness_max), 'r')
        pyplot.vlines(myMarkers[i][1], min(lpf3), max(segments[i].loudness_max), 'r')
        pyplot.legend(["Loudness", #"Autmatically selected start time: " + str(action.humanize_time(segments[i][segmentMarkers[i][0]].start)), 
                            #"Automatically selected end time: " + str(action.humanize_time(segments[i][segmentMarkers[i][1]].start)),
                            "Manually selected start time: " + str(action.humanize_time(timeMarkers[i][0])),
                            "Manually selected end time: " + str(action.humanize_time(timeMarkers[i][1]))])
        pyplot.title(filenames[i])    
    pyplot.show()

"""
I copied this method from capsule_support. It equalizes the volume of the input tracks.
"""
def equalize_tracks(tracks):
    def db_2_volume(loudness):
        return (1.0 - LOUDNESS_THRESH * (LOUDNESS_THRESH - loudness) / 100.0)   
    for track in tracks:
        loudness = track.analysis.loudness
        track.gain = db_2_volume(loudness)
            
"""
This method generates 4-beat Crossmatch objects, then renders them attached 
to the end of Playback objects.
"""
def generateCrossmatch(localAudioFiles, beatMarkers, filenames, beats):
    actions = []
    for i in range(len(beatMarkers)-1): 
        cm = action.Crossmatch((localAudioFiles[i], localAudioFiles[i+1]), 
            ([(b.start, b.duration) for b in beats[i][beatMarkers[i][1] - 
            MIX_LENGTH:beatMarkers[i][1]]],[(b.start, b.duration) 
            for b in beats[i+1][beatMarkers[i+1][0]:beatMarkers[i+1][0]+
            MIX_LENGTH]]))
        actions.append(cm)
    for i in range(len(beatMarkers)): 
        startBeat = beats[i][beatMarkers[i][0]+MIX_LENGTH]
        endBeat = beats[i][beatMarkers[i][1]-MIX_LENGTH]
        actions.insert(2*i, action.Playback(localAudioFiles[i], 
            startBeat.start, endBeat.start-startBeat.start))
    try:
        action.render([action.Fadein(localAudioFiles[0],beats[0]
            [beatMarkers[0][0]].start,beats[0][beatMarkers[0][0]+MIX_LENGTH].
            start-beats[0][beatMarkers[0][0]].start)],"000 fade in")
    except: print() # boundary error, so no fade-in will be generated for this playlist
    for i in range(len(actions)/2):
        index = str(i+1)
        while(len(index) < 3): index = "0" + index
        try:
            action.render([actions[2*i],actions[2*i+1]], index)
        except: print filenames[i]                        
    index = str(len(filenames))
    while(len(index) < 3): index = "0" + index
    action.render([actions[-1]], index)
    try:
        action.render([action.Fadeout(localAudioFiles[-1],beats[-1][beatMarkers[-1][1]-
            MIX_LENGTH].start,beats[-1][beatMarkers[-1][1]].start-beats[-1]
            [beatMarkers[-1][1]-MIX_LENGTH].start)], "999 fade out")
    except: print() #boundary error, so omit fade-out from playlist
    action.render

"""
This method finds the closest beat to my designated segments for Crossmatching.
""" 
def getBeatMarkers(loudnessMarkers,segments,beats):
    return [(b.index(b.that(selection.overlap(segments[i][loudnessMarkers[i][0]]))[0]),
             b.index(b.that(selection.overlap(segments[i][loudnessMarkers[i][1]]))[0]))
            for i,b in enumerate(beats)]
                 
def main():
    for filename in os.listdir(os.getcwd() + '/Output'): 
        if(filename[-4:] == '.mp3'): os.remove('Output/' + filename)
    localAudioFiles = []
    for filename in os.listdir(os.getcwd() + '/Input'):
        if(filename != '.DS_Store' and filename != 'Thumb.db'): 
            localAudioFiles.append(audio.LocalAudioFile('Input/' + filename))
    sortList = [(laf.analysis.tempo['value'],laf) for laf in localAudioFiles]
    sortList.sort() # put analysis objects in ascending order by tempo
    localAudioFiles = [t[1] for t in sortList]
    equalize_tracks(localAudioFiles)
    segments = [laf.analysis.segments for laf in localAudioFiles]
    beats = [laf.analysis.beats for laf in localAudioFiles]
    tempos = [laf.analysis.tempo['value'] for laf in localAudioFiles]
    filenames = [laf.filename for laf in localAudioFiles]
    loudnessMarkers = findLoudestRegion(segments,tempos)
    beatMarkers = getBeatMarkers(loudnessMarkers,segments,beats)
    generateCrossmatch(localAudioFiles,beatMarkers,filenames,beats)    
    for filename in os.listdir(os.getcwd()): 
        if(filename[-4:] == '.mp3'): shutil.move(filename,'Output/' + filename) 
    
if __name__ == '__main__':
    main()
