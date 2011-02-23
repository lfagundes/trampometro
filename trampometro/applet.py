#!/usr/bin/env python

import pygtk
pygtk.require('2.0')

import sys, os
import gtk, gnomeapplet, gnome, gobject

from trampometro import RepositorySet

class TrampometroApplet(object):

    def __init__(self, applet, iid):
        gnome.init("trampometro", "1.0")
        self.applet = applet
        self.hbox = gtk.HBox()
        self.label = gtk.Label("---")
        applet.add(self.hbox)
        self.hbox.add(self.label)

        self.monitor = RepositorySet("%s/devel" % os.environ['HOME'])

        self.check()

        applet.show_all()

    def check(self):
        self.monitor.check()
        if self.monitor.status:
            self.label.set_label(self.monitor.status)
        else:
            self.label.set_label('---')
        gobject.timeout_add(10, self.check)

        
def applet_factory(applet, iid):
    TrampometroApplet(applet, iid)
    return True

if len(sys.argv) == 2 and sys.argv[1] == "run-in-window":   
    main_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    main_window.set_title("Trampometro Applet")
    main_window.connect("destroy", gtk.main_quit) 
    app = gnomeapplet.Applet()
    applet_factory(app, None)
    app.reparent(main_window)
    main_window.show_all()
    gtk.main()
    sys.exit()

gnomeapplet.bonobo_factory("OAFIID:GNOME_TrampometroApplet_Factory",
                            gnomeapplet.Applet.__gtype__,
                            "hello", "0", applet_factory)
