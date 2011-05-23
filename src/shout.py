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

import logging
import asyncore
import socket
import array
import os
import sys

try:
    import songsource
except ImportError:
    print "Error importing songsource!  Without a song source, the shoutcast server doesn't won't have any files to play!"
    sys.exit(1)

# set up logging
logging.basicConfig(level=logging.DEBUG, format="%(created)-15s %(msecs)d %(levelname)8s %(thread)d %(name)s %(message)s")
log = logging.getLogger(__name__)

# constants
BACKLOG = 10
SIZE = 1024

# address we're listening on
interface='localhost'
port=8888

# shoutcast stuff
CHUNKSIZE=32*1024
CHUNKS_IN_BUFFER=32
MINIMUM_CHUNKS_IN_BUFFER=2
RESPONSE= ["ICY 200 OK\r\n",
     "icy-notice1: <BR>This stream requires",
     "icy-notice2: Python Shoutcast server<BR>\r\n",
     "icy-name: Python mix\r\n",
     "icy-genre: Jazz Classical Prog Rock\r\n",
     "icy-url: http://",interface,":",str(port),"\r\n",
     "content-type: audio/mpeg\r\n",
     "icy-pub: 1\r\n",
     "icy-metaint: ",str(CHUNKSIZE), "\r\n",
     "icy-br: 128\r\n\r\n"]

class ShoutHandler(asyncore.dispatcher):
    """ This class handles the interaction with a client"""

    def __init__(self, client_socket, client_address):
        self.songSource = songsource.DefaultSongSource() # get song source
        self.client_address = client_address # (address,port) tuple of client
        fileName = self.songSource.nextSong() # get the next song from the song source
        self.fd = open(fileName, 'rb') # open the next file
        self.data = array.array('B') # array to hold music data
        self.response = False # we haven't sent the initial response yet
        self.file_size = os.path.getsize(fileName) # file size
        self.chunks_in_buffer = 0 # there are no chunks in the buffer yet

        # initialize this dispatcher
        self.refill_buffer() # refill the song buffer
        asyncore.dispatcher.__init__(self, client_socket)
        log.debug("created handler; waiting for loop")

    # shouldn't really be reading from the client
    def readable(self):
        return False

    # Shoutcast servers should always be able to write data
    def writable(self):
        return True

    # really shouldn't be reading from the client
    def handle_read(self):
        data = self.recv(SIZE)
        if data:
            log.debug("got data from client")
        else:
            log.debug("got null data")

    # handle getting the next song from the song source
    def getNextSong(self):
        fileName=self.songSource.nextSong() # get next song filename
        self.fd = open(fileName, 'rb')
        self.file_size = os.path.getsize(fileName)
        self.refill_buffer()

    # refill the buffer
    def refill_buffer(self):
        try:
            for i in range(0, CHUNKS_IN_BUFFER):
                self.data.fromfile(self.fd, CHUNKSIZE)
                self.data.append(0)
                self.chunks_in_buffer += 1
        except EOFError:
            self.fd.close()
            self.getNextSong()            

    # writing to the file
    def handle_write(self):
        # send the initial response
        if self.response == False:
            for i in RESPONSE:
                self.send(i)
            self.response = True
        # send audio data
        else:
            log.debug("writing to client")
            if self.chunks_in_buffer < MINIMUM_CHUNKS_IN_BUFFER:
                self.refill_buffer()                
            self.send(self.data[0:CHUNKSIZE + 1])
            # get rid of the chunk we just sent
            self.data = self.data[CHUNKSIZE + 1:]
            self.chunks_in_buffer -= 1

  
    # closing connection
    def handle_close(self):
        self.fd.close()
        log.info("conn_closed: client_address=%s:%s" % \
                     (self.client_address[0],
                      self.client_address[1]))
        self.close()

class ShoutServer(asyncore.dispatcher):
    """This server uses ShoutHandler's to send Shoutcast data
to clients."""

    allow_reuse_address = True
    request_queue_size = 5
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM

    # initialize the server
    def __init__(self, address, clientHandler=ShoutHandler):
        self.address = address
        self.clientHandler = clientHandler

        asyncore.dispatcher.__init__(self)
        self.create_socket(self.address_family,
                           self.socket_type)

        if self.allow_reuse_address:
            self.set_reuse_addr()

        self.server_bind()
        self.server_activate()

    # bind to address / port
    def server_bind(self):
        self.bind(self.address)
        log.debug("bind: address=%s:%s" % (self.address[0], self.address[1]))

    # start listening for clients
    def server_activate(self):
        self.listen(self.request_queue_size)
        log.debug("listen: backlog=%d" % self.request_queue_size)

    # return our socket's file descriptor
    def fileno(self):
        return self.socket.fileno()

    # start serving requests
    def serve(self):
        asyncore.loop()

    # handle a new client
    def handle_accept(self):
        conn_socket, client_address = self.accept()
        if self.verify_request(conn_socket, client_address):
            self.process_request(conn_socket, client_address)

    # all requests are valid
    def verify_request(self, conn_sock, client_address):
        return True

    # start serving the file to the new client
    def process_request(self, conn_socket, client_address):
        log.info("conn_made: client_address=%s:%s" % \
                     (client_address[0],
                      client_address[1]))
        self.clientHandler(conn_socket, client_address)

    # close the dispatcher when we're requested to close
    def handle_close(self):
        self.close()

# if we're run as a script, then just run the server
if __name__ == '__main__':
    try:
        server = ShoutServer((interface,port))
        server.serve()
    except KeyboardInterrupt:
        print "\nGoodbye!"
