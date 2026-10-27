# -*- coding: utf-8 -*-
"""Ядро Krug: данные, планы дня, вызовы ИИ (без интерфейса)."""
import json, os, re, sys, time, urllib.request, urllib.error, uuid
import datetime as dt
import brain

DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Krug")
os.makedirs(DIR, exist_ok=True)
FILE = os.path.join(DIR, "data.json")
BI = "Krug Brain (встроенный)"
URLS = {"OpenAI": "https://api.openai.com/v1", "OpenRouter": "https://openrouter.ai/api/v1",
        "Groq": "https://api.groq.com/openai/v1", "DeepSeek": "https://api.deepseek.com/v1",
        "Gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
        "Ollama (локально)": "http://localhost:11434/v1"}
PROV = [BI, "OpenAI", "Anthropic", "Gemini", "OpenRouter", "Groq", "DeepSeek", "Ollama (локально)", "Своё (OpenAI-совместимое)"]
MODELS = {"OpenAI": "gpt-4o-mini", "Anthropic": "claude-sonnet-5-5", "Gemini": "gemini-2.0-flash",
          "OpenRouter": "openai/gpt-4o-mini", "Groq": "llama-3.3-70b-versatile", "DeepSeek": "deepseek-chat",
          "Ollama (локально)": "llama3.2", "Своё (OpenAI-совместимое)": ""}
DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
REPS = ["Один раз", "Каждый день", "По будням", "Каждую неделю"]
PR = {"Высокий": 0, "Средний": 1, "Низкий": 2}
BG, PN, FG, AC = "#14161c", "#1d2029", "#e8e8ee", "#6c8cff"

# ---------- данные ----------
def load():
    try:
        d = json.load(open(FILE, encoding="utf-8"))
    except Exception:
        d = {}
    for k in ("tasks", "sched", "rem", "notes", "prompts", "habits", "chat", "sounds", "designs"):
        d.setdefault(k, [])
    c = d.setdefault("cfg", {})
    c.setdefault("provider", BI)
    if c["provider"] not in PROV: c["provider"] = BI
    c.setdefault("keys", {}); c.setdefault("models", dict(MODELS)); c.setdefault("url", "")
    for k in ("tasks", "sched", "rem", "notes", "prompts", "habits", "chat", "sounds", "designs"):
        d[k] = [x for x in d[k] if isinstance(x, dict)]
    d["chat"] = [m for m in d["chat"] if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)]
    return d

D = load()
def save():
    json.dump(D, open(FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

REFRESH = []
def refresh_all():
    for f in REFRESH:
        try: f()
        except Exception: pass

uid = lambda: uuid.uuid4().hex[:8]
fmt = lambda w: w.strftime("%Y-%m-%d %H:%M")

def add_rem(text, when, kind="Напоминание", rep="Один раз"):
    D["rem"].append({"id": uid(), "text": text, "when": fmt(when), "kind": kind, "rep": rep, "on": True})
    save(); refresh_all()

def streak(log):
    d, n = dt.date.today(), 0
    if d.isoformat() not in log: d -= dt.timedelta(days=1)
    while d.isoformat() in log:
        n += 1; d -= dt.timedelta(days=1)
    return n

# ---------- план дня ----------
def day_plan():
    now = dt.datetime.now(); td = now.strftime("%Y-%m-%d"); wd = DAYS[now.weekday()]
    L = [f"📅 {now:%d.%m.%Y}, {wd}", ""]
    sc = sorted([x for x in D["sched"] if x["day"] == wd], key=lambda x: x["time"])
    if sc: L += ["Расписание:"] + [f"  {x['time']} — {x['text']}" for x in sc] + [""]
    rm = sorted([x for x in D["rem"] if x["on"] and x["when"].startswith(td)], key=lambda x: x["when"])
    if rm: L += ["Напоминания и будильники:"] + [f"  {x['when'][11:]} — {x['text']}" for x in rm] + [""]
    ts = sorted([t for t in D["tasks"] if not t["done"]], key=lambda t: (PR.get(t["prio"], 1), t["due"] or "9"))
    if ts:
        L.append("Задачи по приоритету (блок 50 мин + 10 мин отдыха):")
        h = now.replace(second=0, microsecond=0) + dt.timedelta(minutes=(10 - now.minute % 10) % 10)
        for t in ts[:8]:
            L.append(f"  {h:%H:%M}–{h + dt.timedelta(minutes=50):%H:%M}  {t['text']}" + (f"  (срок {t['due']})" if t["due"] else ""))
            h += dt.timedelta(minutes=60)
        L.append("")
    hb = [x["text"] for x in D["habits"] if td not in x["log"]]
    if hb: L += ["Привычки на сегодня: " + ", ".join(hb), ""]
    if len(L) <= 2: L.append("Пока пусто. Добавь задачи, расписание или напиши помощнику: «напомни через 10 минут выпить воды».")
    return "\n".join(L)

# ---------- встроенный помощник (brain.py) ----------
def local(m):
    return brain.think(m, globals())

# ---------- ИИ ----------
def post(url, body, headers):
    headers = dict(headers, **{"Content-Type": "application/json", "User-Agent": "Krug/1.0"})
    req = urllib.request.Request(url, json.dumps(body).encode("utf-8"), headers)
    try:
        return json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        hint = {401: "ключ не принят, проверь его в Настройках", 403: "доступ запрещён, проверь ключ", 402: "на аккаунте нет средств: пополни баланс или выбери бесплатную модель",
                404: "модель не найдена, проверь её название в Настройках", 429: "слишком много запросов или исчерпан лимит"}.get(e.code, "")
        raise RuntimeError(f"HTTP {e.code}" + (f" — {hint}" if hint else "") + "\n" + e.read().decode("utf-8", "ignore")[:300])

def call(p, msgs, system, mt=None):
    c = D["cfg"]; key = c["keys"].get(p, "")
    if p not in ("Ollama (локально)", "Своё (OpenAI-совместимое)") and not key:
        raise RuntimeError("не вставлен API-ключ. Открой «Настройки», вставь ключ " + p + " и нажми «Сохранить». Либо выбери «Krug Brain» в списке внизу: он работает без ключей.")
    model = c["models"].get(p, "") or MODELS.get(p, "")
    if p == "Anthropic":
        r = post("https://api.anthropic.com/v1/messages", {"model": model, "max_tokens": mt or 2000, "system": system, "messages": msgs},
                 {"x-api-key": key, "anthropic-version": "2023-06-01"})
        return "".join(b.get("text", "") for b in r["content"])
    base = (URLS.get(p) or c.get("url", "")).rstrip("/")
    if not base: raise RuntimeError("укажи адрес API в настройках")
    r = post(base + "/chat/completions", dict({"model": model, "messages": [{"role": "system", "content": system}] + msgs}, **({"max_tokens": mt} if mt else {})),
             {"Authorization": "Bearer " + (key or "none")})
    return r["choices"][0]["message"]["content"]

def merge(msgs):
    out = []
    for m in msgs:
        if out and out[-1]["role"] == m["role"]: out[-1]["content"] += "\n" + m["content"]
        elif out or m["role"] == "user": out.append(dict(m))
    return out

def sysprompt():
    ts = [t["text"] for t in D["tasks"] if not t["done"]][:10]
    al = [f"{r['text']} {r['when']}" for r in D["rem"] if r["on"]][:6]
    sn = [s["name"] for s in D.get("sounds", [])][-8:]
    return ("Ты — Круг, ИИ-помощник-приложение на компьютере пользователя. Отвечай по-русски, кратко и по делу. "
            "ВАЖНО: словами ты ничего не создаёшь и не меняешь. Действия выполняет приложение, только если в КОНЦЕ ответа ты добавишь команду [[имя: аргумент]]. "
            "Никогда не говори, что что-то сделано, если не добавил команду. Команды: "
            "[[sound: описание мелодии||alarm]] создать звук и поставить на ближайший будильник (без ||alarm — только в библиотеку); "
            "[[design: тип|описание]] создать страницу в студии дизайна, тип: landing, card, anim, logo, game; "
            "[[ui: preset=НАЗВАНИЕ]] стили: киберпанк, уют, минимализм, неон, океан, закат, лес, сакура, золото, матрица, космос, ретро; "
            "[[ui: accent=#ff4d5e]] [[ui: theme=light]] [[ui: radius=28px]] [[ui: fx=stars]] (stars, grid, glow, none) [[ui: reset]]; "
            "[[restyle: пожелание]] полностью перерисовать интерфейс приложения; [[game: on]] или [[game: off]] — игра-динозаврик в левом углу. "
            "Напоминания, будильники, задачи и заметки приложение создаёт само по обычным фразам пользователя, ты их не оформляешь. "
            f"Сейчас {dt.datetime.now():%Y-%m-%d %H:%M}. Открытые задачи: {ts or 'нет'}. Будильники: {al or 'нет'}. Звуки: {sn or 'нет'}.")
