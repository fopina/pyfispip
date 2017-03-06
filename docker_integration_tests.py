#!/usr/bin/env python

import docker
import time
import unittest
import tarfile
from StringIO import StringIO

from examples import pip_sql_rpc, custom_server, mrpc121


class IntegrationMixin():
    @classmethod
    def customDocker(cls, tar):
        # override this method to add more files to tar
        # return string with commands to be added to entrypoint
        # script. Return empty string if no commands are to be added
        return ''

    @classmethod
    def setUpClass(cls):
        """
        Change pipstart script to disable the SLEEP command
        and only start 1 server to reduce setUpClass time...
        """
        client = docker.from_env()
        c = client.containers.create(
            'fopina/fis-pip',
            privileged=True, detach=True,
            ports={'61315': None},
            command='/entrypoint2.sh'
        )
        tar_stream = StringIO()
        tar = tarfile.open(fileobj=tar_stream, mode='w')

        extra = cls.customDocker(tar)

        file_data = '''\
#!/bin/bash

sed -i '/^sleep/d' /home/pip/pip_V02/pipstart
sed -i 's/",2)$/",1)/g' home/pip/pip_V02/pipstart
%s
/entrypoint.sh
''' % extra
        tarinfo = tarfile.TarInfo(name='entrypoint2.sh')
        tarinfo.size = len(file_data)
        tarinfo.mtime = time.time()
        tarinfo.mode = 0755
        tar.addfile(tarinfo, StringIO(file_data))

        tar.close()
        tar_stream.seek(0)

        assert c.put_archive(path='/', data=tar_stream) is True

        c.start()
        c = client.containers.get(c.name)
        cls._client = c
        cls._client_port = int(
            c.attrs['NetworkSettings']['Ports']['61315/tcp'][0]['HostPort']
        )
        # now wait for two prompts show up after journaling is enabled
        prompts = -1
        for line in c.logs(stream=True):
            if prompts < 0:
                if line.strip().startswith(r'%GTM-I-JNLSTATE'):
                    prompts = 0
            elif line.strip().startswith('GTM>'):
                prompts += 1
                if prompts > 1:
                    break

    @classmethod
    def tearDownClass(cls):
        cls._client.remove(force=True)


class PIPTest(IntegrationMixin, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(PIPTest, cls).setUpClass()
        pip_sql_rpc.port = cls._client_port

    def test_sql(self):
        pip_sql_rpc.test_sql()

    def test_mrpc(self):
        pip_sql_rpc.test_mrpc()

    def test_mrpc121_get_send(self):
        w = mrpc121.Wrapper()
        w.connect('127.0.0.1', self._client_port, '1', 'xxx')

        fobj = StringIO()
        w.get_element_by_name('STBLMSG-2951.DAT', file_obj=fobj)
        self.assertEqual(fobj.getvalue(), '''\
MESSAGE\tMSGID\r\n\
Version number of client message is not compatible with server\t2951''')

        rows, _ = w._pip.executeSQL(
            'SELECT MESSAGE FROM STBLMSG WHERE MSGID= ?',
            9999
        )
        self.assertEqual(rows[0], '')

        fobj = StringIO('''\
MESSAGE\tMSGID
Custom Message\t9999''')
        w.send_element('STBLMSG-9999.DAT', file_obj=fobj)

        rows, _ = w._pip.executeSQL(
            'SELECT MESSAGE FROM STBLMSG WHERE MSGID= ?',
            9999
        )
        self.assertEqual(rows[0], 'Custom Message')

        w.close()

    def test_mrpc81_compile_and_link(self):
        w = mrpc121.Wrapper()
        w.connect('127.0.0.1', self._client_port, '1', 'xxx')

        # MRPC081 is not registered as RPC in default PIP installation
        # this assert is left commented out because of %CACHE being
        # used in PBSMRPC
        # with self.assertRaises(Exception) as cm:
        #     w.compile_and_link('INV.PROC')
        # self.assertEqual(cm.exception.args[0], 'ER_SV_INVLDRPC')

        # so register it (using SQL or MRPC121) and try again
        w._pip.executeSQL(
            "INSERT INTO SCATBL5 (%SN,RPCID,MRPC,DESC,LOGFLG,PARAM01,PARAM02) "
            "VALUES('PBS',81,'$$^MRPC081','MRPC081',1,1,1)"
        )

        fobj = StringIO('''\
AUTH\tLOGFLG\tRPCID\tUCLS
0\t0\t81\tSCA''')
        w.send_element('SCATBL5A-81.DAT', file_obj=fobj)

        with self.assertRaises(Exception) as cm:
            w.compile_and_link('INV.PROC')
        self.assertEqual(cm.exception.args[1], 'Invalid name - INV')

        fobj = StringIO('''\
//DO NOT MODIFY  Custom MRPC|MRPC999|||||||1
        #OPTION ResultClass ON

public String MRPC999(ret ByteString RETURN, Number versn, Number input)
    type String val()
    set val(1) = input.get() + 1
    set RETURN=$$V2LV^MSG(val())
    quit ""
''')
        self.assertIn(
            '%PSL-I-LIST: 0 errors, 0 warnings, 0 informational messages',
            w.test_compile_element(
                'MRPC999.PROC',
                file_obj=fobj, close_file=False
            )
        )
        fobj.seek(0)
        w.send_element('MRPC999.PROC', file_obj=fobj)
        w.compile_and_link('MRPC999.PROC')

        w._pip.executeSQL(
            "INSERT INTO SCATBL5 (%SN,RPCID,MRPC,DESC,LOGFLG,PARAM01) "
            "VALUES('PBS','999','$$^MRPC999','Custom MRPC',1,1)"
        )
        w._pip.executeSQL(
            "INSERT INTO SCATBL5A (RPCID,UCLS,AUTH,LOGFLG) "
            "VALUES('999','SCA',0,0)"
        )

        self.assertEqual(
            w._pip.executeMRPC('999', success_unpack=True),
            ['1']
        )
        self.assertEqual(
            w._pip.executeMRPC('999', '3', success_unpack=True),
            ['4']
        )

        w.close()


class MTMTest(IntegrationMixin, unittest.TestCase):
    @classmethod
    def customDocker(cls, tar):
        """
        Include code for a custom NSM (non-standard messaging) server
        and re-configure SCA$IBS existing SVTYP definition to use it
        """
        file_data = '''\
ZTSTSV(IM)
        I $E(IM,1,5)="echo " quit $E(IM,6,99999)
        Q ""
'''
        tarinfo = tarfile.TarInfo(name='home/pip/pip_V02/zrtns/ZTSTSV.m')
        tarinfo.size = len(file_data)
        tarinfo.mtime = time.time()
        tarinfo.mode = 0666
        tar.addfile(tarinfo, StringIO(file_data))

        return '''\
sed -i 's/-p61315/-a61315/g' home/pip/pip_V02/mtm/PIPMTM
echo 's ^CTBL("SVTYP","SCA$IBS")="Profile Server||0|SVCNCT^PBSSRV||1|1|45||1|MTM|ZTSTSV"' | su pip /home/pip/pip_V02/dm
'''

    @classmethod
    def setUpClass(cls):
        super(MTMTest, cls).setUpClass()
        custom_server.port = cls._client_port

    def test_nsm(self):
        custom_server.main()


if __name__ == '__main__':
    unittest.main()
