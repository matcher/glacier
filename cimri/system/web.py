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
import urllib2
from pattern.web import *
import os
import codecs

from cimri.system.logger import Logger
from cimri.system.config import Config
from cimri.system.cache import Cache
from cimri.util.token import *



class WebError():
        """
	HTTP operasyonlari icin hata tanimlari ve sonuclarini icerir
        """

	def __init__(self, msg, code, url):
	        """
	        @type  msg: str
	        @param msg: hata mesaji

	        @type  code: int
	        @param code: hata kodu

	        @type  url: str
	        @param url: ilgili URL
	        """

		self.msg=msg
		self.code=code
		self.url=url



	def __str__(self):
	        """
		hata mesajini stringe cevirir
	
		@rtype: str
		@return: mata mesajinin stringi
	        """

		if self.code==None:
			return Template("$msg: $url").substitute(msg=self.msg, url=self.url)
		else:
			return Template("$msg (http code: $code): $url").substitute(msg=self.msg, code=str(self.code), url=self.url)	



class FileError():
        """
	File operasyonlari icin hata tanimlari ve sonuclarini icerir
        """

	def __init__(self, msg, file):
	        """
	        @type  msg: str
	        @param msg: hata mesaji

	        @type  file: str
	        @param file: ilgili file'in ismi ve pathi
	        """

		self.msg=msg
		self.file=file


	def __str__(self):
	        """
		hata mesajini stringe cevirir
	
		@rtype: str
		@return: mata mesajinin stringi
	        """

		return Template("$msg: $file").substitute(msg=self.msg, file=self.file)


class WebReport():
        """
	Bir HTTP operasyonun sonuclarini icerir. Asagidaki fieldlari icerir:

	error - herhangi bir hata varsa onu icerir

	content - HTTP operasyonu ile okunan content

	request_url - acilmasi istenen URL

	content_url - eger contente bir redirect ile ulasildi ise redirect olunan URL

	query - kullanilan query parametreleri

	file - eger bir dosya indirildi ise path ve ismi
	
        """

	def __init__(self,url):
	        """
	        @type  url: str
	        @param url: ilgili URL
	        """

		self.headers=None		#response headers
		self.error=None			#will be set if there's an error
		self.content=None		#will have the content
		self.request_url=url		#the requested url
		self.content_url=url		#the actual url if the requested url had a redirect
		self.query=None			#query parameters of content url
		self.file=None			#full name (including) of file saved (for downloads)



class Web(object):
	"""
	HTTP operasyonlari icin kullanilir 
        """

	def __init__(self):
		#get logger
		self.logger=Logger(self.__class__.__name__)
		
		#get configuration
		self.config=Config.getconfig("WEB")


	def ping(self,url):
		"""
		Bir URL'in erisilir olup olmadigini kontrol eder

		@type url:	str
		@param url:	test edilmesi istenen URL

		@rtype:	L{cimri.system.web.WebReport}
		@return: ping sonuclarini iceren WebReport objecti
		"""

		return self.get(url,ping=True)
		


	def get(self,url,unicode=True,download=False,file=None,ping=False,cache=None,timeout=None):
		"""
		Bir URL'deki contenti yuklemek ya da dosya olarak indirmek icin kullanilir

		@type url:	str
		@param url:	acilmasi istenen URL

		@type unicode:	bool
		@param unicode: URLdeki contentin unicode olarak varsayilip sayilmamasi gerektigini kontrol eder

		@type download:	bool
		@param download:True ise URLdeki content bir dosya olarak indirilir, aksi takdirde content string olarak doner

		@type file:	str
		@param file:	URLdeki content dosya olarak indirildiyse dosyanin path ve ismi

		@type ping:	bool
		@param ping:	sadece URLin erisilir olup olmadigini kontrol eder. herhangi bir content yuklenmez ya da indirilmez.

		@type cache:	dict
		@param cache:	URL islemleri ile ilgili cache operasyonlarini kontrol eder. eger None ise herhangi bir cache operasyonu
				yapilmaz.

				eger "read" keyi varsa cache dictionarysinde, istenen content URL yerine bulunursda belirtilen cache
				bolumunden okunur. eger "write" keyi varsa, URLden alinan content belirtilen cache bolumune yazilir.

		@rtype:	L{cimri.system.web.WebReport}
		@return: sonuclari iceren WebReport objecti
		"""

		#initialize report
		report=WebReport(url)
	
		#download file
		f=None

		try:
			#get timeout
			timeout=int(self.config.get("url_open_timeout")) if timeout is None else timeout

			#create url resoure
			res=URL(url)

			#ping only?
			if ping:
				#open and check if url is accessible
	                	res.open(timeout=timeout)
	
			#download?
			elif download:
				#record file name
				report.file=file				

				#open file to save to
				f=open(file,'w')

				#download and write
				f.write(res.download(timeout=timeout, cached=False))

			elif unicode:
				#use cached version?
				if cache is not None and "read" in cache:
					report.content=Cache(cache["read"]).get("web.url."+hash_url(url))

				#download url (if not looking for a cached version or if the cached version not found)
				if report.content is None:
					report.content=res.download(timeout=timeout, cached=False)
				
					#write to cache?
					if cache is not None and "write" in cache:
						Cache(cache["write"]).set("web.url."+hash_url(url),report.content)

			else:
				#use cached version?
				if cache is not None and "read" in cache:
					report.content=Cache(cache["read"]).get("web.url."+hash_url(url))

				#download url (if not looking for a cached version or if the cached version not found)
				if report.content is None:
		                	res.open(timeout=timeout)
					report.content=res.download(cached=False,timeout=timeout)
					#report.content=res.read()
				
					#write to cache?
					if cache is not None and "write" in cache:
						Cache(cache["write"]).set("web.url."+hash_url(url),report.content)
				
                except HTTP400BadRequest as e:
			report.error=WebError("exception ocurred opening url. bad request",400,url)
                        self.logger.error(str(report.error))
                        self.logger.error(str(e))

                except HTTP401Authentication as e:
			report.error=WebError("exception ocurred opening url. url requires authentication",401,url)
                        self.logger.error(str(report.error))
                        self.logger.error(str(e))

                except HTTP403Forbidden as e:
			report.error=WebError("exception ocurred opening url. url not accessible",403,url)
                        self.logger.error(str(report.error))
                        self.logger.error(str(e))

                except HTTP404NotFound as e:
			report.error=WebError("exception ocurred opening url. not found",404,url)
                        self.logger.error(str(report.error))
                        self.logger.error(str(e))

                except HTTPError as e:
			report.error=WebError("exception ocurred opening url",None,url)
                        self.logger.error(str(report.error))
                        self.logger.error(str(e))

                except URLError as e:
			report.error=WebError("exception ocurred opening url. url contains errors",None,url)
                        self.logger.error(str(report.error))
                        self.logger.error(str(e))

                except URLTimeout as e:
			report.error=WebError("exception ocurred opening url. url load timed out",None,url)
                        self.logger.error(str(report.error))
                        self.logger.error(str(e))

		except IOError as e:
			report.error=FileError("exception ocurred writing to file",file)
                        self.logger.error(str(report.error))
                        self.logger.error(str(e))

		except Exception as e:
			report.error=WebError("exception ocurred",None,url)
                        self.logger.error(str(report.error))
                        self.logger.error(str(e))
		
		finally:
			if f!=None:
				f.close()

		#add information
		report.headers=res.headers
		report.query=res.query if (res!=None and res.query!=None) else None
		report.content_url=res.redirect if (res!=None and res.redirect!=None) else report.content_url

		return report



