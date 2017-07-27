# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the Swarm master BuildFactory's.

Based on chromium_factory.py and adds chromium-on-swarm-specific steps.

Common usage:
- For a split builder&tester configuration, use:
  - One ChromiumFactory() builder with 'run_default_swarm_tests' set to the list
    of tests to run on Swarm on the 'tester'.
  - One SwarmTestBuilder() builder named 'swarm_triggered', the builder name
    is currently hardcoded.

- For a single buildertester configuration, use:
  - SwarmFactory()
"""

from master.factory import build_factory
from master.factory import chromium_factory
from master.factory import swarm_commands


class SwarmTest(object):
  """A small helper class containing any required details to run a
     swarm test.
  """
  def __init__(self, test_name, shards):
    self.test_name = test_name
    self.shards = shards


SWARM_TESTS = [
    # The test listed below must be in the REVERSE ORDER of latency to get
    # results, e.g. the slowest test should be LAST.
    #
    # The goal here is to take ~5m of actual test run per shard, e.g. the
    # 'RunTest' section in the logs, so that the trade-off of setup time
    # overhead vs latency is reasonable. The overhead is in the ~90s range, with
    # the vast majority being downloading the executable files. While it can be
    # lowered, it'll stay in the "few seconds" range due to the sheer size of
    # the executables to map.
    SwarmTest('base_unittests', 1),
    SwarmTest('net_unittests', 1),
    SwarmTest('unit_tests', 2),
    SwarmTest('interactive_ui_tests', 3),
    SwarmTest('sync_integration_tests', 4),
    SwarmTest('browser_tests', 10),
]


def SwarmTestBuilder(swarm_server, isolation_outdir, tests):
  """Create a basic swarm builder that runs tests via Swarm.

  To clarify, this 'buildbot builder' doesn't compile.
  """
  valid_tests = set(s.test_name for s in SWARM_TESTS)
  assert not any(t not in valid_tests for t in tests)

  # No need of a window manager when only retrieving results.
  f = build_factory.BuildFactory()

  # Some of the scripts require a build_dir to be set, so set it even
  # if the machine might not have it (It shouldn't matter what this is).
  build_dir = 'chrome'

  swarm_command_obj = swarm_commands.SwarmCommands(factory=f,
                                                   build_dir=build_dir)
  swarm_tests = [s for s in SWARM_TESTS if s.test_name in tests]

  # Checks out the scripts at the right revision so the trigger can happen.
  swarm_command_obj.AddUpdateSwarmClientStep()

  # Send the swarm tests to the swarm server.
  swarm_command_obj.AddTriggerSwarmTestStep(
      swarm_server=swarm_server,
      isolation_outdir=isolation_outdir,
      tests=swarm_tests,
      doStepIf=swarm_commands.TestStepFilterTriggerSwarm)

  # Latency is everything, update scripts only after.
  swarm_command_obj.AddUpdateScriptStep()

  # Collect the results
  for swarm_test in swarm_tests:
    swarm_command_obj.AddGetSwarmTestStep(swarm_server, swarm_test.test_name,
                                          swarm_test.shards)

  return f


class SwarmFactory(chromium_factory.ChromiumFactory):
  """Runs swarm tests in a single build, contrary to ChromiumFactory which can
  trigger swarm jobs but doesn't look for results.

  This factory does both, which is usually a waste of resource, you don't want
  to waste a powerful slave sitting idle, waiting for swarm results. Used on
  chromium.swarm canary for simplicity purpose.
  """
  def SwarmFactory(
      self, tests, options, factory_properties, swarm_server, isolate_server):
    """Only Release is supported for now.

    Caller must not reuse factory_properties since it is modified in-place.
    """
    valid_tests = set(s.test_name for s in SWARM_TESTS)
    assert not (set(tests) - set(valid_tests))
    target = 'Release'

    factory_properties.setdefault('gclient_env', {})
    factory_properties['gclient_env'].setdefault('GYP_DEFINES', '')
    factory_properties['gclient_env']['GYP_DEFINES'] += (
        ' test_isolation_mode=hashtable test_isolation_outdir=' +
        isolate_server)

    # Do not pass the tests to the ChromiumFactory, they'll be processed below.
    f = self.ChromiumFactory(target=target,
                             options=options,
                             factory_properties=factory_properties)

    swarm_command_obj = swarm_commands.SwarmCommands(
        f,
        target,
        self._build_dir,
        self._target_platform)

    using_ninja = '--build-tool=ninja' in (options or []),

    swarm_command_obj.AddGenerateIsolatedHashesStep(
        using_ninja=using_ninja, tests=tests, doStepIf=True)

    # Send of all the test requests as a single step.
    swarm_tests = [s for s in SWARM_TESTS if s.test_name in tests]
    swarm_command_obj.AddTriggerSwarmTestStep(swarm_server, isolate_server,
                                              swarm_tests, True)

    # Each test has its output returned as its own step.
    for test in swarm_tests:
      swarm_command_obj.AddGetSwarmTestStep(swarm_server, test.test_name,
                                            test.shards)

    return f


class IsolatedFactory(chromium_factory.ChromiumFactory):
  """Run all the tests in isolated mode, without using swarm at all.

  It's a normal BuilderTester but runs all its tests in isolated mode
  inconditionally.
  """
  def IsolatedFactory(self, tests, options, factory_properties):
    """Only Release is supported for now.

    Caller must not reuse factory_properties since it is modified in-place.
    """
    target = 'Release'
    tests = tests[:]
    factory_properties.setdefault('gclient_env', {})
    factory_properties['gclient_env'].setdefault('GYP_DEFINES', '')
    factory_properties['gclient_env']['GYP_DEFINES'] += (
        ' test_isolation_mode=check')

    # Do not pass the tests to the ChromiumFactory, they'll be processed below.
    f = self.ChromiumFactory(target=target,
                             options=options,
                             factory_properties=factory_properties)

    swarm_command_obj = swarm_commands.SwarmCommands(
        f,
        target,
        self._build_dir,
        self._target_platform)

    using_ninja = '--build-tool=ninja' in (options or []),

    # Reorder the tests by the order specified in SWARM_TESTS. E.g. the slower
    # tests are retrieved last.
    for swarm_test in SWARM_TESTS:
      if swarm_test.test_name in tests:
        tests.remove(swarm_test.test_name)
        swarm_command_obj.AddIsolateTest(
            swarm_test.test_name, using_ninja=using_ninja)

    assert not tests
    return f
