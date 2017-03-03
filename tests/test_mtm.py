#!/usr/bin/env python

import unittest
import os
from mock import patch
from fispip import MTM


class MTMTest(unittest.TestCase):
    def setUp(self):
        self._mtm = MTM()

    def test_connect(self):
        with patch('socket.socket.connect') as f:
            self._mtm.connect('wtv', 1337)
            f.assert_called_once_with(('wtv', 1337))

    def test_exchange_message(self):
        _recv_queue = [
            '123',
            '\x00\x05'
        ]

        def _fake_recv(s, l):
            return _recv_queue.pop()

        with patch('socket.socket.send') as f_s:
            with patch('socket.socket.recv', _fake_recv):
                r = self._mtm.exchange_message('echo 123')

        f_s.assert_called_once_with('\x00\x0Aecho 123')
        self.assertEqual(r, '123')

    def test_close(self):
        with patch('socket.socket.close') as f:
            self._mtm.close()
        f.assert_called_once_with()

    def test_endianess(self):
        with patch('socket.socket.send') as f_s:
            # big-endian
            self._mtm.set_endianess('>')
            self._mtm.send_message('hello')
            f_s.assert_called_once_with('\00\x07hello')
            f_s.reset_mock()

            # little-endian
            self._mtm.set_endianess('<')
            self._mtm.send_message('hello')
            f_s.assert_called_once_with('\07\x00hello')
            f_s.reset_mock()

            # fallback: network endian (= big-endian)
            self._mtm.set_endianess('invalid')
            self._mtm.send_message('hello')
            f_s.assert_called_once_with('\00\x07hello')

    def test_server_type(self):
        self._mtm = MTM('CUSTOM$SERVER')
        with patch('socket.socket.send') as f_s:
            self._mtm.send_message('hello')
            f_s.assert_called_once_with(
                '\x00\x15CUSTOM$SERVER\x1c'
                'hello'
            )

    def test_read_errors(self):
        with patch('socket.socket.recv', return_value=''):
            r = self._mtm.read_message()
        self.assertIsNone(r)


if __name__ == '__main__':
    unittest.main()
