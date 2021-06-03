/* jshint esversion: 6, asi: true */
/* globals ndt7core */

function update_values(info, tag) {

  const elapsed = info.ElapsedTime / 1e06     /* second */
  let speed = info.NumBytes / elapsed         /* B/s    */
  speed *= 8                                     /* bit/s  */
  speed /= 1e06                                  /* Mbit/s */
  speed = speed.toFixed(1)

  const dl= document.getElementById("ookla_dl")
  dl_value = parseFloat(dl.innerHTML)

  const el = document.getElementById("wifi_bw")

  el.innerHTML = speed

  pardiv = el.parentElement
  pardiv.classList.remove("bad")
  pardiv.classList.remove("ok")
  pardiv.classList.remove("good")

  const txt1 = document.getElementById("text_wifi_interp1")
  const txt2 = document.getElementById("text_wifi_interp2")

  if      (speed < dl_value * 0.75) {
    pardiv.classList.add("bad");
    txt1.innerHTML = "less than"
    txt2.innerHTML = "bad"
  } else if (speed > dl_value * 1.25) {
    pardiv.classList.add("good");
    txt1.innerHTML = "greater than"
    txt2.innerHTML = "good"
  } else {
    pardiv.classList.add("ok");
    txt1.innerHTML = "similar to"
    txt2.innerHTML = "not great"
  }

}

function run_ndt(testName, callback) {
  ndt7core.run("https://192.168.1.5:4443/ndt7.html", testName, function(ev, val) {
    // console.log(ev, val)
    if (ev === 'complete') {
      if (callback !== undefined) {
        callback()
      }
      console.log("ALL COMPLETE")
      return
    }
    if (ev === 'measurement' && val.AppInfo !== undefined &&
        val.Origin === 'client') {
      update_values(val.AppInfo, testName)
    }
  })
}

function run_download(callback) {
  run_ndt('download', callback)
}

function run_upload(callback) {
  run_ndt('upload', callback)
}

function run_both() {
  run_download(function() { run_upload(); })
}

run_download()


