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

class Scrapper(Module):
	"""
	Butun scraper modulleri icin base class
	"""

	def __init__(self):
		super(Scrapper,self).__init__()

		
	def _test_update(self,item,refitem):
                """
		Belli bir MerchantItem icin scrape sonuclarini ve istatistiklerini kayit eder.

                @type  result: dict
                @param result: item match sonuclarini iceren bilgiler

                @type  refitem: L{cimri.api.cimriservice.data.merchantitem.MerchantItem}
                @param refitem: scrape sonuclarini karsilastirmak icin referans olarak kullanian MerchantItem
                """

		#was there any data to be found?
		if item is None and refitem is not None:
			#there should have been a scraped item but none was found
			self.task.stats["test"]["failed"]=self.task.stats["test"]["failed"]+1

		elif item is not None and refitem is None:
			#there should have been no scraped item but there was one found
			self.task.stats["test"]["failed"]=self.task.stats["test"]["failed"]+1

		elif item is None and refitem is None:
			#there was no scraped item as expected
			self.task.stats["test"]["passed"]=self.task.stats["test"]["passed"]+1

		else:
			#compare fields
			passed=True
			for field in vars(refitem):
				#get values
				scraped_value=getattr(item,field)
				ref_value=getattr(refitem,field)

				#ignore fields that are not being tested
				if ref_value is None:
					continue

				#ignore these fields
				if field in ["merchantItemId","merchantItemUrl","merchant"]:
					continue

				#process
				scraped_value=None if scraped_value is None else unicode(scraped_value).strip()
				ref_value=None if ref_value is None else unicode(ref_value).strip()

				#update stats
				if field not in self.task.stats["test"]["fields"]:
					#p: passed, f:failed, a:accuracy
					self.task.stats["test"]["fields"][field]={"p":0,"f":0,"a":0}
				if scraped_value==ref_value:
					count=self.task.stats["test"]["fields"][field]["p"]
					self.task.stats["test"]["fields"][field]["p"]=count+1
				else:
					count=self.task.stats["test"]["fields"][field]["f"]
					self.task.stats["test"]["fields"][field]["f"]=count+1
					passed=False

			#record overall
			if passed:
				self.task.stats["test"]["passed"]=self.task.stats["test"]["passed"]+1
			else:
				self.task.stats["test"]["failed"]=self.task.stats["test"]["failed"]+1


	def _test_finalize(self):
                """
		Scrape islemi sirasinda takip edilen istatistikler ile ilgili belirli ozetler cikartir ve islem 
		sonuclari icinde kayit eder. 
                """

		#total
		total=self.task.stats["test"]["passed"]+self.task.stats["test"]["failed"]
		if total==0:
			return

		#overall accuracy
		self.task.stats["test"]["accuracy"]=int((100.0*self.task.stats["test"]["passed"])/total)

		#field accuracy
		passed=0
		failed=0
		for field in self.task.stats["test"]["fields"].keys():	
			#get field stats
			stats=self.task.stats["test"]["fields"][field]
			total=stats["p"]+stats["f"]
			if total==0:
				continue

			#field accuracy
			self.task.stats["test"]["fields"][field]["a"]=int((100.0*stats["p"])/total)
		
			passed=passed+stats["p"]	
			failed=failed+stats["f"]

		#overall field accuracy
		if (passed+failed)>0:
			self.task.stats["test"]["accuracy.field"]=int((100.0*passed)/(passed+failed))

	
