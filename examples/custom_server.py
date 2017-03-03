#!/usr/bin/env python

"""
MTM Custom Server example

This is a simple example on how to use MTM class to directly interact
with a custom server.

Use the following routine as server entry point:

ZFPSV(IM)
        I $E(IM,1,5)="echo " quit $E(IM,6,99999)
        Q ""
"""

# used only to make sure this test loads fispip module inside this project
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))

from fispip import MTM

# PIP/MTM IP and port configuration
###################################
host = '127.0.0.1'
port = 61315
msg = "echo 123"
###################################


def main():
    mtm = MTM()
    mtm.connect(host, port)
    assert mtm.exchange_message(msg) == "123"
    mtm.close()

if __name__ == '__main__':
    main()
