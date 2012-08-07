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


import time
import subprocess
import os.path
import psutil

from twisted.internet import reactor, defer
from twisted.internet.threads import deferToThread

from cimri.system.task import Task
from cimri.system.cache import Cache
from cimri.module.module import Module
from cimri.system.config import Config
from cimri.tool.analyze import *
from cimri.api.cimriservice.merchants import MerchantsAPI
from cimri.api.cimriservice.data.merchant import MerchantInfo
from cimri.api.matcherdb.catalogue import CatalogueDB


class Controller(Module):
	"""
	Sistem icindeki modulleri calistiran, statulerini monitor eden ve islemleri modullere dagitan kontrol moduludur.
	"""

	def __init__(self):
		super(Controller,self).__init__()

		#configured modules
		self.modules=[]

		#monitors - the controller uses a different set of monitors than the generic module monitors
		self.monitors=[(self._module_monitor,5),
			       (self._resource_monitor,10),
			       (self._dispatch_monitor,1)]

                #supported operations
                self.ops={"controller.schedule"     :None}

		#task threads
		self.threads=[]

		#thread history
		self.history=[]

		#resource monitoring
		self.cpu=[]
		self.mem=0
		
		#start modules
		self._system_start()
	

	def shutdown(self):
                """
		Modulu durdurur.
                """

		#shutdown all modules first
		self._system_stop()

		#done
		super(Controller,self).shutdown()		



	#-controller xmlrpc interface----------------------------------------------------------------------	

	def xmlrpc_getmodulestatus(self,id):
                """
		Kullanilmiyor
		"""

		return self.getmodulestatus(id)

	def xmlrpc_pausethread(self,id):
                """
		Kullanilmiyor
                """

		return self.pausethread(id)

	def xmlrpc_cancelthread(self,id):
                """
		Kullanilmiyor
                """

		return self.cancelthread(id)

	def xmlrpc_resumethread(self,id):
                """
		Kullanilmiyor.
                """

		return self.resumethread(id)
	
	def xmlrpc_getthreads(self):
                """
		XML-RPC uzerinden sistemde islem halinde olan ya da isleme alinmayi bekleyen threadler hakkinda bilgi alir

                @rtype: list
                @return: thread listesi
                """

		#get threads
		threads=self.getthreads()

		return threads

	def xmlrpc_getschedule(self):
                """
		Kullanilmiyor
                """

		#get schedule
		schedule=self.getschedule()

		#serialize schedule
		data=[]

		return data

	def xmlrpc_getthreadinfo(self,id):
                """
		XML-RPC uzerinden sistemde kayitli olan bir threadin raporunu alir

                @type id:str
                @param id:thread IDsi

                @rtype: list
                @return: thread raporu
                """

		#get log
		log=self.getthreadinfo(id)

		return log

	def xmlrpc_gettaskresults(self,id):
                """
		XML-RPC uzerinden sistemde kayitli olan bir taskin sonuclarini alir

                @type id:str
                @param id:task IDsi

                @rtype: list
                @return: task sonuclari
                """

		#get log
		log=self.gettaskresults(id)

		return log

	def xmlrpc_gettasklog(self,id):
                """
		XML-RPC uzerinden sistemde kayitli olan bir taskin loglarini alir

                @type id:str
                @param id:task IDsi

                @rtype: list
                @return: task loglari
                """

		#get log
		log=self.gettasklog(id)

		return log

	def xmlrpc_gettaskerrors(self,id):
                """
		XML-RPC uzerinden sistemde kayitli olan bir taskin hata loglarini alir

                @type id:str
                @param id:task IDsi

                @rtype: list
                @return: task hata loglari
                """

		#get log
		log=self.gettaskerrors(id)

		return log

	def xmlrpc_getthreadlogs(self):
                """
		XML-RPC uzerinden sistemde kayitli olan bir threadlerin listesini alir

                @type id:str
                @param id:thread IDsi

                @rtype: list
                @return: thread listesi
                """

		#get logs
		logs=self.getthreadlogs()

		return logs

	def xmlrpc_getcachestatus(self):
                """
		XML-RPC uzerinden sistem cachei hakkinda bilgiler alir

                @rtype: dict
                @return: cache bolumlerini ve statulerini belirten bilgiler
                """

		return self.getcachestatus()

	def xmlrpc_clearcache(self,section):
                """
		XML-RPC uzerinden sistem cacheindeki bir bolumu temizler

                @type  section:str
                @param section:cache bolumu id ya da ismi

                @rtype: bool
                @return: operasyon sonucu
                """

		self.clearcache(section)
		return True

	def xmlrpc_getmerchants(self):
                """
		XML-RPC uzerinden Cimri Service'de bulunan butun aktif merchantlarin listesini alir

                @rtype: list
                @return: sistemde bulunan aktif merchantlarin id ve isimlerini iceren bir liste
                """

		api=MerchantsAPI()
		merchants=api.get_merchants(status=MerchantInfo.STATUS_ACTIVE)
		merchants.sort(lambda a,b:a.merchantName>b.merchantName)
		return [{"id":merchant.merchantId, "name":merchant.merchantName} for merchant in merchants]

	def xmlrpc_getcatalogueitems(self,title,brand,mpn):
                """
		XML-RPC uzerinden cimri katalogunda arama yapar ve kriterler uygun katalog itemlarini alir

                @type  title:str
                @param title:aranan item'in titlei

                @type  brand:str
                @param brand:aranan item'in brandi

                @type  mpn:str
                @param mpn:aranan item'in MPN degeri

                @rtype: list
                @return: bulunan itemlarin listesi
                """

		db=CatalogueDB()
		items=db.suggestions_by_title_and_brand(title,brand,mpn)
		return [{"id":item["id"],
			 "score":item["score"],
			 "brand":item["brand"],
			 "keywords":item["keywords"]} for item in items]


	#----------------------------------------------------------------------controller xmlrpc interface-
	
	def getstatus(self):
                """
		Sunucu hakkinda, sistemde calisan modullerin durumu hakkinda ve aktif islemler hakkinda bilgi alir
		
                @rtype: dict
                @return: sistem bilgilerini iceren dictionary
                """

		#get controller tasks
		tasks=[]
                for thread in self.threads:
			tasks.append(self._getthreadstatus(thread))

		#get status
       		status={"id":self.id,
                        "module":self.__class__.__name__,
                        "host":self.host,
                        "port":self.port,
                        "status":self.state.get(),
                        "tasks":tasks}

		#add controller specific info
		status["cpu"]=self.cpu
		status["mem"]=self.mem
		status["modules"]=[]

		#get module statuses
		for module in self.modules:
			status["modules"].append({"id":module.id,
					  	  "module":module.module.split('.')[-1],
					  	  "host":module.host,
					  	  "port":module.port,
					  	  "status":module.status,
						  "tasks":module.tasks
					  	})

		return status


	def getmodulestatus(self,id):
		"""
		Kullanilmiyor
                """

		return {}


	def stop(self):
                """
		Modulu durdurur

                @return: operasyon sonucu
                """

		#change state
		res=self.state.set(Module.STATE_STOPPING)
		if res is False:
			return res
		self.logger.info("controller stopping...")		


		#maybe we need stopping/starting states here


		#stop all modules

		#change state
		res=self.state.set(Module.STATE_STOPPED)
		if res is False:
			return res
		self.logger.info("controller stopping...")		

		#done
		return True


	def start(self):
                """
		Modulu calistirir

                @return: operasyon sonucu
                """

		#change state
		res=self.state.set(Module.STATE_STARTING)
		if res is False:
			return res
		self.logger.info("controller starting...")		

		#start all modules

		#change state
		res=self.state.set(Module.STATE_RUNNING)
		if res is False:
			return res
		self.logger.info("controller started...")		

		#done
		return True


	def schedule(self,tasks):
                """
		Bir task listesini islem sirasina koyar. Islem sirasina konulmasi istenen Task listesindeki ilk Task'in 
		"cimri.module.automation.Controller" modulu icin bir "controller.schedule" islemi olmasi gerekir.

             	@type   tasks: list
               	@param  tasks: Task listesi (L{cimri.system.task.Task} objectlerinin dictionary formatli hallerini iceren bir liste) 
	
		@rtype: bool
		@return: operasyon sonucu		
                """

		#check the controller task
		if tasks[0].op!="controller.schedule":
			return False
		if len(tasks)<2:
			return False		

		#generate threadid
		tasks[0].threadid=tasks[0].id
		
		#establish task chain (thread)
		for task in tasks[1:]:
			task.threadid=tasks[0].threadid
			task.threadtags=tasks[0].threadtags
			task.status=Task.STATUS_PENDING
			task.save()

		#schedule the first task
		tasks[1].status=Task.STATUS_SCHEDULED

                #add thread
                self.threads.append([{"task":task,"module":None} for task in tasks])

		return [task.id for task in tasks]



	def pausethread(self,id):
                """
		Kullanilmiyor
		"""

		return True


	def cancelthread(self,id):
		"""
		Kullanilmiyor
                """

		return True

	def resumethread(self,id):
                """
		Kullanilmiyor
                """

		return True

	def getthreads(self):
                """
		Sistem tarafindan tamamlanmis en son 3 thread ile islem gormeyi bekleyen ve aktif olarak islemde olan threadlerin
		listesini alir.

                @rtype: list
                @return: thread listesi
                """

		tasks=[]

		#get last 3 history

		for thread in self.history[-3:]:
			tasks.append(self._getthreadstatus(thread))
			
		#get current and scheduled threads
                for thread in self.threads:
			tasks.append(self._getthreadstatus(thread))

		return tasks

			
	def getschedule(self):
                """
		Kullanilmiyor
                """

		return []

	def getthreadlogs(self):
                """
		Sistemde kayitli olan butun threadlerin listesini alir

                @rtype: list
                @return: thread listesi
                """

		#get thread output log
		Printer.buffer=[]
		analyzer=Analyzer(console=False)
		analyzer.list_tasks(Config.getconfig("SYS").get("task_store_path"),True)

		return Printer.buffer


	def getthreadinfo(self,id):
                """
		Sistemde kayidi olan belli bir islem threadinin bilgilerini alir

                @type  id: str
                @param id: thread IDsi

                @rtype: list
                @return: thread bilgileri
                """

		#get thread info
		Printer.buffer=[]
		analyzer=Analyzer(console=False)
		analyzer.print_report(Config.getconfig("SYS").get("task_store_path"),id)

		return Printer.buffer


	def gettaskresults(self,id):
                """
		Sistemde kayidi olan belli bir taskin sonuclarini alir

                @type  id: str
                @param id: task IDsi

                @rtype: list
                @return: task sonuclari
                """

		#get thread results
		Printer.buffer=[]
		analyzer=Analyzer(console=False)
		analyzer.print_report(Config.getconfig("SYS").get("task_store_path"),id,section="result")

		return Printer.buffer


	def gettasklog(self,id):
                """
		Sistemde kayidi olan belli bir taskin loglarini alir

                @type  id: str
                @param id: task IDsi

                @rtype: list
                @return: task loglari
                """

		#get thread output log
		Printer.buffer=[]
		analyzer=Analyzer(console=False)
		analyzer.print_report(Config.getconfig("SYS").get("task_store_path"),id,section="log")

		return Printer.buffer


	def gettaskerrors(self,id):
                """
		Sistemde kayidi olan belli bir taskin hata loglarini alir

                @type  id: str
                @param id: task IDsi

                @rtype: list
                @return: task hata loglari
                """

		#get task error list
		Printer.buffer=[]
		analyzer=Analyzer(console=False)
		analyzer.print_report(Config.getconfig("SYS").get("task_store_path"),id,section="error")

		return Printer.buffer


	def getcachestatus(self):
                """
		Sistem cachei hakkinda bilgiler alir

                @rtype: dict
                @return: cache bolumlerini ve statulerini belirten bilgiler
                """

		return Cache.getstatus()

	def clearcache(self,section):
                """
		Sistem cacheindeki bir bolumu temizler

                @type  section:str
                @param section:cache bolumu id ya da ismi
                """

		Cache(section).clear()	


	def _getthreadstatus(self,thread):
                """
		Belli bir thread hakkinda statu bilgileri alir

                @type  thread: list
                @param thread: thread (task listesi)

                @rtype: dict
                @return: thread status bilgileri
                """

		#get the controller task
		task=thread[0]["task"]

		#get overall progress
		progress=0
		err=False
		for task in thread[1:]:
			#complete?
			if task["task"].status == Task.STATUS_ERROR:
				err=True
				progress=progress+100
			elif task["task"].status == Task.STATUS_COMPLETE:
				progress=progress+100
			elif task["module"] is not None:
				#find task in module task list
				for t in task["module"].tasks:
					if task["task"].id==t["id"]:
						progress=progress+t["progress"]
		progress=int(float(progress)/len(thread[1:]))
						
		#get the consolidated status
		status=Task.STATUS_PENDING
		if err:
			status=Task.STATUS_ERROR
		elif progress==100:
			status=Task.STATUS_COMPLETE
		elif progress>0:
			status=Task.STATUS_STARTED			

		#construct task info
              	return {"id":task["task"].id,
                        "threadid":task["task"].threadid,
                        "threadtags":task["task"].threadtags,
                        "status":status,
                        "progress":progress}



	def _system_start(self):
                """
		Sistemi calistirir. Sistem konfigurasyonunda bulunan modulleri kendi processleri ile yaratir.
                """

		#base port
		port=int(Config.getconfig("MOD_AUTOMATION").get("base_port"))

		#get configured modules
		config=Config.getconfig("MOD_AUTOMATION")
		for group in ["crawlers","scrapers","matchers","updaters"]:
			list=config.get(group).split(",")
			for name in list:
				name=name.strip()

				#get count
				count=1
				if name.endswith(")"):
					tokens=name.split("(")
					if len(tokens)>1:
						name=tokens[0]
						count=int(tokens[1][:-1])				

				#create proxies
				for index in range(count):
					proxy=ModuleProxy(name.strip(),"localhost",port)
					self.modules.append(proxy)
					port=port+1				

		#stop all rogue modules (that might not have been shutdown)

		#start all modules
		for module in self.modules:
			module.spawn()


	def _system_stop(self):
                """
		Sistemde calisir durumdaki butun modullere "shutdown" komutunu yollar
                """

		#stop all modules
		for module in self.modules:
			module.call("shutdown")


	def _module_monitor(self):
                """
		Periyodik olarak sistemdeki calisir durumda olan modullerin durumunu kontrol eden fonksiyon.
                """

		try:
			#monitor only when module is running
			if self.state.get()==Module.STATE_RUNNING:
				#get status on each module
				for module in self.modules:
					#get status
					deferred=module.call("getstatus")

					#update status on the proxy
					def updatestatus(data,module):
						try:	
							#update task info
							module.id=data["id"]
							module.status=data["status"]
							module.tasks=data["tasks"]
						except Exception as e:
							pass
					deferred.addCallback(updatestatus,module=module)
				
	
		except Exception as e:
			pass


	def _dispatch_monitor(self):
                """
		Periodik olarak yeni schedule edilen islemleri modullere dagitan, modullerin tamamladigi isleri islem akisina gore
		bir sonraki module aktaran, genel olarak islem akisini yoneten fonksiyon.
                """

		#are there any scheduled tasks?
		for thread in self.threads:
			for task in thread[1:]:
				#is task scheduled?
				if task["task"].status!=Task.STATUS_SCHEDULED:
					continue

				#are there any available modules for processing?
				for module in self.modules:
					#check if module type matches
					if module.module!=task["task"].target:
						continue

					#check if module running
					if module.status!=Module.STATE_RUNNING:
						continue

					#check if module is available
					if len(module.tasks)>0 or module.lock is True:
						continue

					#mark as locked so another task is not dispatched while the status updates
					module.lock=True

					#schedule task
					deferred=module.call("schedule",[task["task"].pack("info")])
					def updatestatus(data,task,module):
						#mark task as dispatched
						task["task"].status=Task.STATUS_DISPATCHED
						task["module"]=module
						module.lock=False
					def revertstatus(err,task,module):
						module.lock=False
					deferred.addCallback(updatestatus,task=task,module=module)
					deferred.addErrback(revertstatus,task=task,module=module)

					break

		#are there any tasks that completed?
		for module in self.modules:
			#is there a task?
			if len(module.tasks)==0:
				continue

			#is task complete?
			if module.tasks[0]["status"] not in [Task.STATUS_COMPLETE,Task.STATUS_ERROR]:
				continue

			#is proxy being processed?
			if module.lock is True:
				continue

			#lock proxy
			module.lock=True

			#get updated task from module
			deferred=module.call("gettask")
			def handledata(data,module):
				#unpack task
				task=Task()
				task.unpack(data)

				def handleok(data,module,task):
					#find thread
					thread=None
					for t in self.threads:
						if t[0]["task"].threadid==task.threadid:
							thread=t
							break

					#check thread
					if thread is None:
						return #log error (thread not found!)					

					#find task
					index=None
					for i in range(len(thread)):
						if thread[i]["task"].id==task.id:
							index=i
							break

					#check task
					if index is None:
						return #log error (task not found!)

					#update task
					thread[index]["task"]=task
					thread[index]["module"]=None

					#is there a next task in the thread?
					if index==len(thread)-1:
						#delete thread, we're done
						self.threads.remove(thread)

						#append thread to history
						self.history.append(thread)
						if len(self.history)>10:
							self.history=self.history[-10:]

					else:						
						#assign result to next task in thread
						thread[index]["task"].load()
						thread[index+1]["task"].data=thread[index]["task"].result
						thread[index+1]["task"].save()
			
						#free the memory we just used up
						thread[index]["task"].unload()
						thread[index+1]["task"].unload()

						#mark next task on thread as scheduled
						thread[index+1]["task"].status=Task.STATUS_SCHEDULED

					#done
					module.lock=False
					module.tasks=module.tasks[1:]

				def handleerr(err,module):
					#flush call failed. will try again in next monitor cycle
					module.lock=False

				deferred=module.call("flush")
				deferred.addCallback(handleok,module=module,task=task)
				deferred.addErrback(handleerr,module=module)

			def handleerr(err,module):
				module.lock=False
			deferred.addCallback(handledata,module=module)
			deferred.addErrback(handleerr,module=module)


	def _resource_monitor(self):
                """
		Periyodik olarak sistem bilgilerini (cpu, memory, ...) kontrol eden fonksiyon.
                """

		def logcpu(data):
			self.cpu=[int(usage) for usage in data]
		deferred=deferToThread(psutil.cpu_percent,interval=1,percpu=True)
		deferred.addCallback(logcpu)
		self.mem=int(psutil.phymem_usage().percent)


class ModuleProxy():
	"""
	Sistemde Controller disinda calistirilan modullerin durumunu takip etmek ve bu moduller ile komunikasyonu saglamak icin
	gereken fonksiyonlari saglayan class.
	"""

	def __init__(self,module,host,port):
                """
                @type module: str
                @param module: modulun ismi/turu

                @type host: str
                @param host: modulun XML-RPC cagrilarini dinledigi ip ya da host name

                @type port: int
                @param port: modulun XML-RPC cagrilarini dinledigi port
                """

		self.id=None
		self.module=module
		self.host=host
		self.port=port
		self.status=Module.STATE_STARTING	#default
		self.lock=False
		self.tasks=[]
		self.last_ping=0
		self.pid=0


	def call(self,func,*args):
                """
		Module asynchronous olarak XML-RPC cagrisi yapar

                @type  func: str
                @param func: XML-RPC ile cagrilmasi istenen fonksiyonun ismi

                @type  args: list
                @param args: XML-RPC cagrisi icin ekstra argumanlar

                @rtype: L{twisted.internet.defer.Deferred}
                @return: XML-RPC sonuclarini asynchronous olarak alian Deferred objecti
                """

		#make xml rpc call
		deferred=Module._callremote(self.host,self.port,func,*args)
		#deferred.addCallbacks(self._call_success,self._call_error)
		
		return deferred


	def spawn(self):	
                """
		Modul processini baslatir
                """

		try:
			#get module package (remove the class name)
			pkg=self.module.split('.')[:-1]
		
			#get package path
			path=os.path.join(*pkg)

			#spawn process
			process=subprocess.Popen(["python",path+".py","--host",self.host,"--port",str(self.port)])
			self.pid=process.pid

		except Exception as e:
			pass
	
	def _call_success(self,data):
                """
		Kullanlmiyor
                """

		#update last contact time
		self.last_ping=time.time()

		return data


	def _call_error(self,error):
                """
		Kullanilmiyor
                """

		return error


#bootstrap
if __name__=="__main__":
	#run module
	mod=Controller()
	args=mod._parse_argv()
	mod._run(**args)
