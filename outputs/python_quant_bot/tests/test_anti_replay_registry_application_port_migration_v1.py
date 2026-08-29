from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import unittest

from exchange_terminal.application import (
    anti_replay_registry_identity_preregistration_v1 as identity_v1,
)
from exchange_terminal.application import (
    anti_replay_registry_organization_identity_evidence_bundle_verification_envelope_v1 as verification_v1,
)
from exchange_terminal.application import (
    anti_replay_registry_organization_identity_intake_preregistration_v1 as intake_v1,
)
from exchange_terminal.application import (
    anti_replay_registry_signer_source_trust_preregistration_v1 as signer_v1,
)
from exchange_terminal.application import (
    source_baseline_nonce_anti_replay_provider_conformance_plan_v2 as plan_v2,
)
from exchange_terminal.application.ports import anti_replay_registry_v1 as canonical_v1
from exchange_terminal.interfaces import anti_replay_registry as legacy_v1
from exchange_terminal.interfaces import anti_replay_registry_v2 as legacy_v2
from exchange_terminal.services.strict_canonical_json_hash import strict_canonical_hash


ROOT = Path(__file__).resolve().parents[1]
APPLICATION_ROOT = ROOT / "exchange_terminal" / "application"
CANONICAL_PATH = APPLICATION_ROOT / "ports" / "anti_replay_registry_v1.py"
LEGACY_PATH = ROOT / "exchange_terminal" / "interfaces" / "anti_replay_registry.py"
IDENTITY_PATH = APPLICATION_ROOT / "anti_replay_registry_identity_preregistration_v1.py"
INTAKE_PATH = (
    APPLICATION_ROOT
    / "anti_replay_registry_organization_identity_intake_preregistration_v1.py"
)
SIGNER_PATH = (
    APPLICATION_ROOT
    / "anti_replay_registry_signer_source_trust_preregistration_v1.py"
)
VERIFICATION_PATH = (
    APPLICATION_ROOT
    / "anti_replay_registry_organization_identity_evidence_bundle_verification_envelope_v1.py"
)
PLAN_PATH = APPLICATION_ROOT / "source_baseline_nonce_anti_replay_provider_conformance_plan_v2.py"
CONSUMER_PATH = IDENTITY_PATH
CANONICAL_MODULE = "exchange_terminal.application.ports.anti_replay_registry_v1"
LEGACY_MODULE = "exchange_terminal.interfaces.anti_replay_registry"
CANONICAL_SHA256 = "5eed523c3665e687c6d2f202afcea5cc93bcdee3ef4ee942a7d4f76364f380a0"
H1 = "d21e6864245ccb054329160ca49b2c5b725d6b86c262f0f0728c018b8c5d035f"
H2 = "3d9ce854b1e3f9bc29ce654d189be3c975796d9a4f5a7c7e72ade715f816ef56"
H3 = "12565b61f7984e87821f5abb86edd005436b5214f527549a93c011cb158cd51c"
H5 = "c51984b8e15d7847a46d9d452ab099ca954bd11cadccad1d510fdc2539f9c05d"
H6 = "cb48118f7791f7eb466d8fdc8da3235d568fe2a1a61def7c14df7709c8ad5792"
EVALUATION_HASH = "fec30c1e6433db5ea67c7e2a222e3c74cfd7fac8757461f579ccc7ee6d6fa055"
CROSS_RUNTIME_PROVENANCE_CLOSURE_SHA256 = {
    'exchange_terminal/application/source_baseline_nonce_anti_replay_provider_conformance_presentation_consumer_preregistration_v1.py': '7ff64216e70dcedd43b86210cfac68b632c1eb7bc10a390bec9d4ffb619ac572',
    'exchange_terminal/services/source_baseline_provider_conformance_application_load_descriptor_preregistration_v1.py': '9bcd1f37f8c0ef85ddcfffed65dd1104b7317567e69972ad1469cf55886e7ae5',
    'exchange_terminal/services/source_baseline_provider_conformance_in_memory_delivery_adapter_registration_v1.py': '64013da2f26d49ec1f0ee17b8abee5b061e0f9007c448bc02e0fa18766be46e8',
    'exchange_terminal/services/source_baseline_provider_conformance_in_memory_payload_delivery_adapter_v1.py': 'b6251351e821a455fa781c55d12a41db2ce03e576cbfca6dc78c4a4b767a0ee7',
    'exchange_terminal/services/source_baseline_provider_conformance_presentation_consumer_registration_v1.py': '948aaa77ea86658732226d2ed4d4c585a625ba409b946ef1f79fac58f0a883fe',
    'exchange_terminal/services/source_baseline_provider_conformance_presentation_consumer_registration_v2.py': '160e680e2ad94e281ee4bbe5c22e610c24837c6ec382b93a40408eb15d2d772a',
    'exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v8.py': '7d20b84dd84c7afd228fddedc4510bfb022889b4e488d58ff1e2026f2f1fbe47',
    'exchange_terminal/services/strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v9.py': 'e59e2d88f18d104ea08609b90d775e2d1e4c981040a6de326ed068755f865ab5',
    'exchange_terminal/static/evidence_anti_replay_registry_ed25519_key_possession_candidate_v1.js': 'aab58710d8cc2bf81f66e2daf8f562e1310ab591542a328b00c23ebdc102bdaf',
    'exchange_terminal/static/evidence_anti_replay_registry_gap_projection_v1.js': '021a4618caf5968057b13dd744918bf059d2a756eb47fe4cc1a55b538de1ca7d',
    'exchange_terminal/static/evidence_anti_replay_registry_gap_projection_v2.js': 'ab755cd4579dc5bc7855c54f4625862e9ff3203179303057a23d80f613ab2677',
    'exchange_terminal/static/evidence_anti_replay_registry_organization_identity_signed_artifact_bundle_aggregation_candidate_v1.js': '5a1df11be56fcb641d1d04dc0397a94bd22a8c08ea632cd0cf4eb5d9c9754a0f',
    'exchange_terminal/static/evidence_anti_replay_registry_organization_identity_signed_artifact_bundle_aggregation_candidate_v1.test.js': 'fa428b5e916563da659f0ae1f82db34aaa63ed6df2b71ef6fbcf661c4f045429',
    'exchange_terminal/static/evidence_source_baseline_provider_conformance_card_v1.js': '88a1ac27eaefd554e82129a5b2883d14af365965559d1d0e84db8dc32b1d9a5a',
    'exchange_terminal/static/evidence_source_baseline_provider_conformance_card_v1.test.js': 'e64ec0abd375c6fdda4dde9032b2a79b9535173b25a255cdd20c27e31b1d65a6',
    'exchange_terminal/static/evidence_source_baseline_provider_conformance_in_memory_delivery_adapter_v1.js': '46679b99d3c9c93529d6917960d4dbebc6caffe4b9053826f061cdd7877ab8ed',
    'exchange_terminal/static/evidence_source_baseline_provider_conformance_style_preregistration_v1.js': 'ff06b47a7832a46a7092f5dba4b64401e56b0e6f7562420d2a505bf79bda6ff0',
    'exchange_terminal/static/evidence_source_baseline_provider_conformance_style_preregistration_v1.test.js': '7216175fc3dbbc5efde9767df7ffc43ad3a9f991598ae4bc4101b89bf8704d8b',
}
STALE_PROVENANCE_SHA256 = (
    '02f291f5b759f4175bc1916cadd60eece48c598aa721ec6172f210047c5a9cb7',
    '05b2f4657770d8f7a4e2d13f9ed62f2895c55c96b9514be3626b8a2b90dd65de',
    '0c2d3e9fe1a2c8bd784fb26eea9f9406ec6f8f29ac6b9c13718044ec2727801e',
    '1cda4f6e32fffe21fb2361d77d507ec5cacadecce69347cdef069571ce6a2cf5',
    '210b7eb2976ae086afa80c6bfbb06ba6159643af2f1dca86cbb8237e10a03dfd',
    '213c6bf716440ab36e4d9f0d723f27d132fc522a634a068155cf75c04506b6d9',
    '2d9030f46ab9a9fd08d3007e636dfefe77d9f2dce6f802800f7d77542c556713',
    '2fe336f378cea8da7078d63d15c7d076e5020c24e0c5305bb4bda030dfe262bc',
    '3437cd17f828ec8574e852e050e17e615c6cb439e56f3c243cb16965cf78022b',
    '3565768aaaf0a5aebeeb3eb440eec747121e3d219958259c842e4eaac3bd4bf3',
    '3e79eb28750e46582bcac4e0fcd46b0c112e737af0dee7a33a62f9cb3662dc8a',
    '44a7dc5b310bc0fbaa842d5e460cc6fa1b9df59fe2ff1545d4a51f9d301aacc7',
    '494657af7f34fbf36a52ad873f8bc86a9107ba87f34e36081cf05de9d7d4805f',
    '512f442fc03b5982b9c5a6078d91b77defebf665bf79f841e40cbe38a9642aeb',
    '5a6e3abd4bc9ca32e86363aaf612820b5aa84aacf90333bdbfe4b969c4116eea',
    '5ed8148bb598bffd57ac4fd47af7b11364d8910764a3d0e099b69d80284173eb',
    '5ef04e50e452575447e432931f2513a37a763ec28781b7f842fff5aef203cf9f',
    '60c1e795f7ba337e6d56161a00cfd70d8738d4d55328bc3df1f36b42aaff46ce',
    '67e5e807c71bd35809e2897c32617c3d2ef6e189320f8341ae155a7ea059ad8e',
    '6b6f49e609361ab0858f82a2d099805b4faf5c619b1cc0889f7784b8004c3167',
    '6d67400e11c8f8778094820a9c2e8c92738f3cc10456aa0bd07070dbbf3e6caf',
    '70c2286c23b994872efc65eaa77243ac14f798f2a71e5e2b68a71dc5fcc92e3d',
    '72d9725c128f2d288ba15c9e8d18c675743fa5accfcb838fd78b74c181a98615',
    '736fdf3bddbe73187cc1cd7dec4538f828e384b7205414cb37764cab7b4e4f84',
    '79ba38c53fce6ee01e59bb99936969605b45f5eeeb36fe8e017a4457b646c24d',
    '7b762ab95588fd7851c3e70e3bc675d6e604c0c0141a0c96c762de8ac05568e8',
    '7bffac083b59224eff7ed4e55df641255f985a89fb78c4d59d2b996f0c66cd24',
    '805bdd042a962cac24cd92510f619601df6b6616c207238510b621cd114614ae',
    '82a5f05e26924c7917f359dd251c92fed392bb9dc5745643e81302b39988f1b3',
    '82ce7462389fca1e26021ec00232ebcef85b5b2c8d884fc776fa7948d38403b9',
    '85dd169c2b6c182b6de57aab1ca481ba7ef7899b13c3e85218ba0606694a75d4',
    '8b4f33c5a7108147bf0224fc0cfd6bf335150b88c6ba4973d885b8a5fbd5d342',
    '9053e58f9188811255ceaac0e2338f581702673789f53c4aceb3936e3ff6b4a2',
    '998f3d9b79e950f9c9c8f05a14daf146284c048f9850eb0563e7da247afd55f7',
    'a05a082a8497afbab7212a3ca84fcbda25db874ff1ccae4544ec8469dc5f15c0',
    'a22fcbe46c6ac13191593315b26214f2c9d423581030fe01c18a60919a4faac5',
    'a3c0075c5df6ec8451bc31b43932ea67a0a9075b071ef851b3c177167a10131e',
    'a43272b95120ff5dcc48eb10d8947df1b14c05e36cb9bdcd7814a036e9b7874c',
    'a826bd47f8a7783ec94937a4ca3a222f9392a2bc34a8cd613ef0457b0fec7e79',
    'aae33d9250af14b3e59ce22dda01867f09529114028cf22b08e41888e6f38903',
    'ae37c4e78ebb6c7b16228bea72260bab62442036734643170590f972fc07680e',
    'b5244e1cf078d3b85f89c26e3b87469613fce2a8f27ce2667984082995e50282',
    'b58e1444079931f6ae7e9e5ddf02e05c46a0482480780d34acee7154503e898d',
    'b66e3f865712f83999cc730fafdfa0c0e805386bd4da196b23b3c88236dfc4a2',
    'b9120bf9bb9e6aee710cad30ac6ecec13dd9ef6a4efbe9b62a6f6d9b59f34103',
    'bb2fef43aeee234b7dc99a333c84f7d75383958b1b298dbf9fd9a4a522f02822',
    'be15777ef011634003e4da789670ef772607f3c76f02c85314580c238ee40022',
    'beed220058c1459a305123dc8326ee4bbefb8ee8386e76ffc9c6660c9111c3d9',
    'c044831b8ff2781e6b1bab8f85f2f3a4472e074cfd45c454091f086f1e1e34db',
    'c2d7ff70ec800369b1f3ad5653fc5e5fb6faa4d12b12e13dd4d79e4f5ac62b37',
    'c6e30a4b723fa77b5a4d6931b02230d01a82cbd9943012e79c8de2ec4242cead',
    'c75f0ac1b207d3850b041fdf76d5a7577c2773e7ba1233b75a642155b382fc0a',
    'c98d89b5ec9e75bf54ee1f8175776f4fc6d529aa871bc17efbe663fc9d8a3ea7',
    'ca4cd2156cb1e9dfe2f2a803e62fdb6787be5616acc39f3eb5049436e2563560',
    'ccce91ed39361acdccf9bc0ae3e9d9b8bb3d29a2863fee86c42ac652bc2ce535',
    'd1eb5f3885f2498f08ab4e34ac825423618534283beb51b6989fdb34daddd91c',
    'd3dc913ce5e218b65543b152a56e52b432aed7e25e17e91492db19e61f05aef4',
    'deed34be94846ab36610ca09f02f26df237ebf1b5cbddfe4beb1dfd79e68cec2',
    'e247b9b67c4184d6af68ed4d44d82be431fc1f6cc77154a8eb3c0fb497db5db2',
    'e45dd2a01df2b063cc6b7d84cff94c25910ddd4aec0721647acd2dd882203086',
    'e557c9b0e08e2a78cf700e55556832e6fd38339fc42dc0f216596ef697b13cd2',
    'e824c7a740d6b5ad1706d5869f436b5e81458b79d11506c5bbbf42a03947426e',
    'eb929e30ab747e0577eb0cd1074d186200cff91ac307d9f9278983d236d37361',
    'ef7e050dd9719f3dc4c159e3656dbb1891c26ae1d24b4a9036c5baf163140de4',
    'f9653a567cf1f9bb3a819b796c41f06723e2ce3195142651c9114ce75937f797',
    'fe432d3ed3f0f94be0af203a1198e8094ed0d04c2c2da78628638d9781781e85',
)

DOCUMENT_SEAL_CLOSURE_SHA256 = {
    'consumer_preregistration_hash': '42b4c9830844c455b05c4952a7010655534048f73cf78f9f7ab574bebbddca5d',
    'consumer_registration_v1_hash': '217e4b759b993f3f513b989b79c380f7e192c799872e3f6959116171cc83d036',
    'style_preregistration_hash': 'c8a882d9960d3c37f86d398304f827cf92bb741a229f33eed6abb96f4b8dccb5',
    'consumer_registration_v2_hash': 'ab663f22c980f850b8440b8844909930d7a1a72f27245b26826c45c2000e7c64',
    'load_descriptor_hash': 'a842fe43de8b8c2b7bdd2c2978dfb4d09f03ca49aa8555d2ab3edcbe7cdbd7b2',
    'delivery_adapter_registration_hash': 'db9981006de952321e72973fe2c7e981e5d3b23450e2b2437613c5d2573e6e3f',
}
PUBLIC_NAMES = (
    "ANTI_REPLAY_NAMESPACE",
    "COMPARE_AND_CONSUME_COMMAND_SCHEMA_VERSION",
    "COMPARE_AND_CONSUME_RESULT_SCHEMA_VERSION",
    "CONSUMPTION_REQUEST_SCHEMA_VERSION",
    "TARGET_CONSUMPTION_RECEIPT_SCHEMA_VERSION",
    "AntiReplayCompareAndConsumeCommandV1",
    "AntiReplayCompareAndConsumeResultV1",
    "AntiReplayRegistryOutcomeV1",
    "AntiReplayRegistryPortV1",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _import_targets(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            targets.append(node.module)
        elif isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
    return targets


def _command_kwargs() -> dict[str, str]:
    scope_hash = "a" * 64
    consumption_key = strict_canonical_hash(
        {
            "anti_replay_namespace": canonical_v1.ANTI_REPLAY_NAMESPACE,
            "anti_replay_scope_hash": scope_hash,
        }
    )
    return {
        "anti_replay_scope_hash": scope_hash,
        "attestation_hash": "b" * 64,
        "challenge_hash": "c" * 64,
        "consumption_key": consumption_key,
        "issuance_preregistration_hash": "d" * 64,
        "policy_hash": "e" * 64,
        "request_hash": "f" * 64,
        "witness_id": "synthetic.witness",
        "witness_verification_hash": "1" * 64,
    }


class AntiReplayRegistryApplicationPortMigrationV1Tests(unittest.TestCase):
    def test_canonical_port_preserves_pre_migration_bytes(self):
        self.assertEqual(_sha256(CANONICAL_PATH), CANONICAL_SHA256)

    def test_canonical_port_has_no_interfaces_dependency(self):
        self.assertFalse(
            [
                target
                for target in _import_targets(CANONICAL_PATH)
                if target.startswith("exchange_terminal.interfaces.")
            ]
        )

    def test_legacy_shim_pins_canonical_module_and_hash(self):
        self.assertEqual(legacy_v1.CANONICAL_PORT_MODULE, CANONICAL_MODULE)
        self.assertEqual(
            legacy_v1.CANONICAL_PORT_IMPLEMENTATION_SHA256,
            CANONICAL_SHA256,
        )

    def test_legacy_public_contract_objects_are_exact_canonical_objects(self):
        for name in PUBLIC_NAMES:
            with self.subTest(name=name):
                self.assertIs(getattr(legacy_v1, name), getattr(canonical_v1, name))

    def test_legacy_shim_defines_no_duplicate_class_or_function(self):
        tree = ast.parse(LEGACY_PATH.read_text(encoding="utf-8"))
        definitions = [
            node.name
            for node in tree.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        self.assertEqual(definitions, [])
        self.assertIn(CANONICAL_MODULE, _import_targets(LEGACY_PATH))

    def test_legacy_constructed_command_is_a_canonical_command(self):
        command = legacy_v1.AntiReplayCompareAndConsumeCommandV1(**_command_kwargs())
        self.assertIsInstance(
            command,
            canonical_v1.AntiReplayCompareAndConsumeCommandV1,
        )

    def test_consumption_key_substitution_remains_fail_closed(self):
        kwargs = _command_kwargs()
        kwargs["consumption_key"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "does not bind namespace and scope"):
            legacy_v1.AntiReplayCompareAndConsumeCommandV1(**kwargs)

    def test_runtime_checkable_protocol_identity_is_preserved(self):
        class Registry:
            registry_id = "synthetic.registry"

            def compare_and_consume(self, command):
                return canonical_v1.AntiReplayCompareAndConsumeResultV1(
                    outcome=canonical_v1.AntiReplayRegistryOutcomeV1.DUPLICATE_REJECTED,
                    request_hash=command.request_hash,
                    consumption_key=command.consumption_key,
                    registry_id=self.registry_id,
                    registry_revision=0,
                )

        registry = Registry()
        self.assertIsInstance(registry, canonical_v1.AntiReplayRegistryPortV1)
        self.assertIsInstance(registry, legacy_v1.AntiReplayRegistryPortV1)

    def test_v2_interface_receives_exact_canonical_v1_outcome_identity(self):
        self.assertIs(
            legacy_v2.AntiReplayRegistryOutcomeV1,
            canonical_v1.AntiReplayRegistryOutcomeV1,
        )

    def test_application_consumer_uses_canonical_port(self):
        targets = _import_targets(CONSUMER_PATH)
        self.assertIn(CANONICAL_MODULE, targets)
        self.assertNotIn(LEGACY_MODULE, targets)

    def test_direct_application_to_interfaces_import_statements_remain_at_most_six(self):
        edges: list[tuple[str, str]] = []
        for path in sorted(APPLICATION_ROOT.rglob("*.py")):
            for target in _import_targets(path):
                if target.startswith("exchange_terminal.interfaces."):
                    edges.append((path.relative_to(APPLICATION_ROOT).as_posix(), target))
        self.assertLessEqual(len(edges), 6)
        self.assertFalse([edge for edge in edges if edge[1] == LEGACY_MODULE])

    def test_schema_and_namespace_constants_are_unchanged(self):
        self.assertEqual(
            canonical_v1.COMPARE_AND_CONSUME_COMMAND_SCHEMA_VERSION,
            "anti-replay-compare-and-consume-command-v1",
        )
        self.assertEqual(
            canonical_v1.COMPARE_AND_CONSUME_RESULT_SCHEMA_VERSION,
            "anti-replay-compare-and-consume-result-v1",
        )
        self.assertEqual(
            canonical_v1.ANTI_REPLAY_NAMESPACE,
            "portfolio-risk-downside-tail-post-registration-execution-receipt-v5",
        )

    def test_provenance_closure_matches_current_canonical_files(self):
        self.assertEqual(_sha256(IDENTITY_PATH), H1)
        self.assertEqual(_sha256(INTAKE_PATH), H2)
        self.assertEqual(_sha256(SIGNER_PATH), H3)
        self.assertEqual(_sha256(VERIFICATION_PATH), H5)
        self.assertEqual(_sha256(PLAN_PATH), H6)
        self.assertEqual(intake_v1.IDENTITY_PREREGISTRATION_IMPLEMENTATION_SHA256, H1)
        self.assertEqual(signer_v1.IDENTITY_PREREGISTRATION_IMPLEMENTATION_SHA256, H1)
        self.assertEqual(signer_v1.INTAKE_PREREGISTRATION_IMPLEMENTATION_SHA256, H2)
        self.assertEqual(verification_v1.IDENTITY_PREREGISTRATION_IMPLEMENTATION_SHA256, H1)
        self.assertEqual(verification_v1.INTAKE_PREREGISTRATION_IMPLEMENTATION_SHA256, H2)
        self.assertEqual(
            verification_v1.BUNDLE_EVALUATION_IMPLEMENTATION_SHA256,
            EVALUATION_HASH,
        )
        self.assertEqual(plan_v2.IDENTITY_PREREGISTRATION_V1_IMPLEMENTATION_SHA256, H1)
        self.assertEqual(
            plan_v2.ORGANIZATION_IDENTITY_INTAKE_V1_IMPLEMENTATION_SHA256,
            H2,
        )
        self.assertEqual(plan_v2.SIGNER_SOURCE_TRUST_V1_IMPLEMENTATION_SHA256, H3)

    def test_document_seal_closure_matches_current_producers(self):
        from importlib import import_module

        preregistration_v1 = import_module(
            "exchange_terminal.application."
            "source_baseline_nonce_anti_replay_provider_conformance_"
            "presentation_consumer_preregistration_v1"
        )
        registration_v1 = import_module(
            "exchange_terminal.services."
            "source_baseline_provider_conformance_presentation_consumer_"
            "registration_v1"
        )
        registration_v2 = import_module(
            "exchange_terminal.services."
            "source_baseline_provider_conformance_presentation_consumer_"
            "registration_v2"
        )
        load_descriptor_v1 = import_module(
            "exchange_terminal.services."
            "source_baseline_provider_conformance_application_load_"
            "descriptor_preregistration_v1"
        )
        adapter_registration_v1 = import_module(
            "exchange_terminal.services."
            "source_baseline_provider_conformance_in_memory_delivery_"
            "adapter_registration_v1"
        )

        self.assertEqual(
            preregistration_v1.
            build_source_baseline_provider_conformance_presentation_consumer_preregistration_v1()[
                "consumer_preregistration_hash"
            ],
            DOCUMENT_SEAL_CLOSURE_SHA256["consumer_preregistration_hash"],
        )
        self.assertEqual(
            registration_v1.
            build_source_baseline_provider_conformance_presentation_consumer_registration_v1()[
                "consumer_registration_hash"
            ],
            DOCUMENT_SEAL_CLOSURE_SHA256["consumer_registration_v1_hash"],
        )
        self.assertEqual(
            registration_v2.STYLE_PREREGISTRATION_HASH,
            DOCUMENT_SEAL_CLOSURE_SHA256["style_preregistration_hash"],
        )
        self.assertEqual(
            registration_v2.
            build_source_baseline_provider_conformance_presentation_consumer_registration_v2()[
                "consumer_registration_hash"
            ],
            DOCUMENT_SEAL_CLOSURE_SHA256["consumer_registration_v2_hash"],
        )
        self.assertEqual(
            load_descriptor_v1.
            build_source_baseline_provider_conformance_application_load_descriptor_preregistration_v1()[
                "load_descriptor_hash"
            ],
            DOCUMENT_SEAL_CLOSURE_SHA256["load_descriptor_hash"],
        )
        adapter_document = (
            adapter_registration_v1.
            build_source_baseline_provider_conformance_in_memory_delivery_adapter_registration_v1()
        )
        adapter_hashes = tuple(
            value
            for key, value in adapter_document.items()
            if key.endswith("_hash")
        )
        self.assertEqual(
            adapter_hashes,
            (DOCUMENT_SEAL_CLOSURE_SHA256["delivery_adapter_registration_hash"],),
        )
    def test_cross_runtime_provenance_closure_is_current(self):
        for relative, expected_hash in CROSS_RUNTIME_PROVENANCE_CLOSURE_SHA256.items():
            path = ROOT / relative
            with self.subTest(relative=relative):
                self.assertEqual(_sha256(path), expected_hash)
                source = path.read_text(encoding="utf-8")
                for stale_hash in STALE_PROVENANCE_SHA256:
                    self.assertNotIn(stale_hash, source)

    def test_migration_grants_no_execution_authority(self):
        source = CANONICAL_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "live_order_allowed",
            "paper_authorized",
            "runtime_gate_activation_allowed",
            "writer_allowed",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()