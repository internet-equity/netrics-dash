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
  return $.getJSON('stats', update_view);
}


const subjective = {
    labels: {
        display: {
          unusable: "Unusable",
          slow: "Slow",
          good: "Good"
        },
        color: {
          unusable: "bad",
          slow: "attn",
          good: "good"
        }
    },
    handleSuccess: function (data) {
        const value = data.inserted.value,
              elem = document.getElementById("subj_button"),
              parEl = elem.parentElement,
              thanks_div = document.getElementById("survey_thanks");

        console.debug("survey: success:", value);

        if (!elem) return;

        elem.innerHTML = this.labels.display[value]
        elem.classList.add("survey_after")

        set_color_class(parEl, this.labels.color[value])

        thanks_div.innerHTML = "Thanks for participating!"
    },
    send: function (value) {
        return $.post('/dashboard/survey/', {subjective: value}, this.handleSuccess.bind(this));
    }
};


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


function make_plots (data) {
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


function async_load_plots () {
  return $.getJSON('plots')
    // convert timestamp -> Date to ensure formatting
    .then(data => Object.fromEntries(
      Object.entries(data).map(([name, block]) => {
        const fixed = Object.assign({}, block)

        if (block.ts) {
          fixed.ts = []

          for (let stamp of block.ts) {
            if (typeof stamp === 'number') {
              stamp = new Date(stamp * 1000)
            }

            fixed.ts.push(stamp)
          }
        }

        return [name, fixed]
      })
    ))
    .done(make_plots)
}


function update_trial_stats (wifi_trial, isp_dl) {
  if (Number.isInteger(wifi_trial.total_count) && wifi_trial.total_count > 2) {
    const mbaud = (wifi_trial.stat_mean * 8 / 1e06).toFixed(1),
          [op, desc, label] = ndt7view.compare_speeds(mbaud, isp_dl),
          info = document.getElementById('wifi-info');

    info.innerHTML = `Your Web browser(s) have conducted ${wifi_trial.total_count} download tests of your home network. `;
    info.innerHTML += (wifi_trial.total_count === wifi_trial.stat_count) ? 'Over these, ' : `In the bulk of these — ${wifi_trial.stat_count} tests — `;
    info.innerHTML += `your network bandwidth averaged ${mbaud} megabits per second. So, your home network bandwidth is usually ${op} that of the connection from your ISP: that's ${desc}.`;

    document.querySelectorAll('.wifi-stats').forEach(elem => {
        elem.style.display = 'initial';
    });
  }
}

function async_load_trials () {
  return $.getJSON('trial/stats');
}


const extWatcher = {
  enabled: true,
  installed: null,
  extDataType: 'ndt7ext',
  storageKeys: ['notInstalledDimiss', 'installedDismiss'],
  listen: function (event) {
    // We only accept messages from ourselves
    if (event.source !== window) return;

    if (event.data.type === this.extDataType) {
      // DEBUG: console.debug("page received from extension: %s", event.data.text);

      if (! this.installed) {
        this.installed = true;
        this.updateView();
      }
    }
  },
  start: function () {
    window.addEventListener('message', this.listen.bind(this), false);
    setTimeout(this.timeout.bind(this), 1000);
  },
  timeout: function () {
    if (this.installed === null) {
      this.installed = false;
      this.updateView();
    }
  },
  updateView: function () {
    if (this.getDismiss()) return;

    var notice = $('.extension-notice'),
        noticeMissing = $('.extension-notice-missing'),
        noticeInstalled = $('.extension-notice-installed');

    notice.toggleClass('extension-notice-success', this.installed);
    notice.toggleClass('extension-notice-failure', ! this.installed);

    noticeInstalled.collapse(this.installed ? 'show' : 'hide');
    noticeMissing.collapse(this.installed ? 'hide' : 'show');

    notice.collapse('show');

    notice.click(this, this._dismiss);
  },
  _dismiss: function (event) {
    // collapse notice IFF it wasn't the installation link that they clicked
    if (! event.target.href) {
      $(this).collapse('hide')

      // persist their election to dismiss this notice
      event.data.setDismiss()
    }
  },
  getDismissKey: function () {
      const keyIndex = Number(this.installed)

      return this.storageKeys[keyIndex]
  },
  getDismiss: function () {
      const storageKey = this.getDismissKey()

      return storageKey && localStorage.getItem(storageKey)
  },
  setDismiss: function () {
      const storageKey = this.getDismissKey()

      if (storageKey) {
        localStorage.setItem(storageKey, '1')
      }
  },
  isGoogleChrome: function () {
    var winNav = window.navigator,
        userAgent = winNav.userAgent,
        vendorName = winNav.vendor;

    var hasChromium = Boolean(window.chrome);

    var isOpera = window.opr !== undefined,
        isIEedge = userAgent.indexOf('Edge') > -1,
        isIOSChrome = userAgent.indexOf('CriOS') > -1,
        isGoogle = vendorName === "Google Inc.";

    return isIOSChrome || (
      hasChromium &&
      !isOpera &&
      !isIEedge &&
      isGoogle
    );
  },
  hostPattern: /^(netrics\.)?local/,
  isProperHost: function () {
    return this.hostPattern.test(window.location.hostname);
  },
  canInstall: function () {
    // for now don't bother them unless they're using Google Chrome
    return this.enabled && this.isProperHost() && this.isGoogleChrome();
  }
};

if (extWatcher.canInstall()) extWatcher.start();


Promise.all([
  async_load_data(),
  async_load_trials()
]).then(values => {
  const [isp_stats, wifi_trial] = values;
  update_trial_stats(wifi_trial, isp_stats.ookla_dl);
});

async_load_plots();
