from setuptools import setup, find_packages
import os

setup(name = 'trampometro',
      version = '0.1',
      description = 'Coding work measure tool for git-based projects',
      long_description = '',
      author = "Luis Fagundes",
      author_email = "lhfagundes@hacklab.com.br",
      license = "The MIT License",
      packages = find_packages(),
      entry_points = {
          'console_scripts': [
              'trampometro = trampometro:run',
              ]
          },
      
)
