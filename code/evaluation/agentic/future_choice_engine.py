#!/usr/bin/env python3
"""Domain-agnostic L/U + certificate + exact-fallback future-choice engine.

The engine owns only the correctness protocol. Domain semantics live in an
adapter:

1. reuse a carried replayable certificate when its validity domain still holds;
2. if a sound optimistic necessary condition fails, classify U=0 / unsafe;
3. try to construct a replayable L=1 certificate;
4. otherwise call the domain's exact correctness fallback;
5. carry the selected certificate through execution using an adapter-defined
   suffix/domain transformation.

This intentionally does not encode communication, routing, query or resource
semantics.  Those belong to domain adapters and certificate witnesses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Hashable, Protocol, TypeVar


ContextT=TypeVar("ContextT")
ActionT=TypeVar("ActionT")


@dataclass(frozen=True)
class FutureChoiceCertificate:
    certificate_id:str
    witness:Any
    dependencies:frozenset[str]=frozenset()
    metadata:dict[str,Any]=field(default_factory=dict,compare=False,hash=False)


@dataclass(frozen=True)
class ActionClassification(Generic[ActionT]):
    action:ActionT
    safe:bool
    source:str
    L:int
    U:int
    certificate:FutureChoiceCertificate|None=None


class FutureChoiceAdapter(Protocol[ContextT,ActionT]):
    def action_key(self,action:ActionT)->Hashable: ...
    def optimistic_possible(self,context:ContextT,action:ActionT)->bool: ...
    def carried_certificate_valid(self,context:ContextT,action:ActionT,certificate:FutureChoiceCertificate)->bool: ...
    def lower_certificate(self,context:ContextT,action:ActionT)->FutureChoiceCertificate|None: ...
    def exact_certificate(self,context:ContextT,action:ActionT)->FutureChoiceCertificate|None: ...
    def carry_after_commit(self,context:ContextT,action:ActionT,certificate:FutureChoiceCertificate)->FutureChoiceCertificate|None: ...


class FutureChoiceEngine(Generic[ContextT,ActionT]):
    def __init__(self,adapter:FutureChoiceAdapter[ContextT,ActionT]):
        self.adapter=adapter
        self.carried:FutureChoiceCertificate|None=None
        self.metrics={
            "classifications":0,
            "carried_hits":0,
            "upper_impossible":0,
            "lower_hits":0,
            "exact_fallback_calls":0,
            "exact_success":0,
            "exact_failure":0,
            "commits":0,
        }

    def classify(self,context:ContextT,action:ActionT)->ActionClassification[ActionT]:
        self.metrics["classifications"]+=1
        if self.carried is not None and self.adapter.carried_certificate_valid(context,action,self.carried):
            self.metrics["carried_hits"]+=1
            return ActionClassification(action,True,"L1-carried",1,1,self.carried)

        if not self.adapter.optimistic_possible(context,action):
            self.metrics["upper_impossible"]+=1
            return ActionClassification(action,False,"U0",0,0,None)

        certificate=self.adapter.lower_certificate(context,action)
        if certificate is not None:
            self.metrics["lower_hits"]+=1
            return ActionClassification(action,True,"L1-constructive",1,1,certificate)

        self.metrics["exact_fallback_calls"]+=1
        certificate=self.adapter.exact_certificate(context,action)
        if certificate is None:
            self.metrics["exact_failure"]+=1
            return ActionClassification(action,False,"exact-infeasible",0,1,None)
        self.metrics["exact_success"]+=1
        return ActionClassification(action,True,"exact-certificate",1,1,certificate)

    def frontier(self,context:ContextT,actions:list[ActionT]|tuple[ActionT,...])->dict[Hashable,ActionClassification[ActionT]]:
        return {self.adapter.action_key(action):self.classify(context,action) for action in actions}

    def commit(self,context:ContextT,classification:ActionClassification[ActionT])->None:
        self.metrics["commits"]+=1
        if not classification.safe or classification.certificate is None:
            self.carried=None
            return
        self.carried=self.adapter.carry_after_commit(context,classification.action,classification.certificate)

    def clear(self)->None:
        self.carried=None
