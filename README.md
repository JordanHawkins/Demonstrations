Demonstrations
==============

This repository includes versions of AutomaticDJ and AutomaticMashUp more suited for distribution.

**** Automatic DJ ****

This program takes any input playlist and outputs a mixed playlist, similar to that of a disk jockey. 

Input: This program takes a playlist of audio files as input. 

Execution Summary: 
1. Analysis info is retrieved for all input songs.
2. Playlist is reordered in ascending order by tempo value.
3. Each song has its loudness data lowpass filtered, and then the longest and most consistently loud region is selected for the mix. This selection process aims to mimic the decision-making of a DJ in a high-energy dance venue.
4. The ends of the sections are Crossmatched to create beat-matched transitions between songs in the output playlist.
5. The output playlist is encoded.

Output: The program outputs a mixed, reordered version of the input playlist.

Usage: Place input audio files in the "Input" folder. Songs should be of 4/4 time for best results. Run with…

python Main.py

Ordered output will appear in the "Output" folder.

Current Development Status:

There are two important considerations that affect program performance. 
1. Is the program able to closely replicate the decision-making of a human disk jockey by choosing the best song sections?
2. Are the transitions between the songs smooth and seamless like those of a human disk jockey?

Although my decision-making algorithm can surely benefit by analyzing musical features other than dynamics, I am afraid that imperfect beat detection is limiting performance in both areas. Beat numbers (i.e. their local_context) are often erroneously assigned in Analysis objects, leading to awkward transitions between songs, or unreliable data about the song's musical structure. 


**** Automatic MashUp ****

This program combines components of two different songs into one new "mashup" song. This program is still in development, and produces less reliable results than Automatic DJ.

Input: Although this program mashes together two songs (Song1 and Song2), it does not automatically extract vocal and instrumental tracks, so they must be provided with the main tracks. Five songs must be ordered in the "Input" folder as follows:

1. Song1 main track
2. Song2 main track
3. Song1 instrumental track
4. Song2 vocal track
5. Song1 vocal track

Execution Summary: 
1. Analysis info is retrieved for all input songs.
2. Component tracks are modified to have matching key and tempo.
3. Tracks are processed using Automatic DJ section choosing methods.
4. Image processing is used to best match two sections of the two songs.
5. A short demonstration audio clip is encoded to the Output folder.

Output: The program outputs a short mashup clip to demonstrate program functionality.

Usage: Place input audio files in the "Input" folder. Songs should be of 4/4 time for best results. Run with…

python AutoMashUp.py

Resultant mashup will be placed in the "Output" folder.

Current Development Status:

Similar to the previous program, I must experiment with my decision making code further. The program's output, however, also relies on the accuracy of analysis data. Incorrect key estimations compromise the key matching code, and incorrect beat numbers make track overlaying and alignment very difficult. 
