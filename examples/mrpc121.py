#!/usr/bin/env python

"""
PIP MRPC121 Wrapper

MRPC121 is an RPC that allows a PIP developer to download and upload elements
using the servers (instead of shell).

This class is a wrapper for the methods exposed by this RPC.

Implementation done going through crtns/MRPC121.PSL and
mrtns/TBXDQSVR.m (in PIP directory)
"""

# used only to make sure this test loads fispip module inside this project
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), os.pardir))

from fispip import PIP
from io import StringIO
import getpass
import argparse

PY3 = sys.version_info[0] > 2

# PIP/MTM IP and port configuration
###################################
host = '127.0.0.1'
port = 61315
user = '1'
pwd = 'XXX'
###################################


class MRPC121(object):
    def __init__(self, connection=None, mrpc_id='121'):
        self._con = connection
        self._id = mrpc_id

    def _call(self, *args):
        return self._con.executeMRPC(self._id, *args, success_unpack=True)[0]

    def init_obj(self, obj_type, obj_id):
        r = self._call(
            'INITOBJ',
            '', '', '', obj_type, obj_id
        )
        if r[0] == '0':
            # some of the TBX routines split code and message
            # with | (pipe - such as Data)
            # others split with '\r' (such as Procedure)
            # and the default "Invalid Type" error is split with '\r\n'
            # why? Try to workaround it.....
            err = r[2:]
            if err[0] == '\n':
                err = err[1:]
            raise Exception(r[2:])
        return r.split('\r\n')[1:]

    def ret_obj(self, token):
        r = self._call(
            'RETOBJ',
            '', '', '', '', '', token
        )
        has_more = r[0] == '1'
        return has_more, r[1:]

    def init_code(self, code, compilation_token):
        return self._call(
            'INITCODE',
            code, compilation_token
        )

    def check_obj(self, local_file, token):
        r = self._call(
            'CHECKOBJ',
            '', '', local_file, '', '', token
        )
        if r[0] == '0':
            raise Exception(r[3:])

    def save_obj(self, local_file, token, username):
        r = self._call(
            'SAVEOBJ',
            '', '', local_file, '', '', token, username
        )
        if r[0] == '0':
            raise Exception(r[3:])

    def exec_comp(self, local_file, compilation_token):
        r = self._call(
            'EXECCOMP',
            '', compilation_token, local_file
        )
        return r


class MRPC081(object):
    """
    This procedure exists in PIP but it is not registered as an RPC

    Register easily with

    GTM>s ^SCATBL(5,81)="Profile Interface ToolBox|$$^MRPC081|PBS|1|1|1|1|1|1|1|1|1|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0|0"
    GTM>s ^SCATBL(5,81,"SCA")=0

    Or using a .DAT and sending it with MRPC121,
    as in docker_integration_tests.py
    """
    def __init__(self, connection=None, mrpc_id='81'):
        self._con = connection
        self._id = mrpc_id

    def _call(self, *args):
        return self._con.executeMRPC(self._id, *args, success_unpack=True)[0]

    def compile(self, table, elements):
        return self._call(table, elements)


class Wrapper(object):
    OBJ_TYPES = {
        # incomplete mapping based on TBXDQSVR.m
        'DAT': 'Data',
        'PROC': 'Procedure',
        'TBL': 'Table',
        'COL': 'Column'
    }

    def __init__(self, server_type='SCA$IBS'):
        self._pip = PIP(server_type)
        self._rpc = MRPC121(self._pip)
        self._rpc81 = MRPC081(self._pip)

    def connect(self, host, port, user, pwd):
        self._pip.connect(host, port, user, pwd)

    def close(self):
        self._pip.close()

    def guess_type(self, filename):
        name, ext = os.path.splitext(filename)
        if ext:
            ext = self.OBJ_TYPES.get(ext[1:].upper(), '')
        return ext, name

    def get_element_by_name(self, filename, file_obj=None):
        obj_type, obj_id = self.guess_type(filename)
        return self.get_element(obj_type, obj_id, file_obj)

    def get_element(self, obj_type, obj_id, file_obj=None):
        if file_obj is None:
            file_obj = StringIO()
        token, name = self._rpc.init_obj(obj_type, obj_id)

        has_more = True
        while has_more:
            has_more, text = self._rpc.ret_obj(token)
            if PY3:
                file_obj.write(text.encode())
            else:
                file_obj.write(text)
        return file_obj

    def send_element(self, filename, file_obj=None, close_file=True):
        if file_obj is None:
            file_obj = open(filename, 'rb')
            close_file = True

        token = self._send_code(file_obj, close_file)
        local_file = os.path.basename(filename)
        self._rpc.check_obj(local_file, token)
        self._rpc.save_obj(local_file, token, getpass.getuser())

    def test_compile_element(self, filename, file_obj=None, close_file=True):
        if file_obj is None:
            file_obj = open(filename, 'rb')
            close_file = True

        token = self._send_code(file_obj, close_file)
        local_file = os.path.basename(filename)
        return self._rpc.exec_comp(local_file, token)

    def compile_and_link(self, filename):
        ext, name = self.guess_type(filename)
        if ext == 'Procedure':
            table = 'DBTBL25'
        elif ext in ['Table', 'Column']:
            table = 'DBTBL1'
        else:
            raise Exception('Cannot compile', ext, name)
        return self._rpc81.compile(table, name)

    def _send_code(self, file_obj, close_file=True):
        token = ''

        try:
            while True:
                data = file_obj.read(1024)
                if not data:
                    break
                if PY3 and isinstance(data, bytes):
                    enc_data = '|'.join(str(x) for x in data) + '|'
                else:
                    enc_data = '|'.join(str(ord(x)) for x in data) + '|'
                token = self._rpc.init_code(enc_data, token)
            # one last call to make sure code is saved even if it doesn't end
            # in a NEWLINE (condition based on INITCOD1^TBXDQSVR.m)
            # this is also useful in case we're trying to send an empty file
            # in which case, the previous while loop did not initialize
            # the token (required for check_obj and save_obj)
            token = self._rpc.init_code('', token)
        finally:
            if close_file:
                file_obj.close()

        return token


def build_parser():
    parser = argparse.ArgumentParser(description='Use MRPC121')
    parser.add_argument(
        '-s', '--send',
        dest='send', action='store',
        metavar='FILE',
        help='Send element to PIP'
    )
    parser.add_argument(
        '-t', '--test',
        dest='test', action='store',
        metavar='FILE',
        help='Test compile element in PIP'
    )
    parser.add_argument(
        '-c', '--compile',
        dest='comp', action='store',
        metavar='FILE',
        help='Compile (and re-link) element in PIP'
    )
    parser.add_argument(
        '-g', '--get',
        dest='get', action='store',
        metavar='FILE',
        help='Get element from PIP'
    )
    parser.add_argument(
        '-f', '--force',
        dest='force', action='store_true',
        help='Overwrite file if necessary (for --get)'
    )

    return parser


def main(args=None):
    parser = build_parser()
    args = parser.parse_args(args)
    show_help = True

    w = Wrapper()
    w.connect(host, port, user, pwd)

    try:
        if args.get:
            show_help = False
            if os.path.exists(args.get) and not args.force:
                parser.error(
                    'File %s already exists, use -f to overwrite' % args.get
                )
            f = open(args.get, 'wb')
            w.get_element_by_name(os.path.basename(args.get), file_obj=f)
            f.close()

        if args.send:
            show_help = False
            w.send_element(args.send)

        if args.test:
            show_help = False
            print(w.test_compile_element(args.test))

        if args.comp:
            show_help = False
            print(w.compile_and_link(args.comp))
    finally:
        w.close()

    if show_help:
        parser.error('Please specify at least one option')


if __name__ == '__main__':
    main()
