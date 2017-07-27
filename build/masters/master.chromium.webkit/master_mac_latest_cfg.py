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
  return chromium_factory.ChromiumFactory('src/xcodebuild', 'darwin')

def mac_out():
  return chromium_factory.ChromiumFactory('src/out', 'darwin')


################################################################################
## Release
################################################################################

defaults['category'] = 'nonlayout'

#
# Mac Rel Builder
#
B('Mac10.6 Tests', 'f_mac_tests_rel', scheduler='global_scheduler')
F('f_mac_tests_rel', mac_out().ChromiumFactory(
    options=['--build-tool=ninja', '--compiler=goma-clang', '--',
             'chromium_builder_tests'],
    tests=[
      'browser_tests',
      'cc_unittests',
      'content_browsertests',
      'interactive_ui_tests',
      'unit',
      'webkit_compositor_bindings_unittests',
    ],
    factory_properties={
        'generate_gtest_json': True,
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
            'GYP_DEFINES':'fastbuild=1',
        },
        'blink_config': 'blink',
    }))

B('Mac10.6 Perf', 'f_mac_perf6_rel', scheduler='global_scheduler')
F('f_mac_perf6_rel', mac_out().ChromiumFactory(
    options=['--build-tool=ninja', '--compiler=goma-clang', '--',
             'chromium_builder_perf'],
    tests=[
      'blink_perf',
      'dom_perf',
      'dromaeo',
      'memory',
      'page_cycler_bloat',
      'page_cycler_dhtml',
      'page_cycler_indexeddb',
      'page_cycler_intl_ar_fa_he',
      'page_cycler_intl_es_fr_pt-BR',
      'page_cycler_intl_hi_ru',
      'page_cycler_intl_ja_zh',
      'page_cycler_intl_ko_th_vi',
      'page_cycler_morejs',
      'page_cycler_moz',
      'page_cycler_typical_25',
      'startup',
      'sunspider',
      'tab_switching',
      'octane',
    ],
    factory_properties={
        'show_perf_results': True,
        'perf_id': 'chromium-rel-mac6-webkit',
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
            'GYP_DEFINES': 'fastbuild=1',
        },
        'blink_config': 'blink',
    }))

B('Mac10.8 Tests', 'f_mac_tests_rel_108', scheduler='global_scheduler')
F('f_mac_tests_rel_108', mac_out().ChromiumFactory(
    options=['--build-tool=ninja', '--compiler=goma-clang', '--',
             'chromium_builder_tests'],
    tests=[
      'browser_tests',
      'content_browsertests',
      'interactive_ui_tests',
      'unit',
    ],
    factory_properties={
        'generate_gtest_json': True,
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
            'GYP_DEFINES':'fastbuild=1',
        },
        'blink_config': 'blink',
    }))


################################################################################
## Debug
################################################################################

#
# Mac Dbg Builder
#
B('Mac Builder (dbg)', 'f_mac_dbg', scheduler='global_scheduler')
F('f_mac_dbg', mac().ChromiumFactory(
    target='Debug',
    options=['--compiler=goma-clang', '--', '-target', 'all_webkit'],
    factory_properties={
        'blink_config': 'blink',
    }))

def Update(_config, _active_master, c):
  return helper.Update(c)
