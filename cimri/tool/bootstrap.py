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


import sys
import os
import os.path
from subprocess import Popen

def bootstrap():
	"""
	kullanilmiyor
	"""

	#get directory
	path=os.path.split(os.path.split(os.getcwd())[0])[0]
	print path

	if path not in sys.path:
    		sys.path.append(path)

	#spawn
	Popen(["python","cimri/module/automation/controller.py","--host","localhost","--port","10000"], env={"PYTHONPATH": path})


if __name__=="__main__":
	bootstrap()	
