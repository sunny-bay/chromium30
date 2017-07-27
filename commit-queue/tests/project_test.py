#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Integration tests for project.py."""

import logging
import os
import random
import shutil
import string
import StringIO
import sys
import tempfile
import time
import unittest
import urllib2

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..'))

import projects
from verification import base
from verification import presubmit_check
from verification import try_job_on_rietveld

# From /tests
import mocks


def _try_comment(pc, issue=31337):
  return (
      "add_comment(%d, u'%shttp://localhost/user@example.com/%d/1\\n')" %
      (issue, pc.TRYING_PATCH.replace('\n', '\\n'),
        issue))


class TestCase(mocks.TestCase):
  def setUp(self):
    super(TestCase, self).setUp()
    self.mock(projects, '_read_lines', self._read_lines)
    self.mock(
        projects.async_push,
        'AsyncPush', lambda _1, _2: mocks.AsyncPushMock(self))
    class Dummy(object):
      @staticmethod
      def get_list():
        return []
    if not projects.chromium_committers:
      projects.chromium_committers = Dummy()
    self.mock(
        projects.chromium_committers, 'get_list', self._get_committers_list)
    if not projects.nacl_committers:
      projects.nacl_committers = Dummy()
    self.mock(projects.nacl_committers, 'get_list', self._get_committers_list)
    self.mock(presubmit_check.subprocess2, 'check_output', self._check_output)
    self.mock(urllib2, 'urlopen', self._urlopen)
    self.mock(time, 'time', self._time)
    self.check_output = []
    self.read_lines = []
    self.urlrequests = []
    self.time = []

  def tearDown(self):
    try:
      if not self.has_failed():
        self.assertEqual([], self.check_output)
        self.assertEqual([], self.read_lines)
        self.assertEqual([], self.urlrequests)
        self.assertEqual([], self.time)
    finally:
      super(TestCase, self).tearDown()

  # Mocks
  def _urlopen(self, url):
    if not self.urlrequests:
      self.fail(url)
    expected_url, data = self.urlrequests.pop(0)
    self.assertEqual(expected_url, url)
    return StringIO.StringIO(data)

  @staticmethod
  def _get_committers_list():
    return ['user@example.com', 'user@example.org']

  def _read_lines(self, root, error):
    if not self.read_lines:
      self.fail(root)
    a = self.read_lines.pop(0)
    self.assertEqual(a[0], root)
    self.assertEqual(a[1], error)
    return a[2]

  def _check_output(self, *args, **kwargs):
    # For now, ignore the arguments. Change if necessary.
    if not self.check_output:
      self.fail((args, kwargs))
    return self.check_output.pop(0)

  def _time(self):
    self.assertTrue(self.time)
    return self.time.pop(0)


class ProjectTest(TestCase):
  def setUp(self):
    super(ProjectTest, self).setUp()

  def test_loaded(self):
    members = (
        'blink', 'chromium', 'chromium_deps', 'gyp', 'nacl', 'skia', 'tools')
    self.assertEqual(sorted(members), sorted(projects.supported_projects()))

  def test_all(self):
    # Make sure it's possible to load each project.
    self.time = [1] * 2
    root_dir = os.path.join(os.getcwd(), 'root_dir')
    chromium_status_pwd = os.path.join(root_dir, '.chromium_status_pwd')
    skia_status_pwd = os.path.join(root_dir, '.skia_status_pwd')
    mapping = {
      'blink': {
        'lines': [
          chromium_status_pwd, 'chromium-status password', ['foo'],
        ],
        'pre_patch_verifiers': ['project_bases', 'reviewer_lgtm'],
        'verifiers': ['try job rietveld', 'tree status'],
      },
      'chromium': {
        'lines': [
          chromium_status_pwd, 'chromium-status password', ['foo'],
        ],
        'pre_patch_verifiers': ['project_bases', 'reviewer_lgtm'],
        'verifiers': ['try job rietveld', 'tree status'],
      },
      'chromium_deps': {
        'lines': [
          chromium_status_pwd, 'chromium-status password', ['foo'],
        ],
        'pre_patch_verifiers': ['project_bases', 'reviewer_lgtm'],
        'verifiers': ['presubmit'],
      },
      'gyp': {
        'lines': [
          chromium_status_pwd, 'chromium-status password', ['foo'],
        ],
        'pre_patch_verifiers': ['project_bases', 'reviewer_lgtm'],
        'verifiers': ['tree status'],
      },
      'nacl': {
        'lines': [
          chromium_status_pwd, 'chromium-status password', ['foo'],
        ],
        'pre_patch_verifiers': ['project_bases', 'reviewer_lgtm'],
        'verifiers': ['presubmit', 'tree status'],
      },
      'skia': {
        'lines': [
          skia_status_pwd, 'skia-status password', ['foo'],
        ],
        'pre_patch_verifiers': ['project_bases', 'reviewer_lgtm'],
        'verifiers': ['presubmit', 'tree status'],
      },
      'tools': {
        'lines': [
          chromium_status_pwd, 'chromium-status password', ['foo'],
        ],
        'pre_patch_verifiers': ['project_bases', 'reviewer_lgtm'],
        'verifiers': ['presubmit'],
      },
    }
    for project in sorted(projects.supported_projects()):
      logging.debug(project)
      self.assertEqual([], self.read_lines)
      expected = mapping.pop(project)
      self.read_lines = [expected['lines']]
      p = projects.load_project(
          project, 'user', root_dir, self.context.rietveld, True)
      self.assertEqual(
          expected['pre_patch_verifiers'],
          [x.name for x in p.pre_patch_verifiers],
          (expected['pre_patch_verifiers'],
           [x.name for x in p.pre_patch_verifiers],
           project))
      self.assertEqual(
          expected['verifiers'], [x.name for x in p.verifiers],
          (expected['verifiers'],
           [x.name for x in p.verifiers],
           project))
      if project == 'tools':
        # Add special checks for it.
        project_bases_verifier = p.pre_patch_verifiers[0]
        branch = '\\@[a-zA-Z0-9\\-_\\.]+$'
        self.assertEqual(
            [
              # svn
              '^svn\\:\\/\\/svn\\.chromium\\.org\\/chrome/trunk/tools(|/.*)$',
              '^svn\\:\\/\\/chrome\\-svn\\/chrome/trunk/tools(|/.*)$',
              '^svn\\:\\/\\/chrome\\-svn\\.corp\\/chrome/trunk/tools(|/.*)$',
              '^svn\\:\\/\\/chrome\\-svn\\.corp\\.google\\.com\\/chrome/trunk/'
                  'tools(|/.*)$',
              '^http\\:\\/\\/src\\.chromium\\.org\\/svn/trunk/tools(|/.*)$',
              '^https\\:\\/\\/src\\.chromium\\.org\\/svn/trunk/tools(|/.*)$',
              '^http\\:\\/\\/src\\.chromium\\.org\\/chrome/trunk/tools(|/.*)$',
              '^https\\:\\/\\/src\\.chromium\\.org\\/chrome/trunk/tools(|/.*)$',

              # git
              '^https?\\:\\/\\/git\\.chromium\\.org\\/git\\/chromium\\/tools\\/'
                  '([a-z0-9\\-_]+)(?:\\.git)?' + branch,
              '^https?\\:\\/\\/git\\.chromium\\.org\\/chromium\\/tools\\/'
                  '([a-z0-9\\-_]+)(?:\\.git)?' + branch,
              '^https?\\:\\/\\/chromium\\.googlesource\\.com\\/chromium\\/tools'
                  '\\/([a-z0-9\\-_]+)(?:\\.git)?' + branch,
            ],
            project_bases_verifier.project_bases)
    self.assertEqual({}, mapping)


class ChromiumStateLoad(TestCase):
  # Load a complete state and ensure the code is reacting properly.
  def setUp(self):
    super(ChromiumStateLoad, self).setUp()
    self.buildbot = mocks.BuildbotMock(self)
    self.mock(
        try_job_on_rietveld.buildbot_json, 'Buildbot', lambda _: self.buildbot)
    self.tempdir = tempfile.mkdtemp(prefix='project_test')
    self.now = None

  def tearDown(self):
    try:
      shutil.rmtree(self.tempdir)
    finally:
      super(ChromiumStateLoad, self).tearDown()

  def _add_build(self, builder, buildnumber, revision, steps, completed):
    """Adds a build with a randomly generated key."""
    key = ''.join(random.choice(string.ascii_letters) for _ in xrange(8))
    build = self.buildbot.add_build(
        builder, buildnumber, revision, key, completed, None)
    build.steps.extend(steps)
    return key

  def _LoadPendingManagerState(self, issue):
    self.urlrequests = [
      ( 'http://chromium-status.appspot.com/allstatus?format=json&endTime=%d' %
            (self.now - 300),
        # In theory we should return something but nothing works fine.
        '[]'),
    ]
    self.read_lines = [
        [
          os.path.join(self.tempdir, '.chromium_status_pwd'),
          'chromium-status password',
          ['foo'],
        ],
    ]
    self.context.rietveld.patchsets_properties[(issue, 1)] = {}

    self.time = [self.now] * 1
    pc = projects.load_project(
        'chromium', 'invalid', self.tempdir, self.context.rietveld, False)
    self.assertEqual(0, len(self.time))
    pc.context = self.context
    pc.load(os.path.join(ROOT_DIR, 'chromium.%d.json' % issue))

    # Verify the content a bit.
    self.assertEqual(1, len(pc.queue.iterate()))
    self.assertEqual(issue, pc.queue.get(issue).issue)
    expected = [
      u'presubmit',
      u'project_bases',
      u'reviewer_lgtm',
      u'tree status',
      u'try job rietveld',
    ]
    self.assertEqual(expected, sorted(pc.queue.get(issue).verifications))

    return pc

  def _verify_final_state(self, verifications, why_not, rietveld_calls):
    for name, obj in verifications.iteritems():
      if name == 'try job rietveld':
        self.assertEqual(base.PROCESSING, obj.get_state(), name)
        self.assertEqual(why_not, obj.why_not())
      else:
        self.assertEqual(base.SUCCEEDED, obj.get_state(), name)
        self.assertEqual(None, obj.why_not())

      if name == 'tree status':
        self.time = [self.now] * 1
        self.assertEqual(False, obj.postpone(), name)
        self.assertEqual(0, len(self.time))
      else:
        self.assertEqual(False, obj.postpone(), name)
    self.context.rietveld.check_calls(rietveld_calls)

  def testLoadState(self):
    self.now = 1354207000.
    issue = 31337
    pending_manager = self._LoadPendingManagerState(issue)

    # Then fix the crap out of it.
    self.time = [self.now] * 3
    pending_manager.update_status()
    self.assertEqual(0, len(self.time))
    self.assertEqual(1, len(pending_manager.queue.iterate()))

    why_not = (u'Waiting for the following jobs:\n'
               '  win_rel: sync_integration_tests\n')
    rietveld_calls = [
        "trigger_try_jobs(%d, 1, 'CQ', False, 'HEAD', {u'win_rel': "
        "[u'sync_integration_tests']})" % issue
    ]
    self._verify_final_state(pending_manager.queue.get(issue).verifications,
                             why_not, rietveld_calls)

  def testLoadState11299256(self):
    # Loads a saved state and try to revive it.
    self.now = 1354551606.
    issue = 11299256
    pending_manager = self._LoadPendingManagerState(issue)
    self._add_build('ios_rel_device', 1, 2, [], 4)

    # Then fix the crap out of it.
    self.time = [self.now] * 3
    pending_manager.update_status()
    self.assertEqual(0, len(self.time))
    self.assertEqual(1, len(pending_manager.queue.iterate()))

    why_not = (u'Waiting for the following jobs:\n'
                '  ios_rel_device: compile\n')
    rietveld_calls = [
        "trigger_try_jobs(%d, 1, 'CQ', False, 'HEAD', {u'ios_rel_device': "
        "[u'compile']})" % issue
    ]
    self._verify_final_state(pending_manager.queue.get(issue).verifications,
                             why_not, rietveld_calls)

  def testLoadState12208028(self):
    # Loads a saved state and try to revive it.
    self.now = 1360256000.
    issue = 12208028
    pending_manager = self._LoadPendingManagerState(issue)

    # Then fix the crap out of it.
    self.time = [self.now] * 3
    pending_manager.update_status()
    self.assertEqual(0, len(self.time))
    self.assertEqual(1, len(pending_manager.queue.iterate()))

    why_not = (u'Waiting for the following jobs:\n'
               '  android_dbg_triggered_tests: build\n')
    rietveld_calls = [
        "trigger_try_jobs(%d, 1, 'CQ', False, 'HEAD', {u'android_dbg': "
        "[u'build']})" % issue
    ]
    self._verify_final_state(pending_manager.queue.get(issue).verifications,
                             why_not, rietveld_calls)

  def testLoadState12253015(self):
    # Loads a saved state and try to revive it.
    self.now = 1360256000.
    issue = 12253015
    pending_manager = self._LoadPendingManagerState(issue)

    # Then fix the crap out of it.
    self.time = [self.now] * 3
    pending_manager.update_status()
    self.assertEqual(0, len(self.time))
    self.assertEqual(1, len(pending_manager.queue.iterate()))

    why_not = (
        u'Waiting for the following jobs:\n'
        '  win7_aura: browser_tests\n'
        '  win_rel: chrome_frame_tests,chrome_frame_net_tests,browser_tests,'
        'nacl_integration,sync_integration_tests,installer_util_unittests,'
        'content_browsertests,chrome_frame_unittests,mini_installer_test\n')
    rietveld_calls = [
        "trigger_try_jobs(%d, 1, 'CQ', False, 'HEAD', {u'win7_aura': "
        "[u'browser_tests']})" % issue,
    ]
    self._verify_final_state(pending_manager.queue.get(issue).verifications,
                             why_not, rietveld_calls)

  def testLoadState12633013(self):
    # Loads a saved state and try to revive it.
    self.now = 1363610000.
    issue = 12633013
    pending_manager = self._LoadPendingManagerState(issue)

    # Then fix the crap out of it.
    self.time = [self.now] * 3
    pending_manager.update_status()
    self.assertEqual(0, len(self.time))
    self.assertEqual(1, len(pending_manager.queue.iterate()))

    why_not = (
        u'Waiting for the following jobs:\n'
        '  android_dbg_triggered_tests: slave_steps\n')
    rietveld_calls = [
        "trigger_try_jobs(%d, 1, 'CQ', False, 'HEAD', {u'android_dbg': "
        "[u'slave_steps']})" % issue,
    ]
    self._verify_final_state(pending_manager.queue.get(issue).verifications,
                             why_not, rietveld_calls)

  def testLoadStateSwarm(self):
    # Loads a saved state and try to revive it.
    self.now = 1360256000.
    issue = 666
    pending_manager = self._LoadPendingManagerState(issue)

    # Then fix the crap out of it.
    self.time = [self.now] * 5
    pending_manager.update_status()
    self.assertEqual(0, len(self.time))
    self.assertEqual(1, len(pending_manager.queue.iterate()))

    why_not = (u'Waiting for the following jobs:\n'
               '  linux_rel: browser_tests\n'
               '  mac_rel: browser_tests\n'
               '  win_rel: browser_tests\n')
    # TODO(csharp): These triggered events should be the swarm versions,
    # change them once swarm tests are enabled by default.
    rietveld_calls = [
        "trigger_try_jobs(%d, 1, 'CQ', False, 'HEAD', {u'linux_rel': "
            "[u'browser_tests']})" % issue,
        "trigger_try_jobs(%d, 1, 'CQ', False, 'HEAD', {u'mac_rel': "
            "[u'browser_tests']})" % issue,
        "trigger_try_jobs(%d, 1, 'CQ', False, 'HEAD', {u'win_rel': "
            "[u'browser_tests']})" % issue,
    ]
    self._verify_final_state(pending_manager.queue.get(issue).verifications,
                             why_not, rietveld_calls)

  def test_tbr(self):
    self.time = map(lambda x: float(x*35), range(15))
    self.urlrequests = [
      ('https://chromium-status.appspot.com/allstatus?format=json&endTime=85',
        # Cheap hack here.
        '[]'),
    ]
    root_dir = os.path.join(os.getcwd(), 'root_dir')
    self.read_lines = [
        [
          os.path.join(root_dir, '.chromium_status_pwd'),
          'chromium-status password',
          ['foo'],
        ],
    ]
    pc = projects.load_project(
        'chromium', 'commit-bot-test', root_dir, self.context.rietveld, True)
    pc.context = self.context
    issue = self.context.rietveld.issues[31337]
    self.context.rietveld.patchsets_properties[(31337, 1)] = {}

    # A TBR= patch without reviewer nor messages, like a webkit roll.
    issue['description'] += '\nTBR='
    issue['reviewers'] = []
    issue['messages'] = []
    issue['owner_email'] = u'user@example.com'
    issue['base_url'] = u'svn://svn.chromium.org/chrome/trunk/src'
    pc.look_for_new_pending_commit()
    pc.process_new_pending_commit()
    pc.update_status()
    pc.scan_results()
    self.assertEqual(1, len(pc.queue.iterate()))
    key = self._add_build('chromium_presubmit', 123456, 124,
                          [mocks.BuildbotBuildStep('presubmit', False)], True)
    self.context.rietveld.patchsets_properties[(31337, 1)] = {
      'try_job_results': [{
        'builder': "chromium_presubmit",
        'key': key,
        'buildnumber': "123456",
      }]}
    build = self.buildbot.builders['chromium_presubmit'].builds[123456]
    build.steps[0].simplified_result = True
    pc.update_status()
    pc.scan_results()
    self.assertEqual(0, len(pc.queue.iterate()))
    # check_calls
    self.context.rietveld.check_calls([
      _try_comment(pc),
      "trigger_try_jobs(31337, 1, 'CQ', False, 'HEAD', "
          "{u'chromium_presubmit': ['presubmit']})",
      'close_issue(31337)',
      "update_description(31337, u'foo\\nTBR=')",
      "add_comment(31337, 'Change committed as 125')",
      ])
    self.context.checkout.check_calls([
      'prepare(None)',
      'apply_patch(%r)' % self.context.rietveld.patchsets[0],
      'prepare(None)',
      'apply_patch(%r)' % self.context.rietveld.patchsets[1],
      "commit(u'foo\\nTBR=\\n\\nReview URL: http://nowhere/31337', "
          "u'user@example.com')",
      ])
    self.context.status.check_names(['initial', 'why not', 'why not',
                                     'why not', 'commit'])



if __name__ == '__main__':
  logging.basicConfig(
      level=logging.DEBUG if '-v' in sys.argv else logging.WARNING,
      format='%(levelname)5s %(module)15s(%(lineno)3d): %(message)s')
  unittest.main()
