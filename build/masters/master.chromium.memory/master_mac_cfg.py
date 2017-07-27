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
T = helper.Triggerable

def mac(): return chromium_factory.ChromiumFactory('src/out', 'darwin')

defaults['category'] = '2mac asan'

#
# Main asan release scheduler for src/
#
S('mac_asan_rel', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the rel asan builder
#
T('mac_asan_rel_trigger')

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
  'sync_integration_tests',
  'sync_unit_tests',
  'ui_unittests',
  'unit_tests',
  'views_unittests',
  'webkit_compositor_bindings_unittests',
]

mac_asan_options = [
  'base_unittests',
  'browser_tests',
  'cacheinvalidation_unittests',
  'content_browsertests',
  'content_unittests',
  'crypto_unittests',
  'interactive_ui_tests',
  'ipc_tests',
  'jingle_unittests',
  'media_unittests',
  'net_unittests',
  'ppapi_unittests',
  'printing_unittests',
  'remoting_unittests',
  'sql_unittests',
  'ui_unittests',
  'url_unittests',
]

mac_asan_tests_1 = [
  'base_unittests',
  'browser_tests',
  'cacheinvalidation_unittests',
  'content_browsertests',
  'content_unittests',
  'crypto_unittests',
  'googleurl',
  'ipc_tests',
  'jingle',
  'media',
  'ppapi_unittests',
  'printing',
  'remoting',
  'unit_sql',
]

mac_asan_tests_2 = [
  'browser_tests',
  'net',
  'unit',
]

mac_asan_tests_3 = [
  'browser_tests',
  'interactive_ui_tests',
]

mac_asan_archive = master_config.GetArchiveUrl(
    'ChromiumMemory',
    'Mac ASAN Builder',
    'Mac_ASAN_Builder',
    'mac')


gclient_env = {
  'GYP_DEFINES': 'asan=1 release_extra_cflags=-gline-tables-only',
  'GYP_GENERATORS': 'ninja',
}

#
# Mac ASAN Rel Builder
#
B('Mac ASAN Builder', 'mac_asan_rel', 'compile', 'mac_asan_rel',
  auto_reboot=False, notify_on_missing=True)
F('mac_asan_rel', mac().ChromiumASANFactory(
    target='Release',
    slave_type='Builder',
    options=[
        '--build-tool=ninja',
        '--compiler=goma-clang',
    ] + mac_asan_options,
    factory_properties={
      'asan': True,
      'gclient_env': gclient_env,
      'package_dsym_files': True,
      'trigger': 'mac_asan_rel_trigger',
    },
))

#
# Mac ASAN Rel testers
#
B('Mac ASAN Tests (1)', 'mac_asan_rel_tests_1', 'testers',
  'mac_asan_rel_trigger', notify_on_missing=True)
F('mac_asan_rel_tests_1', mac().ChromiumASANFactory(
    slave_type='Tester',
    build_url=mac_asan_archive,
    tests=mac_asan_tests_1,
    factory_properties={
      'asan': True,
      'browser_shard_index': '1',
      'browser_total_shards': '3',
      'gclient_env': gclient_env,
      'sharded_tests': sharded_tests,
    }))


B('Mac ASAN Tests (2)', 'mac_asan_rel_tests_2', 'testers',
  'mac_asan_rel_trigger', notify_on_missing=True)
F('mac_asan_rel_tests_2', mac().ChromiumASANFactory(
    slave_type='Tester',
    build_url=mac_asan_archive,
    tests=mac_asan_tests_2,
    factory_properties={
      'asan': True,
      'browser_shard_index': '2',
      'browser_total_shards': '3',
      'gclient_env': gclient_env,
      'sharded_tests': sharded_tests,
    }))

B('Mac ASAN Tests (3)', 'mac_asan_rel_tests_3', 'testers',
  'mac_asan_rel_trigger', notify_on_missing=True)
F('mac_asan_rel_tests_3', mac().ChromiumASANFactory(
    slave_type='Tester',
    build_url=mac_asan_archive,
    tests=mac_asan_tests_3,
    factory_properties={
      'asan': True,
      'browser_shard_index': '3',
      'browser_total_shards': '3',
      'gclient_env': gclient_env,
      'sharded_tests': sharded_tests,
    }))

def Update(config, active_master, c):
  return helper.Update(c)
