Unittests are a very nice way to construct scaffolding around code. Such scaffolding enables a programmer more care free development with a reduced fear that a change in one part of the code base would cause unwanted consequences somewhere else. If a project is a part of a larger system, unittests quite often gets exploited also to implement system tests that verify that changes made in one component don't have unwanted effects in other parts of the system. Using unittests also for system tests have some very annoying side effects:

1. Running unittests requires setting dependent services,
2. Calling external services considerably increases running time of unittests,
3. System tests are brittle and require constant maintenance,
4. System tests are run only at deploy time, not with every system upgrade

To address these problems I've developed a python module django-probe whose aim is to separate system tests from unittests. I named an individual system test a probe, since a probe is meant to be run not only at deploy time but periodically and as part of a production system.  Similarly as Django organizes tests into tests modules, probes are organized in probes modules. All you need to do to set up a new probe, is to make either a file probes.py or module probes and populate it with the following code:

import unittest

class TestMyProbe(unittest.TestCase):

def test_my_probe(self):
  # usual unittest code
  # But don't forget. This unittests will be run in the production setting on live data!

Additionally, you should add django_probe to your list of INSTALLED_APPS and PROBE_RUNNER = 'django_probe.simple.DjangoProbeSuiteRunner' to your settings.py.

Probes should not be descendants of django.test.TestCase class but of unittest.TestCase class. Django's TestCase replaces several services with mocks which could wrack havoc if run in production.

Probes are run in a similar fashion as unittests but with a different management command probe

./manage.py probe        # Run all probes in all applications
./manage.py probe app        # Run all probes in application app
./manage.py probe app.TestMyProbe        # Run all probes in class TestMyProbe
./manage.py probe app.TestMyProbe.test_my_probe        # Run a single probe

Django command probe is meant primarily to be executed at deploy time. In order to enable easy execution of probes at runtime django-probe enables triggering of probes through a web interface by accessing /probe url. To install this option add the following to your urls.py

(r'^probe/', include('django_probe.urls'))