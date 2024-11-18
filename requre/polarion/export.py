import os

import click.core
import click.testing
from fmf import Tree
import tmt.base
from tmt.export import polarion
from tmt.identifier import ID_KEY
from requre import RequreTestCase
from pathlib import Path
import tempfile
import shutil
import logging

from typing import Any, IO, Mapping, Optional, Sequence, Union

try:
    from tmt.cli._root import main as cli_main
except ImportError:
    from tmt.cli import main as cli_main

PROJECT = "RHELBASEOS"

# Prepare path to examples
TEST_DIR = Path(__file__).parent

# Create the default logger
logger = tmt.log.Logger.create(verbose=0, debug=0, quiet=False)


# TODO: shamelessly copied from tmt's tests/__init__.py. Is there a way how to re-use/import
# instead of copy & pasting?
def reset_common() -> None:
    """
    Reset CLI invocation storage of classes derived from :py:class:`tmt.utils.Common`

    As CLI invocations are stored in class-level attributes, before each
    invocation of CLI in a test, we must reset these attributes to pretend the
    CLI is invoked for the very first time. Without this, after the very first
    invocation, subsequent CLI invocations would "inherit" options from the
    previous ones.

    A helper function to clear invocations of the "usual suspects". Classes that
    accept CLI options are reset.
    """

    from tmt.base import Core, Plan, Run, Story, Test, Tree
    from tmt.utils import Common, MultiInvokableCommon

    for klass in (
            Core, Run, Tree, Test, Plan, Story,
            Common, MultiInvokableCommon):

        klass.cli_invocation = None


class CliRunner(click.testing.CliRunner):
    def invoke(
            self,
            cli: click.core.BaseCommand,
            args: Optional[Union[str, Sequence[str]]] = None,
            input: Optional[Union[str, bytes, IO]] = None,
            env: Optional[Mapping[str, Optional[str]]] = None,
            catch_exceptions: bool = True,
            color: bool = False,
            **extra: Any) -> click.testing.Result:
        reset_common()

        return super().invoke(
            cli,
            args=args,
            input=input,
            env=env,
            catch_exceptions=catch_exceptions,
            color=color,
            **extra)


class Base(RequreTestCase):
    EXAMPLES = TEST_DIR / "data"

    def setUp(self):
        super().setUp()
        self.tmpdir = Path(tempfile.mktemp(prefix=str(TEST_DIR)))
        shutil.copytree(self.EXAMPLES, self.tmpdir)
        self.cwd = os.getcwd()
        self.runner_output = None

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        os.chdir(self.cwd)
        super().tearDown()
        if hasattr(
                self.runner_output,
                "exit_code") and self.runner_output.exit_code != 0:
            print("Return code:", self.runner_output.exit_code)
            print("Output:", self.runner_output.output)
            print("Exception:", self.runner_output.exception)


class PolarionBase(Base):
    EXAMPLES = TEST_DIR / "data"

    def test(self):
        fmf_node = Tree(self.tmpdir).find("/existing_testcase")
        tmt_test = tmt.base.Test(node=fmf_node, logger=logger)
        tmt_test.opt("project_id", PROJECT)
        polarion.export_to_polarion(tmt_test)


class PolarionExport(Base):
    EXAMPLES = TEST_DIR / "data"

    def test_create(self):
        fmf_node = Tree(self.tmpdir).find("/new_testcase")
        self.assertNotIn(ID_KEY, fmf_node.data)

        os.chdir(self.tmpdir / "new_testcase")
        runner = CliRunner()
        self.runner_output = runner.invoke(cli_main, [
            "test", "export", "--how", "polarion", "--project-id",
            PROJECT, "--create", "."])
        # Reload the node data to see if it appears there
        fmf_node = Tree(self.tmpdir).find("/new_testcase")
        self.assertIn(ID_KEY, fmf_node.data)

    def test_create_dryrun(self):
        fmf_node_before = Tree(self.tmpdir).find("/new_testcase")
        self.assertNotIn(ID_KEY, fmf_node_before.data)

        os.chdir(self.tmpdir / "new_testcase")
        runner = CliRunner()
        self.runner_output = runner.invoke(
            cli_main,
            ["test", "export", "--how", "polarion", "--create", "--project-id",
             PROJECT, "--dry", "."],
            catch_exceptions=False)
        fmf_node = Tree(self.tmpdir).find("/new_testcase")
        self.assertNotIn(ID_KEY, fmf_node.data)
        self.assertEqual(fmf_node_before.data, fmf_node.data)
        self.assertIn(
            "title: This is new testcase inside polarion",
            self.runner_output.output)

    def test_existing(self):
        fmf_node = Tree(self.tmpdir).find("/existing_testcase")
        self.assertEqual(fmf_node.data["extra-nitrate"], "TC#0609686")

        os.chdir(self.tmpdir / "existing_testcase")
        runner = CliRunner()
        self.runner_output = runner.invoke(cli_main, [
            "test", "export", "--how", "polarion", "--project-id",
            PROJECT, "--create", "."])

        fmf_node = Tree(self.tmpdir).find("/existing_testcase")
        self.assertEqual(fmf_node.data["extra-nitrate"], "TC#0609686")

    def test_existing_dryrun(self):
        fmf_node = Tree(self.tmpdir).find("/existing_dryrun_testcase")
        self.assertEqual(fmf_node.data["extra-nitrate"], "TC#0609686")

        os.chdir(self.tmpdir / "existing_dryrun_testcase")
        runner = CliRunner()
        self.runner_output = runner.invoke(
            cli_main,
            ["test", "export", "--how", "polarion", "--debug", "--dry",
             "--bugzilla", "."],
            catch_exceptions=False)
        self.assertIn(
            "title: ABCDEF",
            self.runner_output.output)

    def test_coverage_bugzilla(self):
        fmf_node = Tree(self.tmpdir).find("/existing_testcase")
        self.assertEqual(fmf_node.data["extra-nitrate"], "TC#0609686")

        os.chdir(self.tmpdir / "existing_testcase")
        runner = CliRunner()
        self.runner_output = runner.invoke(cli_main, [
            "test", "export", "--how", "polarion", "--project-id",
            PROJECT, "--bugzilla", "."])
        assert self.runner_output.exit_code == 0
