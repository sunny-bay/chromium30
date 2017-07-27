# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory
from master.factory import chromeos_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
T = helper.Triggerable

def linux(): return chromium_factory.ChromiumFactory('src/out', 'linux2')

# CrOS ASan bots below.
defaults['category'] = '3chromeos asan'

#
# Main asan release scheduler for src/
#
S('chromeos_asan_rel', branch='src', treeStableTimer=60)

#
# Triggerable scheduler for the rel asan builder
#
T('chromeos_asan_rel_trigger')

chromeos_asan_archive = master_config.GetArchiveUrl(
    'ChromiumMemory',
    'Linux Chromium OS ASAN Builder',
    'Linux_Chromium_OS_ASAN_Builder',
    'linux')

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

#
# CrOS ASAN Rel Builder
#
linux_aura_options = [
  'aura_builder',
  'base_unittests',
  'browser_tests',
  'cacheinvalidation_unittests',
  'chromeos_unittests',
  'compositor_unittests',
  'content_browsertests',
  'content_unittests',
  'crypto_unittests',
  'gpu_unittests',
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

# Please do not add release_extra_cflags=-g here until the debug info section
# produced by Clang on Linux is small enough.
fp_chromeos_asan = {
    'asan': True,
    'gclient_env': {
        'GYP_DEFINES': ('asan=1 '
                        'linux_use_tcmalloc=0 '
                        'chromeos=1 '),
        'GYP_GENERATORS': 'ninja',
    },
    'sharded_tests': sharded_tests,
}

B('Linux Chromium OS ASAN Builder', 'chromeos_asan_rel', 'compile',
  'chromeos_asan_rel', auto_reboot=False, notify_on_missing=True)
F('chromeos_asan_rel', linux().ChromiumASANFactory(
    slave_type='Builder',
    options=[
      '--build-tool=ninja',
      '--compiler=goma-clang',
    ] + linux_aura_options,
    factory_properties=dict(fp_chromeos_asan,
                            trigger='chromeos_asan_rel_trigger')))

#
# CrOS ASAN Rel testers
#

asan_tests_1 = [
  'ash_unittests',
  'aura',
  'base_unittests',
  'browser_tests',
  'cacheinvalidation_unittests',
  'chromeos_unittests',
  'compositor',
  'content_browsertests',
  'crypto_unittests',
  'googleurl',
  'gpu',
  'jingle',
  'media',
  'ppapi_unittests',
  'printing',
  'remoting',
  'views',
]

asan_tests_2 = [
  'browser_tests',
  'interactive_ui_tests',
  'net',
]

asan_tests_3 = [
  'browser_tests',
  'unit',
]

B('Linux Chromium OS ASAN Tests (1)', 'chromeos_asan_rel_tests_1', 'testers',
  'chromeos_asan_rel_trigger', notify_on_missing=True)
F('chromeos_asan_rel_tests_1', linux().ChromiumASANFactory(
    slave_type='Tester',
    build_url=chromeos_asan_archive,
    tests=asan_tests_1,
    factory_properties=dict(fp_chromeos_asan,
                            browser_total_shards='3',
                            browser_shard_index='1')))

B('Linux Chromium OS ASAN Tests (2)', 'chromeos_asan_rel_tests_2', 'testers',
  'chromeos_asan_rel_trigger', notify_on_missing=True)
F('chromeos_asan_rel_tests_2', linux().ChromiumASANFactory(
    slave_type='Tester',
    build_url=chromeos_asan_archive,
    tests=asan_tests_2,
    factory_properties=dict(fp_chromeos_asan,
                            browser_total_shards='3',
                            browser_shard_index='2')))

B('Linux Chromium OS ASAN Tests (3)', 'chromeos_asan_rel_tests_3', 'testers',
  'chromeos_asan_rel_trigger', notify_on_missing=True)
F('chromeos_asan_rel_tests_3', linux().ChromiumASANFactory(
    slave_type='Tester',
    build_url=chromeos_asan_archive,
    tests=asan_tests_3,
    factory_properties=dict(fp_chromeos_asan,
                            browser_total_shards='3',
                            browser_shard_index='3')))

B('Chromium OS (x86) ASAN',
  factory='x86_asan',
  builddir='chromium-tot-chromeos-x86-generic-asan',
  gatekeeper='crosasantest',
  scheduler='chromeos_asan_rel',
  notify_on_missing=True)
F('x86_asan', chromeos_factory.CbuildbotFactory(
  buildroot='/b/cbuild.x86.asan',
  pass_revision=True,
  params='x86-generic-tot-asan-informational').get_factory())

B('Chromium OS (amd64) ASAN',
  factory='amd64_asan',
  builddir='chromium-tot-chromeos-amd64-generic-asan',
  gatekeeper='crosasantest',
  scheduler='chromeos_asan_rel',
  notify_on_missing=True)
F('amd64_asan', chromeos_factory.CbuildbotFactory(
  buildroot='/b/cbuild.amd64.asan',
  pass_revision=True,
  params='amd64-generic-tot-asan-informational').get_factory())

def Update(config, active_master, c):
  return helper.Update(c)
