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
import pattern.web 
from itertools import chain
import re
from string import Template
import math
import pickle
import os.path

from twisted.internet import reactor,defer
from twisted.internet.threads import deferToThread

from cimri.system.config import Config
from cimri.module.module import Distributor
from cimri.system.cache import Cache
from cimri.system.logger import Logger
from cimri.system.web import Web
from cimri.system.spec import ProductSpec
from cimri.api.cimriservice.merchants import MerchantsAPI
from cimri.api.cimriservice.data.merchantitem import MerchantItem
from cimri.api.scraper.merchant import MerchantScraperRecord
from cimri.api.scraper.item import MerchantItemScraperRecord
from cimri.module.scrapper.scrapper import Scrapper
from cimri.util.text import *

class DOMScrapper(Scrapper,Web):
        """
	Sistem tarafindan kullanilan scraper algoritmasi ve islemleri

	Modul tarafindan desteklenen islem turleri ve opsiyonlari su sekildedir:

        "scrap"	task : scrape islemi

                task.data      	: islemden gecirilecek her item icin "data" o merchant item'in URL'i olmalidir. ayni zamanda her item icin
				  asagidaki veriler de bulunmalidir 

                                  "meta.merchantid"             : item'in merchant IDsi

                                  "meta.xmlitem" 	        : item'in xml'den alinan MerchantItem bilgileri
								  L{cimri.api.cimriservice.data.merchantitem.MerchantItem}

                                  "meta.refitem" 	        : test islemleri icin kullanilacak referans item bilgileri
								  L{cimri.api.cimriservice.data.merchantitem.MerchantItem}

		task.meta	:
				  "cache.read"			: eger bu opsiyon varsa islem bilgileri cache'den
								  alinacaktir. eger opsiyonun bir degeri varsa
								  cache'in o bolumu kullanilir, eger opsiyonun
								  bir degeri yoksa genel cache kullanilir.

				  "cache.write"			: eger bu opsiyon varsa islem sonuclar cache'e
								  yazilacaktir. eger opsiyonun bir degeri varsa
								  cache'in o bolumu kullanilir, eger opsiyonun
								  bir degeri yoksa genel cache kullanilir.

                 		  "untrained"			: eger bu opsiyon varsa ogernilmis egitim bilgileri
								  kullanilmaz

                 		  "train"			: eger bu opsiyon varsa operasyon bilgileri icerisinde
								  saglanan referans bilgileri ile sistem egitilir.

                 		  "train.uuid"			: sistem egitimi bilgilerini kayit etmek icin referans IDsi

				  "validate_trained"		: herhangi bir merchant itemlari uzerinde scrape islemi yapmadan
								  once o merchant'in egitimli olup olmadigini kontrol et.
								  eger egitimli ise once o merchant'i test edip egitim parametrelerinin
								  hala gecerli olup olmadigina karar ver, gerekirse egitimi gecersiz
								  olarak guncelle.

 				 "ignore_non_active"		: eger bir item cimri servis'te matched ve aktif degilse isleme alma	

 				 "ignore_not_approved"		: eger bir merchant egitimli degilse ya da egitim bilgileri onayli degilse
								  o merchantin itemlarini scrape islemine alma		

				 "passthrough_not_approved"	: eger bir merchant egitimli degilse ya da egitim bilgileri onayli degilse
								  o merchantin itemlarini scrape islemine alma fakat scrape islemi 
								  sonuclarinda item'in xml bilgilerini kullanarak dahil et	
				
				  "test"			: eger bu opsiyon var ve True ise islem bir test islemi olarak
								  calistirilir.

				  "test.uuid"			: test IDsi

                task.result     : islemden gecirilen her item icin "data" scrape edilmis bilgileri iceren MerchantItem objecti 
				  olacaktir. bunun yaninda her item icin asagidaki bilgiler de olacaktir:

				  "meta.refitem" 		: eger bu islem bir test islemi ise, saglanan referans
								  MerchantItem'i icerir

				  "meta.scrapitem"		: sadece scrape edilen bilgileri iceren bir MerchantItem kopyasini
								  icerir. item icin scrape isleminden once varolan bilgiler bu
								  object icinde yer almaz.
	"""


	def __init__(self):

		#initialize parents
		Web.__init__(self)
		Scrapper.__init__(self)
		
		self.logger=Logger(self.__class__.__name__)

		#supported operations
		self.ops={"scrap"		:self._task_scrap}

		#test mode
		self.test=False

		#data to work on
		self.html=None			#original html	
		self.dom=None			#dom structure of html
		self.targets=None		#target nodes to look at for potential data
		self.spec=None			#spec to use
		self.hints=None			#hints to use
		self.P=None			#probabilities to use	
		self.S=None			#statistics used for machine learning

		#do not log url error for scrapper
		self._log_url_faults=False

	@defer.inlineCallbacks
	def _task_scrap(self):
                """
		"scrap" islemini gerceklestirir
                """

		self.logger.info("api call...")

		#get # of workers
		workers=int(self.task.meta["workers"]) if "workers" in self.task.meta else 1

		#run in test mode?
		self.test=("test" in self.task.meta and self.task.meta["test"] is True)  
		self.task.stats["test"]["fields"]={}	#track accuracy of each scraped field (for testing mode)

		#run training?
		self.train=("train" in self.task.meta and self.task.meta["train"] is True)  

		#get other task options
		self.ignore_none_active=("ignore_none_active" in self.task.meta and self.task.meta["ignore_none_active"] is True)  
		self.ignore_not_approved=("ignore_not_approved" in self.task.meta and self.task.meta["ignore_not_approved"] is True)  
		self.passthrough_not_approved=("passthrough_not_approved" in self.task.meta and self.task.meta["passthrough_not_approved"] is True)  

		#keep track of price stats
		self.price_stats={}

		#keep track of merchants processed and errors accessing merchant pages
		self.url_access_stats={}
		
		#get cache section to use, if any
		cache={}
		if "cache.read" in self.task.meta:
			cache["read"]=self.task.meta["cache.read"]
		if "cache.write" in self.task.meta:
			cache["write"]=self.task.meta["cache.write"]

		#initialie product spec
		self._init_spec()

		#init stats
		if self.train:
			self._init_stats()

		#oncomplete handler
		def oncomplete():
			#finalize training
			if self.train:
				self._training_finalize()

			#finalize tests
			if self.test:
				self._test_finalize()

			#record price accuracies
			self._record_price_accuracy()
			
			#record url access errors
			self._record_access_errors()

			#mark as completed
			self._complete()

		#check if a merchant item is active and matched in cimri catagloru
		def isactive(item):
			#if the item is not in cimri catalogue, it's not matched yet
			if item.merchantItemId not in self._merchant_items[item.merchant["merchantId"]]:
				return False

			#check if the item is active 
			return self._merchant_items[item.merchant["merchantId"]][item.merchantItemId].is_matched()

		#scrap
		@defer.inlineCallbacks
		def scrapitem(item,work):
			try:
				#get item url
				url=item["data"]	

				#if item is not active, do not process it
				if self.ignore_none_active is True and isactive(item["meta.xmlitem"]) is False:
					#done with item
					self._progress()
					work.next()
					return

				#get merchant record	
				MerchantScraperRecord.connectdb()
				rec=None
				try:
					rec=MerchantScraperRecord.get(merchantid=int(item["meta.xmlitem"].merchant["merchantId"]))
				except Exception as e:
					pass

				#check options
				if self.ignore_not_approved and (rec is None or rec.is_approved is False):
					#ignore item
					self._progress()
					work.next()
					return

				if self.passthrough_not_approved and (rec is None or rec.is_approved is False):
					#add to results
					result={"data":item["meta.xmlitem"]}
					if self.test:
						result["meta.scrapitem"]=None
						result["meta.refitem"]=item["meta.refitem"]
					self.task.result.append(result)			
		
					#done with item
					self._progress()
					work.next()
					return

				#init url access stat for merchant
				if item["meta.xmlitem"].merchant["merchantId"] not in self.url_access_stats:
					self.url_access_stats[item["meta.xmlitem"].merchant["merchantId"]]={"tout":0,"total":0}

				#if too many time outs happened for this merchant's urls, bypass merchant
				touts=self.url_access_stats[item["meta.xmlitem"].merchant["merchantId"]]["tout"]
				total=self.url_access_stats[item["meta.xmlitem"].merchant["merchantId"]]["total"]
				if total>10 and float(touts)/total>0.3:
					#done with item
					self._progress()
					work.next()
					return		

				#update stats for merchant
				self.url_access_stats[item["meta.xmlitem"].merchant["merchantId"]]["total"]+=1

				#load
				self._benchmark_start("load")
				self.logger.info("opening url: %s",url)
				res=yield self._get_page(url,cache=cache)
				if res.error is not None:
					#log error
#	                                msg=Template("error opening url: $url").substitute(url=url)
#        	                        self._log_error(msg)
				
					#update scraper record
					if res.error.code is None:
	 				      	self._log_scraped_item(item["meta.xmlitem"],None,"http error")
					else:
	 				      	self._log_scraped_item(item["meta.xmlitem"],None,"http "+str(res.error.code))

					#record error
					if res.error.code is None:
						self.url_access_stats[item["meta.xmlitem"].merchant["merchantId"]]["tout"]+=1

				else:	
					self._benchmark_record("load")

					#set html
					self.html=res.content
					
					#preprocess
					self._benchmark_start("preprocess")
					self._preprocess()
					self._benchmark_record("preprocess")

					#parse
					self._benchmark_start("parse")
					self._parse()
					self._benchmark_record("parse")

					#get hints
					self._compile_hints(item["meta.xmlitem"])

					#select target nodes
					self._benchmark_start("targets")
					self._init_targets()
					self._benchmark_record("targets")

					#compile proximity graph
					#self._compile_proximity_graph()

					#compile fractal coordinates
					self._benchmark_start("fractals")
					self._compile_fractal_coordinates()
					self._benchmark_record("fractals")

					#match/train
					if self.train:
						self._train(item["meta.refitem"])
						match=None
					else:
						#initialize probabilities
						self._init_probabilities(item["meta.merchantid"])

						self._benchmark_start("match")
						match=self._match()
						self._benchmark_record("match")

					#construct scrapped and result merchant items (result=scrapped+hints)
					scrapitem=None
					resultitem=None
					if match is not None:
						scrapitem=MerchantItem()
						resultitem=MerchantItem()

						#add scraped data
						for field in match:
							#get value
							val=match[field]

							#extract currency values
							if field in ["pricePlusTax","priceEft"]:
								val=extract_currency(val)

							#record price stats
							if field == "pricePlusTax":
								self._record_price_stats(item["meta.merchantid"],item["meta.xmlitem"],val)

							setattr(scrapitem,field, val)
							setattr(resultitem,field, val)

						#add meta data
						resultitem.merchant={"merchantId":item["meta.merchantid"]}
						for field in ["merchantItemId","merchantItemUrl"]:
							setattr(resultitem,field,getattr(item["meta.xmlitem"],field))
					
						#set result
						result={"data":resultitem}

						#add data for testing
						if self.test:
							result["meta.scrapitem"]=scrapitem
							result["meta.refitem"]=item["meta.refitem"]
			
						#add result
						self.task.result.append(result)

					#log results
 				      	self._log_scraped_item(item["meta.xmlitem"],scrapitem,"ok")

					#comparison test
					if self.test:
						self._test_update(scrapitem,item["meta.refitem"])		
									
					#log analysis
					self._log_fractal_analysis()
	
                        except Exception as e:
                                data=Template("url: $url").substitute(url=url)
                                self._log_exception(e,data=data)

			#update progress		
			self._progress()

			#next item
			work.next()

		#initialize progress tracker
		self._progress(len(self.task.data))

		#distribute tesk
		d=Distributor(scrapitem,oncomplete=oncomplete,workers=workers)
		d.run()

		#clear merchant item cache
		self._merchant_items={}		#items by merchant (from cimri)
	
		#get all existing merchant items from the cimri service
		if self.ignore_none_active is True:
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
				id=item["meta.xmlitem"].merchant["merchantId"]
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

		#add data and complete when all data is processed
		d.adddata(self.task.data)
		d.complete()	

		#log performance benchmark	
		self._log_benchmark()



	def _get_page(self,url,cache):
		"""
		Bir web sayfasinin icerigini indirir

		@type url: str
		@param url: indirilecek URL

		@type cache: bool
		@param cache: True ise operasyon icin cache kullanilir

		@rtype: L{twisted.internet.defer.Deferred}
		@return: sonuclari alicak Deferred objecti
		"""

		return deferToThread(self.get,url,cache,timeout=10.0)


        def _preprocess(self):
                """
		Scrape edilecek itemin web sayfasini onislemden gecirir.
                """

		#strip js, css, comments,...
                for func in [pattern.web.strip_javascript, pattern.web.strip_inline_css, pattern.web.strip_comments]:
                        self.html=func(self.html)


	def _parse(self):
                """
		Scrape edilecek itemin web sayfasini html olarak parse eder.
                """

		#parse the dom
		self.dom=pattern.web.Document(self.html)


	def _compile_hints(self,item):
                """
		Scrape islemine yardimci olmasi icin item'in daha onceden bilinen bazi bilgilerini islem icin kayit eder.

                @type  item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param item: MerchantItem objecti
                """

		#initialie hints
		self.hints=[]

		#get merchant xml hints
		if item.merchantItemTitle is not None and item.merchantItemTitle.strip()!="":
			self.hints.append({"source":"xml", "field":"merchantItemTitle", "value":item.merchantItemTitle})		
		if item.mpnValue is not None and item.mpnValue.strip()!="":
			self.hints.append({"source":"xml", "field":"mpnValue", "value":item.mpnValue})		
		if item.brand is not None and item.brand.strip()!="":
			self.hints.append({"source":"xml", "field":"brand", "value":item.brand})		

		#get html header hints
		try:
			pass
			#self.doc.head.by_tag("title")[0].content

		except:
			pass

		#get item url hints



	def _init_targets(self):
                """
		Scrape islemi icin urun web sitesi html icerisindeki DOM elementlerini hazirlar.
                """

		#nodes that will be targeted for matching
		self.targets=[]		

		#collect targets
		def add_target(node):
			if node.type=="text":	
				text=pattern.web.plaintext(unicode(node)).strip()
				text=remove_non_alphanumeric(replace_turkish_chars(text))
				if text!="":	
					#add attribute to store match data
					node._match={}			

					#add to target list		
					self.targets.append(node)

			return None

		#traverse the dom
		self.dom.body.traverse(add_target)


	def _compile_proximity_graph(self):
                """
		Urun web sitesi html'i icerisindeki DOM elementlerinin birbirlerine DOM structure icindeki yakinligini olcebilmek icin
		gerekli yapiyi olusturur.
                """

		#getid() function for a Node:	traverses the node's parents and generates
		#				a unique id in th form of n0.n1.n2....
		#				where each entry is the index of the each
		#				parent node in the hierachy among its siblings
		#				(check if a unique id already exists for Node)	
                def getparents(node):
                        n=node
                        while not (n.type=='element' and n.tag=='body'):
                                yield n
                                n=n.parent
                for target in self.targets:
                        tree=[str(node.parent.children.index(node)) for node in getparents(target)]
                        tree.reverse()
                        target.proximity_id=".".join(tree)


	def _compile_fractal_coordinates(self):
                """
		Urun web sitesi html'i icerisindeki DOM elementleri icin birbirlerine DOM structure icindeki yakinliklarini olcmek icin
		kullanilabilecek koordinatlar hesaplar.
                """

		def getparents(node):
 			n=node
			while not (n.type=='element' and n.tag=='body'):
				yield n
				n=n.parent

		for target in self.targets:	
			#fractal coordinates are not currently being used. set them to a constant value to save up on exectuion time
			target._fx=1.0
			continue

			tree=[(len(node.parent.children),node.parent.children.index(node)) for node in getparents(target)]
			tree.reverse()
			sum=0
			coordinates=(0,1)
			for dim in tree:
				unit=float(coordinates[1]-coordinates[0])/(dim[0]+1)
				sum=sum+coordinates[0]+unit*dim[1]
				coordinates=(0,unit)

			target._fx=sum

		return


		#the follwoing version computes the fractal coordinates by traversing the dom tree.
		#for some reason when the coordinate values are assigned to nodes this way, the 
		#node references within the self.targets list do not always have the coordinates
		#attribute.

		#set the fractal coordinates for a dom node's children given a coordinate range (min,max) 
		def set_fractal_coordinates(node,coordinates):
			#set coordinate
			node._fx=coordinates[0]

			#if no children, done
			if len(node.children)==0:
				return

			#coordinate space for the children nodes
			unit=float(coordinates[1]-coordinates[0])/(len(node.children)+1)
			coordinates=(coordinates[0]+unit,coordinates[0]+2*unit)

			#set children coordinates
			for child in node.children:
				set_fractal_coordinates(child,coordinates)
				coordinates=(coordinates[1],coordinates[1]+unit)
	
		#go
		set_fractal_coordinates(self.dom.body,(0,1))



	def _get_proximity(self,node_a,node_b):
                """
		Iki DOM node arasinda cesitli yakinlik metriklerini hesaplar

                @type  node_a: object
                @param node_a: DOM node

                @type  node_b: object
                @param node_b: DOM node

                @rtype: dict
                @return: cesitli yakinlik metrikleri
                """

		#proxmity criteria between two nodes are:
		#-closeness:		avg. proximity to common parent (smaller the better)
		#-level symmetry:	same proximity to common parent 
		#-structural symmetry:	parents at same levels have the same #of children 
		#-pattern symmetry:	parents	at same levels have the same indecies within their siblings

		#get the hierarchy trees for each node
		tree_a=[int(index) for index in node_a.proximity_id.split(".")]
		tree_b=[int(index) for index in node_b.proximity_id.split(".")]

		#find the common ancestor of the two nodes
		tree_common=[(pair[0] if pair[0]==pair[1] else None) for pair in zip(tree_a,tree_b)]
		tree_common=tree_common[:tree_common.index(None)] if None in tree_common else tree_common
		node_common=self.dom.body
		for index in tree_common:
			node_common=node_common.children[index]

		#find closeness
		closeness=(len(tree_a[len(tree_common):])+len(tree_b[len(tree_common):]))/2

		#find level symmetry		
		level_symmetry=abs(len(tree_a)-len(tree_b))

		#find structural symmetry
		structural_symmetry=[]
		parent_a=node_common
		parent_b=node_common
		for pair in zip(tree_a[len(tree_common):],tree_b[len(tree_common):]):
			structural_symmetry.append(len(parent_a.children[pair[0]])==len(parent_b.children[pair[1]]))		
			parent_a=parent_a.children[pair[0]]
			parent_b=parent_b.children[pair[1]]

		#find pattern symmetry
		pattern_symmetry=[abs(pair[0]-pair[1]) for  pair in zip(tree_a[len(tree_common):],tree_b[len(tree_common):]) ]
		
		return {"closeness"		: closeness,
			"symmetry"		:    
				{"level" 	: level_symmetry,
				 "structural"	: structural_symmetry,
				 "pattern"	: pattern_symmetry }}


	def _init_spec(self):
                """
		Islem icin kullanilacak urun spec bilgilerini hazirlar.
                """

		self.spec=ProductSpec()


	def _match(self):
                """
		Aranan urun bilgilerini urun sayfasinda bulmaya calisir.		

                @rtype: dict
                @return: bulunan bilgiler
                """

		#classify nodes (based on the specs and hints)
		self._classify_nodes()		

		#check if the reference pattern has enough unique anchors
		threshold=3
		hints=[(node._match["label"] if node._match["label"] is not None else node._match["hint"]) for node in self.pattern]
		if len(list(set(hints)))<=threshold:
			return None

		#compute probabilities
		self._compute_probabilities()

		#pick values
		match=self._pick_values()
		#match=self._match_pattern()

		#postprocess match
		for field in match:
			if match[field] is not None and "content" in match[field]._match:
				#inline match
				match[field]=match[field]._match["content"]

				#process inline currency
				if field in ["pricePlusTax","priceEft"]:
					#pick the first non-all-text chunk
					tokens=match[field].split(" ")
					tokens.reverse()
					match[field]=""
					for token in tokens:
						if remove_non_numeric(token).strip()!="":
							match[field]=token
							break
			else:
				match[field]=replace_turkish_chars(unicode(match[field])) if match[field] is not None else None

			if match[field] is not None:
				match[field]=match[field].replace("&nbsp;",'').replace("\n",'').replace("\t",' ').strip()
			#	match[field]=pattern.web.plaintext(unicode(match[field])).strip()
		

				#check if field has any conversions
				fieldef=self.spec.get_field(field)
				if "conversions" in fieldef["values"]:
					val = None
					for key in fieldef["values"]["conversions"]:
						index = self._find_ignore_spaces( match[field].lower(), key )
						if index is not None:
							val=fieldef["values"]["conversions"][key]
							break
					match[field]=val

		return match



	def _train(self,refitem):
                """
		Bir referans item'a dayali olarak sistem egitim bilgileri hesaplar

                @type  refitem: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param refitem: referans olarak kullanilacak MerchantItem
                """

		#classify nodes (based on the specs and hints)
		self._classify_nodes()		

		#update stats
		self._update_stats(refitem)



	def _classify_nodes(self):
                """
		Urun html sayfasindaki DOM elementlari urun spec kurallarina bagli olarak tasiyabilecekleri bilgilere gore siniflandirir
                """

		#store pattern
		self.pattern=[]

		#get product spec keywords
		keywords=self.spec.get_keywords()
	
		#get types
		types=self.spec.get_types()

		# tranform each keyword and create a mapping between the transformation and the keyword
		#	.nonturkish version (replace_turkish_chars) 	
		#	.remove_non_alphanumeric
		#	.lowercase
		transformations=dict([ (remove_non_alphanumeric(replace_turkish_chars(keyword)).lower(),{"type":"spec","value":keyword})  for keyword in keywords])

		#add meta hints to transformations
		for hint in self.hints:
			transformations[ remove_non_alphanumeric(replace_turkish_chars(hint['value'])).lower() ]={"type":"hint","value":hint['field']}
		
		#match each target node against spec label hints, spec field value hints, spec type hints
		#and meta hints (xml item info,...)
		for node in self.targets:
			#transform text to match
			text=replace_turkish_chars(pattern.web.plaintext(unicode(node))).lower()

			#match keyword
			match=self._match_keyword(text,transformations,[])

			if match is None:
				#record match
				node._match["label"]=None
				node._match["hint"]=None
				node._match["score"]=0
				node._match["inline"]=False

			else:
				#get match result
				transformation=match[0]
				score=match[1]		

				#lookup keyword based on the transformation
				keyword=transformations[transformation]			

				#record match
				node._match["score"]=score
				node._match["inline"]=not match[2]

				#get the field matched
				field=self.spec.get_field_by_keyword(keyword['value'])
				fieldef=self.spec.get_field(field)

				#if this was an inline match that matched a numeric field but there are fewer than 3 numeric chacters, void the match
				if match[3] is not None and set(fieldef["values"]["type"]).isdisjoint(["number","currency"]) is False and len(remove_non_numeric(match[3]).strip())<4:
					node._match["label"]=None
					node._match["hint"]=None
					node._match["score"]=0
					node._match["inline"]=False

				else:
					#get content for inline matches
					if match[3] is not None:
						#get content dependeing on whether this field has conversions or not
						if "conversions" in fieldef["values"]:
							node._match["content"]=match[0]
						else:
							node._match["content"]=match[3]	

					if keyword['type']=="spec":
						#lookup field (get_field) based on the keyword
						node._match["label"]=field
						node._match["hint"]=None	

					else:
						node._match["hint"]=keyword['value']
						node._match["label"]=None

				#record pattern
				self.pattern.append(node)

			#match type
			typ=self._match_type(text,types)

			#record match
			node._match["type"]=typ



	def _init_probabilities(self,merchantid):
                """
		Urun html sayfasindaki DOM elementlari icin olasilik hesaplarini initialize eder

                @type merchantid: str
                @param merchantid: item ile ilgili merchant IDsi
                """

		#init probabilities 
		self.P={}

		#load training based probabilities
		Pt=self._training_load(merchantid)

		#for each field
		fields=self.spec.get_fields()
		for key in fields:
			#get field
			field=self.spec.get_field(key)

			#init field probability distributions
			self.P[key]=[]
			
			#default type match probability distribution
			p={}
			for t in field["values"]["type"]:
				p[t]=1.0/len(field["values"]["type"])
			#use ML probabilities if available
			if Pt is not None and "default" in Pt[key]["match"]:
				p=Pt[key]["match"]["default"] 
			self.P[key].append( (self._p_type_match, {"default":p}) )

			#default probability distribution based on distance from associated labels
			p={-2: 0.1, 
			   -1: 0.2, 
			    1: 0.4, 
		 	    2: 0.2, 
			    3: 0.1}
			#use ML probabilities if available
			if Pt is not None and "default" in Pt[key]["distance"]:
				p=Pt[key]["distance"]["default"] 
			self.P[key].append( (self._p_label_distance, {"default":p}) )

			#default probability distribution based on whether there's an overlap
			#(overlap == another node between node and associated label)
			p={True : 0, 
		 	   False: 1.0}
			#use ML probabilities if available
			if Pt is not None and "default" in Pt[key]["overlap"]:
				p=Pt[key]["overlap"]["default"] 
			self.P[key].append( (self._p_overlap, {"default":p}) )
		
			#default probability distribution for inline hints
			p={True : 0, 
			   False: 1.0}
			#use ML probabilities if available
			if Pt is not None and "ends_with_colon" in Pt[key]["hints"]:
				p=Pt[key]["hints"]["ends_with_colon"] 
			self.P[key].append( (self._p_inline_hints, {"ends_with_colon":p}) )

			#default probability distribution for proximities
			#(proximity == densitiy of hints within a certain radius)
                  	p={0    : 0,	# 0.01 > n >= 0 		
			   0.01 : 0.01,	# 0.08 > n >= 0.01
			   0.08 : 0.03,	# 0.15 > n >= 0.08
		           0.15 : 0.05,	# 0.25 > n >= 0.15
		           0.25 : 0.15,	# 0.33 > n >= 0.25
		           0.33 : 0.3,	# 0.50 > n >= 0.33
	                   0.5  : 0.5}	#        n >= 0.5
			#use ML probabilities if available
			if Pt is not None and "default" in Pt[key]["proximity"]:
				p=Pt[key]["proximity"]["default"] 
			self.P[key].append( (self._p_proximity,{"default":p}) )


	def _init_stats(self):
                """
		Sistem egitimi icin gerekli istatistikleri initialize eder.
                """

		#init stats
		self.S={}

		#for each field
		fields=self.spec.get_fields()
		for key in fields:
			#get field
			field=self.spec.get_field(key)

			#init field stats
			self.S[key]={}
			
			#type match stats
			s={}
			for t in field["values"]["type"]:
				s[t]=0
			self.S[key]["match"]={"func": self._s_type_match, "stats": {"default":s}}

			#stats for distance from associated labels
			s={-2: 0, 
			   -1: 0, 
			    1: 0, 
		 	    2: 0, 
			    3: 0}
			self.S[key]["distance"]={"func": self._s_label_distance, "stats": {"default":s}}

			#overlap stats
			#(overlap == another node between node and associated label)
			s={True : 0, 
		 	   False: 0}
			self.S[key]["overlap"]={"func": self._s_overlap, "stats": {"default":s}}
		
			#inline hint stats
			s={True : 0, 
			   False: 0}
			self.S[key]["hints"]={"func": self._s_inline_hints, "stats": {"ends_with_colon":s} }

			#proximity stats
			#(proximity == densitiy of hints within a certain radius)
                  	s={0    : 0,	# 0.05 > n >= 0 		
			   0.05 : 0,	# 0.15 > n >= 0.05
		           0.15 : 0,	# 0.25 > n >= 0.15
		           0.25 : 0,	# 0.33 > n >= 0.25
		           0.33 : 0,	# 0.50 > n >= 0.33
	                   0.5  : 0}	#        n >= 0.5
			self.S[key]["proximity"]={"func": self._s_proximity, "stats": {"default":s}}


	
	def _p_type_match(self, index, field, p):
		"""
		urun spec "type" bilgilerine dayanarak bulunabilecek bir matchin olasigini hesaplar

                @type  index: int
                @param index: bakilacak node'un DOM listesi icindeki indexi

                @type  field: dict
                @param field: olasilik hesabi yapilacak field

                @type  p: dict
                @param p: probability distribution
                """

		#get node
		node=self.targets[index]

		#if the current probability is 0, no need to process
		if node._match["P"][field["field"]] == 0:
			return

		#get probability
		p=p["default"]
		if node._match["inline"] is True:
			P=1.0
		elif node._match["type"] not in p:
			P=0
		else:
                     	P=p[node._match["type"]]

		#update probability
		node._match["P"][field["field"]] = P * node._match["P"][field["field"]]		
	
	

	def _p_label_distance(self, index, field, p):
		"""
		urun spec "label" bilgilerine ve bu bilgileri iceren node'lara uzakliga dayanarak bulunabilecek bir matchin olasigini hesaplar

                @type  index: int
                @param index: bakilacak node'un DOM listesi icindeki indexi

                @type  field: dict
                @param field: olasilik hesabi yapilacak field

                @type  p: dict
                @param p: probability distribution
                """

		#get node
		if index<0 or index>=len(self.targets):
			return
		node=self.targets[index]

		#if the current probability is 0, no need to process
		if node._match["P"][field["field"]] == 0:
			return

		#inline?
		if node._match["inline"] is True and node._match["label"] == field["field"]:
			P=1.0
		else:
			#find the probability for the nearest matching label
			p=p["default"]
			radius=5
			P=0
			for i in range(1,radius):
				if index-i>=0 and self.targets[index-i]._match["label"] == field["field"]:
					if i in p:	
						P=p[i]
					break

				if index+i<len(self.targets) and self.targets[index+i]._match["label"] == field["field"]:
					if -i in p:	
						P=p[-i]
					break

		#update probability
		node._match["P"][field["field"]] = P * node._match["P"][field["field"]]		




	def _p_overlap(self, index, field, p):
		"""
		DOM yapisi icinde bir bir urun spec field'ina denk gelen bir labela uyan bir node ile o field'a denk gelen bir node
		arasinda baska bir spec fieldina denk gelen bir node olup olmadigina gore overlap olasiligini hesaplar.

                @type  index: int
                @param index: bakilacak node'un DOM listesi icindeki indexi

                @type  field: dict
                @param field: olasilik hesabi yapilacak field

                @type  p: dict
                @param p: probability distribution
                """

		#get node
		node=self.targets[index]

		#if the current probability is 0, no need to process
		if node._match["P"][field["field"]] == 0:
			return

		#get probability
		p=p["default"]
		P=1.0

		#update probability
		node._match["P"][field["field"]] = P * node._match["P"][field["field"]]		



	def _p_inline_hints(self, index, field, p):
		"""
		scrape isleminden once merchant item icin onceden varolan bilgilere dayanarak olasilik hesaplari yapar

                @type  index: int
                @param index: bakilacak node'un DOM listesi icindeki indexi

                @type  field: dict
                @param field: olasilik hesabi yapilacak field

                @type  p: dict
                @param p: probability distribution
                """

		#get node
		node=self.targets[index]

		#if the current probability is 0, no need to process
		if node._match["P"][field["field"]] == 0:
			return

		#process each rule
		P=1.0

		#"ends with colon" rule
		p1=p["ends_with_colon"]
		val=pattern.web.plaintext(unicode(node)).strip().endswith(":")
		P=P*p1[val]

		#if there was an inline match, ignore the inline hints
		if node._match["inline"] is True:
			P=1.0

		#update probability
		node._match["P"][field["field"]] = P * node._match["P"][field["field"]]		



	def _p_proximity(self, index, field, p):
		"""
		DOM yapisi icindeki node'larin yakinlik olculerine dayanarak olasilik hesaplari yapar

                @type  index: int
                @param index: bakilacak node'un DOM listesi icindeki indexi

                @type  field: dict
                @param field: olasilik hesabi yapilacak field

                @type  p: dict
                @param p: probability distribution
                """

		#get node
		node=self.targets[index]

		#if the current probability is 0, no need to process
		if node._match["P"][field["field"]] == 0:
			return
	
		#get proximity (density)
		radius=10
		count=0
		for n in self.targets[index-radius:index+radius]:
			if n._match["hint"] is not None or n._match["label"] is not None:
				count=count+1
		proximity=(1.0*count)/(2*radius+1)

		#get probability
		P=0
		l=-1
		p=p["default"]
		for level in p:
			if proximity>level and level>l:
				l=level
				P=p[level]

		#update probability
		node._match["P"][field["field"]] = P * node._match["P"][field["field"]]		


	def _s_type_match(self, index, field):
		"""
		urun spec "type"larina dayanan istatistikleri kayit eder

                @type  index: int
                @param index: bakilacak node'un DOM listesi icindeki indexi

                @type  field: dict
                @param field: istatistikler icin gozden gecirilecek field
                """

		#get node
		node=self.targets[index]
		
		#get stats
		stats=self.S[field["field"]]["match"]["stats"]["default"]

		#record stat
		if node._match["type"] in stats:
			stats[node._match["type"]]=stats[node._match["type"]]+1
	


	def _s_label_distance(self, index, field):
		"""
		DOM yapisi icinde node'larin birbirlerine olan yakinlik metriklerine dayanan istatistikleri kayit eder

                @type  index: int
                @param index: bakilacak node'un DOM listesi icindeki indexi

                @type  field: dict
                @param field: istatistikler icin gozden gecirilecek field
                """

		#get node
		node=self.targets[index]

		#get stats
		stats=self.S[field["field"]]["distance"]["stats"]["default"]

		#record stats
		for dist in stats:
			if (index-dist)<0 or (index-dist)>=len(self.targets):
				continue
			if self.targets[index-dist]._match["label"] == field["field"]:
				stats[dist]=stats[dist]+1
	

	def _s_overlap(self, index, field):
		"""
		DOM yapisi icinde bir bir urun spec field'ina denk gelen bir labela uyan bir node ile o field'a denk gelen bir node
		arasinda baska bir spec fieldina denk gelen bir node olup olmadigina gore istatistikler kayit eder.

                @type  index: int
                @param index: bakilacak node'un DOM listesi icindeki indexi

                @type  field: dict
                @param field: istatistikler icin gozden gecirilecek field
		"""

		#get node
		node=self.targets[index]

		#get stats
		stats=self.S[field["field"]]["overlap"]["stats"]["default"]



	def _s_inline_hints(self, index, field):
		"""
		scrape isleminden once merchant item icin onceden varolan bilgilere dayanan istatistikleri kayit eder

                @type  index: int
                @param index: bakilacak node'un DOM listesi icindeki indexi

                @type  field: dict
                @param field: istatistikler icin gozden gecirilecek field
                """

		#get node
		node=self.targets[index]

		#get stats
		stats=self.S[field["field"]]["hints"]["stats"]

		#record stats
		if pattern.web.plaintext(unicode(node)).strip().endswith(":"):
			stats["ends_with_colon"][True]=stats["ends_with_colon"][True]+1
		else:
			stats["ends_with_colon"][False]=stats["ends_with_colon"][False]+1



	def _s_proximity(self, index, field):
		"""
		DOM yapisi icinde node'larin birbirlerine olan yakinliklarini olcen cesitli metriklere dayanan istatistikleri kayit eder

                @type  index: int
                @param index: bakilacak node'un DOM listesi icindeki indexi

                @type  field: dict
                @param field: istatistikler icin gozden gecirilecek field
                """

		#get node
		node=self.targets[index]

		#get stats
		stats=self.S[field["field"]]["proximity"]["stats"]["default"]
	
		#get proximity (density)
		radius=10
		count=0
		for n in self.targets[index-radius:index+radius]:
			if n._match["hint"] is not None or n._match["label"] is not None:
				count=count+1
		proximity=(1.0*count)/(2*radius+1)

		#record stat
		keys=stats.keys()
		max=0
		for key in keys:
			if proximity>key:
				stats[key]=stats[key]+1



	def _compute_probabilities(self):
                """
		urun html DOM yapisi icinde butun node'lar icin olasilik hesaplarini yapar ve kayit eder
                """

		#init list of targets to take into consideration (nodes within a radius of anchor nodes)
		targets=[]
		radius=10

		#gather list of nodes to take into consideration (nodes within a radius of anchor nodes)
		buffer=[]
		last=-radius-1
		for index in range(len(self.targets)):
			#get node
			node=self.targets[index]

			#check if the node is an anchor
			if node._match["hint"] is not None or node._match["label"] is not None:
				#flush the buffer
				targets.extend(buffer)
				buffer=[]
				
				#add node to list
				targets.append(index)

				#update the 'last anchor' index
				last=index

			#if this node is within the specified radius of nodes following the last anchor, add to list
			elif (index-last)<=radius:
				#add node to list
				targets.append(index)

			#store node in a moving buffer in case an anchor node is found later
			else:	
				#add to buffer
				buffer.append(index)

				#make sure buffer doesn't have more than the radius
				buffer=buffer[-radius:]


		#get processed spec keywords
		keywords=self.spec.get_keywords()
		keywords=dict([ (remove_non_alphanumeric(replace_turkish_chars(keyword)).lower(),True) for keyword in keywords])

		#evaluate targets for probabilities
		for index in targets:
			#check if the node text is matches a spec keyword exactly
			text=pattern.web.plaintext(unicode(node)).strip()
			text=remove_non_alphanumeric(replace_turkish_chars(text)).lower()
			iskeyword = text in keywords

			#get fields
			fields=self.spec.get_fields()

			#initialize probabilities
			self.targets[index]._match["P"]={}
			for key in fields:
				self.targets[index]._match["P"][key]=1.0 if iskeyword is False else 0
			
			#apply all probability distributions
			for key in self.P:
				for rule in self.P[key]:
					#get parameters
					func=rule[0]
					p=rule[1]
					field=self.spec.get_field(key)
				
					#evaluate
					func(index, field, p)


	def _update_stats(self,refitem):
                """
		referans item bilgilerine dayanarak urun html DOM yapisi icindeki node'larin istatistiklerini kayit eder

                @type refitem: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param refitem: referans olarak kullanilacak merchant item
                """

		#get fields
		fields=self.spec.get_fields()

		#find and record stats for each field
		for key in fields:
			#get field
			field=self.spec.get_field(key)

			#support parameter?
			if hasattr(refitem,key) is False:
				continue

			#is parameter set on the refitem?
			if getattr(refitem,key) is None or getattr(refitem,key)=="":
				continue
			
			#get reference value to search
			ref=unicode(getattr(refitem,key)).strip()

			#find nodes matching the refitem fields
			matches=[]
			for index in range(len(self.targets)):
				#get node
				node=self.targets[index]

				#compare
				if pattern.web.plaintext(unicode(node)).strip()==ref:
					matches.append(index)

			#update stats for each matched sample
			for index in matches:
				for typ in self.S[key]:
					#get funciton
					func=self.S[key][typ]["func"]

					#record
					func(index, field)



	def _pick_values(self):
                """
		yapilan analizlere dayanarak aranan bilgileri bulur		

                @rtype: dict
                @return: bulunan scrape bilgileri
                """

		#initialize match values
		P={}
		match={}

		#pick best matches
		for node in self.targets:
			if "P" not in node._match:
				continue

			for field in node._match["P"]:		
				if field not in match:
					P[field]=0
					match[field]=None
				if node._match["P"][field]>=P[field] and node._match["P"][field]>0:
					P[field]=node._match["P"][field]
					match[field]=node

		return match


     	def _match_keyword(self,text,corpus,filters):
                """
		bir html DOM node icerisinde keyword match arar

                @type  text: str
                @param text: match icin degerlendirilecek text

                @type  corpus: list
                @param corpus: keyword listesi

                @type  filters: list
                @param filters: dikkate alinmamasi gereken kelimler

                @rtype: tuple
                @return: eger bir match bulunduysa bulunan keyword, match skoru, match turu (True - exact, False - inline), ve
			 eger inline bir match ise inline bulunan bilgiyi iceren bir tuple, aksi takdirde None
                """

		#the match
		match=None

		#minimum match score to consider a match		
		score=0.5	

		#get match text
		search=remove_non_alphanumeric(text)

		#ignore filters
		search=" "+search+" "
		for filter in filters:
			search=search.replace(" "+remove_non_alphanumeric(replace_turkish_chars(filter))+" "," ")
		search=search.strip()	
		
		#try exact match against the corpus
		for word in corpus:		
			#check match
			if word.replace(' ','')==search.replace(' ','') or word.replace(' ','')+":"==search.replace(' ',''):
				return (word,1,True,None)

		#try inline match against the corpus (assuming the keyword represents a label)
		for word in corpus:		
			#check match
			index = self._find_ignore_spaces( text,  word.replace(' ','')+":" )
			if index is not None:
				return (word,1,False,text[index[1]+1:].strip())

		#try keyword match
		for word in corpus:		
			#tokenize the word and the corpus
			tokensA=[token for token in search.split(" ") if token!=""]
			tokensB=[token for token in word.split(" ") if token!=""]

			#find the set of common tokens
			count=len(set(tokensA+tokensB))
			if count==0:
				continue

			#subtract the mutually exclusive tokens from the count
			common=count - len(set(tokensA)-set(tokensB)) - len(set(tokensB)-set(tokensA))

	                #get the score
			wordscore=float(common)/count
	
			#a match?
			if wordscore>score:
				match=word
				score=wordscore	
			
		#return match
		if score > 0.7:
			return (match,score,True,None)
			
		#try endswith match against the corpus (assuming the keyword represents a label)
		#this is to catch content such as "10.34 TL KDV Dahil" where "KDV Dahil" is the label
		for word in corpus:		
			#check match
			index=self._find_ignore_spaces( text, word.replace(' ','') )
			if index is not None and index[1]+1==len(text):
				return (word,1,False,text[:index[0]])

		return None



     	def _match_type(self,text,types):
                """
		bir html DOM node'u urun spec tanimlari icinde olan data type'lar ile match etmeye calisir

                @type  text: str
                @param text: match icin degerlendirilecek text

                @type  types: dict
                @param types: type bilgileri

                @rtype: str
                @return: eger bir match bulunduysa bulunan type ("text", "number",...", aksi takdirde None
                """

		#processing flags
		has_currency_filters=False

		#detect and filter out currency filters
		search=text
		for filter in types["currency"]["hints"]:
			search=search.replace(replace_turkish_chars(filter),"")

		#any currency filters detected?
		if search!=text:
			has_currency_filters=True

		#if all the text has is space, newline, and/or nonalphanumerics, discard
		if text==remove_alpha_numeric(text) and text.strip()!="":
			return None		

		#remove non alphanumeric chars except for a few special one
		search=remove_non_alphanumeric(search.strip())	

		#numeric?
		numbase=remove_non_numeric(search)
		if numbase!="" and remove_numeric(search.strip().replace(".","").replace(",","")).strip()=="":
			if has_currency_filters:
				return "currency"
			else:
				return "number"

		#everything else is text by default
		return "text"	


	def _match_pattern(self):
                """
		kullanilmiyor
                """

		ptn=self._compile_match_pattern()
		if ptn is None:
			return None
		
		#find the fields matching the patterns
		match=self._match_pattern(ptn)
		return match


	def _compile_match_pattern(self):
                """
		kullanilmiyor
                """

		#minimum number of samples to match to identify a pattern	
		threshold=2
	
		#find the # of unique labels and hints matched
		labels=set()
		hints=set()
		samples=[]
		for target in self.targets:
			if target._match["label"] is not None:
				labels.add(target._match["label"])	
				samples.append(target)
			elif target._match["hint"] is not None:
				hints.add(target._match["hint"])					
				samples.append(target)

		#number of samples to ideally find in the pattern
		maxsamples=len(labels)+len(hints)
		
		#if less then a threshold, no match:
		if maxsamples<threshold:
			return None

		#find all qualifying contiguous patterns on the fractal coordinate space that:
		patterns=[]
		for first in range(len(samples)):
			#first element in the pattern
			ptn=[samples[first]]

			#rest of the pattern
			for sample in samples[first+1:]:
				#pattern needs to have a set of samples that matched a unique set of fields (each field only once)
				if sample._match["label"] is not None:
					if sample._match["label"] in (s._match["label"] for s in ptn):				
						break
					else:
						ptn.append(sample)

				elif sample._match["hint"] is not None:
					if sample._match["hint"] in (s._match["hint"] for s in ptn):				
						break
					else:
						ptn.append(sample)
			
				#can't have no more than the maximum number of samples
				if len(ptn)==maxsamples:
					break
				
			#can't have no fewer than the threshold number of samples
			if len(ptn)>=threshold:
				patterns.append(ptn)

		#any found?
		if len(patterns)==0:
			return None

		#pick the best pattern - TEMP
		patterns.sort(lambda a,b:len(b)-len(a))
		ptn=patterns[0]

		#mark the targets in the pattern
		for target in ptn:
			target._match["pattern"]=True

		#remove hints				
		ptn=[sample for sample in ptn if sample._match["label"] is not None]

		return ptn



	def _match_pattern(self,refptn):
                """
		kullanilmiyor
                """

		#get statistical data on the reference pattern
		spread=refptn[-1]._fx-refptn[0]._fx
		period=spread/len(refptn)

		#get sample space
		samples=[target for target in self.targets if target._fx>refptn[0]._fx-period and target._fx<refptn[-1]._fx+period]
		
		#disard samples that are also on the reference pattern
		samples=[sample for sample in samples if sample not in refptn]

		#find patterns 
		patterns=[]
		for first in range(len(samples)):
			ptn={}
			for sample in samples[first:]:
				#sample needs to have the corresponding type to the reference pattern sample				
				field=refptn[len(ptn)]._match["label"]
				if sample._match["type"] not in self.spec.get_field(field)["values"]["type"]:
					continue

				#add to pattern
				ptn[field]=sample

				#need to have the exact same number of samples as the reference pattern
				if len(ptn.keys())==len(refptn):
					patterns.append(ptn)
					break			

		#any found?
		if len(patterns)==0:
			return None

		#pick pattern -TEMP
		ptn=patterns[0]

		#mark the targets in the pattern
		for field in ptn:
			ptn[field]._match["match"]=field

		return ptn



	def _training_finalize(self):
                """
		sistem egitim islemini sonuclandirir.
                """

		#process data
		data={}
		for key in self.S:
			data[key]={}

			for p in self.S[key]:
				data[key][p]={}

				for id in self.S[key][p]["stats"]:
					#get stats
					stats=self.S[key][p]["stats"][id]

					#get # of samples
					count=0
					for P in stats:
						count=count+stats[P]
	
					#if there are no samples, do not record probabilities
					if count==0:
						continue

					#record probabilities
					data[key][p][id]={}
					for P in stats:
						data[key][p][id][P]=(1.0*stats[P])/count


		#save
		merchantid=self.task.data[0]["meta.merchantid"]
		f=open(os.path.join(Config.getconfig("SYS").get("ml_store_path"),str(merchantid)),"w")
		f.write(pickle.dumps(data))
		f.close()



	def _training_load(self,merchantid):
                """
		Daha once varolan training bilgilerini yukler

                @type  merchantid: str
                @param merchantid: merchant ID

                @rtype: object
                @return: training bilgileri ya da bulnmadiysa None
                """

		try:
			f=open(os.path.join(Config.getconfig("SYS").get("ml_store_path"),str(merchantid)),"r")
			content=f.read() 
			f.close()

			return pickle.loads(content)

		except:
			return None


	def _find_ignore_spaces(self, text, key):
		#returns (first, last) where first and last are the indices of the first and last characters matched in
		#text. if not found, returns None
		first=-1
		key=key.strip()
		ptr=0
		for i in range(len(text)):
			if text[i] in [" ","\n","\t"]:
				continue
			if text[i]==key[ptr]:
				if ptr==0:
					first=i
				if ptr==len(key)-1:
					return (first,i)
				ptr+=1			
			else:
				ptr=0

		return None
		


	def _record_price_stats(self,merchantid,xmlitem,price):
		try:
			if price is None or xmlitem.pricePlusTax is None or float(xmlitem.pricePlusTax)==0:
				return

			#get price difference
			diff=float(abs(price-float(xmlitem.pricePlusTax)))/float(xmlitem.pricePlusTax)

			#record
			if merchantid not in self.price_stats:
				self.price_stats[merchantid]={"5pct":0, "10pct":0, "count":0}
		
			self.price_stats[merchantid]["count"]+=1
			if diff<0.05:
				self.price_stats[merchantid]["5pct"]+=1
			if diff<0.10:
				self.price_stats[merchantid]["10pct"]+=1
	
		except Exception as e:
			pass


	def _record_price_accuracy(self):
		for mid in self.price_stats:
			#get merchant record	
			MerchantScraperRecord.connectdb()
			rec=None
			try:
				rec=MerchantScraperRecord.get(merchantid=int(mid))
			except Exception as e:
				pass
			if rec is None:
				rec=MerchantScraperRecord()
				rec.merchantid=int(mid)
				rec=rec.create()

			rec.price_accuracy={"5pct":  round(100*float(self.price_stats[mid]["5pct"])/self.price_stats[mid]["count"]),				
					    "10pct": round(100*float(self.price_stats[mid]["10pct"])/self.price_stats[mid]["count"])}				
	
			rec.save()


	def _record_access_errors(self):
		for mid in self.url_access_stats:
			#get merchant record	
			MerchantScraperRecord.connectdb()
			rec=None
			try:
				rec=MerchantScraperRecord.get(merchantid=int(mid))
			except Exception as e:
				pass
			if rec is None:
				rec=MerchantScraperRecord()
				rec.merchantid=int(mid)
				rec=rec.create()

			rec.errors={"access":self.url_access_stats[mid]["tout"]}
	
			rec.save()


	def _log_fractal_analysis(self):
                """
		islem analizini islem loguna yazar
                """

		self._log_task_msg("")
		self._log_task_msg("-fractal analysis------------------------------------------------------")

		#sort nodes by fractal coordinates
		self.targets.sort(lambda a,b: int(100000*a._fx-100000*b._fx))

		#print out the match stat plot:
		for node in self.targets:
			info=[]
			if "pattern" in node._match:
				info.append("***")
			if "match" in node._match:
				info.append("<"+node._match["match"]+">")
			if node._match["label"] is not None:
				info.append("LABEL: "+node._match["label"])
				info.append("SCORE: "+str(node._match["score"]))
				info.append("INLINE: "+str(node._match["inline"]))
			
			elif node._match["hint"] is not None:
				info.append("HINT: "+node._match["hint"])
				info.append("SCORE: "+str(node._match["score"]))
			if "P" in node._match:
				info.append("P: "+repr(node._match["P"]))

			log=Template("$fx $typ $info : $text").substitute(fx=node._fx,
									     typ=node._match["type"],
									     info="["+", ".join(info)+"]" if len(info)>0 else "",
									     text=pattern.web.plaintext(unicode(node)).strip() )
	
			#log
			self._log_task_msg(log)

		self._log_task_msg("------------------------------------------------------fractal analysis-")


        def _log_scraped_item(self,item,scrapeditem,status):
		def checkinfo(val):
			if val is None:
				return None
			else:
				return str(val)

		#get/create item record	
		MerchantItemScraperRecord.connectdb()
		rec=None
		mid=int(item.merchant["merchantId"])
		try:
			rec=MerchantItemScraperRecord.get(merchantid=mid,url=item.merchantItemUrl)
		except Exception as e:
			pass
		if rec is None:
			rec=MerchantItemScraperRecord()
			rec.merchantid=int(mid)
			rec.url=item.merchantItemUrl
			rec=rec.create()

		#update scrape info
		rec.info={}
		rec.updated=None
		rec.info["status"]=status
		rec.info["title"]=checkinfo(scrapeditem.merchantItemTitle) if scrapeditem is not None else None
		rec.info["brand"]=checkinfo(scrapeditem.brand) if scrapeditem is not None else None
		rec.info["model"]=checkinfo(scrapeditem.modelNameView) if scrapeditem is not None else None
		rec.info["mpn"]=checkinfo(scrapeditem.mpnValue) if scrapeditem is not None else None
		rec.info["price-plus-tax"]=checkinfo(scrapeditem.pricePlusTax) if scrapeditem is not None else None
		rec.info["price-eft"]=checkinfo(scrapeditem.priceEft) if scrapeditem is not None else None
		rec.info["in-stock"]=checkinfo(scrapeditem.inStock) if scrapeditem is not None else None
		rec.info["free-shipping"]=checkinfo(scrapeditem.freeShipping) if scrapeditem is not None else None
		rec.save()

		return

		def checkval(val):
			if val is None:
				return ""
			else:
				return str(val)

		#log to file
                fields=[str(item.merchant["merchantId"]),
                        item.merchantItemId,
                        item.merchantItemUrl,
                        item.merchantItemTitle,
                        item.brand,
                        item.modelNameView,
                        str(item.pricePlusTax),
                        str(item.priceEft),
                        checkval(scrapeditem.merchantItemTitle) if scrapeditem is not None else "-",
                        checkval(scrapeditem.brand) if scrapeditem is not None else "-",
                        checkval(scrapeditem.modelNameView) if scrapeditem is not None else "-",
                        checkval(scrapeditem.pricePlusTax) if scrapeditem is not None else "-",
                       	checkval(scrapeditem.priceEft) if scrapeditem is not None else "-"
                        ]
                file_append_utf8("scrape-log.csv","\t".join([field.replace("\t"," ") for field in fields])+"\n")		

		

#bootstrap
if __name__=="__main__":
        #run module
        mod=DOMScrapper()
        args=mod._parse_argv()
        mod._run(**args)
