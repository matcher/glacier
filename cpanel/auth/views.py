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
from django.shortcuts import redirect

from cpanel.auth.mgr import AuthMgr
from cpanel.app.protocol import *
from cpanel.app.logger import Logger
from cpanel.app.view import *


@api_call
def login(request,uname,pwd):
	#get authentication mgr
	mgr=AuthMgr(request)
	
	#authenticate user
	auth=mgr.login(uname,pwd)
	if auth==False:
		return HttpResponse( AIResponse(error=AIError(AIError.VALIDATION)).serialize() )
	
	#return authentication
	return HttpResponse( AIResponse(data=auth).serialize() )
	

@api_requires_session()
@api_call	
def logout(request):
	#get authentication mgr
	mgr=AuthMgr(request)

	#log user out
	mgr.logout()
	
	#return authentication
	return HttpResponse( AIResponse().serialize() )
	
