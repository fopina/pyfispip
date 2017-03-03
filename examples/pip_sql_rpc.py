#!/usr/bin/env python

"""
PIP SQL and MRPC Example

This is a simple example on how to use PIP class to execute SQL
statements and call MRPC in a PIP server running the default PBSSRVers.
"""

# used only to make sure this test loads fispip module inside this project
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))

from fispip import PIP


# PIP/MTM IP and port configuration
###################################
host = '127.0.0.1'
port = 61315
user = '1'
pwd = 'XXX'
server_type = 'SCA$IBS'
###################################


def test_sql():
    pip = PIP(server_type)
    pip.connect(host, port, user, pwd)

    # backup current ICITY
    rows, col_types = pip.executeSQL('SELECT ICITY FROM CUVAR')
    assert col_types[0] == 'T'
    old_city = rows[0]

    # update ICITY to 'TEST'
    pip.executeSQL('UPDATE CUVAR SET ICITY = ?', 'TEST')

    # verify it was updated
    rows, col_types = pip.executeSQL('SELECT ICITY FROM CUVAR')
    assert col_types[0] == 'T'
    assert rows[0] == 'TEST'

    # set it back to old value
    pip.executeSQL('UPDATE CUVAR SET ICITY = ?', old_city)
    rows, col_types = pip.executeSQL('SELECT ICITY FROM CUVAR')
    assert col_types[0] == 'T'
    assert rows[0] == old_city
    pip.close()


def test_mrpc():
    pip = PIP(server_type)
    pip.connect(host, port, user, pwd)

    # test MRPCs (only 121 and 155 available in core PIP)
    # using 155 for assertion, returns an SQL query response formatted in HTML
    assert pip.executeMRPC(
        '155',
        'SELECT TJD FROM CUVAR'
    ).find('<th title="CUVAR.TJD date">System<br>Processing<br>Date</th>') > -1

    pip.close()


def main():
    test_sql()
    test_mrpc()

if __name__ == '__main__':
    main()
