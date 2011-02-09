# -*- coding: utf-8 -*-

import os, pyinotify, time

DEFAULT_HEARTBEAT = 600
DEBUG = False

class EventHandler(pyinotify.ProcessEvent):

    def __init__(self, monitor):
        super(EventHandler, self).__init__()
        self.monitor = monitor

    def process_IN_CREATE(self, event):
        if DEBUG:
            print "Creating %s" % event.pathname
        if os.path.isdir(event.pathname):
            self.monitor.register_dir(event.pathname)

        self.monitor.notify(event.pathname)

    def process_IN_DELETE(self, event):
        if DEBUG:
            print "Delete %s" % event.pathname
        self.monitor.notify(event.pathname)

    def process_IN_CLOSE_WRITE(self, event):
        if DEBUG:
            print "Modified %s" % event.pathname
        self.monitor.notify(event.pathname)

class Repository(object):

    def __init__(self, basedir):
        self.basedir = basedir
        self.name = basedir.rpartition('/')[2]
        self.logfile = os.path.join(self.basedir, '.worklog')

    @property
    def log(self):
        try:
            return [ float(line) for line in open(self.logfile) ]
        except IOError:
            return []

    def notify(self):
        open(self.logfile, 'a').write('%.6f\n' % time.time())

    def calculate_time(self, heartbeat = DEFAULT_HEARTBEAT):
        time = 0
        activity = self.log

        while activity:
            start = activity.pop(0)
            current = start
            while activity and activity[0] - current <= heartbeat:
                current = activity.pop(0)
            time += current - start

        return time

    def clear(self):
        open(self.logfile, 'w').close()
        
class RepositorySet(dict):

    def __init__(self, basedir, timeout=10):
        assert os.path.isdir(basedir)

        self.basedir = os.path.realpath(basedir)
        self.wm = pyinotify.WatchManager()
        self.mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE  | pyinotify.IN_CLOSE_WRITE

        self.notifier = pyinotify.Notifier(self.wm, EventHandler(self), timeout=timeout)

        for subdir in os.listdir(self.basedir):
            path = os.path.join(self.basedir, subdir)
            if os.path.isdir(os.path.join(path, '.git')):
                self[subdir] = Repository(path)
                self.register_dir(path)

    def register_dir(self, path):
        self.wm.add_watch(path, self.mask, rec=True)

    def notify(self, pathname):
        if pathname.endswith('.worklog'):
            return
        pathname = os.path.realpath(pathname).replace('%s/' % self.basedir, '')
        repository = pathname.split('/')[0]

        try:
            self[repository].notify()
        except KeyError:
            pass

    def check(self):
        assert self.notifier._timeout is not None, 'Notifier must be constructed with a short timeout'
        self.notifier.process_events()
        while self.notifier.check_events():
            self.notifier.read_events()
            self.notifier.process_events()

    def run(self):
        while True:
            self.check()


        


