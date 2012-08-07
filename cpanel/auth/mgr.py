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

from mongoengine import *
import json
import uuid
import hashlib
import random
from string import Template

from django.core.mail import send_mail

from cpanel.auth.models import User
from cpanel.config.config import Config
from cpanel.app.mgr import AppMgr
from cpanel.auth.models import *
from cpanel.app.logger import Logger

class AuthMgr(AppMgr):
	def __init__(self,request):	
		super(AuthMgr,self).__init__(request)
		self.logger=Logger.getlogger(self.__class__.__name__)
		
	def login(self,uname,pwd):
		#end previous session first
		self.request.session.clear()
	
		#check user
		usr=User.get(name=uname,pwd=User._get_password_hash(str(pwd)))

		self.logger.info("...logging in..."+uname+" "+pwd)

		if usr is None:
			return False
		
		#start session
		self.request.session['user']=usr
		self.request.session.modified = True
		
		return True

	
	def logout(self):
		#end session
		self.request.session.clear()

		return True

		
