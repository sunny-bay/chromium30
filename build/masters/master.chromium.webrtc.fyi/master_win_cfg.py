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


def win():
  return chromium_factory.ChromiumFactory('src/build', 'win32')

S('win_webrtc_trunk_scheduler', branch='trunk', treeStableTimer=0)
S('win_webrtc_stable_scheduler', branch='stable', treeStableTimer=0)
P('win_every_4_hours_scheduler', periodicBuildTimer=4*60*60)

project = 'all.sln;chromium_builder_webrtc'
tests = [
    'pyauto_webrtc_tests',
    'pyauto_webrtc_apprtc_test',
    'pyauto_webrtc_quality_tests',
    'webrtc_manual_browser_tests',
    'webrtc_manual_content_browsertests',
    'webrtc_content_unittests',
    'webrtc_perf_content_unittests',
]

defaults['category'] = 'win'

B('Win [latest WebRTC trunk]', 'win_webrtc_trunk_factory',
  scheduler='win_webrtc_trunk_scheduler|win_every_4_hours_scheduler',
  notify_on_missing=True)
F('win_webrtc_trunk_factory', win().ChromiumWebRTCLatestTrunkFactory(
    slave_type='BuilderTester',
    target='Release',
    project=project,
    tests=tests,
    factory_properties={
        'show_perf_results': True,
        'perf_id': 'chromium-webrtc-trunk-tot-rel-win',
        'process_dumps': True,
        'start_crash_handler': True,
    }))

B('Win [latest WebRTC stable]', 'win_webrtc_stable_factory',
  scheduler='win_webrtc_stable_scheduler|win_every_4_hours_scheduler',
  notify_on_missing=True)
F('win_webrtc_stable_factory', win().ChromiumWebRTCLatestStableFactory(
    slave_type='BuilderTester',
    target='Release',
    project=project,
    tests=tests,
    factory_properties={
        'show_perf_results': True,
        'perf_id': 'chromium-webrtc-stable-tot-rel-win',
        'process_dumps': True,
        'start_crash_handler': True,
    }))


def Update(config, active_master, c):
  return helper.Update(c)
