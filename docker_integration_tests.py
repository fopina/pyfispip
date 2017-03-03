#!/usr/bin/env python

import docker
import time
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'examples'))

import pip_sql_rpc


def main():
    client = docker.from_env()
    c = client.containers.run(
        'fopina/fis-pip',
        privileged=True, detach=True,
        ports={'61315': '61315'}
    )
    # TODO check log instead of sleep()
    time.sleep(10)
    try:
        pip_sql_rpc.main()
    finally:
        c.remove(force=True)

    # TODO run custom_server example as well (needs setup of the custom server)

if __name__ == '__main__':
    main()
