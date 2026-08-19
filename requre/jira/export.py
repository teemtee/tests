"""
Requre-based integration tests for the tmt Jira export plugin.

Run with recorded cassettes (no live API needed):
    python3 -m pytest -vvv export.py

Re-record cassettes against a real Jira instance (requre only writes when
the cassette is missing or REQURE_MODE=write forces it; there is no
REQURE_CASSETTE_DIR/REQURE_RECORD option, the path is derived from the
test id automatically):
    REQURE_MODE=write TMT_PLUGIN_EXPORT_JIRA_TOKEN=<token> \
    python3 -m pytest -vvv export.py
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, IO, Mapping, Optional, Sequence, Union

import click.core
import click.testing
from fmf import Tree
from requre import RequreTestCase

import tmt.base
import tmt.cli._root
import tmt.log

PROJECT = 'RHELTEST'
JIRA_URL = 'https://stage-redhat.atlassian.net'

TEST_DIR = Path(__file__).parent

logger = tmt.log.Logger.create(verbose=0, debug=0, quiet=False)


def reset_common() -> None:
    from tmt.base import Core, Plan, Run, Story, Test, Tree
    from tmt.utils import Common, MultiInvokableCommon

    for klass in (Core, Run, Tree, Test, Plan, Story, Common, MultiInvokableCommon):
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
            **extra: Any,
            ) -> click.testing.Result:
        reset_common()
        return super().invoke(
            cli, args=args, input=input, env=env,
            catch_exceptions=catch_exceptions, color=color, **extra,
            )


class Base(RequreTestCase):
    EXAMPLES = TEST_DIR / 'data'

    def setUp(self) -> None:
        super().setUp()
        self.tmpdir = Path(tempfile.mktemp(prefix=str(TEST_DIR)))
        shutil.copytree(self.EXAMPLES, self.tmpdir)
        self.cwd = os.getcwd()
        self.runner_output = None

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)
        os.chdir(self.cwd)
        super().tearDown()
        if (
            hasattr(self.runner_output, 'exit_code')
            and self.runner_output.exit_code != 0
        ):
            print('Return code:', self.runner_output.exit_code)
            print('Output:', self.runner_output.output)
            print('Exception:', self.runner_output.exception)


class JiraExportCreate(Base):
    """Create a new Jira TestCase when none exists."""

    def test_create(self) -> None:
        """New TestCase is created and implements link written back."""
        fmf_node_before = Tree(self.tmpdir).find('/new_testcase')
        links_before = fmf_node_before.data.get('link', [])
        jira_links_before = [
            lnk for lnk in links_before
            if isinstance(lnk, dict) and JIRA_URL in str(lnk.get('implements', ''))
        ]
        self.assertEqual(len(jira_links_before), 0, 'Jira implements link present before export')

        os.chdir(self.tmpdir / 'new_testcase')
        runner = CliRunner()
        self.runner_output = runner.invoke(
            tmt.cli._root.main,
            [
                'test', 'export', '--how', 'jira',
                '--project-id', PROJECT,
                '--jira-url', JIRA_URL,
                '--jira-user', 'pmatyas@redhat.com',
                '--jira-token', os.environ.get('TMT_PLUGIN_EXPORT_JIRA_TOKEN', 'token'),
                '--create', '--link-jira', '--ignore-git-validation', '.',
            ],
            )
        self.assertEqual(self.runner_output.exit_code, 0)
        fmf_node = Tree(self.tmpdir).find('/new_testcase')
        links = fmf_node.data.get('link', [])
        jira_links = [
            lnk for lnk in links
            if isinstance(lnk, dict) and JIRA_URL in str(lnk.get('implements', ''))
        ]
        self.assertGreater(len(jira_links), 0, 'No implements link written back')

    def test_create_dryrun(self) -> None:
        """Dry run does not create TestCase or modify fmf."""
        fmf_node_before = Tree(self.tmpdir).find('/new_testcase')

        os.chdir(self.tmpdir / 'new_testcase')
        runner = CliRunner()
        self.runner_output = runner.invoke(
            tmt.cli._root.main,
            [
                'test', 'export', '--how', 'jira',
                '--project-id', PROJECT,
                '--jira-url', JIRA_URL,
                '--jira-user', 'pmatyas@redhat.com',
                '--jira-token', 'token',
                '--create', '--dry', '--ignore-git-validation', '.',
            ],
            catch_exceptions=False,
            )
        self.assertEqual(self.runner_output.exit_code, 0)
        # fmf data must be unchanged
        fmf_node = Tree(self.tmpdir).find('/new_testcase')
        self.assertEqual(fmf_node_before.data, fmf_node.data)
        self.assertIn("would be created", self.runner_output.output)


class JiraExportExisting(Base):
    """Update an existing Jira TestCase."""

    def test_existing_by_implements(self) -> None:
        """Existing TestCase located via implements link is updated."""
        os.chdir(self.tmpdir / 'existing_testcase')
        runner = CliRunner()
        self.runner_output = runner.invoke(
            tmt.cli._root.main,
            [
                'test', 'export', '--how', 'jira',
                '--project-id', PROJECT,
                '--jira-url', JIRA_URL,
                '--jira-user', 'pmatyas@redhat.com',
                '--jira-token', os.environ.get('TMT_PLUGIN_EXPORT_JIRA_TOKEN', 'token'),
                '--ignore-git-validation', '.',
            ],
            )
        self.assertEqual(self.runner_output.exit_code, 0)
        self.assertIn('updated', self.runner_output.output)

    def test_existing_by_uuid(self) -> None:
        """Existing TestCase located via UUID search is updated."""
        os.chdir(self.tmpdir / 'existing_uuid_testcase')
        runner = CliRunner()
        self.runner_output = runner.invoke(
            tmt.cli._root.main,
            [
                'test', 'export', '--how', 'jira',
                '--project-id', PROJECT,
                '--jira-url', JIRA_URL,
                '--jira-user', 'pmatyas@redhat.com',
                '--jira-token', os.environ.get('TMT_PLUGIN_EXPORT_JIRA_TOKEN', 'token'),
                '--ignore-git-validation', '.',
            ],
            )
        self.assertEqual(self.runner_output.exit_code, 0)
        self.assertIn('updated', self.runner_output.output)

    def test_existing_dryrun(self) -> None:
        """Dry run on existing TestCase prints summary and leaves fmf unchanged."""
        fmf_node_before = Tree(self.tmpdir).find('/existing_testcase')

        os.chdir(self.tmpdir / 'existing_testcase')
        runner = CliRunner()
        self.runner_output = runner.invoke(
            tmt.cli._root.main,
            [
                'test', 'export', '--how', 'jira',
                '--project-id', PROJECT,
                '--jira-url', JIRA_URL,
                '--jira-user', 'pmatyas@redhat.com',
                '--jira-token', 'token',
                '--dry', '--ignore-git-validation', '.',
            ],
            catch_exceptions=False,
            )
        self.assertEqual(self.runner_output.exit_code, 0)
        fmf_node = Tree(self.tmpdir).find('/existing_testcase')
        self.assertEqual(fmf_node_before.data, fmf_node.data)
        self.assertIn('summary:', self.runner_output.output)

    def test_missing_required_options(self) -> None:
        """Export fails clearly when required options are absent."""
        os.chdir(self.tmpdir / 'new_testcase')
        runner = CliRunner()
        self.runner_output = runner.invoke(
            tmt.cli._root.main,
            [
                'test', 'export', '--how', 'jira',
                '--create', '--ignore-git-validation', '.',
            ],
            )
        self.assertNotEqual(self.runner_output.exit_code, 0)
        self.assertIn('Missing required Jira options', str(self.runner_output.exception))
