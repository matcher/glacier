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


class CimriStatus():
	"""
	Tanimli MerchantItem statuslerini ve xml'den gelip gelmeme durumunda bu statuslerin nasil degistiklerini tanimlar.
	"""

	class Transformation():
		def __init__(self,name,activecode,pausedcode):
			self.name=name
			self.activecode=activecode
			self.pausedcode=pausedcode

		def __str__(self):
			return self.name

	transformations={0:	Transformation("PAUSED_BY_CIMRI"			,  0,  8),
			 1:	Transformation("ACTIVE"					,  1,  7),
			 2:	Transformation("PAUSED_BY_MERCHANT"			,  2,  2),
			 3:	Transformation("PROCESSING_ACTIVE"			,  3,  7),
			 4:	Transformation("PROCESSING_PAUSED"			,  4,  8),
			 5:	Transformation("PROCESSING_SOLR_MATCHED"		,  5,  9),
			 6:	Transformation("PROCESSING_GOOGLE_MATCHED"		,  6, 10),
			 7:	Transformation("PAUSED_NO_IN_XML_ACTIVE"		,  1,  7),
			 8:	Transformation("PAUSED_NO_IN_XML_PAUSED"		,  0,  8),
			 9:	Transformation("PAUSED_NO_IN_XML_SOLR"			, 12,  9),
			10:	Transformation("PAUSED_NO_IN_XML_GOOGLE"		, 13, 10),
			11:	Transformation("BLACKLIST_ITEM"				, 11, 11),
			12:	Transformation("SOLR_MATCHED"				, 12,  9),
			13:	Transformation("GOOGLE_MATCHED"				, 13, 10),
			14:	Transformation("GOOGLE_SOLR_MATCHED"			, 14, 17),
			15:	Transformation("UNREGISTERED_CATEGORY"			, 15, 15),
			16:	Transformation("PROCESSING_GOOGLE_SOLR_MATCHED"		, 16, 17),
			17:	Transformation("PAUSED_NO_IN_XML_GOOGLE_SOLR_MATCHED"	, 14 ,17), 
			18:	Transformation("PAUSED_BY_OPERATOR"			, 18, 18), 
			19:	Transformation("PAUSED_BY_CIMRI_ZERO_PRICE"		, 19, 19) }


	def __init__(self,code):
                """
                @type  code: int
                @param text: status id
                """

		self.code=int(code)
		self.transformation=CimriStatus.transformations[self.code]



	def __str__(self):
                """
		Statusun string karsiligini verir. Ornegin 1 statusunun karsiligi "ACTIVE" olarak verilir.
                """

		return str(self.transformation)


	@classmethod
	def get_status(self,name):
                """
		Bir cimri status'un ismine gore o status'u temsil eden CimriStatus class instanceini verir

                @type  text: str
                @param text: status'un ismi

                @rtype: L{cimri.api.cimriservice.status.CimriStatus}
                @return: CimriStatus instancei
                """

		for code in CimriStatus.transformations:
			if str(CimriStatus.transformations[code])==name:
				return CimriStatus(code)

	def get_code(self):
                """
		CimriStatus instanceinin temsil ettigi status kodunu verir

                @rtype: int
                @return: status kodu
                """

		return self.code



	def get_active_status(self):
                """
		Bu status'e sahip bir merchant itemin xml'den geldigi zaman alinacagi statusu temsil eden CimriStatus instanceini verir

                @rtype: L{cimri.api.cimriservice.status.CimriStatus}
                @return: CimriStatus instancei
                """

		return CimriStatus(self.transformation.activecode)


	def get_paused_status(self):
                """
		Bu status'e sahip bir merchant itemin xml'den gelmedigi zaman alinacagi statusu temsil eden CimriStatus instanceini verir

                @rtype: L{cimri.api.cimriservice.status.CimriStatus}
                @return: CimriStatus instancei
                """

		return CimriStatus(self.transformation.pausedcode)
	
	
	def is_active(self):
		"""
		Bu CimriStatus instancinin temsil ettigi statusun aktif bir status olup olmadigini verir

		@rtype: bool
		@return: status aktif bir status ise True aksi takdirde False
		"""
		return self.code==CimriStatus(self.transformation.activecode).code

