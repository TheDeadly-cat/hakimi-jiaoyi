from __future__ import annotations

from copy import deepcopy
import hashlib
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services import immutable_artifact_bundle
from exchange_terminal.services.immutable_artifact_bundle import (
    ArtifactBundleByteLimitExceeded,
    ArtifactBundleError,
    DEFAULT_BUNDLE_MANIFEST_FILE,
    build_content_addressed_bundle_manifest,
    bundle_manifest_bytes,
    publish_immutable_artifact_bundle,
    read_bounded_artifact,
    read_immutable_artifact_bundle,
    validate_exact_basenames,
    verify_content_addressed_bundle_manifest,
    windows_safe_basename_identity,
)


def sample_members() -> dict[str, bytes]:
    return {
        "pack.json": b'{"pack":true}\n',
        "research-source.json": b'{"source":true}\n',
    }


def sample_roles() -> dict[str, str]:
    return {
        "pack.json": "PACK",
        "research-source.json": "RESEARCH_SOURCE",
    }


class ImmutableArtifactBundleTests(unittest.TestCase):
    def test_windows_safe_exact_basename_rejects_alias_and_path_forms(self) -> None:
        valid = (
            "pack.json",
            "evidence-20260814.json",
            ".private-member",
            "研究证据.json",
        )
        invalid = (
            "",
            ".",
            "..",
            "../pack.json",
            "folder/pack.json",
            "folder\\pack.json",
            "C:\\pack.json",
            "\\\\server\\share\\pack.json",
            "pack.json:stream",
            "pack.json.",
            "pack.json ",
            "CON",
            "con.txt",
            "COM1.json",
            "Lpt9",
            "pack?.json",
            "pack\x00.json",
            "ｅvidence.json",  # NFKC alias of ASCII characters.
            "／.json",  # Full-width slash normalises to a path separator.
        )
        for name in valid:
            with self.subTest(name=name):
                self.assertIsNotNone(windows_safe_basename_identity(name))
        for name in invalid:
            with self.subTest(name=name):
                self.assertIsNone(windows_safe_basename_identity(name))

    def test_member_names_reject_casefold_duplicates_and_manifest_alias(self) -> None:
        duplicate = validate_exact_basenames(["Pack.json", "pack.JSON"])
        reserved = validate_exact_basenames(
            ["MANIFEST.JSON"],
            reserved_names=(DEFAULT_BUNDLE_MANIFEST_FILE,),
        )

        self.assertEqual(duplicate["status"], "BLOCK")
        self.assertIn("artifact_bundle_member_basename_duplicate", duplicate["blockers"])
        self.assertEqual(reserved["status"], "BLOCK")
        self.assertIn("artifact_bundle_member_basename_reserved", reserved["blockers"])

    def test_bounded_reader_accepts_exact_limit_and_reads_only_limit_plus_one(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "member.bin"
            path.write_bytes(b"abcdef")

            self.assertEqual(read_bounded_artifact(path, byte_limit=6), b"abcdef")
            real_read = os.read
            requested: list[int] = []

            def tracked_read(descriptor: int, amount: int) -> bytes:
                requested.append(amount)
                return real_read(descriptor, amount)

            with patch.object(immutable_artifact_bundle.os, "read", side_effect=tracked_read):
                with self.assertRaises(ArtifactBundleByteLimitExceeded) as raised:
                    read_bounded_artifact(path, byte_limit=5)

        self.assertEqual(raised.exception.blocker, "artifact_bundle_member_size_limit_exceeded")
        self.assertEqual(sum(requested), 6)

    def test_bounded_reader_rejects_symlink_when_host_supports_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.bin"
            link = root / "link.bin"
            source.write_bytes(b"evidence")
            try:
                link.symlink_to(source)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable on this host: {exc}")
            with self.assertRaises(ArtifactBundleError) as raised:
                read_bounded_artifact(link, byte_limit=64)

        self.assertEqual(
            raised.exception.blocker,
            "artifact_bundle_member_link_or_reparse_forbidden",
        )

    def test_windows_reparse_attribute_is_rejected_without_host_privileges(self) -> None:
        synthetic = SimpleNamespace(
            st_mode=stat.S_IFREG,
            st_file_attributes=0x0400,
        )
        self.assertTrue(
            immutable_artifact_bundle._path_is_link_or_reparse(
                Path("synthetic-member.bin"),
                synthetic,
            )
        )

    def test_manifest_is_deterministic_content_addressed_and_strict(self) -> None:
        members = sample_members()
        first = build_content_addressed_bundle_manifest(
            members,
            member_roles=sample_roles(),
            bindings={"family": "synthetic", "revision": 1},
        )
        reversed_members = dict(reversed(list(members.items())))
        second = build_content_addressed_bundle_manifest(
            reversed_members,
            member_roles=sample_roles(),
            bindings={"revision": 1, "family": "synthetic"},
        )

        self.assertEqual(first, second)
        self.assertEqual(bundle_manifest_bytes(first), bundle_manifest_bytes(second))
        self.assertEqual(verify_content_addressed_bundle_manifest(first)["status"], "PASS")
        self.assertEqual(
            [record["file"] for record in first["members"]],
            ["pack.json", "research-source.json"],
        )

        changed = build_content_addressed_bundle_manifest(
            members,
            member_roles=sample_roles(),
            bindings={"family": "synthetic", "revision": 2},
        )
        self.assertNotEqual(first["bundle_hash"], changed["bundle_hash"])

        forged = deepcopy(first)
        forged["members"][0]["size"] += 1
        verification = verify_content_addressed_bundle_manifest(forged)
        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("artifact_bundle_total_size_mismatch", verification["blockers"])
        self.assertIn("artifact_bundle_hash_invalid", verification["blockers"])

    def test_builder_enforces_member_count_member_size_and_total_before_write(self) -> None:
        cases = (
            (
                {"one.bin": b"1", "two.bin": b"2"},
                {"max_member_count": 1},
                "artifact_bundle_member_count_limit_exceeded",
            ),
            (
                {"one.bin": b"12"},
                {"max_member_bytes": 1},
                "artifact_bundle_member_size_limit_exceeded",
            ),
            (
                {"one.bin": b"12", "two.bin": b"34"},
                {"max_total_bytes": 3},
                "artifact_bundle_total_size_limit_exceeded",
            ),
        )
        for members, limits, blocker in cases:
            with self.subTest(blocker=blocker), self.assertRaises(ArtifactBundleError) as raised:
                build_content_addressed_bundle_manifest(members, **limits)
            self.assertEqual(raised.exception.blocker, blocker)

    def test_publish_writes_manifest_last_fsyncs_and_round_trips_exact_members(self) -> None:
        members = sample_members()
        writes: list[str] = []
        real_writer = immutable_artifact_bundle._write_fsynced_file

        def tracked_writer(path: Path, raw: bytes) -> None:
            writes.append(path.name)
            real_writer(path, raw)

        with tempfile.TemporaryDirectory() as temporary, patch.object(
            immutable_artifact_bundle,
            "_write_fsynced_file",
            side_effect=tracked_writer,
        ), patch.object(
            immutable_artifact_bundle.os,
            "fsync",
            wraps=os.fsync,
        ) as fsync:
            result = publish_immutable_artifact_bundle(
                temporary,
                members,
                member_roles=sample_roles(),
                bindings={"family": "synthetic"},
                bundle_name_prefix="test-bundle",
            )
            loaded = read_immutable_artifact_bundle(
                result["bundle_dir"],
                expected_bundle_hash=result["bundle_hash"],
                expected_manifest_sha256=result["manifest_file_sha256"],
            )

        self.assertEqual(result["status"], "PUBLISHED")
        self.assertTrue(result["published"])
        self.assertEqual(writes[-1], DEFAULT_BUNDLE_MANIFEST_FILE)
        self.assertEqual(set(writes[:-1]), set(members))
        self.assertGreaterEqual(fsync.call_count, len(members) + 1)
        self.assertEqual(loaded["status"], "PASS")
        self.assertEqual(loaded["members"], members)

    def test_custom_manifest_basename_is_preserved_in_receipt_and_reader(self) -> None:
        manifest_file = "bundle-index.json"
        with tempfile.TemporaryDirectory() as temporary:
            result = publish_immutable_artifact_bundle(
                temporary,
                sample_members(),
                member_roles=sample_roles(),
                bundle_name_prefix="custom-manifest-bundle",
                manifest_file=manifest_file,
            )
            loaded = read_immutable_artifact_bundle(
                result["bundle_dir"],
                manifest_file=manifest_file,
                expected_bundle_hash=result["bundle_hash"],
                expected_manifest_sha256=result["manifest_file_sha256"],
            )

        self.assertEqual(result["status"], "PUBLISHED")
        self.assertEqual(result["manifest_file"], manifest_file)
        self.assertEqual(loaded["status"], "PASS")

    def test_identical_retry_is_idempotent_and_conflicting_target_is_not_clobbered(self) -> None:
        members = sample_members()
        with tempfile.TemporaryDirectory() as temporary:
            first = publish_immutable_artifact_bundle(
                temporary,
                members,
                member_roles=sample_roles(),
                bundle_name_prefix="retry-bundle",
            )
            before = {
                path.name: path.read_bytes()
                for path in Path(first["bundle_dir"]).iterdir()
            }
            second = publish_immutable_artifact_bundle(
                temporary,
                members,
                member_roles=sample_roles(),
                bundle_name_prefix="retry-bundle",
            )
            after = {
                path.name: path.read_bytes()
                for path in Path(first["bundle_dir"]).iterdir()
            }

            conflict_manifest = build_content_addressed_bundle_manifest(
                members,
                member_roles=sample_roles(),
            )
            conflict_dir = Path(temporary) / f"conflict-bundle-{conflict_manifest['bundle_hash']}"
            conflict_dir.mkdir()
            sentinel = conflict_dir / "sentinel.txt"
            sentinel.write_bytes(b"preserve")
            conflict = publish_immutable_artifact_bundle(
                temporary,
                members,
                member_roles=sample_roles(),
                bundle_name_prefix="conflict-bundle",
            )
            sentinel_bytes = sentinel.read_bytes()

        self.assertEqual(second["status"], "EXISTING_IDENTICAL")
        self.assertFalse(second["published"])
        self.assertEqual(before, after)
        self.assertEqual(conflict["status"], "BLOCK")
        self.assertIn("target_conflict", conflict["blockers"][0])
        self.assertEqual(sentinel_bytes, b"preserve")

    def test_staging_failure_is_block_and_pending_directory_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, patch.object(
            immutable_artifact_bundle,
            "_write_fsynced_file",
            side_effect=OSError("synthetic write failure"),
        ):
            result = publish_immutable_artifact_bundle(
                temporary,
                sample_members(),
                member_roles=sample_roles(),
                bundle_name_prefix="failure-bundle",
            )
            remaining = list(Path(temporary).iterdir())

        self.assertEqual(result["status"], "BLOCK")
        self.assertFalse(result["published"])
        self.assertEqual(remaining, [])

    def test_cleanup_failure_is_explicit_block(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(
                immutable_artifact_bundle,
                "_write_fsynced_file",
                side_effect=OSError("synthetic write failure"),
            ), patch.object(
                immutable_artifact_bundle.shutil,
                "rmtree",
                side_effect=OSError("synthetic cleanup failure"),
            ):
                result = publish_immutable_artifact_bundle(
                    root,
                    sample_members(),
                    member_roles=sample_roles(),
                    bundle_name_prefix="cleanup-bundle",
                )
            pending = list(root.glob(".pending-*"))
            for path in pending:
                shutil.rmtree(path)

        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(
            result["blockers"],
            ["artifact_bundle_temporary_cleanup_failed"],
        )
        self.assertTrue(pending)

    def test_exact_reader_blocks_tamper_extra_missing_and_stricter_budgets(self) -> None:
        mutations = ("tamper", "extra", "missing")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                result = publish_immutable_artifact_bundle(
                    temporary,
                    sample_members(),
                    member_roles=sample_roles(),
                    bundle_name_prefix=f"{mutation}-bundle",
                )
                bundle = Path(result["bundle_dir"])
                if mutation == "tamper":
                    (bundle / "pack.json").write_bytes(b"forged")
                elif mutation == "extra":
                    (bundle / "extra.json").write_bytes(b"extra")
                else:
                    (bundle / "pack.json").unlink()
                loaded = read_immutable_artifact_bundle(bundle)
            self.assertEqual(loaded["status"], "BLOCK")
            self.assertEqual(loaded["members"], {})

        with tempfile.TemporaryDirectory() as temporary:
            result = publish_immutable_artifact_bundle(
                temporary,
                sample_members(),
                member_roles=sample_roles(),
                bundle_name_prefix="limits-bundle",
            )
            count_block = read_immutable_artifact_bundle(result["bundle_dir"], max_member_count=1)
            member_block = read_immutable_artifact_bundle(result["bundle_dir"], max_member_bytes=5)
            total_block = read_immutable_artifact_bundle(result["bundle_dir"], max_total_bytes=10)

        self.assertEqual(count_block["status"], "BLOCK")
        self.assertIn("count_limit", count_block["blockers"][0])
        self.assertEqual(member_block["status"], "BLOCK")
        self.assertIn("member_size_limit", " ".join(member_block["blockers"]))
        self.assertEqual(total_block["status"], "BLOCK")
        self.assertIn("total_size_limit", " ".join(total_block["blockers"]))

    def test_reader_rejects_member_symlink_and_case_alias_inventory_when_possible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = publish_immutable_artifact_bundle(
                temporary,
                sample_members(),
                member_roles=sample_roles(),
                bundle_name_prefix="links-bundle",
            )
            bundle = Path(result["bundle_dir"])
            member = bundle / "pack.json"
            target = Path(temporary) / "outside.bin"
            target.write_bytes(member.read_bytes())
            member.unlink()
            try:
                member.symlink_to(target)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"symlink unavailable on this host: {exc}")
            loaded = read_immutable_artifact_bundle(bundle)

        self.assertEqual(loaded["status"], "BLOCK")
        self.assertIn("link_or_reparse", " ".join(loaded["blockers"]))

    def test_manifest_duplicate_json_keys_and_noncanonical_serialization_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = publish_immutable_artifact_bundle(
                temporary,
                sample_members(),
                member_roles=sample_roles(),
                bundle_name_prefix="manifest-bundle",
            )
            manifest_path = Path(result["bundle_dir"]) / DEFAULT_BUNDLE_MANIFEST_FILE
            canonical = manifest_path.read_text(encoding="utf-8")
            manifest_path.write_text(
                canonical.replace(
                    '"schema_version":',
                    '"schema_version":"duplicate",\n  "schema_version":',
                    1,
                ),
                encoding="utf-8",
            )
            duplicate = read_immutable_artifact_bundle(result["bundle_dir"])

        self.assertEqual(duplicate["status"], "BLOCK")
        self.assertIn("duplicate_json_key", duplicate["blockers"][0])

        with tempfile.TemporaryDirectory() as temporary:
            result = publish_immutable_artifact_bundle(
                temporary,
                sample_members(),
                member_roles=sample_roles(),
                bundle_name_prefix="whitespace-bundle",
            )
            manifest_path = Path(result["bundle_dir"]) / DEFAULT_BUNDLE_MANIFEST_FILE
            manifest_path.write_bytes(manifest_path.read_bytes().rstrip())
            noncanonical = read_immutable_artifact_bundle(result["bundle_dir"])

        self.assertEqual(noncanonical["status"], "BLOCK")
        self.assertIn("serialization_noncanonical", noncanonical["blockers"][0])

    def test_manifest_nonfinite_and_excessive_nesting_map_to_domain_blocker(self) -> None:
        for label, mutation in (
            ("nonfinite", b',"synthetic_nonfinite":1e999}'),
            (
                "deep",
                b',"synthetic_deep":'
                + (b"[" * 127)
                + b"0"
                + (b"]" * 127)
                + b"}",
            ),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                result = publish_immutable_artifact_bundle(
                    temporary,
                    sample_members(),
                    member_roles=sample_roles(),
                    bundle_name_prefix=f"strict-{label}-bundle",
                )
                manifest_path = Path(result["bundle_dir"]) / DEFAULT_BUNDLE_MANIFEST_FILE
                raw = manifest_path.read_bytes().rstrip()
                self.assertTrue(raw.endswith(b"}"))
                manifest_path.write_bytes(raw[:-1] + mutation)

                loaded = read_immutable_artifact_bundle(result["bundle_dir"])

            self.assertEqual(loaded["status"], "BLOCK")
            self.assertEqual(
                loaded["blockers"],
                ["artifact_bundle_manifest_json_invalid"],
            )


if __name__ == "__main__":
    unittest.main()
