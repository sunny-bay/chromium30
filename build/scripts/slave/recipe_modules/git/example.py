# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'git',
  'path',
]


def GenSteps(api):
  url = 'https://chromium.googlesource.com/chromium/src.git'

  # You can use api.git.checkout to perform all the steps of a safe checkout.
  yield api.git.checkout(url, recursive=True)

  # If you need to run more arbitrary git commands, you can use api.git.command,
  # which behaves like api.step(), but automatically sets the name of the step.
  yield api.git.command('status', cwd=api.path.checkout())


def GenTests(_api):
  yield 'basic', {}
