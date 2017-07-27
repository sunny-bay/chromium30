# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}


def mac():
  return webrtc_factory.WebRTCFactory('src/xcodebuild', 'darwin')
def macIos():
  return webrtc_factory.WebRTCFactory('', 'darwin', nohooks_on_update=True)

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

scheduler = 'webrtc_mac_scheduler'
S(scheduler, branch='trunk', treeStableTimer=0)

tests = [
    'audio_decoder_unittests',
    'common_audio_unittests',
    'common_video_unittests',
    'metrics_unittests',
    'modules_integrationtests',
    'modules_unittests',
    'neteq_unittests',
    'system_wrappers_unittests',
    'test_support_unittests',
    'tools_unittests',
    'video_engine_core_unittests',
    'voice_engine_unittests',
]

baremetal_tests = [
    'audio_device_integrationtests',
    'video_capture_integrationtests',
    'vie_auto_test',
    'voe_auto_test',
]
options = ['--', '-project', '../webrtc/webrtc.xcodeproj']

defaults['category'] = 'mac'

B('Mac32 Debug', 'mac_debug_factory', scheduler=scheduler)
F('mac_debug_factory', mac().WebRTCFactory(
    target='Debug',
    options=options,
    tests=tests))

B('Mac32 Release', 'mac_release_factory', scheduler=scheduler)
F('mac_release_factory', mac().WebRTCFactory(
    target='Release',
    options=options,
    tests=tests))

B('Mac64 Debug', 'mac64_debug_factory', scheduler=scheduler)
F('mac64_debug_factory', mac().WebRTCFactory(
    target='Debug',
    options=options,
    tests=tests,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'host_arch=x64 target_arch=x64'}
    }))

B('Mac64 Release', 'mac64_release_factory', scheduler=scheduler)
F('mac64_release_factory', mac().WebRTCFactory(
    target='Release',
    options=options,
    tests=tests,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'host_arch=x64 target_arch=x64'}
    }))

B('Mac Asan', 'mac_asan_factory', scheduler=scheduler)
F('mac_asan_factory', mac().WebRTCFactory(
    target='Release',
    options=options,
    tests=tests,
    factory_properties={'asan': True,
                        'gclient_env':
                        {'GYP_DEFINES': ('asan=1'
                                         ' release_extra_cflags=-g '
                                         ' linux_use_tcmalloc=0 ')}}))

B('Mac32 Release [large tests]', 'mac_largetests_factory',
  scheduler=scheduler)
F('mac_largetests_factory', mac().WebRTCFactory(
    target='Release',
    options=options,
    tests=baremetal_tests,
    factory_properties={
        'show_perf_results': True,
        'expectations': True,
        'perf_id': 'webrtc-mac-large-tests',
        'perf_measuring_tests': ['vie_auto_test'],
        'custom_cmd_line_tests': ['vie_auto_test',
                                  'voe_auto_test'],
    }))

# iOS.
B('iOS Device', 'ios_release_factory', scheduler=scheduler)
F('ios_release_factory', macIos().ChromiumAnnotationFactory(
    target='Release',
    slave_type='AnnotatedBuilderTester',
    annotation_script='src/webrtc/build/ios-webrtc.sh'))


def Update(c):
  helper.Update(c)
