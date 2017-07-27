#!/usr/bin/env python
# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for verification/project_base.py."""

import logging
import os
import re
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT_DIR, '..'))

import find_depot_tools  # pylint: disable=W0611
import breakpad

# From tests/
import mocks

from verification import project_base


class ProjectBaseTest(mocks.TestCase):
  def test_skip(self):
    self._check(project_base.base.IGNORED, '', False)

  def test_base(self):
    self.pending.base_url = 'http://example.com/'
    self._check(project_base.base.SUCCEEDED, '', False)

  def test_relpath(self):
    self.pending.base_url = 'http://example.com/foo/bar'
    self._check(project_base.base.SUCCEEDED, 'foo/bar', False)

  def test_base_dupe(self):
    self.pending.base_url = 'http://example2.com/foo'
    self._check(project_base.base.SUCCEEDED, 'foo', True)

  def _check(self, state, relpath, expected_stack):
    stack = []
    self.mock(breakpad, 'SendStack', lambda *args: stack.append(args))
    base = re.escape('http://example.com/')
    base2 = re.escape('http://example2.com/')
    ver = project_base.ProjectBaseUrlVerifier(
        [
          r'^%s$' % base,
          r'^%s(.+)$' % base,
          r'^%s(.+)$' % base2,
          r'^%s(.+)$' % base2,
        ])
    ver.verify(self.pending)
    ver.update_status([self.pending])
    name = project_base.ProjectBaseUrlVerifier.name
    self.assertEqual([name], self.pending.verifications.keys())
    self.assertEqual(None, self.pending.verifications[name].error_message)
    self.assertEqual(self.pending.verifications[name].get_state(), state)
    self.assertEqual(relpath, self.pending.relpath)
    if expected_stack:
      self.assertEqual(1, len(stack))
      self.assertEqual(2, len(stack[0]))
      self.assertEqual(
          ('pending.base_url triggered multiple matches',), stack[0][0].args)
      self.assertEqual('', stack[0][1])
    else:
      self.assertEqual([], stack)


if __name__ == '__main__':
  logging.basicConfig(level=logging.ERROR)
  unittest.main()
