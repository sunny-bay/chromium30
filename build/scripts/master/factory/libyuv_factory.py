# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master.factory import gclient_factory
from master.factory import chromium_commands

import config


class LibyuvFactory(gclient_factory.GClientFactory):

  CUSTOM_VARS_ROOT_DIR = ('root_dir', 'src')
  # Can't use the same Valgrind constant as in chromium_factory.py, since
  # Libyuv uses another path (use_relative_paths=True in DEPS).
  CUSTOM_DEPS_VALGRIND = ('third_party/valgrind',
     config.Master.trunk_url + '/deps/third_party/valgrind/binaries')

  def __init__(self, build_dir, target_platform):
    """Creates a Libyuv factory.

    Args:
      build_dir: Directory to perform the build relative to. Usually this is
        src/build.
      target_platform: Platform, one of 'win32', 'darwin', 'linux2'
    """
    # Use root_dir=src since many Chromium scripts rely on that path.
    custom_vars_list = [self.CUSTOM_VARS_ROOT_DIR]
    svn_url = config.Master.libyuv_url + '/trunk'
    solutions = []
    solutions.append(gclient_factory.GClientSolution(
        svn_url, name='src', custom_vars_list=custom_vars_list))
    gclient_factory.GClientFactory.__init__(self, build_dir, solutions,
                                            target_platform=target_platform)

  def LibyuvFactory(self, target='Debug', clobber=False, tests=None,
                       mode=None, slave_type='BuilderTester', options=None,
                       compile_timeout=1200, build_url=None, project=None,
                       factory_properties=None, gclient_deps=None):
    options = options or ''
    tests = tests or []
    factory_properties = factory_properties or {}
    factory_properties.setdefault('gclient_env', {})

    if factory_properties.get('needs_valgrind'):
      self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_VALGRIND]
    factory = self.BuildFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties, gclient_deps)

    # Get the factory command object to create new steps to the factory.
    cmds = chromium_commands.ChromiumCommands(factory, target,
                                                 self._build_dir,
                                                 self._target_platform)
    # Override test runner script paths with our own that can run any test and
    # have our suppressions configured.
    valgrind_script_path = cmds.PathJoin('src', 'tools', 'valgrind-libyuv')
    cmds._posix_memory_tests_runner = cmds.PathJoin(valgrind_script_path,
                                                    'libyuv_tests.sh')
    cmds._win_memory_tests_runner = cmds.PathJoin(valgrind_script_path,
                                                  'libyuv_tests.bat')
    # Add tests.
    gyp_defines = factory_properties['gclient_env'].get('GYP_DEFINES', '')
    for test in tests:
      if 'build_for_tool=memcheck' in gyp_defines:
        cmds.AddMemoryTest(test, 'memcheck',
                           factory_properties=factory_properties)
      elif 'build_for_tool=tsan' in gyp_defines:
        cmds.AddMemoryTest(test, 'tsan', factory_properties=factory_properties)
      else:
        cmds.AddAnnotatedGTestTestStep(test, factory_properties)
    return factory
