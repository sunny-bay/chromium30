#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Takes in a test name and retrives all the output that the swarm server
has produced for tests with that name. This is expected to be called as a
build step."""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from common import find_depot_tools  # pylint: disable=W0611
from common import gtest_utils

# From depot tools/
import fix_encoding


NO_OUTPUT_FOUND = (
    'No output produced by the test, it may have failed to run.\n'
    'Showing all the output, including swarm specific output.\n'
    '\n')


def gen_shard_output(result, gtest_parser):
  """Returns output for swarm shard."""
  index = result['config_instance_index']
  machine_id = result['machine_id']
  machine_tag = result.get('machine_tag', 'unknown')

  header = (
    '\n'
    '================================================================\n'
    'Begin output from shard index %s (machine tag: %s, id: %s)\n'
    '================================================================\n'
    '\n') % (index, machine_tag, machine_id)

  # If we fail to get output, we should always mark it as an error.
  if result['output']:
    map(gtest_parser.ProcessLine, result['output'].splitlines())
    content = result['output']
  else:
    content = NO_OUTPUT_FOUND

  test_exit_codes = (result['exit_codes'] or '1').split(',')
  test_exit_code = max(int(i) for i in test_exit_codes)
  test_exit_code = test_exit_code or int(not result['output'])

  footer = (
    '\n'
    '================================================================\n'
    'End output from shard index %s (machine tag: %s, id: %s). Return %d\n'
    '================================================================\n'
  ) % (index, machine_tag, machine_id, test_exit_code)

  return header + content + footer, test_exit_code


def gen_summary_output(failed_tests, exit_code, shards_remaining):
  out = 'Summary for all the shards:\n'
  if failed_tests:
    plural = 's' if len(failed_tests) > 1 else ''
    out += '%d test%s failed, listed below:\n' % (len(failed_tests), plural)
    out += ''.join('  %s\n' % test for test in failed_tests)

  if shards_remaining:
    out += 'Not all shards were executed.\n'
    out += 'The following gtest shards weren\'t run:\n'
    out += ''.join('  %d\n' % shard_id for shard_id in shards_remaining)
    exit_code = exit_code or 1
  elif not failed_tests:
    out += 'All tests passed.'
  return out, exit_code


def GetSwarmResults(
    swarm_get_results, swarm_base_url, test_keys, timeout, max_threads):
  gtest_parser = gtest_utils.GTestLogParser()
  exit_code = None
  shards_remaining = range(len(test_keys))
  first_result = True
  for index, result in swarm_get_results.yield_results(
      swarm_base_url, test_keys, timeout, max_threads):
    assert index == result['config_instance_index']
    if first_result and result['num_config_instances'] != len(test_keys):
      # There are more test_keys than actual shards.
      shards_remaining = shards_remaining[:result['num_config_instances']]
    shards_remaining.remove(index)
    first_result = False
    output, test_exit_code = gen_shard_output(result, gtest_parser)
    print output
    exit_code = max(exit_code, test_exit_code)

  output, exit_code = gen_summary_output(
      gtest_parser.FailedTests(),
      exit_code,
      shards_remaining)
  print output
  return exit_code


def main():
  src_swarming_client = os.path.join(
      os.getcwd(), 'src', 'tools', 'swarming_client')

  # This is the previous path. This can be removed around 2013-12-01.
  src_swarm_client = os.path.join(os.getcwd(), 'src', 'tools', 'swarm_client')

  if os.path.isdir(src_swarming_client):
    sys.path.insert(0, src_swarming_client)
  elif os.path.isdir(src_swarm_client):
    sys.path.insert(0, src_swarm_client)
  else:
    print >> sys.stderr, 'Failed to find swarm_client at %s or %s' % (
        src_swarming_client, src_swarm_client)
    return 1

  import swarm_get_results  # pylint: disable=F0401

  parser, options, test_name = swarm_get_results.parse_args()
  if not options.shards:
    parser.error('The number of shards expected must be passed in.')
  test_keys = swarm_get_results.get_test_keys(
      options.url, test_name, options.timeout)
  if not test_keys:
    parser.error('No test keys to get results with.')

  options.shards = int(options.shards)
  if options.shards == -1:
    options.shards = len(test_keys)
  elif len(test_keys) < options.shards:
    print >> sys.stderr, ('Warning: Test should have %d shards, but only %d '
                          'test keys were found' % (options.shards,
                                                    len(test_keys)))

  return GetSwarmResults(
      swarm_get_results, options.url, test_keys, options.timeout, None)


if __name__ == '__main__':
  fix_encoding.fix_encoding()
  sys.exit(main())
