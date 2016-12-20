=====
Usage
=====

- Run the parser, it will clone openstack-manuals repository, training-labs
  repository and parse the files

    .. code-block:: bash

       $ ./tools/runparser.sh


  Make sure to run it from the root of the directory.
- Check the generated scripts (location in the configuration file
  `rst2bash/conf`), copy them to training-labs:
  `labs/osbash/scripts/` folder.

- Check the generated scripts (location in the configuration file), copy them
  to training-labs: `labs/osbash/scripts/` folder. Default configuration
  specifies the output location at `build/scripts/`.
- Run training labs:

    .. code-block:: bash

       $ PROVIDER=kvm ./build/training-labs/labs/st.py -b cluster

- Sit back, relax and see the cluster deploy.

**Note:** This project is in its nascent state, especially the OpenStack
          cluster deployment part may break at many places.
