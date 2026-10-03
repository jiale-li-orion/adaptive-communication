"""Communication Capability registry and bindings."""
from __future__ import annotations

import json
from pathlib import Path

from .runtime_contracts import (
    CapabilityBinding,
    CapabilityContract,
    EffectSemantics,
    ExecutionClass,
    TaskContract,
    capability_visible_for_task,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = ROOT / "research" / "compiler" / "COMMUNICATION-DOMAIN-REGISTRY.v0.1.json"


def _execution_class(cap: dict) -> ExecutionClass:
    effect = cap["effect_semantics"]
    owner = cap["owner_location"]
    if effect == "observation":
        return (
            ExecutionClass.LOCAL_READ
            if owner == "center"
            else ExecutionClass.INTERMITTENT_REMOTE_READ
        )
    if owner in {"terminal", "gateway", "access_runtime"}:
        return ExecutionClass.LOCAL_ACTION
    return ExecutionClass.INTERMITTENT_REMOTE_ACTION


def _paths(cap: dict) -> tuple[list[str], list[str], list[str]]:
    cid = cap["capability_id"]
    if cid.startswith("communication.center."):
        return [], [], []
    if cid.startswith("communication.gateway."):
        return ["gateway_owner"], ["gateway_to_center_backhaul"], ["gateway_reachability"]
    if cid.startswith("communication.config."):
        return (
            ["center_to_gateway_backhaul", "class_a_receive_window"],
            ["node_uplink", "gateway_to_center_backhaul"],
            ["class_a_receive_opportunity"],
        )
    if cid.endswith("terminal_dts"):
        return ["terminal_dts_opportunity"], ["terminal_dts_return"], ["satellite_contact"]
    if cid.endswith("gateway_backup"):
        return ["gateway_backup_opportunity"], ["gateway_backup_return"], ["backup_capacity"]
    if cid.endswith("access_assist"):
        return ["access_assist_window"], [], ["access_assist_window"]
    return [], [], []


def _schemas(capability_id: str) -> tuple[dict, dict]:
    if capability_id == "communication.gateway.node_report":
        return (
            {"node_id": "string"},
            {
                "soc_wh": "number?",
                "sample_interval_s": "integer?",
                "report_period_s": "integer?",
                "cache_level": "integer?",
                "read_at": "integer?",
            },
        )
    if capability_id == "communication.config.set_sampling_interval":
        return (
            {"node_id": "string", "target_s": "integer>=60"},
            {"lifecycle_stage": "string", "generation": "integer"},
        )
    if capability_id == "communication.config.set_report_period":
        return (
            {"node_id": "string", "target_s": "integer>=60"},
            {"lifecycle_stage": "string", "generation": "integer"},
        )
    if capability_id == "communication.fallback.gateway_backup":
        return (
            {"enabled": "boolean"},
            {"enabled": "boolean", "changed": "boolean", "lifecycle_stage": "applied"},
        )
    if capability_id == "communication.fallback.terminal_dts":
        return ({"enabled": "boolean", "node_id": "string?"}, {"enabled": "boolean"})
    if capability_id == "communication.fallback.access_assist":
        return ({"duration_s": "integer>0"}, {"active_until_s": "integer"})
    return ({}, {})


class CommunicationCapabilityCatalog:
    def __init__(self, registry_path: str | Path = DEFAULT_REGISTRY) -> None:
        self.registry_path = Path(registry_path)
        raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
        self.registry_id = raw["registry_id"]
        self.registry_revision = raw["registry_revision"]
        self.contracts: dict[str, CapabilityContract] = {}
        self.bindings: dict[str, CapabilityBinding] = {}
        self.runtime_status: dict[str, str] = {}
        for cap in raw["capabilities"]:
            effect = EffectSemantics(cap["effect_semantics"])
            input_schema, output_schema = _schemas(cap["capability_id"])
            contract = CapabilityContract(
                capability_id=cap["capability_id"],
                contract_revision=int(cap["contract_revision"]),
                action=cap["action"],
                applicable_resource_types=[cap["resource_type"]],
                canonical_input_schema=input_schema,
                canonical_output_schema=output_schema,
                observation_semantics=cap["observation_semantics"],
                effect_semantics=effect,
                authority_semantics=[cap["owner_location"]],
                preconditions=[],
                postconditions=[],
                idempotency=("read_only" if effect == EffectSemantics.OBSERVATION else "domain_defined"),
                reversibility=("n/a" if effect == EffectSemantics.OBSERVATION else "domain_defined"),
                failure_semantics=list(cap.get("failure_semantics", [])),
                risk_class=("read" if effect == EffectSemantics.OBSERVATION else "physical_effect"),
            )
            req, ret, opp = _paths(cap)
            binding = CapabilityBinding(
                binding_id=f"binding:{cap['capability_id']}",
                binding_revision=1,
                capability_id=cap["capability_id"],
                contract_revision=int(cap["contract_revision"]),
                implementation_ref=cap["binding"]["path"],
                execution_class=_execution_class(cap),
                owner_location=cap["owner_location"],
                required_path=req,
                return_path=ret,
                freshness_semantics={"description": cap.get("freshness_semantics", "")},
                latency_model={"authority": "simulator_time"},
                cost_model={"authority": "simulator_counters"},
                opportunity_dependency=opp,
                fallback_rank=100,
            )
            self.contracts[contract.capability_id] = contract
            self.bindings[binding.capability_id] = binding
            self.runtime_status[contract.capability_id] = str(
                cap.get("runtime_status", "live_planner_device")
            )

    def visible(self, task: TaskContract) -> list[CapabilityContract]:
        return sorted(
            (
                c
                for c in self.contracts.values()
                if self.runtime_status.get(c.capability_id) != "baseline_materializer_only"
                and capability_visible_for_task(task, c)
            ),
            key=lambda c: c.capability_id,
        )

    def planner_specs(self, task: TaskContract) -> list[dict]:
        """Frozen, model-facing capability semantics for PromptAssembly.

        IDs alone are insufficient for replay: the consumer must know observation/effect,
        owner/path, failure and cost/opportunity semantics exactly as they were at run time.
        """
        out = []
        for contract in self.visible(task):
            binding = self.binding(contract.capability_id)
            out.append(
                {
                    "capability_id": contract.capability_id,
                    "contract_revision": contract.contract_revision,
                    "action": contract.action,
                    "resource_types": list(contract.applicable_resource_types),
                    "canonical_input_schema": dict(contract.canonical_input_schema),
                    "canonical_output_schema": dict(contract.canonical_output_schema),
                    "observation_semantics": contract.observation_semantics,
                    "effect_semantics": contract.effect_semantics.value,
                    "authority_semantics": list(contract.authority_semantics),
                    "failure_semantics": list(contract.failure_semantics),
                    "owner_location": binding.owner_location,
                    "execution_class": binding.execution_class.value,
                    "required_path": list(binding.required_path),
                    "return_path": list(binding.return_path),
                    "freshness_semantics": dict(binding.freshness_semantics),
                    "latency_model": dict(binding.latency_model),
                    "cost_model": dict(binding.cost_model),
                    "opportunity_dependency": list(binding.opportunity_dependency),
                }
            )
        return out

    def get(self, capability_id: str) -> CapabilityContract:
        return self.contracts[capability_id]

    def binding(self, capability_id: str) -> CapabilityBinding:
        return self.bindings[capability_id]
