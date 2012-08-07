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

from datetime import datetime

from cpanel.app.mgr import AppMgr
from cpanel.app.logger import Logger

from cimri.api.scraper.merchant import MerchantScraperRecord
from cimri.api.scraper.item import MerchantItemScraperRecord

class ScraperAPI(AppMgr):
	def __init__(self,request):
		super(ScraperAPI,self).__init__(request)

	def getscraperstatus(self):
		return MerchantScraperRecord.list()

	def createmerchant(self,merchantid):
		rec=MerchantScraperRecord()
		rec.merchantid=merchantid
		rec.create()

		return rec

	def updatemerchant(self,merchantid,approved):
		#get merchant record
		rec=MerchantScraperRecord.get(merchantid=merchantid)

		#update
		rec.is_approved=approved
		rec.save()

	def getitems(self,merchantid,url,age=None,skip=0,limit=1000):
		#get merchant item record
		if url is None:
			res=MerchantItemScraperRecord.list_paginated(skip,limit,merchantid=int(merchantid))
		else:
			res=MerchantItemScraperRecord.list_paginated(skip,limit,merchantid=int(merchantid),url=url)

		#get results
		if res is None:
			return []
		items=[item for item in res]

		#check age
		now = datetime.now()
		if age is not None:
			items=[item for item in items if (now - item.updated).seconds < int(age) * 60]

		return items
