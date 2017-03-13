********
pyfispip
********

.. image:: https://travis-ci.org/fopina/pyfispip.svg?branch=master
    :target: https://travis-ci.org/fopina/pyfispip
    :alt: Build Status

.. image:: https://img.shields.io/pypi/v/fispip.svg
    :target: https://pypi.python.org/pypi/fispip
    :alt: PyPI Version

.. image:: https://img.shields.io/pypi/pyversions/fispip.svg
    :target: https://pypi.python.org/pypi/fispip
    :alt: PyPI Python Versions

.. image:: https://coveralls.io/repos/github/fopina/pyfispip/badge.svg?branch=master
    :target: https://coveralls.io/github/fopina/pyfispip?branch=master
    :alt: Coverage Status

Successor to https://github.com/fopina/pygtm


============
Installation
============


Simply use **pip**:

.. code-block:: bash

    $ pip install pyfispip

Or install latest version from github:

.. code-block:: bash

    $ pip install git+https://github.com/fopina/pyfispip/


=====
Usage
=====


Use it in your code (check `examples`_ folder):

.. _examples: examples

.. code-block:: python

    >>> from fispip import PIP
    >>> pip = PIP()
    >>> pip.connect('localhost',61315,'1','XXX')
    >>> pip.executeSQL('SELECT TJD FROM CUVAR')
    (['60960'], ['D'])


Or quickly use the CLI:

.. code-block:: bash

    $ python -m fispip -h
    usage: __main__.py [-h] [-u USER] [-p PWD] [-P PORT] [-S TYPE] [-s]
                       host params [params ...]

    Python FIS MTM/PIP SQL/RPC Interface

    positional arguments:
      host                  Hostname to connect
      params                For RPC: MRPC_ID [MRPC_PARAM1 [MRPC_PARAM...]] For
                            SQL: SQL_STATEMENT

    optional arguments:
      -h, --help            show this help message and exit
      -u USER, --user USER  PIP Username (default: 1)
      -p PWD, --password PWD
                            PIP Password (default: XXX)
      -P PORT, --port PORT  MTM port (default: 61315)
      -S TYPE, --server TYPE
                            PIP server type (default: SCA$IBS)
      -s, --sql             Execute SQL statement (default action is RPC)
    
    $ python -m fispip localhost -s select tjd from cuvar
    60960
