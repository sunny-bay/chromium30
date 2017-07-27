# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common steps for recipes that sync/build Android sources."""

from slave import recipe_api

class AOSPApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(AOSPApi, self).__init__(**kwargs)
    self._repo_path = None

  # TODO(iannucci): use path.checkout
  SLAVE_ANDROID_ROOT_NAME = 'android-src'
  _CHROMIUM_IN_ANDROID_SUBPATH = 'external/chromium_org'

  @property
  def slave_chromium_in_android_path(self):
    return self.m.path.slave_build(self.SLAVE_ANDROID_ROOT_NAME,
                                   self._CHROMIUM_IN_ANDROID_SUBPATH)

  @property
  def build_path(self):
    return self.m.path.slave_build(self.SLAVE_ANDROID_ROOT_NAME)

  @property
  def slave_android_out_path(self):
    return self.m.path.slave_build(self.SLAVE_ANDROID_ROOT_NAME, 'out')

  @property
  def with_lunch_command(self):
    return [self.m.path.build('scripts', 'slave', 'android', 'with_lunch'),
            self.build_path,
            self.c.lunch_flavor]

  def chromium_with_trimmed_deps(self, use_revision=True):
    svn_revision = None
    if use_revision and 'revision' in self.m.properties:
      svn_revision = str(self.m.properties['revision'])

    spec = self.m.gclient.make_config('chromium_empty')
    spec.solutions[0].revision = svn_revision
    self.m.gclient.spec_alias = 'empty_deps'
    yield self.m.gclient.checkout(spec)

    yield self.m.step(
      'calculate trimmed deps',
      [self.m.path.checkout('android_webview', 'buildbot', 'deps_whitelist.py'),
       '--method', 'android_build',
       '--path-to-deps', self.m.path.checkout('DEPS'),
       self.m.json.output()])

    spec = self.m.gclient.make_config('chromium_bare')
    deps_blacklist = self.m.step_history.last_step().json.output['blacklist']
    spec.solutions[0].custom_deps = deps_blacklist
    spec.solutions[0].revision = svn_revision
    spec.target_os = ['android']
    self.m.gclient.spec_alias = 'trimmed'
    yield self.m.gclient.checkout(spec)
    del self.m.gclient.spec_alias

  def lastchange_steps(self):
    lastchange_command = self.m.path.checkout('build', 'util', 'lastchange.py')
    yield (
      self.m.step('Chromium LASTCHANGE', [
        lastchange_command,
        '-o', self.m.path.checkout('build', 'util', 'LASTCHANGE'),
        '-s', self.m.path.checkout()]),
      self.m.step('Blink LASTCHANGE', [
        lastchange_command,
        '-o', self.m.path.checkout('build', 'util', 'LASTCHANGE.blink'),
        '-s', self.m.path.checkout('third_party', 'WebKit')])
    )

  # TODO(iannucci): Refactor repo stuff into another module?
  def repo_init_steps(self):
    # The version of repo checked into depot_tools doesn't support switching
    # between branches correctly due to
    # https://code.google.com/p/git-repo/issues/detail?id=46 which is why we use
    # the copy of repo from the Android tree.
    # The copy of repo from depot_tools is only used to bootstrap the Android
    # tree checkout.
    repo_in_android_path = self.m.path.slave_build(
        self.SLAVE_ANDROID_ROOT_NAME, '.repo', 'repo', 'repo')
    repo_copy_dir = self.m.path.slave_build('repo_copy')
    repo_copy_path = self.m.path.slave_build('repo_copy', 'repo')
    self._repo_path = self.m.path.depot_tools('repo')
    if self.m.path.exists(repo_in_android_path):
      self._repo_path = repo_copy_path
      if not self.m.path.exists(repo_copy_dir):
        yield self.m.step('mkdir repo copy dir',
                             ['mkdir', '-p', repo_copy_dir])
      yield self.m.step('copy repo from Android', [
        'cp', repo_in_android_path, repo_copy_path])
    if not self.m.path.exists(self.build_path):
      yield self.m.step('mkdir android source root', [
        'mkdir', self.build_path])
    yield self.m.step('repo init', [
      self._repo_path,
      'init',
      '-u', self.c.repo.url,
      '-b', self.c.repo.branch],
      cwd=self.build_path)

  def generate_local_manifest_step(self):
    local_manifest_ndk_pin_revision = []
    if self.c.ndk_pin_revision:
      local_manifest_ndk_pin_revision = ['--ndk-revision',
                                         self.c.ndk_pin_revision]
    yield self.m.step(
        'generate local manifest', [
          self.m.path.checkout('android_webview', 'buildbot',
                             'generate_local_manifest.py'),
          self.build_path,
          self._CHROMIUM_IN_ANDROID_SUBPATH] +
        local_manifest_ndk_pin_revision)


  def repo_sync_steps(self):
    # repo_init_steps must have been invoked first.
    yield self.m.step('repo sync',
                    [self._repo_path, 'sync'] + self.c.repo.sync_flags,
                    cwd=self.build_path)

  def symlink_chromium_into_android_tree_step(self):
    if self.m.path.exists(self.slave_chromium_in_android_path):
      yield self.m.step('remove chromium_org',
                      ['rm', '-rf', self.slave_chromium_in_android_path])

    yield self.m.step('symlink chromium_org', [
      'ln', '-s',
      self.m.path.checkout(),
      self.slave_chromium_in_android_path]),

  def gyp_webview_step(self):
    yield self.m.step('gyp_webview', self.with_lunch_command + [
      self.m.path.slave_build(
        self.SLAVE_ANDROID_ROOT_NAME, 'external', 'chromium_org',
        'android_webview', 'tools', 'gyp_webview')],
      cwd=self.slave_chromium_in_android_path)

  def compile_step(self, build_tool, step_name='compile', targets=None,
                   use_goma=True, src_dir=None, target_out_dir=None,
                   envsetup=None):
    src_dir = src_dir or self.build_path
    target_out_dir = target_out_dir or self.slave_android_out_path
    envsetup = envsetup or self.with_lunch_command
    targets = targets or []
    compiler_option = []
    compile_script = [self.m.path.build('scripts', 'slave', 'compile.py')]
    if use_goma and self.m.path.exists(self.m.path.build('goma')):
      compiler_option = ['--compiler', 'goma',
                         '--goma-dir', self.m.path.build('goma')]
    yield self.m.step(step_name,
                      envsetup +
                      compile_script +
                      targets +
                      ['--build-dir', self.m.path.slave_build()] +
                      ['--src-dir', src_dir] +
                      ['--build-tool', build_tool] +
                      ['--verbose'] +
                      compiler_option,
                      cwd=self.m.path.slave_build())

