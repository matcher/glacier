""" 
cimri matcher system
--------------------   
date:                    02.17.2012
author:                  gun@alppay.com

description:
------------

revision history: 
-----------------
gun@alppay.com:          initial version

"""


from itertools import chain
import re
from string import Template
import math
import pickle
import os.path
import datetime
import codecs

from twisted.internet import reactor,defer
from twisted.internet.threads import deferToThread

from cimri.module.module import Distributor
from cimri.system.cache import Cache
from cimri.system.logger import Logger
from cimri.api.cimriservice.data.merchantitem import MerchantItem
from cimri.api.cimriservice.merchants import MerchantsAPI
from cimri.module.update.update import Updater
from cimri.util.text import *

import time

class CimriServiceUpdater(Updater):
        """
	CimriServiceUpdater sistem icindeki diger modullerin belirlenen sonuclarini alir ve CimriService uzerinde 
	belirlenen itemlar icin guncellemeler yapar.

	Modul tarafindan desteklenen islem turleri ve opsiyonlari su sekildedir:

        "update" islemi: belirlenen itemlari Cimri Service'de update eder ya da ekler

                task.data	: islemden gecirilmesi istenilen her item icin "data" o item'in bilgilerini iceren
				  MerchantItem olmalidir (L{cimri.api.cimriservice.merchantitem.MerchantItem})

				  bunun yaninda, her item icin asagidaki veriler de saglanmalidir:

                                  "meta.action"                 : "update" ya da "insert" degerini icermelidir.
								  item uzerinde backendde yapilmasi istenilen
								  operasyonu belirler.

                task.meta       : -

                task.result     : islemden gecirilmesi istenilen her item icin "data" o item icin guncellenmis
				  MerchantItem'dir (L{cimri.api.cimriservice.merchantitem.MerchantItem})

				  bunun yaninda, her item icin asagidaki veriler de saglanir:

                                  "meta.result"	                : "success" ya da "fail" degerlerinden birini icerir

				  "meta.error"			: eger operasyonda bir hata olusursa, hata hakkinda
								  bilgiler icerir

        """

	def __init__(self):
		#initialize parents
		Updater.__init__(self)
		
		self.logger=Logger(self.__class__.__name__)

		#supported operations
		self.ops={"update"	:self._task_update}

		#update chunk size
		self._update_size=1000


	def _task_update(self):
                """
		"update" islemini calistirir
                """

		self.logger.info("api call...")

		#uddater stats
		self.task.stats["data"]["actions"]={"total":0, "insert": 0, "update":0, "clean":0}		

		#get # of workers
		workers=int(self.task.meta["workers"]) if "workers" in self.task.meta else 1

		#oncomplete handler
		def oncomplete():
			#mark as completed
			self._complete()

		#update
		@defer.inlineCallbacks
		def updateitems(items,work):
			#clean task
			data=[item["data"] for item in items if item["meta.action"]=="clean"]
			chunks=int(math.ceil(float(len(data))/self._update_size))
			for index in range(chunks):
				try:
					#update
					res=yield self._clean(data[index*self._update_size:(index+1)*self._update_size])
			
					#check result
	
	                        except Exception as e:
                	                self._log_exception(e,data=None)

				#update progress		
				self._progress()
	
			#update/insert tasks
			data=[item["data"] for item in items if item["meta.action"] in ["insert","update"]]
			chunks=int(math.ceil(float(len(data))/self._update_size))
			for index in range(chunks):
				try:
					#update
					res=yield self._update(data[index*self._update_size:(index+1)*self._update_size])
			
					#check result
	
	                        except Exception as e:
                	                self._log_exception(e,data=None)

				#update progress		
				self._progress()
	
			#next item
			work.next()
			

		#partition data by merchants
		merchants={}
		for item in self.task.data:
			mid=item["data"].merchant["merchantId"]
			if mid not in merchants:
				merchants[mid]=[]
			merchants[mid].append(item)

			#record stats
			self.task.stats["data"]["actions"]["total"]=self.task.stats["data"]["actions"]["total"]+1
			self.task.stats["data"]["actions"][item["meta.action"]]+=1

		#figure out progress
		size=0
		for id in merchants:			
			cleanops=len([item for item in merchants[id] if item["meta.action"]=="clean"])
			size=size+int(math.ceil(float(cleanops)/self._update_size))
			size=size+int(math.ceil(float(len(merchants[id])-cleanops)/self._update_size))

		#initialize progress tracker
		self._progress(size)
			
		#distribute tesk
		d=Distributor(updateitems,oncomplete=oncomplete,workers=workers)
		d.run()
		d.adddata(merchants.values())
		d.complete()	#complete when all data is processed


	def _update(self,items):
                """
		Belirlenen sayida merchant item'i cimri service'de gunceller

                @type  items: list (L{cimri.api.cimriservice.merchantitem.MerchantItem})
                @param items: guncellenmesi istenilen itemlar

                @rtype: L{twisted.internet.defer.Deferred}
                @return: update sonuclarini kabul edicek bir Deferred objecti
                """

		def update_items(items):
			api=MerchantsAPI()
			res=api.update_items(items)	
			if res is False:
				self._log_error("cimriservice update failed")
			return res

		#add timestamp and operator id
		ts=time.strftime("%Y-%m-%d %H:%M:%S",datetime.datetime.now().timetuple())
		for item in items:
			item.lastUpdateDate=ts
			item.operator={"operatorId":0}

		#convert unicode values to string such that utf8 character sequences are interpreted as utf8  
		for item in items:
			item.merchantItemTitle = convert_unicode_to_utf8str(item.merchantItemTitle, item.encoding)
			item.brand = convert_unicode_to_utf8str(item.brand, item.encoding)
			item.modelNameView = convert_unicode_to_utf8str(item.modelNameView, item.encoding)

#			f=open("out.txt","a")
#			f.write(item.merchantItemTitle)
#			f.write("\n")
#			f.close()

		#update
		return deferToThread(update_items,items)


	def _clean(self,items):
                """
		Belirlenen sayida merchant item'in itemid'lerini cimri service'de temizler

                @type  items: list (L{cimri.api.cimriservice.merchantitem.MerchantItem})
                @param items: guncellenmesi istenilen itemlar

                @rtype: L{twisted.internet.defer.Deferred}
                @return: update sonuclarini kabul edicek bir Deferred objecti
                """

		def clean_items(items):
			api=MerchantsAPI()
			res=api.clean_paused_items(items)	
			if res is False:
				self._log_error("cimriservice clean failed")
			return res

		#update
		return deferToThread(clean_items,items)


#bootstrap
if __name__=="__main__":
        #run module
        mod=CimriServiceUpdater()
        args=mod._parse_argv()
        mod._run(**args)
