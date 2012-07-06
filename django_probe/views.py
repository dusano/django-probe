import logging
import sys
import StringIO

from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext

from django_probe.utils import get_probe_runner

logger = logging.getLogger(__name__)


def probe(request):

	# Empty for now. We should be able to set this from the request parameters
	probe_labels = []
	
	ProbeRunner = get_probe_runner(settings)
	probe_output = StringIO.StringIO()
	probe_runner = ProbeRunner(verbosity=2, interactive=False, failfast=False)
	(probe_suite, failures, errors) = probe_runner.run_probes(probe_labels, stream = probe_output)
	
	context = {
		"probe_suite": probe_suite,
		"failures": failures,
		"errors": errors,
		"probe_output": probe_output.getvalue(),
	}
	
	probe_output.close()

	return render_to_response('probe.html', context, RequestContext(request))