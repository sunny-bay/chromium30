#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for verification/try_job_on_rietveld.py."""

import logging
import os
import random
import string
import sys
import time
import unittest

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..'))

# In tests/
import mocks
from mocks import BuildbotBuildStep

# In root
from verification import base
from verification import try_job_steps
from verification import try_job_on_rietveld


# Some tests produce more output if verbose, so we need to
# track if we are in verbose mode or not.
VERBOSE = False


def _posted(builders):
  return 'trigger_try_jobs(42, 23, \'CQ\', False, \'HEAD\', %s)' % str(builders)


def gen_job_pending(**kwargs):
  value = {
    '__persistent_type__': 'RietveldTryJobPending',
    'builder': None,
    'clobber': False,
    'init_time': 1.,
    'requested_steps': [],
    'revision': None,
    'tries': 1,
  }
  assert all(arg in value for arg in kwargs)
  value.update(kwargs)
  return value


def gen_job(**kwargs):
  value = {
    '__persistent_type__': 'RietveldTryJob',
    'build': None,
    'builder': None,
    'clobber': False,
    'completed': False,
    'init_time': 1.,
    'parent_key': None,
    'requested_steps': [],
    'revision': None,
    'started': 1,
    'steps_failed': [],
    'steps_passed': [],
    'tries': 1,
  }
  assert all(arg in value for arg in kwargs)
  value.update(kwargs)
  return value


def gen_jobs(**kwargs):
  value =  {
    '__persistent_type__': 'RietveldTryJobs',
    'error_message': None,
    'irrelevant': [],
    'pendings': [],
    'skipped': False,
    'step_verifiers': [],
    'try_jobs': {},
  }
  for arg in kwargs:
    if arg not in value:
      raise Exception('Invalid arg %s' % str(arg))

  value.update(kwargs)

  # Convert all the verifiers to dicts (i.e. serialize them).
  value['step_verifiers'] = [step.as_dict() for step in value['step_verifiers']]

  return value


class TryJobOnRietveldBase(mocks.TestCase):
  # Base class for all test cases testing try_job_rietveld.py.
  def setUp(self):
    super(TryJobOnRietveldBase, self).setUp()
    self.timestamp = []
    self.mock(time, 'time', self._time)
    self.email = 'user1@example.com'
    self.user = 'user1'
    self.step_verifiers = [
      try_job_steps.TryJobSteps(
        builder_name='linux',
        steps=['test1', 'test2']),
      try_job_steps.TryJobSteps(
        builder_name='mac',
        steps=['test1', 'test2']),
    ]

  def tearDown(self):
    try:
      if not self.has_failed():
        self.assertEqual(0, len(self.timestamp))
    finally:
      super(TryJobOnRietveldBase, self).tearDown()

  def _time(self):
    self.assertTrue(self.timestamp)
    return self.timestamp.pop(0)


class TryRunnerRietveldTest(TryJobOnRietveldBase):
  # These test cases setup self.try_runner and call .verify() and
  # .update_status() to test it.
  def setUp(self):
    super(TryRunnerRietveldTest, self).setUp()
    self.try_runner = None
    self._change_step_verifiers(self.step_verifiers)

    # Patch it a little.
    self.buildbot_status = mocks.BuildbotMock(self)
    self.mock(
        try_job_on_rietveld.buildbot_json,
        'Buildbot',
        lambda _: self.buildbot_status)

    self.pending.revision = 123

    # It's what rietveld is going to report.
    self._key = (self.pending.issue, self.pending.patchset)
    self.context.rietveld.patchsets_properties[self._key] = {
      'try_job_results': [],
    }

  def tearDown(self):
    try:
      if not self.has_failed():
        # Not to confuse with self.context.status which is AsyncPush mock.
        self.buildbot_status.check_calls([])
    finally:
      super(TryRunnerRietveldTest, self).tearDown()

  def _change_step_verifiers(self, step_verifiers):
    """Change the current step verifiers and update any objects that used
    the old ones."""
    self.step_verifiers = step_verifiers

    # time is requested in the object construction below and self.timestamp
    # will be empty at the end of this function call.
    self.timestamp.append(1.)
    self.try_runner = try_job_on_rietveld.TryRunnerRietveld(
        self.context,
        'http://foo/bar',
        self.email,
        self.step_verifiers,
        ['ignored_step'],
        'sol',
        )
    self.try_runner.update_latency = 0


  def _get_verif(self):
    """Returns the RietveldTryJobs instance associated to this PendCommit."""
    return self.pending.verifications[self.try_runner.name]

  def _assert_pending_is_empty(self):
    actual = self._get_verif().as_dict()
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1', 'test2']),
        try_job_steps.TryJobSteps(
          builder_name='mac',
          steps=['test1', 'test2']),
      ],
      pendings=[
        gen_job_pending(builder=u'linux', requested_steps=['test1', 'test2']),
        gen_job_pending(builder=u'mac', requested_steps=['test1', 'test2']),
      ])
    self.assertEqual(expected, actual)

  def _add_build(self, builder, buildnumber, revision, steps, completed):
    """Adds a build with a randomly generated key.

    Adds the build to both the try server and to Rietveld.
    """
    key = ''.join(random.choice(string.ascii_letters) for _ in xrange(8))
    build = self.buildbot_status.add_build(
        builder, buildnumber, revision, key, completed, None)
    build.steps.extend(steps)
    self.context.rietveld.patchsets_properties[self._key][
        'try_job_results'].append(
          {
            'key': key,
            'builder': builder,
            'buildnumber': buildnumber,
          })
    return key

  def _add_triggered_build(self, builder, buildnumber, revision, steps,
                           completed, parent_key):
    """Adds a triggered build with a randomly generated key.

    Adds the build to both the try server and to Rietveld.
    """
    key = ''.join(random.choice(string.ascii_letters) for _ in xrange(8))
    build = self.buildbot_status.add_build(
        builder, buildnumber, revision, key, completed, parent_key)
    build.steps.extend(steps)
    self.context.rietveld.patchsets_properties[self._key][
        'try_job_results'].append(
          {
            'key': key,
            'builder': builder,
            'buildnumber': buildnumber,
          })
    return key

  def check_pending(self, num_status, rietveld, state, err):
    self.context.status.check_names(['try job rietveld'] * num_status)
    self.context.rietveld.check_calls(rietveld)
    self.assertEqual(state, self.pending.get_state())
    self.assertEqual(err, self.pending.error_message())

  def check_verif(self, need, waiting):
    rietveld_try_jobs = self._get_verif()
    self.assertEqual(need, rietveld_try_jobs.tests_need_to_be_run(1.))
    self.assertEqual(waiting, rietveld_try_jobs.tests_waiting_for_result())
    if not waiting:
      why_not = None
    else:
      why_not = (
          'Waiting for the following jobs:\n' +
          ''.join(
            '  %s: %s\n' % (b, ','.join(waiting[b])) for b in sorted(waiting)))
    self.assertEqual(why_not, rietveld_try_jobs.why_not())

  def call_verify(
      self, timestamps, num_status, rietveld, state, err, need, waiting):
    """Calls TryRunnerRietveld.verify().

    Makes sure the specified number of time.time() calls occurred.
    """
    self.assertEqual(0, len(self.timestamp))
    self.timestamp = timestamps
    self.try_runner.verify(self.pending)
    self.assertEqual(0, len(self.timestamp))
    self.check_pending(num_status, rietveld, state, err)
    self.check_verif(need, waiting)

  def call_update_status(
      self, timestamps, num_status, rietveld, state, err, need, waiting):
    """Calls TryRunnerRietveld.update_status().

    Makes sure the specified number of time.time() calls occurred.
    """
    self.assertEqual(0, len(self.timestamp))
    self.timestamp = timestamps
    self.try_runner.update_status([self.pending])
    self.assertEqual(0, len(self.timestamp))
    self.check_pending(num_status, rietveld, state, err)
    self.check_verif(need, waiting)

  def testVoid(self):
    self.assertEqual(self.pending.verifications.keys(), [])
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())

  def testVoidUpdate(self):
    self.try_runner.update_status([])
    self.assertEqual(base.PROCESSING, self.pending.get_state())
    self.assertEqual('', self.pending.error_message())

  def testVerificationVoid(self):
    self.call_verify(
        [1.] * 3,
        num_status=2,
        rietveld=[
          _posted({u"linux": ["test1", "test2"]}),
          _posted({u"mac": ["test1", "test2"]}),
        ],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1', 'test2'], 'mac': ['test1', 'test2']})
    self._assert_pending_is_empty()

  def testVerificationUpdateNoJob(self):
    self.call_verify(
        [1.] * 3,
        num_status=2,
        rietveld=[
          _posted({u"linux": ["test1", "test2"]}),
          _posted({u"mac": ["test1", "test2"]}),
        ],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1', 'test2'], 'mac': ['test1', 'test2']})
    self._assert_pending_is_empty()
    self.call_update_status(
        [1.] * 2,
        num_status=0,
        rietveld=[],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1', 'test2'], 'mac': ['test1', 'test2']})
    self._assert_pending_is_empty()

  def testVerificationUpdate(self):
    self.call_verify(
        [1.] * 3,
        num_status=2,
        rietveld=[
          _posted({u"linux": ["test1", "test2"]}),
          _posted({u"mac": ["test1", "test2"]}),
        ],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1', 'test2'], 'mac': ['test1', 'test2']})
    self._assert_pending_is_empty()
    key = self._add_build('mac', 32, 42, [], False)

    self.call_update_status(
        [1.] * (3 + 1 * VERBOSE),
        num_status=1,
        rietveld=[],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1', 'test2'], 'mac': ['test1', 'test2']})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1', 'test2']),
        try_job_steps.TryJobSteps(
          builder_name='mac',
          steps=['test1', 'test2']),
      ],
      pendings=[
        gen_job_pending(builder='linux', requested_steps=['test1', 'test2']),
      ],
      try_jobs={
        key: gen_job(
          builder='mac',
          build=32,
          requested_steps=['test1', 'test2'],
          revision=42),
      })
    self.assertEqual(expected, self._get_verif().as_dict())

  def testVerificationSuccess(self):
    self.call_verify(
        [1.] * 3,
        num_status=2,
        rietveld=[
          _posted({u"linux": ["test1", "test2"]}),
          _posted({u"mac": ["test1", "test2"]}),
        ],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1', 'test2'], 'mac': ['test1', 'test2']})
    key1 = self._add_build(
        'mac', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)
    key2 = self._add_build(
        'linux', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)

    self.call_update_status(
        [1.] * (4 + 2 * VERBOSE),
        num_status=2,
        rietveld=[],
        state=base.SUCCEEDED,
        err='',
        need={},
        waiting={})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1', 'test2']),
        try_job_steps.TryJobSteps(
          builder_name='mac',
          steps=['test1', 'test2']),
      ],
      try_jobs={
        key1: gen_job(
          builder=u'mac',
          build=32,
          requested_steps=['test1', 'test2'],
          steps_passed=['test1', 'test2'],
          revision=42),
        key2: gen_job(
          builder=u'linux',
          build=32,
          requested_steps=['test1', 'test2'],
          steps_passed=['test1', 'test2'],
          revision=42),
      })
    self.assertEqual(expected, self._get_verif().as_dict())

  def testVerificationRetrySuccess(self):
    self.call_verify(
        [1.] * 3,
        num_status=2,
        rietveld=[
          _posted({u"linux": ["test1", "test2"]}),
          _posted({u"mac": ["test1", "test2"]}),
        ],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1', 'test2'], 'mac': ['test1', 'test2']})
    key1 = self._add_build(
        'mac', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', False)],
        False)
    key2 = self._add_build(
        'linux', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)

    self.call_update_status(
        [1.] * (5 + 2 * VERBOSE),
        num_status=3,
        rietveld=[_posted({u"mac": ["test2"]})],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'mac': ['test2']})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1', 'test2']),
        try_job_steps.TryJobSteps(
          builder_name='mac',
          steps=['test1', 'test2']),
      ],
      pendings=[
        gen_job_pending(builder=u'mac', requested_steps=['test2'], tries=2),
      ],
      try_jobs={
        key1: gen_job(
          builder=u'mac',
          build=32,
          requested_steps=['test1', 'test2'],
          steps_failed=['test2'],
          steps_passed=['test1'],
          revision=42),
        key2: gen_job(
          builder=u'linux',
          build=32,
          requested_steps=['test1', 'test2'],
          steps_passed=['test1', 'test2'],
          revision=42),
      })
    self.assertEqual(expected, self._get_verif().as_dict())

    # Add a new build on mac where test2 passed.
    key3 = self._add_build(
        'mac', 33, 42,
        [BuildbotBuildStep('test1', False), BuildbotBuildStep('test2', True)],
        False)
    self.call_update_status(
        [1.] * (5 + 1 * VERBOSE),
        num_status=3,
        rietveld=[],
        state=base.SUCCEEDED,
        err='',
        need={},
        waiting={})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1', 'test2']),
        try_job_steps.TryJobSteps(
          builder_name='mac',
          steps=['test1', 'test2']),
      ],
      try_jobs={
        key1: gen_job(
          build=32,
          builder='mac',
          requested_steps=['test1', 'test2'],
          steps_failed=['test2'],
          steps_passed=['test1'],
          revision=42),
        key2: gen_job(
          builder='linux',
          build=32,
          requested_steps=['test1', 'test2'],
          revision=42,
          steps_passed=['test1', 'test2']),
        key3: gen_job(
          builder='mac',
          build=33,
          requested_steps=['test2'],
          revision=42,
          steps_failed=['test1'],
          steps_passed=['test2'],
          tries=2),
      })
    self.assertEqual(expected, self._get_verif().as_dict())

  def testVerificationRetryRetry(self):
    self.call_verify(
        [1.] * 3,
        num_status=2,
        rietveld=[
          _posted({u"linux": ["test1", "test2"]}),
          _posted({u"mac": ["test1", "test2"]}),
        ],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1', 'test2'], 'mac': ['test1', 'test2']})
    key1 = self._add_build(
        'mac', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', False)],
        False)
    key2 = self._add_build(
        'linux', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)

    self.call_update_status(
        [1.] * (5 + 2 * VERBOSE),
        num_status=3,
        rietveld=[_posted({u"mac": ["test2"]})],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'mac': ['test2']})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1', 'test2']),
        try_job_steps.TryJobSteps(
          builder_name='mac',
          steps=['test1', 'test2']),
      ],
      pendings=[
        gen_job_pending(builder='mac', requested_steps=['test2'], tries=2),
      ],
      try_jobs={
        key1: gen_job(
          builder='mac',
          build=32,
          requested_steps=['test1', 'test2'],
          steps_failed=['test2'],
          steps_passed=['test1'],
          revision=42),
        key2: gen_job(
          builder='linux',
          build=32,
          requested_steps=['test1', 'test2'],
          steps_passed=['test1', 'test2'],
          revision=42),
      })
    self.assertEqual(expected, self._get_verif().as_dict())

    # Add a new build on mac where test2 failed.
    key3 = self._add_build('mac', 33, 42, [BuildbotBuildStep('test2', False)],
                           False)

    self.call_update_status(
        [1.] * (6 + 1 * VERBOSE),
        num_status=4,
        rietveld=[_posted({u"mac": ["test2"]})],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'mac': ['test2']})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1', 'test2']),
        try_job_steps.TryJobSteps(
          builder_name='mac',
          steps=['test1', 'test2']),
      ],
      pendings=[
        gen_job_pending(builder='mac', requested_steps=['test2'], tries=3),
      ],
      try_jobs={
        key1: gen_job(
          build=32,
          builder='mac',
          requested_steps=['test1', 'test2'],
          steps_failed=['test2'],
          steps_passed=['test1'],
          revision=42),
        key2: gen_job(
          builder='linux',
          build=32,
          requested_steps=['test1', 'test2'],
          revision=42,
          steps_passed=['test1', 'test2']),
        key3: gen_job(
          builder='mac',
          build=33,
          requested_steps=['test2'],
          revision=42,
          steps_failed=['test2'],
          tries=2),
      })
    self.assertEqual(expected, self._get_verif().as_dict())

    # Add a new build on mac where test2 failed again! Too bad now.
    self._add_build('mac', 34, 42, [BuildbotBuildStep('test2', False)], False)

    self.call_update_status(
        [1.] * (6 + 2 * VERBOSE),
        num_status=4,
        rietveld=[],
        state=base.FAILED,
        err=(
          u'Retried try job too often on mac for step(s) test2\n'
          'http://foo/bar/buildstatus?builder=mac&number=34'),
        need={},
        waiting={})

  def testVerificationRetryRetryTriggered(self):
    step_verifiers = [
        try_job_steps.TryJobTriggeredSteps(
            builder_name='triggered',
            trigger_name='builder',
            steps={'test1': 'build'})]
    self._change_step_verifiers(step_verifiers)

    self.call_verify(
        [1.] * 3,
        num_status=2,
        rietveld=[
          _posted({u"builder": ["build"]}),
        ],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'triggered': ['test1']})

    # The trigger bot passed, but the triggered bot fails.
    key1 = self._add_build('builder', 1, 42, [BuildbotBuildStep('build', True)],
                           True)
    self._add_triggered_build('triggered', 1, 42,
                              [BuildbotBuildStep('test1', False)], True, key1)
    triggered_key_1 = 'triggered/1_triggered_%s' % key1

    self.call_update_status(
        [1.] * (6 + 2 * VERBOSE),
        num_status=4,
        rietveld=[_posted({u"builder": ["build"]})],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'triggered': ['test1']})
    expected = gen_jobs(
      step_verifiers=[
          try_job_steps.TryJobTriggeredSteps(
              builder_name='triggered',
              trigger_name='builder',
              steps={'test1': 'build'})],
      pendings=[
        gen_job_pending(builder='builder', requested_steps=['build'], tries=2),
        gen_job_pending(builder='triggered', requested_steps=['test1'],
                        tries=2),
      ],
      try_jobs={
        key1: gen_job(
          builder='builder',
          build=1,
          requested_steps=['build'],
          steps_passed=['build'],
          completed=True,
          revision=42,
          tries=1,
          ),
        triggered_key_1: gen_job(
          builder='triggered',
          build=1,
          requested_steps=['test1'],
          steps_failed=['test1'],
          completed=True,
          revision=42,
          parent_key=key1,
          tries=1,
          ),
      })
    self.assertEqual(expected, self._get_verif().as_dict())

    # Triggered bot fails again.
    key2 = self._add_build('builder', 2, 42, [BuildbotBuildStep('build', True)],
                           True)
    self._add_triggered_build('triggered', 2, 42,
                              [BuildbotBuildStep('test1', False)], True, key2)
    triggered_key_2 = 'triggered/2_triggered_%s' % key2

    self.call_update_status(
        [1.] * (6 + 2 * VERBOSE),
        num_status=4,
        rietveld=[_posted({u"builder": ["build"]})],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'triggered': ['test1']})
    expected = gen_jobs(
      step_verifiers=[
          try_job_steps.TryJobTriggeredSteps(
              builder_name='triggered',
              trigger_name='builder',
              steps={'test1': 'build'})],
      pendings=[
        gen_job_pending(builder='builder', requested_steps=['build'], tries=3),
        gen_job_pending(builder='triggered', requested_steps=['test1'],
                        tries=3),
      ],
      try_jobs={
        key1: gen_job(
          builder='builder',
          build=1,
          requested_steps=['build'],
          steps_passed=['build'],
          completed=True,
          revision=42,
          tries=1,
          ),
        triggered_key_1: gen_job(
          builder='triggered',
          build=1,
          requested_steps=['test1'],
          steps_failed=['test1'],
          completed=True,
          revision=42,
          parent_key=key1,
          tries=1,
          ),
        key2: gen_job(
          builder='builder',
          build=2,
          requested_steps=['build'],
          steps_passed=['build'],
          completed=True,
          revision=42,
          tries=2,
          ),
        triggered_key_2: gen_job(
          builder='triggered',
          build=2,
          requested_steps=['test1'],
          steps_failed=['test1'],
          completed=True,
          revision=42,
          parent_key=key2,
          tries=2,
          ),
      })
    self.assertEqual(expected, self._get_verif().as_dict())

    # Triggered bot fails for the 3rd time, abort.
    key3 = self._add_build('builder', 3, 1, [BuildbotBuildStep('build', True)],
                           True)
    self._add_triggered_build('triggered', 3, 1,
                              [BuildbotBuildStep('test1', False)], True, key3)
    self.call_update_status(
        [1.] * (4 + 3 * VERBOSE),
        num_status=2,
        rietveld=[],
        state=base.FAILED,
        # TODO(csharp): Its the triggered bot that keeps failing, so that should
        # be the bot mentioned here.
        err=(
            u'Retried try job too often on builder for step(s) build\n'
            'http://foo/bar/buildstatus?builder=builder&number=3'),
        need={},
        waiting={})

  def testVerificationPreviousJobGood(self):
    # Reuse the previous job if good.
    key1 = self._add_build(
        'mac', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)

    self.call_verify(
        [1.] * (2 + 1 * VERBOSE),
        num_status=1,
        rietveld=[_posted({u"linux": ["test1", "test2"]})],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1', 'test2']})

    # Sends an update to note the job was started.
    self.call_update_status(
        [1.] * 3,
        num_status=1,
        rietveld=[],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1', 'test2']})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1', 'test2']),
        try_job_steps.TryJobSteps(
          builder_name='mac',
          steps=['test1', 'test2']),
      ],
      pendings=[
        gen_job_pending(builder='linux', requested_steps=['test1', 'test2']),
      ],
      try_jobs={
        key1: gen_job(
          build=32,
          builder='mac',
          # Note that requested_steps is empty since testfilter is not parsed.
          steps_passed=['test1', 'test2'],
          revision=42,
          # tries == 0 since we didn't start it.
          tries=0),
        })
    self.assertEqual(expected, self._get_verif().as_dict())

  def _expired(self, now, **kwargs):
    # Exacly like testVerificationPreviousJobGood except that jobs are always
    # too old, either by revision or by timestamp.
    key1 = self._add_build(
        'mac', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)

    self.call_verify(
        [now] * 3,
        num_status=2,
        rietveld=[
          _posted({u"linux": ["test1", "test2"]}),
          _posted({u"mac": ["test1", "test2"]}),
        ],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1', 'test2'], 'mac': ['test1', 'test2']})

    self.call_update_status(
        [now] * 2,
        num_status=0,
        rietveld=[],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1', 'test2'], 'mac': ['test1', 'test2']})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1', 'test2']),
        try_job_steps.TryJobSteps(
          builder_name='mac',
          steps=['test1', 'test2']),
      ],
      irrelevant=[key1],
      pendings=[
        gen_job_pending(
            builder='linux', requested_steps=['test1', 'test2'], **kwargs),
        gen_job_pending(
            builder='mac', requested_steps=['test1', 'test2'], **kwargs),
      ])
    self.assertEqual(expected, self._get_verif().as_dict())

  def testVerificationPreviousExpiredRevisionTooOld(self):
    self.context.checkout.revisions = lambda _r1, _r2: 201
    self._expired(1.)

  def testVerificationPreviousExpiredDateTooOld(self):
    # 5 days old.
    old = 5*24*60*60.
    self._expired(old, init_time=old)

  def _previous_job_partially_good(
      self, steps, steps_failed, completed, expect_mac_retry, num_time_verify,
      num_time_update, num_status_update):
    # Reuse the previous job tests that passed.
    key1 = self._add_build('mac', 32, 42, steps, completed)

    expected_calls = [_posted({u"linux": ["test1", "test2"]})]
    pendings = [
        gen_job_pending(builder='linux', requested_steps=['test1', 'test2'])
    ]
    if expect_mac_retry:
      # No need to run test2 again.
      expected_calls.append(_posted({u"mac": ["test1"]}))
      pendings.append(gen_job_pending(builder='mac', requested_steps=['test1']))
    self.call_verify(
        [1.] * (num_time_verify + 1 * VERBOSE),
        num_status=len(expected_calls),
        rietveld=expected_calls,
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1', 'test2'], 'mac': ['test1']})
    self.call_update_status(
        [1.] * num_time_update,
        num_status=num_status_update,
        rietveld=[],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1', 'test2'], 'mac': ['test1']})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1', 'test2']),
        try_job_steps.TryJobSteps(
          builder_name='mac',
          steps=['test1', 'test2']),
      ],
      pendings=pendings,
      try_jobs={
        key1: gen_job(
          build=32,
          builder='mac',
          # Note that requested_steps is empty since testfilter is not parsed.
          steps_failed=steps_failed,
          steps_passed=['test2'],
          revision=42,
          # tries == 0 since we didn't start it.
          tries=0,
          completed=completed),
        })
    self.assertEqual(expected, self._get_verif().as_dict())

  def testVerificationPreviousJobPartiallyGood1(self):
    # Only test1 will be run on mac since test2 had passed.
    self._previous_job_partially_good(
        [BuildbotBuildStep('test1', False), BuildbotBuildStep('test2', True)],
        ['test1'], True, True, 3, 2, 0)

  def testVerificationPreviousJobPartiallyGood2(self):
    # Let's assume a testfilter was used and test1 wasn't run. Only test1 will
    # be run on mac.
    self._previous_job_partially_good(
        [BuildbotBuildStep('test2', True)], [], True, True, 3, 2, 0)

  def testVerificationPreviousJobPartiallyGood3(self):
    # Test that we do not retry on mac until it completes.  This is because
    # CQ does not parse the test filter, so we do not know if the mac job
    # will run test1.
    # It's kind of weird, because it sends a status report like if it had
    # started this job.
    self._previous_job_partially_good(
        [BuildbotBuildStep('test2', True)], [], False, False, 2, 3, 1)

  def testVerificationPreviousJobsWereGood(self):
    # Reuse the previous jobs tests that passed. Do not send any try job.
    key1 = self._add_build(
        'mac', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)
    key2 = self._add_build(
        'linux', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        False)

    # People will love that!
    self.call_verify(
        [1.] * (1 + 2 * VERBOSE),
        num_status=0,
        rietveld=[],
        state=base.SUCCEEDED,
        err='',
        need={},
        waiting={})

    self.call_update_status(
        [1.] * 2,
        num_status=0,
        rietveld=[],
        state=base.SUCCEEDED,
        err='',
        need={},
        waiting={})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1', 'test2']),
        try_job_steps.TryJobSteps(
          builder_name='mac',
          steps=['test1', 'test2']),
      ],
      try_jobs={
        key1: gen_job(
          build=32,
          builder='mac',
          # Note that requested_steps is empty since testfilter is not parsed.
          steps_passed=['test1', 'test2'],
          revision=42,
          # tries == 0 since we didn't start it.
          tries=0),
        key2: gen_job(
          build=32,
          builder='linux',
          # Note that requested_steps is empty since testfilter is not parsed.
          steps_passed=['test1', 'test2'],
          revision=42,
          # tries == 0 since we didn't start it.
          tries=0),
        })
    self.assertEqual(expected, self._get_verif().as_dict())

  def testRietveldTryJobsPendingWasLost(self):
    # Requested a pending try job but the request was lost.
    self.try_runner.step_verifiers = [
      try_job_steps.TryJobSteps(
        builder_name='linux',
        steps=['test1']),
    ]
    self.call_verify(
        [1.] * 2,
        num_status=1,
        rietveld=[_posted({u"linux": ["test1"]})],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1']})
    self.call_update_status(
        [1.] * 2,
        num_status=0,
        rietveld=[],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1']})

    # 3 minutes later
    later = 3. * 60
    self.call_update_status(
        [later] * 2,
        num_status=0,
        rietveld=[],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1']})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1']),
      ],
      pendings=[
        gen_job_pending(builder=u'linux', requested_steps=['test1']),
      ])

    # 1h later.
    later = 60. * 60
    self.call_update_status(
        [later] * (3 + 1 * VERBOSE),
        num_status=1,
        rietveld=[_posted({u"linux": ["test1"]})],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1']})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1']),
      ],
      pendings=[
        gen_job_pending(
            builder=u'linux', init_time=later, requested_steps=['test1']),
      ])
    self.assertEqual(expected, self._get_verif().as_dict())

  def testRietveldTryJobsPendingTookSomeTime(self):
    # Requested a pending try job but the request took some time to propagate.
    self.try_runner.step_verifiers = [
      try_job_steps.TryJobSteps(
        builder_name='linux',
        steps=['test1']),
    ]
    self.call_verify(
        [1.] * 2,
        num_status=1,
        rietveld=[_posted({u"linux": ["test1"]})],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1']})
    self.call_update_status(
        [1.] * 2,
        num_status=0,
        rietveld=[],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1']})
    # 3 minutes later
    later = 3. * 60
    self.call_update_status(
        [later] * 2,
        num_status=0,
        rietveld=[],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1']})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1']),
      ],
      pendings=[
        gen_job_pending(builder=u'linux', requested_steps=['test1']),
      ])
    self.assertEqual(expected, self._get_verif().as_dict())

    # Queue it.
    self.buildbot_status.builders['linux'].pending_builds.data = [
      {
        "builderName":"linux",
        "builds":[],
        "reason":"%d-1: None" % self.pending.issue,
        "source": {
          "changes": [
            {
              "at": "Wed 05 Dec 2012 19:11:19",
              "files": [],
              "number": 268857,
              "project": "",
              "properties": [],
              "rev": "171358",
              "revision": "171358",
              "when": 1354763479,
              "who": self.pending.owner,
            },
          ],
          "hasPatch": False,
          "project": "chrome",
          "repository": "",
          "revision": "171358",
        },
        "submittedAt": 1354763479,
      },
    ]

    # 1h later, it must not have queued another job.
    later = 60. * 60
    self.call_update_status(
        [later] * 2,
        num_status=0,
        rietveld=[],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1']})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1']),
      ],
      pendings=[
        gen_job_pending(
            builder=u'linux', requested_steps=['test1']),
      ])
    self.assertEqual(expected, self._get_verif().as_dict())

  def testRietveldHung(self):
    # Send a try job and have it never start.
    self.try_runner.step_verifiers = [
      try_job_steps.TryJobSteps(
        builder_name='linux',
        steps=['test1']),
    ]
    self.call_verify(
        [1.] * 2,
        num_status=1,
        rietveld=[_posted({u"linux": ["test1"]})],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1']})
    key1 = self._add_build(
        'linux', 32, 42,
        [],
        False)
    self.call_update_status(
        [1.] * (3 + 1 * VERBOSE),
        num_status=1,
        rietveld=[],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1']})

    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1']),
      ],
      try_jobs={
        key1: gen_job(
          builder=u'linux',
          build=32,
          requested_steps=['test1'],
          steps_passed=[],
          revision=42,
          completed=False),
      })

    self.assertEqual(expected, self._get_verif().as_dict())

    # Fast forward in time to make the try job request "timeout". Basically,
    # the Try Job trigger on Rietveld was somehow ignored by the Try Server
    # itself. Test our chance by sending another trigger.
    later = 40. * 24 * 60 * 60
    # Update the internal status.
    self.call_update_status(
        [later] * 3,
        num_status=1,
        rietveld=[_posted({u"linux": ["test1"]})],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1']})

    self.assertEqual(
        'Waiting for the following jobs:\n  linux: test1\n',
        self._get_verif().why_not())

    expected_timed_out = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1']),
      ],
      irrelevant=[key1],
      pendings=[
        gen_job_pending(
            builder=u'linux', init_time=later, requested_steps=['test1']),
      ])
    self.assertEqual(expected_timed_out, self._get_verif().as_dict())

  def testVerificationBrokenTestOnHead(self):
    # The CQ retries until it aborts because the test is broken at HEAD on
    # mac/test2.
    self.call_verify(
        [1.] * 3,
        num_status=2,
        rietveld=[
          _posted({u"linux": ["test1", "test2"]}),
          _posted({u"mac": ["test1", "test2"]}),
        ],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'linux': ['test1', 'test2'], 'mac': ['test1', 'test2']})
    key1 = self._add_build(
        'mac', 32, 42,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', False)],
        True)
    key2 = self._add_build(
        'linux', 12, 22,
        [BuildbotBuildStep('test1', True), BuildbotBuildStep('test2', True)],
        True)

    self.call_update_status(
        [1.] * (5 + 2 * VERBOSE),
        num_status=3,
        rietveld=[_posted({u"mac": ["test2"]})],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'mac': ['test2']})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1', 'test2']),
        try_job_steps.TryJobSteps(
          builder_name='mac',
          steps=['test1', 'test2']),
      ],
      pendings=[
        gen_job_pending(builder=u'mac', requested_steps=['test2'], tries=2),
      ],
      try_jobs={
        key1: gen_job(
          builder=u'mac',
          build=32,
          completed=True,
          requested_steps=['test1', 'test2'],
          steps_failed=['test2'],
          steps_passed=['test1'],
          revision=42),
        key2: gen_job(
          builder=u'linux',
          build=12,
          completed=True,
          requested_steps=['test1', 'test2'],
          steps_passed=['test1', 'test2'],
          revision=22),
      })
    self.assertEqual(expected, self._get_verif().as_dict())

    key3 = self._add_build(
        'mac', 33, 42,
        [BuildbotBuildStep('test2', False)],
        True)
    self.call_update_status(
        [1.] * (4 + 1 * VERBOSE),
        num_status=2,
        rietveld=[_posted({u"mac": ["test2"]})],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'mac': ['test2']})
    expected = gen_jobs(
      step_verifiers=[
        try_job_steps.TryJobSteps(
          builder_name='linux',
          steps=['test1', 'test2']),
        try_job_steps.TryJobSteps(
          builder_name='mac',
          steps=['test1', 'test2']),
      ],
      pendings=[
        gen_job_pending(builder=u'mac', requested_steps=['test2'], tries=3),
      ],
      try_jobs={
        key1: gen_job(
          build=32,
          builder=u'mac',
          completed=True,
          requested_steps=['test1', 'test2'],
          steps_failed=['test2'],
          steps_passed=['test1'],
          revision=42),
        key2: gen_job(
          builder=u'linux',
          build=12,
          completed=True,
          requested_steps=['test1', 'test2'],
          revision=22,
          steps_passed=['test1', 'test2']),
        key3: gen_job(
          builder=u'mac',
          completed=True,
          build=33,
          requested_steps=['test2'],
          revision=42,
          steps_failed=['test2'],
          tries=2),
      })
    self.assertEqual(expected, self._get_verif().as_dict())
    self.call_update_status(
        [1.] * (2 + 1 * VERBOSE),
        num_status=0,
        rietveld=[],
        state=base.PROCESSING,
        err='',
        need={},
        waiting={'mac': ['test2']})


class RietveldTryJobsTest(TryJobOnRietveldBase):
  # Directly test RietveldTryJobs without constructing a TryRunnerRietveld.
  # They should never touch self.timestamp.
  def testInitial(self):
    now = 1.
    jobs = try_job_on_rietveld.RietveldTryJobs()
    jobs.step_verifiers = [
      try_job_steps.TryJobSteps(
        builder_name='builder1',
        steps=['test10', 'test11']),
    ]
    jobs.try_jobs['key1'] = try_job_on_rietveld.RietveldTryJob(
        init_time=now,
        builder='builder1',
        build=12,
        revision=13,
        requested_steps=['test10'],
        started=int(now),
        steps_passed=['test10'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=1,
        parent_key=None)
    self.assertEqual({'builder1': ['test11']}, jobs.tests_need_to_be_run(now))
    self.assertEqual({'builder1': ['test11']}, jobs.tests_waiting_for_result())

  def testPending(self):
    now = 1.
    jobs = try_job_on_rietveld.RietveldTryJobs()
    jobs.step_verifiers = [
      try_job_steps.TryJobSteps(
        builder_name='builder1',
        steps=['test10', 'test11']),
    ]
    jobs.try_jobs['key1'] = try_job_on_rietveld.RietveldTryJob(
        init_time=now,
        builder='builder1',
        build=12,
        revision=13,
        requested_steps=['test10'],
        started=int(now),
        steps_passed=['test10'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=1,
        parent_key=None)
    jobs.pendings.append(
        try_job_on_rietveld.RietveldTryJobPending(
            init_time=now,
            builder='builder1',
            revision=13,
            requested_steps=['test11'],
            clobber=False,
            tries=1))
    self.assertEqual({}, jobs.tests_need_to_be_run(now))
    self.assertEqual({'builder1': ['test11']}, jobs.tests_waiting_for_result())

  def testTriggeredPending(self):
    # Construct an instance that has both tests to trigger and tests that are
    # pending results.
    now = 1.
    jobs = try_job_on_rietveld.RietveldTryJobs()
    jobs.step_verifiers = [
      try_job_steps.TryJobSteps(
        builder_name='builder1',
        steps=['test10', 'test11']),
      try_job_steps.TryJobSteps(
        builder_name='builder2',
        steps=['test20', 'test21']),
    ]
    jobs.try_jobs['key1'] = try_job_on_rietveld.RietveldTryJob(
        init_time=now,
        builder='builder1',
        build=12,
        revision=13,
        requested_steps=['test10'],
        started=int(now),
        steps_passed=['test10'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=1,
        parent_key=None)
    jobs.try_jobs['key2'] = try_job_on_rietveld.RietveldTryJob(
        init_time=now,
        builder='builder2',
        build=13,
        revision=14,
        requested_steps=[],
        started=int(now),
        steps_passed=['test21'],
        steps_failed=[],
        clobber=False,
        completed=False,
        tries=1,
        parent_key=None)
    jobs.pendings.append(
        try_job_on_rietveld.RietveldTryJobPending(
            init_time=now,
            builder='builder2',
            revision=14,
            requested_steps=['test20'],
            clobber=False,
            tries=1))
    # test11 is still not queued to be run but build with test20 in it has still
    # not started yet.
    self.assertEqual({'builder1': ['test11']}, jobs.tests_need_to_be_run(now))
    self.assertEqual(
        {'builder1': ['test11'], 'builder2': ['test20']},
        jobs.tests_waiting_for_result())

  def testAddTriggeredBot(self):
    jobs = try_job_on_rietveld.RietveldTryJobs()
    jobs.step_verifiers = [try_job_steps.TryJobTriggeredSteps(
        builder_name='tester1',
        trigger_name='builder1',
        steps={'test3': 'trigger'})]
    self.assertEqual({'builder1': ['trigger']}, jobs.tests_need_to_be_run(1.))
    self.assertEqual({'tester1': ['test3']}, jobs.tests_waiting_for_result())

  def testGenerateWatchedBuilders(self):
    jobs = try_job_on_rietveld.RietveldTryJobs()
    jobs.step_verifiers = [
        try_job_steps.TryJobSteps(
            builder_name='builder1',
            steps=['test']),
        try_job_steps.TryJobTriggeredSteps(
            builder_name='triggered1',
            trigger_name='trigger_bot1',
            steps={'test': 'test'}),
        try_job_steps.TryJobTriggeredOrNormalSteps(
            builder_name='triggered2',
            trigger_name='trigger_bot2',
            trigger_bot_steps=['test'],
            steps={'test': 'test'},
            use_triggered_bot=False)
    ]

    expected_watched_builders = [
        'builder1',
        'trigger_bot1',
        'trigger_bot2',
        'triggered1',
        'triggered2'
    ]
    self.assertEqual(sorted(expected_watched_builders),
                     sorted(jobs.watched_builders()))


if __name__ == '__main__':
  logging.basicConfig(
      level=[logging.WARNING, logging.INFO, logging.DEBUG][
        min(sys.argv.count('-v'), 2)],
      format='%(levelname)5s %(module)15s(%(lineno)3d): %(message)s')
  if '-v' in sys.argv:
    VERBOSE = True
    unittest.TestCase.maxDiff = None
  unittest.main()
