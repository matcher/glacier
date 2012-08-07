""" 
cimri matcher system
--------------------   
date:                    02.17.2012
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
from cimri.api.cimriservice.data.merchantitem import MerchantItem
from cimri.module.scrapper.scrapper import Scrapper
from cimri.util.text import *

class XMLScrapper(Scrapper,Web):
        """
	XMLScrapper bir merchant xml'den alinan merchant itemlarini sistem islem akisi kurallari icinde bir 
	scraper modulu tarafindan yaratilmis olarak formatlar. Gercek anlamda bir scraper degildir.

	Modul asagidaki islemleri destekler:

        "scrap"	islemi :

                task.data      	: islem verileri icindeki her item icin "data" o item'in URL olmalidir. ayrica her item icin
				  asagidaki veriler bulunmalidir:

                                  "meta.merchantid"             : item'in merchant IDsi

                                  "meta.xmlitem" 	        : item bilgilerini iceren MerchanItem objecti
								  L{cimri.api.cimriservice.data.merchantitem.MerchantItem}

                task.result     : her item icin "data" o itemin bilgilerini iceren bir MerchanItem olacaktir.

	"""


	def __init__(self):
		#initialize parents
		Web.__init__(self)
		Scrapper.__init__(self)
		
		self.logger=Logger(self.__class__.__name__)

		#supported operations
		self.ops={"scrap"		:self._task_scrap}


	def _task_scrap(self):
		"""
		"scrap" isini calistirir
		"""

		self.logger.info("api call...")

		#translate data	
		self.task.result=[ {"data":item["meta.xmlitem"]} for item in self.task.data ]

		#mark as completed
		self._complete()


#bootstrap
if __name__=="__main__":
        #run module
        mod=XMLScrapper()
        args=mod._parse_argv()
        mod._run(**args)
