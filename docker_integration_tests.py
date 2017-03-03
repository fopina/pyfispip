#!/usr/bin/env python

import docker
import time
import unittest
import tarfile
from StringIO import StringIO

from examples import pip_sql_rpc, custom_server


class IntegrationMixin():
    @classmethod
    def runContainer(cls):
        client = docker.from_env()
        c = client.containers.run(
            'fopina/fis-pip',
            privileged=True, detach=True,
            ports={'61315': None}
        )
        cls._client = client.containers.get(c.name)
        return cls._client

    @classmethod
    def setUpClass(cls):
        c = cls.runContainer()
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


class MTMTest(IntegrationMixin, unittest.TestCase):
    @classmethod
    def runContainer(cls):
        """
        Override container creation from IntegrationMixin to create
        a container with new entrypoint that re-configures SCA$IBS
        with a custom NSM (non-standard messaging) server
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
        file_data = '''\
#!/bin/bash

sed -i 's/-p61315/-a61315/g' home/pip/pip_V02/mtm/PIPMTM
echo 's ^CTBL("SVTYP","SCA$IBS")="Profile Server||0|SVCNCT^PBSSRV||1|1|45||1|MTM|ZTSTSV"' | su pip /home/pip/pip_V02/dm
/entrypoint.sh
'''
        tarinfo = tarfile.TarInfo(name='entrypoint2.sh')
        tarinfo.size = len(file_data)
        tarinfo.mtime = time.time()
        tarinfo.mode = 0755
        tar.addfile(tarinfo, StringIO(file_data))

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

        tar.close()
        tar_stream.seek(0)

        assert c.put_archive(path='/', data=tar_stream) is True

        c.start()
        cls._client = client.containers.get(c.name)
        return cls._client

    @classmethod
    def setUpClass(cls):
        super(MTMTest, cls).setUpClass()
        custom_server.port = cls._client_port

    def test_nsm(self):
        custom_server.main()


if __name__ == '__main__':
    unittest.main()
