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


def linux():
  return chromium_factory.ChromiumFactory('src/out', 'linux2')

S('linux_webrtc_trunk_scheduler', branch='trunk', treeStableTimer=0)
S('linux_webrtc_stable_scheduler', branch='stable', treeStableTimer=0)
P('linux_every_4_hours_scheduler', periodicBuildTimer=4*60*60)

options = ['--compiler=goma',  '--build-tool=ninja', '--',
           'chromium_builder_webrtc']
tests = [
    'pyauto_webrtc_tests',
    'pyauto_webrtc_apprtc_test',
    'pyauto_webrtc_quality_tests',
    'webrtc_manual_browser_tests',
    'webrtc_manual_content_browsertests',
    'webrtc_content_unittests',
    'webrtc_perf_content_unittests',
]

defaults['category'] = 'linux'

B('Linux [latest WebRTC trunk]', 'linux_webrtc_trunk_factory',
  scheduler='linux_webrtc_trunk_scheduler|linux_every_4_hours_scheduler',
  notify_on_missing=True)
F('linux_webrtc_trunk_factory', linux().ChromiumWebRTCLatestTrunkFactory(
    slave_type='BuilderTester',
    target='Release',
    options=options,
    tests=tests,
    factory_properties={
        'gclient_env': {'GYP_DEFINES':'python_ver=2.7'},
        'pyauto_env': {'DO_NOT_RESTART_PYTHON_FOR_PYAUTO': '1'},
        'use_xvfb_on_linux': True,
        'show_perf_results': True,
        'perf_id': 'chromium-webrtc-trunk-tot-rel-linux',
    }))

B('Linux [latest WebRTC stable]', 'linux_webrtc_stable_factory',
  scheduler='linux_webrtc_stable_scheduler|linux_every_4_hours_scheduler',
  notify_on_missing=True)
F('linux_webrtc_stable_factory', linux().ChromiumWebRTCLatestStableFactory(
    slave_type='BuilderTester',
    target='Release',
    options=options,
    tests=tests,
    factory_properties={
        'gclient_env': {'GYP_DEFINES':'python_ver=2.7'},
        'pyauto_env': {'DO_NOT_RESTART_PYTHON_FOR_PYAUTO': '1'},
        'use_xvfb_on_linux': True,
        'show_perf_results': True,
        'perf_id': 'chromium-webrtc-stable-tot-rel-linux',
    }))


def Update(config, active_master, c):
  helper.Update(c)
