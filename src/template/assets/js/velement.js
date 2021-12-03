//---------------- v_elm.js -----------------
// All functions needed for custom audio playback
// NOTE: for longer videos fragmentation might be needed.
// data-scale can be no-scale or max-height, default:no-scale
const video_played_finished = new Map();
const video_play_start_time = new Map();
const video_play_time_update_listeners = new Map();
const video_player_can_played_through = new Set();

var videoElements=[];
var scheduled_video_play = null;
var split_screen_timer = null;
var tmp_caller_func = null;
var dcr_clip_name_duration= 3100;
function clickManager(event) {
	ae=event.data.ae;
	var id=event.data.id;
	if (ae.paused) {
		pauseAll();
		idT = ae.id;
		id = idT.substring(7,idT.length);
		reset_videos(id);
		playVideo(ae);
	} else {
		pauseVideo(ae);
	}
};

function reset_videos(id){
    //resetting the video1
    tmp1_v = document.getElementById("video1_{0}".f(id));
    tmp1_v.currentTime = 0;

    // resetting video2 if exist
    if ($("#{0}".f(id)).hasClass('dcr')){
        tmp1_v = document.getElementById("video2_{0}".f(id));
        tmp1_v.currentTime = 0;
    }
    duration = 0;
	$("#velmnt_l_c_"+id).text(duration.toString().toMMSS());
}


function fullscreen_closed(e, video, caller){
    if (!document.fullscreenElement && /* Standard syntax */
        !document.webkitFullscreenElement && /* Chrome, Safari and Opera syntax */
        !document.mozFullScreenElement &&/* Firefox syntax */
        !document.msFullscreenElement /* IE/Edge syntax */
      ) {
      	var idT=video.id;
		var id=idT.substring(7,idT.length);
		reset_video_player(idT, video);

		$("#velmnt_"+id).show();

        //restore the old height and weight
        let oldH=video.getAttribute("oldheight");
        let oldW=video.getAttribute("oldwidth");
        video.setAttribute("width",oldW);
        video.setAttribute("height",oldH);
        video.removeAttribute("oldwidth");
        video.removeAttribute("oldheight");
		$( "#video_"+id ).closest( "td" ).addClass("vtd");
		if (video_played_finished.get(idT) != 1 ){
				alert("The video must be watched fully and in fullscreen mode.");
		}
   }
}

function reset_video_player(idT, video){
	if (scheduled_video_play)
		clearTimeout(scheduled_video_play);
	if (split_screen_timer)
        clearTimeout(split_screen_timer);
	if (!(video.paused || video.ended))
		pauseVideo(video);

	id = idT.substring(7,idT.length);
	$("#video1_{0}".f(id)).show();
	if ($("#{0}".f(id)).hasClass('dcr')){
        $("#video2_{0}".f(id)).hide();
	}

	let parent = document.getElementById(id);
	parent.classList.remove("bg");
	parent.classList.remove("bg1");
	parent.classList.remove("bg2");
	$("#{0} .vcontainer".f(id)).show();

	$("#velmnt_s_"+id).removeClass("glyphicon-pause");
	$("#velmnt_"+id).removeClass("btn-primary");
	$("#velmnt_s_"+id).addClass("glyphicon-repeat");
}

function playVideo(video){
	var idT=video.id;
	var id=idT.substring(7,idT.length);
	is_first_video = idT.indexOf('video1_')==0;
	$("#velmnt_s_"+id).removeClass("glyphicon-repeat");
	$("#velmnt_s_"+id).removeClass("glyphicon-play");
	$("#velmnt_s_"+id).addClass("glyphicon-pause");
	$("#velmnt_"+id).addClass("btn-primary");
	$("#video_n_play_"+id).val(parseInt($("#video_n_play_"+id).val())+1);
	$("#velmnt_"+id).hide();

	let parent = document.getElementById(id);
	if (is_first_video){
		if (parent.requestFullscreen) {
			parent.requestFullscreen();
		  } else if (parent.msRequestFullscreen) {
			parent.msRequestFullscreen();
		  } else if (parent.mozRequestFullScreen) {
			parent.mozRequestFullScreen();
		  } else if (parent.webkitRequestFullscreen) {
			parent.webkitRequestFullscreen();
		  }
	}

	// set the listeners for when fullscreen is closed
	previous_caller  =  tmp_caller_func;
	tmp_caller_func = function (e){ fullscreen_closed(e,video, tmp_caller_func) };

	if (parent.requestFullscreen) {
		parent.removeEventListener("fullscreenchange",previous_caller);
		parent.addEventListener("fullscreenchange",tmp_caller_func);
	} else if (parent.msRequestFullscreen) {
		parent.removeEventListener("onmsfullscreenchange",previous_caller);
		parent.addEventListener("onmsfullscreenchange",tmp_caller_func);
	} else if (parent.mozRequestFullScreen) {
		parent.removeEventListener("mozfullscreenchange",previous_caller);
		parent.addEventListener("mozfullscreenchange",tmp_caller_func);
	} else if (parent.webkitRequestFullscreen) {
		parent.removeEventListener("webkitfullscreenchange",previous_caller);
		parent.addEventListener("webkitfullscreenchange",tmp_caller_func);
	}

    if ($("#{0}".f(id)).hasClass('dcr')){
        parent.classList.add("bg1");
        parent.classList.add("bg");
        $("#{0} .vcontainer".f(id)).hide();
        scheduled_video_play = setTimeout(function(){ playVideo_continue(id, video, true); }, dcr_clip_name_duration);
        split_screen_timer = setTimeout(function(){ screen_splitter_timer(id); }, 1000);
    }else{
        playVideo_continue(id, video, false);
    }
}


function screen_splitter_timer(id){
    time = $("#velmnt_l_c_"+id).text().trim();;
    sec = convertMS(time);
    sec = sec +1 ;
    t = sec.toString().toMMSS();
	$("#velmnt_l_c_"+id).text(t);
	split_screen_timer = setTimeout(function(){ screen_splitter_timer(id); }, 1000);
}


function convertMS(timeString){
  const arr = timeString.split(":");
  const seconds = Number(arr[0])*60+Number(arr[1]);
  return seconds;
}


function playVideo_continue(id, video, is_dcr){
    //console.log("playVideo_continue video {0}, time{1}".f(id, (new Date()).toISOString()));
	scheduled_video_play = null;
	if (split_screen_timer){
        clearTimeout(split_screen_timer);
        split_screen_timer = null;
     }
    if (is_dcr){
    	let parent = document.getElementById(id);
    	parent.classList.remove("bg");
        parent.classList.remove("bg1");
        parent.classList.remove("bg2");
        $("#{0} .vcontainer".f(id)).show();
    }
    let oldH=video.getAttribute("height");
    let oldW=video.getAttribute("width");
    let fullW=screen.width;
    let fullH=screen.height;
    //change height and width
    video.setAttribute("oldwidth",oldW);
    video.setAttribute("oldheight",oldH);
	let scale_type = "";
	if ($('#{0}'.f(id)).attr('data-scale')){
		scale_type = $('#{0}'.f(id)).attr('data-scale');
	}else{
		scale_type = "no-scale";
	}
	if (scale_type=="max-height"){
		$( "#"+video.id ).closest( "td" ).removeClass("vtd");
		video.setAttribute("height",fullH);
		video.setAttribute("width",fullW);
	}

    video.play();
    if (video.id.indexOf('video1_')==0){
	    video_play_start_time.set(id, Date.now());

	 }
}

function pauseVideo(video){
	video.pause();
	var idT=video.id;
	var id=idT.substring(7,idT.length);
	$("#velmnt_s_"+id).removeClass("glyphicon-pause");
	$("#velmnt_"+id).removeClass("btn-primary");
	$("#velmnt_s_"+id).addClass("glyphicon-play");
}

function pauseAll(){
	for (i = 0; i < videoElements.length; i++) {
		if (!videoElements[i].paused){
			pauseVideo(videoElements[i]);
		}
	}
}

function canPlay(event){
	var ae=this;
	var idText =this.id;
	var id=idText.substring(7,idText.length);
	videos_not_loaded_yet_set.delete(idText);
	id1 = "video1_{0}".f(id);
	id2 = "video2_{0}".f(id);
	if (videos_not_loaded_yet_set.has(id1) || videos_not_loaded_yet_set.has(id2)){
		return;
	}
	duration = get_expected_duration(id, false);
	$("#velmnt_l_d_"+id).text(" / " + (duration).toString().toMMSS());
	$("#velmnt_"+id).removeClass("disabled");
	$("#velmnt_s_"+id).removeClass("glyphicon-repeat fast-right-spinner");
	$("#velmnt_s_"+id).addClass("glyphicon-play");
}

function canPlayThrough(event){
    var ae=this;
	var idText =this.id;
    video_player_can_played_through.add(idText);
    console.log(idText +", canPlayThrough, ready_state:"+ae.readyState);
}



function timeUpdate(is_dcr){
	var ae=this;
	var idText =this.id;
	var id=idText.substring(7,idText.length);
	let time = ae.currentTime;
	if (time == 0) return;
	if (is_dcr){
		if (idText.indexOf('video2_')==0){
			video1 = document.getElementById("video1_{0}".f(id));
			time = time + 2*(dcr_clip_name_duration/1000)+video1.duration;
		}else{
			time = time +(dcr_clip_name_duration/1000);
		}
	}
	t = time.toString().toMMSS()
	$("#velmnt_l_c_"+id).text(t);
}

function isended(){
	var ae=this;
	var idText =this.id;
	var id=idText.substring(7,idText.length);
    //console.log("is_ended video {0}, time{1}".f(id, (new Date()).toISOString()));
	is_first_time = video_played_finished.get(idText)==0;
	video_played_finished.set(idText, 1);
	let is_first_video = idText.indexOf('video1_')==0;
	//this.currentTime = 0

 	if (($("#{0}".f(id)).hasClass('dcr')) && is_first_video){
 		let parent = document.getElementById(id);
        parent.classList.add("bg2");
        parent.classList.add("bg");
        $("#{0} .vcontainer".f(id)).hide();
        $("#video1_{0}".f(id)).hide();
        $("#video2_{0}".f(id)).show();
        var video = document.getElementById("video2_"+id);

        // set the listeners for when fullscreen is closed
		previous_caller  =  tmp_caller_func;
		tmp_caller_func = function (e){ fullscreen_closed(e,video, tmp_caller_func) };
		if (parent.requestFullscreen) {
			parent.removeEventListener("fullscreenchange",previous_caller);
			parent.addEventListener("fullscreenchange",tmp_caller_func);
		} else if (parent.msRequestFullscreen) {
			parent.removeEventListener("onmsfullscreenchange",previous_caller);
			parent.addEventListener("onmsfullscreenchange",tmp_caller_func);
		} else if (parent.mozRequestFullScreen) {
			parent.removeEventListener("mozfullscreenchange",previous_caller);
			parent.addEventListener("mozfullscreenchange",tmp_caller_func);
		} else if (parent.webkitRequestFullscreen) {
			parent.removeEventListener("webkitfullscreenchange",previous_caller);
			parent.addEventListener("webkitfullscreenchange",tmp_caller_func);
		}

        scheduled_video_play = setTimeout(function(){ playVideo_continue(id, video, true); }, dcr_clip_name_duration);
        split_screen_timer = setTimeout(function(){ screen_splitter_timer(id); }, 1000);
    }else{
        end_video(id, is_first_video);
    }
}

function get_expected_duration(id, is_from_play){
    id1 = "video1_{0}".f(id);
    duration = 0;
	if($("#{0}".f(id)).hasClass('dcr')){
	    id2 = "video2_{0}".f(id);
		duration = (dcr_clip_name_duration/1000) + document.getElementById(id1).duration + document.getElementById(id2).duration ;
		if (!is_from_play)
		    duration+=dcr_clip_name_duration/1000

	}else{
	    duration = document.getElementById(id1).duration
	}

	return duration;
}


function end_video(id, is_first_video){
    //console.log("end_video video {0}, time{1}".f(id, (new Date()).toISOString()));
	$("#velmnt_s_"+id).removeClass("glyphicon-pause");
	$("#velmnt_"+id).removeClass("btn-primary");
	$("#velmnt_s_"+id).addClass("glyphicon-repeat");
	$("#video_n_finish_"+id).val(parseInt($("#video_n_finish_"+id).val())+1);
	if ($("#"+id).attr('data-onfinished')){
		window[$("#"+id).attr('data-onfinished')](id);
	}
	document.exitFullscreen();

	$("#velmnt_l_c_"+id).css('color','green');
	$("#velmnt_l_d_"+id).css('color','green');
	// for testing
	is_first_time = true;
	if (is_first_time){
		now = Date.now();
		play_duration = (Date.now()-  video_play_start_time.get(id))/1000;
		$("#video_play_duration_"+id).val(play_duration);
		expected_duration = get_expected_duration(id, true);
		$("#video_duration_"+id).val(expected_duration);

		extra_duration = play_duration-expected_duration;
		perc_delay = Math.abs(extra_duration)/expected_duration;
		if (extra_duration>max_accepted_extra_playing_time_sec ){
			maximum_extra_playing_time_reached(id);
		}
	}
	if (!is_first_video){
		// it is a two video case and now it is a second video
		$("#video1_{0}".f(id)).show();
        $("#video2_{0}".f(id)).hide();
	}
	//reset_videos(id);
}

function issuePlayingVideo(videoElement, issue){
	// todod log the data
	console.log(videoElement.id+": "+issue);
}



// loading all video elements in the page
$(function() {
    $( ".velmnt" ).each(function(){
		titleTextTemplate='<tr><td>{1}</td></tr>';
		insert='';
		title='';
		one_video_template = '<video id="video1_{0}" preload="true"  width="1" poster="../imgs/poster.png"><source src="{1}" type="video/mp4"> Sorry, your browser does not support embedded videos. </video>';
		two_videos_template = '<video id="video1_{0}" preload="true"  width="1" poster="../imgs/poster.png"><source src="{1}" type="video/mp4"> Sorry, your browser does not support embedded videos. </video>'+
		'<video id="video2_{0}" preload="true"  width="1" poster="../imgs/poster.png" hidden><source src="{2}" type="video/mp4"> Sorry, your browser does not support embedded videos. </video>';

		video_tag = one_video_template;
		is_two_video = $(this).hasClass('dcr');
		if(is_two_video){
			video_tag = two_videos_template;
		}

		a=video_tag +
		'<input type="hidden" id="video_n_play_{0}" name="video_n_play_{0}" value="0">'+
		'<input type="hidden" id="video_n_finish_{0}" name="video_n_finish_{0}" value="0">'+
		'<input type="hidden" id="video_play_duration_{0}" name="video_play_duration_{0}" value="0">'+
		'<input type="hidden" id="video_duration_{0}" name="video_duration_{0}" value="0">';
		if ($(this).attr('title')){
			insert=titleTextTemplate;
			title=$(this).attr('title');
		}
		id=$(this).attr('id');
		if(is_two_video){
			tmp = a.f(id, $(this).attr('data-src-ref'), $(this).attr('data-src-clip'))
		}else{
			tmp = a.f(id,$(this).attr('data-src'));
		}

		t='<table class="velmnt_table" border="0">'+insert+' <tr><td class="vtd"> <div class="vcontainer">'+tmp+'<button id="velmnt_{0}" type="button" class="btn bn disabled"><span id ="velmnt_s_{0}" class="glyphicon glyphicon-repeat fast-right-spinner"></span></button></div></td></tr><tr><td><span id="velmnt_l_c_{0}" class="blabel" >00:00</span><span id="velmnt_l_d_{0}" class="blabel" > / 00:00</span></td></tr></table>';
		$(this).append(t.f(id,title));
		let video_id = "video1_"+id;
		video_played_finished.set(video_id, 0);
		videos_not_loaded_yet_set.add(video_id);

		var videoElement = document.getElementById(video_id);
		//save for later
		videoElements.push(videoElement);
		$( "#velmnt_"+id ).click({ae: videoElement, id: id},clickManager);
		$( "#velmnt_"+id ).disabled=false;
		addListenersToVideoElement(videoElement, is_two_video);


		if(is_two_video){
			let video_id = "video2_"+id;
			video_played_finished.set(video_id, 0);
			videos_not_loaded_yet_set.add(video_id);
			var videoElement = document.getElementById(video_id);
			//save for later
			videoElements.push(videoElement);
			$( "#velmnt_"+id ).disabled=false;
			addListenersToVideoElement(videoElement, is_two_video);
		}

	});

	$("source").on("error", function (e) {
        problematic_urls=problematic_urls+"<li>"+e.target.src+"</li>";
        //$("#error_details").html(problematic_urls);
        recordError("on loading audio clips",e.target.src);
        //$("#error_loading_files").show();
    });
});

function addListenersToVideoElement(videoElement, is_dcr){
		videoElement.addEventListener("canplay",canPlay.bind(videoElement),false);
		videoElement.addEventListener("canplaythrough",canPlayThrough.bind(videoElement),false);
		videoElement.addEventListener("timeupdate",timeUpdate.bind(videoElement, is_dcr) ,false);
		videoElement.addEventListener("ended",isended.bind(videoElement),false);
		videoElement.addEventListener( "loadedmetadata", function (e) {
    		var width = this.videoWidth;
        	var height = this.videoHeight;
        	console.log("w:{0}, h:{1}".f(width,height));
		}, false );
		videoElement.addEventListener("stalled",function(){issuePlayingVideo(videoElement ,'stalled');},false);
		videoElement.addEventListener("suspend",function(){issuePlayingVideo(videoElement ,'suspend');},false);
		videoElement.addEventListener("abort",function(){issuePlayingVideo(videoElement ,'abort');},false);
		videoElement.addEventListener("error",function(){issuePlayingVideo(videoElement ,'error');},false);
}

var problematic_urls="";
/*
	Called when the scale item is clicked
*/
function alertForbiddenChange(){
	alert('You should watch until the end.');
	$(this).prop('checked', false);
}

/*
	Users should not be able to vot before listening the audio clips until the end.
*/
function avoidAnsweringBeforeWatchingThrough(){
	var i;
	// Training section
	for (i = 0; i < config['trainingUrls'].length; i++) {
		$('input[name="t{0}"]'.f(i+1)).on('change', alertForbiddenChange);
	}
	// Rating section
	for (i = 0; i < config['questionUrls'].length; i++) {
		$('input[name="q{0}"]'.f(i+1)).on('change', alertForbiddenChange);
	}
}
//---------------