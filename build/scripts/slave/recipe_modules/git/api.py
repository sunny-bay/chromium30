# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class GitApi(recipe_api.RecipeApi):
  def command(self, *args, **kwargs):
    """Return a git command step."""
    name = 'git '+args[0]
    # Distinguish 'git config' commands by the variable they are setting.
    if args[0] == 'config' and not args[1].startswith('-'):
      name += ' ' + args[1]
    if 'cwd' not in kwargs:
      kwargs.setdefault('cwd', self.m.path.checkout())
    return self.m.step(name, ['git'] + list(args), **kwargs)

  def checkout(self, url, dir_path=None, branch='master', recursive=False,
               keep_paths=None):
    """Returns an iterable of steps to perform a full git checkout.
    Args:
      url (string): url of remote repo to use as upstream
      dir_path (string): optional directory to clone into
      branch (string): branch to check out after fetching
      recursive (bool): whether to recursively fetch submodules or not
      keep_paths (iterable of strings): paths to ignore during git-clean;
          paths are gitignore-style patterns relative to checkout_path.
    """
    if not dir_path:
      dir_path = url.rsplit('/', 1)[-1]
      if dir_path.endswith('.git'):  # ex: https://host/foobar.git
        dir_path = dir_path[:-len('.git')]

      # ex: ssh://host:repo/foobar/.git
      dir_path = dir_path or dir_path.rsplit('/', 1)[-1]

      dir_path = self.m.path.slave_build(dir_path)
    assert self.m.path.pardir not in dir_path
    recursive_args = ['--recurse-submodules'] if recursive else []
    clean_args = list(self.m.itertools.chain(
        *[('-e', path) for path in keep_paths or []]))
    self.m.path.add_checkout(dir_path)
    return [
      self.m.step(
        'git setup', [
          self.m.path.build('scripts', 'slave', 'git_setup.py'),
          '--path', dir_path,
          '--url', url,
        ]),
      self.command('fetch', 'origin', *recursive_args),
      self.command('update-ref', 'refs/heads/'+branch, 'origin/'+branch),
      self.command('clean', '-f', '-d', '-x', *clean_args),
      self.command('checkout', '-f', branch),
      self.command('submodule', 'update', '--init', '--recursive',
                   cwd=dir_path),
    ]
