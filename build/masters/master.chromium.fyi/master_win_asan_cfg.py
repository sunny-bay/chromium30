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

win = lambda: chromium_factory.ChromiumFactory('src/out', 'win32')

defaults['category'] = 'win asan'

#
# Main asan release scheduler for src/
#
S('win_asan_rel', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the rel asan builder
#
T('win_asan_rel_trigger')

win_asan_archive = master_config.GetArchiveUrl('ChromiumFYI',
                                               'Win ASAN Builder',
                                               'Win_ASAN_Builder',
                                               'win32')

tests_1 = [
    'base_unittests',
    'browser_tests',
    'cacheinvalidation_unittests',
    'crypto_unittests',
    'gpu_unittests',
    'jingle_unittests',
    'net_unittests',
    'sql_unittests',
    'ui_unittests',
    'content_unittests',
    'views_unittests',
]

tests_2 = [
    'browser_tests',
    'content_browsertests',
    'ipc_tests',
    'media_unittests',
    'ppapi_unittests',
    'printing_unittests',
    'remoting_unittests',
    'sync_unit_tests',
    'unit_tests',
    'url_unittests',
]

#
# Windows ASAN Rel Builder
#
B('Win ASAN Builder', 'win_asan_rel', 'compile_noclose', 'win_asan_rel',
  auto_reboot=False, notify_on_missing=True)
F('win_asan_rel', win().ChromiumASANFactory(
    slave_type='Builder',
    options=['--build-tool=ninja', '--', 'chromium_builder_tests'],
    compile_timeout=7200,
    factory_properties={
        'asan': True,
        'gclient_env': {
            'GYP_DEFINES': (
                'asan=1 win_z7=1 chromium_win_pch=0 '
                'component=static_library '
            ),
            'GYP_GENERATORS': 'ninja',
        },
        'trigger': 'win_asan_rel_trigger',
    }))

#
# Win ASAN Rel testers
#
B('Win ASAN Tests (1)', 'win_asan_rel_tests_1', 'testers_noclose',
  'win_asan_rel_trigger', notify_on_missing=True)
F('win_asan_rel_tests_1', win().ChromiumASANFactory(
    slave_type='Tester',
    build_url=win_asan_archive,
    tests=tests_1,
    factory_properties={
        'asan': True,
        'browser_shard_index': 1,
        'browser_total_shards': 2,
        'testing_env': {
            # The biggest gain observed on stack cache compression is when we
            # skip the 5 bottom frames of the stack traces. To measure this gain
            # we've run an instrumented version of base_unittests and observed
            # the cache compression. With a value between 0 and 4
            # the compression ratio was around 28.9%, and with a value of 5 it
            # was 92.19%.
            'SYZYGY_ASAN_OPTIONS': '--bottom_frames_to_skip=5',
        },
    }))

B('Win ASAN Tests (2)', 'win_asan_rel_tests_2', 'testers_noclose',
  'win_asan_rel_trigger', notify_on_missing=True)
F('win_asan_rel_tests_2', win().ChromiumASANFactory(
    slave_type='Tester',
    build_url=win_asan_archive,
    tests=tests_2,
    factory_properties={
        'asan': True,
        'browser_shard_index': 2,
        'browser_total_shards': 2,
        'testing_env': {
            # The biggest gain observed on stack cache compression is when we
            # skip the 5 bottom frames of the stack traces. To measure this gain
            # we've run an instrumented version of base_unittests and observed
            # the cache compression. With a value between 0 and 4
            # the compression ratio was around 28.9%, and with a value of 5 it
            # was 92.19%.
            'SYZYGY_ASAN_OPTIONS': '--bottom_frames_to_skip=5',
        },
    }))


def Update(config, active_master, c):
  return helper.Update(c)
