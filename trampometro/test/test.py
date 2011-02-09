#coding: utf-8

import os, random, fudge, time
from unittest import TestCase
from trampometro import RepositorySet, Repository

class BaseTest(TestCase):
    def setUp(self):
        self.basedir = '/tmp/trampometro-%s' % ''.join([ chr(random.choice(range(65,91))) for i in range(5) ])
        os.mkdir(self.basedir)

    def tearDown(self):
        os.system('rm -rf %s' % self.basedir)

    def mkdir(self, name):
        os.mkdir('%s/%s' % (self.basedir, name))

    def init_repo(self, name):
        if not os.path.exists('%s/%s' % (self.basedir, name)):
            self.mkdir(name)

        os.system('git init %s/%s >/dev/null' % (self.basedir, name))

class RepositorySetTest(BaseTest):

    def test_repository_detection(self):
        self.init_repo('repo1')
        reposet = RepositorySet(self.basedir)
        self.assertEquals([repo.name for repo in reposet], ['repo1'])

        self.init_repo('repo2')
        reposet = RepositorySet(self.basedir)
        self.assertEquals(sorted([repo.name for repo in reposet]), ['repo1', 'repo2'])

        self.mkdir('repo3')
        reposet = RepositorySet(self.basedir)
        self.assertEquals(sorted([repo.name for repo in reposet]), ['repo1', 'repo2'])

        self.init_repo('repo3')
        reposet = RepositorySet(self.basedir)
        self.assertEquals(sorted([repo.name for repo in reposet]), ['repo1', 'repo2', 'repo3'])

class RepositoryTest(BaseTest):

    def setUp(self):
        super(RepositoryTest, self).setUp()
        self.time_patch = None

    def tearDown(self):
        super(RepositoryTest, self).tearDown()        
        if self.time_patch:
            self.time_patch.restore()
            
    def set_now(self, now):
        if self.time_patch:
            self.time_patch.restore()
            
        fake_time = fudge.Fake('fake_time', callable=True).returns(now)
        self.time_patch = fudge.patch_object(time, 'time', fake_time)

    def test_edition_timestamps_are_logged(self):
        self.init_repo('testrepo')
        testfile = '%s/testrepo/testfile' % self.basedir
        
        monitor = RepositorySet(self.basedir)
        
        self.set_now(1297247102.816747)
        monitor.notify(testfile)
        self.assertTrue(1297247102.816747 in monitor.log)
            
        self.set_now(1297247104.816787) 
        monitor.notify(testfile)
        self.assertTrue(1297247102.816747 in monitor.log)
        self.assertTrue(1297247104.816787 in monitor.log)
            
        self.set_now(1297247114.916787) 
        monitor.notify(testfile)
        self.assertTrue(1297247102.816747 in monitor.log)
        self.assertTrue(1297247104.816787 in monitor.log)
        self.assertTrue(1297247114.916787 in monitor.log)


        


    
                  
    
