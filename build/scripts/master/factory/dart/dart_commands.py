#!/usr/bin/python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

Contains the Dart specific commands. Based on commands.py
"""

from buildbot.steps import shell
from buildbot.process.properties import WithProperties

from master import chromium_step
from master.factory import commands


class DartCommands(commands.FactoryCommands):
  """Encapsulates methods to add dart commands to a buildbot factory."""

  logfiles = {"flakylog": ".flaky.log", "debuglog": ".debug.log"}

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None, env=None):

    commands.FactoryCommands.__init__(self, factory, target, build_dir,
                                      target_platform)

    # Two additional directories up compared to normal chromium scripts due
    # to using runtime as runtime dir inside dart directory inside
    # build directory.
    self._script_dir = self.PathJoin('..', self._script_dir)
    self._tools_dir = self.PathJoin('tools')

    # Where the chromium slave scripts are.
    self._chromium_script_dir = self.PathJoin(self._script_dir, 'chromium')
    self._private_script_dir = self.PathJoin(self._script_dir, '..', 'private')

    self._slave_dir = self.PathJoin(self._script_dir,
                                            '..', '..', '..',
                                            'build', 'scripts',
                                            'slave', 'dart')

    self._dart_util = self.PathJoin(self._slave_dir, 'dart_util.py')
    self._dart_build_dir = self.PathJoin('build', 'dart')
    self._repository_root = ''
    self._custom_env = env or {}

  def AddMaybeClobberStep(self, clobber, options=None, timeout=1200):
    """Possibly clobber.

    Either clobber unconditionally (e.g. nuke-and-pave builder, set at
    factory build time), or at runtime (clobber checkbox).  If the
    former, the clobber arg is set.  If the latter, we use a buildbot
    Properties object.

    TODO(jrg); convert into a doStepIf with a closure referencing
    step.build.getProperties().  E.g.
    http://permalink.gmane.org/gmane.comp.python.buildbot.devel/6039
    """
    options = options or {}
    clobber_cmd = [self._python, self._dart_util]
    clobber_cmd.append(WithProperties('%(clobber:+--clobber)s'))
    workdir = self._dart_build_dir
    self._factory.addStep(shell.ShellCommand,
                          name='maybe clobber',
                          description='maybe clobber',
                          timeout=timeout,
                          haltOnFailure=True,
                          workdir=workdir,
                          command=clobber_cmd)

  # pylint: disable=W0221
  def AddCompileStep(self, options=None, timeout=1200):
    options = options or {}
    cmd = 'python ' + self._tools_dir + '/build.py --mode=%s' % \
        (options['mode'])
    workdir = self._dart_build_dir
    is_dartc = (options.get('name') != None and
                options.get('name').startswith('dartc'))
    is_dart2dart = (options.get('name') != None and
                    options.get('name').startswith('dart2dart'))
    is_new_analyzer = (options.get('name') != None and
                       options.get('name').startswith('new_analyzer'))
    is_analyzer_experimental = (options.get('name') != None and
                                options.get('name')
                                .startswith('analyzer_experimental'))
    is_vm = not (is_dartc or is_dart2dart or is_new_analyzer or
                 is_analyzer_experimental)

    if is_vm:
      cmd += ' --arch=%s' % (options['arch'])
      cmd += ' runtime'
    elif is_dart2dart:
      cmd += ' dart2dart_bot'
    elif is_dartc and options['mode'] == 'debug':
      # For dartc we always do a full build, except for debug mode
      # where we will time out doing api docs.
      cmd += ' dartc_bot'
    else:
      # We don't specify a specific target (i.e. we build the all target)
      pass

    self._factory.addStep(shell.ShellCommand,
                          name='build',
                          description='build',
                          timeout=timeout,
                          env = self._custom_env,
                          haltOnFailure=True,
                          workdir=workdir,
                          command=cmd)

  def AddTests(self, options=None, timeout=1200):
    options = options or {}
    is_dartc = (options.get('name') != None and
                options.get('name').startswith('dartc'))
    is_dart2dart = (options.get('name') != None and
                    options.get('name').startswith('dart2dart'))
    is_new_analyzer = (options.get('name') != None and
                       options.get('name').startswith('new_analyzer'))
    is_analyzer_experimental = (options.get('name') != None and
                                options.get('name')
                                .startswith('analyzer_experimental'))
    arch = options.get('arch')
    if is_dartc or is_new_analyzer or is_analyzer_experimental:
      compiler = 'dartc'
      if is_new_analyzer:
        compiler = 'dartanalyzer'
      if is_analyzer_experimental:
        compiler = 'dart2analyzer'
      runtime = 'none'
      configuration = (options['mode'], arch, compiler, runtime)
      base_cmd = ('python ' + self._tools_dir + '/test.py '
                  ' --progress=line --report --time --mode=%s --arch=%s '
                  ' --compiler=%s --runtime=%s --failure-summary'
                 ) % configuration
    elif is_dart2dart:
      compiler = 'dart2dart'
      runtime = 'vm'
      # TODO(ricow): Remove shard functionality when we move to annotated.
      shards = 1
      shard = 1
      if options.get('shards') != None and options.get('shard') != None:
        shards = options['shards']
        shard = options['shard']
      configuration = (options['mode'], arch, compiler, shards, shard)
      base_cmd = ('python ' + self._tools_dir + '/test.py '
                  ' --progress=buildbot --report --time --mode=%s --arch=%s '
                  ' --compiler=%s --shards=%s --shard=%s') % configuration
    else:
      compiler = 'none'
      runtime = 'vm'
      configuration = (options['mode'], arch, compiler, runtime)
      base_cmd = ('python ' + self._tools_dir + '/test.py '
                  ' --progress=line --report --time --mode=%s --arch=%s '
                  ' --compiler=%s --runtime=%s --failure-summary'
                 ) % configuration

    base_cmd = base_cmd + " --write-debug-log"

    if is_dartc:
      cmd = base_cmd
      self._factory.addStep(shell.ShellCommand,
                            name='tests',
                            description='tests',
                            timeout=timeout,
                            env = self._custom_env,
                            haltOnFailure=True,
                            workdir=self._dart_build_dir,
                            command=cmd,
                            logfiles=self.logfiles,
                            lazylogfiles=True)
    elif is_dart2dart:
      cmd = base_cmd
      self._factory.addStep(shell.ShellCommand,
                            name='tests',
                            description='tests',
                            timeout=timeout,
                            env = self._custom_env,
                            haltOnFailure=True,
                            workdir=self._dart_build_dir,
                            command=cmd,
                            logfiles=self.logfiles,
                            lazylogfiles=True)
      cmd = base_cmd + ' --minified'
      self._factory.addStep(shell.ShellCommand,
                            name='minified tests',
                            description='minified tests',
                            timeout=timeout,
                            env = self._custom_env,
                            haltOnFailure=True,
                            workdir=self._dart_build_dir,
                            command=cmd,
                            logfiles=self.logfiles,
                            lazylogfiles=True)
    else:
      if options.get('flags') != None:
        base_cmd += options.get('flags')
      cmd = base_cmd
      self._factory.addStep(shell.ShellCommand,
                            name='tests',
                            description='tests',
                            timeout=timeout,
                            env = self._custom_env,
                            haltOnFailure=True,
                            workdir=self._dart_build_dir,
                            command=cmd,
                            logfiles=self.logfiles,
                            lazylogfiles=True)
      # Rerun all tests in checked mode (assertions and type tests).
      cmd = base_cmd + ' --checked'
      self._factory.addStep(shell.ShellCommand,
                            name='checked_tests',
                            description='checked_tests',
                            timeout=timeout,
                            env = self._custom_env,
                            haltOnFailure=True,
                            workdir=self._dart_build_dir,
                            command=cmd,
                            logfiles=self.logfiles,
                            lazylogfiles=True)

  def AddAnnotatedSteps(self, python_script, timeout=1200, run=1):
    name = 'annotated_steps'
    env = dict(self._custom_env)
    env['BUILDBOT_ANNOTATED_STEPS_RUN'] = '%d' % run
    if run > 1:
      name = name + '_run%d' % run
    self._factory.addStep(chromium_step.AnnotatedCommand,
                          name=name,
                          description=name,
                          timeout=timeout,
                          haltOnFailure=True,
                          env=env,
                          workdir=self._dart_build_dir,
                          command=[self._python, python_script],
                          logfiles=self.logfiles,
                          lazylogfiles=True)

  def AddTrigger(self, trigger):
    self._factory.addStep(trigger)

