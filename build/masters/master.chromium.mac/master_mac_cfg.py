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

def ios():
  return chromium_factory.ChromiumFactory('src/xcodebuild', 'darwin')
def mac():
  return chromium_factory.ChromiumFactory('src/xcodebuild', 'darwin')
def mac_tester():
  return chromium_factory.ChromiumFactory(
      'src/xcodebuild', 'darwin', nohooks_on_update=True)
def mac_out():
  return chromium_factory.ChromiumFactory('src/out', 'darwin')

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

################################################################################
## Release
################################################################################

defaults['category'] = '3mac'

# Archive location
rel_archive = master_config.GetArchiveUrl('ChromiumMac', 'Mac Builder',
                                          'cr-mac-rel', 'mac')

#
# Main debug scheduler for src/
#
S('mac_rel', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the dbg builder
#
T('mac_rel_trigger')

#
# Mac Rel Builder
#
B('Mac Builder', 'rel', 'compile', 'mac_rel', builddir='cr-mac-rel',
  auto_reboot=False, notify_on_missing=True)
F('rel', mac().ChromiumFactory(
    slave_type='Builder',
    options=[
        '--compiler=goma-clang', '--', '-target', 'chromium_builder_tests'],
    factory_properties={
        'trigger': 'mac_rel_trigger',
    }))

#
# Mac Rel testers
#
B('Mac10.6 Tests (1)', 'rel_unit_1', 'testers', 'mac_rel_trigger',
  notify_on_missing=True)
F('rel_unit_1', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=rel_archive,
  tests=[
    'base_unittests',
    'browser_tests',
    'cacheinvalidation_unittests',
    'cc_unittests',
    'chromedriver2_unittests',
    'content_browsertests',
    'crypto_unittests',
    'googleurl',
    'gpu',
    'interactive_ui_tests',
    'jingle',
    'media',
    'nacl_integration',
    'ppapi_unittests',
    'printing',
    'remoting',
    'webkit_compositor_bindings_unittests',
  ],
  factory_properties={'generate_gtest_json': True,
                      'sharded_tests': sharded_tests,
                      'browser_total_shards': 3, 'browser_shard_index': 1,})
)

B('Mac10.6 Tests (2)', 'rel_unit_2', 'testers', 'mac_rel_trigger',
  notify_on_missing=True)
F('rel_unit_2', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=rel_archive,
  tests=[
    'browser_tests',
    'components_unittests',
    'unit',
  ],
  factory_properties={'generate_gtest_json': True,
                      'sharded_tests': sharded_tests,
                      'browser_total_shards': 3, 'browser_shard_index': 2,})
)

B('Mac10.6 Tests (3)', 'rel_unit_3', 'testers', 'mac_rel_trigger',
  notify_on_missing=True)
F('rel_unit_3', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=rel_archive,
  tests=[
    'browser_tests',
    'message_center_unittests',
    'net',
    'telemetry_unittests',
  ],
  factory_properties={'generate_gtest_json': True,
                      'sharded_tests': sharded_tests,
                      'browser_total_shards': 3, 'browser_shard_index': 3,})
)

B('Mac10.7 Tests (1)', 'rel_unit_1', 'testers', 'mac_rel_trigger',
  notify_on_missing=True)
B('Mac10.7 Tests (2)', 'rel_unit_2', 'testers', 'mac_rel_trigger',
  notify_on_missing=True)
B('Mac10.7 Tests (3)', 'rel_unit_3', 'testers', 'mac_rel_trigger',
  notify_on_missing=True)

B('Mac10.6 Sync', 'rel_sync', 'testers', 'mac_rel_trigger',
  notify_on_missing=True)
F('rel_sync', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=rel_archive,
  tests=['sync_integration'],
  factory_properties={'generate_gtest_json': True}))

################################################################################
## Debug
################################################################################

# Archive location
dbg_archive = master_config.GetArchiveUrl('ChromiumMac', 'Mac Builder (dbg)',
                                          'Mac_Builder__dbg_', 'mac')

#
# Main debug scheduler for src/
#
S('mac_dbg', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the dbg builder
#
T('mac_dbg_trigger')

#
# Mac Dbg Builder
#
B('Mac Builder (dbg)', 'dbg', 'compile', 'mac_dbg',
  auto_reboot=False, notify_on_missing=True)
F('dbg', mac_out().ChromiumFactory(
    target='Debug',
    slave_type='Builder',
    options=[
        '--compiler=goma-clang', '--build-tool=ninja', '--',
        'chromium_builder_tests'],
    factory_properties={
        'trigger': 'mac_dbg_trigger',
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
            'GYP_DEFINES':'clang=1 clang_use_chrome_plugins=1'
        },
    }))

#
# Mac Dbg Unit testers
#

B('Mac 10.6 Tests (dbg)(1)', 'dbg_unit_1', 'testers', 'mac_dbg_trigger',
  notify_on_missing=True)
F('dbg_unit_1', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=dbg_archive,
  target='Debug',
  tests=[
    'browser_tests',
    'cacheinvalidation_unittests',
    'cc_unittests',
    'chromedriver2_unittests',
    'content_browsertests',
    'crypto_unittests',
    'googleurl',
    'gpu',
    'jingle',
    'nacl_integration',
    'ppapi_unittests',
    'printing',
    'remoting',
    'webkit_compositor_bindings_unittests',
  ],
  factory_properties={'generate_gtest_json': True,
                      'sharded_tests': sharded_tests,
                      'browser_total_shards': 4, 'browser_shard_index': 1,}))

B('Mac 10.6 Tests (dbg)(2)', 'dbg_unit_2', 'testers', 'mac_dbg_trigger',
  notify_on_missing=True)
F('dbg_unit_2', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=dbg_archive,
  target='Debug',
  tests=[
    'browser_tests',
    'check_deps',
    'media',
    'net',
  ],
  factory_properties={'generate_gtest_json': True,
                      'sharded_tests': sharded_tests,
                      'browser_total_shards': 4, 'browser_shard_index': 2,}))

B('Mac 10.6 Tests (dbg)(3)', 'dbg_unit_3', 'testers', 'mac_dbg_trigger',
  notify_on_missing=True)
F('dbg_unit_3', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=dbg_archive,
  target='Debug',
  tests=[
    'base_unittests',
    'browser_tests',
    'interactive_ui_tests',
  ],
  factory_properties={'generate_gtest_json': True,
                      'sharded_tests': sharded_tests,
                      'browser_total_shards': 4, 'browser_shard_index': 3,}))

B('Mac 10.6 Tests (dbg)(4)', 'dbg_unit_4', 'testers', 'mac_dbg_trigger',
  notify_on_missing=True)
F('dbg_unit_4', mac_tester().ChromiumFactory(
  slave_type='Tester',
  build_url=dbg_archive,
  target='Debug',
  tests=[
    'browser_tests',
    'components_unittests',
    'unit',
    'message_center_unittests',
  ],
  factory_properties={'generate_gtest_json': True,
                      'sharded_tests': sharded_tests,
                      'browser_total_shards': 4, 'browser_shard_index': 4,}))

B('Mac 10.7 Tests (dbg)(1)', 'dbg_unit_1', 'testers', 'mac_dbg_trigger',
  notify_on_missing=True)
B('Mac 10.7 Tests (dbg)(2)', 'dbg_unit_2', 'testers', 'mac_dbg_trigger',
  notify_on_missing=True)
B('Mac 10.7 Tests (dbg)(3)', 'dbg_unit_3', 'testers', 'mac_dbg_trigger',
  notify_on_missing=True)
B('Mac 10.7 Tests (dbg)(4)', 'dbg_unit_4', 'testers', 'mac_dbg_trigger',
  notify_on_missing=True)

################################################################################
## iOS
################################################################################

#
# Main scheduler for src/
#
S('ios', branch='src', treeStableTimer=60)

#
# iOS Release iphoneos BuilderTester
#
B('iOS Device', 'ios_rel', gatekeeper='ios_rel', scheduler='ios',
  auto_reboot=True, notify_on_missing=True)
F('ios_rel', ios().ChromiumFactory(
  # TODO(lliabraa): Need to upstream support for running tests on devices
  # before we can actually run any tests.
  tests=[],
  options = [
    '--', '-project', '../build/all.xcodeproj', '-sdk',
    'iphoneos6.1', '-target' , 'All'],
  factory_properties={
    'app_name': 'Chromium.app',
    'gclient_deps': 'ios',
    'gclient_env': {
      'GYP_DEFINES': 'component=static_library OS=ios chromium_ios_signing=0',
      'GYP_GENERATOR_FLAGS': 'xcode_project_version=3.2',
    },
  }))

#
# iOS Debug iphonesimulator BuilderTester
#
B('iOS Simulator (dbg)', 'ios_dbg', gatekeeper='ios_dbg', scheduler='ios',
  auto_reboot=True, notify_on_missing=True)
F('ios_dbg', ios().ChromiumFactory(
  target='Debug',
  tests=[
    'base_unittests',
    'content_unittests',
    'crypto_unittests',
    'googleurl',
    'media',
    'net',
    'ui_unittests',
    'unit_sql',
    'unit_sync',
    'unit_tests',
  ],
  options = [
    '--', '-project', '../build/all.xcodeproj', '-sdk',
    'iphonesimulator6.1', '-target', 'All',],
  factory_properties={
    'app_name': 'Chromium.app',
    'test_platform': 'ios-simulator',
    'gclient_deps': 'ios',
    'gclient_env': {
      'GYP_DEFINES': 'component=static_library OS=ios chromium_ios_signing=0',
      'GYP_GENERATOR_FLAGS': 'xcode_project_version=3.2',
    },
  }))

def Update(config, active_master, c):
  return helper.Update(c)
