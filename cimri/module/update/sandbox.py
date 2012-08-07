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


from itertools import chain
import re

from cimri.system.logger import Logger
from cimri.api.cimriservice.merchants import MerchantsAPI
from cimri.module.update.update import Updater

class SandboxUpdater(Updater):
        """
	SandboxUpdater gelistirme sureci ve testler icindir. Cimri Service'de herhangi bir veri guncellemez.

	Modul tarafindan desteklenen islem turleri ve opsiyonlari su sekildedir:

        "update" islemi: belirlenen update direktiflerini simule eder

                task.data	: islemden gecirilmesi istenilen her item icin "data" o item'in bilgilerini iceren
				  MerchantItem olmalidir (L{cimri.api.cimriservice.merchantitem.MerchantItem})

				  bunun yaninda, her item icin asagidaki veriler de saglanmalidir:

                                  "meta.action"                 : "update" ya da "insert" degerini icermelidir.
								  item uzerinde backendde yapilmasi istenilen
								  operasyonu belirler.

                task.meta       : -

                task.result     : islemden gecirilmesi istenilen her item icin "data" o item icin guncellenmis
				  MerchantItem'dir (L{cimri.api.cimriservice.merchantitem.MerchantItem})

				  bunun yaninda, her item icin asagidaki veriler de saglanir:

                                  "meta.result"	                : "success" ya da "fail" degerlerinden birini icerir

				  "meta.error"			: eger operasyonda bir hata olusursa, hata hakkinda
								  bilgiler icerir

        """

	def __init__(self):
		#initialize parents
		Updater.__init__(self)
		
		self.logger=Logger(self.__class__.__name__)

		#supported operations
		self.ops={"update"	:self._task_update}



	def _task_update(self):
                """
		"update" islemini calistirir
                """

		self.logger.info("api call...")

		#set result
		self.result=[{"data":item["data"], "result":"success"} for item in self.task.data]		



#bootstrap
if __name__=="__main__":
        #run module
        mod=SandboxUpdater()
        args=mod._parse_argv()
        mod._run(**args)
