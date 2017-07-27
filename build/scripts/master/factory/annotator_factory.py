# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to generate and manage a factory to be passed to a
builder dictionary as the 'factory' member, for each builder in c['builders'].

Specifically creates a basic factory that will execute an arbirary annotator
script.
"""

from master.factory import annotator_commands
from master.factory.build_factory import BuildFactory


class AnnotatorFactory(object):
  """Encapsulates data and methods common to all annotators."""

  def __init__(self):
    self._factory_properties = None

  def BaseFactory(self, recipe, factory_properties=None):
    """The primary input for the factory is the |recipe|, which specifies the
    name of a recipe file to search for. The recipe file will fill in the rest
    of the |factory_properties|. This setup allows for major changes to factory
    properties to occur on slave-side without master restarts.

    NOTE: Please be very discerning with what |factory_properties| you pass to
    this method. Ideally, you will pass none, and that will be sufficient in the
    vast majority of cases. Think very carefully before adding any
    |factory_properties| here, as changing them will require a master restart.
    """
    factory_properties = factory_properties or {}
    factory_properties.update({'recipe': recipe})
    self._factory_properties = factory_properties
    factory = BuildFactory()
    cmd_obj = annotator_commands.AnnotatorCommands(factory)
    cmd_obj.AddAnnotatedScript(factory_properties)
    return factory
