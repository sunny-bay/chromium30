#!/usr/bin/python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to generate a Dart-specific BuildFactory.

Based on gclient_factory.py.
"""

from buildbot.process.buildstep import RemoteShellCommand
from buildbot.changes import svnpoller
from buildbot.status.mail import MailNotifier
from buildbot.status.status_push import HttpStatusPush

from master.factory import v8_factory
from master.factory import chromium_factory
from master.factory.dart import dart_commands
from master.factory import gclient_factory
from master import master_utils

import config

current_milestone = '0.3'
v8_stable_branch = '3.19'
android_tools_rev = '@b12d410c0ee23385da78e6c9f353d28fd992e0bd'
android_resources_rev = '@3855'

milestone_path = '/branches/' + current_milestone
dart_milestone_url = config.Master.dart_url + milestone_path

chromium_git = 'http://git.chromium.org/git/'

dartium_url = config.Master.dart_bleeding + '/deps/dartium.deps'
dartium_trunk_url = config.Master.dart_trunk + '/deps/dartium.deps'
dartium_milestone_url = dart_milestone_url + '/deps/dartium.deps'
android_tools_url = chromium_git + 'android_tools.git' + android_tools_rev
if config.Master.v8_internal_url:
  android_resources_url = (config.Master.v8_internal_url +
      '/buildbot_deps/android_testing_resources' + android_resources_rev )
else:
  android_resources_url = None

# We set these paths relative to the dart root, the scripts need to
# fix these to be absolute if they don't run from there.
linux_env =  {'BUILDBOT_JAVA_HOME': 'third_party/java/linux/j2sdk'}
linux_clang_env =  {'BUILDBOT_JAVA_HOME': 'third_party/java/linux/j2sdk',
                    'CC': 'third_party/clang/linux/bin/clang',
                    'CXX': 'third_party/clang/linux/bin/clang++'}
windows_env = {'BUILDBOT_JAVA_HOME': 'third_party\\java\\windows\\j2sdk',
               'LOGONSERVER': '\\\\AD1'}

dart_revision_url = "http://code.google.com/p/dart/source/detail?r=%s"

# gclient custom vars
CUSTOM_VARS_SOURCEFORGE_URL = ('sourceforge_url', config.Master.sourceforge_url)
CUSTOM_VARS_GOOGLECODE_URL = ('googlecode_url', config.Master.googlecode_url)
CUSTOM_VARS_CHROMIUM_URL = (
  'chromium_url', config.Master.server_url + config.Master.repo_root)

custom_vars_list = [CUSTOM_VARS_SOURCEFORGE_URL,
                    CUSTOM_VARS_GOOGLECODE_URL,
                    CUSTOM_VARS_CHROMIUM_URL]

# gclient custom deps
if config.Master.trunk_internal_url:
  CUSTOM_DEPS_WIN7_SDK = (
    "src/third_party/platformsdk_win7",
    config.Master.trunk_internal_url + "/third_party/platformsdk_win7@23175")
  CUSTOM_DEPS_WIN8_SDK = (
    "src/third_party/platformsdk_win8",
    config.Master.trunk_internal_url
    + "/third_party/platformsdk_win8_9200@32005")
  CUSTOM_DEPS_DIRECTX_SDK = (
    "src/third_party/directxsdk",
    config.Master.trunk_internal_url + "/third_party/directxsdk@20250")

  custom_deps_list_win = [CUSTOM_DEPS_WIN7_SDK,
                          CUSTOM_DEPS_WIN8_SDK,
                          CUSTOM_DEPS_DIRECTX_SDK]
else:
  custom_deps_list_win = []
custom_deps_list_vm_linux = [('dart/third_party/clang', '/third_party/clang')]
custom_deps_list_chromeOnAndroid = [
    ('dart/third_party/android_tools', android_tools_url),
]
if android_resources_url:
  custom_deps_list_chromeOnAndroid.append(
      ('dart/third_party/android_testing_resources', android_resources_url))

# These chromium factories are used for building dartium
F_LINUX_CH = None
F_MAC_CH = None
F_WIN_CH = None
F_LINUX_CH_TRUNK = None
F_MAC_CH_TRUNK = None
F_WIN_CH_TRUNK = None
F_LINUX_CH_MILESTONE = None
F_MAC_CH_MILESTONE = None
F_WIN_CH_MILESTONE = None


def setup_chromium_factories():
  def new_solution(url, custom_vars, custom_deps):
    return  gclient_factory.GClientSolution(
        url,
        'dartium.deps',
        custom_vars_list = custom_vars,
        custom_deps_list = custom_deps)

  class DartiumFactory(chromium_factory.ChromiumFactory):
    def __init__(self, target_platform=None):
      if target_platform in ['linux2', 'darwin']:
        # We use make/ninja on our linux/mac dartium builders which use
        # 'src/out' as build directory
        build_directory = 'src/out'
      else:
        # On windows we still use msvc which uses 'src/build' as build directory
        build_directory = 'src/build'
      chromium_factory.ChromiumFactory.__init__(self,
                                                build_directory,
                                                target_platform)
      self._solutions = []

    def add_solution(self, solution):
      self._solutions.append(solution)

  m_linux_ch = DartiumFactory('linux2')
  m_linux_ch.add_solution(new_solution(dartium_url, custom_vars_list, []))
  m_mac_ch = DartiumFactory('darwin')
  m_mac_ch.add_solution(new_solution(dartium_url, custom_vars_list, []))
  m_win_ch = DartiumFactory()
  m_win_ch.add_solution(
      new_solution(dartium_url, custom_vars_list, custom_deps_list_win))

  m_linux_ch_trunk = DartiumFactory('linux2')
  m_linux_ch_trunk.add_solution(
      new_solution(dartium_trunk_url, custom_vars_list, []))
  m_mac_ch_trunk = DartiumFactory('darwin')
  m_mac_ch_trunk.add_solution(
      new_solution(dartium_trunk_url, custom_vars_list, []))
  m_win_ch_trunk = DartiumFactory()
  m_win_ch_trunk.add_solution(
      new_solution(dartium_trunk_url, custom_vars_list, custom_deps_list_win))

  m_linux_ch_milestone = DartiumFactory('linux2')
  m_linux_ch_milestone.add_solution(
      new_solution(dartium_milestone_url, custom_vars_list, []))
  m_mac_ch_milestone = DartiumFactory('darwin')
  m_mac_ch_milestone.add_solution(
      new_solution(dartium_milestone_url, custom_vars_list, []))
  m_win_ch_milestone = DartiumFactory()
  m_win_ch_milestone.add_solution(
      new_solution(dartium_milestone_url,
                   custom_vars_list,
                   custom_deps_list_win))

  # Some shortcut to simplify the code in the master.cfg files
  global F_LINUX_CH, F_MAC_CH, F_WIN_CH
  global F_LINUX_CH_TRUNK, F_MAC_CH_TRUNK, F_WIN_CH_TRUNK
  global F_LINUX_CH_MILESTONE, F_MAC_CH_MILESTONE, F_WIN_CH_MILESTONE
  F_LINUX_CH = m_linux_ch.ChromiumFactory
  F_MAC_CH = m_mac_ch.ChromiumFactory
  F_WIN_CH = m_win_ch.ChromiumFactory
  F_LINUX_CH_TRUNK = m_linux_ch_trunk.ChromiumFactory
  F_MAC_CH_TRUNK = m_mac_ch_trunk.ChromiumFactory
  F_WIN_CH_TRUNK = m_win_ch_trunk.ChromiumFactory
  F_LINUX_CH_MILESTONE = m_linux_ch_milestone.ChromiumFactory
  F_MAC_CH_MILESTONE = m_mac_ch_milestone.ChromiumFactory
  F_WIN_CH_MILESTONE = m_win_ch_milestone.ChromiumFactory

setup_chromium_factories()


# These factories are used for building v8
v8_win_default_opts = ['--build-tool=vs']
v8_linux_default_opts = ['buildbot', '--build-tool=make']
v8_mac_default_opts = ['--solution=build/all.xcodeproj', '--build-tool=xcode']

m_v8_linux_stable = v8_factory.V8Factory('v8', target_platform = 'linux2',
                                         branch='branches/' + v8_stable_branch)
m_v8_win32_stable = v8_factory.V8Factory('v8', target_platform = 'win32',
                                         branch='branches/' + v8_stable_branch)
m_v8_mac_stable = v8_factory.V8Factory('v8', target_platform = 'darwin',
                                       branch='branches/' + v8_stable_branch)

def AddGeneralGClientProperties(factory_properties):
  """Adds the general gclient options to ensure we get the correct revisions"""
  # Make sure that pulled in projects have the right revision based on date.
  factory_properties['gclient_transitive'] = True
  # Don't set branch part on the --revision flag - we don't use standard
  # chromium layout and hence this is doing the wrong thing.
  factory_properties['no_gclient_branch'] = True

class DartFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the dart master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform

  # A map used to skip dependencies when a test is not run.
  # The map key is the test name. The map value is an array containing the
  # dependencies that are not needed when this test is not run.
  NEEDED_COMPONENTS = {
  }

  NEEDED_COMPONENTS_INTERNAL = {
  }

  if config.Master.trunk_internal_url:
    CUSTOM_DEPS_JAVA = ('dart/third_party/java',
                        config.Master.trunk_internal_url +
                        '/third_party/openjdk')
    # Fix broken ubuntu OpenJDK by importing windows TZ files
    CUSTOM_TZ = ('dart/third_party/java/linux/j2sdk/jre/lib/zi',
                 config.Master.trunk_internal_url +
                 '/third_party/openjdk/windows/j2sdk/jre/lib/zi')

  def __init__(self, build_dir='dart', target_platform='posix', trunk=False,
               milestone=False, target_os=None, custom_deps_list=None,
               nohooks_on_update=False):
    solutions = []
    self.target_platform = target_platform
    deps_file = '/deps/all.deps'
    dart_url = config.Master.dart_bleeding + deps_file
    # If this is trunk use the deps file from there instead.
    if trunk:
      dart_url = config.Master.dart_trunk + deps_file
    if milestone:
      dart_url = dart_milestone_url + deps_file

    if not custom_deps_list:
      custom_deps_list = []

    if config.Master.trunk_internal_url:
      custom_deps_list.append(self.CUSTOM_DEPS_JAVA)
      custom_deps_list.append(self.CUSTOM_TZ)

    main = gclient_factory.GClientSolution(
        dart_url,
        needed_components=self.NEEDED_COMPONENTS,
        custom_deps_list = custom_deps_list,
        custom_vars_list = custom_vars_list)
    solutions.append(main)

    gclient_factory.GClientFactory.__init__(self, build_dir, solutions,
                                            target_platform=target_platform,
                                            target_os=target_os,
                                            nohooks_on_update=nohooks_on_update)

  def DartFactory(self, target='Release', clobber=False, tests=None,
                  slave_type='BuilderTester', options=None,
                  compile_timeout=1200, build_url=None,
                  factory_properties=None, env=None, triggers=()):
    factory_properties = factory_properties or {}
    AddGeneralGClientProperties(factory_properties)
    tests = tests or []
    gclient_spec = self.BuildGClientSpec(tests)
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               factory_properties=factory_properties)
    # Get the factory command object to create new steps to the factory.
    dart_cmd_obj = dart_commands.DartCommands(factory,
                                              target,
                                              self._build_dir,
                                              self.target_platform,
                                              env=env)

    # We must always add the MaybeClobberStep, since this factory is
    # created at master start, but the choice of clobber or not may be
    # chosen at runtime (e.g. check the 'clobber' box).
    dart_cmd_obj.AddMaybeClobberStep(clobber, options=options)

    # Add the compile step if needed.
    if slave_type in ['BuilderTester', 'Builder', 'Trybot']:
      dart_cmd_obj.AddCompileStep(options=options,
                                  timeout=compile_timeout)

    # Add all the tests.
    if slave_type in ['BuilderTester', 'Trybot', 'Tester']:
      dart_cmd_obj.AddTests(options=options)

    for trigger in triggers:
      dart_cmd_obj.AddTrigger(trigger)

    return factory

  def DartAnnotatedFactory(self, python_script,
                           target='Release', tests=None,
                           timeout=1200, factory_properties=None,
                           env=None, triggers=(), secondAnnotatedRun=False):
    factory_properties = factory_properties or {}
    AddGeneralGClientProperties(factory_properties)
    tests = tests or []
    # Create the spec for the solutions
    gclient_spec = self.BuildGClientSpec(tests)
    # Initialize the factory with the basic steps.
    factory = self.BaseFactory(gclient_spec,
                               factory_properties=factory_properties)
    # Get the factory command object to create new steps to the factory.
    dart_cmd_obj = dart_commands.DartCommands(factory,
                                              target,
                                              self._build_dir,
                                              self._target_platform,
                                              env=env)
    dart_cmd_obj.AddAnnotatedSteps(python_script, timeout=timeout)

    for trigger in triggers:
      dart_cmd_obj.AddTrigger(trigger)

    if secondAnnotatedRun:
      dart_cmd_obj.AddAnnotatedSteps(python_script, timeout=timeout, run=2)
    return factory

class DartUtils(object):
  mac_options = ['--compiler=goma-clang',
                 '--build-tool=ninja',
                 '--',
                 'dartium_builder']
  mac_dbg_options = ['--compiler=goma-clang',
                     '--build-tool=ninja',
                     '--',
                     'dartium_builder']
  linux_options = ['--compiler=goma', '--build-tool=ninja', 'dartium_builder']
  win_options_ninja = ['--build-tool=ninja', 'dartium_builder']

  win_project = 'all.sln;dartium_builder'

  win_rel_factory_properties = {
    'gclient_env': {
      'GYP_DEFINES': 'fastbuild=1',
    },
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }
  win_rel_factory_properties_ninja = {
    'gclient_env': {
      'GYP_DEFINES': 'fastbuild=1',
      'GYP_GENERATORS': 'ninja',
    },
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }

  win_dbg_factory_properties = {
    'gclient_env': {
      # We currently cannot use 'component=shared_library' here, because
      # dartium/src/build/common.gypi will enable 'ExceptionHandling'.
      # This results in the VisualStudio compiler switch '/EHsc' which in turn
      # will unwind the stack and call destructors when doing a longjmp().
      # The DartVM uses it's own mechanism for calling the destructors (see
      # vm/longjump.cc). (i.e. with /EHsc the destructors will be called twice)
      'GYP_DEFINES': 'fastbuild=1 component=static_library',
    },
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }
  mac_factory_properties = {
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }
  linux_factory_properties = {
    'gclient_env': {'GYP_GENERATORS' : 'ninja'},
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }
  linux32_factory_properties = {
    'gclient_env': {'GYP_GENERATORS' : 'ninja',
                    'GYP_DEFINES': 'target_arch=ia32'},
    'gclient_transitive': True,
    'no_gclient_branch': True,
    'annotated_script': 'dart_buildbot_run.py',
  }


  factory_base = {
    'posix': DartFactory(),
    'posixNoRunhooks': DartFactory(nohooks_on_update=True),
    'chromeOnAndroid':
        DartFactory(custom_deps_list=custom_deps_list_chromeOnAndroid),
    'linux-clang': DartFactory(custom_deps_list=custom_deps_list_vm_linux),
    'android': DartFactory(target_os='android'),
    'windows': DartFactory(target_platform='win32'),

    'posix-milestone': DartFactory(milestone=True),
    'linux-clang-milestone':
        DartFactory(custom_deps_list=custom_deps_list_vm_linux, milestone=True),
    'windows-milestone': DartFactory(target_platform='win32', milestone=True),

    'posix-trunk': DartFactory(trunk=True),
    'linux-clang-trunk':
        DartFactory(custom_deps_list=custom_deps_list_vm_linux, trunk=True),
    'windows-trunk': DartFactory(target_platform='win32', trunk=True),
  }
  factory_base_dartium = {
    'dartium-mac-full' : F_MAC_CH(
        target='Release',
        options=mac_options,
        clobber=True,
        tests=['annotated_steps'],
        factory_properties=mac_factory_properties),
    'dartium-mac-inc' : F_MAC_CH(
        target='Release',
        options=mac_options,
        tests=['annotated_steps'],
        factory_properties=mac_factory_properties),
    'dartium-mac-debug' : F_MAC_CH(
        target='Debug',
        compile_timeout=3600,
        options=mac_dbg_options,
        tests=['annotated_steps'],
        factory_properties=mac_factory_properties),
    'dartium-lucid64-full' : F_LINUX_CH(
        target='Release',
        clobber=True,
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux_factory_properties),
    'dartium-lucid64-inc' : F_LINUX_CH(
        target='Release',
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux_factory_properties),
    'dartium-lucid64-debug' : F_LINUX_CH(
        target='Debug',
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux_factory_properties),
    'dartium-win-full' : F_WIN_CH(
        target='Release',
        project=win_project,
        clobber=True,
        tests=['annotated_steps'],
        factory_properties=win_rel_factory_properties),
    'dartium-win-inc' : F_WIN_CH(
        target='Release',
        project=win_project,
        tests=['annotated_steps'],
        factory_properties=win_rel_factory_properties),
    'dartium-win-inc-ninja' : F_WIN_CH(
        target='Release',
        options=win_options_ninja,
        tests=[], # FIXME: no annotated steps -> no gcs uploads
        factory_properties=win_rel_factory_properties_ninja),
    'dartium-win-debug' : F_WIN_CH(
        target='Debug',
        project=win_project,
        tests=['annotated_steps'],
        factory_properties=win_dbg_factory_properties),
    'dartium-lucid32-full' : F_LINUX_CH(
        target='Release',
        clobber=True,
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux32_factory_properties),
    'dartium-lucid64-full-trunk' : F_LINUX_CH_TRUNK(
        target='Release',
        clobber=True,
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux_factory_properties),
    'dartium-win-full-trunk' : F_WIN_CH_TRUNK(
        target='Release',
        project=win_project,
        clobber=True,
        tests=['annotated_steps'],
        factory_properties=win_rel_factory_properties),
    'dartium-mac-full-trunk' : F_MAC_CH_TRUNK(
        target='Release',
        options=mac_options,
        clobber=True,
        tests=['annotated_steps'],
        factory_properties=mac_factory_properties),
    'dartium-lucid32-full-trunk' : F_LINUX_CH_TRUNK(
        target='Release',
        clobber=True,
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux32_factory_properties),
    'dartium-lucid64-full-milestone' : F_LINUX_CH_MILESTONE(
        target='Release',
        clobber=True,
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux_factory_properties),
    'dartium-win-full-milestone' : F_WIN_CH_MILESTONE(
        target='Release',
        project=win_project,
        clobber=True,
        tests=['annotated_steps'],
        factory_properties=win_rel_factory_properties),
    'dartium-mac-full-milestone' : F_MAC_CH_MILESTONE(
        target='Release',
        options=mac_options,
        clobber=True,
        tests=['annotated_steps'],
        factory_properties=mac_factory_properties),
    'dartium-lucid32-full-milestone' : F_LINUX_CH_MILESTONE(
        target='Release',
        clobber=True,
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux32_factory_properties),
     'release-lucid64-trunk' : F_LINUX_CH(
        target='Release',
        clobber=True,
        options=linux_options,
        tests=['annotated_steps'],
        factory_properties=linux_factory_properties),
  }


  def __init__(self, active_master):
    self._active_master = active_master

  @staticmethod
  def monkey_patch_remoteshell():
    # Hack to increase timeout for steps, dart2js debug checked mode takes more
    # than 8 hours.
    RemoteShellCommand.__init__.im_func.func_defaults = (None,
                                                         1,
                                                         1,
                                                         1200,
                                                         48*60*60, {},
                                                         'slave-config',
                                                         True)

  @staticmethod
  def get_svn_poller():
    def dart_tree_file_splitter(path):
      pieces = path.split('/')
      if pieces[0] == 'trunk':
        return ('trunk', '/'.join(pieces[1:]))
      elif pieces[0] == 'branches':
        return ('/'.join(pieces[0:2]),
                '/'.join(pieces[2:]))
      elif pieces[0] == 'experimental':
        return ('/'.join(pieces[0:2]),
                '/'.join(pieces[2:]))
      else:
        return None

    # Polls config.Master.dart_url for changes
    return svnpoller.SVNPoller(svnurl=config.Master.dart_url,
                               split_file=dart_tree_file_splitter,
                               pollinterval=10,
                               revlinktmpl=dart_revision_url)

  def setup_factories(self, variants):
    def setup_dart_factory(v, base, no_annotated):
      triggers = v.get('triggers', ())

      env = v.get('env', {})
      if no_annotated:
        options = {
            'mode': v['mode'],
            'arch': v['arch'],
            'name': v['name'] }
        # TODO(ricow) Remove shards from here when we move dart2dart
        # to annotated.
        if 'shards' in v and 'shard' in v:
          options['shards'] = v['shards']
          options['shard'] = v['shard']
        v['factory_builder'] = base.DartFactory(
            slave_type='BuilderTester',
            clobber=False,
            options=options,
            env=env,
            triggers=triggers,
        )
      else:
        v['factory_builder'] = base.DartAnnotatedFactory(
            python_script='client/tools/buildbot_annotated_steps.py',
            env=env,
            triggers=triggers,
            secondAnnotatedRun=v.get('second_annotated_steps_run', False)
        )

    def setup_v8_factory(v):
      factory = None
      name = v['name']
      arch = v['arch']
      if name == 'v8-linux-release':
        factory = m_v8_linux_stable.V8Factory(
            options=v8_linux_default_opts,
            target='Release',
            tests=[],
            target_arch=arch)
      elif name == 'v8-win-release':
        factory = m_v8_win32_stable.V8Factory(
            options=v8_win_default_opts,
            project='build\\all.sln',
            target='Release',
            tests=[],
            target_arch=arch)
      elif name == 'v8-mac-release':
        factory = m_v8_mac_stable.V8Factory(
            options=v8_mac_default_opts,
            target='Release',
            tests=[],
            target_arch=arch)
      else:
        raise Exception("Unknown v8 builder")
      v['factory_builder'] = factory

    for v in variants:
      platform = v['platform']
      if platform == 'v8_vm':
        setup_v8_factory(v)
      else:
        base = self.factory_base[platform]
        name = v['name']
        no_annotated = ((name.startswith('vm') or
                        name.startswith('dart2dart') or
                        name.startswith('dartc') or
                        name.startswith('new_analyzer') or
                        name.startswith('analyzer_experimental'))
                        and not name.startswith('vm-android')
                        and not name.startswith('cross-')
                        and not name.startswith('target-'))
        setup_dart_factory(v, base, no_annotated)

  def setup_dartium_factories(self, dartium_variants):
    for variant in dartium_variants:
      variant['factory_builder'] = self.factory_base_dartium[variant['name']]

  def get_web_statuses(self):
    public_html = '../master.chromium/public_html'
    templates = ['../master.client.dart/templates',
                 '../master.chromium/templates']
    master_port = self._active_master.master_port
    master_port_alt = self._active_master.master_port_alt

    http_status_push_url = self._active_master.http_status_push_url

    statuses = []
    statuses.append(master_utils.CreateWebStatus(master_port,
                                                 allowForce=True,
                                                 public_html=public_html,
                                                 templates=templates))
    statuses.append(
        master_utils.CreateWebStatus(master_port_alt, allowForce=False))
    if http_status_push_url:
      statuses.append(HttpStatusPush(serverUrl=http_status_push_url))
    return statuses

  @staticmethod
  def get_builders_from_variants(variants,
                                 slaves,
                                 slave_locks,
                                 auto_reboot = False):
    builders = []
    for v in variants:
      builders.append({
         'name': v['name'],
         'builddir': v['name'],
         'factory': v['factory_builder'],
         'slavenames': slaves.GetSlavesName(builder=v['name']),
         'category': v['category'],
         'locks': slave_locks,
         'auto_reboot': auto_reboot})
    return builders

  @staticmethod
  def get_builder_names(variants):
    return [variant['name'] for variant in variants]

  @staticmethod
  def get_slaves(builders):
    # The 'slaves' list defines the set of allowable buildslaves. List all the
    # slaves registered to a builder. Remove dupes.
    return master_utils.AutoSetupSlaves(builders,
                                        config.Master.GetBotPassword())

  def get_mail_notifier_statuses(self, mail_notifiers):
    statuses = []
    for mail_notifier in mail_notifiers:
      notifying_builders = mail_notifier['builders']
      extra_recipients = mail_notifier['extraRecipients']
      send_to_interested_useres = mail_notifier.get('sendToInterestedUsers',
                                                    False)
      statuses.append(
          MailNotifier(fromaddr=self._active_master.from_address,
                       mode='problem',
                       sendToInterestedUsers=send_to_interested_useres,
                       extraRecipients=extra_recipients,
                       lookup=master_utils.FilterDomain(),
                       builders=notifying_builders))
    return statuses
