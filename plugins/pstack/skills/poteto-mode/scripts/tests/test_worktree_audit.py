import csv
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


AUDIT = Path(__file__).resolve().parents[1] / 'worktree-audit.sh'


class WorktreeAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / 'project'
        self.repo.mkdir()
        self.git('init', '-b', 'main')
        self.git('-c', 'user.name=Audit', '-c', 'user.email=audit@example.com',
                 'commit', '--allow-empty', '-m', 'fixture')
        self.git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        self.worktree = self.root / 'work-tree'
        self.git('worktree', 'add', '-b', 'topic', str(self.worktree))
        self.tools = self.root / 'bin'
        self.tools.mkdir()
        gh = self.tools / 'gh'
        gh.write_text('#!/bin/sh\nprintf "[]\\n"\n')
        gh.chmod(0o755)

    def git(self, *arguments: str) -> str:
        return subprocess.run(
            ['git', '-C', str(self.repo), *arguments],
            text=True, capture_output=True, check=True,
        ).stdout

    def audit(self, transcripts: Path | None = None) -> dict[str, str]:
        args = ['bash', str(AUDIT), str(self.repo)]
        if transcripts is not None:
            args.append(str(transcripts))
        output = subprocess.run(
            args, text=True, capture_output=True, check=True,
            env={**os.environ, 'PATH': f'{self.tools}:{os.environ["PATH"]}'},
        ).stdout
        rows = list(csv.DictReader(io.StringIO(output), delimiter='\t'))
        self.assertEqual(1, len(rows))
        self.assertTrue(self.worktree.is_dir())
        return rows[0]

    def test_unknown_chat_cannot_authorize_cleanup(self) -> None:
        row = self.audit()
        self.assertEqual(str(self.worktree), row['WORKTREE'])
        self.assertEqual('unknown', row['LAST_CHAT'])
        self.assertEqual('hold-unknown-chat', row['BUCKET'])

    def test_scoped_chat_with_spaces_is_recent(self) -> None:
        moved = self.root / 'work tree'
        self.git('worktree', 'move', str(self.worktree), str(moved))
        self.worktree = moved
        transcripts = self.root / 'transcripts'
        transcripts.mkdir()
        (transcripts / 'session with spaces.txt').write_text(
            f'Worked in {self.worktree}/source.py\n'
        )
        row = self.audit(transcripts)
        self.assertNotEqual('unknown', row['LAST_CHAT'])
        self.assertEqual('verify-recent-chat', row['BUCKET'])

    def test_dirty_worktree_stays_protected(self) -> None:
        (self.worktree / 'uncommitted.txt').write_text('keep')
        row = self.audit()
        self.assertEqual('hold-wip', row['BUCKET'])
        self.assertEqual('keep', (self.worktree / 'uncommitted.txt').read_text())


if __name__ == '__main__':
    unittest.main()
