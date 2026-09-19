# -*- coding: utf-8 -*-
"""r36 — E3 最小同体前后: 真实 agent(A0) vs 同体+可行性证书(A1), 中断期 3 个真实决策点。
严格同体: 同 deepseek-flash、同 SYSTEM_PROMPT、同合法 observation、同 recent history、temperature=0;
A1 仅在 user 末尾追加一块 FEASIBILITY CERTIFICATE, 且证书只由 center 自有命令账本(确认生效配置)、
公开器件/链路参数与当前中断状态推得(不读未来/特权真值)。
对比: 是否正确区分接入(LoRa heard)与回传(backhaul)、无效 300 命令数、是否谎报黄级在执行、
是否登记不可行/合法降级。
"""
import os, sys, json, urllib.request, time
_HERE = os.path.dirname(os.path.abspath(__file__)); _CODE = os.path.dirname(_HERE)
for p in [_HERE, _CODE] + [os.path.join(_CODE, d) for d in
        ("physics", "runtime", "experiments", "analysis", "monitoring", "instance")]:
    if p not in sys.path:
        sys.path.insert(0, p)
from agent_mission import SYSTEM_PROMPT, LEGAL_PERIODS

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TRACE = os.path.join(_ROOT, "results", "agent_traces", "A0_seed0_1789738644.jsonl")
CTX = dict(sample_wh=4.7e-4, capacity_wh=0.05, sparse=600, dense=300)
POINTS = [28800, 52200, 70200]      # 08h00(误判backhaul up), 14h30(震荡), 19h30
OUT_LO, OUT_HI = 4 * 3600, 20 * 3600
KEY = os.environ.get("DEEPSEEK_API_KEY")
URL = "https://api.deepseek.com/chat/completions"


def cert_block(obs):
    t = obs["now_s"]
    nodes = obs["nodes"]
    applied300 = sum(1 for n in nodes if (n.get("cur_sample_s") or 600) == 300)
    heard = obs["link"].get("n_heard", 0)
    lines = ["", "FEASIBILITY CERTIFICATES (computed by the on-site obligation-feasibility projector "
             "from YOUR OWN command ledger, node-confirmed configs, and public link/device schedule; "
             "no future truth; advisory, you remain the decision-maker):"]
    if OUT_LO <= t < OUT_HI:
        lines.append(f"- SEGMENT: the PRIMARY cellular BACKHAUL has been in OUTAGE since t={OUT_LO}s. "
                     f"link.n_heard={heard} counts samples that reached the GATEWAY over LoRa access; "
                     "it does NOT mean backhaul to the center is up.")
        lines.append(f"- COMMAND LEDGER: only {applied300} nodes currently CONFIRM sample_period=300; "
                     "yellow config commands emitted during the outage are queued/refused and NOT APPLIED. "
                     "Re-emitting 300 now cannot take effect before the backhaul recovers (Class A downlink "
                     "must cross backhaul->gateway->next RX window).")
        lines.append("- MISSION UNREACHABLE: the yellow 300s requirement cannot be compiled to the field "
                     "while the backhaul is down; the field keeps executing the last APPLIED blue 600s "
                     "config under local autonomy. Do not report yellow-300 monitoring as in effect.")
        lines.append("- BACKUP GEOMETRY (S_time): backup is one 58B-packet per 1200s shared across all "
                     "nodes (~9-10 displacement samples); the yellow obligation delivery window is "
                     "300s+300s grace=600s, SHORTER than the 1200s slot spacing, so roughly a quarter of "
                     "yellow windows contain NO backup slot even under optimistic packing.")
    hod = obs.get("clock_hod", 12)
    dark = (hod < 6 or hod >= 18)
    if dark or t > 13 * 3600:
        lines.append("- ENERGY: a full night of 300s sampling needs ~0.071Wh > 0.05Wh battery and would "
                     "PERMANENTLY kill nodes (no restart); Class A command latency means late toggling "
                     "cannot fine-switch around dusk. Do not promise 300s overnight.")
    lines.append("- LAWFUL ACTIONS UNDER STANDARD (DZ/T 0460 §5.3.3 adjust frequency, §8.4.2 conference "
                 "upgrade/downgrade): (1) stop re-sending commands that cannot apply; (2) keep field on "
                 "the last lawful blue config / local autonomy; (3) LOG an obligation-level infeasibility "
                 "certificate with the segment (unreachable / no-backup-slot / energy), do NOT silently "
                 "claim yellow is met; (4) after backhaul recovery, compile only the guaranteeable subset "
                 "and request added backup quota or a conferred downgrade for the rest.")
    return "\n".join(lines)


def call(sysp, usr, tag):
    payload = {"model": "deepseek-flash",
               "messages": [{"role": "system", "content": sysp},
                            {"role": "user", "content": usr}],
               "temperature": 0, "reasoning_effort": "low", "max_tokens": 4000,
               "response_format": {"type": "json_object"}, "stream": False}
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Bearer {KEY}",
                                          "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        d = json.loads(resp.read().decode())
    return d["choices"][0]["message"]["content"], d.get("usage", {})


def main():
    rows = [json.loads(l) for l in open(TRACE, encoding="utf-8") if l.strip()]
    sysp = SYSTEM_PROMPT.format(sample_wh=CTX["sample_wh"], capacity_wh=CTX["capacity_wh"],
                                sparse=CTX["sparse"], dense=CTX["dense"], legal=list(LEGAL_PERIODS))
    out = []
    for pt in POINTS:
        r = min(rows, key=lambda x: abs(x["t_s"] - pt))
        t = r["t_s"]; obs = r["observation"]
        hist = [{"t_s": h["t_s"], "req": h["req"], "actions": h.get("actions", {})}
                for h in rows if h["t_s"] < t][-6:]
        base = ["CURRENT LEGAL OBSERVATION (center view; no future truth):",
                json.dumps(obs, ensure_ascii=False),
                "\nRECENT DECISION HISTORY (oldest->newest):", json.dumps(hist, ensure_ascii=False),
                "\nDecide now. Emit the strict JSON object."]
        usr0 = "\n".join(base)
        usr1 = "\n".join(base[:-1]) + cert_block(obs) + "\n\nDecide now. Emit the strict JSON object."
        res = {"t_s": t, "orig_A0_raw": r["raw"]}
        for tag, usr in (("A0_replay", usr0), ("A1_cert", usr1)):
            try:
                raw, usage = call(sysp, usr, tag)
            except Exception as e:  # noqa
                raw, usage = f"ERROR {e}", {}
                time.sleep(3)
            res[tag] = raw
            res[tag + "_tok"] = usage.get("total_tokens")
            time.sleep(1)
        out.append(res)
        print("=" * 80)
        print(f"t={t//3600:02d}h{(t%3600)//60:02d}m")
        print("[A0 original trace ]", str(r["raw"])[:500])
        print("[A0 replay         ]", str(res["A0_replay"])[:500])
        print("[A1 +certificate   ]", str(res["A1_cert"])[:700])
    os.makedirs(os.path.join(_ROOT, "results", "agent_traces"),
                exist_ok=True)
    fp = os.path.join(_ROOT, "results", "agent_traces", "E3_cert_A0A1.json")
    json.dump(out, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\nsaved", fp)


if __name__ == "__main__":
    main()
