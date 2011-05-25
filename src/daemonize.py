# File: daemonize.py
# Description: 'Daemonizes' a process,
#   so it can run as a standard Unix daemon.
#   Simply subclass Daemon and implement the run method
# License: Modified from code in the public domain.  
#   Originally by Sander Marechal (www.jejik.com)

import sys, os, time, atexist
from signal import SIGTERM

class Daemon:
    
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    # uses the 'double-forking' technique in order to 
    # properly release control of the terminal it was run from
    def daemonize(self):
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0) # first parent exits
        except OSError, e:
            sys.stderr.write("fork failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # second fork
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0) # second parent exits
        except OSError, e:
            sys.stderr.write("fork failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)
            
        # redirect file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile, 'w+').write("%s\n", % pid)

    def delpid(self):
        os.remove(self.pidfile)

    # start a new daemon
    def start(self):
        # check for a pidfile
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            sys.stderr.write("Pidfile %s already exists.\n" % self.pidfile)
            sys.exit(1)

        # daemonize it
        self.daemonize()
        self.run()

    # stop the daemon 
    def stop(self):
        # get the pidfile
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            sys.stderr.write("Pidfile %s does not exist\n" % self.pidfile)
            return

        # kill the daemon process
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
                else:
                    print str(err)
                    sys.exit(1)

    # restart the daemon process
    def restart(self):
        self.stop()
        self.start()

    # must be overridden in the subclass
    def run(self):
        pass
