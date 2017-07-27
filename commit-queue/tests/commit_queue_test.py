#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for commit_queue.py."""

import os
import StringIO
import sys
import time
import unittest

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..'))

import commit_queue
import context
import creds

from testing_support import auto_stub

# From /tests
import mocks


class Stop(Exception):
  pass


class PendingManagerMock(auto_stub.SimpleMock):
  def __init__(self, unit_test):
    super(PendingManagerMock, self).__init__(unit_test)
    self.context = context.Context(
        mocks.RietveldMock(unit_test), mocks.SvnCheckoutMock(unit_test), None)
    self.count = 0

  def load(self, *args, **kwargs):
    self._register_call(*args, **kwargs)

  def save(self, *args, **kwargs):
    self._register_call(*args, **kwargs)

  def close(self, *args, **kwargs):
    self._register_call(*args, **kwargs)

  def look_for_new_pending_commit(self, *args, **kwargs):
    self._register_call(*args, **kwargs)
    self.count += 1
    if self.count > 3:
      raise Stop()

  def process_new_pending_commit(self, *args, **kwargs):
    self._register_call(*args, **kwargs)

  def update_status(self, *args, **kwargs):
    self._register_call(*args, **kwargs)

  def scan_results(self, *args, **kwargs):
    self._register_call(*args, **kwargs)


class CredentialsMock(object):
  @staticmethod
  def get(user):
    return '1%s1' % user


class CommitQueueTest(auto_stub.TestCase):
  def setUp(self):
    super(CommitQueueTest, self).setUp()
    self.mock(sys, 'argv', ['commit_queue.py'])
    self.mock(sys, 'stdout', StringIO.StringIO())
    self.mock(sys, 'stderr', StringIO.StringIO())
    self.mock(commit_queue.projects, 'load_project', None)
    self._time = 1
    self.mock(time, 'time', self._get_time)
    self.mock(creds, 'Credentials', self._get_cred)

  def tearDown(self):
    try:
      if not self.has_failed():
        self._check('stdout', '')
        self._check('stderr', '')
    finally:
      super(CommitQueueTest, self).tearDown()

  def _check(self, pipe, expected):
    self.assertEqual(expected, self._pop(pipe))

  def _get_time(self):
    self._time += 10
    return self._time

  @staticmethod
  def _pop(pipe):
    data = getattr(sys, pipe).getvalue()
    setattr(sys, pipe, StringIO.StringIO())
    return data

  def _get_cred(self, pwd):
    rootdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    workdir = os.path.join(rootdir, 'workdir')
    self.assertEqual(os.path.join(workdir, '.gaia_pwd'), pwd)
    return CredentialsMock()

  def testHelp(self):
    sys.argv.append('--help')
    try:
      commit_queue.main()
      self.fail()
    except SystemExit as e:
      self.assertEqual(0, e.code)
    output = self._pop('stdout')
    # Cannot compare for the exact string since the formatting depends on the
    # screen size.
    self.assertIn('Minimum delay between each polling loop', output)
    self.assertIn('Run for real instead of dry-run mode which', output)
    self.assertLess(600, len(output), output)

  def testChromium(self):
    sys.argv.extend(('--project', 'chromium'))
    calls = []
    def load_project(*args):
      calls.append(args)
      return PendingManagerMock(self)

    self.mock(commit_queue.projects, 'load_project', load_project)
    try:
      commit_queue.main()
      self.fail()
    except Stop:
      pass
    self.assertEqual(1, len(calls))
    self.assertEqual('chromium', calls[0][0])
    self.assertEqual('commit-bot@chromium.org', calls[0][1])
    self.assertEqual(
        os.path.join(os.path.dirname(ROOT_DIR), 'workdir'), calls[0][2])
    self.assertEqual(None, calls[0][4])
    self._check(
        'stdout',
        'Using read-only Rietveld\n'
        'Using read-only checkout\n'
        'Using read-only chromium-status interface\n')
    self._check('stderr', 'Saving db...     \nDone!            \n')

  def testDryRun(self):
    sys.argv.extend(('--project', 'chromium'))
    pc = PendingManagerMock(self)
    self.mock(
        commit_queue.projects,
        'load_project',
        lambda *args: pc)
    try:
      commit_queue.main()
      self.fail()
    except Stop:
      pass
    self.assertEqual(
        'ReadOnlyCheckout', pc.context.checkout.__class__.__name__)
    # Ugh.
    self.assertEqual(
        'RietveldMock', pc.context.rietveld.__class__.__name__)
    self._check(
        'stdout',
        'Using read-only Rietveld\n'
        'Using read-only checkout\n'
        'Using read-only chromium-status interface\n')
    self._check('stderr', 'Saving db...     \nDone!            \n')


if __name__ == '__main__':
  unittest.main()
