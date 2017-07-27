# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
T = helper.Triggerable

def win():
  return chromium_factory.ChromiumFactory('src/build', 'win32')

defaults['category'] = 'nonlayout'

# Tests that are single-machine shard-safe.
sharded_tests = [
  'aura_unittests',
  'base_unittests',
  'browser_tests',
  'cacheinvalidation_unittests',
  'cc_unittests',
  'chromedriver2_tests',
  'chromedriver2_unittests',
  'components_unittests',
  'content_browsertests',
  'content_unittests',
  'crypto_unittests',
  'device_unittests',
  'gpu_unittests',
  'jingle_unittests',
  'media_unittests',
  'net_unittests',
  'ppapi_unittests',
  'printing_unittests',
  'remoting_unittests',
  # http://crbug.com/157234
  #'sync_integration_tests',
  'sync_unit_tests',
  'ui_unittests',
  'unit_tests',
  'views_unittests',
  'webkit_compositor_bindings_unittests',
]

################################################################################
## Release
################################################################################

# Archive location
rel_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'Win Builder',
                                          'win-latest-rel', 'win32')

# Triggerable scheduler for testers
T('s7_webkit_builder_rel_trigger')


#
# Win Rel Builders
#
B('Win Builder', 'f_win_rel', scheduler='global_scheduler',
  builddir='win-latest-rel', auto_reboot=False)
F('f_win_rel', win().ChromiumFactory(
    slave_type='Builder',
    project='all.sln;chromium_builder',
    factory_properties={
        'trigger': 's7_webkit_builder_rel_trigger',
        'gclient_env': { 'GYP_DEFINES': 'fastbuild=1' },
        'archive_build': True,
        'gs_bucket': 'gs://chromium-webkit-snapshots',
        'gs_acl': 'public-read',
        'blink_config': 'blink',
    }))

#
# Win Rel testers+builders
#
# TODO: Switch back to trigger, http://crbug.com/102331
B('Win7 Perf', 'f_win_rel_perf', scheduler='global_scheduler')
F('f_win_rel_perf', win().ChromiumFactory(
    # TODO: undo, http://crbug.com/102331
    #slave_type='Tester',
    #build_url=rel_archive,
    project='all.sln;chromium_builder_perf',
    tests=[
      'blink_perf',
      'dom_perf',
      'dromaeo',
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
    ],
    factory_properties={
        'perf_id': 'chromium-rel-win7-webkit',
        'show_perf_results': True,
        'start_crash_handler': True,
        # TODO: Remove, http://crbug.com/102331
        'gclient_env': {'GYP_DEFINES': 'fastbuild=1'},
        'blink_config': 'blink',
    }))

B('Vista Tests', 'f_win_rel_tests', scheduler='s7_webkit_builder_rel_trigger')
F('f_win_rel_tests', win().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'installer',
      'unit',
    ],
    factory_properties={
        'perf_id': 'chromium-rel-vista-webkit',
        'show_perf_results': True,
        'start_crash_handler': True,
        'test_results_server': 'test-results.appspot.com',
        'blink_config': 'blink',
    }))

B('Chrome Frame Tests', 'f_cf_rel_tests',
  scheduler='s7_webkit_builder_rel_trigger')
F('f_cf_rel_tests', win().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'chrome_frame_net_tests',
      'chrome_frame_tests',
      'chrome_frame_unittests',
    ],
    factory_properties={
        'process_dumps': True,
        'start_crash_handler': True,
        'blink_config': 'blink',
    }))

################################################################################
## Debug
################################################################################


#
# Win Dbg Builder
#
B('Win7 (dbg)', 'f_win_dbg', scheduler='global_scheduler',
  builddir='win-latest-dbg')
F('f_win_dbg', win().ChromiumFactory(
    target='Debug',
    project='all.sln;chromium_builder',
    tests=[
      'browser_tests',
      'content_browsertests',
      'interactive_ui_tests',
      'unit',
    ],
    factory_properties={
        'sharded_tests': sharded_tests,
        'start_crash_handler': True,
        'generate_gtest_json': True,
        'gclient_env': {'GYP_DEFINES': 'fastbuild=1'},
        'blink_config': 'blink',
    }))

def Update(_config, _active_master, c):
  return helper.Update(c)
