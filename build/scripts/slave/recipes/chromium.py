# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium',
  'gclient',
  'properties',
]

def GenSteps(api):
  # TODO(iannucci): Make a standard way to specify configuration in the recipe
  #                 inputs. Such a design should be able to accept modified
  #                 config blobs as well (hopefully readably delta-encoded).
  config_vals = {'GIT_MODE': True}
  config_vals.update(
    dict((str(k),v) for k,v in api.properties.iteritems() if k.isupper())
  )
  api.chromium.set_config('chromium', **config_vals)

  yield (
    api.gclient.checkout(),
    api.chromium.runhooks(),
    api.chromium.compile(),
  )


def GenTests(api):
  for plat in ('win', 'mac', 'linux'):
    for bits in (32, 64):
      yield 'basic_%s_%s' % (plat, bits), {
        'mock': {'platform': {'name': plat}},
        'properties': {'TARGET_BITS': bits},
      }
