from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):
	"""probe command"""

	help = "Running probes"
	
	def handle_noargs(self, **options):
		print "Probe"
