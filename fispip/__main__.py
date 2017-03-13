import argparse
from . import __description__, __program__
from . import PIP


def build_parser():
    parser = argparse.ArgumentParser(
        prog=__program__,
        description=__description__
    )
    parser.add_argument(
        '-u', '--user',
        dest='user', action='store',
        metavar='USER', default='1',
        help='PIP Username (default: 1)'
    )
    parser.add_argument(
        '-p', '--password',
        dest='password', action='store',
        metavar='PWD', default='XXX',
        help='PIP Password (default: XXX)'
    )
    parser.add_argument(
        '-P', '--port',
        dest='port', action='store',
        metavar='PORT', type=int, default=61315,
        help='MTM port (default: 61315)'
    )
    parser.add_argument(
        '-S', '--server',
        dest='server', action='store',
        metavar='TYPE', default='SCA$IBS',
        help='PIP server type (default: SCA$IBS)'
    )
    parser.add_argument(
        '-s', '--sql',
        dest='sql', action='store_true',
        help='Execute SQL statement (default action is RPC)'
    )
    parser.add_argument(
        'host', metavar='host',
        help='Hostname to connect'
    )
    parser.add_argument(
        'params', nargs='+',
        help='''\
        For RPC: MRPC_ID [MRPC_PARAM1 [MRPC_PARAM...]]
        For SQL: SQL_STATEMENT
        '''
    )

    return parser


def main(args=None):
    parser = build_parser()
    args = parser.parse_args(args)

    pip = PIP(args.server)
    pip.connect(args.host, args.port, args.user, args.password)

    if args.sql:
        rows, _ = pip.executeSQL(' '.join(args.params))
        print('\n'.join(rows))
    else:
        print(pip.executeMRPC(args.params[0], *args.params[1:]))


if __name__ == '__main__':
    main()
