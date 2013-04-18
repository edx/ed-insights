from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('',
    # Examples:
    url(r'^view/([A-Za-z_+]+)$', 'djanalytics.core.views.handle_view'),
    url(r'^query/([A-Za-z_+]+)$', 'djanalytics.core.views.handle_query'),
    url(r'^schema$', 'djanalytics.core.views.schema'),
    url(r'^event_properties$', 'djanalytics.core.views.event_properties'),
    # url(r'^probe$', 'djanalytics.core.views.handle_probe'),
    # url(r'^probe/([A-Za-z_+]+)$', 'djanalytics.core.views.handle_probe'),
    # url(r'^probe/([A-Za-z_+]+)/([A-Za-z_+]+)$', 'djanalytics.core.views.handle_probe'),
    # url(r'^probe/([A-Za-z_+]+)/([A-Za-z_+]+)/([A-Za-z_+]+)$', 'djanalytics.core.views.handle_probe'),
    # url(r'^probe/([A-Za-z_+]+)/([A-Za-z_+]+)/([A-Za-z_+]+)/([A-Za-z_+]+)$', 'djanalytics.core.views.handle_probe'),
)
