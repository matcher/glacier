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


from cimri.module.finder.finder import Finder

class ProductFinder(Finder):
	"""
	Urun finder modulu. Kullanilmiyor.
	"""

	def __init__(self):
		super(ProductFinder,self).__init__()

		
#bootstrap
if __name__=="__main__":
        #run module
        mod=ProductFinder()
        args=mod._parse_argv()
        mod._run(**args)
