#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import json
import logging
import os
import socket
import sys
import time
from urlparse import urljoin, urlparse
import uuid

from buildbot import BuildExitCode
from config import config
# IF USING JENKINS UNCOMMENT BELOW LINES
#from jenkins import JenkinsDefaultValueAction


here = os.path.dirname(os.path.abspath(__file__))

RESULTSET_FRAGMENT = 'api/project/{repository}/resultset/?revision={revision}'
JOB_FRAGMENT = '/#/jobs?repo={repository}&revision={revision}'

BUILD_STATES = ['running', 'completed']

class Submission(object):
    """Class for submitting reports to Treeherder."""

    def __init__(self, repository, revision, settings,
                 treeherder_url=None, treeherder_client_id=None, treeherder_secret=None):
        """Creates new instance of the submission class.
        :param repository: Name of the repository the build has been built from.
        :param revision: Changeset of the repository the build has been built from.
        :param settings: Settings for the Treeherder job as retrieved from the config file.
        :param treeherder_url: URL of the Treeherder instance.
        :param treeherder_client_id: The client ID necessary for the Hawk authentication.
        :param treeherder_secret: The secret key necessary for the Hawk authentication.
        """
        self.repository = repository
        self.revision = revision
        self.settings = settings

        self._job_details = []

        self.url = treeherder_url
        self.client_id = treeherder_client_id
        self.secret = treeherder_secret

        if not self.client_id or not self.secret:
            raise ValueError('The client_id and secret for Treeherder must be set.')
        if not self.url:
            raise ValueError('The Treeherder URL must be set.')

    def _get_treeherder_platform(self):
        """Returns the Treeherder equivalent platform identifier of the current platform."""
        platform = None

        info = mozinfo.info

        if info['os'] == 'linux':
            platform = ('linux', '%s%s' % (info['os'], info['bits']), '%s' % info['processor'])

        elif info['os'] == 'mac':
            platform = ('mac', 'osx-%s' % info['os_version'].replace('.', '-'), info['processor'])

        elif info['os'] == 'win':
            versions = {'5.1': 'xp', '6.1': '7', '6.2': '8'}
            bits = ('-%s' % info['bits']) if info['os_version'] != '5.1' else ''
            platform = ('win', 'windows%s%s' % (versions[info['os_version']], '%s' % bits),
                        info['processor'],
                        )

        return platform

    def create_job(self, data=None, **kwargs):
        data = data or {}

        job = TreeherderJob(data=data)

        # If no data is available we have to set all properties
        if not data:
            job.add_job_guid(str(uuid.uuid4()))
            job.add_tier(self.settings['treeherder']['tier'])

            job.add_product_name('firefox')

            job.add_project(self.repository)
            job.add_revision_hash(self.retrieve_revision_hash())

            # Add platform and build information
            job.add_machine(socket.getfqdn())
            platform = self._get_treeherder_platform()
            job.add_machine_info(*platform)
            job.add_build_info(*platform)

            # TODO debug or others?
            job.add_option_collection({'opt': True})

            # TODO: Add e10s group once we run those tests
            job.add_group_name(self.settings['treeherder']['group_name'].format(**kwargs))
            job.add_group_symbol(self.settings['treeherder']['group_symbol'].format(**kwargs))

            # Bug 1174973 - for now we need unique job names even in different groups
            job.add_job_name(self.settings['treeherder']['job_name'].format(**kwargs))
            job.add_job_symbol(self.settings['treeherder']['job_symbol'].format(**kwargs))

            job.add_start_timestamp(int(time.time()))
 
            # Bug 1175559 - Workaround for HTTP Error
            job.add_end_timestamp(0)
            # Below line is optional. We can choose not to pass any logs.
            job.add_log_reference( 'buildbot_text', self.settings['treeherder']['log_reference'])

        return job

    def retrieve_revision_hash(self):
        if not self.url:
            raise ValueError('URL for Treeherder is missing.')

        lookup_url = urljoin(self.url,
                             RESULTSET_FRAGMENT.format(repository=self.repository,
                                                       revision=self.revision))
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'mozmill-ci',
        }

        # self.logger.debug('Getting revision hash from: %s' % lookup_url)
        response = requests.get(lookup_url, headers=headers)
        response.raise_for_status()

        if not response.json():
            raise ValueError('Unable to determine revision hash for {}. '
                             'Perhaps it has not been ingested by '
                             'Treeherder?'.format(self.revision))

        #print "Server response\n" + json.dumps(response.json())+"\n"
        return response.json()['results'][0]['revision_hash']

    def submit(self, job):
        job.add_submit_timestamp(int(time.time()))

        # We can only submit job info once, so it has to be done in completed
        if self._job_details:
            job.add_artifact('Job Info', 'json', {'job_details': self._job_details})

        job_collection = TreeherderJobCollection()
        job_collection.add(job)

        print('Sent results to Treeherder: {}'.format(job_collection.to_json()))
        print("\n")
        url = urlparse(self.url)
        client = TreeherderClient(protocol=url.scheme, host=url.hostname,
                                  client_id=self.client_id, secret=self.secret)
        print "repository "+self.repository+" url.hostname "+url.hostname+" self.client.id "+self.client_id+" self.secret "+self.secret
        client.post_collection(self.repository, job_collection)

        print('Results are available to view at: {}'.format(
            urljoin(self.url,
                    JOB_FRAGMENT.format(repository=self.repository, revision=self.revision))))

    def submit_running_job(self, job):
        job.add_state('running')
        self.submit(job)

    def submit_completed_job(self, job, retval):

        job.add_state('completed')
        job.add_result(BuildExitCode[retval])
        job.add_end_timestamp(int(time.time()))

        # If the Jenkins BUILD_URL environment variable is present add it as artifact
        # Bug 1218537: Submitting multipe Job Info objects fail right now. So we have to
        # submit the Build URL via the completed job.
        if os.environ.get('BUILD_URL'):
            self._job_details.append({
                'title': 'Inspect Jenkins Build (VPN required)',
                'value': os.environ['BUILD_URL'],
                'content_type': 'link',
                'url': os.environ['BUILD_URL']
            })

        self.submit(job)

def parse_args():
    parser = argparse.ArgumentParser()
    # IF USING JENKINS COMMENT BELOW LINES AND UNCOMMENT THE COMMENTED LINES
    parser.add_argument('--locale',
                        default='DEMO',
                        help='The locale of the build. Default: %(default)s.')
    #parser.add_argument('--locale',
    #                    action=JenkinsDefaultValueAction,
    #                    default='en-US',
    #                    help='The locale of the build. Default: %(default)s.')
    parser.add_argument('--test-type',
                        choices=config['test_types'].keys(),
                        required=True,
                        help='The type of test for building the job name and symbol.')
    parser.add_argument('--repository',
                        required=True,
                        help='The repository name the build was created from.')
    parser.add_argument('--revision',
                        required=True,
                        help='The revision of the build.')
    parser.add_argument('--build-state',
                        choices=BUILD_STATES,
                        required=True,
                        help='The state of the build')
    parser.add_argument('--test-failure',
                        help='(Bool) Set to 1 if the test failed to run on Jenkins (busted).')
    parser.add_argument('venv_path',
                        help='Path to the virtual environment to use.')

    treeherder_group = parser.add_argument_group('treeherder', 'Arguments for Treeherder')
    treeherder_group.add_argument('--treeherder-url',
                                  default=os.environ.get('TREEHERDER_URL'),
                                  help='URL to the Treeherder server.')
    treeherder_group.add_argument('--treeherder-client-id',
                                  default=os.environ.get('TREEHERDER_CLIENT_ID'),
                                  help='Client ID for submission to Treeherder.')
    treeherder_group.add_argument('--treeherder-secret',
                                  default=os.environ.get('TREEHERDER_SECRET'),
                                  help='Secret for submission to Treeherder.')
    #print json.dumps(vars(parser.parse_args()))
    return vars(parser.parse_args())

if __name__ == '__main__':
    print('Demo Treeherder Submission Script Version 1.0\n')
    kwargs = parse_args()

    # Activate the environment, and create if necessary
    #import environment
    #if environment.exists(kwargs['venv_path']):
    #    environment.activate(kwargs['venv_path'])
    #else:
    #    environment.create(kwargs['venv_path'], os.path.join(here, 'requirements.txt'))

    # Can only be imported after the environment has been activated
    import mozinfo
    import requests

    from thclient import TreeherderClient, TreeherderJob, TreeherderJobCollection

    settings = config['test_types'][kwargs['test_type']]

    #print "\nArgs"+json.dumps(kwargs)+"\n"
    th = Submission(kwargs['repository'], kwargs['revision'][:12],
                    treeherder_url=kwargs['treeherder_url'],
                    treeherder_client_id=kwargs['treeherder_client_id'],
                    treeherder_secret=kwargs['treeherder_secret'],
                    settings=settings)

    # State 'running'
    if kwargs['build_state'] == BUILD_STATES[0]:
        job = th.create_job(**kwargs)
        with file('job.json', 'w') as f:
            f.write(json.dumps(job.data))
        th.submit_running_job(job)

    # State 'completed'
    elif kwargs['build_state'] == BUILD_STATES[1]:
        # Read in job guid to update the report
        try:
            with file('job.json', 'r') as f:
                job_data = json.loads(f.read())
        except:
            job_data = {}

        job = th.create_job(job_data, **kwargs)
        retval = 0
        try:
            with file('retval.txt', 'r') as f:
                retval = int(f.read())
                print "\nRead retval and found retval=>"+retval
        except:
            print "Error: Could not find retval.txt" 
        th.submit_completed_job(job, retval)
