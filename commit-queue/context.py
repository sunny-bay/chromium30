# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


class Context(object):
  """Class to hold context about a the current code review and checkout."""
  def __init__(self, rietveld, checkout, status, server_hooks_missing=False):
    """
    Args:
      rietveld: Instance of rietveld.Rietveld.
      checkout: Instance of checkout.SvnCheckout
      status: Instance of async_push.AsyncPush.
      server_hooks_missing: True if the project's SVN repository does not have
                            server-side hooks configured.
    """
    self.rietveld = rietveld
    self.checkout = checkout
    self.status = status
    self.server_hooks_missing = server_hooks_missing
