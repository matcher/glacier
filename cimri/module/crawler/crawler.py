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

class Crawler(Module):
	"""
	Butun crawler classleri icin base class
	"""

	def __init__(self):
		super(Crawler,self).__init__()

