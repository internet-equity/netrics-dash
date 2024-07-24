const dataView = {
  setColorClass (el, val) {
    el.classList.remove("bad")
    el.classList.remove("ok")
    el.classList.remove("good")
    el.classList.remove("attn")
    el.classList.add(val)
  },
}

dataView.elementToggle = (() => {
  function toggle () {
    const target = this.dataset.toggle,
          more = document.getElementById(target),
          html = this.innerHTML,
          expand = (html[0] == "+"),
          txt = html.substr(1, html.length);

    if (expand) {
      this.innerHTML = "- " + txt
      // more.style.display = 'block'
      more.style.maxHeight = more.scrollHeight + "px";
    } else {
      this.innerHTML = "+ " + txt
      // more.style.display = 'none'
      more.style.maxHeight = null;
    }
  }

  return {
    init () {
      $('[data-toggle]:not([data-toggle-defer])').click(toggle)
    },
    initDeferred (tag) {
      $(`[data-toggle][data-toggle-defer=${tag}]:not(.toggle-button-loaded)`)
      .click(toggle)
      .addClass('toggle-button-loaded')
    },
  }
})()


const subjectiveReport = {
  labels: {
    display: {
      unusable: "Unusable",
      slow: "Slow",
      good: "Good",
    },
    color: {
      unusable: "bad",
      slow: "attn",
      good: "good",
    },
  },
  elements: {
    button: document.getElementById('subj_button'),
    thanks: document.getElementById('survey_thanks'),
  },
  handleSuccess (data) {
    const value = data.inserted.value
    const widget = this.elements.button.parentElement

    console.debug("survey: success:", value)

    if (!this.elements.button) return

    this.elements.button.innerHTML = this.labels.display[value]
    this.elements.button.classList.add('survey_after')

    dataView.setColorClass(widget, this.labels.color[value])

    this.elements.thanks.innerHTML = "Thanks for participating!"
  },
  async send (value) {
    const data = await $.post('/dashboard/survey/', {subjective: value})
    this.handleSuccess(data)
    return data
  },
}


const ispStats = (() => {
  let $data = null
  let $request = null

  function cleanNumber (value) {
    return value >= 10 ? Math.round(value) : value
  }

  function updateView (data) {
    /* Update view with received data.
     */

    // Write data to banners.
    for (const [key, value] of Object.entries(data)) {
      const elem = document.getElementById(key)
      if (elem) elem.innerHTML = cleanNumber(value)
    }

    // Oookla data setings.

    let elem = document.getElementById("ookla_dl")
    let pardiv = elem.parentElement.parentElement
    if      (data["ookla_dl"] > 50) dataView.setColorClass(pardiv, "good");
    else if (data["ookla_dl"] < 25) dataView.setColorClass(pardiv, "bad");
    else                 dataView.setColorClass(pardiv, "ok");

    document.getElementById("bw_slash").innerHTML = "/"

    document.getElementById("text_ookla_dl").innerHTML = cleanNumber(data["ookla_dl"])
    document.getElementById("text_ookla_ul").innerHTML = cleanNumber(data["ookla_ul"])

    const text_bw_interp    = document.getElementById("text_bw_interp")
    const text_bw_fcc       = document.getElementById("text_bw_fcc")
    const text_bw_stability = document.getElementById("text_bw_stability")

    if      (data["ookla_dl"] > 500) text_bw_interp.innerHTML = "higher than most";
    else if (data["ookla_dl"] < 30)  text_bw_interp.innerHTML = "lower than most";
    else    text_bw_interp.innerHTML  = "similar to other";

    if (data["ookla_dl"] >= 100 && data["ookla_ul"] >= 20)
      text_bw_fcc.innerHTML = "exceeds";
    else
      text_bw_fcc.innerHTML = "does not meet";

    if (data["ookla_dl_sd"] > 0.15 * data["ookla_dl"])
      text_bw_stability.innerHTML = "However, your bandwidth varies significantly";
    else text_bw_stability.innerHTML = "Your bandwidth is consistent";

    // Latency
    elem = document.getElementById("latency")
    pardiv = elem.parentElement
    if      (data["latency"] < 15) dataView.setColorClass(pardiv, "good");
    else if (data["latency"] > 40) dataView.setColorClass(pardiv, "bad");
    else                 dataView.setColorClass(pardiv, "ok");

    const text_latency_interp = document.getElementById("text_latency_interp")
    if (data["latency"] > 40) text_latency_interp.innerHTML = "worse than most";
    else if (data["latency"] < 10) text_latency_interp.innerHTML = "lower than most";
    else text_latency_interp.innerHTML = "similar to other";
  }

  function update (data) {
    $data = data
    updateView(data)
  }

  return {
    get data () {
      return $data
    },
    get request () {
      return $request
    },
    load () {
      $request = $.getJSON('stats', update)
      return $request
    },
  }
})()


const ispPlots = {
  makePlots (data) {
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
  },
  entryTimestampToDate ([name, block]) {
    // convert timestamp -> Date to ensure formatting
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
  },
  async load () {
    const data = await $.getJSON('plots')
    const fixedEntries = Object.entries(data).map(this.entryTimestampToDate)
    const fixedData = Object.fromEntries(fixedEntries)

    this.makePlots(fixedData)

    dataView.elementToggle.initDeferred('plots')

    return fixedData
  },
}


const networkStats = {
  updateView (wifi_trial, isp_dl) {
    if (! Number.isInteger(wifi_trial.total_count) || wifi_trial.total_count < 3) return;

    const success_rate = wifi_trial.success_count === null ? null : (100 * wifi_trial.success_count / wifi_trial.total_count).toFixed(0),
          failure_rate = success_rate === null ? null : 100 - success_rate,
          failure_count = wifi_trial.success_count === null ? null : wifi_trial.total_count - wifi_trial.success_count,
          rate_stable = wifi_trial.stat_stdev < 0.15 * wifi_trial.recent_rates[0].speed,
          mbaud = (wifi_trial.stat_mean_win * 8 / 1e06).toFixed(0),
          [op, desc, label] = ndt7view.compareSpeeds(mbaud, isp_dl),
          info = $('#wifi-info');

    info.empty();  // clear any previous contents

    info.append(`<p>Your Web browser(s) have conducted ${wifi_trial.total_count} download tests of your home network.</p>`);

    if (rate_stable) {
        win_text = "Your network bandwidth was stable over these tests";
        win_text += (wifi_trial.total_count === wifi_trial.stat_count_win) ? " and" : `. In the bulk of these &ndash; ${wifi_trial.stat_count_win} tests &ndash; your network bandwidth`;
        win_text += ` <em>averaged</em> ${mbaud} megabits per second. This average is ${op} that of the connection from your ISP: that's ${desc}.`;
        info.append(`<p>${win_text}</p>`);
    } else if (success_rate !== null) {
        info.append(`<p>In ${wifi_trial.success_count} of these tests (${success_rate}%), the bandwidth of your network exceeded the most recent bandwidth of your connection to the Internet. In ${failure_count} of these tests (${failure_rate}%), your network &ndash; (probably your Wi-Fi) &ndash; might have limited your Internet speed.</p>`);
    }

    document.querySelectorAll('.wifi-stats').forEach(elem => {
        elem.style.display = 'initial';
    });
  },
  makePlot (trials, totalCount, isp_dl) {
    // for date series:
    // trials.map(point => new Date(point.ts * 1000))  // timestamp => date
    //
    // for trial number (range stepping backwards from totalCount):
    const trialNumbers = Array.from({length: trials.length}, (_undef, index) => totalCount - index)

    // bandwidths
    const bandwidths = trials.map(point => point.speed * 8 / 1e06)  // B/s => Mb/s

    // coax last ISP measurement line into legend
    const ispLine = {
      color: 'rgb(50, 171, 96)',
      dash: 'dashdot',
      width: 5,
    }

    return Plotly.react(
      // HTML target
      'wifi_plot',

      // datasets
      [
        {
          name: 'Network',
          type: 'bar',
          orientation: 'h',
          x: bandwidths,
          y: trialNumbers,
        },
        {
          name: 'ISP',
          visible: 'legendonly',
          x: [0],  // dummy
          y: [0],  // dummy
          line: ispLine,
        },
      ],

      // layout
      {
        autosize: true,
        height: 300,
        margin: {l: 70, r: 60, b: 50, t: 20, pad: 0},
        font: {size : 18},
        showlegend: true,
        legend: {orientation: 'v', x: 0.05, y: 0.95},
        xaxis: {title: {text: 'Download Bandwidth [Mbps]'}},
        yaxis: {dtick: 1, title: {text: 'Network Test #'}},

        // threshold line (isp_dl)
        shapes: [
          {
            type: 'line',
            yref: 'paper',
            y0: 0,
            y1: 1,
            x0: isp_dl,
            x1: isp_dl,
            line: ispLine,
          },
        ],
      },

      // other config
      {
        displayModeBar: false,
      },
    )
  },
  async load (ispRequest) {
    const networkData = await $.getJSON('trial/stats')
    const ispData = await ispRequest

    this.updateView(networkData, ispData.ookla_dl)

    this.makePlot(networkData.recent_rates, networkData.total_count, ispData.ookla_dl)
    .then(() => dataView.elementToggle.initDeferred('plots-trials'))

    return networkData
  },
}


const extWatcher = {
  enabled: false,
  installed: null,
  extDataType: 'ndt7ext',
  storageKeys: ['notInstalledDimiss', 'installedDismiss'],
  listen (event) {
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
  start () {
    window.addEventListener('message', this.listen.bind(this), false);
    setTimeout(this.timeout.bind(this), 1000);
  },
  timeout () {
    if (this.installed === null) {
      this.installed = false;
      this.updateView();
    }
  },
  updateView () {
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
  _dismiss (event) {
    // collapse notice IFF it wasn't the installation link that they clicked
    if (! event.target.href) {
      $(this).collapse('hide')

      // persist their election to dismiss this notice
      event.data.setDismiss()
    }
  },
  getDismissKey () {
      const keyIndex = Number(this.installed)

      return this.storageKeys[keyIndex]
  },
  getDismiss () {
      const storageKey = this.getDismissKey()

      return storageKey && localStorage.getItem(storageKey)
  },
  setDismiss () {
      const storageKey = this.getDismissKey()

      if (storageKey) {
        localStorage.setItem(storageKey, '1')
      }
  },
  isGoogleChrome () {
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
  isProperHost () {
    return this.hostPattern.test(window.location.hostname);
  },
  canInstall () {
    // for now don't bother them unless they're using Google Chrome
    return this.enabled && this.isProperHost() && this.isGoogleChrome();
  }
}

if (extWatcher.canInstall()) extWatcher.start()

ispStats.load()

networkStats.load(ispStats.request)

ispPlots.load()

dataView.elementToggle.init()

addEventListener('ndt7update', () => networkStats.load(ispStats.request))
