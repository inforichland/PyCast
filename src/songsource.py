# File: songsource.py
# Description: A song source object for 
#   the PyCast Shoutcast server
# Copyright: (c) Tim Wawrzynczak, MMXI
# License: BSD 3-clause

import os
import fnmatch
import re

# ensure that you add any new classes to
# the song_source_classes dict at the bottom of this
# file so they can be used in argument parsing

class DefaultSongSource(object):
    """Calling nextSong() on this will return a
filename which the shoutcast server can use as the next file to play
to a client"""

    def __init__(self):
        self.defaultfile="/home/tim/Music/Music1/Camel - Supertwister.mp3"

    def nextSong(self):
        return self.defaultfile

class OsWalkSongSource(object):
    """Picks MP3 files in order (using os.walk) from a given directory as the song source."""

    # a generator function to return files in root which match pattern
    def all_files_by_pattern(self, pattern, root):
        """Find all files in 'root' which match 'pattern' (matched with fnmatch)"""
        for path, dirs, files in os.walk(os.path.abspath(root)):
            for filename in fnmatch.filter(files, pattern):
                yield os.path.join(path, filename)

    def __init__(self, dir):
        self.directory = dir
        if not os.path.exists(dir):
            self.files = None
            raise
        else:
            self.files = self.all_files_by_pattern('*.mp3', dir)

    # return the next song
    def nextSong(self):
        nextFile = self.files.next()
        if nextFile == None:
            self.files = self.all_files_by_pattern('*.mp3', dir)
            return self.files.next()
        else:
            return nextFile


# ensure you add any new classes here
# so you can use these in the argument parsing
song_source_classes = {'default':DefaultSongSource, 
                       'walk':OsWalkSongSource}
