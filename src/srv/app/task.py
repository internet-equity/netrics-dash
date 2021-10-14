"""Background task management."""
import queue as q
import threading
import time

import schedule
from loguru import logger as log


class TaskThread(threading.Thread):

    @classmethod
    def launch(cls, *args, **kwargs):
        worker = cls(*args, **kwargs)
        worker.start()
        return worker

    @log.catch
    def run(self):
        self()


class ScheduleExecutioner(TaskThread):
    """Execute pending jobs at -- *i.e.* with a resolution of -- each
    elapsed time interval.

    Please note that it is *intended behavior* that missed jobs are not
    run. For example, if you've registered a job that should run every
    minute and you set a continuous run interval of one hour then your
    job won't be run 60 times at each interval but only once.

    """
    def __init__(self, interval=1, stop_event=None):
        super().__init__()
        self.interval = interval
        self.stop_event = threading.Event() if stop_event is None else stop_event

    def __call__(self):
        while not self.stop_event.is_set():
            self.run_pending()
            time.sleep(self.interval)

    @staticmethod
    def run_pending():
        # schedule.run_pending() is here decomposed merely to add info logging
        # missing from schedule -- this method should otherwise be entirely
        # replaceable with:
        #
        #    schedule.run_pending()
        #
        runnable_jobs = (job for job in schedule.default_scheduler.jobs if job.should_run)
        for job in sorted(runnable_jobs):
            schedule.default_scheduler._run_job(job)
            log.info('scheduled jobs | ran {}', job)


class ItemExecutioner(TaskThread):
    """Execute enqueued tasks."""

    def __init__(self, interval=1, max_items=-1, queue=None, stop_event=None):
        super().__init__()
        self.interval = interval
        self.max_items = max_items
        self.queue = q.SimpleQueue() if queue is None else queue
        self.stop_event = threading.Event() if stop_event is None else stop_event

    def __call__(self):
        item_count = 0

        while item_count != self.max_items and not self.stop_event.is_set():
            try:
                item = self.queue.get(timeout=self.interval)
            except q.Empty:
                pass
            else:
                item.run()
                log.info('enqueued tasks | ran {}', item)

                item_count += 1
                if item_count == self.max_items:
                    log.debug('enqueued tasks | item limit reached: shutting down')
