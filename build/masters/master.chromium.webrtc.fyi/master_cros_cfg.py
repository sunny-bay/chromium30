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
P = helper.Periodic


def linux():
  return chromium_factory.ChromiumFactory('src/out', 'linux2')

# Use an unused slave_type string to avoid adding the normal compile step in
# chromium_factory.ChromiumFactory.
def trunk_factory():
  return linux().ChromiumWebRTCLatestTrunkFactory(slave_type='WebRtcCros')

def stable_factory():
  return linux().ChromiumWebRTCLatestStableFactory(slave_type='WebRtcCros')

def create_cbuildbot_factory(checkout_factory, target, gs_path, short_name):
  """Generate and register a ChromeOS builder along with its slave(s).

  Args:
    checkout_factory: Factory with the steps to pull out a Chromium source tree
      (shouldn't contain any compile steps).
    target: Target name in Chrome OS's puppet configuration scripts.
    gs_path: Path to use for build artifact storage.
    short_name: String only used to name the build directory.
  """
  archive_base = 'gs://chromeos-image-archive/%s/%s' % (target, gs_path)
  cbuildbot_params = '--archive-base=%s %s' % (archive_base, target)

  # Extend the checkout_factory with Cbuildbot build steps to build and test
  # CrOS using the Chrome from the above Chromium source tree.
  return chromeos_factory.CbuildbotFactory(
      params=cbuildbot_params,
      buildroot='/b/cbuild.%s' % short_name,
      chrome_root='.',  # Where checkout_factory has put "Chrome".
      factory=checkout_factory,
      slave_manager=False).get_factory()

S('cros_webrtc_trunk_scheduler', branch='trunk', treeStableTimer=0)
S('cros_webrtc_stable_scheduler', branch='stable', treeStableTimer=0)
P('cros_every_4_hours_scheduler', periodicBuildTimer=4*60*60)
trunk_schedulers = 'cros_webrtc_trunk_scheduler|cros_every_4_hours_scheduler'
stable_schedulers = 'cros_webrtc_stable_scheduler|cros_every_4_hours_scheduler'

defaults['category'] = 'chromiumos'

# x86.
B('ChromiumOS x86 [latest WebRTC trunk]',
  factory='chromeos_x86_webrtc_trunk_factory', scheduler=trunk_schedulers,
  notify_on_missing=True)
F('chromeos_x86_webrtc_trunk_factory',
  create_cbuildbot_factory(checkout_factory=trunk_factory(),
                           target='x86-webrtc-chromium-pfq-informational',
                           gs_path='webrtc-trunk-tot',
                           short_name='x86'))

B('ChromiumOS x86 [latest WebRTC stable]',
  factory='chromeos_x86_webrtc_stable_factory', scheduler=stable_schedulers,
  notify_on_missing=True)
F('chromeos_x86_webrtc_stable_factory',
  create_cbuildbot_factory(checkout_factory=stable_factory(),
                           target='x86-webrtc-chromium-pfq-informational',
                           gs_path='webrtc-stable-tot',
                           short_name='x86'))
# AMD64.
B('ChromiumOS amd64 [latest WebRTC trunk]',
  factory='chromeos_amd64_webrtc_trunk_factory', scheduler=trunk_schedulers,
  notify_on_missing=True)
F('chromeos_amd64_webrtc_trunk_factory',
  create_cbuildbot_factory(checkout_factory=trunk_factory(),
                           target='amd64-webrtc-chromium-pfq-informational',
                           gs_path='webrtc-trunk-tot',
                           short_name='amd64'))

B('ChromiumOS amd64 [latest WebRTC stable]',
  factory='chromeos_amd64_webrtc_stable_factory', scheduler=stable_schedulers,
  notify_on_missing=True)
F('chromeos_amd64_webrtc_stable_factory',
  create_cbuildbot_factory(checkout_factory=stable_factory(),
                           target='amd64-webrtc-chromium-pfq-informational',
                           gs_path='webrtc-stable-tot',
                           short_name='amd64'))

# ARM.
B('ChromiumOS daisy [latest WebRTC trunk]',
  factory='chromeos_daisy_webrtc_trunk_factory', scheduler=trunk_schedulers,
  notify_on_missing=True)
F('chromeos_daisy_webrtc_trunk_factory',
  create_cbuildbot_factory(checkout_factory=trunk_factory(),
                           target='daisy-webrtc-chromium-pfq-informational',
                           gs_path='webrtc-trunk-tot',
                           short_name='daisy'))

B('ChromiumOS daisy [latest WebRTC stable]',
  factory='chromeos_daisy_webrtc_stable_factory', scheduler=stable_schedulers,
  notify_on_missing=True)
F('chromeos_daisy_webrtc_stable_factory',
  create_cbuildbot_factory(checkout_factory=stable_factory(),
                           target='daisy-webrtc-chromium-pfq-informational',
                           gs_path='webrtc-stable-tot',
                           short_name='daisy'))


def Update(config, active_master, c):
  return helper.Update(c)
