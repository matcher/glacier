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


import solr
import json
import urllib
import time

import twisted
from twisted.internet.protocol import Protocol
from twisted.internet.defer import Deferred
from twisted.internet import reactor
from twisted.web.client import Agent
from twisted.web.http_headers import Headers

from cimri.api.api import API
from cimri.system.logger import Logger



class SolrAPI(API):
        """
	Solr API classleri icin base class
        """

	def __init__(self,url):
		"""
		@type	url: string
		@param 	url: Solr calllari icin kullanilacak URL
		"""

		#get logger
		self.logger=Logger.getlogger(self.__class__.__name__)

		#initialize
		super(SolrAPI,self).__init__()
		self.url=url


	def call(self,query,rows=100,**args):
		"""
		Solr API call yapar

		@type 	query: string
		@param 	query: calistirilmasi istenen query 

		@type 	rows: int
		@param 	rows: istenen maksimum sonuc sayisi

		@type 	args: kargs
		@param 	args: Solr call'da yollanacak ekstra parametreler. facet.field seklinde olan parametreler facet_field seklinde yollanmalidir

		@rtype: list 
		@return: Solr query sonuclari ya da hata durumunda None
		"""

		#make call
		res = self.call_raw(query,rows,**args)
		if res==None:
			return None

		return res.results



	def call_raw(self,query,rows=100,**args):
		"""
		Solr API call yapar

		@type 	query: string
		@param 	query: calistirilmasi istenen query 

		@type 	rows: int
		@param 	rows: istenen maksimum sonuc sayisi

		@type 	args: dict
		@param 	args: Solr call'da yollanacak ekstra parametreler. facet.field seklinde olan parametreler facet_field seklinde yollanmalidir

		@rtype: L{solr.Response}
		@return: Solr query sonuclari ya da hata durumunda None
		"""

		self.logger.info("solr query sent: %s %s %s",self.url,query,repr(args))

		#get connection
		try:
			conn=solr.Solr(self.url)

		except Exception as e:
			self.logger.error("exception ocurred while connecting to solr %s: ",self.url)
			return None

		#send query
		try:
			select=solr.SearchHandler(conn,"/select")
			res=select(q=query, rows=rows, **args)
			#res=conn.query(query, rows=rows)

		except Exception as e:
			self.logger.error("exception ocurred while making solr query: %s",query)
			return None

		finally:
			conn.close()

		return res


	@classmethod
	def escape(cls,query):
		for c in ['\\','+','-','&&','||','!','(',')','{','}','[',']','^','"','~','*','?',':']:
			query=query.replace(c,'\\'+c)
		return query		


class AsyncSolrReader(Protocol):
        """
	Asyncrhonous Solr API call response'ini almak icin kullanilir
        """

	def __init__(self, finished):
                """
                @type  finished: L{twisted.internet.defer.Deferred}
                @param finished: call tamamlandigi zaman callback yapilmak uzere bir Deferred object
                """

		self.finished=finished
		self.buf=""


	def dataReceived(self, bytes):
                """
                @type  text: list
                @param text: call sirasinda cevap olarak gelen data
                """

		self.buf=self.buf+bytes


	def connectionLost(self, reason):
                """
		call sirasinda baglanti kabolursa bu method call olur

                @type  reason: L{twisted.python.failure.Failure}
                @param reason: baglanti kaybolma sebebi
                """

		if reason.type==twisted.web.client.ResponseDone:
			self.finished.callback(self.buf) 
		else:
			self.finished.errback(reason)


class AsyncSolrAPI(API):
        """
	Asyncrhonous Solr API call'lari icin kullanilir
        """


	def __init__(self,url):
		"""
		@type	url: string
		@param 	url: Solr calllari icin kullanilacak URL
		"""

		#get logger
		self.logger=Logger.getlogger(self.__class__.__name__)

		#initialize
		super(AsyncSolrAPI,self).__init__()
		self.url=url


	def call(self, query, rows=100, **args):
                """
		Solr API call yapar. Call asynchronous bir sekilde yapilir.

		@type 	query: string
		@param 	query: calistirilmasi istenen query 

		@type 	rows: int
		@param 	rows: istenen maksimum sonuc sayisi

		@type 	args: dict
		@param 	args: Solr call'da yollanacak ekstra parametreler. facet.field seklinde olan parametreler facet_field seklinde yollanmalidir

                @rtype: L{twisted.internet.defer.Deferred}
                @return: hata ya da sonuclari kabul edicek bir Deferred objecti
                """

		#return result in a deferred
		result=Deferred()

		dur=time.time()

		#get query url
		url=self.url+"/select"
		url=url+"?"+urllib.urlencode({"q":query,"rows":rows,"fl":"*,score","wt":"json"})	

		def handleResponse(packet):
			try:
				data=json.loads(packet)
				res=data["response"]["docs"]

				#print str(time.time()-dur)+" "+self.__class__.__name__

				result.callback(res)
				
			except Exception as e:
				result.errback(reason)

		def handleResponseError(reason):
			result.errback(reason)

		def handleData(resp):
			finished=Deferred()
			finished.addCallback(handleResponse)
			finished.addErrback(handleResponseError)
			resp.deliverBody(AsyncSolrReader(finished))
 			return finished

		def handleConnError(err):
			self.logger.error("exception ocurred while making solr query: %s %s",query,str(err))
			result.errback(err)

		#make call
		agent=Agent(reactor)        
		call=agent.request('GET',url,Headers({'User-Agent': ['Cimri Matcher']}),None)                        
		call.addCallback(handleData)                                
		call.addErrback(handleConnError)

		return result
