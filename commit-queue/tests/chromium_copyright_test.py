#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for post_processors/chromium_copyright.py."""

import datetime
import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(ROOT_DIR, '..')
sys.path.insert(0, PROJECT_DIR)

import find_depot_tools  # pylint: disable=W0611
from testing_support import trial_dir
import patch

from post_processors import chromium_copyright


GIT_NEW = (
    'diff --git a/foo b/foo\n'
    'new file mode 100644\n'
    'index 0000000..5716ca5\n'
    '--- /dev/null\n'
    '+++ b/foo\n'
    '@@ -0,0 +1 @@\n'
    '+bar\n')

GIT_PATCH = (
    'diff --git a/foo3 b/foo3\n'
    'index 257cc56..5716ca5\n'
    '--- a/foo3\n'
    '+++ b/foo3\n'
    '@@ -1 +1 @@\n'
    '-foo\n'
    '+bar\n')

class CCTest(trial_dir.TestCase):
  def setUp(self):
    super(CCTest, self).setUp()
    class FakeCheckout(object):
      project_path = self.root_dir
    self.checkout = FakeCheckout()
    open(self.path('foo1'), 'w').write('bar')

  @staticmethod
  def get_patch():
    return patch.PatchSet([
        patch.FilePatchDelete('foo2', True),
        patch.FilePatchDiff('foo', GIT_NEW, []),
        patch.FilePatchBinary('foo1', 'data', [], True),
        patch.FilePatchDiff('foo3', GIT_PATCH, []),
    ])

  def path(self, base_file):
    return os.path.join(self.root_dir, base_file)

  def full_check(self, content, expected):
    """End-to-end test. That's all that matters."""
    foo_path = self.path('foo')
    foo3_path = self.path('foo3')
    open(foo_path, 'w').write(content)
    open(foo3_path, 'w').write(content)
    for p in self.get_patch():
      chromium_copyright.process(self.checkout, p)
    self.assertEquals(expected, open(foo_path).read())
    self.assertEquals(content, open(foo3_path).read())

  def test_2_times(self):
    content = (
        'Copyright (c) 2010 The Chromium Authors. All rights reserved.\n'
        'Copyright (c) 2010 The Chromium Authors. All rights reserved.\n')
    expected = (
        'Copyright %s The Chromium Authors. All rights reserved.\n'
        'Copyright (c) 2010 The Chromium Authors. All rights reserved.\n') % (
            datetime.date.today().year)
    self.full_check(content, expected)

  def test_5_lines(self):
    content = (
        '0\n'
        '1\n'
        '2\n'
        '3\n'
        'Copyright (c) 2010 The Chromium Authors. All rights reserved.\n')
    expected = (
        '0\n'
        '1\n'
        '2\n'
        '3\n'
        'Copyright %s The Chromium Authors. All rights reserved.\n') % (
            datetime.date.today().year)
    self.full_check(content, expected)

  def test_6_lines(self):
    content = (
        '0\n'
        '1\n'
        '2\n'
        '3\n'
        '4\n'
        'Copyright (c) 2010 The Chromium Authors. All rights reserved.\n')
    expected = content
    self.full_check(content, expected)

  def test_re(self):
    input_base = 'Copyright (c) 2010 The Chromium Authors. All rights reserved.'
    input_no_copyright = ('Copyright 2010 The Chromium Authors. '
                          'All rights reserved.')
    expected_base = ('Copyright %s The Chromium Authors. All rights reserved.' %
        datetime.date.today().year)
    self.full_check(input_base, expected_base)
    self.full_check('a ' + input_base, 'a ' + expected_base)
    self.full_check('// ' + input_base, '// ' + expected_base)
    self.full_check('// ' + input_base + '\n', '// ' + expected_base + '\n')
    self.full_check(input_base + '\n', expected_base + '\n')
    self.full_check(input_no_copyright, expected_base)
    self.full_check('a ' + input_no_copyright, 'a ' + expected_base)
    self.full_check('// ' + input_no_copyright, '// ' + expected_base)
    self.full_check('// ' + input_no_copyright + '\n', '// ' + expected_base +
                    '\n')
    self.full_check(input_no_copyright + '\n', expected_base + '\n')
    ## \r are not supported.
    #self.full_check(
    #    '// Copyright (c) 2010 The Chromium Authors. All rights reserved.\r\n',
    #    '// Copyright %s The Chromium Authors. All rights reserved.\r\n' %
    #        datetime.date.today().year)


if __name__ == '__main__':
  unittest.main()
