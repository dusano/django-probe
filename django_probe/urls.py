from django.conf.urls.defaults import patterns, include, url


urlpatterns = patterns('',
    url(r'^$', 'django_probe.views.probe', name='django_probe'),
)