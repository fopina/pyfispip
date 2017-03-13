import time
from . import MTM
from .mysix import _basestring, _range, makestring


SERV_CLASS_SIGNON = '0'
SERV_CLASS_SQL = '5'
SERV_CLASS_MRPC = '3'


class PIP(MTM):
    def __init__(self, server_type='SCA$IBS'):
        super(PIP, self).__init__(server_type)
        self._token = None
        self._msgid = 0
        self.max_rows = 30

    def connect(self, host, port, user, password):
        super(PIP, self).connect(host, port)

        # Sign on (and acquire token)
        '''
        #define srv_prc   0
        #define user_id   1
        #define stn_id    2
        #define user_pwd  3
        #define inst_id   4
        #define fap_ids   5
        #define context   6
        '''

        msg_arr = [
            '1',
            user,
            'nowhere',  # TLO
            password,
            '',
            '',
            '\x15\x025\x06ICODE\x021\x08PREPARE\x023',  # context
        ]

        result = self.exchange_message(
            SERV_CLASS_SIGNON,
            self._pack_lv(msg_arr)
        )

        result_arr = self._check_error(result)
        result_arr = self._unpack_lv(result_arr[1])

        self._token = result_arr[0]

    def executeSQL(self, query, *args):
        cursor_id = 0
        final_sql = ''
        if query[:6].lower() == 'select':
            cursor_id = int(time.time())
            final_sql = 'OPEN CURSOR %d AS %s' % (cursor_id, query)
        else:
            final_sql = query

        sql_modifiers = '/ROWS=%d' % self.max_rows

        # Replace "?" with host variables
        # TODO desperate need of actual parsing and validation
        # TODO INSERT ... VALUES (?,?,?...) are not covered
        if len(args) > 0:
            host_variables = []
            temp_sql = final_sql.replace('=?', '= ?')
            final_sql = ''
            i = temp_sql.find('= ?')
            old_i = 0
            variable_id = 1
            while i > -1:
                variable_str = 'C%d' % variable_id
                final_sql += temp_sql[old_i:i] + '= :' + variable_str
                old_i = i + 3
                try:
                    host_variables.append('%s=\'%s\'' % (
                        variable_str,
                        args[variable_id - 1]
                    ))
                except IndexError:
                    raise Exception('VAL_ERROR', 'More markers than variables')
                variable_id += 1
                i = temp_sql.find('= ?', old_i)

            if variable_id != (len(args) + 1):
                raise Exception('VAL_ERROR', 'More variables than markers')

            sql_modifiers += '/USING=(%s)' % ','.join(host_variables)

        msg_arr = [
            final_sql,  # query
            sql_modifiers,
            '',  # ?
        ]

        result = self.exchange_message(
            SERV_CLASS_SQL,
            self._pack_lv(msg_arr)
        )

        result_arr = self._check_error(result)
        result_arr = self._unpack_lv(result_arr[1])

        # count = result_arr[2]

        result = result_arr[3].split('\r\n')

        types = list(result_arr[5].split('|')[0])

        if cursor_id > 0:
            msg_arr = [
                'CLOSE %d' % cursor_id,  # query
                '',
                '',
            ]
            # ignored
            self.exchange_message(SERV_CLASS_SQL, self._pack_lv(msg_arr))

        return (result, types)

    def executeMRPC(self, mrpc_id, *args, **kwargs):
        version = kwargs.get('version', '1')
        # Some MRPCs will apply V2LV on RETURN variable, others will not
        # if they do, an extra unpack is required...
        # only 3 MRPCs exist in PIPv02, not enough for a default based on
        # "most cases"... default to "not unpack" for now...
        success_unpack = kwargs.get('success_unpack', False)

        params = self._pack_lv(args)
        msg_arr = [
            mrpc_id,
            version,
            params,
            '\x04\x03\x021',  # dunno
        ]

        result = self.exchange_message(
            SERV_CLASS_MRPC,
            self._pack_lv(msg_arr)
        )

        result_arr = self._check_error(result)

        if success_unpack:
            return self._unpack_lv(result_arr[1])
        return result_arr[1]

    def exchange_message(self, service_class, message):
        # Message Header
        '''
        From libsql.h (for reference):
        #define srv_cls   0
        #define token     1
        #define msg_id    2
        #define stf_flg   3
        #define grp_recs  4
        '''

        msg_arr = [
            service_class,
            self._token,
            str(self._msgid),
            '0',
            '',
        ]

        if service_class == SERV_CLASS_SIGNON:
            msg_arr[1] = ''

        msg_arr = [
            self._pack_lv(msg_arr),
            message,
        ]

        self._msgid += 1

        return super(PIP, self).exchange_message(self._pack_lv(msg_arr))

    def _check_error(self, packed_string):
        if packed_string[0] != '0':
            raise Exception('MTM_ERROR', packed_string[1:])

        result_arr = self._unpack_lv(packed_string[1:])
        result_arr = self._unpack_lv(result_arr[1])

        if result_arr[0] != '0':
            result_arr = self._unpack_lv(result_arr[1])
            raise Exception(result_arr[2], result_arr[4])

        return result_arr

    def _unpack_lv(self, packed_string):
        ret_array = []
        i = 0
        while i < len(packed_string):
            l, o = self._calc_size(packed_string, i)
            i += o
            ret_array.append(packed_string[i:i+l])
            i += l
        return ret_array

    def _pack_lv(self, unpacked_array):
        """
        Based on V2LV^MSG
        """
        if isinstance(unpacked_array, _basestring):
            unpacked_array = [unpacked_array]

        message = []

        for s in unpacked_array:
            l = len(s) + 1
            if l > 255:
                larr = []
                while True:
                    larr.append(l % 256)
                    l = int(l / 256)  # truncate py3
                    if l == 0:
                        break
                    larr[0] += 1

                # in case first larr element got bigger than 256
                carry = 0
                for i in _range(len(larr)):
                    larr[i] += carry
                    if larr[i] < 256:
                        carry = 0
                        break
                    larr[i] = larr[i] % 256
                    carry = 1
                if carry:
                    larr.append(1)

                message.extend(['\x00', chr(len(larr))])
                message.extend(map(chr, larr[::-1]))
            else:
                message.append(chr(l))
            message.append(s)

        return ''.join(message)

    def _calc_size(self, message, start_index=0):
        len_attempt = ord(message[start_index])
        offset = 1

        if len_attempt != 0:
            return (len_attempt - 1, offset)

        start_index += 1
        len_len = ord(message[start_index])

        total_len = 0
        start_index += 1
        for byte_ind in _range(len_len):
            total_len *= 256
            total_len += ord(message[start_index + byte_ind])

        offset += 1 + len_len

        return (total_len - len_len, offset)
