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
from cimri.api.solrapi import SolrAPI, AsyncSolrAPI
from cimri.algorithms.chunker.dictionary import DictionaryChunker
from cimri.util.text import *

class CatalogueDB(SolrAPI):
	"""
	Match islemleri icin cimri katalog solr'a erisim saglar
	"""

	brandchunker=None

	def __init__(self):
		#get api url
		url=Config.getconfig("API").get("cimri_solr_url")

		#initialize
		super(CatalogueDB,self).__init__(url)


	def find_brands_in_title(self,title):
                """
                Bir merchant item title'i icinde katalog solr databaseinda kayitli bulunan brandleri arayip bulur

                @type  title: str
                @param title: icerisinde brandlerin aranacagi title

		@rtype: list
		@return: bulunan brand isimlerinin listesi
		"""

		def get_brand_chunker():
			if CatalogueDB.brandchunker!=None:
				return CatalogueDB.brandchunker

			self.logger.info("solr call...")		

			#construct query
			query="brand:*"
			
			#make query (get all brands)
			#items=self.call("brand:*",500000)	#old matcher does it this way
			res=self.call_raw('*:*',facet='on',rows=0,facet_field='brand')

			#get brands
			brands=res.facet_counts['facet_fields']['brand'].keys()

			self.logger.info("solr call complete...")		

			#create brand chunker
			CatalogueDB.brandchunker=DictionaryChunker( brands )

			return CatalogueDB.brandchunker

		#filter title
		title=lower_non_turkish_alphanumeric(title)

		#find brands in title
		brands=get_brand_chunker().find_all(title)

		return brands



 	def match_by_brands(self,title,brands=[]):
                """
		Brand isimlerine ve title icindeki olasi brand keywordlerine dayanarak solr matchleri arar

                @type  title: str
                @param title: aranacak keywordleri iceren title

                @type  brands: list
                @param brands: aranacak brandleri iceren liste

		@rtype: list
		@return: Solr query sonuclari ya da hata durumunda None
                """

		self.logger.info("solr call...")		

		#any brands passed?
		if len(brands)==0:
			return None

		#query results
		matches=[]

		#run queries
		for brand in brands:
			#construct query
			query=Template("keywords:(+$brand $title)").substitute(brand=SolrAPI.escape(brand),title=SolrAPI.escape(title))

			#make query
			items=self.call(query)

			#anthing matched?
			if len(items)>0:
				matches.append(items[0])
			
		#anything matched?
		if len(matches)==0:
			return None

		#sort by socre
		matches.sort(lambda a,b: int(100*(b["score"]-a["score"])))

		#if the best match is above the score threshold, we have a match
		if matches[0]["score"] > 3:
			return matches[0]

		return None


 	def match_by_keywords(self,keywords):
                """
		Keyword listesine dayanarak solr matchleri arar

                @type  keywords: list
                @param keywords: aranacak keywordleri iceren liste

		@rtype: list
		@return: Solr query sonuclari ya da hata durumunda None
                """

		self.logger.info("solr call...")		

		#any keywords passed?
		if len(keywords)==0:
			return None

		#construct query
#		query=Template("keywords:(${keywords})").substitute(keywords=" ".join(keywords))
		query=Template("title2:(${keywords})").substitute(keywords=SolrAPI.escape(" ".join(keywords)))

		#make query
		matches=self.call(query)

		#sort by score
		matches.sort(lambda a,b: int(100*(b["score"]-a["score"])))

		#pick the top N
		return matches[:25]


 	def match_by_model(self,keywords):
                """
		Model ismine dayanarak solr matchleri arar

                @type  keywords: list
                @param keywords: aranan model icin keywordleri iceren liste

		@rtype: list
		@return: Solr query sonuclari ya da hata durumunda None
                """

		self.logger.info("solr call...")		

		#any keywords passed?
		if len(keywords)==0:
			return None

		#construct query
		query=Template("model:(${keywords})").substitute(keywords=SolrAPI.escape(" ".join(keywords)))

		#make query
		matches=self.call(query)

		#sort by score
		matches.sort(lambda a,b: int(100*(b["score"]-a["score"])))

		#pick the top N
		return matches[:25]



 	def match_by_ids(self,ids):
                """
		Bir itemid listesine dayanarak solr matchleri arar

                @type  ids: list
                @param ids: aranan item Idleri iceren liste

		@rtype: list
		@return: Solr query sonuclari ya da hata durumunda None
                """

		self.logger.info("solr call...")		

		#any ids passed?
		if len(ids)==0:
			return None

		#construct query
		ids=" OR ".join([SolrAPI.escape(str(id)) for id in ids])
		query=Template("id:(${ids})").substitute(ids=ids)

		#make query
		matches=self.call(query)

		#return results
		return matches



 	def suggestions_by_title_and_brand(self,title,brand,mpn):
                """
		Title, brand, ve mpn bilgilerine dayanarak solr matchleri arar

                @type  title: str
                @param title: title bilgileri

                @type  brand: str
                @param brand: brand bilgileri

                @type  mpn: str
                @param mpn: mpn bilgileri

		@rtype: list
		@return: Solr query sonuclari ya da hata durumunda None
                """

		self.logger.info("solr call...")		

		#process keywrods and brand
		keywords=lower_non_turkish_alphanumeric(title).strip()
		brand=lower_non_turkish_alphanumeric(brand).strip()
		mpn=replace_turkish_chars(mpn).strip()

		#append mpn to keywords
		if mpn!="":
			keywords=keywords+" "+mpn

		#construct query
		query=Template("keywords:(${keywords})").substitute(keywords=SolrAPI.escape(keywords))

		#add brand if not empty
		if brand!="":
			query=Template("$query brand:(${brand})").substitute(query=query,brand=SolrAPI.escape(brand))

		#make query
		suggestions=self.call(query,rows=100)

		#return all suggestions
		return suggestions




class AsyncCatalogueDB(AsyncSolrAPI):
	"""
	Katalog solr databaseinde asynchronous searchler yapmak icin kullanilir
	"""

	brandchunker=None

	def __init__(self):
		#get api url
		url=Config.getconfig("API").get("cimri_solr_url")

		#initialize
		super(AsyncCatalogueDB,self).__init__(url)


 	def match_by_keywords(self,keywords):
                """
		Keyword listesine dayanarak solr matchleri arar

                @type  keywords: list
                @param keywords: aranacak keywordleri iceren liste

                @rtype: L{twisted.internet.defer.Deferred}
                @return: hata ya da sonuclari kabul edicek bir Deferred objecti
                """

		self.logger.info("solr call...")		

		#any keywords passed?
		if len(keywords)==0:
			res=Deferred()	
			res.callback([])
			return res

		#construct query
#		query=Template("keywords:(${keywords})").substitute(keywords=" ".join(keywords))
		query=Template("title2:(${keywords})").substitute(keywords=SolrAPI.escape(" ".join(keywords)))

		#make query
		res=self.call(query)
		
		return res


 	def match_by_model(self,keywords):
                """
		Model ismine dayanarak solr matchleri arar

                @type  keywords: list
                @param keywords: aranan model icin keywordleri iceren liste

                @rtype: L{twisted.internet.defer.Deferred}
                @return: hata ya da sonuclari kabul edicek bir Deferred objecti
                """

		self.logger.info("solr call...")		

		#any keywords passed?
		if len(keywords)==0:
			res=Deferred()	
			res.callback([])
			return res

		#construct query
		query=Template("model:(${keywords})").substitute(keywords=SolrAPI.escape(" ".join(keywords)))

		#make query
		res=self.call(query)

		return res



 	def match_by_mpn(self,keywords):
                """
		Mpn bilgilerine dayanarak solr matchleri arar

                @type  keywords: list
                @param keywords: aranan mpn icin keywordleri iceren liste

                @rtype: L{twisted.internet.defer.Deferred}
                @return: hata ya da sonuclari kabul edicek bir Deferred objecti
                """

		self.logger.info("solr call...")		

		#any keywords passed?
		if len(keywords)==0:
			res=Deferred()	
			res.callback([])
			return res

		#construct query
		query=Template("mpnValue:(${keywords})").substitute(keywords=SolrAPI.escape(" ".join(keywords)))

		#make query
		res=self.call(query)

		return res



 	def match_by_ids(self,ids):
                """
		Bir itemid listesine dayanarak solr matchleri arar

                @type  ids: list
                @param ids: aranan item Idleri iceren liste

		@rtype: list
		@return: Solr query sonuclari ya da hata durumunda None
                """

		self.logger.info("solr call...")		

		#any ids passed?
		if len(ids)==0:
			res=Deferred()	
			res.callback([])
			return res

		#construct query
		ids=" OR ".join([SolrAPI.escape(str(id)) for id in ids])
		query=Template("id:(${ids})").substitute(ids=ids)

		#make query
		matches=self.call(query)

		#return results
		return matches
