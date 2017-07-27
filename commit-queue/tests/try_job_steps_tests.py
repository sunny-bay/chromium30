#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for verification/try_job_steps.py."""

import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..'))

from verification import try_job_steps
from verification import try_job_on_rietveld


def CreateRietveldTryJob(builder, requested_steps, steps_passed, steps_failed):
  return try_job_on_rietveld.RietveldTryJob(
      init_time=1.,
      builder=builder,
      build=1,
      revision=1,
      requested_steps=requested_steps,
      started=1,
      steps_passed=steps_passed,
      steps_failed=steps_failed,
      clobber=False,
      completed=False,
      tries=1,
      parent_key=None)


class NeedToRunTest(unittest.TestCase):
  def test_no_tries(self):
    self.assertEqual(
        set(['test1', 'test2']),
        try_job_steps.need_to_trigger('bot', set(['test1', 'test2']), {}))

  def test_non_matching_try(self):
    tries = [
        CreateRietveldTryJob(
            builder='different',
            requested_steps=[],
            steps_passed=[],
            steps_failed=[]),
    ]

    self.assertEqual(
        set(['test1', 'test2']),
        try_job_steps.need_to_trigger('bot', set(['test1', 'test2']), tries))

  def test_partial_match_need_trigger(self):
    tries = [
        CreateRietveldTryJob(
            builder='bot',
            requested_steps=['test1'],
            steps_passed=['test1'],
            steps_failed=[]),
    ]

    self.assertEqual(
        set(['test2']),
        try_job_steps.need_to_trigger('bot', set(['test1', 'test2']), tries))

  def test_partial_match_no_trigger(self):
    tries = [
        CreateRietveldTryJob(
            builder='bot',
            requested_steps=['test1', 'test2'],
            steps_passed=['test1'],
            steps_failed=[]),
    ]

    self.assertEqual(
        set(),
        try_job_steps.need_to_trigger('bot', set(['test1', 'test2']), tries))

  def test_full_match(self):
    tries = [
        CreateRietveldTryJob(
            builder='bot',
            requested_steps=['test1', 'test2'],
            steps_passed=['test1', 'test2'],
            steps_failed=[]),
    ]

    self.assertEqual(
        set(),
        try_job_steps.need_to_trigger('bot', set(['test1', 'test2']), tries))


class WaitingForTest(unittest.TestCase):
  def test_no_tries(self):
    self.assertEqual(
        set(['test1', 'test2']),
        try_job_steps.waiting_for('bot', ['test1', 'test2'], {}))

  def test_failed_try(self):
    tries = [
        CreateRietveldTryJob(
            builder='bot',
            requested_steps=['test1', 'test2'],
            steps_passed=[],
            steps_failed=['test1', 'test2']),
    ]

    self.assertEqual(
        set(['test1', 'test2']),
        try_job_steps.waiting_for('bot', ['test1', 'test2'], tries))

  def test_partial_successful_try(self):
    tries = [
        CreateRietveldTryJob(
            builder='bot',
            requested_steps=['test1', 'test2'],
            steps_passed=['test1'],
            steps_failed=[]),
    ]

    self.assertEqual(
        set(['test2']),
        try_job_steps.waiting_for('bot', ['test1', 'test2'], tries))

  def test_successful_try(self):
    tries = [
        CreateRietveldTryJob(
            builder='bot',
            requested_steps=['test1', 'test2'],
            steps_passed=['test1', 'test2'],
            steps_failed=[]),
    ]

    self.assertEqual(
        set(),
        try_job_steps.waiting_for('bot', ['test1', 'test2'], tries))


class TryJobTriggeredStepsTest(unittest.TestCase):
  def test_waiting_for(self):
    triggered_verifier = try_job_steps.TryJobTriggeredSteps(
        builder_name='triggered_bot',
        trigger_name='parent_bot',
        steps={
            'test1': 'trigger1',
            'test2': 'trigger1',
            'test3': 'trigger2',
        })

    self.assertEqual(
        ('triggered_bot', set(['test1', 'test2', 'test3'])),
        triggered_verifier.waiting_for({}))

  def test_need_to_trigger(self):
    triggered_verifier = try_job_steps.TryJobTriggeredSteps(
        builder_name='triggered_bot',
        trigger_name='parent_bot',
        steps={
            'test1': 'trigger1',
            'test2': 'trigger1',
            'test3': 'trigger2',
        })

    self.assertEqual(
        ('parent_bot', set(['trigger1', 'trigger2'])),
        triggered_verifier.need_to_trigger({}, 1.))

    # With a Try Job running that will run test3, we shouldn't care
    # about trigger2.
    try_jobs = {
        'key1': try_job_on_rietveld.RietveldTryJob(
            init_time=1.,
            builder='parent_bot',
            build=12,
            revision=13,
            requested_steps=['triggered1', 'triggered2'],
            started=1,
            steps_passed=['triggered1', 'triggered2'],
            steps_failed=[],
            clobber=False,
            completed=True,
            tries=1,
            parent_key=None),
        'key2': try_job_on_rietveld.RietveldTryJob(
            init_time=1.,
            builder='triggered_bot',
            build=12,
            revision=13,
            requested_steps=['test1', 'test2', 'test3'],
            started=1,
            steps_passed=[],
            steps_failed=['test1', 'test2'],
            clobber=False,
            completed=False,
            tries=1,
            parent_key='key1')}
    self.assertEqual(
        ('parent_bot', set(['trigger1'])),
        triggered_verifier.need_to_trigger(try_jobs, 1.))

    # A parent bot is running with steps that won't trigger the needed
    # tests, so nothing changes.
    try_jobs['key2'] = CreateRietveldTryJob(
        builder='parent_bot',
        requested_steps=['trigger2'],
        steps_passed=[],
        steps_failed=[])
    self.assertEqual(
        ('parent_bot', set(['trigger1'])),
        triggered_verifier.need_to_trigger(try_jobs, 1.))

    # A parent bot is running steps that will triggered the required tests,
    # so nothing needs to be triggered.
    try_jobs['key3'] = CreateRietveldTryJob(
        builder='parent_bot',
        requested_steps=['trigger1'],
        steps_passed=[],
        steps_failed=[])
    self.assertEqual(
        ('parent_bot', set([])),
        triggered_verifier.need_to_trigger(try_jobs, 1.))

  def test_triggered_bot_found(self):
    """Test that we don't wait on an non-stewed parent if the child is found."""
    triggered_verifier = try_job_steps.TryJobTriggeredSteps(
        builder_name='tester1',
        trigger_name='builder1',
        steps={'test3': 'trigger'})
    try_jobs = {
        'key1': try_job_on_rietveld.RietveldTryJob(
            init_time=1.,
            builder='builder1',
            build=12,
            revision=13,
            requested_steps=['trigger'],
            started=1,
            steps_passed=['trigger'],
            steps_failed=[],
            clobber=False,
            completed=True,
            tries=1,
            parent_key=None),
        'key2': try_job_on_rietveld.RietveldTryJob(
            init_time=1.,
            builder='tester1',
            build=12,
            revision=13,
            requested_steps=['test3'],
            started=1,
            steps_passed=[],
            steps_failed=['test3'],
            clobber=False,
            completed=True,
            tries=1,
            parent_key='key1')}
    self.assertEqual(
        ('builder1', set(['trigger'])),
        triggered_verifier.need_to_trigger(try_jobs, 1.))
    self.assertEqual(
        ('tester1', set(['test3'])),
        triggered_verifier.waiting_for(try_jobs))

  def test_triggered_wait_for_builder(self):
    """Test that we wait for trigger if builder has recently completed."""
    triggered_verifier = try_job_steps.TryJobTriggeredSteps(
        builder_name='tester1',
        trigger_name='builder1',
        steps={'test3': 'trigger'})
    try_jobs = {
        'key1': try_job_on_rietveld.RietveldTryJob(
            init_time=1.,
            builder='builder1',
            build=12,
            revision=13,
            requested_steps=['test10', 'trigger'],
            started=1,
            steps_passed=['test10', 'trigger'],
            steps_failed=[],
            clobber=False,
            completed=True,
            tries=1,
            parent_key=None),
    }
    self.assertEqual(
        ('builder1', set()),
        triggered_verifier.need_to_trigger(try_jobs, 1.))
    self.assertEqual(
        ('tester1', set(['test3'])),
        triggered_verifier.waiting_for(try_jobs))

  def test_not_all_triggered(self):
    """Test that waiting for one triggered job doesn't prevent other triggers
    from getting hit."""
    triggered_verifier = try_job_steps.TryJobTriggeredSteps(
        builder_name='tester1',
        trigger_name='builder1',
        steps={
            'test1': 'trigger1',
            'test2': 'trigger2'})

    try_jobs = {
        'key1': try_job_on_rietveld.RietveldTryJob(
            init_time=1.,
            builder='builder1',
            build=12,
            revision=13,
            requested_steps=['trigger1'],
            started=1,
            steps_passed=['trigger1'],
            steps_failed=[],
            clobber=False,
            completed=True,
            tries=1,
            parent_key=None),
    }

    self.assertEqual(
        ('builder1', set(['trigger2'])),
        triggered_verifier.need_to_trigger(try_jobs, 1.))
    self.assertEqual(
        ('tester1', set(['test1', 'test2'])),
        triggered_verifier.waiting_for(try_jobs))

  def test_triggered_builder_second_pending(self):
    """Test failed trigger jobs do not send trigger if another is pending."""
    now = 1.
    triggered_verifier = try_job_steps.TryJobTriggeredSteps(
        builder_name='tester1',
        trigger_name='builder1',
        steps={'test3': 'trigger'})

    try_jobs = {
        'key1': try_job_on_rietveld.RietveldTryJob(
            init_time=now,
            builder='builder1',
            build=12,
            revision=13,
            requested_steps=['test10', 'trigger'],
            started=int(now),
            steps_passed=['test10', 'trigger'],
            steps_failed=[],
            clobber=False,
            completed=True,
            tries=1,
            parent_key=None),
        'key2': try_job_on_rietveld.RietveldTryJob(
            init_time=now,
            builder='builder1',
            build=13,
            revision=13,
            requested_steps=['test10', 'trigger'],
            started=int(now),
            steps_passed=['test10', 'trigger'],
            steps_failed=[],
            clobber=False,
            completed=True,
            tries=1,
            parent_key=None),
        'key3': try_job_on_rietveld.RietveldTryJob(
            init_time=now,
            builder='tester1',
            build=12,
            revision=13,
            requested_steps=['test3'],
            started=int(now),
            steps_passed=[],
            steps_failed=['test3'],
            clobber=False,
            completed=True,
            tries=1,
            parent_key='key1'),
    }

    self.assertEqual(
        ('builder1', set()),
        triggered_verifier.need_to_trigger(try_jobs, 1.))
    self.assertEqual(
        ('tester1', set(['test3'])),
        triggered_verifier.waiting_for(try_jobs))

  def testGetTriggeredSteps(self):
    triggered_verifier = try_job_steps.TryJobTriggeredSteps(
        builder_name='tester1',
        trigger_name='builder1',
        steps={'test1': 'trigger', 'test2': 'trigger2'})

    self.assertEqual(
        ('tester1', []),
        triggered_verifier.get_triggered_steps('builder_invalid', ['build']))

    self.assertEqual(
        ('tester1', []),
        triggered_verifier.get_triggered_steps('builder1', ['wrong_step']))

    self.assertEqual(
        ('tester1', ['test1']),
        triggered_verifier.get_triggered_steps('builder1', ['trigger']))

    self.assertEqual(
        ('tester1', ['test1', 'test2']),
        triggered_verifier.get_triggered_steps('builder1', ['trigger',
                                                            'trigger2']))


class TryJobTriggeredOrNormalStepsTest(unittest.TestCase):
  def test_need_to_trigger(self):
    now = 1.
    triggered_or_normal_verifier = try_job_steps.TryJobTriggeredOrNormalSteps(
        builder_name='test_triggered',
        trigger_name='builder1',
        steps={
            'test2': 'test2_trigger',
            'test3': 'test3_trigger',
            'test4': 'test4_trigger',
        },
        trigger_bot_steps=[
            'test1',
        ],
        use_triggered_bot=False,
    )
    verifier_use_triggered = try_job_steps.TryJobTriggeredOrNormalSteps(
        builder_name='test_triggered',
        trigger_name='builder1',
        steps={
            'test2': 'test2_trigger',
            'test3': 'test3_trigger',
            'test4': 'test4_trigger',
        },
        trigger_bot_steps=[
            'test1',
        ],
        use_triggered_bot=True,
    )

    self.assertEqual(
        ('builder1', set(['test1', 'test2', 'test3', 'test4'])),
        triggered_or_normal_verifier.need_to_trigger({}, 1.))
    self.assertEqual(
        ('builder1', set(['test1', 'test2_trigger', 'test3_trigger',
                          'test4_trigger'])),
        verifier_use_triggered.need_to_trigger({}, 1.))

    try_jobs = {
        'key1': try_job_on_rietveld.RietveldTryJob(
            init_time=now,
            builder='builder1',
            build=1,
            revision=1,
            requested_steps=['test1', 'test2', 'test3_trigger',
                             'test4_trigger'],
            started=int(now),
            steps_passed=[],
            steps_failed=[],
            clobber=False,
            completed=False,
            tries=1,
            parent_key=None)}
    self.assertEqual(
        ('builder1', set()),
        triggered_or_normal_verifier.need_to_trigger(try_jobs, 1.))
    self.assertEqual(
        ('builder1', set()),
        verifier_use_triggered.need_to_trigger(try_jobs, 1.))

    try_jobs['key1'] = try_job_on_rietveld.RietveldTryJob(
        init_time=now,
        builder='builder1',
        build=1,
        revision=1,
        requested_steps=['test1', 'test2', 'test3_trigger', 'test4_trigger'],
        started=int(now),
        steps_passed=['test1'],
        steps_failed=['test2'],
        clobber=False,
        completed=True,
        tries=1,
        parent_key=None)
    self.assertEqual(
        ('builder1', set(['test2'])),
        triggered_or_normal_verifier.need_to_trigger(try_jobs, 1.))
    self.assertEqual(
        ('builder1', set(['test2_trigger'])),
        verifier_use_triggered.need_to_trigger(try_jobs, 1.))

    try_jobs['key2'] = try_job_on_rietveld.RietveldTryJob(
        init_time=now,
        builder='test_triggered',
        build=1,
        revision=1,
        requested_steps=['test3', 'test4'],
        started=int(now),
        steps_passed=['test3'],
        steps_failed=['test4'],
        clobber=False,
        completed=True,
        tries=1,
        parent_key='key1')
    self.assertEqual(
        ('builder1', set(['test2', 'test4'])),
        triggered_or_normal_verifier.need_to_trigger(try_jobs, 1.))
    self.assertEqual(
        ('builder1', set(['test2', 'test4'])),
        verifier_use_triggered.need_to_trigger(try_jobs, 1.))

    # Add a test bot that wasn't triggered by builder 1 to ensure we don't
    # use its steps.
    try_jobs['key4'] = try_job_on_rietveld.RietveldTryJob(
        init_time=now,
        builder='test_triggered',
        build=2,
        revision=1,
        requested_steps=['test4'],
        started=int(now),
        steps_passed=['test4'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=1,
        parent_key='key3')
    self.assertEqual(
        ('builder1', set(['test2', 'test4'])),
        triggered_or_normal_verifier.need_to_trigger(try_jobs, 1.))
    self.assertEqual(
        ('builder1', set(['test2', 'test4'])),
        verifier_use_triggered.need_to_trigger(try_jobs, 1.))

    # Now retry the failed jobs, ensuring that the verifiers accepts the
    # non-trigger version of test2.
    try_jobs['key5'] = try_job_on_rietveld.RietveldTryJob(
        init_time=now,
        builder='builder1',
        build=2,
        revision=1,
        requested_steps=['test2', 'test4_trigger'],
        started=int(now),
        steps_passed=['test2'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=2,
        parent_key=None)
    self.assertEqual(
        ('builder1', set()),
        triggered_or_normal_verifier.need_to_trigger(try_jobs, 1.))
    self.assertEqual(
        ('builder1', set()),
        verifier_use_triggered.need_to_trigger(try_jobs, 1.))

    try_jobs['key6'] = try_job_on_rietveld.RietveldTryJob(
        init_time=now,
        builder='test_triggered',
        build=3,
        revision=1,
        requested_steps=['test4'],
        started=int(now),
        steps_passed=['test4'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=2,
        parent_key='key5')
    self.assertEqual(
        ('builder1', set()),
        triggered_or_normal_verifier.need_to_trigger(try_jobs, 1.))
    self.assertEqual(
        ('builder1', set()),
        verifier_use_triggered.need_to_trigger(try_jobs, 1.))


  def test_waiting_for(self):
    now = 1.
    triggered_or_normal_verifier = try_job_steps.TryJobTriggeredOrNormalSteps(
        builder_name='test_triggered',
        trigger_name='builder1',
        steps={
            'test2': 'test2_trigger',
            'test3': 'test3_trigger',
            'test4': 'test4_trigger',
        },
        trigger_bot_steps=[
            'test1',
        ],
        use_triggered_bot=False,
    )

    self.assertEqual(
        ('builder1', set(['test1', 'test2', 'test3', 'test4'])),
        triggered_or_normal_verifier.waiting_for({}))

    try_jobs = {
        'key1': try_job_on_rietveld.RietveldTryJob(
            init_time=now,
            builder='builder1',
            build=1,
            revision=1,
            requested_steps=['test1', 'test2', 'test3_trigger',
                             'test4_trigger'],
            started=int(now),
            steps_passed=['test1'],
            steps_failed=['test2'],
            clobber=False,
            completed=True,
            tries=1,
            parent_key=None)}
    self.assertEqual(
        ('builder1', set(['test2', 'test3', 'test4'])),
        triggered_or_normal_verifier.waiting_for(try_jobs))

    try_jobs['key2'] = try_job_on_rietveld.RietveldTryJob(
        init_time=now,
        builder='test_triggered',
        build=1,
        revision=1,
        requested_steps=['test3', 'test4'],
        started=int(now),
        steps_passed=['test3'],
        steps_failed=['test4'],
        clobber=False,
        completed=True,
        tries=1,
        parent_key='key1')
    self.assertEqual(
        ('builder1', set(['test2', 'test4'])),
        triggered_or_normal_verifier.waiting_for(try_jobs))

    # Add a trigger bot that wasn't triggered by builder 1 to ensure we don't
    # use its steps.
    try_jobs['key4'] = try_job_on_rietveld.RietveldTryJob(
        init_time=now,
        builder='test_triggered',
        build=2,
        revision=1,
        requested_steps=['test4'],
        started=int(now),
        steps_passed=['test4'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=1,
        parent_key='key3')
    self.assertEqual(
        ('builder1', set(['test2', 'test4'])),
        triggered_or_normal_verifier.waiting_for(try_jobs))

    # Now retry the failed jobs, ensuring that the verifiers accepts the
    # non-trigger version of test2.
    try_jobs['key5'] = try_job_on_rietveld.RietveldTryJob(
        init_time=now,
        builder='builder1',
        build=2,
        revision=1,
        requested_steps=['test2', 'test4_trigger'],
        started=int(now),
        steps_passed=['test2'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=2,
        parent_key=None)
    self.assertEqual(
        ('builder1', set(['test4'])),
        triggered_or_normal_verifier.waiting_for(try_jobs))

    try_jobs['key6'] = try_job_on_rietveld.RietveldTryJob(
        init_time=now,
        builder='test_triggered',
        build=3,
        revision=1,
        requested_steps=['test4'],
        started=int(now),
        steps_passed=['test4'],
        steps_failed=[],
        clobber=False,
        completed=True,
        tries=2,
        parent_key='key5')
    self.assertEqual(
        ('builder1', set()),
        triggered_or_normal_verifier.waiting_for(try_jobs))


if __name__ == '__main__':
  if '-v' in sys.argv:
    unittest.TestCase.maxDiff = None
  unittest.main()
