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


import os.path
import codecs
import json
import math
import pprint
from string import Template

from twisted.internet import reactor,defer
from twisted.internet.threads import deferToThread
from twisted.internet.defer import Deferred

from cimri.module.module import Distributor
from cimri.module.matcher.matcher import Matcher
from cimri.api.cimriservice.merchants import MerchantsAPI
from cimri.api.cimriservice.data.merchantitem import MerchantItem
from cimri.api.cimriservice.status import CimriStatus
from cimri.api.matcherdb.merchants import MerchantDB,AsyncMerchantDB,AsyncMerchantBlackListDB
from cimri.api.matcherdb.catalogue import CatalogueDB,AsyncCatalogueDB
from cimri.system.cache import Cache
from cimri.system.config import Config
from cimri.util.text import *
from cimri.api.analytics.matcher import MatchRecord

import time

class MetaMatcher(Matcher):
        """
	Sistem tarafindan kullanilan matcher algoritmasi ve islemleri

	Modul tarafindan desteklenen islem turleri ve opsiyonlari su sekildedir:

        "match" islemi: belirlenen merchant itemlarini cimri service katalog itemlari ile eslestirir.
        "match-update" islemi: belirlenen merchant itemlarini sadece guncelleme amacli olarak islemden gecirir
        "match-insert" islemi: belirlenen merchant itemlarini sadece yeni match bulma amacli olarak islemden gecirir
        "match-sim" islemi: belirlenen merchantlarin sistemde daha once match olmus itemlarinini cimri service katalog itemlari 
			    ile eslestirir ve match sonuclarini daha once var olan match sonuclari ile karsilastirark test
			    sonuclari olarak kayit eder.			

                task.data       : 
  				  "data"			: match edilecek MerchantItem
								  L{cimri.api.cimriservice.data.merchantitem.MerchantItem}

                                  "meta.refitem" 	        : test islemlerinde referans olarak kullanilacak MerchantItem
								  L{cimri.api.cimriservice.data.merchantitem.MerchantItem}

                task.meta       : 
				  "cache.read"			: eger bu opsiyon varsa islem bilgileri cache'den
								  alinacaktir. eger opsiyonun bir degeri varsa
								  cache'in o bolumu kullanilir, eger opsiyonun
								  bir degeri yoksa genel cache kullanilir.

				  "cache.write"			: eger bu opsiyon varsa islem sonuclar cache'e
								  yazilacaktir. eger opsiyonun bir degeri varsa
								  cache'in o bolumu kullanilir, eger opsiyonun
								  bir degeri yoksa genel cache kullanilir.

                 		  "untrained"			: eger bu opsiyon varsa, ogernilmis egitim bilgileri
								  kullanilmaz

				  "test"			: eger bu opsiyon varsa, saglanan referans bilgilerine
								  dayanarak test islemi yapilir ve sonuclar kayit edilir.

				  "test.uuid"			: test data referans IDsi

				  "merchant.update"		: eger bu opsiyon varsa, cimri service merchantlarin
								  xml'den gelmeyen itemlari cimri service'de update edilecek
								  sekilde islem sonuclarina eklenir.

				  "match.unmatched"		: eger bu opsiyon varsa, sadece daha once match olmamis
								  itemlar match operasyonundan gecirilir.

				  "match.constrain"		: eger bu opsiyon varsa, ayni merchantin baska itemlari ile
								  match olmus cimri katalog itemlari match islemlerinde 
								  dikkate alinmaz.

                task.result     : her match sonucu icin "data" o sonuc ile ilgili guncellenmesi gereken bilgileri iceren
				  MerchantItem objectini icerir (L{cimri.api.cimriservice.data.merchantitem.MerchantItem})

				  ayni zamanda her item icin sonuclar arasinda asagidaki bilgiler de bulunur:

                                  "meta.action"            : cimri service update islemleri icin "update" ya da "insert"
							     direktifini icerir

				  "meta.refitem" 	   : eger calistirilan islem bir test islemi ise test icin kullanilan
							     referans MerchantItem'i icerir.

        """

	colors=["kirmizi","mavi","sari","siyah","beyaz","yesil","gri","turuncu","mor","bej","kahverengi","pembe","lacivert"]

	product_type_disqualifiers=[('toner','toneri','kartus','kartusu'),
 				    ('kablo','kablosu')
				   ]


	def __init__(self):
		super(MetaMatcher,self).__init__()

		#supported operations
                self.ops={"match"    	  	:self._task_match,
             		  "match-sim"    	:self._task_match,
             		  "match-update"    	:self._task_match,
             		  "match-insert"    	:self._task_match
			 }


	def _reset(self):
                """
		Match islemleri icin kullanilan parametreleri reset eder.
                """

		#merchant items and matches that are already in cimri service 
		self._merchant_items={}
		self._merchant_matches={}
		self._item_matches={}

		#run in test mode?
		self.test=("test" in self.task.meta and self.task.meta["test"] is True) or self.task.op=="match-sim" 

		#update merchant?
		self.merchant_update=("merchant.update" in self.task.meta and self.task.meta["merchant.update"] is True)

		#only match unmatched?
		self.match_unmatched=("match.unmatched" in self.task.meta and self.task.meta["match.unmatched"] is True)

		#constrain match (only valid if match.unmatched is also selected)
		self.match_constrain=("match.constrain" in self.task.meta and self.task.meta["match.constrain"] is True)


	def _reset_stats(self):
                """
		Match islemlerinde takip edilen istatistikleri reset eder.
                """

		#matcher stats - direct matchs
		self.task.stats["data"]["matched"]={"total":0, "insert": 0, "update":0, "matched_same":0, "matched_diff":0, "matched_to_active":0, "duplicate":0, "zero_price":0}

		#matcher stats - possible matches
		self.task.stats["data"]["guessed"]={"total":0, "insert": 0, "update":0, "guessed_same":0, "guessed_diff":0, "zero_price":0}	

		#matcher stats - no matches
		self.task.stats["data"]["nomatch"]={"total":0, "insert": 0, "matched":0, "blacklist": 0, "newitem":0, "zero_price":0}		

		#matcher stats - info updates only (status and all fields that can be updated)
		self.task.stats["data"]["updates"]={"total":0}		

		#additional stats - testing
 		self.task.stats["test"]["guessed"]=0
 		self.task.stats["test"]["badguess"]=0
		self.task.stats["test"]["match_percent"]=0
		self.task.stats["test"]["guess_percent"]=0
		self.task.stats["test"]["guess_accuracy"]=0

		#{scores:[], match:bool, direct:bool, success:bool, ref:id} 
		self.task.stats["test"]["matches"]=[]	



	@defer.inlineCallbacks
	def _task_match(self):
		"""
		Modul tarafindan desteklenen cesitli match islemlerini yapar.
                """

                self.logger.info("starting matcher...")

		#reset all working data
		self._reset()

		#reset stats
		self._reset_stats()

		#get # of workers
		workers=int(self.task.meta["workers"]) if "workers" in self.task.meta else 1
		
		#oncomplete handler
		def oncomplete():
			#finalize tests
			if self.test:
				self._test_finalize()

			#reset all working data to free memory
			self._reset()

			#mark as completed
			self._complete()


		#match items
		self.task.result=[]
		@defer.inlineCallbacks
		def processitem(item,work):
			try:
				#ref item
				ref=item["meta.refitem"] if "meta.refitem" in item else None

				#match
				result=yield self._process_item(item["data"],ref)

				#comparison test
				if self.test:
					#compare to reference match and update test stats
					self._test_update(result,item["meta.refitem"])		
				
					#include in results
					result["meta.refitem"]=item["meta.refitem"]

				#add to results
				if result["meta.action"] is not None:
					self.task.result.append(result)

			except Exception as e:
				data=Template("item(${id}): $url").substitute(id=repr(replace_turkish_chars(item["data"].merchantItemId)),url=item["data"].merchantItemUrl)
				self._log_exception(e,data=repr(data))

			#update progress		
			self._progress()

			#next item
			work.next()

		#initialize progress tracker
		self._progress(len(self.task.data))
			
		#distribute tesk
		d=Distributor(processitem,oncomplete=oncomplete,workers=workers)
		d.run()

		#process each merchant
		@defer.inlineCallbacks
		def process_merchant_items():
			#clear merchant item cache
			self._merchant_items={}		#items by merchant (from cimri)
			self._merchant_matches={}	#items that each merchant already has an item matched to on the cimri side
			self._item_matches={}		#list of merchant items matched to the same cimri item during this task
	
			#get all existing merchant items from the cimri service
			def get_merchant_items(id):	
				def get_merchant_items_async(id):		
					api=MerchantsAPI()
					res=api.get_merchant_items(id)
					if res is None:
						self._log_error("error getting cimri service merchant items for merchant "+str(id))
					return res

				return deferToThread(get_merchant_items_async,id)

			#get all merchants in this task
			for item in self.task.data:
				id=item["data"].merchant["merchantId"]
				if id not in self._merchant_items:
					self._merchant_items[id]={}

			#for each merchant in this task, get all merchant items from the cimri service
			for id in self._merchant_items:
				#get cimri merchant items
				items=yield get_merchant_items(id)
				items=items if items is not None else []	#cimri service returns a 204 when the merchant has no items in cimriservice

				#store items in a format that can be looked up fast
				for it in items:
					self._merchant_items[id][it.merchantItemId]=it
					if it.is_matched():
						self._merchant_matches[id+"-"+it.item["itemId"]]=True

				#get items for merchant for match task
				data=[]
				if self.task.op=="match-sim":
					#if this is a simulation test, only add items if they are already active and matched
					for item in (it for it in self.task.data if it["data"].merchant["merchantId"]==id):
						citem=self._get_cimri_merchant_item(item["data"])
						if citem is not None and str(CimriStatus(citem.status))=="ACTIVE" and citem.is_matched():
							data.append({"data":item["data"],"meta.refitem":citem})

				else:
					#add all items to task for a regular match task
					data=[item for item in self.task.data if item["data"].merchant["merchantId"]==id]

				#add data to match task
				d.adddata(data)

				#update merchant items that are not in the provided data set
				if self.merchant_update:
					items=self._merchant_update(id,data)				
					self.task.result.extend(items)

		#process merchant items for each merchant
		yield process_merchant_items()

		#complete when all data is processed		
		d.complete()	


	def _get_cimri_merchant_item(self,item):
                """
		Bir MerchantItem icin cimri sisteminde varolan MerchantItem kopyasini alir

                @type  item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param item: merchant item

                @rtype: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @return: cimri serviste bulunan merchant item ya da item cimri servicete yok ise None
                """

		if item.merchant["merchantId"] not in self._merchant_items:
			return None
		if item.merchantItemId not in self._merchant_items[item.merchant["merchantId"]]:
			return None
		return self._merchant_items[item.merchant["merchantId"]][item.merchantItemId]


	def _check_existing_match(self,merchantid,itemid):
                """
		Bir merchant item icin cimri serviste daha onceden bir match olup olmadigini kontrol eder

                @type  merchantid: str
                @param merchantid: merchant IDsi

                @type  itemid: str
                @param itemid: merchant item IDsi

                @rtype: bool
                @return: eger item icin bir match varsa True, yoksa False
                """

		return ((str(merchantid)+"-"+str(itemid)) in self._merchant_matches)		


	def _check_duplicate_match(self,merchantid,itemid,score):
                """
		Match islemi sirasinda bir merchant item'in ayni merchantin baska bir item'i ile ayni cimri katalog itemina match
		olup olmadigini kontrol eder. Eger ayni match varsa ve yeni match olan item daha iyi bir match ise, bir onceki
		match dikkate alinmaz.

                @type  merchantid: str
                @param merchantid: merchant IDsi

                @type  itemid: str
                @param itemid: merchant item IDsi

                @type  score: int
                @param score: match skoru

                @rtype: bool
                @return: eger belirtilen item icin bulunan match gecerli ise True, degilse False
                """

		#get key
		key="-".join([merchantid,itemid])

		#check if an item for this merchant was already matched to the same cimri item
		if key in self._item_matches:
			#compare scores to determine which is the better match	
			if score > self._item_matches[key].score:
				#remove the previously matched item from results
				for result in self.task.result:
					if result["data"]==self._item_matches[key]:
						self.task.result.remove(result)
						self.task.stats["data"]["matched"]["duplicate"]=self.task.stats["data"]["matched"]["duplicate"]+1
						if result["meta.action"]=="insert":
							self.task.stats["data"]["matched"]["insert"]=self.task.stats["data"]["matched"]["insert"]-1
						else:
							self.task.stats["data"]["matched"]["update"]=self.task.stats["data"]["matched"]["update"]-1

						break
			else:
				return False
			
		return True


	@defer.inlineCallbacks
	def _process_item(self,item,refitem):
                """
		Bir merchant item'i match isleminden gecirir

                @type item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param item: islemden gecirilecek merchant item

                @type refitem: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param refitem: test islemleri icin referans bilgilerini iceren merchat item

                @rtype: dict
                @return: match sonuclari ve bilgileri
                """

		def find_colors(keywords):
			text=lower_non_turkish_alphanumeric(" ".join(keywords))
			return set( [color for color in MetaMatcher.colors if text.find(color)>-1 ]  )
	
		def match_by_title_keywords(keywords):
			#mdb=MerchantDB()
			#return deferToThread(mdb.match_by_title_keywords,keywords)
			result=Deferred()
			mdb=AsyncMerchantDB()
			res=mdb.match_by_title_keywords(keywords)
			def success(res):
				result.callback(res)
			def fail(err):	
				self._log_error("cimri-solr-mi call failed: match_by_title_keywords ("+repr(keywords)+")")
				result.callback([])
			res.addCallback(success)
			res.addErrback(fail)
			return result


		def match_by_title_keywords_blacklist(keywords):
			#mdb=MerchantDB()
			#return deferToThread(mdb.match_by_title_keywords,keywords)
			result=Deferred()
			mdb=AsyncMerchantBlackListDB()
			res=mdb.match_by_title_keywords(keywords)
			def success(res):
				result.callback(res)
			def fail(err):	
				self._log_error("cimri-solr-mi-bl call failed: match_by_title_keywords ("+repr(keywords)+")")
				result.callback([])
			res.addCallback(success)
			res.addErrback(fail)
			return result


		def match_by_model(keywords):
			#cdb=CatalogueDB()
			#return deferToThread(cdb.match_by_model,keywords)
			result=Deferred()
			mdb=AsyncCatalogueDB()
			res=mdb.match_by_model(keywords)
			def success(res):
				result.callback(res)
			def fail(err):	
				self._log_error("cimri-solr call failed: match_by_model ("+repr(keywords)+")")
				result.callback([])
			res.addCallback(success)
			res.addErrback(fail)
			return result

		def match_by_keywords(keywords):
			#cdb=CatalogueDB()
			#return deferToThread(cdb.match_by_keywords,keywords)
			result=Deferred()
			mdb=AsyncCatalogueDB()
			res=mdb.match_by_keywords(keywords)
			def success(res):
				result.callback(res)
			def fail(err):	
				self._log_error("cimri-solr call failed: match_by_keywords ("+repr(keywords)+")")
				result.callback([])
			res.addCallback(success)
			res.addErrback(fail)
			return result

		def match_by_ids(ids):
			result=Deferred()
			mdb=AsyncCatalogueDB()
			res=mdb.match_by_ids(ids)
			def success(res):
				result.callback(res)
			def fail(err):	
				self._log_error("cimri-solr call failed: match_by_ids ("+repr(ids)+")")
				result.callback([])
			res.addCallback(success)
			res.addErrback(fail)
			return result

		def match_by_mpn(keywords):
			result=Deferred()
			mdb=AsyncCatalogueDB()
			res=mdb.match_by_mpn(keywords)
			def success(res):
				result.callback(res)
			def fail(err):	
				self._log_error("cimri-solr call failed: match_by_mpn ("+repr(keywords)+")")
				result.callback([])
			res.addCallback(success)
			res.addErrback(fail)
			return result

		def get_mismatch_categories(title):	
			def get_mismatch_categories_async(title):		
				api=MerchantsAPI()
				res=api.get_mismatch_categories(title)
				if res is None:
					self._log_error("error getting cimri service mismatch categories for title "+str(title))
				return res

			title=replace_turkish_chars(title)
			return deferToThread(get_mismatch_categories_async,title)

		def model_keywords(model,meta):
			keywords=[]

			#preprocess the model name and the meta string
			model_processed=remove_non_alphanumeric(lower_non_turkish_alphanumeric(model))
			meta_processed=remove_non_alphanumeric(lower_non_turkish_alphanumeric(meta))
	
			#get the keywords as they are found in the model name			
			keywords.extend([key.strip() for key in model.split(" ") if key.strip()!=""])

			#get keywords after removing non-alphanumeric
			keywords.extend([key.strip() for key in model_processed.split(" ") if key.strip()!=""])

			#find words in model name that are also in the title (to detect cases where the model name
			#is in a concatenated format. ie: IXUS 130 appears as IXUS130 in the model name
			tokens=[key.strip() for key in meta_processed.split(" ") if key.strip()!=""]
			for token in tokens:
				if model_processed.find(token)>-1:
					keywords.append(token)

			return keywords

		def compare_merchant_item_ids(item,id):
			return replace_turkish_chars(unicode(item.merchantItemId))==replace_turkish_chars(unicode(id))

		def validate_brand(item, match):
			#get the lowercase text for both brand strings
			text_item=replace_turkish_chars(item.brand).lower().strip()
			text_match=replace_turkish_chars(match["brand"]).lower().strip()

			#ignore certain keywords
			if text_item in ["kitap","digeri"]:
				text_item=""
			if text_match in ["kitap","digeri"]:
				text_match=""

			#check exact match
			if text_item==text_match:
				return True

			#tokenize
			tokens_item=tokenize_alphanumeric(text_item)
			tokens_match=tokenize_alphanumeric(text_match)

			#check for word order (ie: "fisher price" vs "price fisher")
			if set(tokens_item)==set(tokens_match):
				return True

			#check for different tokenization and punctuation 
			#(ie: "baby max" vs "babymax", "eca" vs "e.c.a", "gskill" vs "g.skill", "k's kids" vs "ks kids")
			if "".join(tokens_item)=="".join(tokens_match):
				return True

			#check for abbreviations and shortened names
              		#(ie: "philips avent" vs "p.avent", "asus" vs "asustek", "beko" vs "lg beko", "f-secure" vs "secure"
			for token in [t for t in tokens_item if len(t)>3]:
				if token in tokens_match:
					return True
			for token in [t for t in tokens_match if len(t)>3]:
				if token in tokens_item:
					return True

			#check for missellings
			#"whirpoll" vs "whirlpool", "elecrtolux" vs "electrolux", "plantronic" vs "plantronics", "bambino" vs "bambini"
			if similarity(text_item,text_match)>0.7:
				return True

			return False

		def check_product_type_match(itemtitle,matchtitle):
			#get item title keywords
			words=lower_non_turkish_alphanumeric(itemtitle).split(" ")
			words=[word.strip() for word in words]			
	
			#find qualifiers
			item_qualifiers=[]
			for word in words:
				for disqualifier in MetaMatcher.product_type_disqualifiers:
					for dword in disqualifier:
						if word==dword.lower():
							item_qualifiers.append(disqualifier)
							break

			#get match title keywords
			words=lower_non_turkish_alphanumeric(matchtitle).split(" ")
			words=[word.strip() for word in words]			

			#find qualifiers
			match_qualifiers=[]
			for word in words:
				for disqualifier in MetaMatcher.product_type_disqualifiers:
					for dword in disqualifier:
						if word==dword.lower():
							match_qualifiers.append(disqualifier)
							break

			return set(item_qualifiers)==set(match_qualifiers)

		def spread(matches):
			diff=matches[0]["score"]-(matches[1]["score"] if len(matches)>1 else 0)
			if len(matches)>1:
				divisor=(float( sum([m["score"] for m in matches[1:5]]) )/len(matches[1:5]))
				margin=diff if divisor==0 else diff/(float( sum([m["score"] for m in matches[1:5]]) )/len(matches[1:5]))		
			else:
				margin=diff
			return margin
			
		def margin(matches):
			if len(matches)>1:
				return matches[0]["score"]-matches[1]["score"]
			else:
				return matches[0]["score"]

		def stddev(values):
			avg=float(sum(values))/len(values)
			sd=math.sqrt( float(sum([math.pow(val-avg,2) for val in values]))/len(values) )
			return sd

		def grouping(matches,deviation,distance):
			#detect how many of the top matches are close enough within a certain standard 'deviation'
			#and 'distance' from the next match
			for index in reversed(range(len(matches))):
				#if we're looking at the first match, the search has failed
				if index==0:
					return 0

				#number of top matches we're evaluating
				n=index+1

				#get scores for top n matches
				scores=[m["score"] for m in matches[:n]]					

				#get standard deviation
				sd=stddev(scores)

				#check standard deviation
				if sd>deviation:
					continue

				#get the score for the next match after the top n matches
				if len(matches)==n:
					nextscore=0
				else:
					nextscore=matches[n]["score"]			
					
				#check the distance
				if matches[index]["score"]-nextscore>distance:
					return n

			return 0


		#find match by 'exact match' algorithm
		def exact_match(matches):
			if len(matches)==0:
				return (None,False)

			reftitle=lower_non_turkish_alphanumeric(item.merchantItemTitle).replace(" ","")
			for match in matches:
				if lower_non_turkish_alphanumeric(match["title2"]).replace(" ","")==reftitle:
					return (match,True)
			return (None,False)
			
		#find match by 'best match' algorithm. returns (match, isdirect)
		def best_match(matches):
			if len(matches)==0:
				return (None,False)

			#get top match
			match=matches[0]

			#if score < 1.0, no match
			if match["score"]<1.0:
				return (None, False)

			#direct match if score > 1.5 and spread > 1
			if match["score"] > 1.5 and spread(matches)>=1.0:
				return (match, True)

			#direct match if score between 1.5 and 3 and margin >1.5
			elif match["score"] > 1.5 and match["score"] < 3.0 and margin(matches)>=1.5:
				return (match, True)

			#direct match if score > 3 and margin >1
			elif match["score"] >= 3.0 and margin(matches)>=1.0:
				return (match, True)
			
			#if the score<1.5, do not suggest as a possible match
			if match["score"]<1.5:
				return (None, False)
				
			return (match, False)


		#find match by 'exact match' algorithm on merchant matches
		def exact_merchant_match(m_matches,c_matches):
			if len(m_matches)==0 or len(c_matches)==0:
				return (None,False)

			reftitle=lower_non_turkish_alphanumeric(item.merchantItemTitle).replace(" ","")
			for match in m_matches:
				if lower_non_turkish_alphanumeric(match["merchantItemTitle"]).replace(" ","")==reftitle:
					id=match["itemId"]
					for it in c_matches:
						if str(id)==str(it["id"]):
							return (it,True)
			return (None,False)


		#find match by 'best match' algorithm based on merchant matches. returns (match, isdirect)
		def best_merchant_match(m_matches,c_matches):
			if len(m_matches)==0 or len(c_matches)==0:
				return (None,False)
		
			#record the adjusted best match score corresponding to each cimri catalogue item
			cm_matches=[]
			for cm in c_matches:
				#get the best merchant match score for this cimri item
				mscores=[m["score"] for m in m_matches if str(m["itemId"])==str(cm["id"])]
				score=max(mscores) if len(mscores)>0 else 0
				
				#factor in the adjusted catalogue score (takes into account the price adjustment)
				score*=cm["score"]

				#record
				match={}
				for key in cm:
					match[key]=cm[key]
				match["score"]=score
				cm_matches.append(match)

			#sort 
			cm_matches.sort(lambda a,b: int(100*(b["score"]-a["score"])))

			#get top match
			match=cm_matches[0]

			#if score < 1.0, no match
			if match["score"]<1.0:
				return (None, False)

			#direct match if score > 1.5 and spread > 1
			if match["score"] > 1.5 and spread(cm_matches)>=1.0:
				return (match, True)

			#direct match if score > 4.5 and spread > 0.5
			elif match["score"] > 4.5 and spread(cm_matches)>=0.5:
				return (match, True)

			#direct match if score between 1.5 and 3 and margin >1.5
			elif match["score"] > 1.5 and match["score"] < 3.0 and margin(cm_matches)>=1.5:
				return (match, True)

			#direct match if score > 3 and margin >1
			elif match["score"] >= 3.0 and margin(cm_matches)>=1.0:
				return (match, True)

			#direct match if score > 10 (assumption is that the top matches are the same items at this point)
			elif match["score"] >= 10:
				return (match, True)

			#if the score<1.5, do not suggest as a possible match
			if match["score"]<1.5:
				return (None, False)

			return (match,False)

	
		#find match by 'similar items' algorithm. returns (match, isdirect)
		def similarity_match(matches):
			if len(matches)==0:
				return (None,False)

			#top match needs to have a minimum score
			if matches[0]["score"]<2.5:
				return (None, False)

			#find groupings
			group=grouping(matches,0.25,1.0)
			if group==0:
				return (None, False)

			#pick the top match by default
			match=matches[0]
			score=0

			#adjust the scores by colors and discount by wrong colors
			item_colors=find_colors([item.merchantItemTitle,item.modelNameView])
			for m in matches[:group]:
				match_colors=find_colors([m["title2"]])
	
				#if there's no adjustment, go on to the next match
				if len(item_colors)==0 and len(match_colors)==0:
					continue
		
				#penalize mismatches 
				if item_colors != match_colors:
					coef=0.8
				else:
					coef=1.0
			
				#update match
				if coef*m["score"]>score:
					match=m
					score=coef*m["score"]
				
			return (match, True)
	
		def pattern_match(matches):
			if len(matches)==0:
				return (None,False)

			#top match needs to have a minimum score
			if matches[0]["score"]<2.5:
				return (None, False)

			#find groupings
			#group=max(grouping(matches,1,1.5),grouping(matches,1.5,2.5))
			group=grouping(matches,0.5,1)
			if group==0:
				return (None, False)

			model=ItemPatternModel(item.merchantItemTitle)

			#find best match
			bestmatch=None
			bestscore=0
			for m in matches[:group]:
				score=ItemPatternModel.match(model,ItemPatternModel(m["title2"]))
				if score>bestscore:
					bestscore=score
					bestmatch=m

			return (bestmatch, True)


		def reverse_match(matches,resetscores=False):
			if len(matches)==0:
				return (None,False)

			#reset scores
			if resetscores is True:
				for index in range(len(matches)):
					matches[index]["score"]=0

			#process item title
			item_title=lower_non_turkish_alphanumeric(item.merchantItemTitle)
			item_titleseq=item_title.replace(" ","")
			
			#search each solr match against the item title:
			for index in range(len(matches)):
				score=0

				#get match data
				model=lower_non_turkish_alphanumeric(matches[index]["model"]).strip() if "model" in matches[index] else None
				mpn=lower_non_turkish_alphanumeric(matches[index]["mpnValue"]).strip() if "mpnValue" in matches[index] else None
				keywords=matches[index]["title2"].split(" ")+matches[index]["keywords"].split(" ")
				
				#process keywords
				keywords=[lower_non_turkish_alphanumeric(k) for k in keywords]
				keywords=list(set( [k.strip() for k in keywords if k.strip()!=""] ))

				#record if model is exactly matched
				matches[index]["modelmatch"]=False

				#match model
				if model is not None and model!="":
					#exact match
					if item_title.find(model)>-1:
						score+=3
						matches[index]["modelmatch"]=True
					#sequence match
					elif item_titleseq.find(model.replace(" ",""))>-1:
						score+=1.5				

				#mpn match
				if mpn is not None and mpn!="":		
					#exact match
					if item_title.find(mpn)>-1:
						score+=2
					#sequence match
					elif item_titleseq.find(mpn.replace(" ",""))>-1:
						score+=1				

				#keyword matches
				for keyword in keywords:
					#direct match
					if item_title.find(keyword)>-1:
						score+=len(keyword)*0.125
					#sequence match
					elif item_titleseq.find(keyword.replace(" ",""))>-1:
						score+=len(keyword)*0.1		
	
				#update score
				matches[index]["score"]+=score

			#sort by score			
			matches.sort(lambda a,b: int(100*(b["score"]-a["score"])))

			#get best match 
			match,direct=best_match(matches)

			#if there's a match, return it as a possible match
			return (match,False)

			#if the picked direct match has an exact model match, consider this a direct match. otherwise considera a possible match
			#if match is not None and direct is True and match["modelmatch"] is True:
			#	return (match,True)
			#else:
			#	return (match,False)
			

		def apply_disqualifiers(matches,use_brand=False,constrain=False,check_prod_type=False,price_check=False,mismatch_cats=[]):
			#apply disqualifiers: mismatched categories
			if mismatch_cats is not None:
				matches=[match for match in matches if match["categoryId"] not in mismatch_cats]

			#apply disqualifiers: validate brand
			if use_brand:
				#select matches with matching brands
				qualified=[match for match in matches if validate_brand(item,match) is True]

				#only take the qualified brands
				matches=qualified

				#if all matches have been disqualified, ignore the disqualification 
				#if len(qualified)>0:
					#log
					#for match in matches:
					#	if match["id"] not in (m["id"] for m in qualified):
					#		self._log_disqualification(item,match,"brand")
				#	matches=qualified
	
			#apply disqualifiers: ignore matches that already have a matched item for the same merchant
			if constrain is True:
				qualified=[m for m in matches if self._check_existing_match(item.merchant["merchantId"],m["id"]) is False]
				#log
				#for match in matches:
				#	if match["id"] not in (m["id"] for m in qualified):
				#		self._log_disqualification(item,match,"merchant-item-constraint")
				matches=qualified

			#apply disqualifiers: detect matches of same brand but different product types
			if check_prod_type:
				qualified=[m for m in matches if check_product_type_match(item.merchantItemTitle,m["title2"]) is True]
				#log
				#for match in matches:
				#	if match["id"] not in (m["id"] for m in qualified):
				#		self._log_disqualification(item,match,"product-type")
				matches=qualified

			#adjust the scores by max/min price
			if price_check:
				for index in range(len(matches)):
					matches[index]["score"]=matches[index]["score"]*self._get_price_range_factor(item,matches[index])

			return matches

		
		def update_match(prevmatch,newmatch):
			#get match details
			pmatch=prevmatch[0]
			pdirect=prevmatch[1]
			nmatch=newmatch[0]
			ndirect=newmatch[1]

			#if there was a previous match and it was direct, use that
			if pmatch is not None and pdirect is True:
				return prevmatch
		
			#if there was a previous match but it was a guess, look at the new match
			elif pmatch is not None and pdirect is False:
				#if there's a new match and it is direct, use it
				if nmatch is not None and ndirect is True:
					return newmatch
				#otherwise, keep the previous guess
				else:
					return prevmatch

			#else, return the new match (there was no previous match)
			else:
				return newmatch			


		@defer.inlineCallbacks
		def match_item():
			#get mismatch categories for item
			mismatch_cats=yield get_mismatch_categories(item.merchantItemTitle)	

			#get keywords
			keywords=[]
			keywords_model=[]
			use_brand=False
			use_model=False

			#primary keywords: brand and modelNameview
			if item.brand is not None and item.brand.strip()!="":
				use_brand=True
				keywords.extend([key.strip() for key in item.brand.split(" ") if key.strip()!=""])

			if item.modelNameView is not None and item.modelNameView.strip()!="":
				#use permutations of the model keywords	(the model name is valuable. need to detect any
				#possible variations of it that we can also find in the title and other meta data)	
				use_model=True
				keywords_model=model_keywords(item.modelNameView,item.merchantItemTitle)
				keywords.extend(keywords_model)
		
			#use the title only if the model and brand are not present
			#if (use_brand is False or use_model is False) and item.merchantItemTitle is not None:
			keywords.extend([key.strip() for key in item.merchantItemTitle.split(" ") if key.strip()!=""])

			#also include mpn value
			#if item.mpnValue is not None and item.mpnValue.strip()!="":
			#	keywords.append(item.mpnValue)

			#match catalogue items. pass 1: unprocessed keywords
			#apply disqualifiers: ignore matches if number of keywords < 2
			matches_unprocessed=[]
			keywords_unprocessed=list(set( [remove_non_ascii(replace_turkish_chars(key)).lower() for key in keywords] ))
			if len(keywords_unprocessed)>1:
				matches_unprocessed=yield match_by_keywords(keywords_unprocessed)

			#match catalogue items. pass 2: processed keywords
			#apply disqualifiers: ignore matches if number of keywords < 2
			matches_processed=[]
			keywords_processed=list(set( [lower_non_turkish_alphanumeric(key) for key in keywords] ))
			if len(keywords_processed)>1:
				matches_processed=yield match_by_keywords(keywords_processed)
		
			#merge matches
			matches={}
			for match in matches_unprocessed:
				matches[match["id"]]=match
			for match in matches_processed:
				if match["id"] in matches:
					if match["score"]>matches[match["id"]]["score"]:
						matches[match["id"]]=match
				else:
					matches[match["id"]]=match
			matches=matches.values()
			
			#apply disqualifiers
			matches=apply_disqualifiers(matches,use_brand=use_brand,constrain=self.match_constrain,check_prod_type=True,price_check=True,mismatch_cats=mismatch_cats)

			#match merchant items. pass 1: unprocessed keywords
			#apply disqualifiers: ignore matches if number of keywords < 2
			matches_unprocessed=[]
			keywords_unprocessed=list(set( [remove_non_ascii(replace_turkish_chars(key)).lower() for key in item.merchantItemTitle.split(" ")] ))
			keywords_unprocessed=[keyword for keyword in keywords_unprocessed if keyword!=""]
			if len(keywords_unprocessed)>1:
				matches_unprocessed=yield match_by_title_keywords(" ".join(keywords_unprocessed))

			#match merchant items. pass 2: processed keywords
			#apply disqualifiers: ignore matches if number of keywords < 2
			matches_processed=[]
			keywords_processed=list(set( [lower_non_turkish_alphanumeric(key) for key in item.merchantItemTitle.strip(" ")] ))
			keywords_processed=[keyword for keyword in keywords_processed if keyword!=""]
			if len(keywords_processed)>1:
				matches_processed=yield match_by_title_keywords(" ".join(keywords_processed))
		
			#match by model 
#			if len(keywords_model)>0:
#				mres=yield match_by_model(lower_non_turkish_alphanumeric(" ".join(keywords_model)))
#				if mres is not None:
#					m_matches.append(mres)		


#			f=open("out.txt","a")
#			f.write("matches unprocessed\n")
#			f.write(pprint.pformat(matches_unprocessed))
#			f.write("\n\n\n")
#			f.close()

			#merge merchant matches and select only the ones that are matched
			#ignore the merchant item with the same merchant item id
			m_matches={}
			for match in matches_unprocessed:
				if "itemId" not in match or compare_merchant_item_ids(item,match["merchantItemId"]):
					continue
				m_matches[match["merchantItemId"]]=match
			for match in matches_processed:
				if "itemId" not in match or compare_merchant_item_ids(item,match["merchantItemId"]):
					continue
				if match["merchantItemId"] in m_matches:
					if match["score"]>m_matches[match["merchantItemId"]]["score"]:
						m_matches[match["merchantItemId"]]=match
				else:
					m_matches[match["merchantItemId"]]=match
			m_matches=m_matches.values()

			#sort the merged merchant matches and pick the best 50
			m_matches.sort(lambda a,b: int(100*(b["score"]-a["score"])))
			m_matches=m_matches[:50]

#			f=open("out.txt","a")
#			f.write("matches processed\n")
#			f.write(pprint.pformat(m_matches))
#			f.write("\n\n\n")
#			f.close()

			#adjust catalogue item matches by merchant item match scores
			weights={}
			if len(matches)>0:
				#weigh by the scores
				weighted={}
				for it in m_matches:
					itemid=it["itemId"]
					if itemid not in weighted:
						weighted[itemid]={"score": 0, "count":0}
					if it["score"]>weighted[itemid]["score"]:
						weighted[itemid]["score"]=it["score"]
#					weighted[itemid]["score"]=weighted[itemid]["score"]+it["score"]	
#					weighted[itemid]["count"]=weighted[itemid]["count"]+1
				for id in weighted:
					#only use if score > 2
					if weighted[id]["score"]>=2:
						weights[id]=weighted[id]["score"]
#				for id in weighted:
#					weights[id]=weighted[id]["score"]/weighted[id]["count"]

				#adjust the scores by the weights
				for index in range(len(matches)):
					id=int(matches[index]["id"])
					if id in weights.keys():
						matches[index]["score"]=matches[index]["score"]*weights[id]

			#sort by score			
			matches.sort(lambda a,b: int(100*(b["score"]-a["score"])))

			#log analysis
			self._log_analysis(item,matches,weights)			

			#get match and match type (direct)
			match=None
			direct=False	

			#exact match
			match,direct=exact_match(matches)
			if direct is True:
				self._log_matched_item(item,match,"exact match")

#			#similarity match
#			if match is None or direct is False:
#				match,direct=similarity_match(matches)

#			#pattern match
#			if match is None or direct is False:
#				match,direct=pattern_match(matches)

			#best match
			if match is None or direct is False:
				match,direct=update_match((match,direct), best_match(matches))
				if direct is True:
					self._log_matched_item(item,match,"best match")


			#move on to merchant match based algorithms if there's still no match
			if match is None or direct is False:
				#get cimri items corresponding to merchant matches
				ids=list(set([it["itemId"] for it in m_matches if "itemId" in it]))
				c_matches=yield match_by_ids(ids)

#				f=open("out.txt","a")
#				f.write("ids ("+str(len(ids))+")\n")
#				f.write(repr(ids))
#				f.write("\n\n\n")
#				f.write("catalogue matches ("+str(len(c_matches))+")\n")
#				f.write(pprint.pformat(c_matches))
#				f.write("\n")
#				f.close()
	
				#set all scores to 1.0
				for index in range(len(c_matches)):
					c_matches[index]["score"]=1.0

				#apply disqualifiers
				c_matches=apply_disqualifiers(c_matches,constrain=self.match_constrain, check_prod_type=True, price_check=True,mismatch_cats=mismatch_cats)

			#exact merchant match
			if match is None or direct is False:			
				match,direct=update_match((match,direct), exact_merchant_match(m_matches,c_matches))
				if direct is True:
					self._log_matched_item(item,match,"exact merchant match")

			#best merchant match
			if match is None or direct is False:
				match,direct=update_match((match,direct), best_merchant_match(m_matches,c_matches))
				if direct is True:
					self._log_matched_item(item,match,"best merchant match")

			#reverse match
			if match is None or direct is False:
				#try to leverage guesses or evaluate from scratch
				match,direct=update_match((match,direct), reverse_match(matches,(match is None)))
				if direct is True:
					self._log_matched_item(item,match,"reverse match")

			if match is not None and direct is False:
				self._log_matched_item(item,match,"possible")
			#added for no match items, subject to be deleted 
			if match is None: 
				self._log_unmatched_item(item,"no match")
                        #added for no match items, subject to be deleted
			defer.returnValue( (match,direct,matches) )



		@defer.inlineCallbacks
		def match_blacklist():
			#match blacklist merchant items
			matches=yield match_by_title_keywords_blacklist(lower_non_turkish_alphanumeric(item.merchantItemTitle))
			if matches is None or len(matches)==0:
				defer.returnValue( False )

			#get top match
			match=matches[0]

			#if score > 2.0, match found for this purpose
			if match["score"]>2.0:
				defer.returnValue( True )

			defer.returnValue( False )



		#step 1: get merchant item from cimri
		citem=self._get_cimri_merchant_item(item)


			
		#step 2: handle side tasks 
		#check if item is already matched and inactive. if so, item needs to be cleaned up in cimri service
		if citem is not None and citem.is_matched(False) and citem.status in [CimriStatus.get_status("PAUSED_NO_IN_XML_ACTIVE").get_code(),CimriStatus.get_status("PAUSED_BY_CIMRI").get_code()]:
			#add to update task to clear
			self.task.result.append( {"meta.action":"clean", "data":citem} )

			#record stats
			self.task.stats["data"]["updates"]["total"]+=1			
			if "clean" not in self.task.stats["data"]["updates"]:
				self.task.stats["data"]["updates"]["clean"]=0
			self.task.stats["data"]["updates"]["clean"]+=1



		#step 3: determine tasks
		tasks={"match":False, "update":False}
		if self.task.op=="match-update":
			#only do an update 
			tasks["update"]=True

			#if the merchant item is not in the system or not already matched, do not proceed. nothing to update
			if citem is None or citem.is_matched() is False:
				defer.returnValue({"meta.action":None, "data":item})
				return

		#handle match-insert task (insert new items and match unmatched existing items)
		elif self.task.op=="match-insert":
			#match and update
			tasks["match"]=True
			tasks["update"]=True

			#if the merchant item is already in the system and matched, do not proceed
			if citem is not None and citem.is_matched():
				defer.returnValue({"meta.action":None, "data":item})
				return

		#handle all other match tasks
		else:			
			#if the 'match.unmatched' option is set and the item is already matched, do an information update only
			if self.match_unmatched and citem is not None and citem.is_matched():
				#match update only
				tasks["update"]=True

			#otherwise, run the item through the match algorithm
			else:			
				#match and update
				tasks["match"]=True
				tasks["update"]=True


		
		#step 4: determine task actions
		match, direct, matches = (None, False, [])
		blacklist=False
		if tasks["match"] is True:
			#match item
			match,direct,matches=yield match_item()

			#yeni urun vs kategori uyumsuz
			if match is None:										
               			#match against kategori utumsuz items 
				blacklist=yield match_blacklist()

			#check if matched itemId is already mapped to an item by the same 
			id_mapped=True if (match is not None and self._check_existing_match(item.merchant["merchantId"],match["id"])) else False

			#record stats
			if match is not None and direct is True:
				self.task.stats["data"]["matched"]["total"]=self.task.stats["data"]["matched"]["total"]+1
			elif match is not None and direct is False:
				self.task.stats["data"]["guessed"]["total"]=self.task.stats["data"]["guessed"]["total"]+1
			elif match is None:
				self.task.stats["data"]["nomatch"]["total"]=self.task.stats["data"]["nomatch"]["total"]+1
			
				#record blacklist/newitem
				if blacklist is True:
					self.task.stats["data"]["nomatch"]["blacklist"]=self.task.stats["data"]["nomatch"]["blacklist"]+1
				else:
					self.task.stats["data"]["nomatch"]["newitem"]=self.task.stats["data"]["nomatch"]["newitem"]+1
				



		#step 4: determine action (insert/update/none)
		action=None
		if tasks["match"] is True and (citem is None or self.test is True):	
			#insert item
			action="insert"
	
			#check zero price
			if self._check_zero_price(item) is True:
				item.status=CimriStatus.get_status("PAUSED_BY_CIMRI_ZERO_PRICE").get_code()
				item.matcherType=999

				#record stats
				if match is not None and direct is True:
					self.task.stats["data"]["matched"]["zero_price"]=self.task.stats["data"]["matched"]["zero_price"]+1
				elif match is not None and direct is False:
					self.task.stats["data"]["guessed"]["zero_price"]=self.task.stats["data"]["guessed"]["zero_price"]+1
				elif match is None:
					self.task.stats["data"]["nomatch"]["zero_price"]=self.task.stats["data"]["nomatch"]["zero_price"]+1	

			#no match
			elif match is None:
				#insert as blacklist or no-match
				if blacklist:
					item.status=CimriStatus.get_status("BLACKLIST_ITEM").get_code()
				else:
					item.status=CimriStatus.get_status("PAUSED_BY_CIMRI").get_code()
				item.matcherType=999

				#record stats
				self.task.stats["data"]["nomatch"]["insert"]=self.task.stats["data"]["nomatch"]["insert"]+1

			#matched but matched item already mapped to
			elif direct is True and id_mapped is True and self.test is False:
				#insert as no-match
				item.status=CimriStatus.get_status("PAUSED_BY_CIMRI").get_code()
				item.matcherType=999

				#record stats
				self.task.stats["data"]["nomatch"]["insert"]=self.task.stats["data"]["nomatch"]["insert"]+1
				self.task.stats["data"]["matched"]["matched_to_active"]=self.task.stats["data"]["matched"]["matched_to_active"]+1

			#direct match
			elif direct is True:
				#insert as active
				item.status=CimriStatus.get_status("ACTIVE").get_code()
				item.item={"itemId":match["id"]}
				item.score=match["score"]
				item.matchDate=time.time()				
				item.matcherType=99

				#check to make sure that this is not a duplicate match to a cimri item for this merchant
				if self._check_duplicate_match(item.merchant["merchantId"],item.item["itemId"],item.score) is False:
					#no action here - do not insert
					action=None

					#record stats
					self.task.stats["data"]["matched"]["duplicate"]=self.task.stats["data"]["matched"]["duplicate"]+1
				else:
					#store a reference to the newly matched item for duplicate detection
					self._item_matches["-".join([item.merchant["merchantId"],item.item["itemId"]])]=item

					#record stats
					self.task.stats["data"]["matched"]["insert"]=self.task.stats["data"]["matched"]["insert"]+1

			#possible match
			else:
				item.status=CimriStatus.get_status("SOLR_MATCHED").get_code()
				item.possibleSolrItem={"itemId":match["id"]}
				item.score=match["score"]
				item.matcherType=999

				#record stats
				self.task.stats["data"]["guessed"]["insert"]=self.task.stats["data"]["guessed"]["insert"]+1

			#set operator (cron user)
			item.operator=0

		else:
			#get current item id, possible solr item for item, and status
			matched_id_prev=citem.item["itemId"] if citem.is_matched() else None
			guessed_id_prev=citem.possibleSolrItem["itemId"] if citem.is_guessed() else None
			status_prev=citem.status

			#update item data and detect what changed
			changed=[]
			if tasks["update"] is True:
				changed=self._update_data(citem,item)
				item=citem

				#item exists in xml, update status
				item.status=CimriStatus(item.status).get_active_status().get_code()

				#check zero price
				if self._check_zero_price(item) is True:
					#set status
					item.status=CimriStatus.get_status("PAUSED_BY_CIMRI_ZERO_PRICE").get_code()

					#reset item mapping
					item.item=None

					#update stats
					if "zero_price" not in self.task.stats["data"]["updates"]:
						self.task.stats["data"]["updates"]["zero_price"]=0
					self.task.stats["data"]["updates"]["zero_price"]=self.task.stats["data"]["updates"]["zero_price"]+1

			#handle match task
			if tasks["match"] is True:
				#check if zero price
				if self._check_zero_price(item):
					#do not update match data for zero price items (the "update" task handler above will make the
					#necessary modifications to the item in case of zero price)
					pass
					
				#if the item's current status is blacklisted, do not change anything
				elif item.status==CimriStatus.get_status("BLACKLIST_ITEM").get_code():
					pass

				#if matched but item matched to already matched to another item, record stats
				elif direct and item.is_matched() is False and id_mapped is True:
					#record stats
					self.task.stats["data"]["matched"]["matched_to_active"]=self.task.stats["data"]["matched"]["matched_to_active"]+1

				#direct match and previously not matched
				elif direct and item.is_matched() is False and id_mapped is False:
					#check to make sure that this is not a duplicate match to a cimri item for this merchant
					if self._check_duplicate_match(item.merchant["merchantId"],match["id"],match["score"]) is False:
						#record stats
						self.task.stats["data"]["matched"]["duplicate"]=self.task.stats["data"]["matched"]["duplicate"]+1

					else:
						#update item
						action="update"
						item.status=CimriStatus.get_status("ACTIVE").get_code()
						item.item={"itemId":match["id"]}
						item.score=match["score"]
						item.matchDate=time.time()				
						item.matcherType=99

						#store a reference to the newly matched item for duplicate detection
						self._item_matches["-".join([item.merchant["merchantId"],match["id"]])]=item

						#record stats
						self.task.stats["data"]["matched"]["update"]=self.task.stats["data"]["matched"]["update"]+1

				#possible match and previously not matched and not guessed
				elif match is not None and direct is False and item.is_matched() is False and item.is_guessed() is False:
					action="update"
					item.status=CimriStatus.get_status("SOLR_MATCHED").get_code()
					item.possibleSolrItem={"itemId":match["id"]}
					item.score=match["score"]
					item.matcherType=999

					#record stats
					self.task.stats["data"]["guessed"]["update"]=self.task.stats["data"]["guessed"]["update"]+1
				
				#if no match is found and status was 0 to start with, decide again if blacklist or newitem
				elif match is None and item.status==CimriStatus.get_status("PAUSED_BY_CIMRI").get_code():
					#update as blacklist or no-match
					if blacklist is True and item.status==CimriStatus.get_status("PAUSED_BY_CIMRI").get_code():
						item.status=CimriStatus.get_status("BLACKLIST_ITEM").get_code()
						item.matcherType=999
					elif blacklist is False:
						item.status=CimriStatus.get_status("PAUSED_BY_CIMRI").get_code()
						item.matcherType=999

				#record stats
				if matched_id_prev is not None:
					if direct and str(matched_id_prev)==str(match["id"]):
						#matched the same item as it was already matched to
						self.task.stats["data"]["matched"]["matched_same"]=self.task.stats["data"]["matched"]["matched_same"]+1
					elif direct:
						#matched another item than what it's matched to currently
						self.task.stats["data"]["matched"]["matched_diff"]=self.task.stats["data"]["matched"]["matched_diff"]+1
					elif match is None:
						#matched before but not now
						self.task.stats["data"]["nomatch"]["matched"]=self.task.stats["data"]["nomatch"]["matched"]+1
				elif guessed_id_prev is not None:
					if match is not None and direct is False and str(guessed_id_prev)==str(match["id"]):
						#guessed the same item as before
						self.task.stats["data"]["guessed"]["guessed_same"]=self.task.stats["data"]["guessed"]["guessed_same"]+1
					elif match is not None and direct is False:
						#guessed another item than before
						self.task.stats["data"]["guessed"]["guessed_diff"]=self.task.stats["data"]["guessed"]["guessed_diff"]+1			

			
			#detect if status changed
			statuschanged=int(item.status)!=int(status_prev)

			#if the match/possible match of the items changed or any info changed or the status is changed, update item
			action="update" if (action=="update" or len(changed)>0 or statuschanged) else None

			#record stats
			if action == "update":
				self._record_update_stats(statuschanged,changed)

			#set operator if not set (cron user)	
			item.operator=0 if item.operator is None else item.operator
			
		#if refitem is not None:
		#	#updata match stats
		#	self._test_update_match_stats(match,direct,matches,refitem)			
	
		#record analytics
		if tasks["match"] is True:
			self._test_record_analytics(item,refitem,match,direct,matches)

		defer.returnValue({"meta.action":action, "data":item})



	def _record_update_stats(self,statuschanged,changed):
                """
		Islem istatistiklerini gunceller. Herhangi bir item icin status ya da herhangi bir item bilgisinin degisip degismedigini
		kontrol eder.

                @type  statuschanged: bool
                @param statuschanged: item'in statusun match islemi sonucunda degisip degismedigi

                @type  changed: dict
                @param changed: item'in match islemi sonucunda degerleri degisen fieldlari
		"""

		self.task.stats["data"]["updates"]["total"]+=1
		for key in changed:
			if key not in self.task.stats["data"]["updates"]:
				self.task.stats["data"]["updates"][key]=0
			self.task.stats["data"]["updates"][key]+=1
		if statuschanged:
			if "status" not in self.task.stats["data"]["updates"]:
				self.task.stats["data"]["updates"]["status"]=0
			self.task.stats["data"]["updates"]["status"]+=1


	def _merchant_update(self,merchantid,data):
                """
		Belrili bir merchant icin o merchant'in sistemde olup xml'den gelmeyen itemlarini tesbit edip update edilmek uzere
		update listesi yaratir.

                @type  merchantid: str
                @param merchantid: merchant IDsi

                @type  data: list
                @param data: merchant'in sistemde zaten varolan itemlarinin listesi

                @rtype: list
                @return: update edilecek itemlar ve update bilgileri
                """

		updates=[]

		#create a hash of the merchant item ids in the data to be processed
		ids={}
		for item in data:
			ids[unicode(item["data"].merchantItemId).strip()]=True

		#mark existing items for merchant that are missing in the data
		for itemid in self._merchant_items[merchantid]:		
			if unicode(itemid).strip() not in ids:
				#get item
				item=self._merchant_items[merchantid][itemid]

				#discard if already paused
				if CimriStatus(item.status).is_active() is False:
					continue
	
				#update status to paused
				status_new=CimriStatus(item.status).get_paused_status().get_code()
				if unicode(status_new)==unicode(item.status).strip():	
					continue
				item.status=status_new
				
				#add to update list
				updates.append({"meta.action":"update", "data":item})

				#record stats (total, status, not-in-xml)
				self.task.stats["data"]["updates"]["total"]+=1
				if "status" not in self.task.stats["data"]["updates"]:
					self.task.stats["data"]["updates"]["status"]=0
				self.task.stats["data"]["updates"]["status"]=self.task.stats["data"]["updates"]["status"]+1
				if "not-in-xml" not in self.task.stats["data"]["updates"]:
					self.task.stats["data"]["updates"]["not-in-xml"]=0
				self.task.stats["data"]["updates"]["not-in-xml"]=self.task.stats["data"]["updates"]["not-in-xml"]+1

		return updates


	def _update_data(self,citem,item):
                """
		Bir merchant item'in match islemi sonucunda degerleri degisen fieldlarini tesbit eder	

                @type  citem: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param citem: cimri service MerchantItem

                @type  item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param item:  MerchantItem

                @rtype: list
                @return: merchant item'in match islemi sonucunda degerleri degisen fieldlarinin listesi
                """

		def is_number(s):
			try:
        			float(s)
        			return True
    			except ValueError:
        			return False

		#update any cimri item data that has changed
		changed=[]
		for field in MerchantItem.fieldmap.values():
			#get fields
			ifield=getattr(item,field)
			cfield=getattr(citem,field)

			#if both values are None, nothing to do
			if ifield is None and cfield is None:
				continue

			#check if there's no value in the new copy while there was a value before
			if ifield is None and cfield is not None:
				setattr(citem,field,"")
				changed.append(field)

			#check if there was no value but there's a value now
			elif ifield is not None and cfield is None:
				setattr(citem,field,ifield)
				changed.append(field)

			#check if both values are numeric and are different
			elif is_number(ifield) and is_number(cfield):
				if float(ifield)!=float(cfield):
					setattr(citem,field,ifield)
					changed.append(field)
			
			#otherwise compare as unicode strings		
			elif replace_turkish_chars(ifield).lower().strip()!=replace_turkish_chars(cfield).lower().strip():
				setattr(citem,field,ifield)
				changed.append(field)

		return changed


	def _check_zero_price(self,item):
                """
		Bir merchant item'in price bilgilerinin gecerli olup olmadigini kontrol eder. Gecerli fiyatlar 0'dan buyuk ve rakam
		olarak formatli verilerdir.

                @type  item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param item:  MerchantItem

                @rtype: bool
                @return: eger urun fiyati 0 ya da gecersiz ise True, aksi takdirde False
                """

		def is_number(s):
			try:
        			float(s)
        			return True
    			except ValueError:
        			return False

		#check pricePlusTax (treat non-number values as 0-values)
		return (float(item.pricePlusTax)<=0) if is_number(item.pricePlusTax) else True


	def _get_price_range_factor(self,item,match):
                """
		Bir item ile o item icin bulunan match fiyatlari arasindaki farkliliga gore match skorunu etkilecek sekilde bir katsayi
		hesaplar. Fiyatlar ne kadar yakin ise katsayi 1'e o kadar yakin olacaktir. 

                @type  item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param item:  MerchantItem

                @type  match: dict
                @param match: bulunan match icin max/min fiyat bilgilerini iceren bir dictionary

                @rtype: float
                @return: skor katsayisi
                """

		def is_number(s):
			try:
        			float(s)
        			return True
    			except ValueError:
        			return False
	
		#if item price not a number, return 0
		if is_number(item.pricePlusTax) is False:
			return 0
		itemprice=float(item.pricePlusTax)
		if itemprice<0:
			return 0

		#check min price				
		if is_number(match["minPrice"]) is True:
			#check if price is less than %50 of the min. catalogue price
			minprice=float(match["minPrice"])
			if minprice>0 and itemprice<0.5*minprice:
				return itemprice/(0.5*minprice)			#will be between 0 and 1				

		#check max price				
		if is_number(match["maxPrice"]) is True:
			#check if price is more than %50 of the max. catalogue price
			maxprice=float(match["maxPrice"])
			if maxprice>0 and itemprice>2*maxprice:
				return 0
			if maxprice>0 and itemprice>1.5*maxprice:
				return (2*maxprice-itemprice)/(0.5*maxprice)	#will be between 0 and 1				

		#default
		return 1


	def _test_record_analytics(self,item,refitem,match,direct,matches):
                """
		Test islemleri icin islem analizi bilgilerini kayit eder.

                @type  item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param item:  MerchantItem

                @type  refitem: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param refitem:  MerchantItem

                @type  match: dict
                @param match: match bilgileri

                @type direct: bool
                @param direct: match'in direct match (True) ya da possible match oldugu 

                @type  matches: list
                @param matches: match islemleri sirasinda degerlendirilen olasi matchlerin listesi
                """

		#get match status
		status=None

		#no match
		if match is None:
			#not matched
			status=MatchRecord.MATCH_STATUS_NOT_MATCHED

		#direct match
		elif direct is True:
			if refitem is None or refitem.item is None:
				#direct match (no refitem)
				status=MatchRecord.MATCH_STATUS_MATCHED
			elif match["id"]==refitem.item["itemId"]:
				#direct and correct match (with reference to refitem)
				status=MatchRecord.MATCH_STATUS_MATCHED
			else:
				#wrong direct match (with reference to refitem)
				status=MatchRecord.MATCH_STATUS_MATCHED_WRONG

		#guess
		else:
			if refitem is None or refitem.item is None:
				#guessed (no refitem)
				status=MatchRecord.MATCH_STATUS_GUESSED
			elif match["id"]==refitem.item["itemId"]:
				#guessed right (with reference to refitem)
				status=MatchRecord.MATCH_STATUS_GUESSED
			else:
				#guessed wrong (with reference to refitem)
				status=MatchRecord.MATCH_STATUS_GUESSED_WRONG

		#do not record correct matches
		if status==MatchRecord.MATCH_STATUS_MATCHED:
			return
	
		#record
		record=MatchRecord()
		record.taskid=self.task.id
		record.item=item.to_dict()
		record.refitem=refitem.to_dict() if refitem is not None else None
		record.status=status
		record.score=0 if match is None else match["score"]
		record.matches=matches
		record.create()


	def _test_update_match_stats(self,match,direct,matches,refitem):
                """
		Islem istatistilerini gunceller

                @type  match: dict
                @param match: match bilgileri

                @type direct: bool
                @param direct: match'in direct match (True) ya da possible match oldugu 

                @type  matches: list
                @param matches: match islemleri sirasinda degerlendirilen olasi matchlerin listesi

                @type  refitem: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param refitem:  MerchantItem
                """

		#match scores
		scores=[m["score"] for m in matches]

		#reference item id and score
		refid=None
		refscore=0
		if refitem is not None and refitem.item is not None:
			refid=refitem.item["itemId"]
			for m in matches:
				if m["id"]==refid:
					refscore=m["score"]				

		#success
		if match is not None and refid is not None:
			success=(match["id"]==refid)
		elif match is None and refitem is None:
			success=True
		else:
			success=False

		stats={"scores":scores, "match":(match is not None), "direct":direct, "success":success, "ref":refscore}
		self.task.stats["test"]["matches"].append(stats)


	def _log_analysis(self,item,matches,weighted):
                """
		Match islem analizini islem loguna ekler

                @type  item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param item:  MerchantItem

                @type  matches: list
                @param matches: match islemleri sirasinda degerlendirilen olasi matchlerin listesi

                @type  weighted: dict
                @param weighted: match isleminde kullanilan merchant item matchleri
                """

		self._log_task_msg("")
		self._log_task_msg("-match analysis------------------------------------------------------")

		#log item info
		self._log_task_msg(Template("merchantItemTitle:    $val").substitute(val=repr(replace_turkish_chars(item.merchantItemTitle))))
		self._log_task_msg(Template("brand:                $val").substitute(val=repr(replace_turkish_chars(item.brand))))
		self._log_task_msg(Template("modelNameView:        $val").substitute(val=repr(replace_turkish_chars(item.modelNameView))))
		self._log_task_msg(Template("mpnValue:             $val").substitute(val=repr(replace_turkish_chars(item.mpnValue))))
	
		#log matches	
		self._log_task_msg("matches")
		for match in matches:
			self._log_task_msg(Template("                      $val").substitute(val=repr(replace_turkish_chars(repr(match)))))
			self._log_task_msg("")
	
		#log weights	
		weights=[]
		for id in weighted:
			weights.append((id,weighted[id]))
		weights.sort(lambda a,b:int(100000*b[1])-int(100000*a[1]))
		self._log_task_msg(Template("weights:              $val").substitute(val=str(repr(weights))))

		self._log_task_msg("------------------------------------------------------match analysis-")


	def _log_matched_item(self,item,match,algorithm):
		fields=[str(item.merchant["merchantId"]),
			item.merchantItemId,
			item.merchantItemTitle,
			item.brand,
			item.modelNameView,
			str(item.pricePlusTax),
			algorithm,
			str(match["id"]),
			match["title2"],			
			(match["brand"] if "brand" in match else ""),			
			(match["model"] if "model" in match else ""),			
			(str(match["maxPrice"]) if "maxPrice" in match else ""),			
			(str(match["minPrice"]) if "minPrice" in match else ""),			
			(match["keywords"] if "keywords" in match else ""),			
			str(match["score"])
			]
		file_append_utf8("match-log.csv","\t".join([field.replace("\t"," ") for field in fields])+"\n")

	def _log_unmatched_item(self,item,algorithm):
		fields=[str(item.merchant["merchantId"]),
			item.merchantItemId,
			item.merchantItemTitle,
			item.brand,
			item.modelNameView,
			str(item.pricePlusTax),
			algorithm
			]
		file_append_utf8("match-log.csv","\t".join([field.replace("\t"," ") for field in fields])+"\n")

	def _log_disqualification(self,item,match,disqualifier):
		fields=[str(item.merchant["merchantId"]),
			item.merchantItemId,
			item.merchantItemTitle,
			item.brand,
			item.modelNameView,
			str(item.pricePlusTax),
			disqualifier,
			str(match["id"]),
			match["title2"],			
			(match["brand"] if "brand" in match else ""),			
			(match["model"] if "model" in match else ""),			
			(str(match["maxPrice"]) if "maxPrice" in match else ""),			
			(str(match["minPrice"]) if "minPrice" in match else ""),			
			(match["keywords"] if "keywords" in match else ""),			
			str(match["score"])
			]
		file_append_utf8("match-disq.csv","\t".join([field.replace("\t"," ") for field in fields])+"\n")



	
class ItemPatternModel():
	"""
	Kullanilmiyor.
	"""

#	given some text (item title) comprising of a number of words as follows:
#
#		word(1) word(2) word(3) ... word(n)
#
#	the context of the text is assumed to contain the following possible multi-word terms:
#		
#		brand model specs product-type
#		
#		(ie: lenovo t200 8GB laptop) 
#
#	the pattern matcher works on the following assumptions:
#
#	-the first few words (up to 3) can be the brand
#	-the rest of the words are assumed to represent the model, some product specs and the product type in that specific
# 	 order
#
#	when comparing two items, the algorithm first tries to find the longest match for possible model names between the 
#	two items being compared. the longest match is the exact match between potential model names according to the assumptions
#	above with the most number of letters. once the longest match is identified, the remainder of the text for the two
#	items is compared in terms of similarity. also, any color keywords that are detected in the text is removed before 
#	processing and compared separately.
#
#	the overall score of the match is:
#	
#	100*model_score + 100*int(100*spec_type_score) + int(100*color_score)
#
#	where model_score > 0,
#	      spec_type_score < 1.0,
#	      color_score < 1.0
#

	def __init__(self,text):
		#words in the model
		self._words=[]

		#colors in the model
		self._colors=[]

		#construct models
		self._construct(text)


	
	@classmethod
	def match(cls,model1,model2):
	#	return max( [ItemPatternModel._match(model1._words[i:],model1._colors,model2._words[j:],model2._colors) for i in range(1,4) for j in range(1,4)] )
		return ItemPatternModel._match(model1._words[1:], model1._colors, model2._words[1:], model2._colors) 


	@classmethod
	def _match(cls,words1,colors1,words2,colors2):
		#check lengths
		if len(words1)==0 or len(words2)==0:
			return 0

		#find the maximum number of contigious characters that are the same in the two sets of words. 
		#word boundries need to observed in the process		
		matched=False
		for length1 in reversed(range(len(words1))):
			text1="".join(words1[:length1+1])
			for length2 in reversed(range(len(words2))):
				text2="".join(words2[:length2+1])	
				if text1==text2:
					matched=True
					break
			if matched is True:
				break

		#model score is length of matched text
		length=0 if matched is False else len("".join(words1[:length1+1]))
		model_score=length

		#get spec/type score
		text1="".join(words1)
		text2="".join(words2)
		spec_type_score=similarity(text1[length:],text2[length:])	

		#match colors		
		color_score=0.1 if set(colors1)==set(colors2) else 0

		return 1000*model_score+int(100*spec_type_score)+color_score
	
	
	def _construct(self,text):
		#preprocess
		text=replace_turkish_chars(text).lower().strip()
		tokens=[ignore_non_alphanumeric(token) for token in text.split(" ") if token.strip()!=""]

		#extract colors	
		colors=[token for token in tokens if token in MetaMatcher.colors]						
		tokens=[token for token in tokens if token not in colors]                        

		self._words=tokens
		self._colors=colors		


#bootstrap
if __name__=="__main__":
        #run module
        mod=MetaMatcher()
        args=mod._parse_argv()
        mod._run(**args)
 
