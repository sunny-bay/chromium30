# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumWebkit

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
T = helper.Triggerable

def win():
  return chromium_factory.ChromiumFactory('src/out', 'win32')

defaults['category'] = 'layout'

blink_tests = [
  'webkit',
  'webkit_lint',
  'webkit_python_tests',
  'webkit_unit_tests',
  'weborigin_unittests',
  'wtf_unittests',
]

################################################################################
## Release
################################################################################

# Archive location
rel_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'WebKit Win Builder',
                                          'webkit-win-latest-rel', 'win32')

#
# Triggerable scheduler for testers
#
T('s4_webkit_rel_trigger')

#
# Win Rel Builder
#
B('WebKit Win Builder', 'f_webkit_win_rel',
  scheduler='global_scheduler', builddir='webkit-win-latest-rel',
  auto_reboot=False)
F('f_webkit_win_rel', win().ChromiumFactory(
    slave_type='Builder',
    options=['--build-tool=ninja', 'all_webkit'],
    factory_properties={
        'trigger': 's4_webkit_rel_trigger',
        'blink_config': 'blink',
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
        },
    }))

#
# Win Rel WebKit testers
#
B('WebKit XP', 'f_webkit_rel_tests', scheduler='s4_webkit_rel_trigger')
F('f_webkit_rel_tests', win().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=blink_tests,
    factory_properties={
        'archive_webkit_results': ActiveMaster.is_production_host,
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        'blink_config': 'blink',
    }))

B('WebKit Win7', 'f_webkit_rel_tests', scheduler='s4_webkit_rel_trigger')

################################################################################
## Debug
################################################################################

# Archive location
dbg_archive = master_config.GetArchiveUrl('ChromiumWebkit',
                                          'WebKit Win Builder (dbg)',
                                          'webkit-win-latest-dbg', 'win32')
#
# Triggerable scheduler for testers
#
T('s4_webkit_dbg_trigger')

#
# Win Dbg Builder
#
B('WebKit Win Builder (dbg)', 'f_webkit_win_dbg', scheduler='global_scheduler',
  builddir='webkit-win-latest-dbg', auto_reboot=False)
F('f_webkit_win_dbg', win().ChromiumFactory(
    target='Debug',
    slave_type='Builder',
    options=['--build-tool=ninja', 'all_webkit'],
    factory_properties={
        'trigger': 's4_webkit_dbg_trigger',
        'blink_config': 'blink',
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
        },
    }))

#
# Win Dbg WebKit testers
#

B('WebKit Win7 (dbg)(1)', 'f_webkit_dbg_tests_1',
    scheduler='s4_webkit_dbg_trigger')
F('f_webkit_dbg_tests_1', win().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=blink_tests,
    factory_properties={
        'archive_webkit_results': ActiveMaster.is_production_host,
        'generate_gtest_json': True,
        'layout_part': '1:2',
        'test_results_server': 'test-results.appspot.com',
        'blink_config': 'blink',
    }))

B('WebKit Win7 (dbg)(2)', 'f_webkit_dbg_tests_2',
    scheduler='s4_webkit_dbg_trigger')
F('f_webkit_dbg_tests_2', win().ChromiumFactory(
    target='Debug',
    slave_type='Tester',
    build_url=dbg_archive,
    tests=['webkit'],
    factory_properties={
        'archive_webkit_results': ActiveMaster.is_production_host,
        'layout_part': '2:2',
        'test_results_server': 'test-results.appspot.com',
        'blink_config': 'blink',
    }))

def Update(_config, _active_master, c):
  return helper.Update(c)
