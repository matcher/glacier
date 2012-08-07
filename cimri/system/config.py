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


from cimri.system.logger import Logger
from ConfigParser import SafeConfigParser

class Config():
        """
	Sistem konfigurasyon bilgilerine erisim saglar
        """

	config=None

	def __init__(self,section):
	        """
	        @type  section: str
	        @param section: erisim istenen konfigurasyon sectioni
	        """

		self.section=section


  	@classmethod
        def getconfig(cls,section):
	        """
	      	Belli bir konfigurasyon sectioni icin Config instancei yaratir

	        @type  section: str
	        @param section: erisim istenen konfigurasyon sectioni

	        @rtype: L{cimri.system.config.Config}
	        @return: istenen section icin Config instancei
	        """

                #initialize configuration mgr
                if Config.config==None:
                        Config._initialize()

                return Config(section)


	def get(self,option):
	        """
		Istenen konfigurasyon degerini verir

	        @type  option: str
	        @param option: istenen konfigurasyon parametresi

	        @rtype: str
	        @return: konfigurasyon degeri
	        """

		if self.section not in Config.config:
			return None

		return Config.config[self.section][option] if option in Config.config[self.section] else None


	@classmethod
	def _initialize(cls):
		"""
		Sistem konfigurasyonunu tanimlanmis dosyadan yukler
	        """

		Logger.getlogger("Config").info("initializing configuration manager...")

		#initialize config data
		Config.config={}

		#read configuration
		parser=SafeConfigParser()
		try:
			parser.read("cimri/config/config.ini")
			for section in parser.sections():
				Config.config[section]={}
				for option in parser.options(section):
					Config.config[section][option]=parser.get(section,option)

		except Exception as e:
			Logger.getlogger("Config").error("there was an error reading systen configuration file")
