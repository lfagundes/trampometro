from setuptools import setup, find_packages
import os

setup(name = 'trampometro',
      version = '0.1',
      description = 'Coding work measurement tool for git-based projects',
      long_description = '',
      author = "Luis Fagundes",
      author_email = "lhfagundes@hacklab.com.br",
      license = "The MIT License",
      packages = find_packages(),
      entry_points = {
          'console_scripts': [
              'trampometro = trampometro:run',
              'trampometro_applet = trampometro.applet:applet_factory',
              ]
          },
      data_files = [
          ('/usr/lib/bonobo/servers', ['GNOME_TrampometroApplet_Factory.server']),
          ]
)
