#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DeepSeek-flash 零样本价值打分者（v2gate 的 LLM 臂）。

公平性核心：LLM 与规则臂**同构**——都只产出"每条监测点的重要性分"，打包(full/digest/drop)
一律由 arms.py 里同一个最优背包器完成。LLM 不手搓字节组合，避免把"组合优化操作能力"与
"语境价值判断"耦死（手搓版会冤枉丢条目）。这样 LLM 与规则的唯一差别就是价值来源。

信息纪律（04/04b）：只收 cid+观测文本；不收 v*、ptype、档位、combo、真值、未来；
prompt 不写"加速×非雨峰×隐患=真临滑"这类显式组合判据（那正是 rule_tree 编码、要测 LLM
能否零样本自行推出的东西）。temperature=0、json_object、thinking disabled；prompt 哈希缓存、
复跑不重复扣费；解析失败**固定回退为 rule_linear 分数**并记 parse_fail（不重试到"对"）。
"""
from __future__ import annotations
import hashlib, json, os, re, threading, time, urllib.request, urllib.error

from world_gen import rule_linear_value

_LOCK = threading.Lock()

MODEL = "deepseek-flash"
URL = "https://api.deepseek.com/chat/completions"
_HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(_HERE, "..", "..", "results", "v2gate_llm_cache.json")

SYSTEM = (
    "你是山区地质灾害应急监测系统的研判助手。野外监测点通过北斗短报文回传，带宽极其有限，"
    "每个周期只能把少量监测点的信息发送出去，需要先给每个监测点的本期观测打一个重要性分，"
    "供系统在有限容量里排序取舍。请依据你对滑坡/崩塌机理、降雨诱发表面位移、仪器噪声的理解，"
    "判断每条观测对'是否正在发生真实斜坡失稳'这一预警决策的相对重要性。")


def load_key() -> str:
    path = os.path.expanduser("~/.bashrc")
    key = None
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = re.search(r"export\s+DEEPSEEK_API_KEY=([^\s#]+)", line)
            if m:
                key = m.group(1).strip().strip('"').strip("'")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not found in ~/.bashrc")
    return key


def build_prompt(cands) -> str:
    L = ["本期各监测点观测如下："]
    for c in cands:
        L.append(c.text)
    L.append("请给每一条打 0 到 100 的整数重要性分：分数越高，越值得在极其有限的应急回传"
             "容量中优先发送；纯粹由增强降雨驱动的表面位移、或疑似仪器噪声应给低分，"
             "符合真实斜坡失稳前兆的应给高分。")
    L.append('只输出一个 JSON 对象，不要任何额外文字：'
             '{"scores":[{"id":<每条开头#后的编号>,"score":0到100的整数}, ...]}，'
             '每个编号恰好出现一次。')
    return "\n".join(L)


def _request(prompt: str, key: str, temperature: float = 0.0, retries: int = 1):
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "max_tokens": 600,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
        "stream": False}).encode("utf-8")
    req = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    last = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                doc = json.loads(r.read().decode("utf-8"))
            return doc["choices"][0]["message"]["content"], doc.get("usage", {})
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"deepseek request failed: {last}")


def _load_cache():
    try:
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    tmp = CACHE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    os.replace(tmp, CACHE_PATH)


def parse_scores(content: str, cands):
    """返回 cid->分数(0..100)。必须覆盖全部 cid 且为数值，否则 (None,False) 触发固定回退。"""
    try:
        doc = json.loads(content)
        items = doc["scores"]
        ids = {c.cid for c in cands}
        sc = {}
        for it in items:
            i = int(it["id"]); v = float(it["score"])
            if i in ids:
                sc[i] = max(0.0, min(100.0, v))
        if len(sc) != len(cands):
            return None, False
        return sc, True
    except Exception:
        return None, False


def decide(cands, use_cache=True, key=None, temperature=0.0):
    """返回 (scores: cid->0..100, meta)。解析失败固定回退为 rule_linear 分（明确退化为线性规则）。
    缓存键含 model 与 temperature，t=0.3 变异跑不会误用 t=0 缓存。"""
    prompt = build_prompt(cands)
    h = hashlib.sha256(
        f"{prompt}|T{temperature}|{MODEL}".encode("utf-8")).hexdigest()
    cache = _load_cache() if use_cache else {}
    meta = {"cached": False, "parse_fail": False, "usage": None, "hash": h[:12]}
    if h in cache:
        content = cache[h]["content"]
        meta["cached"] = True
        meta["usage"] = cache[h].get("usage")
    else:
        key = key or load_key()
        content, usage = _request(prompt, key, temperature=temperature)   # 锁外请求，允许并发
        meta["usage"] = usage
        if use_cache:
            with _LOCK:                            # 锁内 merge 最新缓存，避免并发互相覆盖
                latest = _load_cache()
                latest[h] = {"content": content, "usage": usage, "model": MODEL}
                _save_cache(latest)
    scores, ok = parse_scores(content, cands)
    if not ok:
        meta["parse_fail"] = True
        scores = {c.cid: rule_linear_value(c) for c in cands}
    return scores, meta
