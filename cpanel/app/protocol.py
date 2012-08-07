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


import json
from string import Template

class AIError():
	VALIDATION=1
	PERMISSION=2
	NO_DATA=3
	SYSTEM=4
	PROTOCOL=5
	NO_SESSION=6
	LEAGUE_API_ACCESS=7

	def __init__(self,code,msg=""):
		self.code=code
		self.msg=msg
		

class AIResponse():
	SUCCESS=1
	ERROR=-1

	def __init__(self,data=None,error=None):
		class Response():
			def __init__(self):
				self.status=None
				self.error=None
				self.data=None

		self.is_iframe_resp=False
		self.resp=Response()
	
		if data!=None:
			self.resp.data=data
		if error!=None:
			self.resp.status=AIResponse.ERROR
			self.resp.error=error
		else:
			self.resp.status=AIResponse.SUCCESS

	def setIFrameResponse(self):
		self.is_iframe_resp=True			
		return self
	
	def serialize(self):
		try:
			packet=json.dumps({"status": self.resp.status,
					   "error":  (None if self.resp.error==None else {"code":self.resp.error.code,"msg":self.resp.error.msg}),
					   "data":   self.resp.data})
		except Exception as e:  
			packet=Template("{\"status\": {status} ,\"error\":{\"code\": {err},\"msg\":\"protocol error\"} }").substitute(status=str(AIResponse.ERROR),err=str(AIError.PROTOCOL))
			
		#wrap response for iframe calls
		if self.is_iframe_resp:
			return "<html><head></head><body><textarea>"+packet+"</textarea></body></html>"
		else: 	
			return packet
		 

	def getError(self):
		return self.resp.error
		
	def getStatus(self):
		return self.resp.status
		
	def getData(self):
		return self.resp.data
