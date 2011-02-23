# -*- coding: utf-8 -*-

import os, random, fudge, time, subprocess
from unittest import TestCase
from trampometro import RepositorySet, Repository, DEFAULT_HEARTBEAT

def dev(test):
    test.tags = 'dev'
    return test
    
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
        current_dir = os.getcwd()
        if not os.path.exists('%s/%s' % (self.basedir, name)):
            self.mkdir(name)
        os.chdir('%s/%s' % (self.basedir, name))
        os.system('git init >/dev/null')
        os.system('git config user.name "Trampometro tester"')
        os.system('git config user.email "trampometro@example.com"')
        os.chdir(current_dir)

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

    def test_if_clock_is_adjusted_to_earlier_time_during_monitoring_than_negative_gap_is_ignored(self):
        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')
        
        self.set_now(10**9)
        monitor.notify(self.testfile)
        self.set_now(10**9 + 60)
        monitor.notify(self.testfile)
        self.set_now(10**9 - 1000)
        monitor.notify(self.testfile)
        self.set_now(10**9 -1000 + 60)
        monitor.notify(self.testfile)

        self.assertEquals(repo.calculate_time(heartbeat = 200), 120)


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

    def test_if_new_directory_is_created_and_instantly_removed_error_does_not_happen(self):
        self.init_repo('testrepo')
        monitor = RepositorySet(self.basedir)
        fake = fudge.Fake('isdir', callable=True).returns(True)
        patch = fudge.patch_object(os.path, 'isdir', fake)
        try:
            monitor.check()
            os.mkdir(os.path.join(self.basedir, 'testrepo', 'testdir'))
            os.rmdir(os.path.join(self.basedir, 'testrepo', 'testdir'))
            monitor.check()
        finally:
            patch.restore()
        
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

        self.assertTrue(os.path.exists('meta/worklog'))
        self.assertTrue('nothing to commit' in self.stdout('git status worklog'))

        content = [ line.strip() for line in open('meta/worklog') ]
        self.assertTrue('Trampometro tester <trampometro@example.com>' in content)
        self.assertTrue('Test Message' in content)
        self.assertTrue('00:02:00' in content)

        open(self.testfile, 'a').write('more')
        self.set_now(10**9 + 1220)
        monitor.check()
        open(self.testfile, 'a').write('yet')
        self.set_now(10**9 + 1280)
        monitor.check()
        
        os.system('git commit -a -m "Yet another message" >/dev/null')
        monitor.check()

        self.assertTrue(os.path.exists('meta/worklog'))
        self.assertTrue('nothing to commit' in self.stdout('git status worklog'))

        content = [ line.strip() for line in open('meta/worklog') ]
        self.assertTrue('Test Message' in content)
        self.assertTrue('00:02:00' in content)

        content = content[int(len(content)/2):]
        self.assertTrue('Yet another message' in content)
        self.assertTrue('00:01:00' in content)

    def test_commit_accepts_non_ascii(self):
        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')

        self.set_now(10**9)
        open(self.testfile, 'w').write('hello')
        monitor.check()
        self.set_now(10**9 + 60)
        open(self.testfile, 'a').write(' world')
        monitor.check()

        os.chdir('%s/testrepo' % self.basedir)

        utf_message_file = os.path.join(os.path.dirname(__file__), 'utf_message.txt')

        os.system('git add testfile >/dev/null')
        os.system('git commit -a -m `cat %s` >/dev/null' % utf_message_file)
  
        monitor.check()

        utf_message = open(utf_message_file).read().strip()
        worklog = open('meta/worklog').read()

        self.assertTrue(utf_message in worklog)

    def test_repository_can_identify_if_object_is_commit_or_not(self):
        monitor = RepositorySet(self.basedir)
        repo = monitor.get('testrepo')

        open(self.testfile, 'w').write('hello world')
        
        os.chdir('%s/testrepo' % self.basedir)
        os.system('git add testfile 2>/dev/null')
        os.system('GIT_COMMITTER_DATE="Tue Feb 15 08:50:31 BRST 2011" git commit -a -m "test commit" --date="Tue Feb 15 08:50:31 BRST 2011" --author="Trampometro tester <trampometro@example.com>" >/dev/null 2>/dev/null')
        
        self.assertTrue(not repo.is_commit('95d09f2b10159347eece71399a7e2e907ea3df4f'))
        self.assertTrue(not repo.is_commit('d34a3a0c29dbfab0dc7469cb6f7afeb52d6d1edd'))
        self.assertTrue(repo.is_commit('f7eb24d3aeb8d6ac71f147eaad97fd44192d6365'))

    def test_pull_is_not_considered(self):

        os.chdir(self.basedir)

        os.system('git clone testrepo testclone 2>/dev/null >/dev/null')

        os.chdir('%s/testrepo' % self.basedir)
        open('somefile', 'w').write('hello world')
        os.system('git add somefile >/dev/null')
        os.system('git commit -a -m "test commit" >/dev/null')

        monitor = RepositorySet(self.basedir)

        start = time.time()
        
        os.chdir('%s/testclone' % self.basedir)

        open('testfile', 'w').write('hello')
        monitor.check()
        self.set_now(start + 60)
        open('testfile', 'a').write(' world')
        monitor.check()

        os.system('git pull >/dev/null 2>/dev/null')
        monitor.check()
        self.set_now(start + 110.1)
        open('testfile', 'a').write('!!')
        monitor.check()

        os.system('git add testfile > /dev/null')
        os.system('git commit -a -m "second commit" 2>/dev/null > /dev/null')
        monitor.check()

        content = [ line.strip() for line in open('meta/worklog') ]
        self.assertTrue('second commit' in content)
        self.assertTrue('00:01:50' in content)

class StatusTest(BaseTest):

    def setUp(self):
        super(StatusTest, self).setUp()
        self.init_repo('repo1')
        self.init_repo('repo2')
        os.chdir(self.basedir)
        self.monitor = RepositorySet(self.basedir)

    def test_activity_in_project_changes_repositoryset_status(self):
        open('repo1/asdf', 'w').close()
        self.monitor.check()
        self.assertEquals(self.monitor.status, 'Working on repo1')

        open('repo2/asdf', 'w').close()
        self.monitor.check()
        self.assertEquals(self.monitor.status, 'Working on repo2')

        open('repo1/asdf', 'w').close()
        self.monitor.check()
        self.assertEquals(self.monitor.status, 'Working on repo1')
        self.monitor.check()
        self.assertEquals(self.monitor.status, 'Working on repo1')

    def test_inactivity_makes_status_idle(self):
        self.assertEquals(self.monitor.status, 'IDLE')
        self.monitor.check()
        self.assertEquals(self.monitor.status, 'IDLE')

        self.set_now(100)

        open('repo1/asdf', 'w').close()
        self.monitor.check()
        self.assertEquals(self.monitor.status, 'Working on repo1')

        self.set_now(101 + DEFAULT_HEARTBEAT)
        self.monitor.check()
        self.assertEquals(self.monitor.status, 'IDLE')

    def test_recent_commit_is_reported_on_status(self):
        os.chdir('repo1')
        
        self.set_now(10**9)
        open('testfile', 'w').write('hello')
        self.monitor.check()
        self.set_now(10**9 + 60)
        open('testfile', 'a').write(' world')
        self.monitor.check()

        os.system('git add testfile')
        os.system('git commit -a -m "first commit" 2>/dev/null > /dev/null')

        self.monitor.check()
        
        self.assertEquals(self.monitor.status, 'repo1 00:01:00')

        


        
