===============================
rst2bash
===============================

Parser to convert RST into Bash. Allows generating Bash scripts to deploy
OpenStack from install guides.

Generating Bash code from install guides RST code snippets allows us to
automatically test and validate the installation guides in the CI. This
cluster should make it extremely easy for contributors to test their
changes and additionally allows us to maintain higher quality installation
instructions.

These are the major goals which are accomplished by the parser:

- To allow automated testing of installation guides.
- To automate generation of installation scripts for training-labs from
  install guides.
- To write a generic parser which should be usable for parsing code block
  snippets from any sphinx documentation.
- To test and validate OpenStack in the CI using training-labs and
  installation guides.
- To make OpenStack awesome.


Training-Labs
-------------

[Training-labs](https://git.openstack.org/openstack/training-labs) is part
of OpeNStack Documentation team and provides an unique tool to deploy core
OpenStack services. Training labs closely follows installation guides for
the OpenStack deployment steps.


Installation Guides (OpenStack Installation Tutorial)
-----------------------------------------------------

[Installation guides](https://docs.openstack.org) provides step by step
instructions to deploy OpenStack on a multi-node cluster.


More Details
------------

- Most of the parser logic is running from parser.py.
- More scripts (glue-code) should allow setting up the openstack-manuals
  and training-labs repository.
- The generated output (parsed files) should then be triggered via.
  training-labs to deploy the OpenStack cluster.
- Additionally, this project should showcase and allow the workflow in the
  OpenStack CI for installation guides and cross-project installation-guides.


Usage
-----

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


Roadmap
-------

- Create glue-code scripts to automate setting up of various repositories
  required to easily carry the workflow.
- Setup the non-voting jobs to deploy the cluster. This cluster should be
  a two node KVM/VirtualBox cluster which runs in the OpenStack CI.
- Update the Bash templates (Jinja templates) to allow nicer Bash scripts
  which are following training-labs conventions and standards.
- Stabilize the CI and add the CI template in openstack-infra.
- Add this job for installation guides and other related guides for
  openstack-manuals.
- Add this job for training-labs to automatically generate Bash scripts.
  Figure out a mechanism which does not rewrite from scratch but rather
  nicely and carefully updates existing Bash scripts from training-labs.


Misc
----

* Free software: Apache license
* Documentation: http://docs.openstack.org/developer/rst2bash
* Source: http://git.openstack.org/cgit/openstack/rst2bash
* Bugs: http://bugs.launchpad.net/rst2bash
