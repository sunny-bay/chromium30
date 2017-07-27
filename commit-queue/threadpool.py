# coding=utf8
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Thread pool with task queues to make work items asynchronous."""

import logging
import Queue
import threading
import sys


class ThreadPool(object):
  def __init__(self, num_threads):
    self._tasks = Queue.Queue()
    self._lock = threading.Lock()
    self._outputs = []
    self._exceptions = []
    self._workers = [
      threading.Thread(target=self._run, name='worker-%d' % i)
      for i in range(num_threads)
    ]
    for w in self._workers:
      w.daemon = True
      w.start()

  def add_task(self, function, *args, **kwargs):
    self._tasks.put((function, args, kwargs))

  def join(self):
    """Extracts all the results from each threads unordered."""
    self._tasks.join()
    with self._lock:
      # Look for exceptions.
      if self._exceptions:
        exception = self._exceptions.pop(0)
        raise exception[0], exception[1], exception[2]
      out = self._outputs
      self._outputs = []
    return out

  def close(self):
    """Closes all the threads."""
    for _ in range(len(self._workers)):
      # Enqueueing None causes the worker to stop.
      self._tasks.put(None)
    for t in self._workers:
      t.join()

  def _run(self):
    """Runs until a None task is queued."""
    while True:
      task = self._tasks.get()
      if task is None:
        # We're done.
        return
      try:
        # The first item is the index.
        func, args, kwargs = task
        self._outputs.append(func(*args, **kwargs))
      except Exception, e:
        task_str = "<unserializable>"
        try:
          task_str = repr(task)
        except:  # pylint: disable=W0702
          pass
        logging.error('Caught exception while running %s! %s' % (task_str, e))
        self._exceptions.append(sys.exc_info())
      finally:
        self._tasks.task_done()
