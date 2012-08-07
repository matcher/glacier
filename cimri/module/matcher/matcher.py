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


from cimri.module.module import Module

class Matcher(Module):
	"""
	Butun matcher classleri icin base class
	"""

	def __init__(self):
		super(Matcher,self).__init__()

		
	def match_item(self,merchant,item):
		pass


	def _test_update(self,result,refitem):
                """
		Belli bir MerchantItem icin match sonuclarini ve istatistiklerini kayit eder.

                @type  result: dict
                @param result: item match sonuclarini iceren bilgiler

                @type  refitem: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param refitem: match sonuclarini karsilastirmak icin referans olarak kullanian MerchantItem
                """

		def get_item_id(item):	
			if item.item is None:
				return None
			elif "itemId" not in item.item:
				return None
			elif item.item["itemId"] is None:
				return None
			elif item.item["itemId"] == "":
				return None
			return item.item["itemId"]

		def get_possible_item_id(item):	
			if item.possibleSolrItem is None:
				return None
			elif "itemId" not in item.possibleSolrItem:
				return None
			elif item.possibleSolrItem["itemId"] is None:
				return None
			elif item.possibleSolrItem["itemId"] == "":
				return None
			return item.possibleSolrItem["itemId"]
		
		#get item
		item=result["data"]

		#get matched item id and possible solr item id
		matched_item_id=get_item_id(item)
		matched_possible_item_id=get_possible_item_id(item)

		#if there was no reference item, there's noting to test
		if refitem is None:
			return

		#if the reference item indicates there should be no match, and there was no match, record success
		if refitem.item is None and matched_item_id is None:
			self.task.stats["test"]["passed"]=self.task.stats["test"]["passed"]+1

		#if there should have been no match but there was, record failure
		elif refitem.item is None and matched_item_id is not None:
			self.task.stats["test"]["failed"]=self.task.stats["test"]["failed"]+1

		#if the expected item was matched, record success
		elif matched_item_id is not None and matched_item_id == refitem.item["itemId"]:
			self.task.stats["test"]["passed"]=self.task.stats["test"]["passed"]+1
		
		#if an item other than the expected item was matched, record failure 
		elif matched_item_id is not None and matched_item_id != refitem.item["itemId"]:
			self.task.stats["test"]["failed"]=self.task.stats["test"]["failed"]+1
			
		#check if the item was found as a possible item correctly
		elif matched_possible_item_id == refitem.item["itemId"]:
			self.task.stats["test"]["guessed"]=self.task.stats["test"]["guessed"]+1

		elif matched_possible_item_id != refitem.item["itemId"]:
			self.task.stats["test"]["badguess"]=self.task.stats["test"]["badguess"]+1


	def _test_finalize(self):
                """
		Match islemi sirasinda takip edilen istatistikler ile ilgili belirli ozetler cikartir ve islem 
		sonuclari icinde kayit eder. 
                """

		#match accuracy
		passed=self.task.stats["test"]["passed"]
		total=self.task.stats["test"]["passed"]+self.task.stats["test"]["failed"]
		if total>0:
			self.task.stats["test"]["accuracy"]=int(100*float(passed)/total)

		#match percentage
		passed=self.task.stats["test"]["passed"]
		total=len(self.task.result) if self.task.op=="match-sim" else len(self.task.data)
		if total>0:
			self.task.stats["test"]["match_percent"]=int(100*float(passed)/total)

		#guess accuracy
		passed=self.task.stats["test"]["guessed"]
		total=self.task.stats["test"]["guessed"]+self.task.stats["test"]["badguess"]
		if total>0:
			self.task.stats["test"]["guess_accuracy"]=int(100*float(passed)/total)

		#guess percentage
		passed=self.task.stats["test"]["guessed"]
		total=len(self.task.result) if self.task.op=="match-sim" else len(self.task.data)
		if total>0:
			self.task.stats["test"]["guess_percent"]=int(100*float(passed)/total)

