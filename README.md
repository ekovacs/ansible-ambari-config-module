# ansible-ambari-config-module
A module that update Ambari configuration through Ambari API. Please find the actual module file under:

    extra_modules/ambari_cluster_config.py
    extra_modules/ambari_service_control.py
    extra_modules/ambari_component_extend.py

**IMPORTANT** Please note that, the above modules are calling Ambari API, so **ideal location** to run those modules in is on the **ambari server node**. In that case you could just do localhost connection to your ambari server for setup. A example would be:

    hosts: ambari-server
    ambari_service_control:
        host: localhost          ----> this will run the module on the ambari-server and try to request to its 'localhost'

As the ambari_service_control module is calling the stop/start API, if running on multiple nodes, e.g. the `agent` nodes, this will create multiple start/stop requests which will impact on performance and execution sequences.

## Dependencies:

Python
- re
- requests
- time
- json


## How to include this module
1. Create a folder under your ansible playbook root path e.g. `extra_modules`
    
    `mkdir <path-to-ansible-playbook>/extra_modules`

2. Git clone this repository or copy the file across to the folder
   
    `cp ambari_cluster_config.py <path-to-ansible-playbook>/extra_modules`

3. Create an `ansible.cfg` file under your project root and add following line into it:

    `library=./extra_modules`

4. Start using this module

## Module modes:
This module support 3 modes:
- Simple key-value replacement
- Regex based replacement. e.g. `<HistoryDays>30</HistoryDays> (regex: <HistoryDays>\d+</HistoryDays>`) replace with `<HistoryDays>20</HistoryDays>` 
- File based replacement, replace the config content with the file content, this feature could be done by using native `lookup` plugin. e.g.
    
    `value: {{ lookup('template', './files/your_template_file.j2')}}`


## Module Functions:
### ambari_cluster_config module
This module allows you to configure Ambari cluster configurations via Ambari API in an idempotent way. Ambari cluster configurations usually contains few parts:
- config type
- config tag (which is version)

And underneath there's the actual configurations you want to change:
- config properties for specific config type + config tag
- config properties-attributes for config type + config tag

e.g. A typical config API will look like:
`http://<ambari-server>:8080/api/v1/clusters/<cluster-name>/configurations?type=admin-log4j&tag=version1525157305324`

Where `admin-log4j` is the `config type` and `version1525157305324` is the `config tag`. And underneath you will see the actual properties like:

    {
        "href" : "http://master01.dipa-test-2.labs.restest.nbn-aws.local:8080/api/v1/clusters/DIPA/configurations?type=admin-log4j&tag=version1525157305324",
        "items" : [
            {
            "href" : "http://master01.dipa-test-2.labs.restest.nbn-aws.local:8080/api/v1/clusters/DIPA/configurations?type=admin-log4j&tag=version1525157305324",
            "tag" : "version1525157305324",
            "type" : "admin-log4j",
            "version" : 1,
            "Config" : {
                "cluster_name" : "DIPA",
                "stack_id" : "HDF-3.1"
            },
            "properties" : {
                "content" : " ... <content template> ...",
                "ranger_xa_log_maxbackupindex" : "20",
                "ranger_xa_log_maxfilesize" : "256"
            }
            }
        ]
    }

In the above case, we could change the `ranger_xa_log_maxfilesize` from `256` to `512` by using this module like:

    ambari_cluster_config:
        host: localhost
        port: 8080
        username: admin
        password: admin
        cluster_name: my_cluster
        config_type: admin-log4j
        ignore_secret: true
        timeout_sec: 10
        config_map:
          ranger_xa_log_maxfilesize:
            value: 512

Please note that for things like `content` it could be a very large template file in Ambari, what you could do is:

    ambari_cluster_config:
        host: localhost
        port: 8080
        username: admin
        password: admin
        cluster_name: my_cluster
        config_type: admin-log4j
        ignore_secret: true
        timeout_sec: 10
        config_map:
          content:
            value: "{{ lookup('template', './file/content.template.j2') }}"



### ambari_service_control module
Ambari service control module controls the Ambari Services start or stop (installed in Ambari Service language).

Please refer to the `ambari_cluster_sample.yml` file for a better reference.

### ambari_component_extend module
Ambari component extend module currently serve a basic concept of extending **Existing Services**. e.g. Add a new Data Node for HDFS.

Please be aware, since this is targeting existing service:

- it would **NOT** create a non-existing service 
- it would **NOT** add a host to the cluster, it would assume the host does exist already (*open for improvement*)
- it would **NOT** enable the component once it is installed into the host, instead, you should use the *ambari_service_control* module to do that


### Testing
This module have a minimum test using `nosetests`. To run the test, you will need to run like:

    nosetests -v

To get a verbose output of the tests.




