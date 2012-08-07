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

import logging
import logging.config
import os
import inspect
from string import Template

from cpanel.config.config import Config
 
class Logger():
	logger=None
	
	def __init__(self,name):
		self.name=name
				
	@classmethod
	def getlogger(cls,name):
		#configure logger if not configured yet
		if Logger.logger==None:
			Logger._configure()
			
		return Logger(name)
	
	def debug(self,msg,*args):
		#log but check if the log level is enabled first
		if Logger.logger.isEnabledFor(logging.DEBUG):
			args=self._process_args(args)
			Logger.logger.debug(self._format(msg),*args)
		
	def info(self,msg,*args):
		#log but check if the log level is enabled first
		if Logger.logger.isEnabledFor(logging.INFO):
			args=self._process_args(args)
			Logger.logger.info(self._format(msg),*args)
	
	def warn(self,msg,*args):
		#log but check if the log level is enabled first
		if Logger.logger.isEnabledFor(logging.WARN):
			args=self._process_args(args)
			Logger.logger.warn(self._format(msg),*args)
	
	def error(self,msg,*args):
		#log but check if the log level is enabled first
		if Logger.logger.isEnabledFor(logging.ERROR):
			args=self._process_args(args)
			Logger.logger.error(self._format(msg),*args)
	
	def critical(self,msg,*args):
		#log but check if the log level is enabled first
		if Logger.logger.isEnabledFor(logging.CRITICAL):
			args=self._process_args(args)
			Logger.logger.critical(self._format(msg),*args)
		
	@classmethod
	def _configure(self):
		#logger
		logging.config.fileConfig(Config.log_config)
		Logger.logger = logging.getLogger('cpanel')
	
	def _format(self,msg):
		#get caller - this is the 3rd previous function on the stack:  caller > debug|info|warn|error|critical > _format
		caller=inspect.stack()[2][3]
		
		#format message
		return Template("$pid:$name.$caller(...): $msg").substitute(name=self.name, pid=os.getpid(), caller=caller, msg=msg )

	def _process_args(self,args):
		#invoke any functions
		args=[arg() if hasattr(arg,'__call__') else arg for arg in args]
		return args

		
