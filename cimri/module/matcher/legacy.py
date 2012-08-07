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


import time
import os.path
import codecs
import json
from string import Template

from twisted.internet import reactor,defer
from twisted.internet.threads import deferToThread

from cimri.module.module import Distributor
from cimri.module.matcher.matcher import Matcher
from cimri.api.cimriservice.merchants import MerchantsAPI
from cimri.api.cimriservice.data.merchantitem import MerchantItem
from cimri.api.cimriservice.status import CimriStatus
from cimri.api.matcherdb.merchants import MerchantDB
from cimri.api.matcherdb.catalogue import CatalogueDB
from cimri.system.cache import Cache
from cimri.system.config import Config
from cimri.util.text import *

class LegacyMatcher(Matcher):
        """
	Eski cimri matcher sistemindeki algoritmayi kullanan bir matcher modulu. Gelistirme sureci icin yazilmistir, su anda
	desteklenmemektedir.
        """

	def __init__(self):

		super(LegacyMatcher,self).__init__()

		#test mode 
		self.test=False

		#supported operations
                self.ops={"match"    	  	:self._task_match}


	def _task_match(self):
		"""
		"match" islemini calistirir.
                """

                self.logger.info("starting matcher...")

		#get # of workers
		workers=int(self.task.meta["workers"]) if "workers" in self.task.meta else 1

		#run in test mode?
		self.test=("test" in self.task.meta and self.task.meta["test"] is True)  

		#additional stats
		self.task.stats["test"]["guessed"]=0

		#oncomplete handler
		def oncomplete():
			#finalize tests
			if self.test:
				self._test_finalize()
			
			#mark as completed
			self._complete()

		#match items
		self.task.results=[]
		@defer.inlineCallbacks
		def matchitem(item,work):
			try:
				#match
				result=yield self._match_item(item["data"])

				#comparison test
				if self.test:
					#comparet to reference match and update test stats
					self._test_update(result,item["meta.refitem"])		
				
					#include in results
					result["meta.refitem"]=item["meta.refitem"]

				#add to results
				if result["meta.action"] is not None:
					self.task.result.append(result)

		
			except Exception as e:
				data=Template("item(${id}): $url").substitute(id=replace_turkish_chars(item["data"].merchantItemId),url=item["data"].merchantItemUrl)
				self._log_exception(e,data=data)
			
			#update progress		
			self._progress()

			#next item 
			work.next()


		#initialize progress tracker
		self._progress(len(self.task.data))
			
		#distribute tesk
		d=Distributor(matchitem,oncomplete=oncomplete,workers=workers)
		d.run()
		d.adddata(self.task.data)
		d.complete()	#complete when all data is processed



	@defer.inlineCallbacks
	def _match_item(self,item):
                """
		Bir merchant item'i match isleminden gecirir

               	@type   item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
               	@param  item: islemden gecirilmesi istenen merchant item

		@rtype: dict
               	@return: islem sonuclari       
                """

		#get all items for merchant
		merchant_items=yield self._get_merchant_items(item.merchant["merchantId"])
	
		#filter out items that do not have a propoer merchantItemId
		merchant_items=[it for it in merchant_items if it.merchantItemId is not None and it.merchantItemId.strip()!="" ]	

		#set if this is a zero price item or not
		item_zero_price = float(item.pricePlusTax) == 0 
		item_nonzero_price = not item_zero_price
		
		#set as 'update for price' if the item was already on the system
		item_update = None
		item_update_zero_price = None
		for it in merchant_items:
			 if it.merchantItemId==item.merchantItemId:
				item_update=it
				item_update_zero_price = it if int(it.status)==CimriStatus.get_status("PAUSED_BY_CIMRI_ZERO_PRICE").get_code() else None

		#set as new, if this is a new item
		item_new = item if item_update is None else None
		
		#update info for item
		if item_update is not None:
			#update info
			item_update.update(item)

			#update status
			item_update.status=CimriStatus(item_update.status).get_active_status().get_code()

		#if this is a new item, try finding the same merchant item by other merchants
		item_direct_match=None
		if item_new is not None:			
			item_direct_match=yield self._match_direct(item_new, merchant_items)

		#if this is a new item and direct match did not work, try matching against the catalogue
		item_insert=None
		if item_direct_match is None and item_new is not None:
			item_insert=yield self._match_merchant_item(item_new) 

		#update status for 0 price
		if item_zero_price:
			#item_update==item_zero_price
			if item_update is not None:
				item_update.status=CimriStatus.get_status("PAUSED_BY_CIMRI_ZERO_PRICE").get_code()

			#item_direct_match==item_zero_price
			if item_direct_match is not None:
				item_direct_match.status=CimriStatus.get_status("PAUSED_BY_CIMRI_ZERO_PRICE").get_code()

			#item_insert==item_zero_price
			if item_insert is not None:
				item_insert.status=CimriStatus.get_status("PAUSED_BY_CIMRI_ZERO_PRICE").get_code()

		#update status if the price became non-zero
		if item_nonzero_price:
			#item_nonzero_price==item_update_zero_price
			if item_update_zero_price is not None:			
				#if matched before, activate
				if item_update_zero_price.item is not None:
					item_update_zero_price.status=CimriStatus.get_status("ACTIVE").get_code()

				#if not matched before and automatically matched:
				elif item_update_zero_price.possibleSolrItem is not None:
					item_update_zero_price.status=CimriStatus.get_status("SOLR_MATCHED").get_code()

				#otherwise:
				else:
					item_update_zero_price.status=CimriStatus.get_status("PAUSED_BY_CIMRI").get_code()

		#make sure the merchantItemURl and pricePLusTax values are not null for items to be updated/inserted

		#return action and matched item
		item_matched=None
		action=None
		if item_update is not None:
			item_matched=item_update
			action="update"
		elif item_direct_match is not None:
			item_matched=item_direct_match
			action="match"
		elif item_insert is not None:
			item_matched=item_insert
			action="insert"
		
		defer.returnValue({"meta.action":action, "data":item_matched})


	@defer.inlineCallbacks
	def _match_direct(self,item,merchant_items):
		"""
		Bir merchant xml item'i ayni merchantin diger itemlari ile MPN ve Title bilgilerini kullanrak match etmeye calisir

		@type item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
		@param item: match isleminden gecirilmesi istenilen item

		@type merchant_items: list (L{cimri.api.cimriservice.data.merchantitem.MerchantItem})
		@param merchant_items: ayni merchantin diger itemlari
	
		@rtype: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
		@return: match isleminden gecirilmis ve match bilgileri ile guncellenmis merchant item
		"""

		def match_by_mpn(item):
			db=MerchantDB()
			return deferToThread(db.match_by_mpn,item)

		def match_by_title(item):
			db=MerchantDB()
			return deferToThread(db.match_by_title,item)

		#match new item
		match=None

		#match by mpn
		if item.mpnType is not None and item.mpnType.strip()!='' and item.mpnValue is not None and item.mpnValue.strip()!='':
			match=yield match_by_mpn(item)

		#match by title
		if match is None and item.merchantItemTitle!="":
			match=yield match_by_title(item)

		#check and return a match if there was a match and 
		if match is not None:
			itemid=match["itemId"] if "itemId" in match else None
			yield self._add_matching_data(item,itemid,None,True)				
		
		yield None


	@defer.inlineCallbacks
	def _match_merchant_item(self,item):
		"""
		Bir merchant item icin match arar

		@type item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
		@param item: match isleminden gecirilecek item

		@rtype: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
		@return: match isleminden gecirilmis ve match bilgileri ile guncellenmis merchant item
		"""

		def find_brands_in_title(search):
			db=CatalogueDB()
			return deferToThread(db.find_brands_in_title,search)
	
		def match_by_brands(title,brands):
			db=CatalogueDB()
			return deferToThread(db.match_by_brands,title,brands)
			
		#get tokens to find brands for item
		tokens=[]
		if item.brand is not None and item.brand!="":
			tokens.append(item.brand)
		if item.merchantItemTitle is not None and item.merchantItemTitle!="":
			tokens.append(item.merchantItemTitle)
		
		#get search string
		search=" ".join(tokens)
		if search=="":
			yield None
	
		#find brands for item
		brands=yield find_brands_in_title(search)

		#append brand name and model name to the title to assist in matching
		tokens=[]
		if item.brand is not None and item.brand!="":
			tokens.append(item.brand)
		if item.modelNameView is not None and item.modelNameView!="":
			tokens.append(item.modelNameView)
		if item.merchantItemTitle is not None and item.merchantItemTitle!="":
			tokens.append(item.merchantItemTitle)

		#sanitize the match string
		title=lower_non_turkish_alphanumeric(" ".join(tokens))

		#match on title and brands
		match=yield match_by_brands(title,brands)
		
		#anything matched?
		if match==None:
			yield None

		#return match		
		yield self._add_matching_data(item,match["id"],match["score"],False)



	def _add_matching_data(self,item,itemid,score,direct):
                """
		Match edilmis bir merchant item'i match ile ilgili belirli bilgiler ile gunceller

                @type  item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param item: guncellenecek item

		@type itemid: int
		@param itemid: match edilen cimri katalog item IDsi

		@type score: int
		@param score: match skoru

		@type direct: bool
		@param direct: bulunan matchin direk mi (True) ya da possible match mi oldugu

                @rtype: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @return: guncellenmis merchant item
                """

		item.score=score
		if itemid is not None:
			if direct:
				item.item={"itemId":itemid}
				item.status=CimriStatus.get_status("ACTIVE").get_code()
				item.matchDate=time.time()				
			else:
				item.possibleSolrItem={"itemId":itemid}
				item.status=CimriStatus.get_status("SOLR_MATCHED").get_code()

		else:
			item.status=CimriStatus.get_status("PAUSED_BY_CIMRI").get_code()

		#set operator (cron user)
		item.operator=0

		if direct:
			item.matcherType=99
		else:
			item.matcherType=999

		return item


	@defer.inlineCallbacks
	def _get_merchant_items(self,merchantid):
                """
		Belirli bir merchant icin cimri service'den merchant itemlari alir

                @type  merchantid: int
                @param merchantid: merchant ID

                @rtype: list (L{cimri.api.cimriservice.data.merchantitem.MerchantItem})
                @return: istenen merchant itemlari
                """

		def get_merchant_items(merchantid):
			api=MerchantsAPI()
			return deferToThread(api.get_merchant_items,merchantid)

		#check cache
		items=self._get_cached_merchant_items(merchantid)
		if items!=None:
			yield items

		#get from API
		merchant_items=yield get_merchant_items(merchantid)

		#cache
		self._cache_merchant_items(merchant_items,merchantid)

		yield merchant_items


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
		Cache(section).set( "matcher.legacy.items."+str(merchantid),
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
		content=Cache(section).get("matcher.legacy.items."+str(merchantid))
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
        mod=LegacyMatcher()
        args=mod._parse_argv()
        mod._run(**args)
