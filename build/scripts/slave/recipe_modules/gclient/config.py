# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import types

from slave.recipe_configs_util import config_item_context, ConfigGroup, BadConf
from slave.recipe_configs_util import DictConfig, SimpleConfig, StaticConfig
from slave.recipe_configs_util import SetConfig, ConfigList, ListConfig

def BaseConfig(USE_MIRROR=True, GIT_MODE=False, CACHE_DIR=None, **_kwargs):
  deps = '.DEPS.git' if GIT_MODE else 'DEPS'
  cache_dir = str(CACHE_DIR) if GIT_MODE and CACHE_DIR else None
  return ConfigGroup(
    solutions = ConfigList(
      lambda: ConfigGroup(
        name = SimpleConfig(basestring),
        url = SimpleConfig(basestring),
        deps_file = SimpleConfig(basestring, empty_val=deps, required=False),
        managed = SimpleConfig(bool, empty_val=True, required=False),
        custom_deps = DictConfig(value_type=(basestring, types.NoneType)),
        custom_vars = DictConfig(value_type=basestring),
        safesync_url = SimpleConfig(basestring, required=False),

        revision = SimpleConfig(basestring, required=False, hidden=True),
      )
    ),
    deps_os = DictConfig(value_type=basestring),
    hooks = ListConfig(basestring),
    target_os = SetConfig(basestring),
    target_os_only = SimpleConfig(bool, empty_val=False, required=False),
    checkouts = ListConfig(basestring, hidden=True),
    cache_dir = StaticConfig(cache_dir, hidden=False),

    GIT_MODE = StaticConfig(bool(GIT_MODE)),
    USE_MIRROR = StaticConfig(bool(USE_MIRROR)),
  )

VAR_TEST_MAP = {
  'USE_MIRROR': (True, False),
  'GIT_MODE':   (True, False),
  'CACHE_DIR':  (None, 'CACHE_DIR'),
}

TEST_NAME_FORMAT = lambda kwargs: (
  'using_mirror-%(USE_MIRROR)s-git_mode-%(GIT_MODE)s-cache_dir-%(using)s' %
  dict(using=bool(kwargs['CACHE_DIR']), **kwargs)
)

config_ctx = config_item_context(BaseConfig, VAR_TEST_MAP, TEST_NAME_FORMAT)

def ChromiumSvnSubURL(c, *pieces):
  BASES = ('https://src.chromium.org',
           'svn://svn-mirror.golo.chromium.org')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)

def ChromiumGitURL(_c, *pieces):
  return '/'.join(('https://chromium.googlesource.com',) + pieces)

def ChromiumSrcURL(c):
  if c.GIT_MODE:
    return ChromiumGitURL(c, 'chromium', 'src.git')
  else:
    return ChromiumSvnSubURL(c, 'chrome', 'trunk', 'src')

def BlinkURL(c):
  if c.GIT_MODE:
    return ChromiumGitURL(c, 'chromium', 'blink.git')
  else:
    return ChromiumSvnSubURL(c, 'blink', 'trunk')

def ChromeSvnSubURL(c, *pieces):
  BASES = ('svn://svn.chromium.org',
           'svn://svn-mirror.golo.chromium.org')
  return '/'.join((BASES[c.USE_MIRROR],) + pieces)

def ChromeInternalGitURL(_c, *pieces):
  return '/'.join(('https://chrome-internal.googlesource.com',) + pieces)

def ChromeInternalSrcURL(c):
  if c.GIT_MODE:
    return ChromeInternalGitURL(c, 'chrome', 'src-internal.git')
  else:
    return ChromeSvnSubURL(c, 'chrome-internal', 'trunk', 'src-internal')

def mirror_only(c, obj):
  return obj if c.USE_MIRROR else obj.__class__()

@config_ctx()
def chromium_bare(c):
  s = c.solutions.add()
  s.name = 'src'
  s.url = ChromiumSrcURL(c)
  s.custom_vars = mirror_only(c, {
    'googlecode_url': 'svn://svn-mirror.golo.chromium.org/%s',
    'nacl_trunk': 'svn://svn-mirror.golo.chromium.org/native_client/trunk',
    'sourceforge_url': 'svn://svn-mirror.golo.chromium.org/%(repo)s',
    'webkit_trunk': 'svn://svn-mirror.golo.chromium.org/blink/trunk'})

@config_ctx(includes=['chromium_bare'])
def chromium_empty(c):
  c.solutions[0].deps_file = ''

@config_ctx(includes=['chromium_bare'])
def chromium(c):
  s = c.solutions[0]
  s.custom_deps = mirror_only(c, {
    'src/third_party/WebKit/LayoutTests': None,
    'src/webkit/data/layout_tests/LayoutTests': None})

@config_ctx()
def blink_bare(c):
  s = c.solutions.add()
  s.name = 'blink'
  s.url = BlinkURL(c)

# TODO(iannucci,vadimsh): Switch this to src-limited
@config_ctx()
def chrome_internal(c):
  s = c.solutions.add()
  s.name = 'src-internal'
  s.url = ChromeInternalSrcURL(c)
  # Remove some things which are generally not needed
  s.custom_deps = {
    "src/data/autodiscovery" : None,
    "src/data/page_cycler" : None,
    "src/tools/grit/grit/test/data" : None,
    "src/chrome/test/data/perf/frame_rate/private" : None,
    "src/data/mozilla_js_tests" : None,
    "src/chrome/test/data/firefox2_profile/searchplugins" : None,
    "src/chrome/test/data/firefox2_searchplugins" : None,
    "src/chrome/test/data/firefox3_profile/searchplugins" : None,
    "src/chrome/test/data/firefox3_searchplugins" : None,
    "src/chrome/test/data/ssl/certs" : None,
    "src/data/mach_ports" : None,
    "src/data/esctf" : None,
    "src/data/selenium_core" : None,
    "src/chrome/test/data/plugin" : None,
    "src/data/memory_test" : None,
    "src/data/tab_switching" : None,
    "src/chrome/test/data/osdd" : None,
    "src/webkit/data/bmp_decoder":None,
    "src/webkit/data/ico_decoder":None,
    "src/webkit/data/test_shell/plugins":None,
    "src/webkit/data/xbm_decoder":None,
  }

@config_ctx(includes=['chromium'])
def blink(c):
  c.solutions[0].custom_deps = {
    'src/third_party/WebKit': BlinkURL(c)
  }
  c.solutions[0].custom_vars['webkit_revision'] = 'HEAD'

@config_ctx(includes=['blink', 'chrome_internal'])
def blink_internal(c):
  # Add back the webkit data dependencies
  needed_components_internal = [
    "src/webkit/data/bmp_decoder",
    "src/webkit/data/ico_decoder",
    "src/webkit/data/test_shell/plugins",
    "src/webkit/data/xbm_decoder",
  ]
  for key in needed_components_internal:
    del c.solutions[1].custom_deps[key]


@config_ctx()
def nacl(c):
  if c.GIT_MODE:
    raise BadConf('nacl only supports svn')
  s = c.solutions.add()
  s.name = 'native_client'
  s.url = ChromiumSvnSubURL(c, 'native_client', 'trunk', 'src', 'native_client')
  s.custom_vars = mirror_only(c, {
    'webkit_trunk': 'svn://svn-mirror.golo.chromium.org/blink/trunk',
    'googlecode_url': 'svn://svn-mirror.golo.chromium.org/%s',
    'sourceforge_url': 'svn://svn-mirror.golo.chromium.org/%(repo)s'})

  s = c.solutions.add()
  s.name = 'supplement.DEPS'
  s.url = ChromiumSvnSubURL(c, 'native_client', 'trunk', 'deps',
                            'supplement.DEPS')

@config_ctx()
def tools_build(c):
  if not c.GIT_MODE:
    raise BadConf('tools_build only supports git')
  s = c.solutions.add()
  s.name = 'build'
  s.url = ChromiumGitURL(c, 'chromium', 'tools', 'build.git')


