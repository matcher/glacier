""" 
cimri matcher control panel
---------------------------
date:                    03.14.2012
author:                  gun@alppay.com

description:
------------

revision history: 
-----------------
gun@alppay.com:          initial version

"""


from cpanel.app.mgr import AppMgr
from cpanel.app.logger import Logger

from cimri.api.analytics.matcher import MatchRecord

class AnalyticsAPI(AppMgr):
	def __init__(self,request):
		super(AnalyticsAPI,self).__init__(request)

	def getmatcheritems(self,taskid):
		return MatchRecord.list(taskid=taskid)
