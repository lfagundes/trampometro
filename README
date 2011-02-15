Trampometro
===========

Trampometro is a tool to measure the ammount of time spent coding on each of your projects. Current assumptions:

- You use git to mantain your code
- You have a Linux environment
- If you edit a file every 5 minutes, then you're coding
- All you repositores are in same directory

How it works
............

A daemon monitors all filesystem activity in you base development directory. Everytime a modification occurs (IN_CREATE, IN_DELETE or IN_MODIFY event) in a git repository, trampometro marks the timestamp of that edition in .worklog file.

When a commit is detected, the ammount of work is calculated based on a heartbeat (currently hardcoded to 5 minutes), that indicates the maximum ammount of time between filesystem modifications for a work to be considered continous. Then the commit message and formmated time is written to meta/worklog file and a git commit --amend is done to include this logging.

How to run
..........

In shell::

    $ trampometro /home/myuser/my_development_dir

Current status
..............

No releases have been done and only the core concept is implemented. The software is in proof of concept stage.

Once this concept is proved valid, than some efforts may be done to make this configurable and easy to use.

Developers welcome!


