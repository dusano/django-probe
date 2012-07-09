from setuptools import setup, find_packages

setup(name='django_probe',
      version='0.1',
      description='Django Probe',
      author='Dusan Omercevic',
      packages=['django_probe'] + [ 'django_probe.%s' % package for package in find_packages('django_probe') ],
      package_dir = {'django_probe':'django_probe'},
     )
