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

`Training-labs <https://git.openstack.org/openstack/training-labs>`_ is part
of OpenStack Documentation team and provides an unique tool to deploy core
OpenStack services. Training labs closely follows installation guides for
the OpenStack deployment steps.


Installation Guides (OpenStack Installation Tutorial)
-----------------------------------------------------

`Installation guides <https://docs.openstack.org>`_ provides step by step
instructions to deploy OpenStack on a multi-node cluster.


More Details
------------

- Most of the parser logic is running from parser.py.
- More scripts (glue-code) should allow setting up the openstack-manuals
  and training-labs repository.
- The generated output (parsed files) should then be triggered via.
  training-labs to deploy the OpenStack cluster.
- Additionally, this project should showcase and allow the work-flow in the
  OpenStack CI for installation guides and cross-project installation-guides.


Roadmap
-------

- Create glue-code scripts to automate setting up of various repositories
  required to easily carry the work-flow.
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
