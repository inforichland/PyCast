# File: shout.py
# Description: A Python shoutcast server
#    Just run as 'python shout.py'
#    Feel free to change the port the server listens on
#      and/or the song source
#    The server uses asynchronous I/O in order to
#      be able to serve many clients at once
#      quickly and without the overhead of threads
# Copyright: (c) Tim Wawrzynczak, MMXI
# License: BSD 3-clause

# http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/

import logging
import asyncore
import socket
import array
import os
import sys
import re
import id3reader # available from pip
import ConfigParser

try:
    import songsource
except ImportError:
    print "Error importing songsource!  Without a song source, the shoutcast server doesn't won't have any files to play!"
    sys.exit(1)

# set up logging
logging.basicConfig(level = logging.DEBUG, format = "%(created)-15s %(levelname)8s %(thread)d %(name)s %(message)s")
log = logging.getLogger(__name__)

# constants
BACKLOG = 10
SIZE = 1024

# address we're listening on
server_address = 'localhost'
server_port = 8888

# shoutcast / buffer constants
CHUNKSIZE = 32*1024
CHUNKS_IN_BUFFER = 32
MINIMUM_BYTES_IN_BUFFER = 2*CHUNKSIZE
RESPONSE = ["ICY 200 OK\r\n",
     "icy-notice1: <BR>This stream requires",
     "icy-notice2: Winamp, or another streaming media player<BR>\r\n",
     "icy-name: Python mix\r\n",
     "icy-genre: Jazz Classical Rock\r\n",
     "icy-url: http://", server_address, ":", str(server_port), "\r\n",
     "content-type: audio/mpeg\r\n",
     "icy-pub: 1\r\n",
     "icy-metaint: ", str(CHUNKSIZE), "\r\n",
     "icy-br: 128\r\n\r\n"]

class ShoutHandler(asyncore.dispatcher):
    """ This class handles the interaction with a client"""

    def __init__(self, client_socket, client_address):
        #self.songSource = songsource.DefaultSongSource
        self.songSource = songsource.OsWalkSongSource("/home/tim/Music/") # get song source
        self.client_address = client_address # (address,port) tuple of client
        fileName = self.songSource.nextSong() # get the next song from the song source
        self.data = array.array('B') # array to hold music data
        self.response = False # we haven't sent the initial response yet
        self.wants_metadata = False # assume they don't want metadata
        self.metadata_re = re.compile(r"Icy-MetaData", re.I)
        self.bytes_to_metadata = CHUNKSIZE # how many bytes are left until we need to send metadata

        # initialize this dispatcher
        self.getNextSong()
        asyncore.dispatcher.__init__(self, client_socket)

    # normally shouldn't really be reading much from the client.
    # should be just once at the beginning (the request/headers),
    #   and then once at the end when they disconnect (I believe this is for 
    #   clients that send connection:close in the headers
    def readable(self):
        return True

    # Shoutcast servers should always be able to write data
    def writable(self):
        return True

    # really shouldn't be reading from the client
    def handle_read(self):
        data = self.recv(SIZE)
        if data:
            if self.metadata_re.search(data):
                self.wants_metadata = True
                log.debug("Client wants metadata")
        else:
            log.debug("got null data")

    # create the metadata string
    def make_metadata(self):
        text = "StreamTitle='%s';"
        if self.id3:
            text = text % self.id3.getValue('title')
        else:
            text = text % ''
        blocks = len(text) // 16 + 1
        metadata = chr(blocks) + text
        metadata = metadata.ljust(blocks * 16 + 1, chr(0)) # add 1 to include the data length byte
        return metadata.encode('ascii')

    # handle getting the next song from the song source
    def getNextSong(self):
        try:
            fileName = self.songSource.nextSong() # get next song filename
            self.fd = open(fileName, 'rb')
            self.file_size = os.path.getsize(fileName)
            # if there is valid ID3 data, read it out of the file first,
            # so we can skip sending it to the client
            try:
                self.id3 = id3reader.Reader(self.fd)
                if isinstance(self.id3.header.size, int) and self.id3.header.size < self.file_size: # read out the id3 data
                    self.fd.seek(self.id3.header.size+1, os.SEEK_SET)
                    log.debug("Reading %d bytes of ID3: %d", self.id3.header.size, self.fd.tell())
            except id3reader.Id3Error:
                self.id3 = None
            self.metadata = self.make_metadata()

        except StopIteration:
            fileName = None
            self.fd = None
        except IOError:
            self.fd = None
        log.debug("getting next song: %s", fileName)

    # refill the buffer
    def refill_buffer(self):
        try:
            if self.fd: # could be None
                for i in range(0, CHUNKS_IN_BUFFER):
                    self.data.fromfile(self.fd, CHUNKSIZE)
        except EOFError:
            self.fd.close()
            self.getNextSong()

    # writing to the client
    def handle_write(self):
        # send the initial response
        if self.response == False:
            for i in RESPONSE:
                self.send(i)
            self.response = True
        # send audio data
        else:
            # figure out how much data there is to send and send it
            data = self.data[0:self.bytes_to_metadata]
            data_len = len(data)
            self.bytes_to_metadata -= data_len
            self.send(data)
            
            # send metadata
            if self.bytes_to_metadata <= 0 and self.wants_metadata:
                self.bytes_to_metadata = CHUNKSIZE
                self.metadata = self.make_metadata()
                self.send(self.metadata)

            # get rid of the chunk we just sent - this means the buffer for a client shouldn't exceed 1M in size
            self.data = self.data[data_len:]
            if len(self.data) < MINIMUM_BYTES_IN_BUFFER:
                self.refill_buffer()

    # closing connection
    def handle_close(self):
        self.fd.close()
        log.info("lost client %s:%s" % (self.client_address[0], self.client_address[1]))
        self.close()

    # handle errors
    def handle_error(self):
        pass

class ShoutServer(asyncore.dispatcher):
    """This server uses ShoutHandler's to send Shoutcast data
to clients."""

    # initialize the server
    def __init__(self, address, clientHandler=ShoutHandler):
        self.address = address
        self.clientHandler = clientHandler

        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.server_bind()
        self.server_activate()

    # bind to address / port
    def server_bind(self):
        self.bind(self.address)
        log.debug("bind: %s:%s" % (self.address[0], self.address[1]))

    # start listening for clients
    def server_activate(self):
        self.listen(BACKLOG)
        log.debug("listen: %d" % BACKLOG)

    # start serving requests
    def serve(self):
        asyncore.loop()

    # handle a new client
    def handle_accept(self):
        client_socket, client_address = self.accept()
        self.process_request(client_socket, client_address)

    # start serving the file to the new client
    def process_request(self, client_socket, client_address):
        log.info("new client: %s:%s" % (client_address[0], client_address[1]))
        self.clientHandler(client_socket, client_address)

    # close the dispatcher when we're requested to close
    def handle_close(self):
        self.close()

    # return our socket's file descriptor
    def fileno(self):
        return self.socket.fileno()

# if we're run as a script, then just run the server
if __name__ == '__main__':
    try:
        config = ConfigParser.ConfigParser()
        config.read('shout.cfg')
        source = config.get('source', 'type')
        songSource = songsource.song_source_classes[source]
    except:
        print >>sys.stderr, "Invalid song source type in config file!"
    try:
        server = ShoutServer((server_address, server_port), songSource)
        server.serve()
    except KeyboardInterrupt:
        print "\nGoodbye!"
