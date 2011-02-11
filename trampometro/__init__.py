# -*- coding: utf-8 -*-

import os, sys, pyinotify, time, re, git

DEFAULT_HEARTBEAT = 300
DEBUG = False

class EventHandler(pyinotify.ProcessEvent):

    def __init__(self, monitor):
        super(EventHandler, self).__init__()
        self.monitor = monitor

    def process_IN_CREATE(self, event):
        if DEBUG:
            print "Creating %s" % event.pathname
        self.monitor.notify(event.pathname, event.maskname)
        if os.path.isdir(event.pathname):
            self.monitor.register_dir(event.pathname)

    def process_IN_DELETE(self, event):
        if DEBUG:
            print "Delete %s" % event.pathname
        self.monitor.notify(event.pathname, event.maskname)

    def process_IN_CLOSE_WRITE(self, event):
        if DEBUG:
            print "Modified %s" % event.pathname
        self.monitor.notify(event.pathname, event.maskname)

class Repository(object):

    def __init__(self, basedir):
        self.basedir = basedir
        self.name = basedir.rpartition('/')[2]
        self.logfile = os.path.join(self.basedir, '.worklog')
        self.repository = git.Repo(self.basedir)
        self.last_commit = ''

    @property
    def log(self):
        try:
            return [ float(line) for line in open(self.logfile) ]
        except IOError:
            return []

    def notify(self):
        open(self.logfile, 'a').write('%.6f\n' % time.time())

    def is_head_commit(self, commit_id):
        return self.repository.head.commit.hexsha == commit_id

    def notify_commit(self):
        current_dir = os.getcwd()
        os.chdir(self.basedir)
        
        worked_time = self.calculate_time()
        self.clear()

        if not os.path.isdir('meta'):
            os.mkdir('meta')
        log = open(os.path.join(self.basedir, 'meta/worklog'), 'a')
        log.write('\n')
        log.write(self.repository.head.commit.summary.encode('latin-1'))
        log.write('\n')
        log.write(self.format_time(worked_time))
        log.write('\n')
        log.close()
        
        self.repository.index.add(['meta/worklog'])
        os.system('git commit --amend -C HEAD >/dev/null')

        self.last_commit = self.repository.head.commit.hexsha
        
        os.chdir(current_dir)

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

    def format_time(self, time):
        return '%02d:%02d:%02d' % (int(time/3600), int((time % 3600) / 60), time % 60)
        
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
                self.wm.add_watch(path, self.mask, rec=True)

    def register_dir(self, path):
        for filename in os.listdir(path):
            filename = os.path.join(path, filename)
            self.notify(filename, 'IN_CREATE')
            if os.path.isdir(filename):
                self.register_dir(filename)
        self.wm.add_watch(path, self.mask, rec=True)
        

    def notify(self, pathname, maskname = None):
        if pathname.endswith('.worklog'):
            return

        pathname = os.path.realpath(pathname).replace('%s/' % self.basedir, '')
        repository = pathname.split('/')[0]

        try:
            self[repository].notify()
        except KeyError:
            return

        if re.search('.git/objects/[0-9a-f]{2}/[0-9a-f]{38}$', pathname) and maskname == 'IN_CREATE':
            object_id = ''.join(pathname.split('/')[-2:])
            if not self[repository].is_head_commit(object_id):
                return

            if object_id != self[repository].last_commit:
                self[repository].notify_commit()

    def check(self):
        assert self.notifier._timeout is not None, 'Notifier must be constructed with a short timeout'
        self.notifier.process_events()
        while self.notifier.check_events():
            self.notifier.read_events()
            self.notifier.process_events()

    def run(self):
        self.notifier.loop()


def run():
    try:
        development_dir = sys.argv[1]
        assert os.path.exists(development_dir)
    except (IndexError, AssertionError):
        me = __file__.split('/')[-1]
        print """Usage: %s development_dir

development_dir is the base dir where your git repositories are""" % me
        sys.exit(0)

    RepositorySet(development_dir, 50).run()
    

