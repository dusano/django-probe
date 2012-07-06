import sys
from django.core.management.base import BaseCommand
from optparse import make_option


class Command(BaseCommand):
	option_list = BaseCommand.option_list + (
		make_option('--noinput', action='store_false', dest='interactive', default=True,
			help='Tells Django to NOT prompt the user for input of any kind.'),
		make_option('--failfast', action='store_true', dest='failfast', default=False,
			help='Tells Django to stop running the probe suite after first failed probe.')
	)
	help = 'Runs the probe suite for the specified applications, or the entire site if no apps are specified.'
	args = '[appname ...]'

	def handle(self, *probe_labels, **options):
		from django.conf import settings
		from django_probe.utils import get_probe_runner
		
		verbosity = int(options.get('verbosity', 1))
		interactive = options.get('interactive', True)
		failfast = options.get('failfast', False)
		ProbeRunner = get_probe_runner(settings)
		
		probe_runner = ProbeRunner(verbosity=verbosity, interactive=interactive, failfast=failfast)
		failures = probe_runner.run_probes(probe_labels)
		
		if failures:
			sys.exit(bool(failures))
