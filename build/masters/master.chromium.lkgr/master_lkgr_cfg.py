# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

import master_site_config

ActiveMaster = master_site_config.ChromiumLKGR

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

def win(): return chromium_factory.ChromiumFactory('src/build', 'win32')
def win_out(): return chromium_factory.ChromiumFactory('src/out', 'win32')
def linux(): return chromium_factory.ChromiumFactory('src/build', 'linux2')
def mac(): return chromium_factory.ChromiumFactory('src/build', 'darwin')
def linux_android(): return chromium_factory.ChromiumFactory(
    'src/out', 'linux2', nohooks_on_update=True, target_os='android')

defaults['category'] = '1lkgr'

# Global scheduler
S('chromium_lkgr', branch='src', treeStableTimer=1, categories=['lkgr'])

################################################################################
## Windows
################################################################################

B('Win', 'win_full', 'compile|windows', 'chromium_lkgr')
F('win_full', win().ChromiumFactory(
    clobber=True,
    project='all.sln',
    factory_properties={'archive_build': ActiveMaster.is_production_host,
                        'gs_bucket': 'gs://chromium-browser-continuous',
                        'gs_acl': 'public-read',}))

B('Win x64', 'win_x64_full', 'windows', 'chromium_lkgr')
F('win_x64_full', win_out().ChromiumFactory(
    clobber=True,
    compile_timeout=9600,  # Release build is LOOONG
    target='Release_x64',
    options=['--build-tool=ninja', '--', 'all'],
    factory_properties={
      'archive_build': ActiveMaster.is_production_host,
      'gclient_env': {
        'GYP_DEFINES': 'component=static_library target_arch=x64',
        'GYP_MSVS_VERSION': '2012',
      },
      'gs_bucket': 'gs://chromium-browser-continuous',
      'gs_acl': 'public-read',
    }))

################################################################################
## Mac
################################################################################

B('Mac', 'mac_full', 'compile|testers', 'chromium_lkgr')
F('mac_full', mac().ChromiumFactory(
    clobber=True,
    factory_properties={'archive_build': ActiveMaster.is_production_host,
                        'gs_bucket': 'gs://chromium-browser-continuous',
                        'gs_acl': 'public-read',}))

B('Mac ASAN Release', 'mac_asan_rel', 'compile', 'chromium_lkgr')
F('mac_asan_rel', linux().ChromiumASANFactory(
    clobber=True,
    options=['--compiler=goma-clang', '--', '-target',
             'chromium_builder_asan_mac'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': 'asan=1 '}}))

B('Mac ASAN Debug', 'mac_asan_dbg', 'compile', 'chromium_lkgr')
F('mac_asan_dbg', linux().ChromiumASANFactory(
    clobber=True,
    target='Debug',
    options=['--compiler=goma-clang', '--', '-target',
             'chromium_builder_asan_mac'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': 'asan=1 component=static_library '}}))

################################################################################
## Linux
################################################################################

B('Linux', 'linux_full', 'compile|testers', 'chromium_lkgr')
F('linux_full', linux().ChromiumFactory(
    clobber=True,
    factory_properties={'archive_build': ActiveMaster.is_production_host,
                        'gs_bucket': 'gs://chromium-browser-continuous',
                        'gs_acl': 'public-read',}))

B('Linux x64', 'linux64_full', 'compile|testers', 'chromium_lkgr')
F('linux64_full', linux().ChromiumFactory(
    clobber=True,
    factory_properties={
        'archive_build': ActiveMaster.is_production_host,
        'gs_bucket': 'gs://chromium-browser-continuous',
        'gs_acl': 'public-read',
        'gclient_env': {'GYP_DEFINES':'target_arch=x64'}}))

asan_rel_gyp = ('asan=1 linux_use_tcmalloc=0 v8_enable_verify_heap=1 '
                'release_extra_cflags="-gline-tables-only"')

B('ASAN Release', 'linux_asan_rel', 'compile', 'chromium_lkgr')
F('linux_asan_rel', linux().ChromiumASANFactory(
    clobber=True,
    options=['--compiler=clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_rel_gyp}}))

asan_rel_sym_gyp = ('asan=1 linux_use_tcmalloc=0 v8_enable_verify_heap=1 '
                    'release_extra_cflags="-gline-tables-only '
                    '-O1 -fno-inline-functions -fno-inline"')

B('ASAN Release (symbolized)', 'linux_asan_rel_sym', 'compile', 'chromium_lkgr')
F('linux_asan_rel_sym', linux().ChromiumASANFactory(
    clobber=True,
    options=['--compiler=clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan-symbolized',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': asan_rel_sym_gyp}}))

B('ASAN Debug', 'linux_asan_dbg', 'compile', 'chromium_lkgr')
F('linux_asan_dbg', linux().ChromiumASANFactory(
    clobber=True,
    target='Debug',
    options=['--compiler=clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'asan',
       'gs_bucket': 'gs://chromium-browser-asan',
       'gs_acl': 'public-read',
       'gclient_env': {'GYP_DEFINES': 'asan=1 linux_use_tcmalloc=0 '}}))

# The build process for TSan is described at
# http://dev.chromium.org/developers/testing/threadsanitizer-tsan-v2
tsan_gyp = ('tsan=1 linux_use_tcmalloc=0 disable_nacl=1 '
            'debug_extra_cflags="-gline-tables-only" '
            'release_extra_cflags="-gline-tables-only" ')

B('TSAN Release', 'linux_tsan_rel', 'compile', 'chromium_lkgr')
F('linux_tsan_rel', linux().ChromiumFactory(
    clobber=True,
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'tsan',
       'gs_bucket': 'gs://chromium-browser-tsan',
       'gs_acl': 'public-read',
       'tsan': True,
       'gclient_env': {'GYP_DEFINES': tsan_gyp}}))

B('TSAN Debug', 'linux_tsan_dbg', 'compile', 'chromium_lkgr')
F('linux_tsan_dbg', linux().ChromiumFactory(
    clobber=True,
    target='Debug',
    options=['--compiler=goma-clang', 'chromium_builder_asan'],
    factory_properties={
       'cf_archive_build': ActiveMaster.is_production_host,
       'cf_archive_name': 'tsan',
       'gs_bucket': 'gs://chromium-browser-tsan',
       'gs_acl': 'public-read',
       'tsan': True,
       'gclient_env': {'GYP_DEFINES': tsan_gyp}}))

################################################################################
## Android
################################################################################

B('Android', 'android', None, 'chromium_lkgr')
F('android', linux_android().ChromiumAnnotationFactory(
    clobber=True,
    target='Release',
    factory_properties={
      'android_bot_id': 'lkgr-clobber-rel',
      'archive_build': True,
      'gs_acl': 'public-read',
      'gs_bucket': 'gs://chromium-browser-continuous',
      'perf_id': 'android-release',
      'show_perf_results': True,
    },
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    ))


def Update(_config, active_master, c):
  return helper.Update(c)
