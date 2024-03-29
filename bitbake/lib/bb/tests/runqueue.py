#
# BitBake Tests for runqueue task processing
#
# Copyright (C) 2019 Richard Purdie
#
# SPDX-License-Identifier: GPL-2.0-only
#

import unittest
import bb
import os
import tempfile
import subprocess

#
# TODO:
# Add tests on task ordering (X happens before Y after Z)
#

class RunQueueTests(unittest.TestCase):

    alltasks = ['package', 'fetch', 'unpack', 'patch', 'prepare_recipe_sysroot', 'configure',
                'compile', 'install', 'packagedata', 'package_qa', 'package_write_rpm', 'package_write_ipk',
                'populate_sysroot', 'build']
    a1_sstatevalid = "a1:do_package a1:do_package_qa a1:do_packagedata a1:do_package_write_ipk a1:do_package_write_rpm a1:do_populate_lic a1:do_populate_sysroot"
    b1_sstatevalid = "b1:do_package b1:do_package_qa b1:do_packagedata b1:do_package_write_ipk b1:do_package_write_rpm b1:do_populate_lic b1:do_populate_sysroot"

    def run_bitbakecmd(self, cmd, builddir, sstatevalid="", slowtasks="", extraenv=None):
        env = os.environ.copy()
        env["BBPATH"] = os.path.realpath(os.path.join(os.path.dirname(__file__), "runqueue-tests"))
        env["BB_ENV_EXTRAWHITE"] = "SSTATEVALID SLOWTASKS"
        env["SSTATEVALID"] = sstatevalid
        env["SLOWTASKS"] = slowtasks
        if extraenv:
            for k in extraenv:
                env[k] = extraenv[k]
                env["BB_ENV_EXTRAWHITE"] = env["BB_ENV_EXTRAWHITE"] + " " + k
        try:
            output = subprocess.check_output(cmd, env=env, stderr=subprocess.STDOUT,universal_newlines=True, cwd=builddir)
        except subprocess.CalledProcessError as e:
            self.fail("Command %s failed with %s" % (cmd, e.output))
        tasks = []
        with open(builddir + "/task.log", "r") as f:
            tasks = [line.rstrip() for line in f]
        return tasks

    def test_no_setscenevalid(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "a1"]
            sstatevalid = ""
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid)
            expected = ['a1:' + x for x in self.alltasks]
            self.assertEqual(set(tasks), set(expected))

    def test_single_setscenevalid(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "a1"]
            sstatevalid = "a1:do_package"
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid)
            expected = ['a1:package_setscene', 'a1:fetch', 'a1:unpack', 'a1:patch', 'a1:prepare_recipe_sysroot', 'a1:configure',
                        'a1:compile', 'a1:install', 'a1:packagedata', 'a1:package_qa', 'a1:package_write_rpm', 'a1:package_write_ipk',
                        'a1:populate_sysroot', 'a1:build']
            self.assertEqual(set(tasks), set(expected))

    def test_intermediate_setscenevalid(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "a1"]
            sstatevalid = "a1:do_package a1:do_populate_sysroot"
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid)
            expected = ['a1:package_setscene', 'a1:packagedata', 'a1:package_qa', 'a1:package_write_rpm', 'a1:package_write_ipk',
                        'a1:populate_sysroot_setscene', 'a1:build']
            self.assertEqual(set(tasks), set(expected))

    def test_intermediate_notcovered(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "a1"]
            sstatevalid = "a1:do_package_qa a1:do_packagedata a1:do_package_write_ipk a1:do_package_write_rpm a1:do_populate_lic a1:do_populate_sysroot"
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid)
            expected = ['a1:package_write_ipk_setscene', 'a1:package_write_rpm_setscene', 'a1:packagedata_setscene',
                        'a1:package_qa_setscene', 'a1:build', 'a1:populate_sysroot_setscene']
            self.assertEqual(set(tasks), set(expected))

    def test_all_setscenevalid(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "a1"]
            sstatevalid = self.a1_sstatevalid
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid)
            expected = ['a1:package_write_ipk_setscene', 'a1:package_write_rpm_setscene', 'a1:packagedata_setscene',
                        'a1:package_qa_setscene', 'a1:build', 'a1:populate_sysroot_setscene']
            self.assertEqual(set(tasks), set(expected))

    def test_no_settasks(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "a1", "-c", "patch"]
            sstatevalid = self.a1_sstatevalid
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid)
            expected = ['a1:fetch', 'a1:unpack', 'a1:patch']
            self.assertEqual(set(tasks), set(expected))

    def test_mix_covered_notcovered(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "a1:do_patch", "a1:do_populate_sysroot"]
            sstatevalid = self.a1_sstatevalid
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid)
            expected = ['a1:fetch', 'a1:unpack', 'a1:patch', 'a1:populate_sysroot_setscene']
            self.assertEqual(set(tasks), set(expected))


    # Test targets with intermediate setscene tasks alongside a target with no intermediate setscene tasks
    def test_mixed_direct_tasks_setscene_tasks(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "c1:do_patch", "a1"]
            sstatevalid = self.a1_sstatevalid
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid)
            expected = ['c1:fetch', 'c1:unpack', 'c1:patch', 'a1:package_write_ipk_setscene', 'a1:package_write_rpm_setscene', 'a1:packagedata_setscene',
                        'a1:package_qa_setscene', 'a1:build', 'a1:populate_sysroot_setscene']
            self.assertEqual(set(tasks), set(expected))

    # This test slows down the execution of do_package_setscene until after other real tasks have
    # started running which tests for a bug where tasks were being lost from the buildable list of real
    # tasks if they weren't in tasks_covered or tasks_notcovered
    def test_slow_setscene(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "a1"]
            sstatevalid = "a1:do_package"
            slowtasks = "a1:package_setscene"
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid, slowtasks)
            expected = ['a1:package_setscene', 'a1:fetch', 'a1:unpack', 'a1:patch', 'a1:prepare_recipe_sysroot', 'a1:configure',
                        'a1:compile', 'a1:install', 'a1:packagedata', 'a1:package_qa', 'a1:package_write_rpm', 'a1:package_write_ipk',
                        'a1:populate_sysroot', 'a1:build']
            self.assertEqual(set(tasks), set(expected))

    def test_setscenewhitelist(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "a1"]
            extraenv = {
                "BB_SETSCENE_ENFORCE" : "1",
                "BB_SETSCENE_ENFORCE_WHITELIST" : "a1:do_package_write_rpm a1:do_build"
            }
            sstatevalid = "a1:do_package a1:do_package_qa a1:do_packagedata a1:do_package_write_ipk a1:do_populate_lic a1:do_populate_sysroot"
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid, extraenv=extraenv)
            expected = ['a1:packagedata_setscene', 'a1:package_qa_setscene', 'a1:package_write_ipk_setscene',
                        'a1:populate_sysroot_setscene', 'a1:package_setscene']
            self.assertEqual(set(tasks), set(expected))

    # Tests for problems with dependencies between setscene tasks
    def test_no_setscenevalid_harddeps(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "d1"]
            sstatevalid = ""
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid)
            expected = ['a1:package', 'a1:fetch', 'a1:unpack', 'a1:patch', 'a1:prepare_recipe_sysroot', 'a1:configure',
                        'a1:compile', 'a1:install', 'a1:packagedata', 'a1:package_write_rpm', 'a1:package_write_ipk',
                        'a1:populate_sysroot', 'd1:package', 'd1:fetch', 'd1:unpack', 'd1:patch', 'd1:prepare_recipe_sysroot', 'd1:configure',
                        'd1:compile', 'd1:install', 'd1:packagedata', 'd1:package_qa', 'd1:package_write_rpm', 'd1:package_write_ipk',
                        'd1:populate_sysroot', 'd1:build']
            self.assertEqual(set(tasks), set(expected))

    def test_no_setscenevalid_withdeps(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "b1"]
            sstatevalid = ""
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid)
            expected = ['a1:' + x for x in self.alltasks] + ['b1:' + x for x in self.alltasks]
            expected.remove('a1:build')
            expected.remove('a1:package_qa')
            self.assertEqual(set(tasks), set(expected))

    def test_single_a1_setscenevalid_withdeps(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "b1"]
            sstatevalid = "a1:do_package"
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid)
            expected = ['a1:package_setscene', 'a1:fetch', 'a1:unpack', 'a1:patch', 'a1:prepare_recipe_sysroot', 'a1:configure',
                        'a1:compile', 'a1:install', 'a1:packagedata', 'a1:package_write_rpm', 'a1:package_write_ipk',
                        'a1:populate_sysroot'] + ['b1:' + x for x in self.alltasks]
            self.assertEqual(set(tasks), set(expected))

    def test_single_b1_setscenevalid_withdeps(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "b1"]
            sstatevalid = "b1:do_package"
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid)
            expected = ['a1:package', 'a1:fetch', 'a1:unpack', 'a1:patch', 'a1:prepare_recipe_sysroot', 'a1:configure',
                        'a1:compile', 'a1:install', 'a1:packagedata', 'a1:package_write_rpm', 'a1:package_write_ipk',
                        'a1:populate_sysroot', 'b1:package_setscene'] + ['b1:' + x for x in self.alltasks]
            expected.remove('b1:package')
            self.assertEqual(set(tasks), set(expected))

    def test_intermediate_setscenevalid_withdeps(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "b1"]
            sstatevalid = "a1:do_package a1:do_populate_sysroot b1:do_package"
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid)
            expected = ['a1:package_setscene', 'a1:packagedata', 'a1:package_write_rpm', 'a1:package_write_ipk',
                        'a1:populate_sysroot_setscene', 'b1:package_setscene'] + ['b1:' + x for x in self.alltasks]
            expected.remove('b1:package')
            self.assertEqual(set(tasks), set(expected))

    def test_all_setscenevalid_withdeps(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            cmd = ["bitbake", "b1"]
            sstatevalid = self.a1_sstatevalid + " " + self.b1_sstatevalid
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid)
            expected = ['a1:package_write_ipk_setscene', 'a1:package_write_rpm_setscene', 'a1:packagedata_setscene',
                        'b1:build', 'a1:populate_sysroot_setscene', 'b1:package_write_ipk_setscene', 'b1:package_write_rpm_setscene',
                        'b1:packagedata_setscene', 'b1:package_qa_setscene', 'b1:populate_sysroot_setscene']
            self.assertEqual(set(tasks), set(expected))

    def test_multiconfig_setscene_optimise(self):
        with tempfile.TemporaryDirectory(prefix="runqueuetest") as tempdir:
            extraenv = {
                "BBMULTICONFIG" : "mc1 mc2",
                "BB_SIGNATURE_HANDLER" : "basic"
            }
            cmd = ["bitbake", "b1", "mc:mc1:b1", "mc:mc2:b1"]
            setscenetasks = ['package_write_ipk_setscene', 'package_write_rpm_setscene', 'packagedata_setscene',
                             'populate_sysroot_setscene', 'package_qa_setscene']
            sstatevalid = ""
            tasks = self.run_bitbakecmd(cmd, tempdir, sstatevalid, extraenv=extraenv)
            expected = ['a1:' + x for x in self.alltasks] + ['b1:' + x for x in self.alltasks] + \
                       ['mc1:b1:' + x for x in setscenetasks] + ['mc1:a1:' + x for x in setscenetasks] + \
                       ['mc2:b1:' + x for x in setscenetasks] + ['mc2:a1:' + x for x in setscenetasks] + \
                       ['mc1:b1:build', 'mc2:b1:build']
            for x in ['mc1:a1:package_qa_setscene', 'mc2:a1:package_qa_setscene', 'a1:build', 'a1:package_qa']:
                expected.remove(x)
            self.assertEqual(set(tasks), set(expected))

