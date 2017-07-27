# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory

def win():
  return chromium_factory.ChromiumFactory('src/build', 'win32')

defaults['category'] = 'gpu'

################################################################################
## Release
################################################################################

#
# GPU Win Release
#
B('GPU Win7 (NVIDIA)', 'f_gpu_win_rel', scheduler='global_scheduler')
F('f_gpu_win_rel', win().ChromiumFactory(
    target='Release',
    slave_type='BuilderTester',
    tests=[
      'content_gl_tests',
      'gles2_conform_test',
      'gl_tests',
      'gpu_content_tests',
      'gpu_frame_rate',
      'gpu_throughput',
    ],
    project='all.sln;chromium_gpu_builder',
    factory_properties={
        'generate_gtest_json': True,
        'start_crash_handler': True,
        'perf_id': 'gpu-webkit-win7-nvidia',
        'show_perf_results': True,
        'gclient_env': {
          'GYP_DEFINES': 'fastbuild=1 internal_gles2_conform_tests=1',
        },
        'blink_config': 'blink',
    }))

################################################################################
## Debug
################################################################################


#
# GPU Win Debug
#
B('GPU Win7 (dbg) (NVIDIA)', 'f_gpu_win_dbg', scheduler='global_scheduler')
F('f_gpu_win_dbg', win().ChromiumFactory(
    target='Debug',
    slave_type='BuilderTester',
    tests=[
      'content_gl_tests',
      'gles2_conform_test',
      'gl_tests',
      'gpu_content_tests',
    ],
    project='all.sln;chromium_gpu_debug_builder',
    factory_properties={
        'generate_gtest_json': True,
        'start_crash_handler': True,
        'gclient_env': {
          'GYP_DEFINES': 'fastbuild=1 internal_gles2_conform_tests=1',
        },
        'blink_config': 'blink',
    }))


def Update(_config, _active_master, c):
  return helper.Update(c)
