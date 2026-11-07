"""Read-only rendering checks; no server, workspace or economic run is created."""
from hashlib import sha256
from pathlib import Path
import unittest

from exchange_terminal.services import quant_workspace as quant


class CoreCompletionRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = quant._verified_package_root(quant._VENDOR)
        cls.path = cls.root / "resources" / "desktop.html"
        cls.raw = cls.path.read_bytes()

    def test_rendered_adapter_preserves_the_verified_frozen_package(self):
        before = sha256(self.raw).hexdigest()
        html = quant.render_quant_html(self.raw, "synthetic-session-token", "synthetic-nonce").decode()
        self.assertIn("coreCompletion.confirm(action,job.result);announce", html)
        self.assertIn("await coreCompletion.present(onSuccess,job.result,action)", html)
        self.assertIn("return coreCompletion.operationError(action,job,e", html)
        self.assertIn("catch(e){coreCompletion.readFailure('refresh',e);}", html)
        self.assertIn("return coreCompletion.loadRun(id,quiet)", html)
        self.assertIn("${coreCompletion.resultPlaceholder(id)}", html)
        self.assertLess(html.index("const coreCompletion=window.createCoreCompletionAdapter"),
                        html.index("$('#navigation').innerHTML="))
        self.assertEqual(html.count("synthetic-session-token"), 1)
        self.assertIn("terminal_preflight", quant._READ_RESOURCES)
        self.assertEqual(sha256(self.path.read_bytes()).hexdigest(), before)
        self.assertEqual(quant._verified_package_root(quant._VENDOR), self.root)

    def test_frozen_function_drift_and_duplicate_are_rejected_before_adaptation(self):
        text = self.raw.decode().replace("\r\n", "\n")
        for name in quant._CORE_PRESENTATION_FUNCTIONS:
            with self.subTest(function=name):
                changed = text.replace("function " + name + "(", "function " + name + "( ", 1)
                with self.assertRaisesRegex(ValueError, "quant_core_completion_adapter_source_mismatch"):
                    quant.render_quant_html(changed.encode(), "token", "nonce")
        duplicate = text + "\n" + next(line for line in text.splitlines() if line.startswith("async function loadRun("))
        with self.assertRaisesRegex(ValueError, "quant_core_completion_adapter_source_mismatch"):
            quant.render_quant_html(duplicate.encode(), "token", "nonce")

    def test_crlf_normalization_keeps_the_same_rendered_function_contract(self):
        text = self.raw.decode().replace("\r\n", "\n")
        self.assertEqual(quant.render_quant_html(text.encode(), "token", "nonce"),
                         quant.render_quant_html(text.replace("\n", "\r\n").encode(), "token", "nonce"))


if __name__ == "__main__":
    unittest.main()
