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


class FSM(object):
	"""
	finite state machine
        """

	def __init__(self,state,transitions=[]):
	        """
	        @type  state: str
	        @param state: baslangic statei

	        @type  transitions: list
	        @param transitions: state machine icin tanimli state gecisleri
	        """

		#state transitions. list of tuples that dictate possible state transitions
		self.transitions=transitions		

		#current state
		self.state=state


	def get(self):
	        """
		Aktif statei gosterir

	        @rtype: str
	        @return: aktif statein ismi
	        """

		return self.state	


	def set(self,state):
	        """
		Aktif statei degistirir

	        @type  state: str
	        @param state: gecilmesi istenen statein ismi

	        @rtype: bool
	        @return: state degisikligi basarili ise True, aksi takdirde False
	        """

		#check if transition allowed
		if (self.state,state) not in self.transitions:
			return False

		#change state
		self.state=state
	
		return True
	
