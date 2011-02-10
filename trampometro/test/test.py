#coding: utf-8

import os, random, fudge, time, subprocess
from unittest import TestCase
from trampometro import RepositorySet, Repository

class BaseTest(TestCase):
    def setUp(self):
        self.basedir = '/tmp/trampometro-%s' % ''.join([ chr(random.choice(range(65,91))) for i in range(5) ])
        os.mkdir(self.basedir)
        self.time_patch = None
        self.current_dir = os.getcwd()

    def tearDown(self):
        os.chdir(self.current_dir)
        os.system('rm -rf %s' % self.basedir)
        if self.time_patch:
            self.time_patch.restore()
        

    def set_now(self, now):
        if self.time_patch:
            self.time_patch.restore()
            
        fake_time = fudge.Fake('fake_time', callable=True).returns(now)
        self.time_patch = fudge.patch_object(time, 'time', fake_time)

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
        self.init_repo('testrepo')
        self.testfile = '%s/testrepo/testfile' % self.basedir

    def test_log_starts_empty(self):

        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')

        self.assertEquals(len(repo.log), 0)

    def test_edition_timestamps_are_logged(self):

        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')

        self.set_now(1297247102.816747)
        monitor.notify(self.testfile)
        self.assertTrue(1297247102.816747 in repo.log)
            
        self.set_now(1297247104.816787) 
        monitor.notify(self.testfile)
        self.assertTrue(1297247102.816747 in repo.log)
        self.assertTrue(1297247104.816787 in repo.log)
            
        self.set_now(1297247114.916787) 
        monitor.notify(self.testfile)
        self.assertTrue(1297247102.816747 in repo.log)
        self.assertTrue(1297247104.816787 in repo.log)
        self.assertTrue(1297247114.916787 in repo.log)


    def test_non_repo_editions_are_not_logged(self):
        self.mkdir('nonrepo')
        
        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')
        
        monitor.notify(self.testfile)
        self.assertEquals(len(repo.log), 1)

        monitor.notify('%s/nonrepo/testfile' % self.basedir)
        self.assertEquals(len(repo.log), 1)

    def test_activity_is_object_independent(self):
        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')

        monitor.notify(self.testfile)
        self.assertEquals(len(repo.log), 1)

        monitor2 = RepositorySet(self.basedir)
        repo2 = monitor2.get('testrepo')
        self.assertEquals(len(repo2.log), 1)

        monitor.notify(self.testfile)
        self.assertEquals(len(repo.log), 2)
        self.assertEquals(len(repo2.log), 2)

    def test_empty_log_results_in_no_work(self):
        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')
        self.assertEquals(repo.calculate_time(), 0)
        

    def test_work_is_calculated_based_on_log(self):
        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')

        for i in range(11):
            self.set_now(10**9 + 60 * i)
            monitor.notify(self.testfile)

        self.assertEquals(repo.calculate_time(heartbeat = 70), 600)

    def test_work_gaps_bigger_than_heartbeat_are_not_considered_in_work_calculation(self):
        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')

        self.set_now(10**9)
        monitor.notify(self.testfile)
        self.set_now(10**9 + 60)
        monitor.notify(self.testfile)
        self.set_now(10**9 + 200)
        monitor.notify(self.testfile)
        self.set_now(10**9 + 260)
        monitor.notify(self.testfile)

        self.assertEquals(repo.calculate_time(heartbeat = 70), 120)
        self.assertEquals(repo.calculate_time(heartbeat = 200), 260)

    def test_log_can_be_cleared(self):
        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')
        
        self.set_now(10**9)
        monitor.notify(self.testfile)
        self.set_now(10**9 + 60)
        monitor.notify(self.testfile)

        self.assertEquals(repo.calculate_time(heartbeat = 70), 60)
        self.assertEquals(repo.calculate_time(heartbeat = 70), 60)

        repo.clear()
        self.assertEquals(repo.calculate_time(heartbeat = 70), 0)

class FileSystemMonitoringTest(BaseTest):

    def test_monitor_is_notified_when_file_changes(self):
        self.init_repo('testrepo')
        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')

        self.assertEquals(len(repo.log), 0)
        open(os.path.join(self.basedir, 'testrepo', 'asdf'), 'w').write('hello')
        monitor.check()
        self.assertTrue(len(repo.log) > 0)

    def test_new_directories_are_monitored(self):
        self.init_repo('testrepo')
        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')

        os.mkdir(os.path.join(self.basedir, 'testrepo', 'testdir'))
        monitor.check()
        repo.clear()

        self.assertEquals(len(repo.log), 0)
        open(os.path.join(self.basedir, 'testrepo', 'testdir', 'asdf'), 'w').write('hello')
        monitor.check()
        self.assertTrue(len(repo.log) > 0)        
        repo.clear()

class CommitTest(BaseTest):

    def setUp(self):
        super(CommitTest, self).setUp()
        self.time_patch = None
        self.init_repo('testrepo')
        self.testfile = '%s/testrepo/testfile' % self.basedir

    def stdout(self, command):
        proc = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        proc.wait()
        return proc.stdout.read()
        
    def test_commit(self):
        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')

        self.set_now(10**9)
        open(self.testfile, 'w').write('hello')
        monitor.check()
        self.set_now(10**9 + 60)
        open(self.testfile, 'a').write(' world')
        monitor.check()
        self.set_now(10**9 + 120)
        open(self.testfile, 'a').write(' world')
        monitor.check()

        os.chdir('%s/testrepo' % self.basedir)

        os.system('git add testfile >/dev/null')
        os.system('git commit -a -m "Test Message" >/dev/null')

        monitor.check()

        self.assertTrue(os.path.exists('worklog'))
        self.assertTrue('new file' not in self.stdout('git status worklog'))

        content = [ line.strip() for line in open('worklog') ]
        self.assertTrue('Test Message' in content)
        self.assertTrue('00:02:00' in content)
        
                        

        

        



        

        

