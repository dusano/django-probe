def get_probe_runner(settings):
	probe_path = settings.PROBE_RUNNER.split('.')
	# Allow for Python 2.5 relative paths
	if len(probe_path) > 1:
		probe_module_name = '.'.join(probe_path[:-1])
	else:
		probe_module_name = '.'
	probe_module = __import__(probe_module_name, {}, {}, probe_path[-1])
	probe_runner = getattr(probe_module, probe_path[-1])
	return probe_runner