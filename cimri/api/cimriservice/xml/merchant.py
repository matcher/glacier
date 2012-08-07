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

from lxml import etree

from cimri.api.cimriservice.data.merchantitem import MerchantItem
from cimri.system.logger import Logger
from cimri.system.config import Config
from cimri.system.web import Web
from cimri.util.text import *

class MerchantXML(Web):
        """
	Merchant XML bilgileri
        """

	def __init__(self,merchant):
                """
		@type merchant:	L{cimri.api.cimriservice.data.merchant.MerchantInfo}
                @param id: merchant 
                """

		#init parent
		super(MerchantXML,self).__init__()

		self.id=id		
		self.logger=Logger.getlogger(self.__class__.__name__)
#		self.url=Config.getconfig("API").get("cimri_merchant_xml_url")+str(merchant.merchantId)
		self.url=merchant.xmlUrl1
		self.xml=None
		self.parser=None
		self.items=[]
		self.encoding=""


	def geturl(self):
                """
		Merchant XML'e erismek icin kullanilacak URL'i verir

                @rtype: str
                @return: merchant XML'i indirmek icin kullanilan URL
                """

		return self.url

	def load(self):
                """
		Merchant XML'i yukler ve parse eder

                @rtype: bool
                @return: XML basarili ile yuklenir ve parse olursa True aksi takdirde False
                """

		self.logger.info("loading xml: "+self.url)

		return self._load() and self._validate() and self._parse()


	def getid(self):
                """
		Merchant IDsini verir

                @rtype: str
                @return: merchant IDsi
                """

		return ""
		

	def getitems(self):
                """
		XML'de bulunan merchant itemlari verir

                @rtype: list (L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @return: merchant item listesi
                """

		return self.items


	def _load(self):
                """
		Merchant XML'i yukler

                @rtype: bool
                @return: XML basarili ile yuklenirse True aksi takdirde False
                """

		#temp - read from file
#		f="/home/gun/matcher-new/cimri-matcher/src/"+str(self.id)+".xml"
#		self.xml=file_read_utf8(f)		
#		return True


		#if already loaded, nothing to do
		if self.xml!=None:
			return True

		#load
		res=self.get(self.url, unicode=False)

		#check response
		if res.error!=None:
			self.logger.error(str(res.error))
			return False

		#set xml	
		self.xml=res.content

		return True
   		

	def _validate(self):
                """
		Merchant XML'i validate eder

                @rtype: bool
                @return: XML valid ise True aksi takdirde False
                """

		#TEMP - SKIP VALIDATION
		return True


		#get schema file 
		xsd=Config.getconfig("API").get("cimri_merchant_xml_schema")

		#open schema file
		try:
			f=open(xsd,'r')

		except Exception as e:
			self.logger.error("exception reading merchant xml schema file: %s",xsd)
			return False

		#validate xml
		try:
			#get schema
			schema=etree.XMLSchema( etree.XML(f.read()) )

			#create parser
			self.parser=etree.XMLParser(schema=scheme)

			#validate
			root=etree.fromstring(self.xml,self.parser)

		except Exception as e:
			self.logger.error("validation failed on merchant xml "+str(e))

		finally:
			f.close()

		return True



	def _parse(self):
                """
		Merchant XML'i parse eder

                @rtype: bool
                @return: XML hatasiz parse oluyor ise True aksi takdirde False
                """

		#get namespace
		ns=Config.getconfig("API").get("cimri_merchant_xml_namespace")

		try:	
			#get encoding (assume utf8) 
			#(also note the use of \uFEFF - in merchant 2824 for example - http://blogs.msdn.com/b/michkap/archive/2005/01/20/357028.aspx)
			header=ignore_non_alphanumeric(self.xml[:1000].lower())
			if header.find("iso88599")>-1:
				self.encoding="iso-8859-9"
			else:
				self.encoding="utf-8"
	
			#strip xml header
			if self.xml.find("<?xml")>-1:
				index=self.xml.find(">")
				self.xml=self.xml[index+1:].strip()
			elif self.xml.find("<")>-1:
				index=self.xml.find("<")
				self.xml=self.xml[index:].strip()
			
			#parser 
			self.parser=etree.XMLParser(recover=True)	#ns_clean=True

			#get root element
			root=etree.fromstring(self.xml,self.parser)

			#parse items
			self.items=[]
			for element in root.iter("{"+ns+"}MerchantItem"):
				self.items.append(MerchantItem(xml=element,encoding=self.encoding))
			for element in root.iter("MerchantItem"):
				self.items.append(MerchantItem(xml=element,encoding=self.encoding))

		except Exception as e:
			self.logger.error("exception parsing merchant xml: %s",e)
			return False


		return True
