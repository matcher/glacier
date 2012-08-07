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


from django.http import HttpResponse
from django.shortcuts import *

from cpanel.config.config import Config
from cpanel.app.logger import Logger
from cpanel.app.protocol import *


#decorator for checking valid session on view handlers
def requires_session(roles=None):
	def decorator(func):
		def wrapper(request,*args,**kwargs):
			#check session
		        if 'user' not in request.session or (roles is not None and request.session["user"].type not in roles):
				return redirect("/")

			return func(request,*args,**kwargs)

		return wrapper

	return decorator

#decorator for checking valid session on view handlers
def api_requires_session(roles=None):
	def decorator(func):
		def wrapper(request,*args,**kwargs):
			#check session
		        if 'user' not in request.session or (roles is not None and request.session["user"].type not in roles):
				return HttpResponse( AIResponse( error=AIError(AIError.NO_SESSION) ).serialize() )

			return func(request,*args,**kwargs)

		return wrapper

	return decorator


#decorator for implementing API wrapper functionality such as exception handling
#include this at the end of the decorator list for each view function (to make sure
#the actual function name gets logged)
def api_call(func):
	def wrapper(*args,**kwargs):
		try:
			return func(*args,**kwargs)
		
	        except Exception as e:
			Logger.getlogger("view").error("exception occurred within "+func.__name__)
			Logger.getlogger("view").error(str(e))
			
		return HttpResponse( AIResponse(error=AIError(AIError.SYSTEM)).serialize() )

	return wrapper
