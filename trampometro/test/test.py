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
        self.assertEquals(len(reposet), 1)
        self.assertTrue('repo1' in reposet)

        self.init_repo('repo2')
        reposet = RepositorySet(self.basedir)
        self.assertEquals(len(reposet), 2)
        self.assertTrue('repo1' in reposet)
        self.assertTrue('repo2' in reposet)

        self.mkdir('repo3')
        reposet = RepositorySet(self.basedir)
        self.assertEquals(len(reposet), 2)
        self.assertTrue('repo1' in reposet)
        self.assertTrue('repo2' in reposet)

        self.init_repo('repo3')
        reposet = RepositorySet(self.basedir)
        self.assertEquals(len(reposet), 3)
        self.assertTrue('repo1' in reposet)
        self.assertTrue('repo2' in reposet)

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

    def test_log_starts_empty(self):
        self.init_repo('testrepo')

        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')

        self.assertEquals(len(repo.log), 0)

    def test_edition_timestamps_are_logged(self):
        self.init_repo('testrepo')
        testfile = '%s/testrepo/testfile' % self.basedir

        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')

        self.set_now(1297247102.816747)
        monitor.notify(testfile)
        self.assertTrue(1297247102.816747 in repo.log)
            
        self.set_now(1297247104.816787) 
        monitor.notify(testfile)
        self.assertTrue(1297247102.816747 in repo.log)
        self.assertTrue(1297247104.816787 in repo.log)
            
        self.set_now(1297247114.916787) 
        monitor.notify(testfile)
        self.assertTrue(1297247102.816747 in repo.log)
        self.assertTrue(1297247104.816787 in repo.log)
        self.assertTrue(1297247114.916787 in repo.log)


    def test_non_repo_editions_are_not_logged(self):
        self.init_repo('testrepo')
        self.mkdir('nonrepo')
        
        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')
        
        monitor.notify('%s/testrepo/testfile' % self.basedir)
        self.assertEquals(len(repo.log), 1)

        monitor.notify('%s/nonrepo/testfile' % self.basedir)
        self.assertEquals(len(repo.log), 1)

    def test_activity_is_object_independent(self):
        self.init_repo('testrepo')
        testfile = '%s/testrepo/testfile' % self.basedir

        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')

        monitor.notify(testfile)
        self.assertEquals(len(repo.log), 1)

        monitor2 = RepositorySet(self.basedir)
        repo2 = monitor2.get('testrepo')
        self.assertEquals(len(repo2.log), 1)

        monitor.notify(testfile)
        self.assertEquals(len(repo.log), 2)
        self.assertEquals(len(repo2.log), 2)
        

        
        
