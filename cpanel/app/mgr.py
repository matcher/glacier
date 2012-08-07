""" 
cimri matcher control panel
---------------------------
date:                    01.31.2012
author:                  gun@alppay.com

description:
------------

revision history: 
-----------------
gun@alppay.com:          initial version

"""

import xmlrpclib

from cpanel.config.config import Config
from cpanel.app.logger import Logger

class AppMgr(object):
	def __init__(self,request):	
		self.request=request		#set the HttpRequest reference
		
	def rpccall(self,cmd,*args):
		#host
		host=Config.matcher_controller_host
		port=Config.matcher_controller_port

		try:
			#connect
		        proxy=xmlrpclib.ServerProxy("http://"+host+":"+str(port)+"/")
        	
			#get method
			method=getattr(proxy,cmd,None)
        
			#make call
			resp=method(*args)

			return resp

		except Exception as e:
			Logger.getlogger("app").info(e)

			return None
