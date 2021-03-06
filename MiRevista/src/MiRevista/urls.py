from django.conf.urls import patterns, include, url
# from django.conf.urls.defaults import *
# from django.views.generic.simple import direct_to_template

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Reglas para templates
    url(r'css/defaultdyn.css$', 'Content.views.customvalues'),
    url(r'rss$', 'Content.views.xmlrender'),
    url(r'css/(?P<path>.*)$', 'django.views.static.serve',{'document_root': 'templates'}),
    url(r'images/(?P<path>.*)$', 'django.views.static.serve',{'document_root': 'templates/images'}),
    # Admin
    url(r'^admin', include(admin.site.urls)),
    # /canales
    url(r'^canales$', 'Content.views.channels'),
    url(r'^canales/\d*$', 'Content.views.channels'),
    # /help
    url(r'^help$', 'Content.views.help'),
    # Otros (ie. /usuario)
    url(r'^(.*)$', 'Content.views.server',),




    # Examples:
    # url(r'^$', 'MiRevista.views.home', name='home'),
    # url(r'^MiRevista/', include('MiRevista.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    
)
