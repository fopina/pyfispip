#!/usr/bin/env python

import unittest
from mock import patch
from fispip import PIP


class PIPTest(unittest.TestCase):
    def setUp(self):
        self._pip = PIP('SCA$IBS')

    def test_lv(self):
        LONG = 'b' * 255
        x = self._pip._unpack_lv('\x03ab\x04abc')
        self.assertEqual(x, ['ab', 'abc'])
        x = self._pip._unpack_lv('\x02a\x00\x02\x01\x01' + LONG)
        self.assertEqual(x, ['a', LONG])

        self.assertEqual(
            self._pip._pack_lv(['ab', 'abc']),
            '\x03ab\x04abc'
        )
        self.assertEqual(
            self._pip._pack_lv(['a', LONG]),
            '\x02a\x00\x02\x01\x01' + LONG
        )

    def test_connect(self):
        with patch('fispip.MTM.connect'):
            with patch(
                'fispip.MTM.exchange_message',
                # unpacked 3 times!
                return_value='0\x01\x08'
                             '\x020\x05'
                             '\x04abc'
            ) as f_e:
                self._pip.connect('wtv', 1337, 'user', 'pass')

        self.assertEqual(self._pip._token, 'abc')
        f_e.assert_called_once_with(
            # transport header
            '\x09'  # header length
            '\x02' '0'
            '\x01' ''
            '\x02' '0'
            '\x02' '0'
            '\x01' ''
            # signon message
            '\x2d'  # message length
            '\x02' '1'
            '\x05' 'user'
            '\x08' 'nowhere'
            '\x05' 'pass'
            '\x01' ''
            '\x01' ''
            '\x16' '\x15\x025\x06ICODE\x021\x08PREPARE\x023'
        )

    def test_mrpc(self):
        self.test_connect()
        with patch(
            'fispip.MTM.exchange_message',
            # unpacked 3 times!
            return_value='0\x01\x08'
                         '\x020\x05'
                         'leet'
        ) as f_e:
            r = self._pip.executeMRPC('1337', 'param1', 'param2')

        self.assertEqual(r, 'leet')
        f_e.assert_called_once_with(
            # transport header
            '\x0c'  # header length
            '\x02' '3'
            '\x04' 'abc'  # token from test_connect
            '\x02' '1'  # msg_id increased after test_connect
            '\x02' '0'
            '\x01' ''
            # signon message
            '\x1c'  # message length
            '\x05' '1337'
            '\x02' '1'
            '\x0f' '\x07' 'param1' '\x07' 'param2'
            '\x05' '\x04' '\x03' '\x02' '1'
        )

    def test_sql_select(self):
        self.test_connect()

        _out = [
            # whatever val for CLOSE CURSOR
            '0\x01\x0f'
            '\x020\x01',

            # reply for the actual OPEN CURSOR
            '0\x01\x0f'
            '\x020\x0c'
            # SQL array
            '\x01' ''
            '\x01' ''
            '\x02' '1'
            '\x04' 'val'
            '\x01' ''
            '\x02' 'T'
        ]
        _inp = []

        def _fake_exchange(*args):
            _inp.append(args)
            return _out.pop()

        with patch('fispip.MTM.exchange_message', _fake_exchange):
            rows, col_types = self._pip.executeSQL('SELECT col FROM table')

        self.assertEqual(col_types[0], 'T')
        self.assertEqual(rows[0], 'val')

        self.assertRegexpMatches(
            _inp[0][1],
            '\x0c'  # transport header
            '\x02' '5'
            '\x04' 'abc'
            '\x02' '1'
            '\x02' '0'
            '\x01' ''
            '\x3b'  # SQL message
            '\x30' 'OPEN CURSOR \d{10} AS SELECT col FROM table'
            '\x09' '/ROWS=30'
            '\x01' ''
        )

        self.assertRegexpMatches(
            _inp[1][1],
            '\x0c'  # transport header
            '\x02' '5'
            '\x04' 'abc'
            '\x02' '2'
            '\x02' '0'
            '\x01' ''
            '\x14'  # SQL message
            '\x11' 'CLOSE \d{10}'
            '\x01' ''
            '\x01' ''
        )

if __name__ == '__main__':
    unittest.main()
