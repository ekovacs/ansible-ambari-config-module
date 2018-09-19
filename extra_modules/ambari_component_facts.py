#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Documentation section
DOCUMENTATION = '''
---
module: ambari_component_facts
version_added: "1.0"
short_description: Capturing Ambari cluster/component configuration as Ansible facts
description: 
    - Used for capturing the configuration of all components installed on Ambari server into facts. 
    - "Facts gather by this module should be accessed through the vars dict: {{ ambari_component_facts['config_type_name']['config_key'] }}, 
        eg.: {{ ambari_component_facts['zoo.cfg']['syncLimit'] }} to avoid problems with invalid dict keys."
    - "It makes sense to use: 'run_once: true' as well as 'delegate_to' the ambari host 
       and then use the default localhost as the host to speed things up" 
    - To see all the facts gathered, run your playbook with at least one level of verbosity

author: Endre Zoltan Kovacs
options:
  protocol:
    description:
      The protocol for the ambari web server (http / https)
  host:
    description:
      The hostname for the ambari web server.
    default:
      localhost 
  port:
    description:
      The port for the ambari web server
  context_path:
    description:
      In case Ambari has a proxy in front of it, context path is the additional path, which must be prepended to each Ambari call. It should include a prepended slash, but no trailing slash
    default:
      ''
  username:
    description:
      The username for the ambari web server
  password:
    description:
      The name of the cluster in web server
    required: yes
  cluster_name:
    description:
      The name of the cluster in ambari
    required: yes
'''

EXAMPLES = '''
# example:
  - name: Gather facts for components
    run_once: true
    delegate_to: "{{ ambari_host }}"
    ambari_component_facts:
        protocol: http
        port: 8080
        context_path: /ambari
        username: admin
        password: admin
        cluster_name: my_cluster
        timeout_sec: 10
'''

from ansible.module_utils.basic import AnsibleModule
import json
import traceback

try:
    import requests
except ImportError:
    REQUESTS_FOUND = False
else:
    REQUESTS_FOUND = True

try:
    import yaml
except ImportError:
    YAML_FOUND = False
else:
    YAML_FOUND = True



def main():
    argument_spec = dict(
        protocol=dict(type='str', default='http', required=False),
        host=dict(type='str', default='localhost', required=False),
        port=dict(type='int', default=None, required=True),
        context_path=dict(type='str', default='', required=False),
        username=dict(type='str', default=None, required=True),
        password=dict(type='str', default=None, required=True, no_log=True),
        cluster_name=dict(type='str', default=None, required=True),
        timeout_sec=dict(type='int', default=10, required=False),
    )

    module = AnsibleModule(
        argument_spec=argument_spec
    )

    if not REQUESTS_FOUND:
        module.fail_json(
            msg='requests library is required for this module')

    if not YAML_FOUND:
        module.fail_json(
            msg='pyYaml library is required for this module')


    p = module.params

    protocol = p.get('protocol')
    host = p.get('host')
    port = p.get('port')
    context_path = p.get('context_path')
    username = p.get('username')
    password = p.get('password')
    cluster_name = p.get('cluster_name')

    connection_timeout = p.get('timeout_sec')

    gather_facts(module, protocol, host, port, context_path, username, password,
                          cluster_name, connection_timeout)


def gather_facts(module, protocol, host, port, context_path, username, password, cluster_name, connection_timeout):
    ambari_url = '{0}://{1}:{2}{3}'.format(protocol, host, port, context_path)
    try:
        # Get config using the effective tag
        config_types = get_config_types(ambari_url, username, password, cluster_name, connection_timeout)
        ambari_cluster_config_facts = {}
        for config_type in config_types:
            config = get_cluster_config(ambari_url, username, password, cluster_name, config_type, config_types[config_type]['tag'], connection_timeout)
            ambari_cluster_config_facts[config_type] = config['properties']

        module.exit_json(changed=False,
                         results=ambari_cluster_config_facts,
                         ansible_facts={'ambari_component_facts': ambari_cluster_config_facts},
                         msg='Gathered facts for ambari services.')
    except requests.ConnectionError as e:
        module.fail_json(
            msg="Could not connect to Ambari client: " + str(e.message), stacktrace=traceback.format_exc())
    except AssertionError as e:
        module.fail_json(msg=e.message, stacktrace=traceback.format_exc())
    except Exception as e:
        module.fail_json(
            msg="Ambari client exception occurred: " + str(e.message), stacktrace=traceback.format_exc())


def get_cluster_config(ambari_url, user, password, cluster_name, config_type, config_tag, connection_timeout):
    r = get(ambari_url, user, password,
            '/api/v1/clusters/{0}/configurations?type={1}&tag={2}'.format(cluster_name, config_type, config_tag),
            connection_timeout)
    assert_return_code(r, 200)
    config = json.loads(r.content)
    return parse_config(r, config,
                        lambda config: config['items'][0]['properties'] is not None,
                        lambda config: config['items'][0])


def get_config_types(ambari_url, user, password, cluster_name, connection_timeout):
    r = get(ambari_url, user, password,
            '/api/v1/clusters/{0}?fields=Clusters/desired_configs'.format(cluster_name),
            connection_timeout)
    assert_return_code(r, 200)
    config = json.loads(r.content)
    config_types = parse_config(r, config,
                        lambda conf: conf['Clusters']['desired_configs'] is not None,
                        lambda conf: conf['Clusters']['desired_configs'])
    for k in config_types:
        print('key:{0} => {1}'.format(k, config_types[k]))
    return config_types


def assert_return_code(request, expected_code):
    try:
        request.status_code == expected_code
    except AssertionError as e:
        e.message = 'Could not get cluster configuration: ' \
                    'request code {0}, ' \
                    'request message {1}'.format(request.status_code, request.content)
        raise


def parse_config(request, config, assertor, selector):
    try:
        assert assertor(config)
        return selector(config)
    except (KeyError, AssertionError) as e:
        e.message = 'Could not find the right properties key, ' \
                    'request code {0}, ' \
                    'possibly having a wrong tag, ' \
                    'response content is: {1}'.format(request.status_code, request.content)
        raise


def get(ambari_url, user, password, path, connection_timeout):
    headers = {'X-Requested-By': 'ambari'}
    r = requests.get(ambari_url + path, auth=(user, password),
                     headers=headers, timeout=connection_timeout)
    return r


if __name__ == '__main__':
    main()