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


class CatalogueItem(DataObject):
        """
	Cimri katalog item bilgileri
        """

	def __init__(self,data=None):
                """
                @type  data: dict
                @param data: CatalogueItem fieldlarini initialize etmek icin kullanilabilecek degerler
                """

		self.itemTitle=""
		self.title4SEO=""
		self.brand=None
		self.category=None
		self.modelView=""
		self.minPrice=0
		self.maxPrice=0
		self.priceRange=""
		self.stores=0
		self.inStores=0
		self.listImage=""
		self.listImageUrl=""
		self.specsSummary=""
		self.merchantItems=[]
		self.showcasedMerchantItem=None
		self.createDate=None
		self.updateDate=None
		self.imageUrl200x200=""
		self.imageUrl300x300=""
		self.rank=0
		self.description=""
		self.itemSpecs=[]
		self.similarItemsQuery=""
	
		super(CatalogueItem,self).__init__(data=data)

