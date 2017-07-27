#!/usr/bin/python -u
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This allows easy execution of a recipe (scripts/slave/recipes, etc.)
without buildbot.

This is currently useful for testing recipes locally while developing them.

Example:
  ./run_recipe.py run_presubmit repo_name=tools_build -- issue=12345 \
      patchset=1 description="this is a cool description" \
      blamelist=['dude@chromium.org'] \
      rietveld=https://chromiumcodereview.appspot.com

  This would execute the run_presubmit recipe, passing
  {'repo_name':'tools_build'} as factory_properties, and {'issue':'12345' ...}
  as build_properties.

See scripts/slave/annotated_run.py for more information about recipes.
"""

import json
import os
import subprocess
import sys

SCRIPT_PATH = os.path.abspath(os.path.dirname(__file__))
ROOT_PATH = os.path.abspath(os.path.join(SCRIPT_PATH, os.pardir, os.pardir))
SLAVE_DIR = os.path.join(ROOT_PATH, 'slave', 'fake_slave', 'build')

RUNIT = os.path.join(SCRIPT_PATH, 'runit.py')
ANNOTATED_RUN = os.path.join(ROOT_PATH, 'scripts', 'slave', 'annotated_run.py')

def usage(msg=None):
  """Print help and exit."""
  if msg:
    print 'Error:', msg

  print (
"""
usage: %s <recipe_name> [<factory_property=value>*] [-- <build_property=value>*]
""" % os.path.basename(sys.argv[0]))
  sys.exit(bool(msg))


def type_scrub_factory_properties(fp):
  """Specially 'eval' certain keys in factory_properties."""
  fp['tests'] = eval(fp.get('tests', '[]'))
  return fp


def type_scrub_build_properties(bp):
  """Specially 'eval' certain keys in build_properties."""
  bp['use_mirror'] = eval(bp.get('use_mirror', 'True'))
  bp['blamelist'] = eval(bp.get('blamelist', '[]'))
  if 'TARGET_BITS' in bp:
    bp['TARGET_BITS'] = eval(bp['TARGET_BITS'])
  return bp


def parse_args(argv):
  """Parses the commandline arguments and returns type-scrubbed
  build_properties and factory_properties.

  (See the type_scrub_*_properties functions)"""
  if len(argv) <= 1:
    usage('Must specify a recipe.')
  bad_parms = [x for x in argv[2:] if ('=' not in x and x != '--')]
  if bad_parms:
    usage('Got bad arguments %s' % bad_parms)

  recipe = argv[1]

  separator = argv.index('--') if '--' in argv else len(argv)+1
  fp = dict(x.split('=', 1) for x in argv[2:separator])
  fp['recipe'] = recipe

  bp = {}
  if separator > 0:
    bp = dict(x.split('=', 1) for x in argv[separator+1:])

  return (type_scrub_factory_properties(fp),
          type_scrub_build_properties(bp))


def main(argv):
  fp, bp = parse_args(argv)

  if not os.path.exists(SLAVE_DIR):
    os.makedirs(SLAVE_DIR)

  env = os.environ.copy()
  env['RUN_SLAVE_UPDATED_SCRIPTS'] = '1'
  env['PYTHONUNBUFFERED'] = '1'
  return subprocess.call(
      ['python', '-u', RUNIT, 'python', '-u', ANNOTATED_RUN,
       '--keep-stdin',  # so that pdb works for local execution
       '--factory-properties', json.dumps(fp),
       '--build-properties',   json.dumps(bp)],
      cwd=SLAVE_DIR,
      env=env)


if __name__ == '__main__':
  sys.exit(main(sys.argv))
