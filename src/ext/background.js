/*
 * Netrics Network Speed Test background extension
 *
 */

/* Meta configuration */

const DEBUG = true

const SERVER_ENV = 'rpi'  // enum: local | rpi


/* Extension configuration */

const PERIODIC_ALARM = 'cdac.netrics.wifi.periodic'

/*
 * alarm periodicity is here configured to be far more frequent than the
 * intended trial periodicity:
 *
 * 1) to make up for any inconsistency in the firing of the alarm due to
 *    browser downtime
 *
 * 2) to aid in the postponement of testing during periods of high usage
 *
 * 3) (and: see below)
 *
 */
const ALARM_PERIOD = 15    // int minutes for chrome.alarms.create
const TRIAL_PERIOD = '6h'  // period spec for /dashboard/trial/

const PAGE_COOLDOWN_PERIOD = 15  // seconds since last tab completed load

/*
 * note: background extensions are not permitted to run perpetually --
 * rather, they are throttled, and eventually suspended.
 *
 */
const RETRY_PERIOD = 3000  // int ms for setTimeout
const RETRY_MAX = 15

const KNOWN_HOSTS = SERVER_ENV == 'rpi' ? [
  'netrics.local',
  'netrics.localdomain',
] : ['localhost:8080']


/* Extension sandbox initialization */

if (! DEBUG) console.debug = (() => {});


/* Extension sandbox globals */

let deviceSniff
let trialSlot
let wifiTester


class SniffError extends Error {

  constructor (...params) {
    super(...params)

    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor)
    }

    this.name = this.constructor.name
  }

}


class UnidentifiedSoftwareError extends SniffError {

  constructor (netloc, ...params) {
    super(...params)

    this.netloc = netloc
  }

}


class SniffFailure extends SniffError {

  static #defaultMessage = 'netrics device address could not be found'

  constructor (message, ...params) {
    if (message === undefined) message = SniffFailure.#defaultMessage

    super(message, ...params)
  }

}


class SniffedNetricsDevice {

  static #hosts = KNOWN_HOSTS
  static #storageKey = 'localDashboardNetloc'

  static* #streamNetlocs () {
    yield* this.#hosts

    //
    // More? We'll see. Unclear whether raw IPs will even work....
    //
    // (This could just be an Array; however, if we are iterating over an IP
    // range, will be nice to support generator....)
    //
  }

  static async #testNetloc (netloc) {
    const response = await fetch(`http://${netloc}/dashboard/`, {method: 'HEAD'}),
          software = response.headers.get('Software');

    if (software === 'netrics-dashboard') return netloc;

    throw new UnidentifiedSoftwareError(netloc);
  }

  static* #streamTrials (netlocs) {
    for (const netloc of netlocs) {
      yield this.#testNetloc(netloc)
    }
  }

  static #getStored (storage) {
    return new Promise(resolve => {
      if (storage === localStorage) {
        resolve(localStorage.getItem(this.#storageKey))
      } else if (storage === chrome.storage.local) {
        chrome.storage.local.get(this.#storageKey, items => {
          resolve(items[this.#storageKey])
        })
      } else {
        throw new TypeError("unsupported storage backend")
      }
    })
  }

  static #setStored (storage, netloc) {
    if (storage === localStorage) {
      localStorage.setItem(this.#storageKey, netloc)
    } else if (storage === chrome.storage.local) {
      chrome.storage.local.set({
        [this.#storageKey]: netloc
      })
    } else {
      throw new TypeError("unsupported storage backend")
    }
  }

  static async sniff (storage=chrome.storage.local) {
    let netloc = await this.#getStored(storage)

    if (! netloc) {
      try {
        netloc = await Promise.any(this.#streamTrials(this.#streamNetlocs()))
      } catch (error) {
        if (error instanceof AggregateError) {
          throw new SniffFailure()
        } else {
          throw error
        }
      }

      this.#setStored(storage, netloc)
    }

    return new this(netloc)
  }

  constructor (netloc) {
    this.netloc = netloc
  }

  get dashboardUri () {
    return `http://${this.netloc}/dashboard/`
  }

  get trialUri () {
    return `http://${this.netloc}/dashboard/trial/`
  }

}


class TrialSlot {

  constructor (deviceSniff, period=TRIAL_PERIOD) {
    this.sniff = deviceSniff
    this.period = period
  }

  async #getQueryUrl () {
    const device = await this.sniff,
          url = new URL(device.trialUri);

    url.searchParams.set('active', 'on');
    url.searchParams.set('period', this.period);

    return url;
  }

  async #getUpdateUrl (ts) {
    const device = await this.sniff,
          uri = device.trialUri;

    return uri.endsWith('/') ? `${uri}${ts}` : `${uri}/${ts}`;
  }

  async isOpen () {
    const url = await this.#getQueryUrl();

    url.searchParams.set('limit', '1');

    const response = await fetch(url),
          data = response.ok ? await response.json() : null;

    return data && data.count === 0;
  }

  async createTrial () {
    const url = await this.#getQueryUrl(),
          response = await fetch(url, {method: 'POST'}),
          data = response.ok ? await response.json() : null;

    return data && data.inserted;
  }

  async updateTrial (ts, measurement) {
    const url = await this.#getUpdateUrl(ts),
          formData = new FormData();

    if (! measurement) {
      return false;
    }

    formData.append('size', measurement.NumBytes);
    formData.append('period', measurement.ElapsedTime.toFixed());

    const response = await fetch(url, {method: 'PUT', body: formData});

    return response.ok;
  }

}


class WifiTester {

  constructor (
    slot,
    alarmName=PERIODIC_ALARM,
    alarmPeriod=ALARM_PERIOD,
    pageCooldownPeriod=PAGE_COOLDOWN_PERIOD,
    retryPeriod=RETRY_PERIOD,
    retryMax=RETRY_MAX
  ) {
    console.debug('WifiTester: construction');

    this.alarmName = alarmName;
    this.alarmPeriod = alarmPeriod;
    this.pageCooldownPeriod = pageCooldownPeriod;
    this.retryPeriod = retryPeriod;
    this.retryMax = retryMax;

    this.slot = slot;
  }

  registerAll () {
    this.registerAlarmListener();
    this.registerAlarm();

    this.registerClickListener();
    this.registerTabListener();
    this.registerInstallationListener();
  }

  registerInstallationListener () {
    /* Register extension installation handler.
     */
    console.debug('WifiTester: add installation listener');

    chrome.runtime.onInstalled.addListener(({reason}) => {
      if (reason === chrome.runtime.OnInstalledReason.INSTALL) {
        // NOTE: this could also be a welcome HTML page
        chrome.notifications.create('installed', {
          type: 'basic',
          title: "Installed | Home Network Speed Test",
          message: "• Your browser will now attempt to detect your Network Measurement Device and open its Dashboard.\n" +
                   "• In the future you may access the Dashboard by clicking the Speed Test extension icon in your browser toolbar.\n" +
                   "• Your browser will also perform automated tests of your home network. You can view the results in the Dashboard.",
          iconUrl: 'img/wifi-128.png',
          priority: 1
        });

        this.openDashboard(true);
      }
    });
  }

  registerTabListener () {
    /* Register tab status handler.
     */
    console.debug('WifiTester: add tab listener');

    chrome.tabs.onUpdated.addListener((_tabId, changeInfo, _tab) => {
      if (changeInfo.status === 'complete') {
        chrome.storage.local.set({'lastTabComplete': Date.now()});
      }
    });
  }

  registerClickListener () {
    /* Register toolbar click handler.
     */
    console.debug('WifiTester: add click listener');

    chrome.browserAction.onClicked.addListener(this.openDashboard.bind(this, false));
  }

  registerAlarmListener () {
    /* Register alarm handler.
     */
    console.debug('WifiTester: add alarm listener');

    // event listeners do not appear durable over sleeps/updates/resets/etc. --
    // (i.e. this appears either necessary or idempotent as is)
    chrome.alarms.onAlarm.addListener(this.runTest.bind(this));
  }

  registerAlarm () {
    /* Create/update alarm to wake up extension periodically.
     */
    console.debug('WifiTester: put alarm');

    // alarms appear durable over sleeps/updates.
    // this *could* most likely be made a simple put/update one-liner;
    // but, left as is for clarity, safety and/or further investigation.
    chrome.alarms.get(this.alarmName, this.#tryRegisterAlarm.bind(this));
  }

  #tryRegisterAlarm (alarm) {
    if (alarm) {
      if (alarm.periodInMinutes === this.alarmPeriod) {
        console.debug('WifiTester: put alarm: alarm already exists: done:', alarm.name);
        return;
      }

      console.debug('WifiTester: put alarm: alarm already exists: resetting:', alarm.name);

      chrome.alarms.clear(alarm.name, wasCleared => {
        if (wasCleared) {
          console.debug('WifiTester: put alarm: alarm cleared:', alarm.name);
        } else {
          console.error('WifiTester: put alarm: alarm not cleared:', alarm.name);
        }
      });
    }

    chrome.alarms.create(this.alarmName, {
      delayInMinutes: 1,
      periodInMinutes: this.alarmPeriod
    });

    console.debug('WifiTester: put alarm: alarm created:', this.alarmName);
  }

  async openDashboard (reload=false) {
    /* Open a tab for the Local Dashboard.
     *
     * If such a tab is already open, this is given focus.
     *
     * Otherwise, a new tab is created.
     *
     */
    let device;

    try {
      device = await this.slot.sniff;
    } catch (error) {
      if (error instanceof SniffFailure) {
        chrome.notifications.create('openDashboard-SniffFailure', {
          type: 'basic',
          title: "Error | Home Network Speed Test",
          message: "Network Measurement Device could not be found. Please ensure:\n\n" +
                   "1) the device is connected to power and connected to your network\n\n" +
                   "2) your computer is connected to your network (\"online\")",
          iconUrl: 'img/wifi-128.png',
          priority: 2,
          requireInteraction: true,
        });
        console.error('WifiTester:', error);
        return;
      } else {
        throw error;
      }
    }

    const dashboardInfo = {url: device.dashboardUri};

    // NOTE: we should be able to see *our* pages (called out in manifest)
    // even without the special "tabs" permission
    chrome.tabs.query(dashboardInfo, tabs => {
      const dashboardTab = tabs[0];

      if (dashboardTab) {
        if (reload) {
          chrome.tabs.reload(dashboardTab.id);
        }
        chrome.tabs.highlight({
          tabs: dashboardTab.index,
          windowId: dashboardTab.windowId,
        });
        chrome.windows.update(dashboardTab.windowId, {focused: true});
      } else {
        chrome.tabs.create(dashboardInfo);
      }
    });
  }

  async runTest (/* ... */) {
    /* Negotiate WiFi testing with server and initiate test in response to an alarm.
     */
    try {
      await this.#tryTest(...arguments);
    } catch (error) {
      console.error('WifiTester:', error);
    }
  }

  async #tryTest (alarm, retryCount=0) {
    if (retryCount === 0) {
      console.debug('WifiTester: handling alarm:', alarm);
    } else {
      console.debug('WifiTester: handling retry:', retryCount);
    }

    const isOpen = await this.slot.isOpen();

    if (! isOpen) {
      // most likely it hasn't been TRIAL_PERIOD since last test (or there's an active test) --
      // in which case: bail
      console.debug('WifiTester: no open trial slot: done');
      return;
    }

    const browserInactive = await this.#browserInactive();

    if (! browserInactive) {
      // it is time to test -- BUT the browser appears active --
      // rather than wait for next alarm in ALARM_PERIOD, retry in RETRY_PERIOD:
      if (retryCount < this.retryMax) {
        //
        // NOTE: Should alarm trigger clear this timer, on off-chance could continue that long?
        //
        // Overlap seems fantastically unlikely --
        // especially because browser should unload the extension process --
        // AND, lock acquisition should protect against any problem --
        // *but*, could ensure this....
        //
        console.debug('WifiTester: browser active: will retry');
        setTimeout(this.runTest.bind(this, alarm, retryCount + 1), this.retryPeriod);
      } else {
        console.debug('WifiTester: browser active: done');
      }

      return;
    }

    // looks all clear -- acquire lock & trial record:
    const trial = await this.slot.createTrial();

    if (! trial) {
      // a competitor might've beaten us to the punch!
      console.debug('WifiTester: no open trial slot (race?): done');
      return;
    }

    // let's test! and then record the result:
    const device = await this.slot.sniff;

    this.#beforeTest();

    ndt7common.run_ndt({
      testName: 'download',
      testHost: device.netloc,
      done: this.#afterTest.bind(this, trial),
    });
  }

  async #browserInactive () {
    const noneRecentlyLoaded_ = this.#noneRecentlyLoaded(),
          noneCurrentlyLoading_ = this.#noneCurrentlyLoading();

    // await/resolve promises separately to ensure they are executed in parallel
    const noneRecentlyLoaded = await noneRecentlyLoaded_,
          noneCurrentlyLoading = await noneCurrentlyLoading_;

    console.debug('WifiTester: noneRecentlyLoaded=%o noneCurrentlyLoading=%o',
                  noneRecentlyLoaded,
                  noneCurrentlyLoading);

    return noneRecentlyLoaded && noneCurrentlyLoading;
  }

  // chrome doesn't return promises until MV3 :(
  #noneRecentlyLoaded () {
    return new Promise(resolve => {
      chrome.storage.local.get('lastTabComplete', items => {
        const lastTabComplete = items.lastTabComplete;

        resolve(
          lastTabComplete === undefined ||
          (Date.now() - lastTabComplete) / 1000 >= this.pageCooldownPeriod
        );
      });
    });
  }

  #noneCurrentlyLoading () {
    return new Promise(resolve => {
      chrome.tabs.query({status: 'loading'}, tabs => {
        resolve(tabs.length === 0);
      });
    });
  }

  #beforeTest () {
    // set a badge of the unicode up-down arrow
    chrome.browserAction.setBadgeText({text: '\u{02195}'});

    // append the word "active" to the title tooltip
    chrome.browserAction.getTitle({}, defaultTitle => {
      const activeTitle = `${defaultTitle}: active`;

      chrome.browserAction.setTitle({title: activeTitle});
    });
  }

  #afterTest (trial, measurement) {
    // update the trial record with the test results
    this.slot.updateTrial(trial.ts, measurement);

    // reset the title tooltip to its configured default
    chrome.browserAction.getTitle({}, activeTitle => {
      const defaultTitle = activeTitle.replace(/: active$/, '');

      chrome.browserAction.setTitle({title: defaultTitle});
    });

    // clear the badge
    chrome.browserAction.setBadgeText({text: ''});
  }

}


/* Extension initialization */

deviceSniff = SniffedNetricsDevice.sniff();

trialSlot = new TrialSlot(deviceSniff);

wifiTester = new WifiTester(trialSlot);

wifiTester.registerAll();
