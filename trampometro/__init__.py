# -*- coding: utf-8 -*-

import os, pyinotify, time

class Repository(object):

    def __init__(self, basedir):
        self.basedir = basedir
        self.name = basedir.rpartition('/')[2]
    
class RepositorySet(set):

    def __init__(self, basedir):
        assert os.path.isdir(basedir)
        self.basedir = os.path.realpath(basedir)

        self.log = []

        for subdir in os.listdir(self.basedir):
            subdir = os.path.join(self.basedir, subdir)
            if os.path.isdir(os.path.join(subdir, '.git')):
                self.add(Repository(subdir))

    def notify(self, pathname):
        self.log.append(time.time())

