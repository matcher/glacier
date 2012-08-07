(function ($) {
	//main plugin constructor
	_plugin = $.fn['cimri_cpanel'] = $['cimri_cpanel'] = function(){;};

	//no session url
	_plugin.nosessionurl="/";

	//comm
	_plugin.comm={lock:false};

	//return codes
	_plugin.comm.SUCCESS=1;
	_plugin.comm.ERROR=-1;

	//error codes
	_plugin.comm.ERROR_VALIDATION=1;
	_plugin.comm.PERMISSION=2;
	_plugin.comm.NO_DATA=3;
	_plugin.comm.SYSTEM=4;
	_plugin.comm.PROTOCOL=5;
	_plugin.comm.NO_SESSION=6;

    _plugin.comm.call=function(path,args,handler){
                //single concurrent API call
                if(_plugin.comm.lock)
                        return;
                _plugin.comm.lock=true;

	var type='POST';
	if(args==null)
		type='GET';

        $.ajax({
            url: path+"/",
            data: args,
            dataType: 'json',
            type: type,
            success: function(resp){
                                _plugin.comm.lock=false;


                //check response
                if(resp.status==_plugin.comm.SUCCESS){
		if(handler)
                    handler.success(resp.data);
                }else{
                                        //check session timeout
                                        if(resp.error.code==_plugin.comm.NO_SESSION){
                                                //redirect
                                                if(_plugin.nosessionurl)
                                                        window.location=_plugin.nosessionurl;

                                                return;
                                        }

		if(handler)
                    handler.error(resp.error);
                                }
            },
            error: function(req, status, err){
                                _plugin.comm.lock=false;

                handler.error({code:_plugin.comm.SYSTEM,msg:''});
            }
        });
    }

    _plugin.comm.html=function(path,args,handler){
	var type='POST';
	if(args==null)
		type='GET';
	
        $.ajax({
            url: path,
            data: args,
            dataType: 'text',
            type: type,
            success: function(resp){
                handler.success(resp);
            },
            error: function(req, status, err){
                handler.error();
            }
        });
    }


        _plugin.login=function(uname,pwd){
                //login
                _plugin.comm.call("/login/"+uname+"/"+pwd,
                                                  {},
                                                  {success: function(data){
                                                        window.location='/system/monitor/';
                                                   },
                                                   error: function(){
							console.log('fail');
                                                  }});
        }


        _plugin.logout=function(){
                //logout
                _plugin.comm.call("/logout",
                                                  {},
                                                  {success: function(data){			
                                                        window.location=_plugin.nosessionurl;
                                                   },
                                                   error: function(){
                                                        window.location=_plugin.nosessionurl;
                                                  }});
        }


	_plugin.showcontent=function(div,url){
		_plugin.comm.html(url,null,{"success":function(html){$("#"+div).html(html) } });
	}

	_plugin.submitcontent=function(div,url){
		//get parameters
		params={}
		$("#"+div).find("input").each(function(index,elmt){
			var dom=$(elmt);
			params[dom.attr("id")]=dom.val();
		});
		$("#"+div).find("select").each(function(index,elmt){
			var dom=$(elmt);
			params[dom.attr("id")]=dom.val();
		});
		$("#"+div).find("textarea").each(function(index,elmt){
			var dom=$(elmt);
			params[dom.attr("id")]=dom.val();
		});

		//submit
		_plugin.comm.html(url,params,{"success":function(html){$("#"+div).html(html) } });
	}


})(jQuery);

