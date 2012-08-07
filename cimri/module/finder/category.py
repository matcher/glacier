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

class CategoryFinder(Finder):
	"""
	Urun kategorisi finder modulu. Kullanilmiyor.
	"""

	def __init__(self):
		super(CategoryFinder,self).__init__()



#bootstrap
if __name__=="__main__":
        #run module
        mod=CategoryFinder()
        args=mod._parse_argv()
        mod._run(**args)
		
