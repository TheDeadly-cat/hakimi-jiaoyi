"""Bounded child protocol around a backend-assembled ActionCoordinator.

The standalone entrypoint has no authority, package loader, connection factory
or dynamic import hook and always denies dispatch. Trusted future bootstrap can
call serve with its assembled coordinator; synthetic tests exercise that same
function in owned children. PackageWorkerSpec admission remains unavailable.
"""
import argparse
from hashlib import sha256
import json
import sys


SCHEMA = "hakimi-broker-worker-message-v1"
MAX_INPUT_BYTES, MAX_INPUT_MESSAGES = 32768, 50
MAX_MESSAGE_BYTES, MAX_OUTPUT_BYTES = 4096, 65536


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def serve(*, run_id, request_id, coordinator=None, input_stream=None, output_stream=None):
    source = input_stream or sys.stdin.buffer
    target = output_stream or sys.stdout.buffer
    sequence = incoming = received = written = 0

    def emit(kind, payload):
        nonlocal sequence, written
        sequence += 1
        value = dict(schema_version=SCHEMA, run_id=run_id, request_id=request_id,
                     sequence=sequence, kind=kind, payload=payload)
        raw = json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        if len(raw) > 8192 or written + len(raw) > MAX_OUTPUT_BYTES:
            raise ValueError("worker_output_budget_exceeded")
        written += len(raw)
        target.write(raw)
        target.flush()

    emit("READY", {"dispatch_admission": "UNAVAILABLE" if coordinator is None else "BACKEND_BOUND_ONLY",
                   "renderer_authority": False, "automatic_retry": False})
    completed = 0
    try:
        while incoming < MAX_INPUT_MESSAGES:
            raw = source.readline(MAX_MESSAGE_BYTES + 1)
            if not raw:
                raise ValueError("input_ended_without_stop")
            received += len(raw)
            if len(raw) > MAX_MESSAGE_BYTES or received > MAX_INPUT_BYTES or not raw.endswith(b"\n"):
                raise ValueError("worker_input_budget_or_frame_invalid")
            value = json.loads(raw, object_pairs_hook=_pairs,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite_json")))
            incoming += 1
            if (type(value) is not dict or set(value) != {"schema_version", "run_id", "request_id", "sequence", "kind", "payload"}
                or value["schema_version"] != SCHEMA or value["run_id"] != run_id or value["request_id"] != request_id
                or type(value["sequence"]) is not int or value["sequence"] != incoming or type(value["payload"]) is not dict):
                raise ValueError("worker_message_identity_or_sequence_invalid")
            if value["kind"] == "STOP":
                if value["payload"]:
                    raise ValueError("stop_payload_must_be_empty")
                cleanup = coordinator.close() if coordinator is not None else {"closed": True, "cleanup_confirmed": True}
                emit("RESULT", {"status": "PROTOCOL_COMPLETE" if cleanup["cleanup_confirmed"] else "UNKNOWN",
                    "operations_observed": completed, "cleanup_confirmed": cleanup["cleanup_confirmed"],
                    "external_authorization_granted": False, "economic_acceptance": "NOT_INFERRED"})
                return 0
            if value["kind"] != "INPUT" or set(value["payload"]) != {"operation_id"} or type(value["payload"]["operation_id"]) is not str:
                raise ValueError("only_prebound_operation_id_accepted")
            identity = value["payload"]["operation_id"]
            result = (coordinator.execute(identity) if coordinator is not None else
                      {"operation_id": identity, "status": "DENIED", "reason": "PRODUCTION_ADMISSION_UNAVAILABLE"})
            encoded = json.dumps(result, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
            # Full evidence lives in the original durable journal and private
            # bounded sink. The pipe carries identity/status only, never frames.
            emit("EVIDENCE", {"operation_id": identity, "status": result["status"],
                "projection_sha256": sha256(encoded).hexdigest(), "automatic_retry": False,
                "economic_acceptance": "NOT_INFERRED"})
            completed += 1
        raise ValueError("worker_input_count_exceeded")
    except Exception as error:
        cleanup = False
        if coordinator is not None:
            try:
                cleanup = coordinator.close()["cleanup_confirmed"]
            except Exception:
                pass
        emit("RESULT", {"status": "UNKNOWN", "reason": type(error).__name__,
            "operations_observed": completed, "cleanup_confirmed": cleanup,
            "external_authorization_granted": False, "economic_acceptance": "NOT_INFERRED"})
        return 1


def main():
    parser = argparse.ArgumentParser(description="Unavailable-by-default broker worker protocol")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--request-id", required=True)
    args = parser.parse_args()
    return serve(run_id=args.run_id, request_id=args.request_id)


if __name__ == "__main__":
    raise SystemExit(main())
