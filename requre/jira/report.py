"""
Requre-based integration tests for the tmt Jira report plugin.

Run with recorded cassettes (no live API needed):
    python3 -m pytest -vvv report.py

Re-record cassettes against a real Jira instance (requre only writes when
the cassette is missing or REQURE_MODE=write forces it; there is no
REQURE_CASSETTE_DIR/REQURE_RECORD option, the path is derived from the
test id automatically):
    REQURE_MODE=write TMT_PLUGIN_REPORT_JIRA_TOKEN=<token> \
    python3 -m pytest -vvv report.py
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, IO, Mapping, Optional, Sequence, Union

import click.core
import click.testing
from requre import RequreTestCase

import tmt.cli._root
import tmt.log

PROJECT = 'RHELTEST'
JIRA_URL = 'https://stage-redhat.atlassian.net'

TEST_DIR = Path(__file__).parent

logger = tmt.log.Logger.create(verbose=0, debug=0, quiet=False)

# Common environment for all report runs
JIRA_ENV = {
    'TMT_PLUGIN_REPORT_JIRA_URL': JIRA_URL,
    'TMT_PLUGIN_REPORT_JIRA_USER': 'pmatyas@redhat.com',
    'TMT_PLUGIN_REPORT_JIRA_TOKEN': os.environ.get('TMT_PLUGIN_REPORT_JIRA_TOKEN', 'token'),
    'TMT_PLUGIN_REPORT_JIRA_PROJECT_ID': PROJECT,
    'TMT_PLUGIN_REPORT_JIRA_COMPOSE_ID': 'RHEL-10.3-20260817.0',
    'TMT_PLUGIN_REPORT_JIRA_FIX_VERSION': 'rhel-10.3',
}


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

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)
        os.chdir(self.cwd)
        super().tearDown()

    def run_tmt(
            self, extra_args: list[str], extra_env: Optional[dict] = None,
            ) -> click.testing.Result:
        # requre replays cassettes by patching the HTTP layer of the current
        # Python process; a subprocess wouldn't inherit that instrumentation,
        # so the CLI must be invoked in-process, same as export.py does.
        os.chdir(self.tmpdir)
        env = {**JIRA_ENV, **(extra_env or {})}
        return CliRunner().invoke(
            tmt.cli._root.main,
            [
                '--feeling-safe', 'run',
                'provision', '--how', 'local',
                'discover', '--how', 'fmf', '--test', '/existing_testcase$',
                'execute',
                'report', '--how', 'jira',
            ] + extra_args,
            env=env,
            )


class JiraReportDry(Base):
    """Dry-run tests — no API calls made."""

    def test_dryrun(self) -> None:
        """Dry run completes without error and without API calls."""
        result = self.run_tmt(['--dry'])
        # Dry run may exit non-zero due to no results, but must not crash
        self.assertNotIn('Traceback', result.stderr)
        self.assertNotIn('Error', result.stderr.split('\n')[0])

    def test_missing_options_fails(self) -> None:
        """Missing required credentials produce a clear error."""
        result = self.run_tmt([], extra_env={
            'TMT_PLUGIN_REPORT_JIRA_URL': '',
            'TMT_PLUGIN_REPORT_JIRA_TOKEN': '',
            'TMT_PLUGIN_REPORT_JIRA_USER': '',
        })
        self.assertNotEqual(result.exit_code, 0)
        # tmt.cli._root.main is invoked directly here, bypassing
        # tmt.__main__.run_cli()'s except-clause, which is the only place
        # that formats and prints an exception (via show_exception()). So
        # the ReportError never reaches stdout/stderr; it is only available
        # chained as __cause__ of the GeneralError('plan failed.') that
        # Run.go() raises for a crashed plan.
        self.assertIsNotNone(result.exception)
        self.assertIn('Missing required Jira options', str(result.exception.__cause__))


class JiraReportPass(Base):
    """Report a passing result — TestResult skeleton created and PASS comment posted."""

    def test_report_pass(self) -> None:
        """PASS result creates a TestResult subtask and posts a green comment."""
        result = self.run_tmt(['--component-nvr', 'bash-5.3.9-3.fc44'])
        self.assertEqual(result.exit_code, 0, msg=result.stderr)
        self.assertIn('PASS', result.stderr)
        self.assertIn('Jira report:', result.stderr)


class JiraReportFail(Base):
    """Report a failing result — TestResult skeleton transitions to FAIL."""

    def setUp(self) -> None:
        super().setUp()
        (self.tmpdir / 'main.fmf').write_text('test: /bin/false\n')

    def tearDown(self) -> None:
        (self.tmpdir / 'main.fmf').write_text('test: /bin/true\n')
        super().tearDown()

    def test_report_fail(self) -> None:
        """FAIL result transitions TestResult subtask to FAIL status."""
        result = self.run_tmt(['--component-nvr', 'bash-5.3.9-3.fc44'])
        # tmt exits non-zero on test failure but report should succeed
        self.assertIn('FAIL', result.stderr)
        self.assertIn('Jira report:', result.stderr)
