# coding=utf8
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import model


# CQ uses this delay to decide if a triggered job hasn't show up from
# rietveld processing time or if it has gone missing
PROPOGATION_DELAY_S = 3 * 60 * 60


def need_to_trigger(builder_name, need_to_run, try_jobs):
  """Returns which tests need to be triggered.

  These are the tests that are not pending on any try job, either running or
  in the pending list.
  """
  need_to_run = set(need_to_run)
  for try_job in try_jobs:
    if try_job.builder == builder_name:
      need_to_run -= set(try_job.steps_passed)
      if not try_job.completed:
        if try_job.requested_steps == []:
          # Special case jobs discovered by CQ that it did not send. Wait for
          # these jobs to complete rather than trying to interpret the filter
          assert try_job.started
          need_to_run.clear()
        else:
          need_to_run -= (
              set(try_job.requested_steps) - set(try_job.steps_failed))

  return need_to_run


def waiting_for(builder_name, tests, try_jobs):
  """Returns the tests that we are waiting for results on pending or running
  builds.
  """
  tests = set(tests)
  for try_job in try_jobs:
    if try_job.builder == builder_name:
      tests -= set(try_job.steps_passed)
  return tests


class TryJobStepsBase(model.PersistentMixIn):
  builder_name = unicode

  # Name of the prerequisite builder.
  prereq_builder = unicode
  # List of prerequisite tests to look for.
  prereq_tests = list

  def __init__(self, **kwargs):
    kwargs.setdefault('prereq_builder', u'')
    kwargs.setdefault('prereq_tests', [])
    required = set(self._persistent_members())
    actual = set(kwargs)
    assert required == actual, (required - actual, required, actual)
    super(TryJobStepsBase, self).__init__(**kwargs)
    # Then mark it read-only.
    self._read_only = True

  @model.immutable
  def unmet_prereqs(self, try_jobs):
    """
    Determine if this TryJobSteps has unmet prerequisites.

    Returns True iff prereq is unmet.
    """
    if not self.prereq_builder or not self.prereq_tests:
      return None
    unmet_steps = set(self.prereq_tests)
    for try_job in try_jobs.itervalues():
      if try_job.builder == self.prereq_builder:
        unmet_steps -= set(try_job.steps_passed)
    return bool(unmet_steps)

  @model.immutable
  def get_triggered_steps(self, _builder, _steps):
    """Returns the steps on this builder that will get triggered by the given
    builder and its steps, which is always None since this isn't a triggered
    bot."""
    return (self.builder_name, [])


class TryJobSteps(TryJobStepsBase):
  steps = list

  @model.immutable
  def waiting_for(self, try_jobs):
    """Returns the tests that we are waiting for results on pending or running
    builds.
    """
    return (self.builder_name,
            waiting_for(self.builder_name, self.steps, try_jobs.itervalues()))

  @model.immutable
  def need_to_trigger(self, try_jobs, _now):
    """Returns which tests need to be triggered.

    These are the tests that are not pending on any try job, either running or
    in the pending list.
    """
    if self.unmet_prereqs(try_jobs):
      return (self.builder_name, [])
    return (self.builder_name,
            need_to_trigger(self.builder_name, self.steps,
                            try_jobs.itervalues()))


class TryJobTriggeredSteps(TryJobStepsBase):
  # The name of the bot that triggers this bot.
  trigger_name = unicode
  # Maps the triggered_bot_step -> trigger_bot_step required to trigger it.
  steps = dict

  @model.immutable
  def _triggered_try_jobs(self, try_jobs):
    """Return all the try jobs that were on this builder and had been trigger
    by the trigger_name bot."""
    triggered_try_jobs = []
    for try_job in try_jobs.itervalues():
      if (try_job.builder == self.builder_name and
          try_job.parent_key and try_job.parent_key in try_jobs and
          try_jobs[try_job.parent_key].builder == self.trigger_name):
        triggered_try_jobs.append(try_job)

    return triggered_try_jobs

  @model.immutable
  def waiting_for(self, try_jobs):
    """Returns the tests that we are waiting for results on pending or running
    builds.
    """
    return (self.builder_name,
            waiting_for(self.builder_name, self.steps,
                        self._triggered_try_jobs(try_jobs)))

  @model.immutable
  def need_to_trigger(self, try_jobs, now):
    """Returns which tests need to be triggered.

    These are the tests that are not pending on any try job, either running or
    in the pending list.
    """
    if self.unmet_prereqs(try_jobs):
      return (self.builder_name, [])
    need_to_run = set(self.steps)
    steps_to_trigger = need_to_trigger(self.builder_name, need_to_run,
                                       self._triggered_try_jobs(try_jobs))

    # Convert the steps to trigger to their trigger options.
    trigger_need_to_run = set(self.steps[step] for step in steps_to_trigger)

    # See which triggered builds have already started, so we can then ignore
    # their parents when seeing if more triggered build are on the way.
    detected_triggered_keys = set(
        job.parent_key for key, job in try_jobs.iteritems()
        if job.builder == self.builder_name)

    # Remove any trigger options that are waiting to run from the set to
    # trigger.
    for key, try_job in try_jobs.iteritems():
      if try_job.builder == self.trigger_name:
        if (try_job.completed and
            not (now - try_job.init_time > PROPOGATION_DELAY_S) and
            key not in detected_triggered_keys):
          # If we get here a triggered build hasn't started yet, so wait for
          # any steps that should run on the triggered build.
          trigger_need_to_run -= (
              set(step for step in self.steps.itervalues()
                  if step in try_job.requested_steps))
        if not try_job.completed:
          trigger_need_to_run -= (
              set(try_job.requested_steps) - set(try_job.steps_failed))

    return (self.trigger_name, trigger_need_to_run)

  @model.immutable
  def get_triggered_steps(self, builder, steps):
    """Returns the steps on this builder that will get triggered by the given
    builder and its steps."""
    trigger_steps = []
    if builder == self.trigger_name:
      trigger_steps = [key for key, value in self.steps.iteritems()
                       if value in steps]

    return (self.builder_name, sorted(trigger_steps))


class TryJobTriggeredOrNormalSteps(TryJobTriggeredSteps):
  """This class assumes that the triggered names can be run
  on the trigger bot with the same name that they appear with on
  the triggered bot."""

  # The list of steps that have to be run on the trigger bot.
  trigger_bot_steps = list

  # True if the triggered bot should try and run the missing tests.
  use_triggered_bot = bool

  @model.immutable
  def need_to_trigger(self, try_jobs, now):
    if self.unmet_prereqs(try_jobs):
      return (self.builder_name, [])
    name, steps = super(TryJobTriggeredOrNormalSteps,
                        self).need_to_trigger(try_jobs, now)

    # Remove any tests where that could still be triggered by the trigger bot.
    steps = need_to_trigger(self.trigger_name, steps, try_jobs.itervalues())

    # Convert the trigger names to the triggered names.
    steps = set(step for step, trigger
                in self.steps.iteritems() if trigger in steps)

    # Add the trigger bot only steps and remove ones that have passed.
    steps = steps.union(self.trigger_bot_steps)
    steps = need_to_trigger(self.trigger_name, steps, try_jobs.itervalues())

    # If we want to use the triggered bot, convert the steps backs to their
    # trigger name (where possible).
    if self.use_triggered_bot:
      # TODO(csharp): Remove this once the triggered bots should always handle
      # retry (limit it to one attempt each to prevent too much breakage).
      if any(try_job.builder == self.builder_name
             for try_job in try_jobs.itervalues()):
        return name, steps

      steps = set(self.steps.get(step, step) for step in steps)

    return name, steps

  @model.immutable
  def waiting_for(self, try_jobs):
    steps = waiting_for(self.builder_name, self.steps,
                        self._triggered_try_jobs(try_jobs))

    # Add the steps that can only run on the trigger bot and see what hasn't
    # passed on the trigger bot yet.
    steps = steps.union(self.trigger_bot_steps)

    steps = waiting_for(self.trigger_name, steps, try_jobs.itervalues())

    return self.trigger_name, steps
