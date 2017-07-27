# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

def linux(): return webrtc_factory.WebRTCFactory('src/out', 'linux2')
def mac(): return webrtc_factory.WebRTCFactory('src/out', 'darwin')
def win(): return webrtc_factory.WebRTCFactory('src/build', 'win32')

scheduler_name = 'libjingle_scheduler'
S(scheduler_name, branch='trunk', treeStableTimer=60)

tests = [
    'libjingle_media_unittest',
    'libjingle_p2p_unittest',
    'libjingle_peerconnection_unittest',
    'libjingle_sound_unittest',
    'libjingle_unittest',
]
asan_gyp_defines = 'asan=1 release_extra_cflags=-g linux_use_tcmalloc=0 '
ninja_options = ['--build-tool=ninja']
win_project = r'..\talk\libjingle_tests.sln'
win_factory_prop = {
    'gclient_env': {'GYP_GENERATOR_FLAGS': 'msvs_error_on_missing_sources=1'}}

# Windows.
defaults['category'] = 'win'

B('Win32 Debug', 'win32_debug_factory', scheduler=scheduler_name)
F('win32_debug_factory', win().WebRTCFactory(
    target='Debug',
    project=win_project,
    tests=tests,
    factory_properties=win_factory_prop.copy()))

B('Win32 Release', 'win32_release_factory', scheduler=scheduler_name)
F('win32_release_factory', win().WebRTCFactory(
    target='Release',
    project=win_project,
    tests=tests,
    factory_properties=win_factory_prop.copy()))

# Mac.
defaults['category'] = 'mac'

B('Mac32 Debug', 'mac_debug_factory', scheduler=scheduler_name)
F('mac_debug_factory', mac().WebRTCFactory(
    target='Debug',
    options=ninja_options,
    tests=tests))

B('Mac32 Release', 'mac_release_factory', scheduler=scheduler_name)
F('mac_release_factory', mac().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=tests))

B('Mac Asan', 'mac_asan_factory', scheduler=scheduler_name)
F('mac_asan_factory', mac().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=tests,
    factory_properties={
        'asan': True,
        'gclient_env': {'GYP_DEFINES': asan_gyp_defines},
    }))

# Linux.
defaults['category'] = 'linux'

# Pass the location to the Java JDK as a GYP variable named 'java_home' to
# enable Java compilation on Linux.
java_home = 'java_home=/usr/lib/jvm/java-6-sun'

B('Linux32 Debug', 'linux32_debug_factory', scheduler=scheduler_name)
F('linux32_debug_factory', linux().WebRTCFactory(
    target='Debug',
    options=ninja_options,
    tests=tests,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'target_arch=ia32 %s' % java_home},
    }))

B('Linux32 Release', 'linux32_release_factory', scheduler=scheduler_name)
F('linux32_release_factory', linux().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=tests,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'target_arch=ia32 %s' % java_home},
    }))

B('Linux64 Debug', 'linux64_debug_factory', scheduler=scheduler_name)
F('linux64_debug_factory', linux().WebRTCFactory(
    target='Debug',
    options=ninja_options,
    tests=tests,
    factory_properties={'gclient_env': {'GYP_DEFINES': java_home}}))

B('Linux64 Release', 'linux64_release_factory', scheduler=scheduler_name)
F('linux64_release_factory', linux().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=tests,
    factory_properties={'gclient_env': {'GYP_DEFINES': java_home}}))

B('Linux Clang', 'linux_clang_factory', scheduler=scheduler_name)
F('linux_clang_factory', linux().WebRTCFactory(
    target='Debug',
    options=ninja_options + ['--compiler=clang'],
    tests=tests,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'clang=1 %s' % java_home}}))

B('Linux Memcheck', 'linux_memcheck_factory', scheduler=scheduler_name)
F('linux_memcheck_factory', linux().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=['memcheck_' + test for test in tests],
    factory_properties={
        'needs_valgrind': True,
        'gclient_env': {
            'GYP_DEFINES': 'build_for_tool=memcheck %s' % java_home,
        },
    }))

B('Linux Tsan', 'linux_tsan_factory', scheduler=scheduler_name)
F('linux_tsan_factory', linux().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=['tsan_' + test for test in tests],
    factory_properties={
        'needs_valgrind': True,
        'gclient_env': {'GYP_DEFINES': 'build_for_tool=tsan %s' % java_home},
    }))

B('Linux Asan', 'linux_asan_factory', scheduler=scheduler_name)
F('linux_asan_factory', linux().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=tests,
    factory_properties={
        'asan': True,
        'gclient_env': {'GYP_DEFINES': '%s %s' % (asan_gyp_defines, java_home)},
    }))

# Chrome OS.
B('Chrome OS', 'chromeos_factory', scheduler=scheduler_name)
F('chromeos_factory', linux().WebRTCFactory(
    target='Debug',
    options=ninja_options,
    tests=tests,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'chromeos=1 %s' % java_home},
    }))


def Update(c):
  helper.Update(c)
