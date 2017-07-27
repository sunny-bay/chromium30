# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime
import os
import re

import errors


def process(checkout, patch):
  """Enforces current year in Chromium copyright."""
  pattern = (
    r'^(.*)Copyright (?:\(c\) )?\d{4}(|-\d{4}) The Chromium Authors. '
    r'All rights reserved.$')
  replacement = (
      r'\1Copyright %s The Chromium Authors. All rights reserved.' %
        datetime.date.today().year)

  if not patch.is_new or patch.is_binary:
    return
  filepath = os.path.join(checkout.project_path, patch.filename)
  try:
    with open(filepath, 'rb') as f:
      lines = f.read().splitlines(True)
  except IOError, e:
    errors.send_stack(e)
    lines = None
  if not lines:
    return
  modified = False
  for i in xrange(min(5, len(lines))):
    old_line = lines[i]
    lines[i] = re.sub(pattern, replacement, lines[i])
    if old_line != lines[i]:
      modified = True
      break
  if modified:
    with open(filepath, 'wb') as f:
      f.write(''.join(lines))
