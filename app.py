# -*- coding: utf-8 -*-
"""Krug — окно на WebView2 (Edge), интерфейс в ui.html."""
import os, re, base64, sys, json, time, threading, subprocess, shutil, webbrowser
import datetime as dt
import hashlib, urllib.request, uuid
import webview
import core, brain

D = core.D
STOP = threading.Event()
win = None
LAUNCHER = 1
ALLOWED = ("app.py", "core.py", "brain.py", "ui.html")

def _read_version():
    for b in (os.path.dirname(os.path.abspath(__file__)), getattr(sys, "_MEIPASS", "")):
        try:
            with open(os.path.join(b, "version.json"), encoding="utf-8") as f:
                return json.load(f)["version"]
        except Exception: pass
    return "0.0.0"
VERSION = _read_version()

def _ver(s):
    try: return tuple(int(x) for x in str(s).split("."))
    except Exception: return (0,)

def _base():
    u = (D["cfg"].get("update_url") or "").strip()
    if re.fullmatch(r"[\w.-]+/[\w.-]+", u): u = "https://raw.githubusercontent.com/%s/main/" % u
    if not (u.startswith("https://") or u.startswith("http://127.0.0.1")): return ""
    return u if u.endswith("/") else u + "/"

def _get(url):
    req = urllib.request.Request(url + ("&" if "?" in url else "?") + "t=%d" % time.time(), headers={"User-Agent": "Krug", "Cache-Control": "no-cache"})
    return urllib.request.urlopen(req, timeout=20).read()

def _restart():
    time.sleep(1.2)
    try: win.destroy()
    except Exception: pass
    if getattr(sys, "frozen", False):
        cmd = [sys.executable]
    else:
        cmd = [sys.executable, os.path.abspath(__file__)]
    subprocess.Popen(cmd, env=dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1"), close_fds=True)
    os._exit(0)

def res(name):
    for b in (os.path.dirname(os.path.abspath(__file__)), getattr(sys, "_MEIPASS", "")):
        if b and os.path.exists(os.path.join(b, name)): return os.path.join(b, name)
    return name

AG = {"run": False}
AG_STOP = threading.Event()
AG_LOCK = threading.Lock()
SAVE_LISTS = ("tasks", "sched", "rem", "notes", "habits", "prompts", "sounds", "designs")

def _js(code):
    try: return win.evaluate_js(code)
    except Exception: return None

def _emit(ev): _js("Krug.agent(%s)" % json.dumps(ev, ensure_ascii=False))

def _confirm(title, msg):
    try: return bool(win.create_confirmation_dialog(title, msg))
    except Exception: return False

PERM_WAIT = {}

def _ask(kind, title, detail="", risk="mid"):
    """Окно «Разрешаю / Отклонить». Ждём ответ пользователя до 5 минут; «Стоп» или тишина = отказ."""
    pid = uuid.uuid4().hex[:8]; ev = threading.Event(); PERM_WAIT[pid] = {"ev": ev, "ans": "deny"}
    try: win.restore()
    except Exception: pass
    shown = _js("Krug.perm(%s)" % json.dumps({"id": pid, "kind": kind, "title": title, "detail": detail[:700], "risk": risk}, ensure_ascii=False))
    t0 = time.time()
    while not ev.wait(0.4):
        if (AG["run"] and AG_STOP.is_set()) or time.time() - t0 > 300: break
    ans = PERM_WAIT.pop(pid, {}).get("ans", "deny") if ev.is_set() else "deny"
    PERM_WAIT.pop(pid, None)   # чистка даже если прервались досрочно
    _js("Krug.permDone(%s)" % json.dumps(pid))
    return ans

core.ASK = _ask

def _check_html(html):
    """Страница запускается в скрытом iframe внутри окна Круга; ждём отчёт об ошибках JS."""
    cid = uuid.uuid4().hex[:10]
    _js("Krug.check(%s,%s)" % (json.dumps(cid), json.dumps(html)))
    for _ in range(44):
        time.sleep(0.25)
        r = _js("Krug.chkGet(%s)" % json.dumps(cid))
        if r:
            try: return json.loads(r)
            except Exception: break
    return {"timeout": True}

def _agent_job():
    try: out = core.agent(_emit, AG_STOP, _confirm, _check_html)
    except Exception as e: out = "⚠ Внутренняя ошибка агента: %s" % e
    r = Api()._finish(out); AG["run"] = False
    _emit({"t": "done", "state": D, "acts": r["acts"]})

class Api:
    def state(self): return D
    def save(self, s):
        for k, v in (s or {}).items():
            if k == "cfg" and isinstance(v, dict): D["cfg"].update(v)
            elif k in SAVE_LISTS and isinstance(v, list): D[k] = v
        core.save(); return True
    def _finish(self, r):
        r = r or ""
        chat = core.chat_get()
        user = next((m["content"] for m in reversed(chat) if m["role"] == "user"), "")
        acts = re.findall(r"\[\[\s*(\w+)\s*:?\s*(.*?)\]\]", r, re.S)
        r = re.sub(r"\[\[.*?\]\]", "", r, flags=re.S).strip() or "Готово ✅"
        learned = []
        try: learned = core.after_turn(user, r)
        except Exception: pass
        core.chat_append("assistant", r)
        if learned: D.setdefault("_learned", []).extend(learned)
        core.chat_trim(80); core.save()
        return {"state": D, "acts": [list(x) for x in acts]}
    def chat(self, text):
        """Встроенный мозг без ИИ (и совместимость со старым интерфейсом)."""
        core.chat_append("user", text)
        try:
            r = core.local(text)
            if r is None:
                p = D["cfg"]["provider"]
                if p == core.BI: r = brain.fallback(text, vars(core))
                else:
                    try: r = core.call(p, core.merge(core.chat_get()[-12:]), core.sysprompt())
                    except Exception as e: r = "⚠ Ошибка " + p + ": " + str(e)
        except Exception as e: r = "⚠ Внутренняя ошибка: %s" % e
        return self._finish(r)
    def chat2(self, text):
        """Умный режим: быстрые команды — локально, остальное делает агент с инструментами."""
        p = D["cfg"]["provider"]
        if p == core.BI: return dict(self.chat(text), mode="chat")
        if AG.get("run"): return {"mode": "busy"}
        try:
            r = core.local(text, llm=True)
        except Exception:
            r = None
        if r is not None:
            core.chat_append("user", text)
            return dict(self._finish(r), mode="chat")
        with AG_LOCK:
            if AG["run"]: return {"mode": "busy"}
            core.chat_append("user", text)
            AG["run"] = True; AG_STOP.clear()
        threading.Thread(target=_agent_job, daemon=True).start()
        return {"mode": "agent"}
    def agent_stop(self): AG_STOP.set(); return True
    def ping(self): return True
    def perm_answer(self, pid, ans):
        w = PERM_WAIT.get(pid)
        if w: w["ans"] = ans if ans in ("once", "task") else "deny"; w["ev"].set()
        return True
    # --- память и обучение
    def mem_add_user(self, text, cat="Факты"):
        core.mem_add(text, cat, "вручную", True); return D["memory"]
    def mem_del(self, i): D["memory"] = [x for x in D["memory"] if x["id"] != i]; core.save(); return D["memory"]
    def mem_pin(self, i):
        for x in D["memory"]:
            if x["id"] == i: x["pin"] = not x.get("pin")
        core.save(); return D["memory"]
    def mem_edit(self, i, text):
        text = (text or "").strip()
        if 3 <= len(text) <= 240 and not core.SENS.search(text):
            for x in D["memory"]:
                if x["id"] == i: x["t"] = text
        core.save(); return D["memory"]
    def mem_clear(self): D["memory"] = []; D["mem"] = {"facts": {}, "name": ""}; core.save(); return D["memory"]
    def rule_del(self, i): D["learn"]["rules"] = [r for r in D["learn"]["rules"] if r["id"] != i]; core.save(); return D["learn"]["rules"]
    def learn_clear(self): D["learn"].update(rules=[], lessons=[], freq={}, top=[]); core.save(); return D["learn"]
    def feedback(self, idx, good, note=""):
        ok = core.add_feedback(int(idx), bool(good), note); return {"ok": ok, "chat": D["chat"], "learn": D["learn"]}
    def audit_clear(self): D["audit"] = []; core.save(); return True
    # --- музыка (кнопки пользователя в самом приложении — отдельное разрешение не нужно)
    def music_find(self, q):
        try: return core.music_find(q)
        except Exception as e: return {"items": [], "note": "Ошибка: %s" % e}
    def music_play(self, q, service="youtube"):
        try:
            core.play_url(core.music_url(q, service, service == "youtube")); core.audit("music", "Кнопка в «Музыке»: " + str(q)[:60], "по клику пользователя"); return ""
        except Exception as e: return "Не открылось: %s" % e
    def media(self, action, times=1):
        try: core.media_key(action, times); return ""
        except Exception as e: return str(e)
    def music_local(self): return [{"name": os.path.basename(p), "path": p} for p in core.music_local()]
    def music_open_file(self, p):
        try: core.music_open_file(p); core.audit("music", "Кнопка: файл " + os.path.basename(p), "по клику пользователя"); return ""
        except Exception as e: return str(e)
    def connect_free(self, key):
        key = (key or "").strip()
        if len(key) < 20: return {"ok": False, "error": "ключ слишком короткий. Скопируй его целиком со страницы openrouter.ai/keys"}
        c = D["cfg"]; c["keys"]["OpenRouter"] = key; c["provider"] = "OpenRouter"; c["models"]["OpenRouter"] = "auto"
        try: c["free_models"] = core.fetch_free_models()
        except Exception: c["free_models"] = core.FREE_FALLBACK
        core.save()
        try: core.call_smart("OpenRouter", [{"role": "user", "content": "Ответь одним словом: ок"}], "Тест", 200)
        except Exception as e: return {"ok": False, "error": str(e)[:400], "cfg": c}
        core.save(); return {"ok": True, "model": c.get("last_model", ""), "cfg": c}
    def projects(self):
        out = []
        try: names = sorted(os.listdir(core.WS))
        except OSError: return out
        for n in names:
            p = os.path.join(core.WS, n)
            if not os.path.isdir(p): continue
            fl = [os.path.join(r, x) for r, _, f in os.walk(p) for x in f]
            mt = max([os.path.getmtime(x) for x in fl] or [os.path.getmtime(p)])
            out.append({"name": n, "files": len(fl), "mt": mt, "when": dt.datetime.fromtimestamp(mt).strftime("%d.%m %H:%M")})
        return sorted(out, key=lambda x: -x["mt"])
    def open_project(self, name):
        try:
            p = core.wp(name); idx = os.path.join(p, "index.html")
            if not os.path.exists(idx):
                h = [f for f in sorted(os.listdir(p)) if f.endswith(".html")] if os.path.isdir(p) else []
                idx = os.path.join(p, h[0]) if h else p
            core.open_path(idx); return ""
        except Exception as e: return "Не открылось: %s" % e
    def zip_project(self, name):
        try: r = core._zip(name); core.open_path(core.WS); return r
        except Exception as e: return "Не вышло: %s" % e
    def delete_project(self, name):
        try:
            p = core.wp(name)
            if p != core.WS and os.path.isdir(p): shutil.rmtree(p)
            return True
        except Exception: return False
    def workspace_folder(self): core.open_path(core.WS)
    def ask(self, user, system="Ты помощник."):
        p = D["cfg"]["provider"]
        if p == core.BI: return "Для этого нужен подключённый ИИ: Настройки → «Скачать локальный ИИ» или вставь ключ."
        try: return core.call(p, [{"role": "user", "content": user}], system)
        except Exception as e: return "⚠ Ошибка " + p + ": " + str(e)
    def gen(self, kind, prompt):
        p = D["cfg"]["provider"]
        if p == core.BI: return ""
        sy = {"sound": "Ты композитор-синтезист. Верни ТОЛЬКО JSON без пояснений и без ```: {\"name\":строка,\"wave\":\"sine|triangle|square|sawtooth|bell|piano\",\"bpm\":60-180,\"root\":MIDI 48-84,\"scale\":[3-8 полутонов 0-12],\"bars\":2-8,\"pattern\":\"arp|melody|rise\",\"decay\":0.1-1.5,\"delay\":0-0.6,\"notes\":[необязательно: до 64 пар [MIDI, длительность в долях]]}. Подбери параметры под описание настроения.",
              "css": "Ты UI-дизайнер. Верни ТОЛЬКО CSS без пояснений и без ``` ограждений (до 70 строк), который переопределяет внешний вид приложения по пожеланию. Переменные :root: --bg --s1 --s2 --bd --tx --mu --a1 --a2 --a3 --r --ff. Классы: .sb (боковая панель), .nv (пункт меню), .cd (карточка), .bt (кнопка), .chip, #cp (поле ввода), #view (основная область), .hero h1, .m .b (сообщение), body:before (фон). Без @import и внешних url, без JS. Меняй цвета, формы, тени, шрифты, анимации.",
              "design": "Ты senior frontend-дизайнер. Верни ТОЛЬКО один полный HTML-документ (<!doctype html>...</html>) с CSS и JS внутри, без внешних ресурсов и без пояснений, без ``` ограждений. Современный адаптивный дизайн, красивая типографика, плавные анимации (keyframes, transitions, IntersectionObserver), готовый к показу."}[kind]
        try: r = core.call(p, [{"role": "user", "content": prompt}], sy, {"design": 8000, "css": 3000}.get(kind, 1200)).strip()
        except Exception as e: return "⚠ " + str(e)
        if kind == "css": return re.sub(r"```(?:css)?", "", r).strip()
        m = re.search(r"<!doctype html.*</html>|<html.*</html>", r, re.S | re.I) if kind == "design" else re.search(r"\{.*\}", r, re.S)
        return m.group(0) if m else r
    def save_file(self, name, data, b64=False):
        d = os.path.join(os.path.expanduser("~"), "Documents", "Krug"); os.makedirs(d, exist_ok=True)
        path = os.path.join(d, re.sub(r'[\\/:*?"<>|]', "_", name) or "file")
        with open(path, "wb") as f: f.write(base64.b64decode(data) if b64 else data.encode("utf-8"))
        try: os.startfile(path if path.endswith(".html") else d)
        except Exception: pass
        return path
    def export(self):
        core.save(); d = os.path.join(os.path.expanduser("~"), "Documents", "Krug"); os.makedirs(d, exist_ok=True)
        path = os.path.join(d, "backup-%s.json" % dt.datetime.now().strftime("%Y%m%d-%H%M")); shutil.copy(core.FILE, path); return path
    def check_update(self):
        out = {"current": VERSION, "available": False}; b = _base()
        if not b: out["error"] = "no_url"; return out
        try: m = json.loads(_get(b + "version.json").decode("utf-8"))
        except Exception as e: out["error"] = str(e); return out
        if _ver(m.get("version")) > _ver(VERSION):
            out.update(available=True, version=str(m["version"]), notes=str(m.get("notes", "")), rebuild=int(m.get("min_launcher", 1)) > LAUNCHER)
        return out
    def apply_update(self):
        b = _base(); tmp = os.path.join(core.DIR, "app_new")
        try:
            m = json.loads(_get(b + "version.json").decode("utf-8"))
            if int(m.get("min_launcher", 1)) > LAUNCHER: return {"ok": False, "error": "Нужна пересборка: скачай новый ZIP и запусти Rebuild.bat"}
            shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
            for name in ALLOWED:
                data = _get(b + name)
                if len(data) > 5000000 or hashlib.sha256(data).hexdigest() != m["files"].get(name): raise RuntimeError("файл %s не прошёл проверку" % name)
                if name.endswith(".py"): compile(data, name, "exec")
                with open(os.path.join(tmp, name), "wb") as f: f.write(data)
            with open(os.path.join(tmp, "version.json"), "w", encoding="utf-8") as f:
                json.dump(m, f, ensure_ascii=False)
            ovr = os.path.join(core.DIR, "app")
            shutil.rmtree(ovr, ignore_errors=True)    # удаляем старую версию
            shutil.move(tmp, ovr)                       # перемещаем новую (tmp больше не существует)
        except Exception as e:
            shutil.rmtree(tmp, ignore_errors=True)     # чистим временные файлы при ошибке
            return {"ok": False, "error": str(e)}
        threading.Thread(target=_restart, daemon=True).start()
        return {"ok": True}
    def plan(self): return core.day_plan()
    def stop(self): STOP.set(); return True
    def snooze(self, text, kind):
        STOP.set(); core.add_rem(text, dt.datetime.now() + dt.timedelta(minutes=5), kind); return D
    def clear_chat(self):
        core.chat_get()  # чистим через helper
        with core._LOCK:
            D["chat"].clear()
        core.save(); return D
    def folder(self):
        if hasattr(os, "startfile"): os.startfile(core.DIR)
    def autostart(self):
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, "Krug", 0, winreg.REG_SZ, '"%s"' % sys.executable if getattr(sys, "frozen", False) else '"%s" "%s"' % (sys.executable, os.path.abspath(__file__)))
            return "Круг будет запускаться вместе с Windows."
        except Exception as e: return "Не вышло: " + str(e)
    def setup_local(self):
        if shutil.which("ollama"):
            subprocess.Popen('start "Krug: загрузка ИИ" cmd /k "ollama pull llama3.2"', shell=True)
            return "Скачиваю модель llama3.2 (около 2 ГБ). Когда окно закончит, чат заработает с локальным ИИ."
        webbrowser.open("https://ollama.com/download")
        return "Установи Ollama (открылся сайт) и снова нажми эту кнопку: Круг скачает модель сам."

def ring(r):
    STOP.clear(); n = 80 if r.get("kind") == "Будильник" else 3
    def go():
        for _ in range(n):
            if STOP.is_set(): break
            try:
                import winsound; winsound.Beep(1000, 400)
            except Exception: pass
            time.sleep(0.6)
    threading.Thread(target=go, daemon=True).start()

def loop():
    """Фоновый цикл: тик каждые 4 секунды, останавливается по STOP."""
    while not STOP.is_set():
        STOP.wait(4)
        try: _tick()
        except Exception: pass

def _tick():
    """Проверяет напоминания и будильники."""
    now = dt.datetime.now(); fired = []
    for r in list(D["rem"]):
        if not r.get("on"): continue
        try: w = dt.datetime.strptime(r["when"], "%Y-%m-%d %H:%M")
        except ValueError: continue
        if w > now: continue
        fired.append(dict(r))
        if r.get("rep", "Один раз") == "Один раз": r["on"] = False
        else:
            while w <= now:
                w += dt.timedelta(days=7 if r.get("rep") == "Каждую неделю" else 1)
                while r.get("rep") == "По будням" and w.weekday() > 4: w += dt.timedelta(days=1)
            r["when"] = w.strftime("%Y-%m-%d %H:%M")
    if fired:
        core.save()
        try: win.restore(); win.on_top = True; time.sleep(0.05); win.on_top = False
        except Exception: pass
        for r in fired:
            if not r.get("sound"): ring(r)
            try: win.evaluate_js("Krug.fire(%s)" % json.dumps(r, ensure_ascii=False))
            except Exception: pass
        try: win.evaluate_js("Krug.sync(%s)" % json.dumps({"rem": D["rem"]}, ensure_ascii=False))
        except Exception: pass

def main():
    global win
    with open(res("ui.html"), encoding="utf-8") as f:
        html = f.read()
    win = webview.create_window("Круг", html=html, js_api=Api(), width=1240, height=800, min_size=(960, 620), background_color="#0b0c10")
    webview.start(loop, storage_path=os.path.join(core.DIR, "web"))

if __name__ == "__main__":
    main()
