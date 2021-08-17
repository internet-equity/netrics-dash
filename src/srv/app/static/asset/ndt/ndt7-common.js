const ndt7common = {
  run_ndt: function (testName, viewUpdater, callback, assetUri) {
    const assetUrl = assetUri || '',
          updateValues = viewUpdater || (() => {}),
          done = callback || (() => {});

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
    ndt7core.run('http://netrics.local:8888/ndt7.html', assetUrl, testName, (eventName, values) => {
      // DEBUG: console.debug(eventName, values)
  
      const origin = values.Origin,
            results = values.AppInfo || null;
  
      if (eventName === 'starting') {
        console.debug('LAN bandwidth test: started');
      } else if (eventName === 'measurement') {
        recordMeasurement(origin, results);
        updateValues(lastMeasurement, testName);
      } else if (eventName === 'complete') {
        updateValues(lastMeasurement, testName, true);
        done(lastMeasurement, testName);
        console.debug('LAN bandwidth test: complete');
      }
    });
  }
};
