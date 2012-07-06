import sys
import signal
import unittest

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import get_app, get_apps


try:
	all
except NameError:
	from django.utils.itercompat import all

# The module name for probes
PROBE_MODULE = 'probes'

class DjangoProbeRunner(unittest.TextTestRunner):

	def __init__(self, verbosity=0, failfast=False, **kwargs):
		super(DjangoProbeRunner, self).__init__(verbosity=verbosity, **kwargs)
		self.failfast = failfast
		self._keyboard_interrupt_intercepted = False

	def run(self, *args, **kwargs):
		"""
		Runs the probe suite after registering a custom signal handler
		that triggers a graceful exit when Ctrl-C is pressed.
		"""
		self._default_keyboard_interrupt_handler = signal.signal(signal.SIGINT,
			self._keyboard_interrupt_handler)
		try:
			result = super(DjangoProbeRunner, self).run(*args, **kwargs)
		finally:
			signal.signal(signal.SIGINT, self._default_keyboard_interrupt_handler)
		return result

	def _keyboard_interrupt_handler(self, signal_number, stack_frame):
		"""
		Handles Ctrl-C by setting a flag that will stop the probe run when
		the currently running probe completes.
		"""
		self._keyboard_interrupt_intercepted = True
		sys.stderr.write(" <Probe run halted by Ctrl-C> ")
		# Set the interrupt handler back to the default handler, so that
		# another Ctrl-C press will trigger immediate exit.
		signal.signal(signal.SIGINT, self._default_keyboard_interrupt_handler)

	def _makeResult(self):
		result = super(DjangoProbeRunner, self)._makeResult()
		failfast = self.failfast

		def stoptest_override(func):
			def stoptest(test):
				# If we were set to failfast and the unit test failed,
				# or if the user has typed Ctrl-C, report and quit
				if (failfast and not result.wasSuccessful()) or \
					self._keyboard_interrupt_intercepted:
					result.stop()
				func(test)
			return stoptest

		setattr(result, 'stopTest', stoptest_override(result.stopTest))
		return result

def get_probes(app_module):
	try:
		app_path = app_module.__name__.split('.')[:-1]
		probe_module = __import__('.'.join(app_path + [PROBE_MODULE]), {}, {}, PROBE_MODULE)
	except ImportError, e:
		# Couldn't import probes.py. Was it due to a missing file, or
		# due to an import error in a probes.py that actually exists?
		import os.path
		from imp import find_module
		try:
			mod = find_module(PROBE_MODULE, [os.path.dirname(app_module.__file__)])
		except ImportError:
			# 'probes' module doesn't exist. Move on.
			probe_module = None
		else:
			# The module exists, so there must be an import error in the
			# probe module itself. We don't need the module; so if the
			# module was a single file module (i.e., probes.py), close the file
			# handle returned by find_module. Otherwise, the probe module
			# is a directory, and there is nothing to close.
			if mod[0]:
				mod[0].close()
			raise
	return probe_module

def build_suite(app_module):
	"Create a complete Django probe suite for the provided application module"
	suite = unittest.TestSuite()

	suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(app_module))

	# Check to see if a separate 'probes' module exists parallel to the
	# models module
	probe_module = get_probes(app_module)
	if probe_module:
		# Probes in the probes.py module. If module has
		# a suite() method, use it. Otherwise build the test suite ourselves.
		if hasattr(probe_module, 'suite'):
			suite.addTest(probe_module.suite())
		else:
			suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(probe_module))

	return suite

def build_probe(label):
	"""Construct a probe with the specified label. Label should be of the
	form app.Probe or app.Probe.probe_method. Returns an
	instantiated probe or probe suite corresponding to the label provided.

	"""
	parts = label.split('.')
	if len(parts) < 2 or len(parts) > 3:
		raise ValueError("Probe label '%s' should be of the form app.Probe or app.Probe.probe_method" % label)

	#
	# First, look for Probe instances with a name that matches
	#
	app_module = get_app(parts[0])
	probe_module = get_probes(app_module)
	ProbeClass = getattr(probe_module, parts[1], None)

	try:
		if issubclass(ProbeClass, unittest.TestCase):
			if len(parts) == 2: # label is app.ProbeClass
				try:
					return unittest.TestLoader().loadTestsFromTestCase(ProbeClass)
				except TypeError:
					raise ValueError("Probe label '%s' does not refer to a probe class" % label)
			else: # label is app.ProbeClass.probe_method
				return ProbeClass(parts[2])
	except TypeError:
		# ProbeClass isn't a Probe - it must be a method or normal class
		pass

	raise ValueError("Probe label '%s' does not refer to a probe" % label)

def partition_suite(suite, classes, bins):
	"""
	Partitions a probe suite by probe type.

	classes is a sequence of types
	bins is a sequence of TestSuites, one more than classes

	Probes of type classes[i] are added to bins[i],
	probes with no match found in classes are place in bins[-1]
	"""
	for probe in suite:
		if isinstance(probe, unittest.TestSuite):
			partition_suite(probe, classes, bins)
		else:
			for i in range(len(classes)):
				if isinstance(probe, classes[i]):
					bins[i].addTest(probe)
					break
			else:
				bins[-1].addTest(probe)

def reorder_suite(suite, classes):
	"""
	Reorders a probe suite by probe type.

	classes is a sequence of types

	All probes of type clases[0] are placed first, then probes of type classes[1], etc.
	Probes with no match in classes are placed last.
	"""
	class_count = len(classes)
	bins = [unittest.TestSuite() for i in range(class_count+1)]
	partition_suite(suite, classes, bins)
	for i in range(class_count):
		bins[0].addTests(bins[i+1])
	return bins[0]

class DjangoProbeSuiteRunner(object):
	def __init__(self, verbosity=1, interactive=True, failfast=True, **kwargs):
		self.verbosity = verbosity
		self.interactive = interactive
		self.failfast = failfast

	def build_suite(self, probe_labels, extra_probes=None, **kwargs):
		suite = unittest.TestSuite()

		if probe_labels:
			print "build_suite.probe_labels"
			for label in probe_labels:
				if '.' in label:
					suite.addTest(build_probe(label))
				else:
					app = get_app(label)
					suite.addTest(build_suite(app))
		else:
			print "build_suite.all"
			for app in get_apps():
				suite.addTest(build_suite(app))

		if extra_probes:
			for extra_probe in extra_probes:
				suite.addTest(extra_probe)

		return reorder_suite(suite, (unittest.TestCase,))

	def run_suite(self, suite, **kwargs):
		return DjangoProbeRunner(verbosity=self.verbosity, failfast=self.failfast).run(suite)

	def suite_result(self, suite, result, **kwargs):
		return len(result.failures) + len(result.errors)

	def run_probes(self, probe_labels, extra_probes=None, **kwargs):
		"""
		Run the probes for all the probe labels in the provided list.
		Labels must be of the form:
		 - app.ProbeClass.probe_method
			Run a single specific probe method
		 - app.ProbeClass
			Run all the probe methods in a given class
		 - app
			Search for probes in the named application.

		When looking for probes, the probe runner will look in the models and
		probes modules for the application.

		A list of 'extra' probes may also be provided; these probes
		will be added to the probe suite.

		Returns the number of probes that failed.
		"""
		suite = self.build_suite(probe_labels, extra_probes)
		result = self.run_suite(suite)
		return self.suite_result(suite, result)
