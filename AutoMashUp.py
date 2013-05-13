#!/usr/bin/env/python
# encoding: utf=8
'''
Created on Oct 15, 2012
@author: jordanhawkins
'''
import echonest.audio as audio
import echonest.modify as modify
import echonest.selection as selection
import echonest.action as action
import os
import plistlib
import shutil
import urllib
import numpy as numpy
import sys
import matplotlib.pyplot as pyplot
import skimage.feature as feature
import Main

programFiles = ['__init__.py','Main.py','AutoMashUp.py','cowbell0.wav', 'cowbell2.wav']
workingDirectory = '/Users/jordanhawkins/Documents/workspace/Automatic DJ/src/root/nested'
lib = plistlib.readPlist('/Users/jordanhawkins/Music/iTunes/iTunes Music Library.xml')
LOUDNESS_THRESH = -8 # per capsule_support module
TEMPLATE_WIDTH = 30
                   
def getAudioFiles():
    filenames = []
    for count in range(len(lib['Playlists'])):
        if lib['Playlists'][count]['Name'] == 'Automatic MashUp Input':
            playlistItems = lib['Playlists'][count]['Playlist Items']
            trackIDs = [i['Track ID'] for i in playlistItems]
            for i in range(len(trackIDs)):
                location = lib['Tracks'][str(trackIDs[i])]['Location']
                location = urllib.unquote(location)
                shutil.copy(location[16:], workingDirectory)
                filenames.append(location[16:])
            break
    return filenames

 
def equalize_tracks(tracks):   # copied from capsule_support module 
    def db_2_volume(loudness):
        return (1.0 - LOUDNESS_THRESH * (LOUDNESS_THRESH - loudness) / 100.0)  
    for track in tracks:
        loudness = track.analysis.loudness
        track.gain = db_2_volume(loudness)


def meanPitches(segments, beats): 
    """ 
    Returns a pitch vector that is the mean of the pitch vectors of any segments
    that overlap this AudioQuantum. 
    """ 
    pitches = []
    for beat in beats:
        temp_pitches = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        segs = segments.that(selection.are_contained_by(beat))
        if(len(segs) == 0): segs = segments.that(selection.start_during(beat))
        if(len(segs) == 0): segs = segments.that(selection.overlap(beat))
        for seg in segs:
            for index, pitch in enumerate(seg.pitches): 
                temp_pitches[index] = temp_pitches[index] + pitch 
        pitches.append([float(pitch / len(segs)) for pitch in temp_pitches])
    return pitches 

def meanTimbre(segments, beats): 
    """ 
    Returns a timbre vector that is the mean of the timbre vectors of any segments  
    that overlap this AudioQuantum. 
    """ 
    timbre = []
    for beat in beats:
        temp = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        segs = segments.that(selection.are_contained_by(beat))
        if(len(segs) == 0): segs = segments.that(selection.start_during(beat))
        if(len(segs) == 0): segs = segments.that(selection.overlap(beat))
        for seg in segs:
            for index, tim in enumerate(seg.pitches): 
                temp[index] = temp[index] + tim
        timbre.append([float(tim / len(segs)) for tim in temp])
    return timbre

def meanLoudness(segments, beats): 
    """ 
    Returns a loudness vector that is the mean of the loudness values of any segments  
    that overlap this AudioQuantum. 
    """ 
    loudness = []
    for beat in beats:
        segs = segments.that(selection.are_contained_by(beat))
        if(len(segs) == 0): segs = segments.that(selection.start_during(beat))
        if(len(segs) == 0): segs = segments.that(selection.overlap(beat))
        values = [seg.loudness_max for seg in segments.that(selection.are_contained_by
                                                            (beat))]
        loudness.append([sum(values)/len(segs)]*6)
    return loudness

    """
    Get the beats that comprise a specific section of a song. 
    """
def getSectBeats(section):
    beats = []
    bars = section.children()
    for bar in bars:
        for beat in bar.children():
            beats.append(beat)
    return beats
    
def matchTempoAndKey(localAudioFiles, tempos, keys):
    keys[2] = keys[0]
    keys[4] = keys[0]
    keys[3] = keys[1]
    tempos[2] = tempos[0]
    tempos[4] = tempos[0]
    tempos[3] = tempos[1]
    print "tempos: ", tempos
    midTempo = (max(tempos) + min(tempos))/2.0
    print "midTempo: ", midTempo
    midTempo = round(midTempo)
    print "rounded midTempo: ", midTempo
    mod = modify.Modify()
    out = [mod.shiftTempo(laf, midTempo/tempo) for laf,tempo in 
           zip(localAudioFiles,tempos)]
    if max(keys)-min(keys) > 6:
        midKey = (((12 - max(keys) + min(keys))/2) + max(keys)) % 12 #12 chroma values...
    else:
        midKey = (max(keys) + min(keys))/2
    for i in range(len(out)):
        if(abs(midKey-keys[i])>3):
            out[i] = mod.shiftPitchSemiTones(out[i],midKey-keys[i]+12)
        else:
            out[i] = mod.shiftPitchSemiTones(out[i],midKey-keys[i])
    print "filename of first in group of 5: ", localAudioFiles[0].filename
    print "midKey: ", midKey
    for i in range(len(out)): out[i].encode(str(i) + '.mp3')
    return [audio.LocalAudioFile(str(i) + '.mp3') for i in range(5)]
    
""" Determines the best matching section of two songs. The variables x,y mark this
    location as the middle of the template. From x,y the best-matched section
    and its mashed location can be derived as section = x/12 and starting_segment = y."""    
def mashComponents(localAudioFiles, loudnessMarkers):
    instSegments = localAudioFiles[0].analysis.segments# This is the base track
    vocalSegments = localAudioFiles[1].analysis.segments# This is the overlay track
    instBeats = localAudioFiles[0].analysis.beats[loudnessMarkers[0][0]:
                                                  loudnessMarkers[0][1]]
    vocalBeats = localAudioFiles[1].analysis.beats[loudnessMarkers[1][0]:
                                                   loudnessMarkers[1][1]]
    pitches = meanPitches(instSegments,instBeats)
    timbre = meanTimbre(instSegments,instBeats)
    sections = localAudioFiles[1].analysis.sections #This is the new lead vocal layer
    sections = sections.that(selection.are_contained_by_range(
            vocalBeats[0].start, vocalBeats[-1].start+vocalBeats[-1].duration))
    if(len(sections)==0):sections = localAudioFiles[1].analysis.sections[2:-2]
    pyplot.figure(0,(16,9))
    image = numpy.array(pitches)
    image = numpy.concatenate((image,numpy.array(timbre)),axis = 1)
    image = numpy.concatenate((image,numpy.array(meanLoudness(instSegments,instBeats))),
                              axis = 1)
    """ Now image contains chromatic, timbral, and loudness information"""
    sectBeats = getSectBeats(sections[0]) # get beats that comprise a specific section
    template = numpy.array(meanPitches(vocalSegments,sectBeats))
    template = numpy.concatenate((template,numpy.array(
                                meanTimbre(vocalSegments,sectBeats))),axis=1)
    template = numpy.concatenate((template,numpy.array(
                                meanLoudness(vocalSegments,sectBeats))),axis = 1)
    im = feature.match_template(image,template,pad_input=True)
    maxValues = [] #tuples of x coord, y coord, correlation, and section len(in secs)
    ij = numpy.unravel_index(numpy.argmax(im), im.shape)
    x, y = ij[::-1]
    maxValues.append((numpy.argmax(im),x,y,sections[0].duration))
    for i in range(len(sections)-1):
        sectBeats = getSectBeats(sections[i+1])
        template = numpy.array(meanPitches(vocalSegments,sectBeats))
        template = numpy.concatenate((template,numpy.array(
                                meanTimbre(vocalSegments,sectBeats))), axis=1)
        template = numpy.concatenate((template,numpy.array(
                                meanLoudness(vocalSegments,sectBeats))),axis = 1)
        match = feature.match_template(image,template,pad_input=True)
        ij = numpy.unravel_index(numpy.argmax(match), match.shape)
        x, y = ij[::-1]
        maxValues.append((numpy.argmax(match),
                          TEMPLATE_WIDTH*i+x,y,sections[i+1].duration))
        im = numpy.concatenate((im,match),axis = 1)
    maxValues.sort()
    maxValues.reverse()
    try:
        count = 0
        while(maxValues[count][3] < 10.0): # choose a section longer than 10 secs
            count += 1
        x = maxValues[count][1]
        y = maxValues[count][2]
    except:        
        print "exception in mashComponents..."
        ij = numpy.unravel_index(numpy.argmax(im), im.shape)
        x, y = ij[::-1]
    pyplot.imshow(im, cmap = pyplot.get_cmap('gray'), aspect = 'auto')
    pyplot.plot(x,y,'o',markeredgecolor='r',markerfacecolor='none',markersize=15)
    pyplot.show()
    sectionBeats = getSectBeats(sections[x/TEMPLATE_WIDTH])
    print "len(sectionBeats): ", len(sectionBeats)
    print "len(instBeats): ", len(instBeats)
    print "y: ", y
    y = instBeats[y].absolute_context()[0]
    instBeats = localAudioFiles[0].analysis.beats 
    matchingBeats = instBeats[(y-len(sectionBeats)/2):(y+len(sectionBeats)/2)]
    print"len(matchingBeats): ", len(matchingBeats)
    matchingBeats = matchingBeats[-len(sectionBeats):]
    print"len(matchingBeats): ", len(matchingBeats)
    """ Check to make sure lengths of beat lists are equal... """
    if len(matchingBeats) != len(sectionBeats):
        print "len(matchingBeats) != len(sectionBeats). For now, I will just truncate..."
        print "len(matchingBeats): ", len(matchingBeats)
        print "len(sectionBeats): ", len(sectionBeats)
        if len(matchingBeats) > len(sectionBeats):matchingBeats = matchingBeats[
                                                            :len(sectionBeats)]
        else: sectionBeats = sectionBeats[:len(matchingBeats)]
    """ I have to make sure sectionBeats and matchingBeats are similarly aligned
        within their group, aka bar of four beats. I will add a beat to the beginning
        of matchingBeats until that condition is met. I re-initialize instBeats and
        vocalBeats, because now I want to include the areas outside of those marked
        off by AutomaticDJ for fade ins and fade outs."""
    vocalBeats = localAudioFiles[1].analysis.beats
    while(matchingBeats[0].local_context()[0] != sectionBeats[0].local_context()[0]):
        matchingBeats.insert(0,instBeats[matchingBeats[0].absolute_context()[0]-1])
        sectionBeats.append(vocalBeats[sectionBeats[-1].absolute_context()[0]+1])
    """ Check to make sure lengths of beat lists are equal... """
    if len(matchingBeats) != len(sectionBeats):
        print "len(matchingBeats) != len(sectionBeats) at the second checkpoint."
        print "This should not be the case. The while loop must not be adding beats"
        print "to both lists equally."
        print "len(matchingBeats): ", len(matchingBeats)
        print "len(sectionBeats): ", len(sectionBeats)
        sys.exit()
    """ Next, I will use the beats around the designated beats above to transition into
    and out of the mashup. """
    XLEN = 4 # number of beats in crossmatch
    if(matchingBeats[0].absolute_context()[0] < XLEN or
       len(instBeats) - matchingBeats[-1].absolute_context()[0] - 1 < XLEN or
       sectionBeats[0].absolute_context()[0] < XLEN or
       len(vocalBeats) - sectionBeats[-1].absolute_context()[0] - 1 < XLEN):
        XLEN -= 1
    BUFFERLEN = 12 # number of beats before and after crossmatches
    while(matchingBeats[0].absolute_context()[0] < BUFFERLEN+XLEN or
       len(instBeats) - matchingBeats[-1].absolute_context()[0] - 1 < BUFFERLEN+XLEN or
       sectionBeats[0].absolute_context()[0] < BUFFERLEN+XLEN or
       len(vocalBeats) - sectionBeats[-1].absolute_context()[0] - 1 < BUFFERLEN+XLEN):
        BUFFERLEN -= 1
    try:
        """ These are the 4 beats before matchingBeats. These are the four beats of the
        instrumental track that preclude the mashed section. """
        b4beatsI = instBeats[matchingBeats[0].absolute_context()[0]-XLEN:
                            matchingBeats[0].absolute_context()[0]]
        """ These are the 4 beats after matchingBeats. These are the four beats of the
        instrumental track that follow the mashed section. """
        afterbeatsI = instBeats[matchingBeats[-1].absolute_context()[0]+1:
                            matchingBeats[-1].absolute_context()[0]+1+XLEN]
        if(len(b4beatsI) != len(afterbeatsI)):
            print "The lengths of b4beatsI and afterbeatsI are not equal."
        """ These are the 16 beats before the 4-beat crossmatch into matchingBeats. """
        preBufferBeats = instBeats[matchingBeats[0].absolute_context()[0]-BUFFERLEN-XLEN:
                                            matchingBeats[0].absolute_context()[0]-XLEN]
        """ These are the 16 beats before the 4-beat crossmatch into matchingBeats. """
        postBufferBeats = instBeats[matchingBeats[-1].absolute_context()[0]+1+XLEN:
                                matchingBeats[-1].absolute_context()[0]+1+XLEN+BUFFERLEN]
        if(len(preBufferBeats) != len(postBufferBeats)):
            print "The lengths of preBufferBeats and postBufferBeats are not equal."
            print "len(preBufferBeats): ", len(preBufferBeats)
            print "len(postBufferBeats): ", len(postBufferBeats)
            print matchingBeats[-1].absolute_context()[0]
            print len(instBeats)
            sys.exit()
        """ These are the 4 beats before matchingBeats. These are the four beats of the
        new vocal track that preclude the mashed section. """
        b4beatsV = vocalBeats[sectionBeats[0].absolute_context()[0]-XLEN:
                            sectionBeats[0].absolute_context()[0]]
        """ These are the 4 beats after matchingBeats. These are the four beats of the 
        new vocal track that follow the mashed section. """
        afterbeatsV = vocalBeats[sectionBeats[-1].absolute_context()[0]+1:
                            sectionBeats[-1].absolute_context()[0]+1+XLEN]
        if(len(b4beatsV) != len(afterbeatsV)):
            print "The lengths of b4beatsI and afterbeatsI are not equal."
            sys.exit()
    except: 
        print "exception in 4 beat try block."
        sys.exit()
    """ vocData: An AudioData object for the new vocal data that will be overlaid. 
        instData: An AudioData object for the base instrumental track. 
        originalVocData: An AudioData object of the original vocal to accompany 
            the new one. 
        vocalMix: An AudioData of both vocal tracks mixed together, in order to 
            keep the overall vocal loudness approximately constant. 
        mix: An AudioData of the instrumental track and combined vocals
            mixed together. """
    vocData = audio.getpieces(localAudioFiles[3],b4beatsV+sectionBeats+afterbeatsV)
    instData = audio.getpieces(localAudioFiles[2],b4beatsI+matchingBeats+afterbeatsI)
    if instData.data.shape[0] >= vocData.data.shape[0]: 
        mix = audio.megamix([instData, vocData])
    else: 
        mix = audio.megamix([vocData, instData]) # the longer data set has to go first.
    mix.encode('mix.mp3')
    vocData.encode('vocData.mp3')
    """ Now, make a similar mix for before the mashed sections..."""
    instData = audio.getpieces(localAudioFiles[2], preBufferBeats + b4beatsI)
    vocData = audio.getpieces(localAudioFiles[4], preBufferBeats + b4beatsI)
    premix = audio.megamix([instData, vocData])
    """ ...and another mix for after the mashed sections."""
    instData = audio.getpieces(localAudioFiles[2], afterbeatsI + postBufferBeats)
    vocData = audio.getpieces(localAudioFiles[4], afterbeatsI + postBufferBeats)
    postmix = audio.megamix([instData, vocData])
    """ Now, I have three AudioData objects, mix, premix, and postmix, that overlap by
    four beats. I will build Crossmatch objects from the overlapping regions, and three 
    Playback objects for the areas that are not in transition. """
    action.make_stereo(premix)
    action.make_stereo(mix)
    action.make_stereo(postmix)
    preBuffdur = sum([p.duration for p in preBufferBeats]) # duration of preBufferBeats
    playback1 = action.Playback(premix,0.0,preBuffdur)
    b4dur = sum([p.duration for p in b4beatsI]) # duration of b4beatsI
    crossfade1 = action.Crossfade((premix,mix),(preBuffdur,0.0),b4dur) 
    abdur = sum([p.duration for p in afterbeatsI])
    playback2 = action.Playback(mix,b4dur,mix.duration - b4dur - abdur)
    crossfade2 = action.Crossfade((mix,postmix),(mix.duration - abdur,0.0),abdur) 
    playback3 = action.Playback(postmix,abdur,sum([p.duration for p in postBufferBeats]))
    action.render([playback1,crossfade1,playback2,crossfade2,playback3], 'mashup.mp3')
    
def checkBeats(lafs, tempos, filenames):
    beats = [l.analysis.beats for l in lafs]
    for i,t in enumerate(tempos):
        misAlignedBeats = 0
        misAlignedBars = 0
        beatDur = 60.0/round(t)
        for b in beats[i]:
            #Do the beats land on the on-beat?
            if(b.start % beatDur > beatDur/4):
                #print "mis-aligned beat.start at: ", b.start
                #print "b.absolute_context()[0]*beatDur: ", b.absolute_context()[0]*beatDur
                #print "b.start % beatDur: ", b.start % beatDur
                misAlignedBeats+=1
            #Does the 1 beat line up with the 1?
            if(b.local_context()[0] == 0 and b.start % 4*beatDur > beatDur/4): 
                misAlignedBars+=1
        print "filename: ", filenames[i]
        print "len(beats): ", len(beats[i])
        print "misAlignedBeats: ", float(misAlignedBeats)/float(len(beats[i]))
        print "misAlignedBars: ", float(misAlignedBars)/(float(len(beats[i]))/4)
        print "mean beat confidence: ", numpy.mean(beats[i].confidence)
        
def main():
    for filename in os.listdir(os.getcwd() + '/Output'): 
        if(filename[-4:] == '.mp3'): os.remove('Output/' + filename)
    localAudioFiles = []
    for filename in os.listdir(os.getcwd() + '/Input'):
        print filename
        if(filename != '.DS_Store' and filename != 'Thumb.db'):
            localAudioFiles.append(audio.LocalAudioFile('Input/' + filename))
    keys = [localAudioFiles[0].analysis.key['value'], localAudioFiles[1].
                analysis.key['value'], 0,0,0]
    for i,laf in enumerate(localAudioFiles[0:2]):
            if(laf.analysis.mode['value'] == 0): keys[i] = keys[i]+3
            if(keys[i] > 11): keys[i] = keys[i] - 12
    tempos = [localAudioFiles[0].analysis.tempo['value'], localAudioFiles[1].
                  analysis.tempo['value'], 0,0,0]
    localAudioFiles = matchTempoAndKey(localAudioFiles, tempos, keys)
    for i in range(3): localAudioFiles[i+2].encode(str(i)+'.mp3')
    print "tempos after match should equal midTempo: ", [laf.analysis.tempo['value']
                                                             for laf in localAudioFiles]
    equalize_tracks([localAudioFiles[0],localAudioFiles[1],localAudioFiles[2]])
    equalize_tracks([localAudioFiles[3],localAudioFiles[4]])
    print "len(localAudioFiles)/5 after match: ", len(localAudioFiles)/5
    loudnessMarkers = Main.findLoudestRegion([localAudioFiles[0].analysis.segments,
            localAudioFiles[1].analysis.segments],
            [localAudioFiles[0].analysis.tempo['value'],
            localAudioFiles[1].analysis.tempo['value']])
    beatMarkers = Main.getBeatMarkers(loudnessMarkers,
            [localAudioFiles[0].analysis.segments,
            localAudioFiles[1].analysis.segments],[localAudioFiles[0].analysis.beats,
            localAudioFiles[1].analysis.beats])
    mashComponents(localAudioFiles, beatMarkers)  
    
if __name__ == '__main__':
    main()
