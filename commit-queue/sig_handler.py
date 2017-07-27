# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging as _logging
import signal as _signal
import threading as _threading

_OK_HANDLERS = set((
    _signal.SIG_DFL,
    _signal.SIG_IGN,
    _signal.default_int_handler,
))

# Only manipulated on the main thread, so it doesn't need a lock.
_PREV_HANDLERS = {}

_SET_SIGNALS_LOCK = _threading.Lock()
_SET_SIGNALS = set()


def _handler(signal_num, _):
  with _SET_SIGNALS_LOCK:
    _SET_SIGNALS.add(signal_num)
  _signal.signal(signal_num, _PREV_HANDLERS[signal_num])
  _logging.warn(
      '\n'
      'commit-queue will exit at the end of this processing loop.\n'
      'Hit Ctrl-C again to exit immediately.'
  )


def getTriggeredSignals():
  with _SET_SIGNALS_LOCK:
    return _SET_SIGNALS.copy()


def installHandlers(*signal_numbers):
  for signal_num in signal_numbers:
    cur_handler = _signal.getsignal(signal_num)
    if cur_handler == _handler:
      continue

    assert cur_handler in _OK_HANDLERS, \
        'A signal handler is already installed for signal %d' % signal_num

    _PREV_HANDLERS[signal_num] = cur_handler
    _signal.signal(signal_num, _handler)
