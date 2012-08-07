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


import json

from cimri.system.config import Config
from cimri.system.logger import Logger
from cimri.util.text import *


class ProductSpec():
        """
	Scraperin kullandigi urun bilgileri tanimlarina erismeyi saglar.
        """


	def __init__(self):
		#get logger
		self.logger=Logger.getlogger(self.__class__.__name__)
	
		#get configuration
		self.config=Config.getconfig("SPECS")

		#init fields
		self.fields=[]
		self.types={}

		#load
		self._load()


	def get_keywords(self):
	        """
		Urun bilgilerini tanimlayan olasi butun keywordleri verir

	        @rtype: list
	        @return: keywordler listesi
	        """

		return list(set([keyword for keywords in (field["label"]["corpus"] for field in self.fields if field["label"]!=None) for keyword in keywords]))



	def get_fields(self):
	        """
		Urun bilgileri icin tanimli butun field isimlerini verir

	        @rtype: list
	        @return: tanimli urun field isimleri
	        """

		return [field["field"] for field in self.fields]



	def get_types(self):
	        """
		Urun bilgilerini tesbit edebilmek icin kullanilabilecek veri turleri ile ilgili keywordleri verir

	        @rtype: dict
	        @return: veri turlerini iceren bir dictionary
	        """

		return self.types


	def get_field(self,name):
	        """
		Belli bir urun field tanimini verir

	        @type  name: str
	        @param name: fieldin ismi

	        @rtype: dict
	        @return: urun field tanimi
	        """

		for field in self.fields:
			if field["field"]==name:
				return field

		return None		


	def get_field_by_keyword(self,word):
	        """
		Bir keyworde bagli olarak o keyworde denk gelen field ismini verir

	        @type word: str
	        @param word: urun fieldina denk gelen bir keyword

	        @rtype: str
	        @return: eger belirtilen keyworde denk gelen bir field varsa o fieldin ismi, yoksa None
	        """

		for field in self.fields:
			if field["label"]!=None and word in field["label"]["corpus"]:
				return field["field"]

		return None


	def get_fields_by_type(self,typ):
	        """
		Belirli bir field turune denk gelen fieldlarin isimlerini verir

	        @type  typ: str
	        @param typ: field turunun ismi

	        @rtype: list
	        @return: field isimlerinin listesi
	        """

		return [field["field"] for field in self.fields if field["values"]!=None and typ in field["values"]["type"] ]


	def _load(self):
	        """
		Urun bilgi tanimlarini yukler 
	        """

		#load
		file=self.config.get("product_spec")
		try:
			info=json.loads( file_read_utf8(file) )
			self.fields=info["fields"]
			self.types=info["types"]

		except Exception as e:
			self.logger.error("error reading product specs from file %s",file)

