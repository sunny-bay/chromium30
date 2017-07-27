# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'gclient',
  'git',
  'path',
  'properties',
  'rietveld',
  'step',
]

def GenSteps(api):
  root = api.rietveld.calculate_issue_root()

  # FIXME: Remove the blink_bare repository type.
  # TODO(iannucci): Pass the build repo info directly via properties
  repo_name = api.properties['repo_name']
  if repo_name == 'blink_bare':
    root = ''

  api.gclient.set_config(repo_name)
  yield api.gclient.checkout()

  spec = api.gclient.c
  if spec.solutions[0].url.endswith('.git'):
    yield (
        api.git.command('config', 'user.email', 'commit-bot@chromium.org'),
        api.git.command('config', 'user.name', 'The Commit Bot'),
        api.git.command('clean', '-xfq')
    )

  yield api.rietveld.apply_issue(root)

  yield api.step('presubmit', [
    api.path.depot_tools('presubmit_support.py'),
    '--root', api.path.checkout(root),
    '--commit',
    '--verbose', '--verbose',
    '--issue', api.properties['issue'],
    '--patchset', api.properties['patchset'],
    '--skip_canned', 'CheckRietveldTryJobExecution',
    '--skip_canned', 'CheckTreeIsOpen',
    '--skip_canned', 'CheckBuildbotPendingBuilds',
    '--rietveld_url', api.properties['rietveld'],
    '--rietveld_email', '',  # activates anonymous mode
    '--rietveld_fetch'])


def GenTests(api):
  for repo_name in ['blink', 'blink_bare', 'tools_build', 'chromium']:
    if 'blink' in repo_name:
      props = api.properties_tryserver(
        root='src/third_party/WebKit'
      )
    else:
      props = api.properties_tryserver()

    props['repo_name'] = repo_name
    yield repo_name, {
      'properties': props
    }
