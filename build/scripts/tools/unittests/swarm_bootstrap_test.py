#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

SWARM_BOOTSTRAP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'swarm_bootstrap')
sys.path.insert(0, SWARM_BOOTSTRAP_DIR)

import swarm_bootstrap


class SwarmBootTest(unittest.TestCase):
  def test_dimensions(self):
    actual = swarm_bootstrap.GetChromiumDimensions('s33-c4', 'darwin')
    expected = {'dimensions': {'os': 'Mac', 'vlan': 'm4'}, 'tag': 's33-c4'}
    self.assertEqual(expected, actual)

    actual = swarm_bootstrap.GetChromiumDimensions('vm1-m4', 'linux2')
    expected = {'dimensions': {'os': 'Linux', 'vlan': 'm4'}, 'tag': 'vm1-m4'}
    self.assertEqual(expected, actual)

    actual = swarm_bootstrap.GetChromiumDimensions('vm1-m1', 'win32')
    expected = {'dimensions': {'os': 'Windows', 'vlan': 'm1'}, 'tag': 'vm1-m1'}
    self.assertEqual(expected, actual)


if __name__ == '__main__':
  unittest.TestCase.maxDiff = None
  unittest.main()
