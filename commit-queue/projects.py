# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Define the supported projects."""

import json
import logging
import os
import re
import sys
import urllib2

import find_depot_tools  # pylint: disable=W0611
import checkout

import async_push
import context
import errors
import pending_manager
from post_processors import chromium_copyright
from verification import presubmit_check
from verification import project_base
from verification import reviewer_lgtm
from verification import tree_status
from verification import try_job_steps
from verification import try_job_on_rietveld
from verification import try_server


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..', 'commit-queue-internal'))

# These come from commit-queue in the internal repo.
try:
  import chromium_committers  # pylint: disable=F0401
  import gyp_committers  # pylint: disable=F0401
  import nacl_committers  # pylint: disable=F0401
  import skia_committers  # pylint: disable=F0401
except ImportError as e:
  print >> sys.stderr, (
      'Failed to find commit-queue-internal, will fail to start: %s' % e)
  chromium_committers = None
  gyp_committers = None
  nacl_committers = None
  skia_committers = None


# It's tricky here because 'chrome' is remapped to 'svn' on src.chromium.org but
# the other repositories keep their repository name. So don't list it here.
SVN_HOST_ALIASES = [
    'svn://svn.chromium.org',
    'svn://chrome-svn',
    'svn://chrome-svn.corp',
    'svn://chrome-svn.corp.google.com'
]

CHROME_SVN_BASES = [item + '/chrome' for item in SVN_HOST_ALIASES] + [
    'http://src.chromium.org/svn',
    'https://src.chromium.org/svn',
    'http://src.chromium.org/chrome',
    'https://src.chromium.org/chrome',
]

BLINK_SVN_BASES = [item + '/blink' for item in SVN_HOST_ALIASES] + [
    'http://src.chromium.org/blink',
    'https://src.chromium.org/blink',
]

# Steps that are never considered to determine the try job success.
IGNORED_STEPS = (
  'svnkill', 'update_scripts', 'taskkill', 'cleanup_temp', 'process_dumps')

# To be used in a regexp to match the branch part of an git url.
BRANCH_MATCH = r'\@[a-zA-Z0-9\-_\.]+'


def _read_lines(filepath, what):
  try:
    return open(filepath).readlines()
  except IOError:
    raise errors.ConfigurationError('Put the %s in %s' % (what, filepath))


def _get_chromium_committers():
  """Gets the list of all allowed committers."""
  if not chromium_committers:
    # Fake values.
    entries = ['georges']
  else:
    entries = chromium_committers.get_list()
  logging.info('Found %d committers' % len(entries))
  return ['^%s$' % re.escape(i) for i in entries]


def _get_skia_committers():
  """Gets the list of all allowed committers."""
  if not skia_committers:
    # Fake values.
    entries = ['georges']
  else:
    entries = skia_committers.get_list()
  logging.info('Found %d committers' % len(entries))
  return ['^%s$' % re.escape(i) for i in entries]


def _get_nacl_committers():
  """Gets the list of all allowed committers."""
  if not nacl_committers:
    # Fake values.
    entries = ['georges']
  else:
    entries = nacl_committers.get_list()
  logging.info('Found %d committers' % len(entries))
  return ['^%s$' % re.escape(i) for i in entries]


def _get_gyp_committers():
  """Gets the list of all allowed committers."""
  if not gyp_committers:
    # Fake values.
    entries = ['georges']
  else:
    entries = gyp_committers.get_list()
  logging.info('Found %d committers' % len(entries))
  return ['^%s$' % re.escape(i) for i in entries]


def _chromium_lkgr():
  try:
    return int(
        urllib2.urlopen('https://chromium-status.appspot.com/lkgr').read())
  except (ValueError, IOError):
    return None


def _nacl_lkgr():
  try:
    return int(
        urllib2.urlopen('https://nativeclient-status.appspot.com/lkgr').read())
  except (ValueError, IOError):
    return None


def _chromium_status_pwd(root_dir):
  filepath = os.path.join(root_dir, '.chromium_status_pwd')
  return _read_lines(filepath, 'chromium-status password')[0].strip()


def _gen_blink(user, root_dir, rietveld_obj, no_try):
  """Generates a PendingManager commit queue for blink/trunk."""
  local_checkout = checkout.SvnCheckout(
      root_dir,
      'blink',
      user,
      None,
      'svn://svn.chromium.org/blink/trunk',
      [])
  context_obj = context.Context(
      rietveld_obj,
      local_checkout,
      async_push.AsyncPush(
        'https://chromium-status.appspot.com/cq',
        _chromium_status_pwd(root_dir)))

  project_bases = [
      '^%s/trunk(|/.*)$' % re.escape(base) for base in BLINK_SVN_BASES]
  project_bases.append(
      r'^https?\:\/\/chromium.googlesource.com\/chromium\/blink(?:\.git)?%s$' %
        BRANCH_MATCH)
  verifiers_no_patch = [
      project_base.ProjectBaseUrlVerifier(project_bases),
      reviewer_lgtm.ReviewerLgtmVerifier(
          _get_chromium_committers(),
          [re.escape(user)]),
  ]
  verifiers = []
  prereq_builder = 'blink_presubmit'
  prereq_tests = ['presubmit']
  step_verifiers = [
    try_job_steps.TryJobSteps(builder_name=prereq_builder,
                              steps=prereq_tests)]
  if not no_try:
    blink_tests = [
      'webkit_lint',
      'webkit_python_tests',
      'webkit_tests',
      'webkit_unit_tests',
      'weborigin_unittests',
      'wtf_unittests',
    ]

    # A "compile-only" bot runs the webkit_lint tests (which are fast)
    # in order to pick up the default build targets. We don't use the
    # "compile" step because that will build all the chromium targets, not
    # just the blink-specific ones.
    compile_only = [ 'webkit_lint' ]

    builders_and_tests = {
      'linux_layout':     compile_only,
      'mac_layout':       compile_only,
      'win_layout':       compile_only,

      'linux_blink_rel': blink_tests,
      'mac_blink_rel':   blink_tests,
      'win_blink_rel':   blink_tests,
    }

    step_verifiers += [
      try_job_steps.TryJobSteps(builder_name=b, prereq_builder=prereq_builder,
                                prereq_tests=prereq_tests, steps=s)
      for b, s in builders_and_tests.iteritems()
    ]

  verifiers.append(try_job_on_rietveld.TryRunnerRietveld(
      context_obj,
      'http://build.chromium.org/p/tryserver.chromium/',
      user,
      step_verifiers,
      IGNORED_STEPS,
      'src'))

  verifiers.append(tree_status.TreeStatusVerifier(
      'https://blink-status.appspot.com'))
  return pending_manager.PendingManager(
      context_obj,
      verifiers_no_patch,
      verifiers)


def _gen_chromium(user, root_dir, rietveld_obj, no_try):
  """Generates a PendingManager commit queue for chrome/trunk/src."""
  local_checkout = checkout.SvnCheckout(
      root_dir,
      'chromium',
      user,
      None,
      'svn://svn.chromium.org/chrome/trunk/src',
      [chromium_copyright.process])
  context_obj = context.Context(
      rietveld_obj,
      local_checkout,
      async_push.AsyncPush(
        'https://chromium-status.appspot.com/cq',
        _chromium_status_pwd(root_dir)))

  project_bases = [
      '^%s/trunk/src(|/.*)$' % re.escape(base) for base in CHROME_SVN_BASES]

  aliases = (
    # Old path.
    'git.chromium.org/git/chromium',
    # New path.
    'git.chromium.org/chromium/src',
    'chromium.googlesource.com/chromium/src',
  )
  project_bases.extend(
      r'^https?\:\/\/%s(?:\.git)?%s$' % (re.escape(i), BRANCH_MATCH)
      for i in aliases)
  verifiers_no_patch = [
      project_base.ProjectBaseUrlVerifier(project_bases),
      reviewer_lgtm.ReviewerLgtmVerifier(
          _get_chromium_committers(),
          [re.escape(user)]),
  ]
  verifiers = []
  prereq_builder = 'chromium_presubmit'
  prereq_tests = ['presubmit']
  step_verifiers = [
    try_job_steps.TryJobSteps(builder_name=prereq_builder,
                              steps=prereq_tests)]
  if not no_try:
    # To add tests to this list, they MUST be in
    # /chrome/trunk/tools/build/masters/master.chromium/master_gatekeeper_cfg.py
    # or somehow close the tree whenever they break.
    standard_tests = [
        'base_unittests',
        'browser_tests',
        'cacheinvalidation_unittests',
        'check_deps',
        'content_browsertests',
        'content_unittests',
        'crypto_unittests',
        #'gfx_unittests',
        # Broken in release.
        #'url_unittests',
        'gpu_unittests',
        'ipc_tests',
        'interactive_ui_tests',
        'jingle_unittests',
        'media_unittests',
        'net_unittests',
        'ppapi_unittests',
        'printing_unittests',
        'sql_unittests',
        'sync_unit_tests',
        'unit_tests',
        #'webkit_unit_tests',
    ]
    # Use a smaller set of tests for *_aura, since there's a lot of overlap with
    # the corresponding *_rel builders.
    # Note: *_aura are Release builders even if their names convey otherwise.
    aura_tests = [
      'aura_unittests',
      'browser_tests',
      'compositor_unittests',
      'content_browsertests',
      'content_unittests',
      'interactive_ui_tests',
      'unit_tests',
      'views_unittests',
    ]
    linux_aura_tests = aura_tests[:]
    linux_aura_tests.remove('views_unittests')
    builders_and_tests = {
      # TODO(maruel): Figure out a way to run 'sizes' where people can
      # effectively update the perf expectation correctly.  This requires a
      # clobber=True build running 'sizes'. 'sizes' is not accurate with
      # incremental build. Reference:
      # http://chromium.org/developers/tree-sheriffs/perf-sheriffs.
      # TODO(maruel): An option would be to run 'sizes' but not count a failure
      # of this step as a try job failure.
      'android_dbg': ['slave_steps'],
      'android_clang_dbg': ['slave_steps'],
      'android_aosp': ['compile'],
      'ios_dbg_simulator': [
        'compile',
        'base_unittests',
        'content_unittests',
        'crypto_unittests',
        'url_unittests',
        'media_unittests',
        'net_unittests',
        'sql_unittests',
        'ui_unittests',
      ],
      'ios_rel_device': ['compile'],
      'linux_aura': linux_aura_tests,
      'linux_clang': ['compile'],
      'linux_chromeos_clang': ['compile'],
      # Note: It is a Release builder even if its name convey otherwise.
      'linux_chromeos': standard_tests + [
        'app_list_unittests',
        'aura_unittests',
        'ash_unittests',
        'chromeos_unittests',
        'components_unittests',
        'dbus_unittests',
        'device_unittests',
        'sandbox_linux_unittests',
      ],
      'linux_rel': standard_tests + [
        'cc_unittests',
        'chromedriver2_unittests',
        'components_unittests',
        'nacl_integration',
        'remoting_unittests',
        'sandbox_linux_unittests',
        'sync_integration_tests',
      ],
      'mac': ['compile'],
      'mac_rel': standard_tests + [
        'cc_unittests',
        'chromedriver2_unittests',
        'components_unittests',
        'nacl_integration',
        'remoting_unittests',
        'sync_integration_tests',
        'telemetry_unittests',
      ],
      'win': ['compile'],
      'win7_aura': aura_tests + [
        'ash_unittests',
      ],
      'win_rel': standard_tests + [
        'cc_unittests',
        'chrome_frame_net_tests',
        'chrome_frame_tests',
        'chrome_frame_unittests',
        'chromedriver2_unittests',
        'components_unittests',
        'installer_util_unittests',
        'mini_installer_test',
        'nacl_integration',
        'remoting_unittests',
        'sync_integration_tests',
        'telemetry_unittests',
      ],
      'win_x64_rel': [
        'compile',
      ],
    }

    swarm_enabled_tests = (
      'base_unittests',
      'browser_tests',
      'interactive_ui_tests',
      'net_unittests',
      'unit_tests',
    )

    swarm_test_map = dict(
      (test, test + '_swarm') for test in swarm_enabled_tests)

    swarm_enabled_builders_and_tests = {
      'linux_rel': swarm_test_map,
      # TODO(csharp): Enable once isoalte works on Mac again
      # 'mac_rel': swarm_test_map,
      'win_rel': swarm_test_map,
    }

    step_verifiers += [
      try_job_steps.TryJobSteps(
          builder_name=b, prereq_builder=prereq_builder,
          prereq_tests=prereq_tests, steps=s)
      for b, s in builders_and_tests.iteritems()
      if b not in swarm_enabled_builders_and_tests
    ] + [
      try_job_steps.TryJobTriggeredSteps(
        builder_name='android_dbg_triggered_tests',
        trigger_name='android_dbg',
        prereq_builder=prereq_builder,
        prereq_tests=prereq_tests,
        steps={'slave_steps': 'slave_steps'}),
    ]

    # Add the swarm enabled builders with swarm accepted tests.
    for builder, swarm_enabled_tests in (
        swarm_enabled_builders_and_tests.iteritems()):
      regular_tests = list(set(builders_and_tests[builder]) -
                           set(swarm_enabled_tests))

      step_verifiers.append(
          try_job_steps.TryJobTriggeredOrNormalSteps(
              builder_name='swarm_triggered',
              trigger_name=builder,
              prereq_builder=prereq_builder,
              prereq_tests=prereq_tests,
              steps=swarm_enabled_tests,
              trigger_bot_steps=regular_tests,
              use_triggered_bot=False))

  verifiers.append(try_job_on_rietveld.TryRunnerRietveld(
      context_obj,
      'http://build.chromium.org/p/tryserver.chromium/',
      user,
      step_verifiers,
      IGNORED_STEPS,
      'src'))

  verifiers.append(tree_status.TreeStatusVerifier(
      'https://chromium-status.appspot.com'))
  return pending_manager.PendingManager(
      context_obj,
      verifiers_no_patch,
      verifiers)


def _skia_status_pwd(root_dir):
  filepath = os.path.join(root_dir, '.skia_status_pwd')
  return _read_lines(filepath, 'skia-status password')[0].strip()


def _gen_skia(user, root_dir, rietveld_obj, no_try):
  """Generates a PendingManager commit queue for Skia.

  Adds the following verifiers to the PendingManager:
  * ProjectBaseUrlVerifier
  * ReviewerLgtmVerifier
  * PresubmitCheckVerifier
  * TreeStatusVerifier
  * TryRunnerRietveld (runs compile trybots)
  """
  naked_url = '://skia.googlecode.com/svn/trunk'
  local_checkout = checkout.SvnCheckout(
      root_dir,
      'skia',
      user,
      None,
      'https' + naked_url)
  context_obj = context.Context(
      rietveld_obj,
      local_checkout,
      async_push.AsyncPush(
          'https://skia-tree-status.appspot.com/cq',
          _skia_status_pwd(root_dir)),
      server_hooks_missing=True)

  project_bases = [
      '^%s(|/.*)$' % re.escape(base + naked_url) for base in ('http', 'https')
  ]
  verifiers_no_patch = [
      project_base.ProjectBaseUrlVerifier(project_bases),
      reviewer_lgtm.ReviewerLgtmVerifier(
          _get_skia_committers(),
          [re.escape(user)]),
  ]
  verifiers = [
      presubmit_check.PresubmitCheckVerifier(context_obj),
      tree_status.TreeStatusVerifier(
          'https://skia-tree-status.appspot.com')
  ]

  if not no_try:
    # TODO(rmistry): This should instead be a URL that does not change.
    try_server_url = 'http://108.170.217.252:10117/'
    compile_required_build_steps = [
        'BuildBench',
        'BuildGm',
        'BuildMost',
        'BuildSkiaLib',
        'BuildTests',
        'BuildTools',
    ]

    builder_names = list(
        json.load(urllib2.urlopen(try_server_url + 'json/cqtrybots')))

    step_verifiers = []
    for builder_name in builder_names:
      step_verifiers.append(
          try_job_steps.TryJobSteps(
              builder_name=builder_name,
              steps=compile_required_build_steps))
    verifiers.append(try_job_on_rietveld.TryRunnerRietveld(
          context_obj=context_obj,
          try_server_url=try_server_url,
          commit_user=user,
          step_verifiers=step_verifiers,
          ignored_steps=[],
          solution='src'))

  return pending_manager.PendingManager(
      context_obj,
      verifiers_no_patch,
      verifiers)


def _gen_nacl(user, root_dir, rietveld_obj, no_try):
  """Generates a PendingManager commit queue for Native Client."""
  offset = 'trunk/src/native_client'
  local_checkout = checkout.SvnCheckout(
      root_dir,
      'nacl',
      user,
      None,
      'svn://svn.chromium.org/native_client/' + offset)
  context_obj = context.Context(
      rietveld_obj,
      local_checkout,
      async_push.AsyncPush(
        'https://nativeclient-status.appspot.com/cq',
        _chromium_status_pwd(root_dir)))

  host_aliases = SVN_HOST_ALIASES + [
      'http://src.chromium.org', 'https://src.chromium.org']
  svn_bases = [i + '/native_client' for i in host_aliases]
  project_bases = [
      '^%s/%s(|/.*)$' % (re.escape(base), offset) for base in svn_bases
  ]
  aliases = (
    'git.chromium.org/native_client/src/native_client',
    'chromium.googlesource.com/native_client/src/native_client',
  )
  project_bases.extend(
      r'^https?\:\/\/%s(?:\.git)?%s$' % (re.escape(i), BRANCH_MATCH)
      for i in aliases)
  verifiers_no_patch = [
      project_base.ProjectBaseUrlVerifier(project_bases),
      reviewer_lgtm.ReviewerLgtmVerifier(
          _get_nacl_committers(),
          [re.escape(user)]),
  ]
  verifiers = [
      presubmit_check.PresubmitCheckVerifier(context_obj),
  ]
  if not no_try:
    # Grab the list of all the builders here. The commit queue needs to know
    # which builders were triggered. TODO: makes this more automatic.
    url = 'http://build.chromium.org/p/tryserver.nacl/json/builders'
    builders_and_tests = dict(
      (key, []) for key in json.load(urllib2.urlopen(url))
      if (key.startswith('nacl-') and
          'toolchain' not in key and
          'valgrind' not in key and
          'perf_panda' not in key and
          'arm_hw' not in key and
          'shared' not in key and
          'coverage' not in key)
    )
    verifiers.append(try_server.TryRunnerSvn(
        context_obj,
        'http://build.chromium.org/p/tryserver.nacl/',
        user,
        builders_and_tests,
        IGNORED_STEPS,
        'native_client',
        ['--root', 'native_client'],
        _nacl_lkgr))

  verifiers.append(tree_status.TreeStatusVerifier(
      'https://nativeclient-status.appspot.com'))
  return pending_manager.PendingManager(
      context_obj,
      verifiers_no_patch,
      verifiers)


def _gen_gyp(user, root_dir, rietveld_obj, no_try):
  """Generates a PendingManager commit queue for GYP."""
  naked_url = '://gyp.googlecode.com/svn/trunk'
  local_checkout = checkout.SvnCheckout(
      root_dir,
      'gyp',
      user,
      None,
      'https' + naked_url)
  context_obj = context.Context(
      rietveld_obj,
      local_checkout,
      async_push.AsyncPush(
        'https://chromium-status.appspot.com/cq/receiver',
        _chromium_status_pwd(root_dir)))

  project_bases = [
      '^%s(|/.*)$' % re.escape(base + naked_url) for base in ('http', 'https')
  ]
  verifiers_no_patch = [
      project_base.ProjectBaseUrlVerifier(project_bases),
      reviewer_lgtm.ReviewerLgtmVerifier(
          _get_gyp_committers(),
          [re.escape(user)]),
  ]
  verifiers = []
  if not no_try:
    # Grab the list of all the builders here. The commit queue needs to know
    # which builders were triggered. TODO: makes this more automatic.
    # GYP is using the Nacl try server.
    url = 'http://build.chromium.org/p/tryserver.nacl/json/builders'
    builders_and_tests = dict(
      (key, []) for key in json.load(urllib2.urlopen(url))
      if key.startswith('gyp-')
    )
    verifiers.append(try_server.TryRunnerSvn(
        context_obj,
        'http://build.chromium.org/p/tryserver.nacl/',
        user,
        builders_and_tests,
        IGNORED_STEPS,
        'gyp',
        ['--root', 'gyp'],
        lambda: None))

  verifiers.append(tree_status.TreeStatusVerifier(
      'https://gyp-status.appspot.com/status'))
  return pending_manager.PendingManager(
      context_obj,
      verifiers_no_patch,
      verifiers)


def _gen_tools(user, root_dir, rietveld_obj, _no_try):
  """Generates a PendingManager commit queue for everything under
  chrome/trunk/tools.

  These don't have a try server but have presubmit checks.
  """
  # Ignore no_try.
  path = 'tools'
  project_bases = [
      '^%s/trunk/%s(|/.*)$' % (re.escape(base), path)
      for base in CHROME_SVN_BASES
  ]
  aliases = (
    # Old path.
    'git.chromium.org/git/chromium/tools',
    # New path.
    'git.chromium.org/chromium/tools',
    'chromium.googlesource.com/chromium/tools',
  )
  project_bases.extend(
      r'^https?\:\/\/%s\/([a-z0-9\-_]+)(?:\.git)?%s$' % (
        re.escape(i), BRANCH_MATCH) for i in aliases)
  return _internal_simple(path, project_bases, user, root_dir, rietveld_obj)


def _gen_chromium_deps(user, root_dir, rietveld_obj, _no_try):
  """Generates a PendingManager commit queue for
  chrome/trunk/deps/.
  """
  # Ignore no_try.
  path = 'deps'
  project_bases = [
      '^%s/trunk/%s(|/.*)$' % (re.escape(base), path)
      for base in CHROME_SVN_BASES
  ]
  return _internal_simple(path, project_bases, user, root_dir, rietveld_obj)


def _internal_simple(path, project_bases, user, root_dir, rietveld_obj):
  """Generates a PendingManager commit queue for chrome/trunk/tools/build."""
  local_checkout = checkout.SvnCheckout(
      root_dir,
      os.path.basename(path),
      user,
      None,
      'svn://svn.chromium.org/chrome/trunk/' + path,
      [chromium_copyright.process])
  context_obj = context.Context(
      rietveld_obj,
      local_checkout,
      async_push.AsyncPush(
        'https://chromium-status.appspot.com/cq',
        _chromium_status_pwd(root_dir)))

  verifiers_no_patch = [
      project_base.ProjectBaseUrlVerifier(project_bases),
      reviewer_lgtm.ReviewerLgtmVerifier(
          _get_chromium_committers(),
          [re.escape(user)]),
  ]
  verifiers = [
      presubmit_check.PresubmitCheckVerifier(context_obj, timeout=900),
  ]

  return pending_manager.PendingManager(
      context_obj,
      verifiers_no_patch,
      verifiers)


def supported_projects():
  """List the projects that can be managed by the commit queue."""
  return sorted(
      x[5:] for x in dir(sys.modules[__name__]) if x.startswith('_gen_'))


def load_project(project, user, root_dir, rietveld_obj, no_try):
  """Loads the specified project."""
  assert os.path.isabs(root_dir)
  return getattr(sys.modules[__name__], '_gen_' + project)(
      user, root_dir, rietveld_obj, no_try)
