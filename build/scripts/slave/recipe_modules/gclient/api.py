# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

GIT_DEFAULT_WHITELIST = frozenset((
  'tools_build',
))

def jsonish_to_python(spec, is_top=False):
  ret = ''
  if is_top:  # We're the 'top' level, so treat this dict as a suite.
    ret = '\n'.join(
      '%s = %s' % (k, jsonish_to_python(spec[k])) for k in sorted(spec)
    )
  else:
    if isinstance(spec, dict):
      ret += '{'
      ret += ', '.join(
        "%s: %s" % (repr(str(k)), jsonish_to_python(spec[k])) for k in sorted(spec))
      ret += '}'
    elif isinstance(spec, list):
      ret += '['
      ret += ', '.join(jsonish_to_python(x) for x in spec)
      ret += ']'
    elif isinstance(spec, basestring):
      ret = repr(str(spec))
    else:
      ret = repr(spec)
  return ret


class GclientApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(GclientApi, self).__init__(**kwargs)
    self.USE_MIRROR = None
    self._spec_alias = None

  def __call__(self, name, cmd, **kwargs):
    """Wrapper for easy calling of gclient steps."""
    assert isinstance(cmd, (list, tuple))
    prefix = 'gclient '
    if self.spec_alias:
      prefix = ('[spec: %s] ' % self.spec_alias) + prefix

    return self.m.python(
        prefix + name, self.m.path.depot_tools('gclient.py'), cmd, **kwargs)

  @property
  def use_mirror(self):
    """Indicates if gclient will use mirrors in its configuration."""
    if self.USE_MIRROR is None:
      self.USE_MIRROR = self.m.properties.get('use_mirror', True)
    return self.USE_MIRROR

  @use_mirror.setter
  def use_mirror(self, val):  # pragma: no cover
    self.USE_MIRROR = val

  @property
  def spec_alias(self):
    """Optional name for the current spec for step naming."""
    return self._spec_alias

  @spec_alias.setter
  def spec_alias(self, name):
    self._spec_alias = name

  @spec_alias.deleter
  def spec_alias(self):
    self._spec_alias = None

  def get_config_defaults(self, config_name):
    ret = {
      'USE_MIRROR': self.use_mirror
    }
    if config_name in GIT_DEFAULT_WHITELIST:
      ret['GIT_MODE'] = True
    ret['CACHE_DIR'] = self.m.path.root('git_cache')
    return ret

  def checkout(self, gclient_config=None, revert=True):
    """Return a step generator function for gclient checkouts."""
    cfg = gclient_config or self.c
    assert cfg.complete()

    spec_string = jsonish_to_python(cfg.as_jsonish(), True)

    revisions = []
    for s in cfg.solutions:
      if s.revision is not None:
        revisions.extend(['--revision', '%s@%s' % (s.name, s.revision)])

    steps = [
      self('setup', ['config', '--spec', spec_string])
    ]

    if not cfg.GIT_MODE:
      if revert:
        steps.append(self.revert())
      steps.append(self('sync', ['sync', '--nohooks'] + revisions))
    else:
      # clean() isn't used because the gclient sync flags passed in checkout()
      # do much the same thing, and they're more correct than doing a separate
      # 'gclient revert' because it makes sure the other args are correct when
      # a repo was deleted and needs to be re-cloned (notably
      # --with_branch_heads), whereas 'revert' uses default args for clone
      # operations.
      #
      # TODO(mmoss): To be like current official builders, this step could just
      # delete the whole <slave_name>/build/ directory and start each build
      # from scratch. That might be the least bad solution, at least until we
      # have a reliable gclient method to produce a pristine working dir for
      # git-based builds (e.g. maybe some combination of 'git reset/clean -fx'
      # and removing the 'out' directory).
      j = '-j2' if self.m.platform.is_win else '-j8'
      steps.append(self('sync',
        ['sync', '--verbose', '--with_branch_heads', '--nohooks', j,
        '--reset', '--delete_unversioned_trees', '--force', '--upstream',
        '--no-nag-max'] + revisions))

      cfg_cmds = [
        ('user.name', 'local_bot'),
        ('user.email', 'local_bot@example.com'),
      ]
      for var, val in cfg_cmds:
        name = 'recurse (git config %s)' % var
        steps.append(self(name, ['recurse', 'git', 'config', var, val]))

    for c in cfg.checkouts:
      self.m.path.add_checkout(self.m.path.slave_build(c))
    for s in cfg.solutions:
      self.m.path.add_checkout(self.m.path.slave_build(s.name))

    return steps

  def revert(self):
    """Return a gclient_safe_revert step."""
    # Not directly calling gclient, so don't use self().
    prefix = 'gclient '
    if self.spec_alias:
      prefix = ('[spec: %s] ' % self.spec_alias) + prefix

    return self.m.python(prefix + 'revert',
        self.m.path.build('scripts', 'slave', 'gclient_safe_revert.py'),
        ['.', self.m.path.depot_tools('gclient', wrapper=True)],
    )

  def runhooks(self, args=None, **kwargs):
    """Return a 'gclient runhooks' step."""
    args = args or []
    assert isinstance(args, (list, tuple))
    return self('runhooks', ['runhooks'] + list(args), **kwargs)
