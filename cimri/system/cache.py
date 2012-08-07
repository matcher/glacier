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
import os.path
import shutil
import codecs

from cimri.system.config import Config


class Cache(object):
        """
	Modullerin cache yazma/okuma operasyonlari icin kullanilir
        """

	def __init__(self,section=None):
	        """
	        @type  section: str
	        @param section: cache operasyonlari icin kullanilacak cache sectioni. eger None ise genel cache kullanilir.
	        """

		#cache section
		self.section=section

		#make sure section is specified right
		if self.section is not None:
			self.section=self.section.strip()
			if self.section=="":
				self.section=None

		#cache path
		self.path=os.path.join(Config.getconfig("SYS").get("cache_path"),("__global__" if section is None else section))

		#if cache path doesn't exist, create it		
		try:
			if not os.path.exists(self.path):
    				os.makedirs(self.path)
		except Exception as e:
			passs


	def get(self,key):
	        """
		cache'den istenen bilgileri okur

	        @type  key: str
	        @param key: cache bolumu icinde istenen bilgileri identify eden key

	        @rtype: str
	        @return: istenen cache bilgileri
	        """

                file=os.path.join(self.path,key)
                try:
                        f=codecs.open(file,"r","utf-8")
                        content=f.read()
                        f.close()
			return content

                except Exception as e:
                        return None


	def set(self,key,content):
	        """
		cache'e istenen bilgileri yazar

	        @type  key: str
	        @param key: cache bolumu icinde yazilacak bilgileri identify eden key

	        @type  content: str
	        @param content: yazilacak bilgiler
	        """

                file=os.path.join(self.path,key)
		try:
	                f=codecs.open(file,"w","utf-8")
        	        f.write(content)
                	f.close()

		except Exception as e:
			pass


	def clear(self):
	        """
	        cache bolumunu temizler, icerinde bulunan butun bilgileri siler.
	        """

		try:
			shutil.rmtree(self.path)		
		except Exception as e:
			pass


	@classmethod
	def getstatus(cls):
	        """
		Cache ve icerisinde bulunan bilgiler hakkinda genel bilgiler verir

	        @rtype: dict
	        @return: her cache bolumu hakkinda cache bolumunun ismi ve icerisindeki dosyalarin sayisini iceren bilgiler
	        """

		#get cache sections
		path=Config.getconfig("SYS").get("cache_path")
		sections=filter(lambda f:os.path.isdir(os.path.join(path,f)), os.listdir(path))
		
		#organize
		data=[{"id":section} for section in sections]		

		#get counts
		for section in data:
			sectionpath=os.path.join(path,section["id"])
			files=filter(lambda f: not os.path.isdir(os.path.join(sectionpath,f)), os.listdir(sectionpath))
			
			#add counts
			section["count"]=len(files)

		return data
		
