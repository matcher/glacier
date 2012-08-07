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
from lxml import etree

from cimri.system.data import DataObject
from cimri.system.config import Config
from cimri.api.cimriservice.status import CimriStatus


class MerchantItem(DataObject):
        """
	Merchant item bilgileri
        """

	#xml fields to api fields
	fieldmap={"merchantItemId": 		"merchantItemId",
		  "itemUrl":			"merchantItemUrl",
		  "merchantItemCategoryId":	"merchantItemCategoryId",
		  "merchantItemCategoryName":	"merchantItemCategoryName",
		  "brand":			"brand",
		  "model":			"modelNameView",
		  "itemTitle":			"merchantItemTitle",
	  	  "merchantItemField":		"merchantItemField",
		  "pricePlusTax":		"pricePlusTax",
		  "priceEft":			"priceEft",
		  "price3T":			"price3T",
		  "price6T":			"price6T",
		  "price12T":			"price12T",
		  "price24T":			"price24T",
	  	  "mpnValue":			"mpnValue",
		  "mpnType":			"mpnType" }



	def __init__(self,data=None,xml=None,encoding=""):
                """
                @type  data: dict
                @param data: MerchantItem fieldlarini initialize etmek icin kullanilabilecek degerler

                @type  xml: str
                @param xml: MerchantItem fieldlarini initialize etmek icin kullanilabilecek xml element
	
                @type  encoding: str
                @param encoding: text encoding
                """

		self.sid=None
		self.merchantItemId=""
		self.merchantItemTitle=""
		self.merchantItemUrl=""
		self.merchantItemCategoryId=""
		self.merchantItemCategoryName=""
		self.merchantItemField=""
		self.status=None
		self.item=None				#value: {"itemId":<id>}
		self.mpnType=""
		self.mpnValue=""
		self.modelNameView=""
		self.brand=""
		self.possibleSolrItem=None		#value: {"itemId":<id>}
		self.ignoredItemId=None
		self.possibleGoogleItem=None
		self.merchant=None			#value:	{"merchantId":<id>}
		self.price3T=None
		self.price6T=None
		self.price12T=None
		self.price24T=None
		self.priceEft=None
		self.pricePlusTax=None
		self.pricePlusTaxStr=""
		self.score=None
		self.operator=None
		self.matcherType=None
		self.lastUpdateDate=None
		self.matchDate=None
		self.sponsored=None
		self.sponsoreText=""
		self.possibleShowcased=False
			
		self.freeShipping=None
		self.inStock=None

                #set encoding
                self.encoding=encoding

		#load from provided data
		super(MerchantItem,self).__init__(data=data)

		#load from xml
		if xml is not None:
			self.from_xml(xml)



	def is_matched(self,ignoreinactive=True):
                """
		MerchantItem'in bir cimri katalog item'a matched olup olmadigini belirler

                @type  ignoreactive: bool
                @param ignoreactive: eger bu parametre dogru ise, MerchantItem'in bir itemIdsi olsa dahi eger status'u
				     PAUSED_BY_CIMRI ya da PAUSED_NO_IN_XML_ACTIVE ise matched olarak degerlendirilmez.

                @rtype: bool
                @return: MerchantItem'in matched olup olmadigi
                """

		try:
			if self.item["itemId"] in [None,""]:
				return False				
			else:
				#cimri backend includes items with itemIds with the following statuses. these are not actual matches
				#and the data is stored erronously
				if ignoreinactive is True and self.status==CimriStatus.get_status("PAUSED_NO_IN_XML_ACTIVE").get_code():
					return False
				if ignoreinactive is True and self.status==CimriStatus.get_status("PAUSED_BY_CIMRI").get_code():
					return False

				return True
					
		except Exception as e:
			pass

		return False



	def is_guessed(self):
                """
		MerchantItem'in bir cimri katalog item ile possible matchinin olup olmadini belirler

                @rtype: bool
                @return: MerchantItem'in possible matchinin olup olmadigi
                """

		try:
			if self.possibleSolrItem["itemId"] in [None,""]:
				return False				
			else:
				if self.status==CimriStatus.get_status("SOLR_MATCHED").get_code():
					return True
				elif self.status==CimriStatus.get_status("PAUSED_NO_IN_XML_SOLR").get_code():
					return True

				return False
					
		except Exception as e:
			pass

		return False




	def from_xml(self,xml):
                """
		MerchantItem fieldlarini bir xml elementina dayanarak initialize eder.

                @type  xml: str
                @param xml: MerchantItem fieldlarini initialize etmek icin kullanilabilecek xml element
                """

		#get namespace
		ns=Config.getconfig("API").get("cimri_merchant_xml_namespace")
		nslen=len(ns)
					  
		#parse from xml
		for element in xml.iter():
			keys=[element.tag, element.tag[nslen+2:]]
			for key in keys:
				if key in MerchantItem.fieldmap:
					try:
						setattr(self, MerchantItem.fieldmap[key], element.text.strip())
					except Exception as e:
						pass



	def update(self,item):
                """
		MerchantItem'in field'larini baska bir MerchantItem'a dayanarak gunceller

                @type  item: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param item: bu MerchantItem'i guncellemek icin kullanilacak MerchantItem
                """

		for field in MerchantItem.fieldmap.itervalues():
			setattr(self,field,getattr(item,field))

