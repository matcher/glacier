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

from cimri.system.data import DataObject


class MerchantInfo(DataObject):
        """
	Merchant bilgileri
        """

	STATUS_ACTIVE="A"
	STATUS_TEMP_SUSPENDED="T"		#matcher should ignore
	STATUS_S="S"				#suspended - matcher should ignore
	STATUS_N="N"				#new - matcher should ignore

	
	def __init__(self,data=None):
                """
                @type  data: dict
                @param data: MerchantInfo fieldlarini initialize etmek icin kullanilabilecek degerler
                """

		self.merchantId=0
		self.merchantName=""
		self.xmlUrl1=""
		self.status=""
		self.username=""
		self.password=""
		self.merchantUrl=""
		self.merchantLogo=""
		self.directMatcher=False	#not used
		self.rank=0
		self.domainName=""
		self.logo=None
		self.contactEmail=""
		self.merchantPhone=""
		self.shippingInfo=""
		self.customerCareInfo=""
		self.refundConditions=""
		self.paymentOptions=""
	
		super(MerchantInfo,self).__init__(data=data)
		
