#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for classes in annotator.py."""

import cStringIO
import json
import os
import sys
import tempfile
import unittest

import test_env  # pylint: disable=W0611

from common import annotator
from common import chromium_utils


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class FilterCapture(chromium_utils.RunCommandFilter):
  """Captures the text and places it into an array."""
  def __init__(self):
    chromium_utils.RunCommandFilter.__init__(self)
    self.text = []

  def FilterLine(self, line):
    self.text.append(line.rstrip())

  def FilterDone(self, text):
    self.text.append(text)


class TestAnnotationStreams(unittest.TestCase):
  def setUp(self):
    self.buf = cStringIO.StringIO()

  def _getLines(self):
    """Return list of non-empty lines in output."""
    return [line for line in self.buf.getvalue().rstrip().split('\n') if line]

  def testBasicUsage(self):
    stream = annotator.StructuredAnnotationStream(stream=self.buf)
    with stream.step('one') as _:
      pass
    with stream.step('two') as _:
      pass

    result = [
        '@@@SEED_STEP one@@@',
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_STARTED@@@',
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_CLOSED@@@',
        '@@@SEED_STEP two@@@',
        '@@@STEP_CURSOR two@@@',
        '@@@STEP_STARTED@@@',
        '@@@STEP_CURSOR two@@@',
        '@@@STEP_CLOSED@@@',
    ]

    self.assertEquals(result, self._getLines())

  def testStepAnnotations(self):
    stream = annotator.StructuredAnnotationStream(stream=self.buf)
    with stream.step('one') as s:
      s.step_warnings()
      s.step_failure()
      s.step_exception()
      s.step_clear()
      s.step_summary_clear()
      s.step_text('hello')
      s.step_summary_text('hello!')
      s.step_log_line('mylog', 'test')
      s.step_log_end('mylog')
      s.step_log_line('myperflog', 'perf data')
      s.step_log_end_perf('myperflog', 'dashboardname')
      s.write_log_lines('full_log', ['line one', 'line two'])
      s.write_log_lines('full_perf_log', ['perf line one', 'perf line two'],
                        perf='full_perf')

    result = [
        '@@@SEED_STEP one@@@',
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_STARTED@@@',
        '@@@STEP_WARNINGS@@@',
        '@@@STEP_FAILURE@@@',
        '@@@STEP_EXCEPTION@@@',
        '@@@STEP_CLEAR@@@',
        '@@@STEP_SUMMARY_CLEAR@@@',
        '@@@STEP_TEXT@hello@@@',
        '@@@STEP_SUMMARY_TEXT@hello!@@@',
        '@@@STEP_LOG_LINE@mylog@test@@@',
        '@@@STEP_LOG_END@mylog@@@',
        '@@@STEP_LOG_LINE@myperflog@perf data@@@',
        '@@@STEP_LOG_END_PERF@myperflog@dashboardname@@@',
        '@@@STEP_LOG_LINE@full_log@line one@@@',
        '@@@STEP_LOG_LINE@full_log@line two@@@',
        '@@@STEP_LOG_END@full_log@@@',
        '@@@STEP_LOG_LINE@full_perf_log@perf line one@@@',
        '@@@STEP_LOG_LINE@full_perf_log@perf line two@@@',
        '@@@STEP_LOG_END_PERF@full_perf_log@full_perf@@@',
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_CLOSED@@@',
    ]

    self.assertEquals(result, self._getLines())

  def testSeedStep(self):
    steps = ['one', 'two']
    stream = annotator.StructuredAnnotationStream(seed_steps=steps,
                                                  stream=self.buf)
    with stream.step('one'):
      pass
    with stream.step('two'):
      pass

    result = [
        '@@@SEED_STEP one@@@',
        '@@@SEED_STEP two@@@',
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_STARTED@@@',
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_CLOSED@@@',
        '@@@STEP_CURSOR two@@@',
        '@@@STEP_STARTED@@@',
        '@@@STEP_CURSOR two@@@',
        '@@@STEP_CLOSED@@@'
    ]

    self.assertEquals(result, self._getLines())

  def testSeedStepSkip(self):
    steps = ['one', 'two', 'three']
    stream = annotator.StructuredAnnotationStream(seed_steps=steps,
                                                  stream=self.buf)
    with stream.step('one'):
      pass
    with stream.step('three'):
      pass
    with stream.step('two'):
      pass

    result = [
        '@@@SEED_STEP one@@@',
        '@@@SEED_STEP two@@@',
        '@@@SEED_STEP three@@@',
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_STARTED@@@',
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_CLOSED@@@',
        '@@@STEP_CURSOR three@@@',
        '@@@STEP_STARTED@@@',
        '@@@STEP_CURSOR three@@@',
        '@@@STEP_CLOSED@@@',
        '@@@SEED_STEP two@@@',
        '@@@STEP_CURSOR two@@@',
        '@@@STEP_STARTED@@@',
        '@@@STEP_CURSOR two@@@',
        '@@@STEP_CLOSED@@@',
    ]

    self.assertEquals(result, self._getLines())

  def testException(self):
    stream = annotator.StructuredAnnotationStream(stream=self.buf)

    def dummy_func():
      with stream.step('one'):
        raise Exception('oh no!')
    self.assertRaises(Exception, dummy_func)

    log_string = '@@@STEP_LOG_LINE@exception'
    exception = any(line.startswith(log_string) for line in self._getLines())
    self.assertTrue(exception)

  def testNoNesting(self):
    stream = annotator.StructuredAnnotationStream(stream=self.buf)

    def dummy_func():
      with stream.step('one'):
        with stream.step('two'):
          pass
    self.assertRaises(Exception, dummy_func)

  def testProtectedStartStop(self):
    stream = annotator.StructuredAnnotationStream(stream=self.buf)

    def dummy_func():
      with stream.step('one') as s:
        s.step_started()
    self.assertRaises(AttributeError, dummy_func)

    def dummy_func2():
      with stream.step('two') as s:
        s.step_closed()
    self.assertRaises(AttributeError, dummy_func2)

  def testDupLogs(self):
    stream = annotator.StructuredAnnotationStream(stream=self.buf)

    with stream.step('one') as s:
      lines = ['one', 'two']
      s.write_log_lines('mylog', lines)
      self.assertRaises(ValueError, s.write_log_lines, 'mylog', lines)

  def testAdvanced(self):
    step = annotator.AdvancedAnnotationStep(stream=self.buf, flush_before=None)
    stream = annotator.AdvancedAnnotationStream(stream=self.buf,
                                                flush_before=None)
    stream.seed_step('one')
    stream.seed_step('two')
    stream.step_cursor('one')
    step.step_started()
    stream.step_cursor('two')
    step.step_started()
    stream.step_cursor('one')
    step.step_closed()
    stream.step_cursor('two')
    step.step_closed()

    result = [
        '@@@SEED_STEP one@@@',
        '@@@SEED_STEP two@@@',
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_STARTED@@@',
        '@@@STEP_CURSOR two@@@',
        '@@@STEP_STARTED@@@',
        '@@@STEP_CURSOR one@@@',
        '@@@STEP_CLOSED@@@',
        '@@@STEP_CURSOR two@@@',
        '@@@STEP_CLOSED@@@',
    ]

    self.assertEquals(result, self._getLines())


def _synthesizeCmd(args):
  basecmd = [sys.executable, '-c']
  basecmd.extend(args)
  return basecmd


class TestExecution(unittest.TestCase):
  def setUp(self):
    self.capture = FilterCapture()
    self.tempfd, self.tempfn = tempfile.mkstemp()
    self.temp = os.fdopen(self.tempfd, 'wb')
    self.script = os.path.join(SCRIPT_DIR, os.pardir, 'annotator.py')

  def tearDown(self):
    self.temp.close()
    if os.path.exists(self.tempfn):
      os.remove(self.tempfn)

  def _runAnnotator(self, cmdlist, env=None):
    json.dump(cmdlist, self.temp)
    self.temp.close()
    cmd = [sys.executable, self.script, self.tempfn]
    cmd_env = os.environ.copy()
    cmd_env['PYTHONPATH'] = os.pathsep.join(sys.path)
    if env:
      cmd_env.update(env)
    return chromium_utils.RunCommand(cmd, filter_obj=self.capture, env=cmd_env,
                                     print_cmd=False)

  def testSimpleExecution(self):
    cmdlist = [{'name': 'one', 'cmd': _synthesizeCmd(['print \'hello!\''])},
               {'name': 'two', 'cmd': _synthesizeCmd(['print \'yo!\''])}]

    ret = self._runAnnotator(cmdlist)

    self.assertEquals(ret, 0)

    preamble = [
        '@@@SEED_STEP one@@@',
        '',
        '@@@SEED_STEP two@@@',
    ]
    step_one_header = [
        '@@@STEP_CURSOR one@@@',
        '',
        '@@@STEP_STARTED@@@',
        '',
        sys.executable + " -c print 'hello!'",
        'in dir %s:' % os.getcwd(),
        ' allow_subannotations: False',
        ' always_run: False',
        ' build_failure: False',
        ' cmd: [' + repr(sys.executable) + ', \'-c\', "print \'hello!\'"]',
        ' followup_fn: default_followup(...)',
        ' name: one',
        ' skip: False',
        'full environment:',
    ]
    step_one_result = [
        'hello!',
        '',
        '@@@STEP_CURSOR one@@@',
        '',
        '@@@STEP_CLOSED@@@',
    ]
    step_two_header = [
        '@@@STEP_CURSOR two@@@',
        '',
        '@@@STEP_STARTED@@@',
        '',
        sys.executable + " -c print 'yo!'",
        'in dir %s:' % os.getcwd(),
        ' allow_subannotations: False',
        ' always_run: False',
        ' build_failure: False',
        ' cmd: [' + repr(sys.executable) + ', \'-c\', "print \'yo!\'"]',
        ' followup_fn: default_followup(...)',
        ' name: two',
        ' skip: False',
        'full environment:',
    ]
    step_two_result = [
        'yo!',
        '',
        '@@@STEP_CURSOR two@@@',
        '',
        '@@@STEP_CLOSED@@@',
    ]

    def has_sublist(whole, part):
      n = len(part)
      return any((part == whole[i:i+n]) for i in xrange(len(whole) - n+1))

    self.assertTrue(has_sublist(self.capture.text, preamble))
    self.assertTrue(has_sublist(self.capture.text, step_one_header))
    self.assertTrue(has_sublist(self.capture.text, step_one_result))
    self.assertTrue(has_sublist(self.capture.text, step_two_header))
    self.assertTrue(has_sublist(self.capture.text, step_two_result))

  def testFailBuild(self):
    cmdlist = [{'name': 'one', 'cmd': _synthesizeCmd(['print \'hello!\''])},
               {'name': 'two', 'cmd': _synthesizeCmd(['error'])}]

    ret = self._runAnnotator(cmdlist)

    self.assertTrue('@@@STEP_FAILURE@@@' in self.capture.text)
    self.assertEquals(ret, 1)

  def testStopBuild(self):
    cmdlist = [{'name': 'one', 'cmd': _synthesizeCmd(['error'])},
               {'name': 'two', 'cmd': _synthesizeCmd(['print \'yo!\''])}]

    ret = self._runAnnotator(cmdlist)

    self.assertTrue('@@@STEP_CURSOR two@@@' not in self.capture.text)
    self.assertEquals(ret, 1)

  def testException(self):
    cmdlist = [{'name': 'one', 'cmd': ['doesn\'t exist']}]

    ret = self._runAnnotator(cmdlist)

    self.assertTrue('@@@STEP_EXCEPTION@@@' in self.capture.text)
    self.assertEquals(ret, 1)

  def testAlwaysRun(self):
    cmdlist = [{'name': 'one', 'cmd': _synthesizeCmd(['error'])},
               {'name': 'two', 'cmd': _synthesizeCmd(['print \'yo!\'']),
                    'always_run': True}]

    ret = self._runAnnotator(cmdlist)
    self.assertTrue('@@@STEP_CURSOR two@@@' in self.capture.text)
    self.assertTrue('yo!' in self.capture.text)
    self.assertEquals(ret, 1)

  def testAlwaysRunNoDupes(self):
    cmdlist = [{'name': 'one', 'cmd': _synthesizeCmd(['print \'yo!\'']),
                    'always_run': True},
               {'name': 'two', 'cmd': _synthesizeCmd(['error'])},
               {'name': 'three', 'cmd': _synthesizeCmd(['print \'hello!\'']),
                    'always_run': True}]

    ret = self._runAnnotator(cmdlist)
    self.assertEquals(self.capture.text.count('yo!'), 1)
    self.assertTrue('hello!' in self.capture.text)
    self.assertEquals(ret, 1)

  def testSkip(self):
    cmdlist = [{'name': 'one', 'cmd': _synthesizeCmd(['print \'yo!\''])},
               {'name': 'delete', 'cmd': _synthesizeCmd(['error']),
                    'skip': True},
               {'name': 'checkout', 'cmd': _synthesizeCmd(['print \'nop\'']),
                    'skip': False}]

    ret = self._runAnnotator(cmdlist)
    self.assertEquals(self.capture.text.count('yo!'), 1)
    self.assertEquals(self.capture.text.count('nop'), 1)
    self.assertTrue('@@@SEED_STEP delete@@@' in self.capture.text)
    self.assertEquals(ret, 0)

  def testCwd(self):
    tmpdir = os.path.realpath(tempfile.mkdtemp())
    try:
      cmdlist = [{'name': 'one',
                  'cmd': _synthesizeCmd(['import os; print os.getcwd()']),
                  'cwd': tmpdir
                 },]
      ret = self._runAnnotator(cmdlist)
    finally:
      os.rmdir(tmpdir)
    self.assertTrue(tmpdir in self.capture.text)
    self.assertEquals(ret, 0)

  def testStepEnvKeep(self):
    cmdlist = [{'name': 'one',
                'cmd': _synthesizeCmd([
                  'import os; print os.environ[\'SOME_ENV\']'
                ]),
                'env': {'SOME_OTHER_ENV': '123'}
               },]
    ret = self._runAnnotator(cmdlist, env={'SOME_ENV': 'blah-blah'})
    self.assertTrue('blah-blah' in self.capture.text)
    self.assertEquals(ret, 0)

  def testStepEnvAdd(self):
    cmdlist = [{'name': 'one',
                'cmd': _synthesizeCmd([
                  'import os; print os.environ[\'SOME_ENV\']'
                ]),
                'env': {'SOME_ENV': 'blah-blah'}
               },]
    ret = self._runAnnotator(cmdlist)
    self.assertTrue('blah-blah' in self.capture.text)
    self.assertEquals(ret, 0)

  def testStepEnvReplace(self):
    cmdlist = [{'name': 'one',
                'cmd': _synthesizeCmd([
                  'import os; print os.environ[\'SOME_ENV\']'
                ]),
                'env': {'SOME_ENV': 'two'}
               },]
    ret = self._runAnnotator(cmdlist, env={'SOME_ENV': 'one'})
    self.assertTrue('two' in self.capture.text)
    self.assertEquals(ret, 0)

  def testStepEnvRemove(self):
    cmdlist = [{'name': 'one',
                'cmd': _synthesizeCmd([
                  'import os\n'
                  'print \'SOME_ENV is set:\', \'SOME_ENV\' in os.environ'
                ]),
                'env': {'SOME_ENV': None}
               },]
    ret = self._runAnnotator(cmdlist, env={'SOME_ENV': 'one'})
    self.assertTrue('SOME_ENV is set: False' in self.capture.text)
    self.assertEquals(ret, 0)

  def testIgnoreAnnotations(self):
    cmdlist = [{'name': 'one',
                'cmd': _synthesizeCmd(['print \'@@@SEED_STEP blah@@@\'']),
                'ignore_annotations': True
               },]
    ret = self._runAnnotator(cmdlist)
    self.assertFalse('@@@SEED_STEP blah@@@' in self.capture.text)
    self.assertEquals(ret, 0)


if __name__ == '__main__':
  unittest.main()
