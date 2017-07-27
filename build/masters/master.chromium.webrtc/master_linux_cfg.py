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
T = helper.Triggerable


def linux():
  return chromium_factory.ChromiumFactory('src/out', 'linux2')
def linux_tester():
  return chromium_factory.ChromiumFactory('src/out', 'linux2',
                                          nohooks_on_update=True)

S('linux_rel_scheduler', branch='src', treeStableTimer=60)
P('linux_daily_scheduler', periodicBuildTimer=24*60*60)
T('linux_rel_trigger')

chromium_rel_archive = master_config.GetGSUtilUrl('chromium-webrtc',
                                                  'Linux Builder')
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

B('Linux Builder', 'linux_rel_factory', scheduler='linux_rel_scheduler',
  notify_on_missing=True)
F('linux_rel_factory', linux().ChromiumFactory(
    slave_type='Builder',
    target='Release',
    options=['--compiler=goma', '--build-tool=ninja', '--',
             'chromium_builder_webrtc'],
    factory_properties={
        'gclient_env': {'GYP_DEFINES':'python_ver=2.7'},
        'trigger': 'linux_rel_trigger',
        'build_url': chromium_rel_archive,
    }))

B('Linux Tester', 'linux_tester_factory', scheduler='linux_rel_trigger')
F('linux_tester_factory', linux_tester().ChromiumFactory(
    slave_type='Tester',
    build_url=chromium_rel_archive,
    tests=tests,
    factory_properties={
        'pyauto_env': {'DO_NOT_RESTART_PYTHON_FOR_PYAUTO': '1'},
        'use_xvfb_on_linux': True,
        'show_perf_results': True,
        'halt_on_missing_build': True,
        'perf_id': 'chromium-webrtc-rel-linux',
    }))

# Builder to catch errors when enable_webrtc=0.
B('Linux Daily WebRTC Disabled', 'linux_webrtc_disabled_factory',
  scheduler='linux_daily_scheduler')
F('linux_webrtc_disabled_factory', linux().ChromiumFactory(
    slave_type='BuilderTester',
    factory_properties={
        'gclient_env': {'GYP_DEFINES': ('enable_webrtc=0 '
                                        'component=static_library')},
    }))

def Update(config, active_master, c):
  helper.Update(c)
