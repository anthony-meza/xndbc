Installation
============

Install the current development version from GitHub:

.. code-block:: bash

   pip install git+https://github.com/anthony-meza/xndbc.git@main

For local development, clone the repository and create the development
environment:

.. code-block:: bash

   git clone https://github.com/anthony-meza/xndbc.git
   cd xndbc
   conda env create -f docs/environment.yml
   conda activate xndbc-dev

Run the test suite with:

.. code-block:: bash

   pytest
