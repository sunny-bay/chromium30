# coding=utf8
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Defines base classes for pending change verification classes."""

import model


# Verifier state in priority level.
# SUCCEEDED : This verifier is fine to commit this patch.
# PROCESSING: No decision was made yet. The verifier runs asynchronously.
# FAILED    : Verification failed, this patch must not be committed.
# IGNORED   : This patch must be ignored and no comment added to the code
#             review.
SUCCEEDED, PROCESSING, FAILED, IGNORED = range(4)
VALID_STATES = set((SUCCEEDED, PROCESSING, FAILED, IGNORED))


class DiscardPending(Exception):
  """Exception to be raised when a pending item should be discarded."""

  def __init__(self, pending, status):
    super(DiscardPending, self).__init__(status)
    self.pending = pending
    self.status = status


class Verified(model.PersistentMixIn):
  """A set of verifications that are for a specific patch."""
  verifications = dict

  def pending_name(self):
    raise NotImplementedError()

  @model.immutable
  def get_state(self):
    """Returns the combined state of all the verifiers for this item.

    Use priority with the states: IGNORED > FAILED > PROCESSING > SUCCEEDED.
    """
    # If there's an error message, it failed.
    if self.error_message():
      return FAILED
    if not self.verifications:
      return PROCESSING
    states = set(v.get_state() for v in self.verifications.itervalues())
    assert states.issubset(VALID_STATES)
    return max(states)

  @model.immutable
  def postpone(self):
    """This item shouldn't be committed right now.

    Call repeatedly until it returns False. This is a potentially slow call so
    only call it when get_state() returns SUCEEDED.
    """
    return any(v.postpone() for v in self.verifications.itervalues())

  @model.immutable
  def error_message(self):
    """Returns all the error messages concatenated if any."""
    out = (i.error_message for i in self.verifications.itervalues())
    return '\n\n'.join(filter(None, out))

  def apply_patch(self, context, prepare):
    """Applies a patch from the codereview tool to the checkout."""
    raise NotImplementedError()

  @model.immutable
  def why_not(self):
    """Returns a string of all the reasons the current patch can't be
       commited"""
    why_nots = dict((k, v.why_not())
                    for k, v in self.verifications.iteritems())
    return '\n'.join('%s: %s' % (k, v) for k, v in why_nots.iteritems() if v)


class IVerifierStatus(model.PersistentMixIn):
  """Interface for objects in Verified.verifications dictionary."""
  error_message = (None, unicode)

  def get_state(self):
    """See Verified.get_state()."""
    raise NotImplementedError()

  @model.immutable
  def postpone(self):  # pylint: disable=R0201
    """See Verified.postpone()."""
    return False

  def why_not(self):
    """Returns a message why the commit cannot be committed yet.

    E.g. why get_state() == PROCESSING.
    """
    raise NotImplementedError()


class SimpleStatus(IVerifierStatus):
  """Base class to be used for simple true/false and why not verifiers."""
  state = int

  def __init__(self, state=PROCESSING, **kwargs):
    super(SimpleStatus, self).__init__(state=state, **kwargs)

  @model.immutable
  def get_state(self):
    return self.state

  @model.immutable
  def why_not(self):
    if self.state == PROCESSING:
      return 'Processing'
    return


class Verifier(object):
  """This class and its subclasses are *not* serialized."""
  name = None

  def __init__(self):
    assert self.name is not None

  def verify(self, pending):
    """Verifies a pending change.

    Called with os.getcwd() == checkout.project_path.
    """
    raise NotImplementedError()

  def update_status(self, queue):
    """Updates the status of all pending changes, for asynchronous checks.

    It is not necessarily called from inside checkout.project_path.
    """
    raise NotImplementedError()

  @model.immutable
  def loop(self, queue, gen_obj, pending_only):
    """Loops in a pending queue and returns the verified item corresponding to
    the Verifier.
    """
    for pending in queue:
      if self.name not in pending.verifications:
        pending.verifications[self.name] = gen_obj()
      if (not pending_only or
          pending.verifications[self.name].get_state() == PROCESSING):
        yield pending, pending.verifications[self.name]


class VerifierCheckout(Verifier):  # pylint: disable=W0223
  """A verifier that needs a rietveld and checkout objects.

  When verify() is called, it is guaranteed that the patch is applied on the
  checkout.
  """
  def __init__(self, context_obj):
    super(VerifierCheckout, self).__init__()
    self.context = context_obj

  @model.immutable
  def send_status(self, pending, data):
    """Sends an update to the CQ dashboard.

    self.context.status is usually an instance of AsyncPush so the HTTP POST is
    done in a background thread.
    """
    self.context.status.send(
        pending, {'verification': self.name, 'payload': data})
