/* jshint esversion: 6, asi: true */
/* globals ndt7core */

function update_values (info, tag, complete) {
  if (!info) {
    if (complete) {
      const failure = document.getElementById('wifi-failure');

      failure.classList.remove('d-none');
      post_loading(failure.parentElement);
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

  const [op, desc, label] = compare_speeds(speed, dl_value);
  pardiv.classList.add(label);

  if (complete) {
    const txt1 = document.getElementById("text_wifi_interp1")
    const txt2 = document.getElementById("text_wifi_interp2")
    const paragraph = txt1.parentElement
    const section = paragraph.parentElement

    txt1.innerHTML = op;
    txt2.innerHTML = desc;

    paragraph.classList.remove('d-none');
    post_loading(section);
  }
}

function post_loading (elem) {
  elem.querySelectorAll('.loading').forEach(
    function (elem) {
        elem.classList.remove('loading');
        elem.classList.add('loading-done');
    }
  );
}

function compare_speeds(a, b) {
  if      (a < b * 0.75) {
    return ['less than', 'bad', 'bad'];
  } else if (a > b * 1.25) {
    return ["greater than", "good", "good"];
  } else {
    return ["similar to", "not great", "ok"];
  }
}

function run_ndt (testName, callback) {
  let lastMeasurement = null;

  function recordMeasurement (origin, results) {
    if (origin === 'client') {
      lastMeasurement = results;
    }
  }

  /*
   * HTTPS would be nice -- but disabling for now as user must manually accept certificate!
   */
  // FIXME: can't assume netrics.local!
  ndt7core.run('http://netrics.local:8888/ndt7.html', testName, function (eventName, values) {
    // DEBUG: console.debug(eventName, values)

    const origin = values.Origin,
          results = values.AppInfo || null;

    if (eventName === 'starting') {
      console.debug('LAN bandwidth test started');
    } else if (eventName === 'measurement') {
      recordMeasurement(origin, results);
      update_values(lastMeasurement, testName);
    } else if (eventName === 'complete') {
      update_values(lastMeasurement, testName, true);

      if (callback !== undefined) {
        callback(lastMeasurement, testName);
      }

      console.debug('LAN bandwidth test complete');
    }
  });
}

function send_download (callback, measurement, testName) {
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
}

function run_download (callback) {
  $.post('trial/?active=on', null, 'json')
  .done(result => {
    run_ndt('download', send_download.bind(result.inserted, callback))
  })
  .fail(() => {
    console.error('LAN bandwidth test could not be started');
    update_values(null, 'download', true);
  });
}

function run_upload (callback) {
  run_ndt('upload', callback)
}

function run_both () {
  run_download(() => run_upload())
}

run_download()
