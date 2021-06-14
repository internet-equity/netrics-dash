function set_color_class (el, val) {
  el.classList.remove("bad")
  el.classList.remove("ok")
  el.classList.remove("good")
  el.classList.remove("attn")
  el.classList.add(val)
}


function update_view (data) {
  for (const [key, value] of Object.entries(data)) {
    elem = document.getElementById(key)
    if (!elem) continue;
    elem.innerHTML = value;
  }

  // Oookla data setings.

  elem = document.getElementById("ookla_dl")
  pardiv = elem.parentElement.parentElement
  if      (data["ookla_dl"] > 50) set_color_class(pardiv, "good");
  else if (data["ookla_dl"] < 25) set_color_class(pardiv, "bad");
  else                 set_color_class(pardiv, "ok");

  document.getElementById("bw_slash").innerHTML = "/"

  document.getElementById("text_ookla_dl").innerHTML = data["ookla_dl"]
  document.getElementById("text_ookla_ul").innerHTML = data["ookla_ul"]

  text_bw_interp    = document.getElementById("text_bw_interp")
  text_bw_fcc       = document.getElementById("text_bw_fcc")
  text_bw_stability = document.getElementById("text_bw_stability")

  if      (data["ookla_dl"] > 500) text_bw_interp.innerHTML = "higher than most";
  else if (data["ookla_dl"] < 30)  text_bw_interp.innerHTML = "lower than most";
  else    text_bw_interp.innerHTML  = "similar to other"

  if (data["ookla_dl"] > 25 && data["ookla_ul"] > 3)
    text_bw_fcc.innerHTML = "exceeds";
  else 
    text_bw_fcc.innerHTML = "does not meet";

  if (data["ookla_dl_sd"] > 0.15 * data["ookla_dl"])
    text_bw_stability.innerHTML = "not stable"
  else text_bw_stability.innerHTML = "stable"

  // Latency
  elem = document.getElementById("latency")
  pardiv = elem.parentElement.parentElement
  pardiv = elem.parentElement
  if      (data["latency"] < 15) set_color_class(pardiv, "good");
  else if (data["latency"] > 40) set_color_class(pardiv, "bad");
  else                 set_color_class(pardiv, "ok");

  text_latency_interp = document.getElementById("text_latency_interp")
  if (data["latency"] > 40) text_latency_interp.innerHTML = "worse than most";
  else if (data["latency"] < 10) text_latency_interp.innerHTML = "lower than most";
  else text_latency_interp.innerHTML = "similar to other";
}


function async_load_data () {
  $.ajax({
    url: 'stats',
    dataType: 'json',
    success: update_view
  });
}


function send_subjective (value) {
  display_map = {"unusable" : "Unusable", "slow" : "Slow", "good" : "Good"}
  color_map   = {"unusable" : "bad", "slow" : "attn", "good" : "good"}

  $.post('/dashboard/survey/',
    {
      subjective: value
    }, 
    function () {
      console.log("survey: success:", value);

      const elem = document.getElementById("subj_button")
      if (!elem) return
      elem.innerHTML = display_map[value]
      elem.classList.add("survey_after")

      parEl = elem.parentElement
      set_color_class(parEl, color_map[value])

      const thanks_div = document.getElementById("survey_thanks")
      thanks_div.innerHTML = "Thanks for participating!"
    }
  );
}


function toggle (a, target) {
  expand = (a.innerHTML[0] == "+")
  txt = a.innerHTML
  txt = txt.substr(1, txt.length)

  more = document.getElementById(target)

  if (expand) {
    a.innerHTML = "- " + txt
    // more.style.display = 'block'
    more.style.maxHeight = more.scrollHeight + "px";
  } else {
    a.innerHTML = "+ " + txt
    // more.style.display = 'none'
    more.style.maxHeight = null;

  }
}


function make_plots(data) {
  var config = {"displayModeBar" : false}

  var layout = {
    autosize: true,
    height: 300,
    margin: { l: 70, r: 60, b: 50, t: 20, pad: 0},
    font : { size : 18 },
    showlegend: true,
    legend: {"orientation": "v", "x" : 0.05, "y" : 0.95}
  };


  // BANDWIDTH

  var bw_series = [
    { name: "Download", type: 'scatter',
      x: data["bw"]["ts"], y: data["bw"]["dl"]},
    { name: "Upload", type: 'scatter',
      x: data["bw"]["ts"], y: data["bw"]["ul"]
    }
  ];

  bw_layout = layout;
  bw_layout["yaxis"] = { title : { text: 'Bandwidth [Mbps]'} };

  Plotly.newPlot('bw_plot', bw_series, bw_layout, config);


  // LATENCY

  var lat_series = [
    { name: "Google", type: 'scatter',
      x: data["latency"]["ts"], y: data["latency"]["google"]},
    { name: "Amazon", type: 'scatter',
      x: data["latency"]["ts"], y: data["latency"]["amazon"]},
    { name: "Wikipedia", type: 'scatter',
      x: data["latency"]["ts"], y: data["latency"]["wikipedia"]},
  ];

  lat_layout = layout;
  lat_layout["yaxis"] = { title : { text: 'Latency [ms]'},
                          range : [0, 75]};

  Plotly.newPlot('latency_plot', lat_series, lat_layout, config);

  // CONSUMPTION

  var con_series = [
    { name: "Download", type: 'scatter',
      x: data["consumption"]["ts"], y: data["consumption"]["dl"]},
    { name: "Upload", type: 'scatter',
      x: data["consumption"]["ts"], y: data["consumption"]["ul"]
    }
  ];

  con_layout = layout;
  con_layout["yaxis"] = { title : { text: 'Bandwidth [Mbps]'},
                          range : [0, 10]};

  Plotly.newPlot('cons_plot', con_series, con_layout, config);

  if (data['consumption']['ts'].length > 0) {
    // consumption stat requires hardware we're not currently rolling out
    $('#cons_plot').parents('.row').first().collapse('show');
  }

  // DEVICES
	
  var dev_series = [
    { name: "Active", type: 'scatter',
      x: data["devices"]["ts"], y: data["devices"]["active"]},
    { name: "1-Day", type: 'scatter',
      x: data["devices"]["ts"], y: data["devices"]["1d"]},
    { name: "1-Week", type: 'scatter',
      x: data["devices"]["ts"], y: data["devices"]["1w"]},
    { name: "All Time", type: 'scatter',
      x: data["devices"]["ts"], y: data["devices"]["tot"]}
  ];

  dev_layout = layout;
  dev_layout["yaxis"] = { title : { text: '# of Devices'}};

  Plotly.newPlot('dev_plot', dev_series, dev_layout, config);
}


function async_load_plots() {
  $.ajax({
    url: "plots",
    dataType: 'json',
    success: make_plots
  });
}


async_load_data();
async_load_plots();
