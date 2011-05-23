# File: songsource.py
# Description: A song source object for 
#   the PyCast Shoutcast server
# Copyright: (c) Tim Wawrzynczak, MMXI
# License: BSD 3-clause

class DefaultSongSource(object):
    """Calling nextSong() on this will return a
filename which the shoutcast server can use as the next file to play
to a client"""

    def __init__(self):
        self.defaultfile="/home/tim/Music/Music1/Camel - Supertwister.mp3"

    def nextSong(self):
        return self.defaultfile
