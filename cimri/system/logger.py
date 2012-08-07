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


import logging
import logging.config
import os
import inspect
from string import Template

 
class Logger():
        """
	Log operasyonlari icin kullanilir
        """

	logger=None

	
	def __init__(self,name):
	        """
	        @type  name: str
	        @param name: log bolumunun ismi
	        """

		self.name=name

				
	@classmethod
	def getlogger(cls,name):
	        """
		Bellir bir log bolumu icin bir Logger objecti verir

	        @type  name: str
	        @param name: log bolumunun ismi

	        @rtype: L{cimri.system.logger.Logger}
	        @return: istenen log bolumu icin bir Logger objecti
	        """

		#configure logger if not configured yet
		if Logger.logger==None:
			Logger._configure()
			
		return Logger(name)

	
	def debug(self,msg,*args):
	        """
		Debug seviyesinde bir log yaratir
	
	        @type  msg: str
	        @param msg: log mesaji

	        @type  args: args
	        @param args: log yazilacak opsiyonel bilgiler
	        """

		#log but check if the log level is enabled first
		if Logger.logger.isEnabledFor(logging.DEBUG):
			args=self._process_args(args)
			Logger.logger.debug(self._format(msg),*args)

		
	def info(self,msg,*args):
	        """
		Info seviyesinde bir log yaratir
	
	        @type  msg: str
	        @param msg: log mesaji

	        @type  args: args
	        @param args: log yazilacak opsiyonel bilgiler
	        """

		#log but check if the log level is enabled first
		if Logger.logger.isEnabledFor(logging.INFO):
			args=self._process_args(args)
			Logger.logger.info(self._format(msg),*args)
	

	def warn(self,msg,*args):
	        """
		Warning seviyesinde bir log yaratir
	
	        @type  msg: str
	        @param msg: log mesaji

	        @type  args: args
	        @param args: log yazilacak opsiyonel bilgiler
	        """

		#log but check if the log level is enabled first
		if Logger.logger.isEnabledFor(logging.WARN):
			args=self._process_args(args)
			Logger.logger.warn(self._format(msg),*args)
	

	def error(self,msg,*args):
	        """
		Error seviyesinde bir log yaratir
	
	        @type  msg: str
	        @param msg: log mesaji

	        @type  args: args
	        @param args: log yazilacak opsiyonel bilgiler
	        """

		#log but check if the log level is enabled first
		if Logger.logger.isEnabledFor(logging.ERROR):
			args=self._process_args(args)
			Logger.logger.error(self._format(msg),*args)

	

	def critical(self,msg,*args):
	        """
		Critical seviyesinde bir log yaratir
	
	        @type  msg: str
	        @param msg: log mesaji

	        @type  args: args
	        @param args: log yazilacak opsiyonel bilgiler
	        """

		#log but check if the log level is enabled first
		if Logger.logger.isEnabledFor(logging.CRITICAL):
			args=self._process_args(args)
			Logger.logger.critical(self._format(msg),*args)
		

	@classmethod
	def _configure(self):
	        """
		Log konfigurasyon dosyasina dayanarak python loggingi ayarlar
	        """

		#logger
		logging.config.fileConfig('cimri/config/logger.conf')
		Logger.logger = logging.getLogger('matcher')
	

	def _format(self,msg):
	        """
		Bir log mesajini log konfigurasyonunda tanimli olan diger bilgileri ekleyerek loga yazilacak formatli mesaji yaratir
	
	        @type  msg: str
	        @param msg: log mesaji
	
	        @rtype: str
	        @return: formatlanmis log mesaji
	        """

		#get caller - this is the 3rd previous function on the stack:  caller > debug|info|warn|error|critical > _format
		caller=inspect.stack()[2][3]
		
		#format message
		return Template("$pid:$name.$caller(...): $msg").substitute(name=self.name, pid=os.getpid(), caller=caller, msg=msg )


	def _process_args(self,args):
	        """
		Loga yazilacak verileri verilerin turune gore onislemden gecirerek loga yazilmak icin hazirlar. Eger verilerden
		herhangi biri bir fonksiyon ise, bu fonksiyonlar loga tam yazilmadan once cagrilarak loga yazilacak degerler
		elde edilir. Eger aktif log seviyesi yaratilan logun seviyesinden yuksek ise bu fonksiyonlar log yazilmayacagi
		icin gereksiz bir sekilde cagrilmaz. Bu ozellik loga yazilmak istenen ve uzun komputasyon gerektiren islemlerin
		gereksiz yapilmamasi icindir.

	        @type  args: list
	        @param args: veri listesi
	
	        @rtype: list
	        @return: islenmis parametreler
	        """

		#invoke any functions
		args=[arg() if hasattr(arg,'__call__') else arg for arg in args]
		return args

		
