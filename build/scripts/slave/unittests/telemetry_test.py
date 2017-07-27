#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for telemetry.py.

This is a basic check that telemetry.py forms commands properly.

"""

import json
import os
import sys
import unittest

import test_env  # pylint: disable=W0403,W0611

from common import chromium_utils


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def runScript(*args, **kwargs):
  """Ensures scripts have a proper PYTHONPATH."""
  env = os.environ.copy()
  env['PYTHONPATH'] = os.pathsep.join(sys.path)
  return chromium_utils.RunCommand(*args, env=env, **kwargs)


class FilterCapture(chromium_utils.RunCommandFilter):
  """Captures the text and places it into an array."""
  def __init__(self):
    chromium_utils.RunCommandFilter.__init__(self)
    self.text = []

  def FilterLine(self, line):
    self.text.append(line.rstrip())

  def FilterDone(self, text):
    self.text.append(text)

class TelemetryTest(unittest.TestCase):
  """Holds tests for telemetry script."""

  @staticmethod
  def _GetDefaultFactoryProperties():
    fp = {}
    fp['page_set'] = 'sunspider.json'
    fp['build_dir'] = 'src/build'
    fp['test_name'] = 'sunspider'
    fp['target'] = 'Release'
    fp['target_os'] = 'android'
    fp['target_platform'] = 'linux2'
    fp['step_name'] = 'sunspider'
    fp['show_perf_results'] = True
    fp['perf_id'] = 'android-gn'
    return fp

  def setUp(self):
    super(TelemetryTest, self).setUp()

    self.telemetry = os.path.join(SCRIPT_DIR, '..', 'telemetry.py')
    self.capture = FilterCapture()

  def testSimpleCommand(self):
    fp = self._GetDefaultFactoryProperties()

    cmd = [self.telemetry, '--print-cmd',
           '--factory-properties=%s' % json.dumps(fp)]

    ret = runScript(cmd, filter_obj=self.capture, print_cmd=False)
    self.assertEqual(ret, 0)

    runtest = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'runtest.py'))

    expectedText = (['\'adb\' \'root\'',
        '\'adb\' \'wait-for-device\'',
        '\'%s\' ' % sys.executable +
        '\'%s\' \'--run-python-script\' \'--target\' \'Release\' ' % runtest +
            '\'--build-dir\' \'src/build\' \'--no-xvfb\' ' +
            '\'--factory-properties=' +
            '{"page_set": "sunspider.json", "target": "Release", ' +
            '"build_dir": "src/build", "perf_id": "android-gn", ' +
            '"step_name": "sunspider", "test_name": "sunspider", ' +
            '"target_platform": "linux2", "target_os": "android", ' +
            '"show_perf_results": true}\' ' +
            '\'src/tools/perf/run_measurement\' \'-v\' ' +
            '\'--browser=android-chromium-testshell\' \'sunspider\' ' +
            '\'src/tools/perf/page_sets/sunspider.json\''
        ])

    self.assertEqual(expectedText, self.capture.text)

  def testPageRepeat(self):
    fp = self._GetDefaultFactoryProperties()
    fp['page_repeat'] = 20

    cmd = [self.telemetry, '--print-cmd',
           '--factory-properties=%s' % json.dumps(fp)]

    ret = runScript(cmd, filter_obj=self.capture, print_cmd=False)
    self.assertEqual(ret, 0)

    runtest = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'runtest.py'))

    expectedText = (['\'adb\' \'root\'',
        '\'adb\' \'wait-for-device\'',
        '\'%s\' ' % sys.executable +
        '\'%s\' \'--run-python-script\' \'--target\' \'Release\' ' % runtest +
            '\'--build-dir\' \'src/build\' \'--no-xvfb\' ' +
            '\'--factory-properties=' +
            '{"page_set": "sunspider.json", "target": "Release", ' +
            '"build_dir": "src/build", "perf_id": "android-gn", ' +
            '"step_name": "sunspider", "test_name": "sunspider", ' +
            '"page_repeat": 20, '+
            '"target_platform": "linux2", "target_os": "android", ' +
            '"show_perf_results": true}\' ' +
            '\'src/tools/perf/run_measurement\' \'-v\' ' +
            '\'--page-repeat=20\' '+
            '\'--browser=android-chromium-testshell\' \'sunspider\' ' +
            '\'src/tools/perf/page_sets/sunspider.json\''
        ])

    self.assertEqual(expectedText, self.capture.text)

  def testPageRepeatMozJS(self):
    fp = self._GetDefaultFactoryProperties()
    fp['page_repeat'] = 20
    fp['page_set'] = 'moz.json'
    fp['target_os'] = 'mac'

    cmd = [self.telemetry, '--print-cmd',
           '--factory-properties=%s' % json.dumps(fp)]

    ret = runScript(cmd, filter_obj=self.capture, print_cmd=False)
    self.assertEqual(ret, 0)

    capture_text = self.capture.text
    self.assertEqual(len(capture_text), 4)
    for line in capture_text:
      self.assertEqual(line.count('moz.json'), 2)

  def testWithoutPageSet(self):
    fp = self._GetDefaultFactoryProperties()
    fp['page_set'] = None

    cmd = [self.telemetry, '--print-cmd',
           '--factory-properties=%s' % json.dumps(fp)]

    ret = runScript(cmd, filter_obj=self.capture, print_cmd=False)
    self.assertEqual(ret, 0)

    runtest = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'runtest.py'))

    expectedText = (['\'adb\' \'root\'',
        '\'adb\' \'wait-for-device\'',
        '\'%s\' ' % sys.executable +
        '\'%s\' \'--run-python-script\' \'--target\' \'Release\' ' % runtest +
            '\'--build-dir\' \'src/build\' \'--no-xvfb\' ' +
            '\'--factory-properties=' +
            '{"page_set": null, "target": "Release", ' +
            '"build_dir": "src/build", "perf_id": "android-gn", ' +
            '"step_name": "sunspider", "test_name": "sunspider", ' +
            '"target_platform": "linux2", "target_os": "android", ' +
            '"show_perf_results": true}\' ' +
            '\'src/tools/perf/run_measurement\' \'-v\' ' +
            '\'--browser=android-chromium-testshell\' \'sunspider\''
        ])

    self.assertEqual(expectedText, self.capture.text)

if __name__ == '__main__':
  unittest.main()
