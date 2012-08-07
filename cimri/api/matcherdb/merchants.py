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


from string import Template
from twisted.internet.defer import Deferred

from cimri.system.config import Config
from cimri.api.solrapi import SolrAPI,AsyncSolrAPI

class MerchantDB(SolrAPI):
	"""
	Match islemleri icin cimri merchant item solr databaseina erisim saglar
	"""
	

	def __init__(self):
		#get api url
		url=Config.getconfig("API").get("cimri_solr_mi_url")

		#initialize
		super(MerchantDB,self).__init__(url)

 
	def match_by_mpn(self,item):
                """
                Bir merchant item'in MPN bilgilerine dayanarak en uygun solr matchi arar

                @type  item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param item: arama bilgilerini iceren MerchantItem

		@rtype: dict
		@return: Solr query sonucu ya da hata durumunda None
                """

		self.logger.info("solr call...")

		#construct query
		query=Template("+mpnType:\"$type\" and +mpnValue:\"$val\"").substitute(type=SolrAPI.escape(item.mpnType),val=SolrAPI.escape(item.mpnValue))
	
		#make query
		items=self.call(query)

		#anything found?
		if len(items)==0:
			return None

		elif len(items)==1:
			return items[0]

		else:
			#if all the matched items point to the same catalog item, item is matched
			if len(set([item['itemId'] for item in items]))==1:
				return items[0]
						
		return None



	def match_by_title(self,item):
                """
                Bir merchant item'in title bilgilerine dayanarak solr matchleri arar

                @type  item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param item: arama bilgilerini iceren MerchantItem

		@rtype: list
		@return: Solr query sonuclari ya da hata durumunda None
		"""

		self.logger.info("solr call...")

		#construct query
		query=Template("merchantItemTitle:\"$title\"").substitute(title=SolrAPI.escape(item.merchantItemTitle))

		#make query
		items=self.call(query)
		
		#anything found?
		if len(items)==0:
			return None

		elif len(items)==1:
			return items[0]

		else:
			#if all the matched items point to the same catalog item, item is matched
			if len(set([item['itemId'] for item in items]))==1:
				return items[0]
						
		return None



	def match_by_title_keywords(self,title):
                """
		Title icide yer alabilecek keywordlere gore solr matchleri arar                

                @type  title: str
                @param title: aranacak keywordleri iceren title

		@rtype: list
		@return: Solr query sonuclari ya da hata durumunda None
                """

		self.logger.info("solr call...")

		#get keywords
		tokens=title.split(" ")
		keywords=[SolrAPI.escape(token.strip()) for token in tokens if token.strip()!=""]

		#construct query
		#query=Template("merchantItemTitle:(${keywords})").substitute(keywords=" ".join(keywords))
		query=Template("merchantItemTitle2:(${keywords})").substitute(keywords=" ".join(keywords))

		#make query
		items=self.call(query)

		#return the top N matches
		return items[:20]




class AsyncMerchantDB(AsyncSolrAPI):
	"""
	Merchant solr databaseinde asynchronous searchler yapmak icin kullanilir
	"""
	
	def __init__(self):
		#get api url
		url=Config.getconfig("API").get("cimri_solr_mi_url")

		#initialize
		super(AsyncMerchantDB,self).__init__(url)



	def match_by_title_keywords(self,title):
                """
		Title icide yer alabilecek keywordlere gore solr matchleri arar                

                @type  title: str
                @param title: aranacak keywordleri iceren title

                @rtype: L{twisted.internet.defer.Deferred}
                @return: hata ya da sonuclari kabul edicek bir Deferred objecti
                """

		self.logger.info("solr call...")

		#get keywords
		tokens=title.split(" ")
		keywords=[SolrAPI.escape(token.strip()) for token in tokens if token.strip()!=""]

		#any keywords?
		if len(keywords)==0:
			res=Deferred()	
			res.callback([])
			return res

		#construct query
		#query=Template("merchantItemTitle:(${keywords})").substitute(keywords=" ".join(keywords))
		query=Template("merchantItemTitle2:(${keywords})").substitute(keywords=" ".join(keywords))

		#make query
		res=self.call(query)

		return res




class AsyncMerchantBlackListDB(AsyncSolrAPI):
	"""
	Blacklist merchant solr databaseinde asynchronous searchler yapmak icin kullanilir
	"""
	
	def __init__(self):
		#get api url
		url=Config.getconfig("API").get("cimri_solr_mi_bl_url")

		#initialize
		super(AsyncMerchantBlackListDB,self).__init__(url)


	def match_by_title_keywords(self,title):
                """
		Title icide yer alabilecek keywordlere gore solr matchleri arar                

                @type  title: str
                @param title: aranacak keywordleri iceren title

                @rtype: L{twisted.internet.defer.Deferred}
                @return: hata ya da sonuclari kabul edicek bir Deferred objecti
                """

		self.logger.info("solr call...")

		#get keywords
		tokens=title.split(" ")
		keywords=[SolrAPI.escape(token.strip()) for token in tokens if token.strip()!=""]

		#any keywords?
		if len(keywords)==0:
			res=Deferred()	
			res.callback([])
			return res

		#construct query
		query=Template("merchantItemTitle2:(${keywords})").substitute(keywords=" ".join(keywords))

		#make query
		res=self.call(query)

		return res
