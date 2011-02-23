# -*- coding: utf-8 -*-

import os, sys, pyinotify, time, re, git
from subprocess import Popen, PIPE

DEFAULT_HEARTBEAT = 300
DEBUG_LEVEL = 0

class EventHandler(pyinotify.ProcessEvent):

    def __init__(self, monitor):
        super(EventHandler, self).__init__()
        self.monitor = monitor

    def process_IN_CREATE(self, event):
        self.monitor.notify(event.pathname, event.maskname)
        if os.path.isdir(event.pathname):
            self.monitor.register_dir(event.pathname)

    def process_IN_DELETE(self, event):
        self.monitor.notify(event.pathname, event.maskname)

    def process_IN_CLOSE_WRITE(self, event):
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

    def is_commit(self, object_id):
        current_dir = os.getcwd()
        os.chdir(self.basedir)
        proc = Popen(('git cat-file -t %s' % object_id).split(), stdout=PIPE)
        proc.wait()
        os.chdir(current_dir)
        return proc.stdout.read().strip() == 'commit'

    def is_head_commit(self, commit_id):
        if DEBUG_LEVEL > 1:
            print "head commit is %s, this one is %s" % (self.repository.head.commit.hexsha, commit_id)
        return self.repository.head.commit.hexsha == commit_id

    def notify_commit(self, object_id):
        if DEBUG_LEVEL > 0:
            print "commit notified on %s" % self.name
            
        current_dir = os.getcwd()
        os.chdir(self.basedir)
        
        worked_time = self.calculate_time()
        self.clear()

        proc = Popen(('git cat-file -p %s' % object_id).split(), stdout=PIPE)
        proc.wait()
        commit_info = proc.stdout.read()
        author_info = [ line for line in commit_info.split('\n') if line.startswith('author') ][0].split()
        author = ' '.join(author_info[1:-2])

        if not os.path.isdir('meta'):
            os.mkdir('meta')
        log = open(os.path.join(self.basedir, 'meta/worklog'), 'a')
        log.write('\n')
        log.write(author)
        log.write('\n')
        log.write(self.format_time(worked_time))
        log.write('\n')
        log.write(self.repository.head.commit.summary.encode('utf-8'))
        log.write('\n')
        log.close()

        if DEBUG_LEVEL > 0:
            print "logged %s on %s" % (self.name, self.format_time(worked_time))
        
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
            while activity and activity[0] - current <= heartbeat and activity[0] >= current:
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

        self.status = 'IDLE'
        self.last_activity = time.time()

    def register_dir(self, path):
        self.wm.add_watch(path, self.mask, rec=True)
        try:
            for filename in os.listdir(path):
                filename = os.path.join(path, filename)
                self.notify(filename, 'IN_CREATE')
                if os.path.isdir(filename):
                    self.register_dir(filename)
        except OSError:
            # Directory might have been removed
            pass
        

    def notify(self, pathname, maskname = None):
        if DEBUG_LEVEL > 1:
            print "%s %s" % (maskname, pathname)

        if pathname.endswith('.worklog'):
            return

        pathname = os.path.realpath(pathname).replace('%s/' % self.basedir, '')
        repository = pathname.split('/')[0]

        try:
            self[repository].notify()
            if '/.git/' not in pathname and not re.search('meta(/worklog)?$', pathname):
                self.status = 'Working on %s' % repository
            self.last_activity = time.time()
            
        except KeyError:
            if DEBUG_LEVEL > 1:
                print "No such repository %s" % repository
            return

        if re.search('.git/objects/[0-9a-f]{2}/[0-9a-f]{38}$', pathname) and maskname == 'IN_CREATE':
            if DEBUG_LEVEL > 1:
                print "New git object detected"
            object_id = ''.join(pathname.split('/')[-2:])

            if not self[repository].is_commit(object_id):
                # Object is not commit, ignore
                return
            
            if object_id == self[repository].last_commit:
                # This was our last commit logging work time, ignore
                return

            """
            The test below was substituted by is_commit(), because there is a delay
            before the just created commit becomes the head commit
            
            if not self[repository].is_head_commit(object_id):
                return
            """

            if DEBUG_LEVEL > 0:
                print "Object is commit"

            try:
                fetch_head = os.path.join(self[repository].basedir, '.git/FETCH_HEAD')
                fetch_object_id = open(fetch_head).read().split()[0]
                if object_id == fetch_object_id:
                    return
            except IOError: #no such file
                pass

            if DEBUG_LEVEL > 0:
                print "Commit does not come from a fetch"

            self.status = '%s %s' % (repository, self[repository].format_time(self[repository].calculate_time()))
            self[repository].notify_commit(object_id)

    def check(self):
        assert self.notifier._timeout is not None, 'Notifier must be constructed with a short timeout'
        if time.time() - self.last_activity > DEFAULT_HEARTBEAT:
            self.status = 'IDLE'
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
    

