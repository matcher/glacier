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


import urllib2
import os.path

from cimri.system.logger import Logger
from cimri.api.api import API


class HttpAPI(API):
        """
	http API classleri icin base class
        """


	def __init__(self,url):
		"""
		@type	url: string
		@param 	url: API callari icin kullanilacak url 
		"""

		#get logger
		self.logger=Logger.getlogger(self.__class__.__name__)

		#initialize
		super(HttpAPI,self).__init__()
		self.url=url


	def call(self,path,args=[],data=None):
		"""
		HTTP API call gerceklestir

		eger data parametresi None ise HTTP GET request yapar, aksi takdirde POST request

		@type 	path: string
		@param 	path: API call icin API url'e eklenecek relative path

		@type 	args: dict
		@param	args: API call icin url parametreleri

		@type	data: dict
		@param  data: HTTP POST ile yollanacak parametreler

		@rtype: string
		@return: HTTP call response ya da hata varsa None
		"""
	 	
		#construct url
		list = []
		for key in args:
			list.append(key + "=" + str(args[key]))
		urlargs = ''
		if len(list) > 0:
			urlargs = '?' + '&'.join(list)
		url=self.url+path+urlargs

		self.logger.info("opening url: %s",url)		

		#open url
		f = None
		try:
			f=urllib2.urlopen(url, data)
		except:
			self.logger.error("exception ocurred opening api url")
			return None

		#get response
		try:
			response = f.read()		
		except:
			self.logger.error("exception ocurred reading api response")
			return None
		finally:
			f.close()

		return response



	def put(self,path,content):
                """
		HTTP PUT call gerceklestirir

		@type 	path: string
		@param 	path: API call icin API url'e eklenecek relative path

                @type  content: string
                @param content: PUT request icinde yollanmasi istenen content

                @rtype: boolean
                """

		url=self.url+path

		try:
			opener = urllib2.build_opener(urllib2.HTTPHandler)
			request = urllib2.Request(url, data=content)
			request.add_header('Content-Type', 'application/json')
			request.get_method = lambda: 'PUT'

		except Exception as e:
			self.logger.error("exception ocurred creating API PUT call")
			return False

		try:
			f=opener.open(request)

		except Exception as e:
			self.logger.error("exception ocurred making API PUT call")
			return False

		#get response
		try:
			response = f.read()	
		except Exception as e:
			self.logger.error("exception ocurred reading api response")
			return False
		finally:
			f.close()

		return True
			


	def delete(self,path,content):
                """
		HTTP DELETE call gerceklestirir

		@type 	path: string
		@param 	path: API call icin API url'e eklenecek relative path

                @type  content: string
                @param content: DELETE request icinde yollanmasi istenen content

                @rtype: boolean
                """

		url=self.url+path

		try:
			opener = urllib2.build_opener(urllib2.HTTPHandler)
			request = urllib2.Request(url, data=content)
			request.add_header('Content-Type', 'application/x-www-form-urlencoded')
			request.get_method = lambda: 'DELETE'

		except Exception as e:
			self.logger.error("exception ocurred creating API DELETE call")
			return False

		try:
			f=opener.open(request)

		except Exception as e:
			self.logger.error("exception ocurred making API DELETE call")
			return False

		#get response
		try:
			response = f.read()	
		except Exception as e:
			self.logger.error("exception ocurred reading api response")
			return False
		finally:
			f.close()

		return True
			


if __name__=="__main__":
	#test
	api=HttpAPI("http://www.gstecc.com/")
	res=api.call("about")
