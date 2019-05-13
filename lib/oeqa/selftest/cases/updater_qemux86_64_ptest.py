# pylint: disable=C0111,C0325
import os
import re

from oeqa.selftest.case import OESelftestTestCase
from oeqa.utils.commands import runCmd
from testutils import qemu_launch, qemu_send_command, qemu_terminate


class PtestTests(OESelftestTestCase):

    def setUpLocal(self):
        layer = "meta-updater-qemux86-64"
        result = runCmd('bitbake-layers show-layers')
        if re.search(layer, result.output) is None:
            # Assume the directory layout for finding other layers. We could also
            # make assumptions by using 'show-layers', but either way, if the
            # layers we need aren't where we expect them, we are out of like.
            path = os.path.abspath(os.path.dirname(__file__))
            metadir = path + "/../../../../../"
            self.meta_qemu = metadir + layer
            runCmd('bitbake-layers add-layer "%s"' % self.meta_qemu)
        else:
            self.meta_qemu = None
        self.append_config('MACHINE = "qemux86-64"')
        self.append_config('SYSTEMD_AUTO_ENABLE_aktualizr = "disable"')
        self.append_config('PTEST_ENABLED_pn-aktualizr = "1"')
        self.append_config('IMAGE_INSTALL_append += "aktualizr-ptest ptest-runner "')
        self.qemu, self.s = qemu_launch(machine='qemux86-64')

    def tearDownLocal(self):
        qemu_terminate(self.s)
        if self.meta_qemu:
            runCmd('bitbake-layers remove-layer "%s"' % self.meta_qemu, ignore_status=True)

    def qemu_command(self, command, timeout=60):
        return qemu_send_command(self.qemu.ssh_port, command, timeout=timeout)

    def test_run_ptests(self):
        # simulate a login shell, so that /usr/sbin is in $PATH (from /etc/profile)
        stdout, stderr, retcode = self.qemu_command('sh -l -c ptest-runner', timeout=None)
        output = stdout.decode()
        print(output)

        has_failure = re.search('^FAIL', output, flags=re.MULTILINE) is not None
        if has_failure:
            print("Full test suite log:")
            stdout, _, _ = self.qemu_command('cat /tmp/aktualizr-ptest.log || cat /tmp/aktualizr-ptest.log.tmp', timeout=None)
            print(stdout.decode())

        self.assertEqual(retcode, 0)
        self.assertFalse(has_failure)
