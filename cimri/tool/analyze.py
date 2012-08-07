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


import os
import os.path
import sys

if __name__=="__main__":
	path=os.getcwd()
#	for i in range(2):
#		path=os.path.split(path)[0]
        if path not in sys.path:
                sys.path.append(path)

import argparse
import itertools
import codecs
from string import Template
from time import *
import json

from cimri.system.task import Task
from cimri.system.config import Config

class Printer():
        """
	Analiz sirasinda bulunan bilgileri bir stringe, dosyaya ya da konsola yazar
        """

	file=None
	buffer=None

	@classmethod
	def send(cls,msg):
	        """
		Yazilmasi istenen bir mesaji konsola, bir dosyaya ya da string bufferina yazar.

	        @type  msg: str 
	        @param msg: yazilmasi istenen mesaj
        	"""

		if Printer.file!=None:
			Printer.file.write(msg)
			Printer.file.write("\n")
	
		elif Printer.buffer!=None:
			Printer.buffer.append(msg)

		else:
			print msg


class Analyzer():
        """
	Sistem modulleri tarafindan islemden gecirilmis olan islerin analizi icin kullanilir.
        """

	def __init__(self,console=False):
	        """
	        @type  console: bool
	        @param console: eger True is analiz bilgileri konsola yazilir.
	        """

		self._console=console


	def list_tasks(self,path,threadsonly):
	        """
		Sistem tarafindan daha once yaratilmis ve islemden gecirilmis butun islemleri listeler

	        @type  path: str
	        @param path: sistem Tasklerinin filesystemda kayitli olduklari path

	        @type  threadsonly: bool
	        @param threadsonly: eger True ise sadece Task threadlerini listeler, aksi takdirde Tasklerin kapsadigi butun islemleri listeler.
	        """

		#get task list
		tasks=self._get_tasks(path)

		#show threads or tasks?
		if threadsonly:		
			#group tasks by threadid
			tasks=sorted(tasks,key=lambda a:a.threadid)		
			threads=[]
			for tid,group in itertools.groupby(tasks,key=lambda a:a.threadid):
				threads.append(sorted(list(group),key=lambda a:a.created))	

			#sort by date			
			threads=sorted(threads,key=lambda group:group[0].created)

			#print out
			if self._console:
				Printer.send("")
				Printer.send("created           \ttags                   \tthreadid                             \ttasks")
				Printer.send("----------------- \t---------------------- \t------------------------------------ \t-----------------------")
			for thread in threads:
				#get thread info
				created=self._format_timestamp(thread[0].created)
				id=thread[0].threadid
				ops=[task.op for task in thread]
				tags=""
				if hasattr(thread[0],"threadtags"):
					tags=thread[0].threadtags
				tags=tags+" "*(22-len(tags))
				
				#get status
				statuses=set([task.status for task in thread])
				if statuses.isdisjoint(set([Task.STATUS_NEW,Task.STATUS_STARTED])) is False:
					status=Task.STATUS_STARTED	
				elif Task.STATUS_ERROR in list(statuses):
					status=Task.STATUS_ERROR
				else:
					status=Task.STATUS_COMPLETE
			
				if self._console:
					Printer.send(Template("$created \t$tags \t$id \t$ops").substitute(created=created,tags=tags,id=id,ops=",".join(ops)) )
				else:
					Printer.send({"created":created,"tags":tags,"id":id,"status":status,"ops":",".join(ops)} ) 
				

			if self._console:		
				Printer.send("")

		#show tasks
		else:
			#sort tasks by date
			tasks=sorted(tasks,key=lambda a:a.created)		

			#print out
			Printer.send("")
			Printer.send("created           \tthread    \ttaskid                               \ttask")
			Printer.send("----------------- \t--------- \t------------------------------------ \t--------")
			for task in tasks:
				#get task info
				created=self._format_timestamp(task.created)
				id=task.id
				threadid=task.threadid[:4]+"xxxx"
				op=task.op
				Printer.send(Template("$created \t$tid \t$id \t$op").substitute(created=created,tid=threadid,id=id,op=op) )
			Printer.send("")



	def print_report(self,path, id=None, lasttask=False, lastthread=False, section=None, file=None):
	        """
		Belirli bir Task icin istenen raporlari cikartir.

	        @type  path: str
	        @param path: sistem Tasklerinin filesystemda kayitli olduklari path

	        @type  id: str
	        @param id: bir Taskin id ya da threadidsi. eger verilen id herhangi bir Taskin id'si ise o Taski raporlar. eger verilen id
			   birden fazla Taskin threadid'si ise o threadid'ye sahip butun Taskleri raporlar.

	        @type  lasttask: bool
	        @param lasttask: eger True ise sistemin islemden en son gecirdigi Taski raporlar

	        @type  lastthread: bool
	        @param lastthread: eger True ise sistemin islemden en son gecirdigi Task threadini raporlar

	        @type  section: str
	        @param section: eger None ise butun Task bolumlerini raporlar, eger None degil ise sadece belirtilen Task bolumunu raporlar

	        @type  file: str
	        @param file: yaratilan raporun yazilmasi istenilen dosyanin path ve ismi. eger None ise rapor dosyaya yazilmaz.
	        """

		#get task list
		tasks=self._get_tasks(path)

		#sort tasks by date
		tasks=sorted(tasks,key=lambda a:a.created)		

		#set id
		if lasttask:
			id=tasks[-1].id	
		elif lastthread:
			id=tasks[-1].threadid

		#filter tasks with matching task id or thread id
		tasks=[task for task in tasks if task.id==id or task.threadid==id]

		#write to file?
		if file!=None:
			Printer.file=codecs.open(file,"w","utf-8")	

		#print report for each task
		if self._console:
			Printer.send("")
		for task in tasks:
			if self._console:
				self._print_task_report(task,section)
				Printer.send("")
			else:
				Printer.send(self._compile_task_report(task,section))

		if self._console:
			Printer.send("")

		#close file
		if file!=None:
			Printer.file.close()


	def _compile_task_report(self,task,section=None):
	        """
		Belli bir Task'in raporlarini istenilen sekilde cikartip bir dictionary olarak sunar.

	        @type  task: L{cimri.system.task.Task}
	        @param task: raporlanmasi istenen Task

	        @type  section: str
	        @param section: belirtilen Task'in raporlanmasi istenilen bolumu. eger None ise Task'in butun blumleri raporlanir
	
	        @rtype: dict
	        @return: istenilen Task raporu
	        """

		#get summary info
		data={}
		for key in Task.sections["info"]:
			data[key]=getattr(task,key)

		#get other sections
		if section is not None:
			#load section
			task.load(section)

			#add section to report
			for key in Task.sections[section]:
				data[key]=getattr(task,key)
			

		return data


	def _print_task_report(self,task,section=None):
	        """
		Belli bir Task'in raporlarini istenilen sekilde yaratir

	        @type  task: L{cimri.system.task.Task}
	        @param task: raporlanmasi istenen Task

	        @type  section: str
	        @param section: belirtilen Task'in raporlanmasi istenilen bolumu. eger None ise Task'in butun blumleri raporlanir
	        """

		#print info
		self._print_line("task type",task.op)
		self._print_line("module",task.target)
		self._print_line("created",self._format_timestamp(task.created))
		self._print_line("duration(secs)",str(task.duration))
		self._print_line("task id",task.id)
		self._print_line("thread id",task.threadid)
		self._print_line("status",task.status)

		#print summary
		if task.op in ["crawl","get"]:
			first=task.meta["merchants.index"] if "merchants.index" in task.meta else 0
			last=first+task.meta["merchants.range"] if "merchants.range" in task.meta else ""
			self._print_line("summary","looking at active merchants: ["+str(first)+":"+str(last)+"]")

			first=task.meta["merchants.items.index"] if "merchants.items.index" in task.meta else 0
			last=first+task.meta["merchants.items.range"] if "merchants.items.range" in task.meta else ""
			self._print_line(value="for each merchant, looking at items: ["+str(first)+":"+str(last)+"]")

			self._print_line(value="number of merchant item urls found and verified: "+str(len(task.result)))

		elif task.op in ["scrap","scrap.benchmark"]:
			self._print_line(value="number of merchant item urls to scrap: "+str(len(task.data)))

			self._print_line(value="number of merchant items scrapped: "+str(len(task.result)))

		elif task.op in ["match","match.benchmark"]:
			self._print_line(value="number of merchant items to match: "+str(len(task.data)))

			self._print_line(value="number of items matched: "+str(len(task.result)))
			counts={}
			for result in task.result:
				counts[result["meta.action"]]=counts[result["meta.action"]]+1 if result["meta.action"] in counts else 1
			for k in counts:
				self._print_line(value="items for '"+k+"': "+str(counts[k]))

		elif task.op=="update":
			self._print_line(value="number of items to update: "+str(len(task.data)))
			counts={}
			for result in task.data:
				counts[result["meta.action"]]=counts[result["meta.action"]]+1 if result["meta.action"] in counts else 1
			for k in counts:
				self._print_line(value="items for '"+k+"': "+str(counts[k]))

			self._print_line(value="number of items updated: "+str(len(task.result)))
			counts={}
			for result in task.result:
				counts[result["meta.result"]]=counts[result["meta.result"]]+1 if result["meta.result"] in counts else 1
			for k in counts:
				self._print_line(value="'"+k+"' count: "+str(counts[k]))


		#if in summary mode, this all 	
		return

		#print input/output/meta/feedback
		if task.op=="crawl":
       	 	#       data:   none
       	 	#       meta:   crawl domain parameters
        	#       result: [{data:url,meta.merchantid: ,meta.xmlitem: }])
			Printer.send("\ntask results:")
			self._print_crawl_items(task.result)

		elif task.op in ["sample","get"]:
        	#       data:   none
        	#       result: [{data:url,meta.merchantid: ,meta.xmlitem: }])
			Printer.send("\ntask results:")
			self._print_crawl_items(task.result)

		elif task.op in ["scrap","scrap.benchmark"]:
        	#       data:   [{data:url, meta.merchantid: ,meta.xmlitem: }])
        	#       result: [{data:merchantitem}]	

			#print results
			Printer.send("\ntask results:")
			self._print_scrape_items(task.result)

		elif task.op in ["match","match.benchmark"]:
       	 	#       data:   [{data:merchantitem}]
        	#       result: [{data:merchantitem, meta.action:"update/insert/.."}]

			#print results
			Printer.send("\ntask results:")
			self._print_match_items(task.result)

		elif task.op=="update":
        	#       data:   [{data:merchantitem, meta.action:"update/insert/.."}]
        	#       result: [{data:merchantitem, meta.result:"success/fail", meta.error:}]
			pass

		#print log
		Printer.send("\ntask log:")

		for log in task.log:
			self._print_line(value=log)


	def _print_crawl_items(self,items):
	        """
		Bir crawl islemi ile ilgili verileri raporlar

	        @type  items: list
	        @param items: islem verileri
	        """

		#print out a list of urls
		data=[]
		for item in items:
			self._print_line(value="merchant id: "+str(item["meta.merchantid"]))
			self._print_line(value="item id:     "+item["meta.xmlitem"].merchantItemId)
			self._print_line(value="item url:    "+item["data"])
			Printer.send("")

			#serialize the xmlitem
			data.append(item["meta.xmlitem"].to_dict())

		#dump xmlitems
		Printer.send(json.dumps(data))
	

	def _print_scrape_items(self,items):
	        """
		Bir scrape islemi ile ilgili verileri raporlar

	        @type  items: list
	        @param items: islem verileri
	        """

		fields= [ "merchantItemId",
       	           	  "merchantItemUrl",
                  	  "brand",
                  	  "modelNameView",
                  	  "merchantItemTitle",
                  	  "pricePlusTax",
                  	  "mpnValue",
           	  	  "mpnType"]

		for item in items:
			#print merchant item fields
			for field in fields:
				label=field+" "*(24-len(field))
				self._print_line(value=label+" "+unicode(getattr(item["data"],field)))
			#print meta fields
			if "meta" in item:
				self._print_line(value="-----")
				for field in item["meta"]:
					label=field+" "*(24-len(field))
					self._print_line(value=label+" "+unicode(item["meta"][field]))
			Printer.send("")


	def _print_match_items(self,items):
	        """
		Bir match islemi ile ilgili verileri raporlar

	        @type  items: list
	        @param items: islem verileri
	        """

		fields= [ "merchantItemId",
        	          "merchantItemUrl",
                	  "brand",
                	  "modelNameView",
                	  "merchantItemTitle",
                 	  "pricePlusTax",
                 	  "mpnValue",
           	  	 "mpnType"]

		for item in items:
			#print merchant item fields
			for field in fields:
				label=field+" "*(24-len(field))
				self._print_line(value=label+" "+unicode(getattr(item["data"],field)))
		
			#print item id if matched
			if type(item["data"].item).__name__ == "dict" and "itemId" in item["data"].item:
				label="item.itemId"+" "*(24-len("item.itemId"))
				self._print_line(value=label+" "+item["data"].item["itemId"])
			
			#print action
			label="action"+" "*(24-len("action"))
			self._print_line(value=label+" "+item["meta.action"])

			Printer.send("")



	def _get_tasks(self,path):
	        """
		Sistemde kayitli butun Taskleri getirir
		
	        @type  path: str
	        @param path: Tasklerin sistemde kayitli oldugu path
	
	        @rtype: list (L{cimri.system.task.Task})
	        @return: istenilen Task'ler
	        """

		#get task list
		files=[ f for f in os.listdir(path) if os.path.isfile( os.path.join(path,f) ) and f.find("-info")>-1 ]

		#get tasks
		tasks=[]
		for file in files:
			tasks.append(Task.create_from_file(os.path.join(path,file)))

		return tasks


	def _format_timestamp(self,ts):
	        """
		Bir timestampi kullanici icin date/time bilgilerini gosterecek sekilde formatlar

	        @type  ts: long
	        @param ts: timestamp
	
	        @rtype: str
	        @return: formatlanmis tarih ve zaman bilgileri
	        """

		return strftime('%m.%d.%y %H:%M:%S',gmtime(ts))
	
	def _print_line(self,label=None,value=None):
	        """
		Belirli bilgileri konsola, bir dosyaya ya da rapor bufferina formatli bir sekilde ekler

	        @type  label: str
	        @param label: eklenmesi istenen bilginin labeli

	        @type  value: str
	        @param value: eklenmesi istenen bilgi 
	        """

		if label==None:
			label=" "*24
		label=label+" "*(24-len(label))
		Printer.send(label+value)



if __name__=="__main__":
	#handle runtime arguments
	parser=argparse.ArgumentParser(description='cimri matcher task result analyzer')
	parser.add_argument('-l','--ls',
			    action='store_true',
			    dest='list',
			    help='display a summary list of tasks found in archive')
	parser.add_argument('-o',
			    dest='file',
			    help='output file to print the report to')
	parser.add_argument('--threads-only',
			    action='store_true',
			    dest='threadsonly',
			    help='display a summary list of task threads rather than the tasks themselves')
	parser.add_argument('id',
			    nargs='?',
			    default=None,
			    help='print out a report for a task or task thread. a task id or thread id can be specified here')
	parser.add_argument('--last-task',
			    action='store_true',
			    dest='lasttask',
			    help='print out a report for the last task that was created')
	parser.add_argument('--last-thread',
			    action='store_true',
			    dest='lastthread',
			    help='print out a report for the last thread that was created')
	parser.add_argument('--summary',
			    action='store_true',
			    dest='summary',
			    help='when printing out reports, display only summary information about tasks')
	parser.add_argument('--path',
			    dest='path',
			    default=Config.getconfig("SYS").get("task_store_path"),
			    help='provide a path different than the default system task archive path')

	#compile arguments
	args=parser.parse_args()

	#dispatch
	analyzer=Analyzer(console=True)
	if args.list==True:
		analyzer.list_tasks(args.path,args.threadsonly)

	elif args.id!=None:
		analyzer.print_report(args.path, id=args.id, section=("info" if args.summary is True else None), file=args.file)

	elif args.lasttask==True:
		analyzer.print_report(args.path, lasttask=True, section=("info" if args.summary is True else None), file=args.file)

	elif args.lastthread==True:
		analyzer.print_report(args.path, lastthread=True, section=("info" if args.summary is True else None), file=args.file)
