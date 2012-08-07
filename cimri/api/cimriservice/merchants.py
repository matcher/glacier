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
from types import ListType
import json
import urllib2
import pprint

from cimri.api.httpapi import HttpAPI
from cimri.system.config import Config
from cimri.api.cimriservice.data.merchant import MerchantInfo
from cimri.api.cimriservice.data.merchantitem import MerchantItem



class MerchantsAPI(HttpAPI):
        """
	Cimri Service Merchants API'ina erisim saglar
        """


	def __init__(self):
                """
                """

		#get api end point
		url=Config.getconfig("API").get("cimri_service_url")

		#initialize
		super(MerchantsAPI,self).__init__(url)
  



	#- merchant related calls ---------------------------------------------------------------------------

	def get_merchants(self,**args):
		"""
		Merchant listesini al

		@type	args: dict
		@param	args: API call icin url parametreleri. desteklenen bazi parametreler: 
			      status, start (default==0), max (default==-1), fields (default==""), startLetter

		@rtype: L{cimri.api.cimriservice.data.merchant.MerchantInfo}
		@return: MerchantInfo listesi ya da hata durumunda None
		"""

		self.logger.info("api call...")

		#sample:  http://glacier.cimri.com:8080/cimri-service/merchants
		packet=self.call("merchants",args=args)
		if packet is None:
			return None
		
		#parse and return merchants
		return MerchantInfo.list_from_json(packet,["merchant"])


	def get_merchant(self,id,**args):
		"""
		Belli bir merchantin bilgilerini al

		@type 	id: string
		@param 	id: merchantId

		@type	args: dict
		@param	args: API call icin url parametreleri. desteklenen bazi parametreler: 
				fields (default=="")

		@rtype: L{cimri.api.cimriservice.data.merchant.MerchantInfo}
		@return: MerchantInfo ya da hata durumunda None
		"""

		self.logger.info("api call...")
		
		#sample:  http://glacier.cimri.com:8080/cimri-service/merchants/2158
		packet=self.call(Template("merchants/$id").substitute(id=str(id)),args=args)
		if packet is None:
			return None

		#parse and return response
		return MerchantInfo.from_json(packet)

	#----------------------------------------------------------------------------- merchant related calls




	#- merchant item related calls ----------------------------------------------------------------------

	def get_items(self,**args):
		"""
		Merchant itemlarini alir

		@type	args: dict
		@param	args: API call icin url parametreleri. desteklenen bazi parametreler: 
				status, sid, start (default=0), max (default=-1), fields (default=""), expandLevel (default=1),
				catIds, catId, merchantId, sortField, sortOrder, filter, itemId, cimriUrl, mCatNames

		@rtype: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
		@return: MerchantItem listesi ya da hata durumunda None
		"""

		self.logger.info("api call...")

		#sample http://glacier.cimri.com:8080/cimri-service/merchants/items?status=1&max=10
		packet=self.call("merchants/items",args=args)
		if packet is None:
			return None

		return MerchantItem.list_from_json(packet,["merchantItem"])



	def get_merchant_items(self,id,**args):
		"""
		Belli bir merchantin itemlarini alir

		@type 	id: str
		@param 	id: merchantId

		@type	args: dict
		@param	args: API call icin url parametreleri. desteklenen bazi parametreler: 
			      status, itemId, start (default==0), max (default==-1), fields (default==""), expandLebel (defaul==1)

		@rtype: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
		@return: MerchantItem listesi ya da hata durumunda None
		"""

		self.logger.info("api call...")

		#sample http://glacier.cimri.com:8080/cimri-service/merchants/2158/items
		packet=self.call(Template("merchants/$id/items").substitute(id=id),args=args)
		if packet is None:
			return None

		#parse and return items
		return MerchantItem.list_from_json(packet,["merchantItem"])


	def search_items(self,**args):
		"""
		Merchant itemlar icin arama yapar

		@type	args: dict
		@param	args: API call icin url parametreleri. desteklenen bazi parametreler: 
			      queryString, start (default==0), max (default==-1), status, fields (default==""), expandLevel (default==1)

		@rtype: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
		@return: MerchantItem listesi ya da hata durumunda None
		"""

		self.logger.info("api call...")

		#make call
		packet=self.call(Template("merchants/$id/items/search/title").substitute(id=id),args=args)
		if packet is None:
			return None
		
		#parse and return items
		return MerchantItem.list_from_json(packet,["merchantItem"])


	def get_item_by_title(self,**args):
		"""
		Merchant item title'ina gore merchant itemlari alir

		@type	args: dict
		@param	args: API call icin url parametreleri. desteklenen bazi parametreler: 
				status, merchantItemTitle, merchantId,
				start (default=0), max (default=-1), fields (default=""), expandLevel (default=1), merchantItemId

		@rtype: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
		@return: MerchantItem listesi ya da hata durumunda None
		"""

		self.logger.info("api call...")

		#make call
		packet=self.call("merchants/itembyTitle",args=args)
		if packet is None:
			return None

		#parse and return items
		return MerchantItem.list_from_json(packet,["merchantItem"])



	def get_mismatch_categories(self,title,**args):
		"""
		Bir merchant item title'i icin match edilmemesi gereken categoryleri alir

		@type 	title: str
		@param 	title: merchantItemTitle

		@type	args: dict
		@param	args: API call icin url parametreleri. desteklenen bazi parametreler: 
				status, sid, start (default=0), max (default=-1), fields (default=""), expandLevel (default=1),
				catIds, catId, merchantId, sortField, sortOrder, filter, itemId, cimriUrl, mCatNames

		@rtype: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
		@return: MerchantItem listesi ya da hata durumunda None
		"""

		self.logger.info("api call...")

		#sample http://glacier.cimri.com:8080/cimri-service/matcher/dontmatchkeywords?keyword=rexona%20deodorant
		packet=self.call(Template("matcher/dontmatchkeywords?keyword=${title}").substitute(title=urllib2.quote(title)),args=args)
		if packet is None:
			return None
		elif packet.strip()=="":
			return []

		#parse
		try:
			data=json.loads(packet)
			return [ cat["categoryId"] for cat in data["matcherDontMatch"]["categories"] ]
		except:
			temp_data = data["matcherDontMatch"]["categories"]
			return [ temp_data["categoryId"] ]


	def get_items_by_category(self,**args):
		"""
		Kategoriye gore merchant itemlari alir

		@type	args: dict
		@param	args: API call icin url parametreleri. desteklenen bazi parametreler: 
				mStatus, status, sortField, sortOrder, merchantId, start (default=0), max (default=-1),
				merchantCategory, filter, fields (default=""), expandLevel (default=1)

		@rtype: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
		@return: MerchantItem listesi ya da hata durumunda None
		"""

		self.logger.info("api call...")

		#sample http://glacier.cimri.com:8080/cimri-service/merchant/mItems/category?max-10
		packet=self.call("merchants/mItems/category",args=args)
		if packet is None:
			return None

		#parse and return items
		return MerchantItem.list_from_json(packet,["merchantItem"])


	def get_items_by_mpn(self,**args):
		"""
		MPN degerlerine dayanarak merchant itemlari alir

		@type	args: dict
		@param	args: API call icin url parametreleri. desteklenen bazi parametreler: 
				mpntype, mpnvalue, start (default=0), max (default=-1), fields (default=""), expandLevel (default=1)

		@rtype: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
		@return: MerchantItem listesi ya da hata durumunda None
		"""

		self.logger.info("api call...")

		#make call
		packet=self.call("merchants/items/search/mpn",args=args)
		if packet is None:
			return None

		#parse and return items
		return MerchantItem.list_from_json(packet,["merchantItem"])
		
	#------------------------------------------------------------------------ merchant item related calls
	



	#- count related calls ------------------------------------------------------------------------------

	def get_counts(self,**args):
		"""
		Cesitli merchant sayilari ve rakamlarini bulmak icin kullanilabilir

		@type	args: dict
		@param	args: API call icin url parametreleri. desteklenen bazi parametreler: 
				mStatus, status, sid, mCatNames, catIds, catId, merchantId, filter, merchantCategory,
				cimriUrl, itemid, groupByCategory (default=false), fields (default="")

		@rtype: int
		@return: belirlenen parametrelere uyan merchant sayisi
		"""

		self.logger.info("api call...")

		#make call
		return self.call("merchants/counts",args=args)


	def get_category_counts(self,**args):
		"""
		Cesitli merchant kategori sayilari ve rakamlarini bulmak icin kullanilabilir

		@type	args: dict
		@param	args: API call icin url parametreleri. desteklenen bazi parametreler: 
				mStatus, status, merchantId, filter, merchantCategory

		@rtype: int
		@return: belirlenen parametrelere uyan merchant kategori sayisi
		"""

		self.logger.info("api call...")

		#make call
		return self.call("merchants/mCategory/counts",args=args)

	#-------------------------------------------------------------------------------- count related calls




	#- update related calls -----------------------------------------------------------------------------

	def update_items(self,items,**args):
                """
		MerchantItemlari (L{cimri.api.cimriservice.data.merchantitem.MerchantItem}) cimri service uzerinde
		guncellemek icin kullanilir.

		@type: list (L{cimri.api.cimriservice.data.merchantitem.MerchantItem})
		@param: update edilecek MerchantItemlarin listesi

		@type	items: dict
		@param	args: API call icin opsiyonel url parametreleri

		@rtype: bool
		@return: HTTP PUT call basarili ise True, aksi takdirde False
                """

		self.logger.info("api call...")

		#process item
		def process(item):
			pre=item.to_dict()
			post={}
			for key in pre:
				if pre[key] is not None and pre[key] is not {}:
					post[key]=pre[key]
			return post
			
		#get packet
		packet=json.dumps({"merchantItem":[process(item) for item in items]})

#		f=open("update.txt","w")
#		f.write("\n".join(["\n".join([item.merchantItemTitle,repr(item.merchantItemTitle),"\n"]) for item in items]))
#		f.write(packet)
#		f.close()

		return self.put("merchants/items/sma",packet)



	def clean_paused_items(self,items,**args):
                """
		Belirli statude bulunan MerchantItemlarin (L{cimri.api.cimriservice.data.merchantitem.MerchantItem}) 
		cimri service uzerindeki itemidkerini temizlemek icin kullanilir.

		@type: list (L{cimri.api.cimriservice.data.merchantitem.MerchantItem})
		@param: temizlenecek MerchantItemlarin listesi

		@type	items: dict
		@param	args: API call icin opsiyonel url parametreleri

		@rtype: bool
		@return: HTTP DELETE call basarili ise True, aksi takdirde False
                """

		self.logger.info("api call...")

		return self.put("merchants/items/paused", "&".join( [ "sid="+str(item.sid) for item in items] ) )


	#------------------------------------------------------------------------------- update related calls






	#- unused calls (not fully implemented/tested -------------------------------------------------------

	def get_items_summary_counts(self,id):
		"""
		Kullanilmiyor
		"""
		self.logger.info("api call...")

		#sample http://glacier.cimri.com:8080/cimri-service/merchants/2161/items/summarycounts
		return self.call(Template("merchants/$id/items/summarycounts").substitute(id=id))



	def get_item(self,id,**args):
		"""
		Kullanilmiyor
		"""

		self.logger.info("api call...")

		#make call
		packet=self.call(Template("merchants/items/$id").substitute(id=id),args=args)

		#parse and return item
		items=MerchantItem.list_from_json(packet,["merchant"])

		#return item
		return items[0] if items!=None else None




	def get_merchant_log(self,id,**args):
		"""
		Kullanilmiyor
		"""

		self.logger.info("api call...")

		return self.call(Template("merchants/$id/rawlog").substitute(id=id),args=args)

		
	def get_raw_log(self,id,**args):
		"""
		Kullanilmiyor
		"""

		self.logger.info("api call...")

		return self.call(Template("merchants/rawlog/$id").substitute(id=id),args=args)

		
	def save_log(self,log):
		"""
		Kullanilmiyor
		"""

		self.logger.info("api call...")

		return self.call("merchants/rawlog",data=log.pack())


	def search_merchants(self,username,**args):
		"""
		Kullanilmiyor
		"""
	
		self.logger.info("api call...")

		args["username"]=username

		return self.call("merchants/search/username",args=args)



	def login_merchant(self,**args):
                """
		Kullanilmiyor
                """

		self.logger.info("api call...")

		return self.call("merchants/login",args=args)


	def change_password(self,id,**args):
                """
		Kullanilmiyor
                """

		self.logger.info("api call...")

		return self.call(Template("merchants/$id/password").substitute(id=id),args=args)


	def direct_matcher(self,**args):
		"""
		Kullanilmiyor
		"""

		self.logger.info("api call...")

		return self.call("merchants/directmatcher",args=args)


	def get_items_for_bo(self,**args):
                """
		Kullanilmiyor
                """

		self.logger.info("api call...")

		return self.call("merchants/itemsforbo",args=args)


	def get_popular_items(self,id,**args):
                """
		Kullanilmiyor
		"""

		self.logger.info("api call...")

		return self.call(Template("merchants/$id/populeritems").substitute(id=id),args=args)



	def update_item_status(self,**args):
                """
		Kullanilmiyor
                """

		self.logger.info("api call...")

		return self.call("merchants/items",args=args)


	def update_item(self,**args):
                """
		Kullanilmiyor
                """

		self.logger.info("api call...")

		return self.call("merchants/items/upt",args=args)


	def update_category(self,**args):
                """
		Kullanilmiyor
                """

		self.logger.info("api call...")

		return self.call("merchants/categories/upt",args=args)


	def get_top_merchant_items(self,id,**args):
                """
		Kullanilmiyor
                """

		self.logger.info("api call...")

		return self.call(Template("merchants/$id/topitems").substitute(id=id),args=args)


	def get_merchant_by_logo_name(self,logo,**args):
                """
		Kullanilmiyor
                """

		self.logger.info("api call...")

		return self.call(Template("merchants/logo/$logo").substitute(logo=logo),args=args)


	def delete_item(self,**args):
                """
		Kullanilmiyor
                """

		self.logger.info("api call...")

		return self.call("merchants/deleteMerchantItem",args=args)


	def get_untrusted_merchants(self,**args):
                """
		Kullanilmiyor
                """

		self.logger.info("api call...")

		return self.call("merchants/untrusted",args=args)


	def delete_untrusted_merchant(self,id,**args):
                """
		Kullanilmiyor
                """

		self.logger.info("api call...")

		return self.call(Template("merchants/untrusted/$id").substitute(id=id),args=args)



	def make_merchant_untrusted(self,id,**args):
                """
		Kullanilmiyor
                """

		self.logger.info("api call...")

		return self.call(Template("merchants/$id/makeuntrusted").substitute(id=id),args=args)


