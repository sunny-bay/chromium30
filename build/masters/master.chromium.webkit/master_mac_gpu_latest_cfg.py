# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory

def mac():
  return chromium_factory.ChromiumFactory('src/out', 'darwin')


################################################################################
## Release
################################################################################

defaults['category'] = 'gpu'

#
# GPU Mac Release
#
B('GPU Mac10.7', 'f_gpu_mac_rel', scheduler='global_scheduler')
F('f_gpu_mac_rel', mac().ChromiumFactory(
    target='Release',
    options=['--build-tool=ninja', '--compiler=goma-clang',
             'chromium_gpu_builder'],
    tests=[
      'content_gl_tests',
      'gles2_conform_test',
      'gl_tests',
      'gpu_content_tests',
      'gpu_frame_rate',
      'gpu_throughput',
    ],
    factory_properties={
        'generate_gtest_json': True,
        'perf_id': 'gpu-webkit-mac',
        'show_perf_results': True,
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
            'GYP_DEFINES':'fastbuild=1 internal_gles2_conform_tests=1',
        },
        'blink_config': 'blink',
    }))

################################################################################
## Debug
################################################################################

#
# GPU Mac Debug
#
B('GPU Mac10.7 (dbg)', 'f_gpu_mac_dbg', scheduler='global_scheduler')
F('f_gpu_mac_dbg', mac().ChromiumFactory(
    target='Debug',
    options=['--build-tool=ninja', '--compiler=goma-clang',
             'chromium_gpu_debug_builder'],
    tests=[
      'content_gl_tests',
      'gles2_conform_test',
      'gl_tests',
      'gpu_content_tests',
    ],
    factory_properties={
        'generate_gtest_json': True,
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
            'GYP_DEFINES':'fastbuild=1 internal_gles2_conform_tests=1',
        },
        'blink_config': 'blink',
    }))

def Update(_config, _active_master, c):
  return helper.Update(c)
