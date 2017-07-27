# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
P = helper.Periodic


def mac():
  return chromium_factory.ChromiumFactory('src/xcodebuild', 'darwin')

S('mac_webrtc_trunk_scheduler', branch='trunk', treeStableTimer=0)
S('mac_webrtc_stable_scheduler', branch='stable', treeStableTimer=0)
P('mac_every_4_hours_scheduler', periodicBuildTimer=4*60*60)

options = ['--compiler=goma-clang', '--', '-target', 'chromium_builder_webrtc']
tests = [
    'pyauto_webrtc_tests',
    'pyauto_webrtc_apprtc_test',
    'pyauto_webrtc_quality_tests',
    'webrtc_manual_browser_tests',
    'webrtc_manual_content_browsertests',
    'webrtc_content_unittests',
    'webrtc_perf_content_unittests',
]

defaults['category'] = 'mac'

B('Mac [latest WebRTC trunk]', 'mac_webrtc_trunk_factory',
  scheduler='mac_webrtc_trunk_scheduler|mac_every_4_hours_scheduler',
  notify_on_missing=True)
F('mac_webrtc_trunk_factory', mac().ChromiumWebRTCLatestTrunkFactory(
    slave_type='BuilderTester',
    target='Release',
    options=options,
    tests=tests,
    factory_properties={
        'show_perf_results': True,
        'perf_id': 'chromium-webrtc-trunk-tot-rel-mac',
    }))

B('Mac [latest WebRTC stable]', 'mac_webrtc_stable_factory',
  scheduler='mac_webrtc_stable_scheduler|mac_every_4_hours_scheduler',
  notify_on_missing=True)
F('mac_webrtc_stable_factory', mac().ChromiumWebRTCLatestStableFactory(
    slave_type='BuilderTester',
    target='Release',
    options=options,
    tests=tests,
    factory_properties={
        'show_perf_results': True,
        'perf_id': 'chromium-webrtc-stable-tot-rel-mac',
    }))


def Update(config, active_master, c):
  return helper.Update(c)
