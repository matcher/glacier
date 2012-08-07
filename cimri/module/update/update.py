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

class Updater(Module):
	"""
	Butun updater modulleri icin base class
	"""

	def __init__(self):
		super(Updater,self).__init__()
		
