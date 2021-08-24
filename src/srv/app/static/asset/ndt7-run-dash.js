const ndt7view = {
  compare_speeds: function (a, b) {
    if      (a < b * 0.75) {
      return ['less than', 'bad', 'bad'];
    } else if (a > b * 1.25) {
      return ["greater than", "good", "good"];
    } else {
      return ["similar to", "not great", "ok"];
    }
  },

  post_loading: function (elem) {
    elem.querySelectorAll('.loading').forEach(
      function (elem) {
          elem.classList.remove('loading');
          elem.classList.add('loading-done');
      }
    );
  },

  update_values: function (info, tag, complete) {
    if (!info) {
      if (complete) {
        const failure = document.getElementById('wifi-failure');
  
        failure.classList.remove('d-none');
        this.post_loading(failure.parentElement);
      }
  
      return;
    }
  
    const elapsed = info.ElapsedTime / 1e06     /* second */
    let speed = info.NumBytes / elapsed         /* B/s    */
    speed *= 8                                     /* bit/s  */
    speed /= 1e06                                  /* Mbit/s */
    speed = speed.toFixed(1)
  
    const el = document.getElementById("wifi_bw"),
          dl = document.getElementById("ookla_dl"),
          dl_value = parseFloat(dl.innerHTML);
  
    el.innerHTML = speed;
  
    const pardiv = el.parentElement
    pardiv.classList.remove("bad")
    pardiv.classList.remove("ok")
    pardiv.classList.remove("good")
  
    const [op, desc, label] = this.compare_speeds(speed, dl_value);
    pardiv.classList.add(label);
  
    if (complete) {
      const txt1 = document.getElementById("text_wifi_interp1")
      const txt2 = document.getElementById("text_wifi_interp2")
      const paragraph = txt1.parentElement
      const section = paragraph.parentElement
  
      txt1.innerHTML = op;
      txt2.innerHTML = desc;
  
      paragraph.classList.remove('d-none');
      this.post_loading(section);
    }
  }
};

const ndt7run = {
  ndtTestHost: window.location.host,
  ndtAssetPath: '/dashboard/asset/ndt/',

  runNdt: function (testName, viewUpdater, callback) {
    ndt7common.run_ndt({
      testName: testName,
      updateValues: viewUpdater,
      done: callback,
      testHost: this.ndtTestHost,
      assetUrl: this.ndtAssetPath,
    });
  },

  sendTrial: function (callback, measurement, testName) {
    if (measurement && Number.isInteger(this.ts)) {
      $.ajax(`trial/${this.ts}`, {
        method: 'PUT',
        data: {
          size: measurement.NumBytes,
          period: measurement.ElapsedTime.toFixed()
        }
      });
    } else {
      console.error('bad trial object %o or results %o', this, measurement);
    }
  
    if (callback !== undefined) {
      callback(measurement, testName);
    }
  },

  run_download: function (callback) {
    $.post('trial/?active=on', null, 'json')
    .done(result => this.runNdt(
      'download',
      ndt7view.update_values.bind(ndt7view),
      this.sendTrial.bind(result.inserted, callback)
    ))
    .fail(() => {
      console.error('LAN bandwidth test could not be started');
      ndt7view.update_values(null, 'download', true);
    });
  },

  run_upload: function (callback) {
    this.runNdt(
      'upload',
      ndt7view.update_values.bind(ndt7view),
      callback
    );
  },
  
  run_both: function () {
    this.run_download(() => this.run_upload())
  }
};

ndt7run.run_download()
