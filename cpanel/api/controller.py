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


from cpanel.app.mgr import AppMgr
from cpanel.app.logger import Logger

from cimri.system.task import Task

class ControllerAPI(AppMgr):
	def __init__(self,request):
		super(ControllerAPI,self).__init__(request)

	def getstatus(self):
		return self.rpccall("getstatus")

	def getthreads(self):
		return self.rpccall("getthreads")

	def getcachestatus(self):
		return self.rpccall("getcachestatus")

	def clearcache(self,section):
		return self.rpccall("clearcache",section)

	def getthreadlogs(self):
		return self.rpccall("getthreadlogs")

	def getthreadinfo(self,id):
		return self.rpccall("getthreadinfo",id)

	def gettaskresults(self,id):
		return self.rpccall("gettaskresults",id)

	def gettasklog(self,id):
		return self.rpccall("gettasklog",id)

	def gettaskerrors(self,id):
		return self.rpccall("gettaskerrors",id)

	def schedule(self,tasks):
		return self.rpccall("schedule",[task.pack() for task in tasks])

	def getmerchants(self):
		return self.rpccall("getmerchants")

	def getcatalogueitems(self,title,brand,mpn):
		return self.rpccall("getcatalogueitems",title,brand,mpn)

	def getmoduledescriptors(self):
		#descriptor (this is TEMP. get these from the controller)
		descriptors=[
			#ProductXMLCrawler
			{"module":	"cimri.module.crawler.productxml.ProductXMLCrawler",
			 "type":	"crawler",
			 "ops":		["crawl","sample"],
			 "data":	None,
			 "meta":	[{"key":	"merchants.id",
					  "type":	"cimri.module.type.MerchantID",
					  "default":	None
					 },
					 {"key":	"merchants.id.alt",
					  "type":	"str",
					  "default":	""
					 },
					 {"key":	"merchants.index",
					  "type":	"int",
					  "default":	0
					 },
					 {"key":	"merchants.range",
					  "type":	"int",
					  "default":	None
					 },
					 {"key":	"merchants.items.index",
					  "type":	"int",
					  "default":	0
					 },
					 {"key":	"merchants.items.range",
					  "type":	"int",
					  "default":	None
					 },
					 {"key":	"merchants.all",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"cache.read",
					  "type":	"str",
					  "default":	""
					 },
					 {"key":	"cache.write",
					  "type":	"str",
					  "default":	""
					 },
					 {"key":	"workers",
					  "type":	"int",
					  "default":	1
					 }],

			 "result":	{"data":		"cimri.module.type.URL",
					 "meta.merchantid":	"cimri.module.type.MerchantID",
					 "meta.xmlitem":	"cimri.api.cimriservice.data.merchantitem.MerchantItem"
					}
			},

			#XMLScrapper
			{"module":	"cimri.module.scrapper.xmlscraper.XMLScrapper",
			 "type":	"scraper",
			 "ops":		["scrap"],
			 "data":	{"data":		"cimri.module.type.URL",
					 "meta.merchantid":	"cimri.module.type.MerchantID",
					 "meta.xmlitem":	"cimri.api.cimriservice.data.merchantitem.MerchantItem"
					},
			 "meta":	[{"key":	"cache.read",
					  "type":	"str",
					  "default":	""
					 },
					 {"key":	"cache.write",
					  "type":	"str",
					  "default":	""
					 },
					 {"key":	"untrained",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"benchmark",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"workers",
					  "type":	"int",
					  "default":	1
					 }],
			 "result":	{"data":		"cimri.api.cimriservice.data.merchantitem.MerchantItem",
					 "meta":		["str"]
					}
			},

			#DOMScrapper
			{"module":	"cimri.module.scrapper.dom.DOMScrapper",
			 "type":	"scraper",
			 "ops":		["scrap"],
			 "data":	{"data":		"cimri.module.type.URL",
					 "meta.merchantid":	"cimri.module.type.MerchantID",
					 "meta.xmlitem":	"cimri.api.cimriservice.data.merchantitem.MerchantItem"
					},
			 "meta":	[{"key":	"cache.read",
					  "type":	"str",
					  "default":	""
					 },
					 {"key":	"cache.write",
					  "type":	"str",
					  "default":	""
					 },
					 {"key":	"untrained",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"train",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"train.uuid",
					  "type":	"str",
					  "default":	""
					 },
					 {"key":	"validate_trained",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"ignore_not_approved",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"passthrough_not_approved",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"test",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"test.uuid",
					  "type":	"str",
					  "default":	""
					 },
					 {"key":	"benchmark",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"workers",
					  "type":	"int",
					  "default":	1
					 }],
			 "result":	{"data":		"cimri.api.cimriservice.data.merchantitem.MerchantItem",
					 "meta":		["str"]
					}
			},

			#LegacyMatcher
			{"module":	"cimri.module.matcher.legacy.LegacyMatcher",
			 "type":	"matcher",
			 "ops":		["match"],
			 "data":	{"data":		"cimri.api.cimriservice.data.merchantitem.MerchantItem",
					},
			 "meta":	[{"key":	"cache.read",
					  "type":	"str",
					  "default":	""
					 },
					 {"key":	"cache.write",
					  "type":	"str",
					  "default":	""
					 },
					 {"key":	"benchmark",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"workers",
					  "type":	"int",
					  "default":	1
					 }],
			 "result":	{"data":		"cimri.api.cimriservice.data.merchantitem.MerchantItem",
					 "meta.action":		"cimri.module.type.UpdateAction"
					},
			},

			#MetaMatcher
			{"module":	"cimri.module.matcher.meta.MetaMatcher",
			 "type":	"matcher",
			 "ops":		["match","match-sim","match-update","match-insert"],
			 "data":	{"data":		"cimri.api.cimriservice.data.merchantitem.MerchantItem",
					},
			 "meta":	[{"key":	"cache.read",
					  "type":	"str",
					  "default":	""
					 },
					 {"key":	"cache.write",
					  "type":	"str",
					  "default":	""
					 },
					 {"key":	"benchmark",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"workers",
					  "type":	"int",
					  "default":	1
					 },
					 {"key":	"match.unmatched",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"match.constrain",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"merchant.update",
					  "type":	"bool",
					  "default":	False
					 }],
			 "result":	{"data":		"cimri.api.cimriservice.data.merchantitem.MerchantItem",
					 "meta.action":		"cimri.module.type.UpdateAction"
					},
			},

			#SandboxUpdater
			{"module":	"cimri.module.update.sandbox.SandboxUpdater",
			 "type":	"updater",
			 "ops":		["update"],
			 "data":	{"data":		"cimri.api.cimriservice.data.merchantitem.MerchantItem",
					 "meta.action":		"cimri.module.type.UpdateAction"
					},
			 "meta":	[{"key":	"benchmark",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"workers",
					  "type":	"int",
					  "default":	1
					 }],
			 "result":	{"data":		"cimri.api.cimriservice.data.merchantitem.MerchantItem",
					 "meta.result":		"cimri.module.type.TaskResult",
					 "meta.error":		"cimri.module.type.TaskError"
					}
			},

			#CimriServiceUpdater
			{"module":	"cimri.module.update.cimriservice.CimriServiceUpdater",
			 "type":	"updater",
			 "ops":		["update"],
			 "data":	{"data":		"cimri.api.cimriservice.data.merchantitem.MerchantItem",
					 "meta.action":		"cimri.module.type.UpdateAction"
					},
			 "meta":	[{"key":	"benchmark",
					  "type":	"bool",
					  "default":	False
					 },
					 {"key":	"workers",
					  "type":	"int",
					  "default":	1
					 }],
			 "result":	{"data":		"cimri.api.cimriservice.data.merchantitem.MerchantItem",
					 "meta.result":		"cimri.module.type.TaskResult",
					 "meta.error":		"cimri.module.type.TaskError"
					}
			}
		]

		return descriptors


