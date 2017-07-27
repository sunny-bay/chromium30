# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_configs_util import config_item_context, ConfigGroup
from slave.recipe_configs_util import DictConfig, SimpleConfig, StaticConfig
from slave.recipe_configs_util import SetConfig, BadConf

# Because of the way that we use decorators, pylint can't figure out the proper
# type signature of functions annotated with the @config_ctx decorator.
# pylint: disable=E1123

def norm_host_platform(plat):
  if plat.startswith('linux'):
    return 'linux'
  elif plat.startswith(('win', 'cygwin')):
    return 'win'
  elif plat.startswith(('darwin', 'mac')):
    return 'mac'
  else:  # pragma: no cover
    raise ValueError('Don\'t understand platform "%s"' % plat)

def norm_targ_platform(plat):
  try:
    return norm_host_platform(plat)
  except ValueError:
    pass

  if plat.startswith('ios'):
    return 'ios'
  elif plat.startswith('android'):
    return 'android'
  elif plat.startswith('chromeos'):
    return 'chromeos'
  else:  # pragma: no cover
    raise ValueError('Don\'t understand platform "%s"' % plat)

def norm_bits(arch):
  if not arch:
    return None
  return 64 if '64' in str(arch) else 32

def norm_arch(arch):
  if not arch:
    return None

  # platform.machine() can be things like:
  #   * x86_64
  #   * i386
  #   * etc.
  # So we cheat a bit here and just look at the first char as a heruistic.
  return 'intel' if arch[0] in 'xi' else 'arm'

def norm_build_config(build_config=None):
  return 'Release' if build_config == 'Release' else 'Debug'

# Because bits and arch actually accept None as a valid parameter,
# give them a means of distinguishing when they've been passed a default
# argument v. None
HostPlatformValue = object()

# Schema for config items in this module.
def BaseConfig(HOST_PLATFORM=None, HOST_ARCH=None, HOST_BITS=None,
               TARGET_PLATFORM=None, TARGET_ARCH=HostPlatformValue,
               TARGET_BITS=32, BUILD_CONFIG=norm_build_config(),
               **_kwargs):
  assert HOST_PLATFORM and HOST_ARCH and HOST_BITS
  TARGET_PLATFORM = TARGET_PLATFORM or HOST_PLATFORM
  TARGET_ARCH = HOST_ARCH if TARGET_ARCH is HostPlatformValue else TARGET_ARCH

  return ConfigGroup(
    compile_py = ConfigGroup(
      default_targets = SetConfig(basestring),
      build_tool = SimpleConfig(basestring),
      compiler = SimpleConfig(basestring, required=False),
    ),
    gyp_env = ConfigGroup(
      GYP_DEFINES = DictConfig(lambda i: ('%s=%s' % i), ' '.join, (basestring,int)),
      GYP_GENERATORS = SetConfig(basestring, ','.join),
      GYP_GENERATOR_FLAGS = DictConfig(
        lambda i: ('%s=%s' % i), ' '.join, (basestring,int)),
      GYP_MSVS_VERSION = SimpleConfig(basestring, required=False),
    ),
    build_dir = SimpleConfig(basestring),

    # Some platforms do not have a 1:1 correlation of BUILD_CONFIG to what is
    # passed as --target on the command line.
    build_config_fs = SimpleConfig(basestring),

    BUILD_CONFIG = StaticConfig(norm_build_config(BUILD_CONFIG)),

    HOST_PLATFORM = StaticConfig(norm_host_platform(HOST_PLATFORM)),
    HOST_ARCH = StaticConfig(norm_arch(HOST_ARCH)),
    HOST_BITS = StaticConfig(norm_bits(HOST_BITS)),

    TARGET_PLATFORM = StaticConfig(norm_targ_platform(TARGET_PLATFORM)),
    TARGET_ARCH = StaticConfig(norm_arch(TARGET_ARCH)),
    TARGET_BITS = StaticConfig(norm_bits(TARGET_BITS)),
  )

TEST_FORMAT = (
  '%(BUILD_CONFIG)s-'
  '%(HOST_PLATFORM)s.%(HOST_ARCH)s.%(HOST_BITS)s'
  '-to-'
  '%(TARGET_PLATFORM)s.%(TARGET_ARCH)s.%(TARGET_BITS)s'
)

# Used by the test harness to inspect and generate permutations for this
# config module.  {varname -> [possible values]}
VAR_TEST_MAP = {
  'HOST_PLATFORM':   ('linux', 'win', 'mac'),
  'HOST_ARCH':       ('intel',),
  'HOST_BITS':       (32, 64),

  'TARGET_PLATFORM': ('linux', 'win', 'mac', 'ios', 'android', 'chromeos'),
  'TARGET_ARCH':     ('intel', 'arm', None),
  'TARGET_BITS':     (32, 64, None),

  'BUILD_CONFIG':    ('Debug', 'Release'),
}
config_ctx = config_item_context(BaseConfig, VAR_TEST_MAP, TEST_FORMAT)


@config_ctx(is_root=True)
def BASE(c):
  host_targ_tuples = [(c.HOST_PLATFORM, c.HOST_ARCH, c.HOST_BITS),
                      (c.TARGET_PLATFORM, c.TARGET_ARCH, c.TARGET_BITS)]

  for (plat, arch, bits) in host_targ_tuples:
    if plat in ('ios', 'android'):
      if arch or bits:
        raise BadConf('Cannot specify arch or bits for %s' % plat)
    else:
      if not (arch and bits):
        raise BadConf('"%s" requires arch and bits to be set' % plat)

    if arch == 'arm' and plat != 'chromeos':
      raise BadConf('Arm arch is only supported on chromeos')

  if c.HOST_PLATFORM not in ('win', 'linux', 'mac'):  # pragma: no cover
    raise BadConf('Cannot build on "%s"' % c.HOST_PLATFORM)

  if c.HOST_BITS < c.TARGET_BITS:
    raise BadConf('Invalid config: host bits < targ bits')
  if c.TARGET_PLATFORM == 'ios' and c.HOST_PLATFORM != 'mac':
    raise BadConf('iOS target only supported on mac host')
  if (c.TARGET_PLATFORM in ('chromeos', 'android') and
      c.HOST_PLATFORM != 'linux'):
    raise BadConf('Can not compile "%s" on "%s"' %
                  (c.TARGET_PLATFORM, c.HOST_PLATFORM))
  if c.HOST_PLATFORM in ('win', 'mac') and c.TARGET_PLATFORM != c.HOST_PLATFORM:
    raise BadConf('Can not compile "%s" on "%s"' %
                  (c.TARGET_PLATFORM, c.HOST_PLATFORM))
  if c.HOST_PLATFORM == 'linux' and c.TARGET_PLATFORM in ('win', 'mac'):
    raise BadConf('Can not compile "%s" on "%s"' %
                  (c.TARGET_PLATFORM, c.HOST_PLATFORM))

  c.build_config_fs = c.BUILD_CONFIG
  if c.HOST_PLATFORM == 'win':
    if c.TARGET_BITS == 64:
      # Windows requires 64-bit builds to be in <dir>_x64.
      c.build_config_fs += '_x64'
      c.gyp_env.GYP_MSVS_VERSION = '2012'
      c.gyp_env.GYP_DEFINES['target_arch'] = 'x64'
    else:
      c.gyp_env.GYP_MSVS_VERSION = '2010'

  if c.BUILD_CONFIG == 'Release':
    static_library(c, final=False)
  elif c.BUILD_CONFIG == 'Debug':
    shared_library(c, final=False)
  else:  # pragma: no cover
    raise BadConf('Unknown build config "%s"' % c.BUILD_CONFIG)

@config_ctx(group='builder')
def ninja(c):
  c.gyp_env.GYP_GENERATORS.add('ninja')
  c.compile_py.build_tool = 'ninja'
  c.build_dir = 'out'

@config_ctx(group='builder')
def msvs(c):
  if c.HOST_PLATFORM != 'win':
    raise BadConf('can not use msvs on "%s"' % c.HOST_PLATFORM)
  c.gyp_env.GYP_GENERATORS.add('msvs')
  c.gyp_env.GYP_GENERATOR_FLAGS['msvs_error_on_missing_sources'] = 1
  c.compile_py.build_tool = 'msvs'
  c.build_dir = 'out'

@config_ctx(group='builder')
def xcodebuild(c):
  if c.HOST_PLATFORM != 'mac':
    raise BadConf('can not use xcodebuild on "%s"' % c.HOST_PLATFORM)
  c.gyp_env.GYP_GENERATORS.add('xcodebuild')

@config_ctx(group='compiler')
def clang(c):
  c.compile_py.compiler = 'clang'

@config_ctx(group='compiler')
def default_compiler(_c):
  pass

@config_ctx(deps=['compiler', 'builder'], group='distributor')
def goma(c):
  if c.compile_py.build_tool == 'msvs':  # pragma: no cover
    raise BadConf('goma doesn\'t work with msvs')

  # TODO(iannucci): support clang and jsonclang
  if not c.compile_py.compiler:
    c.compile_py.compiler = 'goma'
  else:  # pragma: no cover
    raise BadConf('goma config dosen\'t understand %s' % c.compile_py.compiler)

  if c.TARGET_PLATFORM == 'win':
    pch(c, invert=True)

@config_ctx()
def pch(c, invert=False):
  if c.TARGET_PLATFORM == 'win':
    c.gyp_env.GYP_DEFINES['chromium_win_pch'] = int(not invert)

@config_ctx()
def dcheck(c, invert=False):
  c.gyp_env.GYP_DEFINES['dcheck_always_on'] = int(not invert)

@config_ctx()
def fastbuild(c, invert=False):
  c.gyp_env.GYP_DEFINES['fastbuild'] = int(not invert)

@config_ctx(group='link_type')
def shared_library(c):
  c.gyp_env.GYP_DEFINES['component'] = 'shared_library'

@config_ctx(group='link_type')
def static_library(c):
  c.gyp_env.GYP_DEFINES['component'] = 'static_library'

@config_ctx()
def trybot_flavor(c):
  fastbuild(c, optional=True)
  dcheck(c, optional=True)

#### 'Full' configurations
@config_ctx(includes=['ninja', 'default_compiler', 'goma'])
def chromium(c):
  c.compile_py.default_targets = ['All', 'chromium_builder_tests']

@config_ctx(includes=['chromium'])
def blink(c):
  c.compile_py.default_targets = ['all_webkit']
