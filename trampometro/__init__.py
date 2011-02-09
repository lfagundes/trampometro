# -*- coding: utf-8 -*-

import os, pyinotify, time

class Repository(object):

    def __init__(self, basedir):
        self.basedir = basedir
        self.name = basedir.rpartition('/')[2]
        self.logfile = os.path.join(self.basedir, '.worklog')

    @property
    def log(self):
        return [ float(line) for line in open(self.logfile) ]

    def notify(self):
        open(self.logfile, 'a').write('%.6f\n' % time.time())
        
class RepositorySet(dict):

    def __init__(self, basedir):
        assert os.path.isdir(basedir)
        self.basedir = os.path.realpath(basedir)

        for subdir in os.listdir(self.basedir):
            path = os.path.join(self.basedir, subdir)
            if os.path.isdir(os.path.join(path, '.git')):
                self[subdir] = Repository(path)

    def notify(self, pathname):
        pathname = os.path.realpath(pathname).replace('%s/' % self.basedir, '')
        repository = pathname.split('/')[0]

        try:
            self[repository].notify()
        except KeyError:
            pass


