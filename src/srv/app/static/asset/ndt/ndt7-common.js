const ndt7common = (function () {
  const noop = (() => {});

  return {
    run_ndt: ({testName, testHost, assetUrl='', updateValues=noop, done=noop}) => {
      let hostname = testHost.match(/^([^:]+)(?::|$)/)[1];

      if (hostname === 'localhost' || hostname === '0.0.0.0') {
        const qs = new URLSearchParams(location.search);

        if (qs.has('ndtHost')) {
          hostname = qs.get('ndtHost');
        }
      }

      let lastMeasurement = null;

      function recordMeasurement (origin, results) {
        if (origin === 'client') {
          lastMeasurement = results;
        }
      }

      // NOTE: HTTPS would be nice -- but disabling for now as user must manually accept certificate!
      ndt7core.run(`http://${hostname}:8888/ndt7.html`, assetUrl, testName, (eventName, values) => {
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
})();
