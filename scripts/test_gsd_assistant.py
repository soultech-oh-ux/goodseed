import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("assistant", Path(__file__).with_name("gsd-assistant.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def capability(procedure="폼 구현 후 입력 오류와 저장을 검사한다."):
    return {"name": "form-validation", "trigger": "입력 폼 validation", "procedure": procedure,
            "validation_command": "python -m unittest test_form"}


def result(completed=True, caps=None):
    return {"completed": completed, "answer": "구현 결과와 실행 방법", "capabilities": caps or [capability()]}


class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="gsd-assistant-test-")
        self.root = Path(self.temp.name)
        self.project = str(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, db, response=None, successful=None, learn=True):
        return a.record_result(db, self.project, [], response or result(),
                               successful if successful is not None else {capability()["validation_command"]}, learn)

    def test_no_execution_evidence_or_incomplete_run_cannot_activate(self):
        with a.database(self.root) as db:
            self.assertEqual(self.save(db, successful=set()), 0)
            self.assertEqual(self.save(db, response=result(False)), 0)
            self.assertEqual(a.current_capabilities(db, self.project), [])

    def test_revision_retrieval_and_project_isolation(self):
        with a.database(self.root) as db:
            self.assertEqual(self.save(db), 1)
            self.assertEqual(self.save(db), 0)
            self.assertEqual(self.save(db, result(caps=[capability("저장과 초기화까지 검사한다.")])), 1)
            caps = a.retrieve(db, self.project, "입력 폼 만들어줘")
            self.assertEqual(caps[0]["version"], 2)
            self.assertEqual(a.retrieve(db, "other-project", "입력 폼"), [])
            self.assertEqual(a.retrieve(db, self.project, "음악 플레이어"), [])

    def test_rollback_retains_audit_history_and_forget_removes_versions(self):
        with a.database(self.root) as db, contextlib.redirect_stdout(io.StringIO()):
            self.save(db)
            self.save(db, result(caps=[capability("개선한 절차")]))
            args = a.parser().parse_args(["learn", "rollback", "form-validation", "--version", "1"])
            a.manage(db, args, self.project)
            cap = a.current_capabilities(db, self.project)[0]
            self.assertEqual(cap["version"], 3)
            self.assertEqual(cap["procedure"], capability()["procedure"])
            self.assertEqual(db.execute("SELECT COUNT(*) FROM capabilities").fetchone()[0], 3)
            a.manage(db, a.parser().parse_args(["learn", "forget", "form-validation"]), self.project)
            self.assertEqual(a.current_capabilities(db, self.project), [])

    def test_disabled_learning_and_explicit_profile_persist(self):
        with a.database(self.root) as db, contextlib.redirect_stdout(io.StringIO()):
            a.manage(db, a.parser().parse_args(["learn", "off"]), self.project)
            a.manage(db, a.parser().parse_args(["learn", "profile", "--level", "advanced"]), self.project)
            self.assertEqual(a.settings(db), ("advanced", False))
            self.assertEqual(self.save(db, learn=False), 0)
        with a.database(self.root) as db:
            self.assertEqual(a.settings(db), ("advanced", False))

    def test_invalid_response_is_rejected(self):
        invalid = [{}, result(caps=[dict(capability(), name="../escape")]),
                   result(caps=[capability(), capability()]),
                   result(caps=[dict(capability(), procedure="x" * 6001)]),
                   dict(result(), completed="true"), dict(result(), answer="")]
        for value in invalid:
            with self.subTest(value=str(value)[:80]), self.assertRaises(ValueError):
                a.validate_result(value)

    def test_profile_feedback_is_explicit(self):
        self.assertEqual(a.level_hint("초보자인데 앱 만들어줘"), "beginner")
        self.assertEqual(a.level_hint("전문가 수준으로 설명해"), "advanced")
        self.assertIsNone(a.level_hint("고급 암호화 기능 앱을 만들어줘"))

    def test_failed_transaction_does_not_replace_existing_procedure(self):
        with a.database(self.root) as db:
            self.save(db)
        with self.assertRaises(RuntimeError), a.database(self.root) as db:
            self.save(db, result(caps=[capability("폐기할 절차")]))
            raise RuntimeError("interrupted")
        with a.database(self.root) as db:
            self.assertEqual(a.current_capabilities(db, self.project)[0]["version"], 1)

    def test_preview_does_not_execute_or_learn(self):
        with patch.dict(a.os.environ, {"GSD_ASSISTANT_HOME": str(self.root / "state")}), \
             patch.object(a, "run_engine") as engine, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(a.main(["ask", "--preview", "--cwd", self.project, "입력 폼"]), 0)
            engine.assert_not_called()
            self.assertIn("입력 폼", output.getvalue())
        with a.database(self.root / "state") as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM runs").fetchone()[0], 0)

    def test_no_learn_excludes_memory_and_failed_run_returns_nonzero(self):
        state = self.root / "state"
        with a.database(state) as db:
            self.save(db)
        with patch.dict(a.os.environ, {"GSD_ASSISTANT_HOME": str(state)}), \
             patch.object(a, "run_engine", return_value=(result(False), set())) as engine, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(a.main(["ask", "--no-learn", "--cwd", self.project, "입력 폼"]), 1)
            self.assertIn("재사용 절차(JSON): []", engine.call_args.args[0])
        with a.database(state) as db:
            self.assertEqual(a.current_capabilities(db, self.project)[0]["version"], 1)

    def fake_engine(self, mode):
        script = self.root / "fake_engine.py"
        script.write_text("""import sys,json,time
from pathlib import Path
prompt=sys.stdin.read()
mode=sys.argv[1]
if mode=='timeout': time.sleep(10)
if mode=='fail': print('authentication failed');sys.exit(2)
item={'type':'item.completed','item':{'type':'command_execution','status':'completed',
      'command':'python -m unittest test_form','exit_code':0}}
print(json.dumps(item),flush=True)
out=Path(sys.argv[sys.argv.index('--output-last-message')+1])
out.write_text(sys.argv[2],encoding='utf-8')
""", encoding="utf-8")
        return [sys.executable, str(script), mode, json.dumps(result())]

    def test_engine_subprocess_schema_and_observed_evidence(self):
        with contextlib.redirect_stdout(io.StringIO()):
            response, evidence = a.run_engine('한글 " & $(no-shell)', self.project, 10, self.fake_engine("ok"))
        self.assertTrue(response["completed"])
        self.assertEqual(evidence, {"python -m unittest test_form"})

    def test_shell_wrapped_evidence_requires_whole_command_not_substring(self):
        wrapped = '\"C:/Program Files/PowerShell/7/pwsh.exe\" -NoProfile -Command \'python -m unittest test_form\''
        self.assertEqual(a.command_evidence(wrapped), {wrapped, "python -m unittest test_form"})
        combined = "bash -lc 'echo start; python -m unittest test_form'"
        self.assertNotIn("python -m unittest test_form", a.command_evidence(combined))
        self.assertEqual(a.command_evidence("unterminated '"), {"unterminated '"})

    def test_engine_failure_and_timeout_cannot_return_success(self):
        for mode in ("fail", "timeout"):
            with self.subTest(mode=mode), contextlib.redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
                a.run_engine("요청", self.project, 1, self.fake_engine(mode))

    def test_management_cwd_before_and_after_subcommand(self):
        for args in (["learn", "--cwd", self.project, "status"], ["learn", "status", "--cwd", self.project]):
            self.assertEqual(a.parser().parse_args(args).cwd, self.project)


if __name__ == "__main__":
    unittest.main()
