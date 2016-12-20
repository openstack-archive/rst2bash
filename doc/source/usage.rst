=====
Usage
=====

- To run the parser please clone the [openstack-manuals](git://git.openstack.org/openstack/openstack-manuals)
  repository and update the configuration file.
- Additionally, if you wish to deploy OpenStack cluster, also clone the [training-labs](git://git.openstack.org/openstack/training-labs)
  repository.
- Run the parser:

    $ python parser.py

- Check the generated scripts (location in the configuration file), copy them
  to training-labs: labs/osbash/scripts/ folder.
- Run training labs:

    $ PROVIDER=kvm ./st.py -b cluster

- Sit back, relax and see the cluster deploy.

**Note:** This project is in its nascent state, especially the OpenStack
          cluster deployment part may break at many places.
