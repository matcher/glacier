""" 
cimri matcher system
--------------------   
date:                    01.31.2012
author:                  gun@alppay.com

description:
------------

revision history: 
-----------------
gun@alppay.com:          initial version

"""


import os
import codecs
import json
from random import shuffle
from string import Template

from twisted.internet import reactor,defer
from twisted.internet.threads import deferToThread

from cimri.module.module import Distributor
from cimri.module.crawler.product import ProductCrawler
from cimri.api.cimriservice.merchants import MerchantsAPI
from cimri.api.cimriservice.data.merchant import MerchantInfo
from cimri.api.cimriservice.data.merchantitem import MerchantItem
from cimri.api.cimriservice.xml.merchant import MerchantXML

from cimri.system.config import Config
from cimri.system.logger import Logger
from cimri.system.cache import Cache
from cimri.system.web import Web

class ProductXMLCrawler(ProductCrawler,Web):
	"""
	ProductXMLCrawler urun bilgilerini web siteleri dolasarak bulma bakimindan gercek bir crawler degildir.
	Urun bilgilerini Merchant XML'lerden alir, sistem icindeki normal bir web crawlerinin islem akisi
	icinde calistigi ayni seviyede calisir. Sistemin geri kalanina gercek bir crawler olarak gorunur.

	Modul tarafindan desteklenen islem turleri ve opsiyonlari su sekildedir:

	"crawl" islemi: bir ya da daha fazla merchant XML'i tarayarak icinde bulunan merchant itemlari bulur

		task.data	: -

		task.meta	: 
				  "merchants.id"		: aktif merchantlar arasinda aranan cimri-service 
								  merchant IDsi. eger bu opsiyon icin bir deger 
								  verildiyse merchants.index ve merchant.range 
								  opsiyonlari dikkate alinmaz 

       				  "merchants.id.alt"		: butun merchantlar arasinda aranan cimri-service
								  merchant IDsi. eger bu opsiyon icin bir deger 
								  verildiyse merchants.id, merchants.index, ve
								  merchants.range opsiyonlari dikkate alinmaz

       				  "merchants.index"		: aktif merchantlar arasinda crawl islemi
								  icin kullanilacak ilk merchantin indexi.
								  eger bir deger verilmediyse 0 kullanilir

        			  "merchants.range"		: aktif merchantlar arasinda crawl islemi
								  icin kullanilacak merchantlarin sayisi.
								  eger bir deger verilmediye merchants.index
								  indexli merchanttan baslayarak butun merchantlar
								  kullanilir.

        			  "merchants.items.index"	: islem icin kullanilan bir merchantin itemlari 
								  arasinda isleme alinacak ilk itemin indexi.
								  eger bir deger verilmediyse 0 kullanilir.

        			  "merchants.items.range"	: islem icin kullanilan bir merchant icin isleme
								  alinacak itemlarin sayisi. eger bir deger 
								  verilmediyse merchants.items.index indexli
								  itemdan baslayarak butun itemlar isleme alinir.

				  "merchants.all"		: eger bu opsiyon varsa sadece aktif merchantlar
								  degil butun merchantlar islem icin dikkate alinacaktir.

				  "cache.read"			: eger bu opsiyon varsa islem bilgileri cache'den
								  alinacaktir. eger opsiyonun bir degeri varsa
								  cache'in o bolumu kullanilir, eger opsiyonun
								  bir degeri yoksa genel cache kullanilir.

				  "cache.write"			: eger bu opsiyon varsa islem sonuclar cache'e
								  yazilacaktir. eger opsiyonun bir degeri varsa
								  cache'in o bolumu kullanilir, eger opsiyonun
								  bir degeri yoksa genel cache kullanilir.

		task.result	: islem sonucu olarak bulunan her item icin "data" o item'in urli olacaktir.

				  ayrica, her item icin asagidaki meta veriler de sonuclara dahil edilir;

				  "meta.merchantid"		: bulunan item'in mechant IDsi

				  "meta.xmlitem"		: bulunan item bilgilerini iceren MerchantItem
								  L{cimri.api.cimriservice.data.merchantitem.MerchantItem}

	"sample" islemi: bir  merchant XML'i tarayarak random bir sayida merchant item bulur.
			 cesitli testler icin ornek veriler yaratmak icin kullanilir.

		task.data	: -

		task.meta	:
				  "merchants.id"		: aktif merchantlar arasinda aranan cimri-service 
								  merchant IDsi. eger bu opsiyon icin bir deger 
								  verildiyse merchants.index ve merchant.range 
								  opsiyonlari dikkate alinmaz 
       			
				  "sample.size"			: bulunmasi istenilen item sayisi 
                                
				  "cache.read"			: eger bu opsiyon varsa islem bilgileri cache'den
								  alinacaktir. eger opsiyonun bir degeri varsa
								  cache'in o bolumu kullanilir, eger opsiyonun
								  bir degeri yoksa genel cache kullanilir.

				  "cache.write"			: eger bu opsiyon varsa islem sonuclar cache'e
								  yazilacaktir. eger opsiyonun bir degeri varsa
								  cache'in o bolumu kullanilir, eger opsiyonun
								  bir degeri yoksa genel cache kullanilir.

		task.result	: islem sonucu olarak bulunan her item icin "data" o item'in urli olacaktir.

				  ayrica, her item icin asagidaki meta veriler de sonuclara dahil edilir;

				  "meta.merchantid"		: bulunan item'in mechant IDsi

				  "meta.xmlitem"		: bulunan item bilgilerini iceren MerchantItem
								  L{cimri.api.cimriservice.data.merchantitem.MerchantItem}

	"get"   islemi: belirtilen merchant item'lar icin merchant XML'lerinden MerchantItem bilgilerini bulur

                task.data      	: bulunmasi istenen her item icin "data" o item'in merchantId ve merchantItemId'sini
				  iceren MerchantItem objecti olmalidir (L{cimri.api.cimriservice.data.merchantitem.MerchantItem})

		task.meta	: 
				  "cache.read"			: eger bu opsiyon varsa islem bilgileri cache'den
								  alinacaktir. eger opsiyonun bir degeri varsa
								  cache'in o bolumu kullanilir, eger opsiyonun
								  bir degeri yoksa genel cache kullanilir.

				  "cache.write"			: eger bu opsiyon varsa islem sonuclar cache'e
								  yazilacaktir. eger opsiyonun bir degeri varsa
								  cache'in o bolumu kullanilir, eger opsiyonun
								  bir degeri yoksa genel cache kullanilir.

		task.result	: islem sonucu olarak bulunan her item icin "data" o item'in urli olacaktir.

				  ayrica, her item icin asagidaki meta veriler de sonuclara dahil edilir;

				  "meta.merchantid"		: bulunan item'in mechant IDsi

				  "meta.xmlitem"		: bulunan item bilgilerini iceren MerchantItem
								  L{cimri.api.cimriservice.data.merchantitem.MerchantItem}

	"discover" islemi: kullanilmamaktadir.


	"""
	def __init__(self):
		Web.__init__(self)
		ProductCrawler.__init__(self)

                self.logger=Logger(self.__class__.__name__)
	
		#supported operations
		self.ops={"discover":	self._task_discover,
			  "crawl":	self._task_crawl,
			  "sample":	self._task_sample,
			  "get":	self._task_get}		


	def _task_discover(self):
                """
		Kullanilmiyor
                """

		pass


	def _task_crawl(self):
                """
		"crawl" isini calistirir
		"""

		self.logger.info("starting crawler...")

		#get number of workers
		workers=int(self.task.meta["workers"]) if "workers" in self.task.meta else 1
		
		#get list of merchants according to task 
		#parmeters: range, status,...
		allmerchants=("merchants.all" in self.task.meta and self.task.meta["merchants.all"] is True)
		merchants=self._get_merchants( allmerchants )


		#get range to operate on
		if "merchants.id.alt" in self.task.meta:
			merchants=[merchant for merchant in merchants if str(merchant.merchantId)==str(self.task.meta["merchants.id.alt"])]
		elif "merchants.id" in self.task.meta:
			merchants=[merchant for merchant in merchants if str(merchant.merchantId)==str(self.task.meta["merchants.id"])]
		else:
			if "merchants.index" in self.task.meta:
				merchants=merchants[int(self.task.meta["merchants.index"]):]
			if "merchants.range" in self.task.meta:
				merchants=merchants[:int(self.task.meta["merchants.range"])]

		#progress steps for each merchant
		steps=10000

		#check items
		@defer.inlineCallbacks
		def checkitems(merchant,work):
			try:
				#reet progress counter
				counter=steps 

				#get items for merchant
				try:
					items=yield self._get_merchant_items(merchant)		
				except:
					items=None
				if items is None:
					self._log_error("failed to load merchant xml "+MerchantXML(merchant).geturl())
					items=[] #TEMP workaround to make sure task completes			

				#progress counter size
				stepby=steps if len(items)==0 else float(steps)/len(items)

				#get range to operate on
				if "merchants.items.index" in self.task.meta:
					items=items[int(self.task.meta["merchants.items.index"]):]
				if "merchants.items.range" in self.task.meta:
					items=items[:int(self.task.meta["merchants.items.range"])]

				#check items
				for item in items:
					#TEMP - do not check
					#check page
					#res=yield self._check_item(item)
					res=True
						
					#set task result
					if res:
						self.task.result.append({"data":item.merchantItemUrl, "meta.merchantid":merchant.merchantId, "meta.xmlitem":item})
					else:
						msg=Template("item(${id}) url could not verified: $url").substitute(id=str(item.merchantItemId),url=item.merchantItemUrl)
						self._log_error(msg)

					self._progress(stepby=stepby)
					counter=counter-stepby

			except Exception as e:
				data=Template("exception while processing merchant(${id}): $url").substitute(id=str(merchant.merchantId),url=MerchantXML(merchant).geturl())
				self._log_exception(e,data=data)
				self._fail()				
			
			#update progress		
			self._progress(stepby=counter)

			#next item
			work.next()

		#initialize progress tracker
		self._progress(len(merchants)*steps)
			
		#start task distributor
		d=Distributor(checkitems,oncomplete=self._complete,workers=workers)
		d.run()

		#process each merchant
		d.adddata(merchants)

		#when done processing all data
		d.complete()		




	@defer.inlineCallbacks
	def _task_sample(self):
                """
		"sample" isini calistirir
		"""

		self.logger.info("starting crawler 'sample' task...")

		#get number of workers
		workers=int(self.task.meta["workers"]) if "workers" in self.task.meta else 1

		#get list of merchants 
		merchants=self._get_merchants()
			
		#apply filters
		if "merchants.id" in self.task.meta:
			merchants=[merchant for merchant in merchants if str(merchant.merchantId).strip()==str(self.task.meta["merchants.id"]).strip()]
		self.count=int(self.task.meta["sample.size"]) if "sample.size" in self.task.meta else 100

		#process each merchant
		for merchant in merchants:
			try:
				#get items for merchant
				items=yield self._get_merchant_items(merchant)
				if items is None:
					self._log_error("failed to load merchant xml "+MerchantXML(merchant).geturl())
					items=[] #TEMP workaround to make sure task completes			

				#shuffle the items
				shuffle(items)

				#check items
				@defer.inlineCallbacks
				def checkitem(item,work):
					try:
						#check page
						res=yield self._check_item(item)

						#check if task was completed while we were waiting to get the item
						if work.isactive():
							if res:
								#set task result
								self.task.result.append({"data":item.merchantItemUrl, "meta.merchantid":merchant.merchantId, "meta.xmlitem":item})

								#update progress		
								self._progress()
							
								#done?
								self.count=self.count-1
								if self.count<1:
									work.complete()
						
							else:
								msg=Template("item(${id}) url could not verified: $url").substitute(id=str(item.merchantItemId),url=item.merchantItemUrl)
								self._log_error(msg)

					except Exception as e:
						data=Template("exception while processing item(${id}): $url").substitute(id=str(merchant.merchantId),url=item.merchantItemUrl)
						self._log_exception(e,data=data)

					#next item
					work.next()
	
				#initialize progress tracker
				self._progress(self.count)

				#distribute tesk
				d=Distributor(checkitem,oncomplete=self._complete,workers=workers)
				d.run()
				d.adddata(items)
				d.complete()		#when done processing all data

			except Exception as e:
				data=Template("exception while processing merchant(${id}): $url").substitute(id=str(merchant.merchantId),url=MerchantXML(merchant).geturl())
				self._log_exception(e,data=data)
				self._fail()
		

	def _task_get(self):
                """
		"get" isini calistirir
		"""

		self.logger.info("starting crawler...")

		#get number of workers
		workers=int(self.task.meta["workers"]) if "workers" in self.task.meta else 1
		
		#get merchant ids we're looking for 
		merchantids=list(set([it.merchant["merchantId"] for it in self.task.data]))

		#get list of merchants according to task 
		merchants=[]
		for id in merchantids:
			merchant=self._get_merchant(id)
			if merchant is not None:
				merchants.append(merchant)				

		#worker to check items
		@defer.inlineCallbacks
		def checkitems(merchant,work):
			try:
				#get item ids we're looking for 
				ids=[it.merchantItemId for it in self.task.data if it.merchant["merchantId"]==merchant.merchantId]

				#get items for merchant
				items=yield self._get_merchant_items(merchant)
				if items is None:
					self._log_error("failed to load merchant xml "+MerchantXML(merchant).geturl())
					items=[] #TEMP workaround to make sure task completes		
	
				#get merchant items to sample for merchant
				items=[item for item in items if item.merchantItemId in ids]
				
				#process items
				for item in items:
					#TEMP - do not check
					#check page
					#res=yield self._check_item(item)
					res=True				
		
					#set task result
					if res:
						self.task.result.append({"data":item.merchantItemUrl, "meta.merchantid":merchant.merchantId, "meta.xmlitem":item})
					else:
						msg=Template("item(${id}) url could not verified: $url").substitute(id=str(item.merchantItemId),url=item.merchantItemUrl)
						self._log_error(msg)

					#update progress		
					self._progress()

			except Exception as e:
				data=Template("exception while processing merchant(${id}): $url").substitute(id=str(merchant.merchantId),url=MerchantXML(merchant).geturl())
				self._log_exception(e,data)
							
			#next item
			work.next()

		#initialize progress tracker
		self._progress(len(self.task.data))
			
		#start task distributor
		d=Distributor(checkitems,oncomplete=self._complete,workers=workers)
		d.run()

		#process each merchant
		d.adddata([merchant for merchant in merchants if merchant.merchantId in merchantids])

		#when done processing all data
		d.complete()		


	def _get_merchants(self, all=False):
                """
		Cimri Service'den merchantlarin listesini alir

		@type all:	bool
		@param all:	eger dogru ise butun merchantlar alinir, aksi takdirde sadece aktif merchantlar alinir

		@rtype:	list (L{cimri.api.cimriservice.data.merchant.MerchantInfo})
		@return: merchant listesi
                """

		self.logger.info("getting merchants...")

		#get active merchants
        	api=MerchantsAPI()
		if all is True:
			merchants=api.get_merchants()
		else:
			merchants=api.get_merchants(status=MerchantInfo.STATUS_ACTIVE)
        	if merchants is None:
			self._log_error("error getting cimri service merchant list")
			self.logger.warn("did not get any merchants from cimri-service")
                	return []
       
		self.logger.info("number of merchants retrieved: "+str(len(merchants)))

		#get only the active ones
       		#merchants=[merchant for merchant in merchants if merchant.status==MerchantInfo.STATUS_ACTIVE]

		self.logger.info("number of active merchants found: "+str(len(merchants)))

		return merchants


	def _get_merchant(self,id):
                """
		Cimri service'den belli bir merchanti alir

		@type id: str
		@param id: merchant ID

		@rtype: L{cimri.api.cimriservice.data.merchant.MerchantInfo}
		@return: MerchantInfo objecti
                """

		self.logger.info("getting merchant..."+str(id))

		#get active merchants
        	api=MerchantsAPI()
		merchant=api.get_merchant(id)
        	if merchant is None:
			self._log_error("error getting cimri service merchant "+str(id))
			self.logger.warn("did not get merchant from cimri-service")
                	return None
       
		return merchant


	def _get_merchant_items(self,merchant):
                """
		Bir merchant icin butun merchant itemlari asynchronous olarak cimri serviceden alir

		@type merchant:	L{cimri.api.cimriservice.data.merchant.MerchantInfo}
		@param merchant: itemlari istenen merchant

		@rtype: L{twisted.internet.defer.Deferred}
		@return: merchant itemlarin yollanacagi Deferred
                """
	
		return deferToThread(self._get_merchant_items_async,merchant)


	def _get_merchant_items_async(self,merchant):
                """
		Bir merchant icin butun merchant itemlari cimri serviceden alir

		@type merchant:	L{cimri.api.cimriservice.data.merchant.MerchantInfo}
		@param merchant: itemlari istenen merchant

                @rtype: list (L{cimri.api.cimriservice.data.merchantitem.MerchantItem})
                @return: istenen merchant itemlar
                """

		self.logger.info("getting merchant items for ... "+str(merchant.merchantId)+":"+merchant.merchantName)

                #check cache
       		items=self._get_cached_merchant_items(merchant.merchantId)
               	if items is None:
			#load items for merchant
		        xml=MerchantXML(merchant)
	       		res=xml.load()
			if res is False:
				return None

	        	#get items
			items=xml.getitems()

	       	     	#cache
            		self._cache_merchant_items(items,merchant.merchantId)

		#add merchant id
		for item in items:
			item.merchant={"merchantId":merchant.merchantId}

		return items


	def _check_item(self,item):
		"""
		Bir merchant item'a ait URL'in erisilir olup olmadigini asynchronous olarak kontrol eder

                @type item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param item: kontrol edilmesi istenen merchant item

		@rtype: L{twisted.internet.defer.Deferred}
		@return: operasyon sonucunun yollanacagi Deferred
		"""

		return deferToThread(self.ping,item.merchantItemUrl)


        def _cache_merchant_items(self,items,merchantid):
                """
		Belirlenen merchant itemlari cache'e kayit eder

                @type items: list (L{cimri.api.cimriservice.data.merchantitem.MerchantItem})
                @param items: kayit edilmesi istenen merchant itemlar

                @type merchantid: str
                @param merchantid: itemlarin ait oldugu merchantin IDsi
                """

		#check if we should cache
		if "cache.write" not in self.task.meta:
			return

		#get section to cache to
		section=self.task.meta["cache.write"]
			
		#write to cache
		Cache(section).set( "crawler.productxml.items."+str(merchantid),
				    json.dumps([item.to_dict() for item in items]) )


        def _get_cached_merchant_items(self,merchantid):
                """
		Belirli bir merchant icin cache'de kayitli merchant itemlari alir

                @type merchantid: str
                @param merchantid: itemlarin ait oldugu merchantin IDsi

                @rtype: list (L{cimri.api.cimriservice.data.merchantitem.MerchantItem})
                @return: cache'de bulunan itemlarin listesi. cache bolumu yoksa ya da bir hata olusursa None
                """

		#check if we should use the cache
		if "cache.read" not in self.task.meta:
			return None

		#get section to use
		section=self.task.meta["cache.read"]

		#read cache
		content=Cache(section).get("crawler.productxml.items."+str(merchantid))
		if content is None:
			return None

		#parse
                try:
                        return MerchantItem.list_from_json(content,[])

                except Exception as e:
                        return None


#bootstrap
if __name__=="__main__":
        #run module
        mod=ProductXMLCrawler()
        args=mod._parse_argv()
        mod._run(**args)
