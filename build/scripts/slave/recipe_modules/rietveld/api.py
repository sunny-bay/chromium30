# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class RietveldApi(recipe_api.RecipeApi):
  def calculate_issue_root(self):
    root = self.m.properties.get('root', '')
    # FIXME: Rietveld passes the blink path as src/third_party/WebKit
    #        so we have to strip the src bit off before passing to
    #        api.checkout_path. :(
    if root.startswith('src'):
      root = root[3:].lstrip('/')
    return root

  def apply_issue(self, *root_pieces):
    return self.m.python('apply_issue',
        self.m.path.depot_tools('apply_issue.py'), [
        '-r', self.m.path.checkout(*root_pieces),
        '-i', self.m.properties['issue'],
        '-p', self.m.properties['patchset'],
        '-s', self.m.properties['rietveld'],
        '--no-auth'])

