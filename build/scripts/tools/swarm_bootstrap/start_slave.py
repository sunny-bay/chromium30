#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This file is needed by Google Cloud Compute Engine slaves."""

import slave_machine  # pylint: disable-msg=F0401


if __name__ == '__main__':
  slave_machine.Restart()
