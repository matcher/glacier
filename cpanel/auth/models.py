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


#is this needed with mongoengine?
#from django.db import models

import mongoengine
from mongoengine import *
import datetime
import json
import hashlib

from cpanel.config.config import Config
from cpanel.app.document import SerialDoc

class User(Document,SerialDoc):	
	name = StringField(max_length=100, required=True, unique_with='email')
	email = EmailField(max_length=100, required=True)
 	type = StringField(max_length=12, required=True)                #admin, operator
	pwd = StringField(max_length=40, required=True)
	created = DateTimeField(default=datetime.datetime.now)
	
	@classmethod	
	def authenticate(self,uname,pwd):	
		try:
			#connect to db
			SerialDoc.connectdb()

			#find user
			user=User.objects.get(name=uname,
					      pwd=User._get_password_hash(pwd))

			print repr(user)

			if user==None:
				return None

			return user

		except Exception as e:
			return None


	def create(self):
		try:
			#hash password
			self.pwd=User._get_password_hash(self.pwd)

			#connect to db
			SerialDoc.connectdb()

			#save
			self.save()

			return self

		except Exception as e:
			return None


	@classmethod
	def _get_password_hash(self,pwd):
		return hashlib.sha1(repr(pwd) + "," + Config.pwd_key).hexdigest()


