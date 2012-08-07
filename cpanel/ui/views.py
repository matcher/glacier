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


import os.path
import json

from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import get_template
from django.template import Context

from cpanel.config.config import Config
from cpanel.app.protocol import *
from cpanel.app.logger import Logger
from cpanel.app.view import *
from cpanel.auth.models import User
from cpanel.app.models import *
from cpanel.api.controller import ControllerAPI
from cpanel.api.analytics import AnalyticsAPI
from cpanel.api.scraper import ScraperAPI

from cimri.system.task import Task
from cimri.system.data import DataObject
from cimri.api.cimriservice.data.merchantitem import MerchantItem

from datetime import datetime

def default(request):
        #template context
	context=_get_context(request,section="common",content="content_login")

	#render
        return HttpResponse( get_template('template_public.html').render(Context(context)) )


@requires_session(["admin"])
def users(request):
	#get users
	users=User.list()

        #template context
	context=_get_context(request,section="admin",content="content_users",users=users)

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )


@requires_session(["admin"])
def system_control(request):
	#get task tempaltes
	templates=TaskTemplate.list()

	#order tempaltes
	templates=[template for template in templates]
	templates.sort(lambda a,b:1 if a.label > b.label else (-1 if b.label > a.label else 0) )

        #template context
	context=_get_context(request,section="admin",content="content_system_control",templates=templates)

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )

@requires_session(["admin"])
def system_cache(request):
	#get controller api
	api=ControllerAPI(request)
	status=api.getcachestatus()

	#rearrange
	def func(a,b):
		if a["id"]=="__global__":
			return -1		
		elif b["id"]=="__global__":
			return 1
		else:
			return a>b
	status.sort(func)

	#add labels
	for section in status:
		section["label"]="genel" if section["id"]=="__global__" else section["id"]

        #template context
	context=_get_context(request,section="admin",content="content_system_cache",status=status)

	#render
        return HttpResponse( get_template('template_content.html').render(Context(context)) )


@requires_session(["admin"])
def system_monitor(request):	
        #template context
	context=_get_context(request,section="admin",content="content_system_monitor")

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )

@requires_session(["admin"])
def system_monitor_module(request,id):	
        #template context
	context=_get_context(request,section="admin",content="content_system_monitor_module",id=id)

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )


@api_requires_session(["admin"])
@api_call
def system_status(request):
	#get controller api
	api=ControllerAPI(request)
	status=api.getstatus()
	
	#return authentication
	return HttpResponse( AIResponse(data=status).serialize() )


@api_requires_session(["admin"])
@api_call
def system_threads(request):
	#get controller api
	api=ControllerAPI(request)
	status=api.getthreads()
	
	#return authentication
	return HttpResponse( AIResponse(data=status).serialize() )


@api_requires_session(["admin"])
def scraper_reports(request):
	#get merchants
	api=ControllerAPI(request)
	merchants=api.getmerchants()
	if merchants is None:	
		merchants=[]

	#get scraper status for each merchant
	api=ScraperAPI(request)
	statuses=api.getscraperstatus()

	#create status for merchants that do not have a stored status
	ids=[str(status.merchantid) for status in statuses]
	for merchant in merchants:
		if str(merchant["id"]) not in ids:
			s=api.createmerchant(merchant["id"])

	#convert merchant ids to ints
	for merchant in merchants:
		merchant["id"]=int(merchant["id"])

	#get statuses again
	statuses=api.getscraperstatus()

        #template context
	context=_get_context(request,section="admin",content="content_scraper_reports",merchants=merchants,statuses=statuses)

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )


@api_requires_session(["admin"])
@api_call
def scraper_control(request):
	#get parameters
	merchantid=int(request.REQUEST["merchant"])
	activate=int(request.REQUEST["activate"])==1

	#update merchant
	api=ScraperAPI(request)
	api.updatemerchant(merchantid,activate)

	return HttpResponse( AIResponse().serialize() )



@requires_session(["admin"])
def task_create(request):
	#get descriptors and merchants
	api=ControllerAPI(request)
	descriptors=api.getmoduledescriptors()
	merchants=api.getmerchants()

	#template context
	context=_get_context(request,content="content_task_addedit",descriptors=json.dumps(descriptors),merchants=json.dumps(merchants))

	#render
        return HttpResponse( get_template('template_content.html').render(Context(context)) )


@requires_session(["admin"])
def task_created(request):	
        #template context
	context=_get_context(request,content="content_task_created")

	#render
        return HttpResponse( get_template('template_content.html').render(Context(context)) )


@api_requires_session(["admin"])
@api_call
def task_schedule(request):
	#get parameters
	tags=request.REQUEST["label"] if "label" in request.REQUEST else ""
	tasks=json.loads(request.REQUEST["tasks"]) if "tasks" in request.REQUEST else []

	#validate
	if len(tasks)==0:
		return HttpResponse( AIResponse(error=AIError(AIError.SYSTEM)).serialize() )

	#create task thread
	thread=[]
	task=Task()
	task.target="cimri.module.automation.controller.Controller"
	task.op="controller.schedule"
	thread.append(task)
	for info in tasks:
	        task=Task()
		task.target=info["target"]
		task.op=info["op"]
		for key in info["meta"]:
			if info["meta"][key]!="":
			        task.meta[key]=info["meta"][key]             
		thread.append(task)

	#add label
	thread[0].threadtags=tags if tags!="" else ", ".join([task.op for task in thread[1:]])

	#schedule
	api=ControllerAPI(request)
	res=api.schedule(thread)

	return HttpResponse( AIResponse().serialize() )


@api_call
def handle_schedule(request):
	#get all templates
	templates=TaskTemplate.list()

	#get day-of-year, hour and minute
	now=datetime.now()

	#check for schedule
	for template in templates:
		#does tempalte have a schedule?
		if template.schedule.strip()=="":
			continue

		#get schedule
		times=template.schedule.split(" ")
		runtask=False
		for t in times:
			try:
				#get schedule time hour and minute
				tokens=t.strip().split(":")
				hour=int(tokens[0])
				minute=int(tokens[1])

				#is it time to schedule this?
				if now.hour!=hour or now.minute!=minute:
					continue

				#get year-month-day
				ts=str(now.year)+"."+str(now.month)+"."+str(now.day)				

				#was this schedule already run today?
				if t.strip() in template.schedule_log and template.schedule_log[t.strip()]==ts:
					continue

				#run rask
				runtask=True

				#update schedule log
				template.schedule_log[t.strip()]=ts
				template.save()

				#done
				break

			except:
				continue
		
		#run task?
		if runtask is False:
			continue

		#create task thread
		thread=[]
		task=Task()
		task.target="cimri.module.automation.controller.Controller"
		task.op="controller.schedule"
		thread.append(task)
		for info in template.tasks:
		        task=Task()
			task.target=info["target"]
			task.op=info["op"]

			for key in info["meta"]:
				if info["meta"][key]!="":
				        task.meta[key.replace("-",".")]=info["meta"][key]  
			thread.append(task)

		#add label
#		thread[0].threadtags=", ".join([task.op for task in thread[1:]])+" (auto)"
		thread[0].threadtags=template.label+" (auto)"

		#schedule
		api=ControllerAPI(request)
		res=api.schedule(thread)
		

	return HttpResponse( AIResponse().serialize() )



@requires_session()
def test_created(request):	
        #template context
	context=_get_context(request,section="common",content="content_test_created")

	#render
        return HttpResponse( get_template('template_content.html').render(Context(context)) )


@requires_session()
def test_schedule(request,id):
	#get test
	test=TestCase.get(id=id)

	#create task chain
	tasks=[]
	task=Task()
	task.target="cimri.module.automation.controller.Controller"
	task.op="controller.schedule"
	task.threadtags="test: "+test.label
	tasks.append(task)

	#create test task
	task=Task()
	task.target=test.module
	task.op=test.op
	task.meta['test']=True
	task.meta['test.uuid']=test.uuid
	task.meta['workers']=8

	#set task data
	task.data=[]
	for data in test.data:
		taskdata={}
		
		if task.op=="scrap":
			taskdata["data"]=data["data"]
			taskdata["meta.merchantid"]=data["meta.merchantid"]
			if "meta.xmlitem" in data:
				taskdata["meta.xmlitem"]={"__class__":"MerchantItem", "dump":MerchantItem(data["meta.xmlitem"]).to_dict()}
			if "meta.refitem" in data:
				taskdata["meta.refitem"]={"__class__":"MerchantItem", "dump":MerchantItem(data["meta.refitem"]).to_dict()}
			else:
				taskdata["meta.refitem"]=None

		elif task.op=="match":		
			taskdata["data"]={"__class__":"MerchantItem", "dump":MerchantItem(data["meta.xmlitem"]).to_dict()}
			if "meta.refitem" in data:
				taskdata["meta.refitem"]={"__class__":"MerchantItem", "dump":MerchantItem(data["meta.refitem"]).to_dict()}
			else:
				taskdata["meta.refitem"]=None

		task.data.append(taskdata)

	tasks.append(task)
	
	
	#schedule
	api=ControllerAPI(request)
	res=api.schedule(tasks)
		        
	#template context
	context=_get_context(request,section="common",content="content_test_scheduled")

	#render
        return HttpResponse( get_template('template_content.html').render(Context(context)) )



@requires_session()
def training_created(request):	
        #template context
	context=_get_context(request,section="common",content="content_training_created")

	#render
        return HttpResponse( get_template('template_content.html').render(Context(context)) )


@requires_session()
def training_schedule(request,id):
	#get training
	case=MLCase.get(id=id)

	#create task chain
	tasks=[]
	task=Task()
	task.target="cimri.module.automation.controller.Controller"
	task.op="controller.schedule"
	task.threadtags="egitim: "+case.label
	tasks.append(task)

	#create ML task
	task=Task()
	task.target=case.module
	task.op=case.op
	task.meta['train']=True
	task.meta['train.uuid']=case.uuid

	#set task data
	task.data=[]
	for data in case.data:
		taskdata={}
		
		if task.op=="scrap":
			taskdata["data"]=data["data"]
			taskdata["meta.merchantid"]=data["meta.merchantid"]
			if "meta.xmlitem" in data:
				taskdata["meta.xmlitem"]={"__class__":"MerchantItem", "dump":MerchantItem(data["meta.xmlitem"]).to_dict()}
			if "meta.refitem" in data:
				taskdata["meta.refitem"]={"__class__":"MerchantItem", "dump":MerchantItem(data["meta.refitem"]).to_dict()}
			else:
				taskdata["meta.refitem"]=None

		elif task.op=="match":		
			taskdata["data"]={"__class__":"MerchantItem", "dump":MerchantItem(data["meta.xmlitem"]).to_dict()}
			if "meta.refitem" in data:
				taskdata["meta.refitem"]={"__class__":"MerchantItem", "dump":MerchantItem(data["meta.refitem"]).to_dict()}
			else:
				taskdata["meta.refitem"]=None

		task.data.append(taskdata)

	tasks.append(task)
	
	
	#schedule
	api=ControllerAPI(request)
	res=api.schedule(tasks)
		        
	#template context
	context=_get_context(request,section="common",content="content_training_scheduled")

	#render
        return HttpResponse( get_template('template_content.html').render(Context(context)) )


@api_requires_session(["admin"])
@api_call
def template_create(request):
	#get parameters
	tags=request.REQUEST["label"] if "label" in request.REQUEST else ""
	tasks=json.loads(request.REQUEST["tasks"]) if "tasks" in request.REQUEST else []

	#validate
	if len(tasks)==0:
		return HttpResponse( AIResponse(error=AIError(AIError.SYSTEM)).serialize() )

	#create template
	template=TaskTemplate()
	template.owner=request.session["user"].id
	template.label=tags if tags!="" else ", ".join([task.op for task in thread[1:]])
	template.settasks(tasks)
	template.create()
	
	#return authentication
	return HttpResponse( AIResponse().serialize() )



@requires_session(["admin"])
def template_created(request):	
        #template context
	context=_get_context(request,content="content_template_created")

	#render
        return HttpResponse( get_template('template_content.html').render(Context(context)) )


@requires_session(["admin"])
def template_updated(request):	
        #template context
	context=_get_context(request,content="content_template_updated")

	#render
        return HttpResponse( get_template('template_content.html').render(Context(context)) )


@requires_session(["admin"])
def create_task_from_template(request,id):
	#get template
	template=TaskTemplate.get(id=id)

	#get descriptors and merchants
	api=ControllerAPI(request)
	descriptors=api.getmoduledescriptors()
	merchants=api.getmerchants()

	#template context
	context=_get_context(request,content="content_task_addedit",descriptors=json.dumps(descriptors),merchants=json.dumps(merchants),template=template,tasks=json.dumps(template.gettasks()))

	#render
        return HttpResponse( get_template('template_content.html').render(Context(context)) )


@requires_session(["admin"])
def update_template(request,id):
	#get template
	template=TaskTemplate.get(id=id)

	#get action
	action=request.REQUEST["a"]
	if action=="delete":
		template.delete()

	elif action=="update":
		#get parameters
		tags=request.REQUEST["label"] if "label" in request.REQUEST else ""
		tasks=json.loads(request.REQUEST["tasks"]) if "tasks" in request.REQUEST else []

		#validate
		if len(tasks)==0:
			return HttpResponse( AIResponse(error=AIError(AIError.SYSTEM)).serialize() )

		#update template
		template.label=tags if tags!="" else ", ".join([task.op for task in thread[1:]])
		template.settasks(tasks)
		template.save()

	return HttpResponse( AIResponse().serialize() )


@requires_session(["admin"])
def update_template_schedule(request,id):
	#get template
	template=TaskTemplate.get(id=id)

	#get schedule
	schedule=request.REQUEST["schedule"]

	#update schedule
	template.schedule=schedule
	template.save()

	return HttpResponse( AIResponse().serialize() )



@requires_session(["admin"])
def system_log(request):
        #template context
	context=_get_context(request,section="admin",content="content_system_log")

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )


@requires_session(["admin"])
def system_reports(request):
	#get controller api
	api=ControllerAPI(request)
	reports=api.getthreadlogs()

	#sort by date
	reports.reverse()

        #template context
	context=_get_context(request,section="admin",content="content_system_reports",reports=reports)

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )


@requires_session(["admin"])
def system_report(request,id):
	#get controller api
	api=ControllerAPI(request)
	report=api.getthreadinfo(id)

        #template context
	context=_get_context(request,section="admin",content="content_system_report",report=report)

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )


@requires_session(["admin"])
def system_report_log(request,id):
	#get controller api
	api=ControllerAPI(request)
	report=api.gettasklog(id)

        #template context
	context=_get_context(request,section="admin",content="content_task_log",report=report)

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )

@requires_session(["admin"])
def system_report_error(request,id):
	#get controller api
	api=ControllerAPI(request)
	report=api.gettaskerrors(id)

        #template context
	context=_get_context(request,section="admin",content="content_task_errors",report=report)

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )

@requires_session(["admin"])
def system_report_test(request,id):
	def spread(match):
		diff=match["scores"][0]-(match["scores"][1] if len(match["scores"])>1 else 0)
		if len(match["scores"])>1:
			spread=diff/(float(sum(match["scores"][1:5]))/len(match["scores"][1:5]))
		else:
			spread=diff
		return spread

	#get controller api
	api=ControllerAPI(request)
	report=api.gettaskresults(id)

	#get stats
	stats={}
	for task in report:
		dataset=task["stats"]["test"]["matches"]

		#direct successful matches 
		stats["direct_success"]=[]

		#match score
		stats["direct_success"].append( [match["scores"][0] for match in dataset if (match["match"] is True and match["direct"] and match["success"]) ] )

		#2nd best score
		stats["direct_success"].append( [(match["scores"][1] if len(match["scores"])>1 else 0) for match in dataset if (match["match"] is True and match["direct"] and match["success"]) ] )


		#direct successful spread
		stats["direct_success_spread"]=[]

		#match spread
		stats["direct_success_spread"].append( [spread(match) for match in dataset if (match["match"] is True and match["direct"] and match["success"]) ] )


		#direct failed matches
		stats["direct_fail"]=[]

		#match score
		stats["direct_fail"].append( [match["scores"][0] for match in dataset if (match["match"] is True and match["direct"] and match["success"] is False) ] )

		#2nd best score
		stats["direct_fail"].append( [(match["scores"][1] if len(match["scores"])>1 else 0) for match in dataset if (match["match"] is True and match["direct"] and match["success"] is False) ] )

		#reference item score
		stats["direct_fail"].append( [match["ref"] for match in dataset if (match["match"] is True and match["direct"] and match["success"] is False) ] )


		#direct failed match spread
		stats["direct_fail_spread"]=[]

		#match spread
		stats["direct_fail_spread"].append( [spread(match) for match in dataset if (match["match"] is True and match["direct"] and match["success"] is False) ] )


        #template context
	context=_get_context(request,section="common",content="content_task_test",report=report,stats=stats)

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )


@requires_session(["admin"])
def system_analytics_test(request,id):
	#get anayltics api
	api=AnalyticsAPI(request)
	items=api.getmatcheritems(id)
	items=[item.todict() for item in items]

        #template context
	context=_get_context(request,section="common",content="content_task_analytics",items=json.dumps(items))

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )


@requires_session(["admin"])
def system_report_results(request,id):
	#get controller api
	api=ControllerAPI(request)
	report=api.gettaskresults(id)

        #template context
	context=_get_context(request,section="admin",content="content_task_results",report=report)

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )


@requires_session(["admin"])
def system_training(request):
	#get all data
	data=MLCase.list()

        #template context
	context=_get_context(request,section="common",content="content_system_training",data=data)

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )


@requires_session()
def system_tests(request):
	#get tests
	data=TestCase.list(owner=request.session['user'].id)

        #template context
	context=_get_context(request,section="common",content="content_system_tests",data=data)

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )



@requires_session()
def training_new(request):
	#get merchants
	api=ControllerAPI(request)
	merchants=api.getmerchants()

	#create?
	if "action" in request.REQUEST and request.REQUEST["action"]=="update":
		#get parameters
		label=request.REQUEST["label"]
		module=request.REQUEST["module"]
		merchantid=request.REQUEST["merchant"]
		autotask="system" in request.REQUEST
		
		#find merchant name
		mname="*"
		if merchantid!="*":
			for merchant in merchants:
				if merchantid==merchant["id"]:
					merchantname=merchant["name"]
		
		#create or update
		data=None
		if autotask is True:
			data=MLCase.get(label=label,module=module)
		if data is None:
			data=MLCase()
		data.owner=request.session["user"].id
		data.label=label
		data.module=module
		data.op="match" if module.endswith("Matcher") else "scrap"
		data.target={"merchant":{"id":merchantid,"name":merchantname}}
		data.create()

		#create task to generate samples for the training data
		tasks=[]
		task=Task()
		task.target="cimri.module.automation.controller.Controller"
		task.op="controller.schedule"
		task.threadtags="egitim: "+label
		tasks.append(task)
       	 	task=Task()
        	task.target="cimri.module.crawler.productxml.ProductXMLCrawler"
 		task.op="sample"
		if merchantid!="*":
			task.meta["merchants.id"]=int(merchantid)
		task.meta["sample.size"]=40     
		tasks.append(task)

		#schedule
		api=ControllerAPI(request)
		res=api.schedule(tasks)

		#get task id 
		tid=res[1]

		#response
		if autotask:
			return HttpResponse( AIResponse( data={"id":str(data.id), "tid":tid} ).serialize() )

	        #template context
		context=_get_context(request,section="common",content="content_training_created",data=data,tid=tid)

	else:
	        #template context
		context=_get_context(request,section="common",content="content_training_new",merchants=merchants)

	#render
        return HttpResponse( get_template('template_content.html').render(Context(context)) )



@api_requires_session()
@api_call
def training_check(request,id,tid):
	#get controller api
	api=ControllerAPI(request)
	report=api.gettaskresults(tid)

	#if ready, get urls
	if report[0]["status"]=="complete":
		#get ML data
		data=MLCase.get(id=id)

		#set data
		data.data=report[0]["result"]

		#update
		data.status=MLCase.STATUS_READY
		data.save()

	#return authentication
	return HttpResponse( AIResponse(data=data.data).serialize() )


@requires_session()
def test_new(request):
	#get merchants
	api=ControllerAPI(request)
	merchants=api.getmerchants()

	#create?
	if "action" in request.REQUEST and request.REQUEST["action"]=="update":
		#get parameters
		auto=int(request.REQUEST["auto"])
		label=request.REQUEST["label"]
		module=request.REQUEST["module"]
		merchantid=request.REQUEST["merchant"]
		items=request.REQUEST["items"]
		
		#autogenerate samples?
		if auto==1:		
			#find merchant name
			mname="*"
			if merchantid!="*":
				for merchant in merchants:
					if merchantid==merchant["id"]:
						merchantname=merchant["name"]
		
			#create
			data=TestCase()
			data.owner=request.session["user"].id
			data.label=label
			data.module=module
			data.op="match" if module.endswith("Matcher") else "scrap"
			data.target={"merchant":{"id":merchantid,"name":merchantname}}
			data.create()

			#create task to generate samples for the training data
			tasks=[]
			task=Task()
			task.target="cimri.module.automation.controller.Controller"
			task.op="controller.schedule"
			task.threadtags="test: "+label
			tasks.append(task)
       		 	task=Task()
 	      	 	task.target="cimri.module.crawler.productxml.ProductXMLCrawler"
 			task.op="sample"
			if merchantid!="*":
				task.meta["merchants.id"]=int(merchantid)
			task.meta["sample.size"]=40     
			tasks.append(task)

		#create samples based on the provided list of item IDs
		else:
			#get items
			input=eval(items.replace("\n",""))
			items=[]
			for it in input:
				item=MerchantItem()
				item.merchant={"merchantId":str(it[0]).strip()}
				item.merchantItemId=str(it[1]).strip()
				item.item={"itemId":str(it[2]).strip()}
				items.append(item)				

			#create
			data=TestCase()
			data.owner=request.session["user"].id
			data.label=label
			data.module=module
			data.op="match" if module.endswith("Matcher") else "scrap"
			data.target={}
			data.batch=[item.to_dict() for item in items]
			data.create()

			#create task to generate samples for the training data
			tasks=[]
			task=Task()
			task.target="cimri.module.automation.controller.Controller"
			task.op="controller.schedule"
			task.threadtags="test: "+label
			tasks.append(task)
       		 	task=Task()
 	      	 	task.target="cimri.module.crawler.productxml.ProductXMLCrawler"
 			task.op="get"
			task.data=items
			task.meta={"workers":8}
			tasks.append(task)

		#schedule
		api=ControllerAPI(request)
		res=api.schedule(tasks)

		#get task id			
		tid=res[1]

	        #template context
		context=_get_context(request,section="common",content="content_test_created",test=data,tid=tid)

	else:
	        #template context
		context=_get_context(request,section="common",content="content_test_new",merchants=merchants)

	#render
        return HttpResponse( get_template('template_content.html').render(Context(context)) )



@api_requires_session()
@api_call
def test_check(request,id,tid):
	#get controller api
	api=ControllerAPI(request)
	report=api.gettaskresults(tid)

	#if ready, get urls
	if report[0]["status"]=="complete":
		#get test case
		data=TestCase.get(id=id)

		#set data
		data.data=report[0]["result"]

		#if batch, prepare the reference items
		if data.batch is not None:
			for index in range(len(data.data)):
				#find the batch reference data for this item
				xmlitem=data.data[index]['meta.xmlitem']
				for batch in data.batch:
					if batch['merchant']['merchantId']==xmlitem['merchant']['merchantId'] and batch['merchantItemId']==xmlitem['merchantItemId']:
						#create merchantItem with values from the xml as reference
						item=MerchantItem()
						item.merchantItemTitle=xmlitem["merchantItemTitle"]	
						item.brand=xmlitem["brand"]	
						item.mpnValue=xmlitem["mpnValue"]
						item.item={"itemId":batch["item"]["itemId"]}
						data.data[index]["meta.refitem"]=item.to_dict()

		#update
		data.status=TestCase.STATUS_READY
		data.save()

	#return authentication
	return HttpResponse( AIResponse(data=data.data).serialize() )


@requires_session()
def scraper_test_build(request,id):
	#get test case
	data=TestCase.get(id=id)

        #template context
	context=_get_context(request,section="common",content="content_scraper_test_build",data=json.dumps(data.data),id=id)

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )


@api_requires_session()
@api_call
def scraper_test_update(request,id):
	#get parameters
	index=int(request.REQUEST["index"])
	fields={}
	for field in ['merchantItemTitle','pricePlusTax','priceEft','modelNameView','brand','mpnValue','shipping','inStock']:
		if field in request.REQUEST:
			fields[field]=request.REQUEST[field]

	#create merchantItem
	item=MerchantItem()
	for field in vars(item):
		if field in fields.keys():
			setattr(item,field,fields[field])
		else:
			setattr(item,field,None)

	#get test case
	data=TestCase.get(id=id)

	#update
	data.data[index]["meta.refitem"]=item.to_dict()
	data.save()
	
	#return authentication
	return HttpResponse( AIResponse().serialize() )


@requires_session()
def scraper_training_build(request,id):
	#get ML case
	ml=MLCase.get(id=id)

        #template context
	context=_get_context(request,section="common",content="content_scraper_training_build",data=json.dumps(ml.data),id=id)

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )



@api_requires_session()
@api_call
def scraper_training_update(request,id):
	#get parameters
	index=int(request.REQUEST["index"])
	fields={}
	for field in ['merchantItemTitle','pricePlusTax','priceEft','modelNameView','brand','mpnValue','shipping','inStock']:
		if field in request.REQUEST:
			fields[field]=request.REQUEST[field]

	#create merchantItem
	item=MerchantItem()
	for field in vars(item):
		if field in fields.keys():
			setattr(item,field,fields[field])
		else:
			setattr(item,field,None)

	#get ML case
	data=MLCase.get(id=id)

	#update
	data.data[index]["meta.refitem"]=item.to_dict()
	data.save()
	
	#return authentication
	return HttpResponse( AIResponse().serialize() )



@requires_session()
def matcher_test_build(request,id):
	#get test case
	data=TestCase.get(id=id)

        #template context
	context=_get_context(request,section="common",content="content_matcher_test_build",data=json.dumps(data.data),id=id)

	#render
        return HttpResponse( get_template('template_cpanel.html').render(Context(context)) )


@api_requires_session()
@api_call
def matcher_test_update(request,id):
	#get parameters
	index=int(request.REQUEST["index"])
	fields={}
	for field in ['merchantItemTitle','brand','mpnValue','item.itemId']:
		if field in request.REQUEST:
			tokens=field.split(".")
			if len(tokens)>1:
				fields[tokens[0]]={}
				fields[tokens[0]][tokens[1]]=request.REQUEST[field]		
			else:
				fields[field]=request.REQUEST[field]

	#create merchantItem
	item=MerchantItem()
	for field in vars(item):
		if field in fields.keys():
			setattr(item,field,fields[field])
		else:
			setattr(item,field,None)

	#get test case
	data=TestCase.get(id=id)

	#update
	data.data[index]["meta.refitem"]=item.to_dict()
	data.save()
	
	#return authentication
	return HttpResponse( AIResponse().serialize() )


@api_requires_session(["admin"])
@api_call
def catalogue_items(request):
	#get parameters
	title=request.REQUEST["title"];
	brand=request.REQUEST["brand"];
	mpn=request.REQUEST["mpn"];

	#get controller api
	api=ControllerAPI(request)
	data=api.getcatalogueitems(title,brand,mpn)
	
	#return authentication
	return HttpResponse( AIResponse(data=data).serialize() )

@api_call
def get_scraper_item(request,merchantid):
	#get scraper api
	api=ScraperAPI(request)

	#get parameters
	url=request.REQUEST["url"] if "url" in request.REQUEST else ""
	age=request.REQUEST["age"] if "age" in request.REQUEST else None
	format=request.REQUEST["format"] if "format" in request.REQUEST else "json"

	#validate
	if format not in ["json","html"]:
		format="json"

	#get item
	items=api.getitems(merchantid,url,age,0,1)
	item=items[0].todict() if (items is not None and len(items)>0) else None
	
	#render
	if format=="json":
		return HttpResponse( AIResponse(data=item).serialize() )
	else:
		output=[]
		output.append("id: "+str(item["id"])+"<br/>")
		output.append("merchantid: "+str(item["merchantid"])+"<br/>")
		output.append("url: <a href='"+item["url"]+"' target='_blank'>"+str(item["url"])+"</a><br/>")
		output.append("updated: "+str(item["updated"])+"<br/>")

		for field in item["info"]:
			if item["info"][field] is not None:
				output.append(field+": "+str(item["info"][field])+"<br/>")
		return HttpResponse( "".join(output) )


@api_call
def get_scraper_items(request,merchantid):
	#get scraper api
	api=ScraperAPI(request)

	#get parameters
	age=request.REQUEST["age"] if "age" in request.REQUEST else None
	format=request.REQUEST["format"] if "format" in request.REQUEST else "json"
	skip=request.REQUEST["skip"] if "skip" in request.REQUEST else 0
	limit=request.REQUEST["limit"] if "limit" in request.REQUEST else 1000

	#validate
	if format not in ["json","html"]:
		format="json"
	try:
		skip=int(skip)
	except:
		skip=0		
	try:
		limit=int(limit)
		if limit>1000:
			limit=1000
	except:
		limit=1000
		
	#get item
	items=api.getitems(merchantid,None,age,skip,limit)
	items=[item.todict() for item in items]

	#render
	if format=="json":
		return HttpResponse( AIResponse(data=items).serialize() )
	else:
		output=[]
		for item in items:
			output.append("id :"+str(item["id"])+"<br/>")
			output.append("merchantid :"+str(item["merchantid"])+"<br/>")
			output.append("url: <a href='"+item["url"]+"' target='_blank'>"+str(item["url"])+"</a><br/>")
			output.append("updated :"+str(item["updated"])+"<br/>")

			for field in item["info"]:
				if item["info"][field] is not None:
					output.append(field+": "+str(item["info"][field])+"<br/>")
			output.append("<br/>")
		return HttpResponse( "".join(output) )



def _get_context(request,**kwargs):
        #default context
        context={"resource_url":                Config.resource_url}

	#default content section
	section=''

	#get session related
	if 'user' in request.session:
		section=request.session['user'].type

		#set user
		context['user']=request.session['user']

		#set menu
		context['menu']=os.path.join(section,'section_menu.html')

	#if section specifically specified:
	if "section" in kwargs:
		section=kwargs["section"]

	#add content
	if "content" in kwargs:
		context['content']=os.path.join(section,kwargs['content']+".html")

        #add other context variables
        for key in kwargs:
		if key in ["section","content"]:
			continue
                context[key]=kwargs[key]

        return context




