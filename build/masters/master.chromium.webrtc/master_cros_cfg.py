# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromeos_factory
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler


def linux():
  return chromium_factory.ChromiumFactory('src/out', 'linux2')


def create_cbuildbot_factory(target, gs_path, short_name):
  """Generate and register a ChromeOS builder along with its slave(s).

  Args:
    target: Target name in Chrome OS's puppet configuration scripts.
    gs_path: Path to use for build artifact storage.
    short_name: String only used to name the build directory.
  """
  # Factory with the steps to pull out a Chromium source tree (no compilation).
  # It uses an unused slave_type string to avoid adding the normal compile step.
  chrome_factory = linux().ChromiumFactory(slave_type='WebRtcCros')

  archive_base = 'gs://chromeos-image-archive/%s/%s' % (target, gs_path)
  cbuildbot_params = '--archive-base=%s %s' % (archive_base, target)

  # Extend that factory with Cbuildbot build steps to build and test CrOS using
  # the Chrome from the above Chromium source tree.
  return chromeos_factory.CbuildbotFactory(
      params=cbuildbot_params,
      buildroot='/b/cbuild.%s' % short_name,
      chrome_root='.',  # Where ChromiumFactory has put "Chrome".
      factory=chrome_factory,
      slave_manager=False).get_factory()


S(name='chromium_cros', branch='src', treeStableTimer=60)

defaults['category'] = 'chromiumos'

B('ChromiumOS [x86]', 'chromeos_x86_factory', scheduler='chromium_cros',
  notify_on_missing=True)
F('chromeos_x86_factory',
  create_cbuildbot_factory(target='x86-webrtc-chromium-pfq-informational',
                           gs_path='unchanged-deps',
                           short_name='x86'))

B('ChromiumOS [amd64]', 'chromeos_amd64_factory', scheduler='chromium_cros',
  notify_on_missing=True)
F('chromeos_amd64_factory',
  create_cbuildbot_factory(target='amd64-webrtc-chromium-pfq-informational',
                           gs_path='unchanged-deps',
                           short_name='amd64'))

B('ChromiumOS [daisy]', 'chromeos_daisy_factory', scheduler='chromium_cros',
  notify_on_missing=True)
F('chromeos_daisy_factory',
  create_cbuildbot_factory(target='daisy-webrtc-chromium-pfq-informational',
                           gs_path='unchanged-deps',
                           short_name='daisy'))


def Update(config, active_master, c):
  helper.Update(c)
