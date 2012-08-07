""" 
cimri matcher control panel
---------------------------
date:                    01.31.2012
author:                  gun@alppay.com

description:
------------

revision history: 
-----------------
gun@alppay.com:          initial version

"""

from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
        #public home page
        url(r'^$', 'cpanel.ui.views.default', name='home'),

	#system 
        url(r'^system/monitor/$', 'cpanel.ui.views.system_monitor', name='system_monitor'),
        url(r'^system/monitor/(?P<id>.+)/$', 'cpanel.ui.views.system_monitor_module', name='system_monitor_module'),
        url(r'^system/control$', 'cpanel.ui.views.system_control', name='system_control'),
        url(r'^system/reports$', 'cpanel.ui.views.system_reports', name='system_reports'),
        url(r'^system/reports/log/(?P<id>.+)/$', 'cpanel.ui.views.system_report_log', name='system_report_log'),
        url(r'^system/reports/error/(?P<id>.+)/$', 'cpanel.ui.views.system_report_error', name='system_report_error'),
        url(r'^system/reports/result/(?P<id>.+)/$', 'cpanel.ui.views.system_report_results', name='system_report_results'),
        url(r'^system/reports/test/(?P<id>.+)/$', 'cpanel.ui.views.system_report_test', name='system_report_test'),
        url(r'^system/reports/scraper/$',   'cpanel.ui.views.scraper_reports', name='scraper_reports'),
        url(r'^system/analytics/test/(?P<id>.+)/$', 'cpanel.ui.views.system_analytics_test', name='system_analytics_test'),
        url(r'^system/reports/(?P<id>.+)/$', 'cpanel.ui.views.system_report', name='system_report'),
        url(r'^system/log$', 	 'cpanel.ui.views.system_log', name='system_log'),
        url(r'^system/training$','cpanel.ui.views.system_training', name='system_training'),
        url(r'^system/tests$','cpanel.ui.views.system_tests', name='system_tests'),
        url(r'^system/cache$',   'cpanel.ui.views.system_cache', name='system_cache'),

	#get status
        url(r'^system/status/$', 'cpanel.ui.views.system_status', name='system_status'),
        url(r'^system/threads/$', 'cpanel.ui.views.system_threads', name='system_threads'),

	#handle schedules tasks
        url(r'^system/schedule/$', 'cpanel.ui.views.handle_schedule', name='handle_schedule'),

	#tasks
        url(r'^task/new/$', 'cpanel.ui.views.task_create', name='task_create'),
        url(r'^task/created/$', 'cpanel.ui.views.task_created', name='task_created'),
        url(r'^task/schedule/$', 'cpanel.ui.views.task_schedule', name='task_schedule'),
        url(r'^template/create/$', 'cpanel.ui.views.template_create', name='template_create'),
        url(r'^template/(?P<id>.+)/newtask/$', 'cpanel.ui.views.create_task_from_template', name='task_from_template'),
        url(r'^template/(?P<id>.+)/schedule/$', 'cpanel.ui.views.update_template_schedule', name='update_template_schedule'),
        url(r'^template/created/$', 'cpanel.ui.views.template_created', name='template_created'),
        url(r'^template/updated/$', 'cpanel.ui.views.template_updated', name='template_updated'),
        url(r'^template/(?P<id>.+)/$', 'cpanel.ui.views.update_template', name='update_template'),

	#scraper control
        url(r'^system/scraper/$',   'cpanel.ui.views.scraper_control', name='scraper_control'),

	#data access
        url(r'^data/scraper/(?P<merchantid>.+)/item/$',   'cpanel.ui.views.get_scraper_item', name='get_scraper_item'),
        url(r'^data/scraper/(?P<merchantid>.+)/items/$',   'cpanel.ui.views.get_scraper_items', name='get_scraper_items'),

	#testing
        url(r'^test/new/$', 'cpanel.ui.views.test_new', name='test_new'),
        url(r'^test/check/(?P<id>.+)/(?P<tid>.+)/$', 'cpanel.ui.views.test_check', name='test_check'),
        url(r'^test/created/$', 'cpanel.ui.views.test_created', name='test_created'),
        url(r'^test/(?P<id>.+)/schedule/$', 'cpanel.ui.views.test_schedule', name='test_schedule'),

	#training
        url(r'^training/new/$', 'cpanel.ui.views.training_new', name='training_new'),
        url(r'^training/check/(?P<id>.+)/(?P<tid>.+)/$', 'cpanel.ui.views.training_check', name='training_check'),
        url(r'^training/created/$', 'cpanel.ui.views.training_created', name='training_created'),
        url(r'^training/(?P<id>.+)/schedule/$', 'cpanel.ui.views.training_schedule', name='training_schedule'),
	
	#users
        url(r'^users/$', 'cpanel.ui.views.users', name='users'),

	#scraper training
        url(r'^scraper/training/(?P<id>.+)/build/$', 'cpanel.ui.views.scraper_training_build', name='scraper_training_build'),
        url(r'^scraper/training/(?P<id>.+)/update/$', 'cpanel.ui.views.scraper_training_update', name='scraper_training_update'),

	#scraper testing
        url(r'^scraper/test/(?P<id>.+)/build/$', 'cpanel.ui.views.scraper_test_build', name='scraper_test_build'),
        url(r'^scraper/test/(?P<id>.+)/update/$', 'cpanel.ui.views.scraper_test_update', name='scraper_test_update'),

	#matcher testing
        url(r'^matcher/test/(?P<id>.+)/build/$', 'cpanel.ui.views.matcher_test_build', name='matcher_test_build'),
        url(r'^matcher/test/(?P<id>.+)/update/$', 'cpanel.ui.views.matcher_test_update', name='matcher_test_update'),

	#cimri catalogue access
        url(r'^catalogue/items/$', 'cpanel.ui.views.catalogue_items', name='catalogue_items'),

        #login 
        url(r'^login/(?P<uname>.+)/(?P<pwd>.+)/$', 'cpanel.auth.views.login', name='login'),

        #logout
        url(r'^logout/$', 'cpanel.auth.views.logout', name='logout'),

)
