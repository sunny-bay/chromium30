#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Functions for adding results to perf dashboard."""

import httplib
import json
import os
import urllib
import urllib2

from slave import slave_utils

# The paths in the results dashboard URLs for sending and viewing results.
SEND_RESULTS_PATH = '/add_point'
RESULTS_LINK_PATH = '/report?masters=%s&bots=%s&tests=%s&rev=%s'
# CACHE_DIR/CACHE_FILENAME will be created in options.build_dir to cache
# results which need to be retried.
CACHE_DIR = 'results_dashboard'
CACHE_FILENAME = 'results_to_retry'


#TODO(xusydoc): set fail_hard to True when bots stabilize. See crbug.com/222607.
def SendResults(logname, lines, system, test, url, masterid,
                buildername, buildnumber, build_dir, supplemental_columns,
                fail_hard=False):
  if not logname.endswith('-summary.dat'):
    return

  new_results_line = _GetResultsJson(logname, lines, system, test, url,
                                     masterid, buildername, buildnumber,
                                     supplemental_columns)
  # Write the new request line to the cache, in case of errors.
  cache_filename = _GetCacheFileName(build_dir)
  cache = open(cache_filename, 'ab')
  cache.write('\n' + new_results_line)
  cache.close()

  # Send all the results from this run and the previous cache to the dashboard.
  cache = open(cache_filename, 'rb')
  cache_lines = cache.readlines()
  cache.close()
  errors = []
  lines_to_retry = []
  fatal_error = False
  for index, line in enumerate(cache_lines):
    line = line.strip()
    if not line:
      continue
    error = _SendResultsJson(url, line)
    if error:
      if index != len(cache_lines) -1:
        # This request has already been tried before, now it's fatal.
        fatal_error = True
      lines_to_retry = [l.strip() for l in cache_lines[index:] if l.strip()]
      errors.append(error)
      break

  # Write any failing requests to the cache.
  cache = open(cache_filename, 'wb')
  cache.write('\n'.join(set(lines_to_retry)))
  cache.close()

  # Print any errors, and if there was a fatal error, it should be an exception.
  for error in errors:
    print error
  if fatal_error:
    if fail_hard:
      print 'Multiple failures uploading to dashboard.'
      print '@@@STEP_EXCEPTION@@@'
    else:
      print 'Multiple failures uploading to dashboard.'
      print 'You may have to whitelist your bot, please see crbug.com/222607.'
      print '@@@STEP_WARNINGS@@@'

def _GetCacheFileName(build_dir):
  """Gets the cache filename, creating the file if it does not exist."""
  cache_dir = os.path.join(os.path.abspath(build_dir), CACHE_DIR)
  if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
  cache_filename = os.path.join(cache_dir, CACHE_FILENAME)
  if not os.path.exists(cache_filename):
    # Create the file.
    open(cache_filename, 'wb').close()
  return cache_filename

def _GetResultsJson(logname, lines, system, test, url, masterid,
                    buildername, buildnumber, supplemental_columns):
  results_to_add = []
  master = slave_utils.GetActiveMaster()
  bot = system
  graph = logname.replace('-summary.dat', '')
  for line in lines:
    data = json.loads(line)
    # TODO(sullivan): the dashboard requires ordered integer revision numbers.
    # If the revision is not an integer, assume it's a git hash and send the
    # buildnumber for an ordered revision until we can come up with a more
    # correct solution.
    revision = data['rev']
    git_hash = None
    try:
      revision = int(revision)
    except ValueError:
      revision = int(buildnumber)
      git_hash = data['rev']

    for (trace, values) in data['traces'].iteritems():
      # Test to make sure we don't have x/y data.
      for value in values:
        if not isinstance(value, basestring):
          # http://crbug.com/224719
          raise NotImplementedError('x/y graphs not supported at this time.')

      important = trace in data.get('important', [])
      if trace == graph + '_ref':
        trace = 'ref'
      graph = graph.replace('_by_url', '')
      trace = trace.replace('/', '_')
      test_path = '%s/%s/%s' % (test, graph, trace)
      if graph == trace:
        test_path = '%s/%s' % (test, graph)
      result = {
          'master': master,
          'bot': system,
          'test': test_path,
          'revision': revision,
          'value': values[0],
          'error': values[1],
          'masterid': masterid,
          'buildername': buildername,
          'buildnumber': buildnumber,
      }
      if 'webkit_rev' in data and data['webkit_rev'] != 'undefined':
        result.setdefault(
            'supplemental_columns', {})['r_webkit_rev'] = data['webkit_rev']
      if 'v8_rev' in data and data['v8_rev'] != 'undefined':
        result.setdefault(
            'supplemental_columns', {})['r_v8_rev'] = data['v8_rev']
      if git_hash:
        result.setdefault(
            'supplemental_columns', {})['r_chromium_rev'] = git_hash
      result.setdefault('supplemental_columns', {}).update(supplemental_columns)
      if data.get('units'):
        result['units'] = data['units']
      if important:
        result['important'] = True
      results_to_add.append(result)
  _PrintLinkStep(url, master, bot, test, revision)
  return json.dumps(results_to_add)


def _SendResultsJson(url, results_json):
  data = urllib.urlencode({'data': results_json})
  req = urllib2.Request(url + SEND_RESULTS_PATH, data)
  try:
    urllib2.urlopen(req)
  except urllib2.HTTPError, e:
    return 'HTTPError: %d for JSON %s\n' % (e.code, results_json)
  except urllib2.URLError, e:
    return 'URLError: %s for JSON %s\n' % (str(e.reason), results_json)
  except httplib.HTTPException, e:
    return 'HTTPException for JSON %s\n' % results_json
  return None

def _PrintLinkStep(url, master, bot, test_path, revision):
  results_link = url + RESULTS_LINK_PATH % (
      urllib.quote(master),
      urllib.quote(bot),
      urllib.quote(test_path),
      revision)
  print '@@@STEP_LINK@%s@%s@@@' % ('Results Dashboard', results_link)
