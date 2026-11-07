"""Actual pinned protobuf/private workers plus owned TCP; synthetic business values."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time
import unittest


spec_path = Path(sys.argv[1]).resolve(strict=True)
specification = json.loads(spec_path.read_text(encoding="utf-8"))
bootstrap_path = Path(specification["bootstrap"]).resolve(strict=True)
assert sha256(bootstrap_path.read_bytes()).hexdigest() == specification["bootstrap_sha256"]
assert sha256(Path(__file__).read_bytes()).hexdigest() == specification["controller_sha256"]
loader_spec = importlib.util.spec_from_file_location("actual_quote_bootstrap", bootstrap_path)
bootstrap_module = importlib.util.module_from_spec(loader_spec)
loader_spec.loader.exec_module(bootstrap_module)
runtime, bindings, private_proof = bootstrap_module.bootstrap(spec_path)
output = Path(specification["output_root"])

from tests.test_terminal_broker_quote_integration import QuoteChainChecks


def child_prelude(endpoint, case_root):
    return "\n".join([
        "import importlib.util",
        "from hashlib import sha256",
        "boot=Path(" + repr(str(bootstrap_path)) + ")",
        "assert sha256(boot.read_bytes()).hexdigest()==" + repr(specification["bootstrap_sha256"]),
        "s=importlib.util.spec_from_file_location('actual_quote_bootstrap',boot)",
        "b=importlib.util.module_from_spec(s);s.loader.exec_module(b)",
        "RUNTIME_IDENTITY,PROTOBUF_BINDINGS,ACTUAL_PROOF=b.bootstrap(" + repr(str(spec_path)) +
            ",endpoint=" + repr(endpoint) + ",case_root=" + repr(str(case_root)) + ")",
    ])


class ActualQuoteWorkerTests(QuoteChainChecks, unittest.TestCase):
    actual_context = dict(runtime_identity=runtime, bindings=bindings,
        interpreter=str(Path(sys.executable).resolve()), child_prelude=child_prelude,
        authorize_child_command=private_proof.authorize_child_command)

    def tearDown(self):
        # Settle only our own process handles before copying raw SQLite/files.
        # A failure receipt is never rewritten into a successful receipt.
        self.worker.close_handles()
        destination = output / "cases" / self._testMethodName
        destination.mkdir(parents=True)
        for label, root in (("case-root", self.root), ("supervisor-root", self.worker.root)):
            shutil.copytree(root, destination / label)
        peer = self.peer
        peer_record = dict(endpoint=peer.endpoint, accepts=len(peer.clients),
            accepted_client_addresses=peer.accepted_addresses, errors=peer.errors,
            received_frames=[dict(bytes=len(frame), sha256=sha256(frame).hexdigest(), hex=frame.hex()) for frame in peer.frames],
            sent_response_frames=[dict(bytes=len(frame), sha256=sha256(frame).hexdigest(), hex=frame.hex()) for frame in peer.sent_frames],
            protocol_layer=self.layer, synthetic_values=True, scenario_notes=self.scenario_notes)
        (destination / "peer-record.json").write_text(json.dumps(peer_record, indent=2), encoding="utf-8")
        file_hashes = {path.relative_to(destination).as_posix(): sha256(path.read_bytes()).hexdigest()
                      for path in sorted(destination.rglob("*")) if path.is_file()}
        (destination / "SHA256.json").write_text(json.dumps(file_hashes, indent=2), encoding="utf-8")


start = time.monotonic()
try:
    chosen = specification.get("case_names")
    suite = (unittest.TestSuite(ActualQuoteWorkerTests(name) for name in chosen) if chosen else
             unittest.defaultTestLoader.loadTestsFromTestCase(ActualQuoteWorkerTests))
    with (output / "actual-tests.log").open("x", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    proof = private_proof()
    proof.update(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skipped=len(result.skipped), seconds=time.monotonic() - start,
        status="PASS_ACTUAL_PROTOBUF_ORIGINAL_WORKER_OWNED_TCP" if result.wasSuccessful() else "FAIL_PRESERVE_ORIGINALS",
        test_case_names=chosen or unittest.defaultTestLoader.getTestCaseNames(ActualQuoteWorkerTests),
        diagnostic_subset=bool(chosen),
        future_case_scope="EXPLICIT_FUTURE_RECEIVED_AT_REPROJECTION_NOT_NETWORK_DELAY",
        registry_scope="TEST_ONLY_PREBOUND_ORIGINAL_FRAME_REGISTRY_NOT_A_PRODUCTION_LEDGER",
        package_bootstrap_scope="CURRENT_SOURCE_TEST_ASSEMBLY_NOT_R7_FEATURE_OR_PRODUCTION_BOOTSTRAP_ACCEPTANCE")
    (output / "result.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    print(json.dumps({key: proof[key] for key in ("status", "tests_run", "failures", "errors", "skipped", "seconds")}), flush=True)
finally:
    (output / "guard-final.json").write_text(json.dumps(private_proof(), indent=2), encoding="utf-8")
raise SystemExit(not result.wasSuccessful())
