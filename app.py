# -*- coding: utf-8 -*-
"""Krug — окно на WebView2 (Edge), интерфейс в ui.html."""
import os, re, base64, sys, json, time, threading, subprocess, shutil, webbrowser
import datetime as dt
import hashlib, urllib.request
import webview
import core, brain

D = core.D
STOP = threading.Event()
win = None
LAUNCHER = 1
ALLOWED = ("app.py", "core.py", "brain.py", "ui.html")

def _read_version():
    for b in (os.path.dirname(os.path.abspath(__file__)), getattr(sys, "_MEIPASS", "")):
        try: return json.load(open(os.path.join(b, "version.json"), encoding="utf-8"))["version"]
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
    cmd = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "launcher.py")]
    subprocess.Popen(cmd, env=dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT="1"), close_fds=True)
    os._exit(0)

def res(name):
    for b in (os.path.dirname(os.path.abspath(__file__)), getattr(sys, "_MEIPASS", "")):
        if b and os.path.exists(os.path.join(b, name)): return os.path.join(b, name)
    return name

class Api:
    def state(self): return D
    def save(self, s):
        D.update(s); core.save(); return True
    def chat(self, text):
        D["chat"].append({"role": "user", "content": text})
        r = core.local(text)
        if r is None:
            p = D["cfg"]["provider"]
            if p == core.BI: r = brain.fallback(text, vars(core))
            else:
                try: r = core.call(p, core.merge(D["chat"][-12:]), core.sysprompt())
                except Exception as e: r = "⚠ Ошибка " + p + ": " + str(e)
        acts = re.findall(r"\[\[\s*(\w+)\s*:?\s*(.*?)\]\]", r, re.S)
        r = re.sub(r"\[\[.*?\]\]", "", r, flags=re.S).strip() or "Готово ✅"
        D["chat"].append({"role": "assistant", "content": r}); del D["chat"][:-80]; core.save()
        return {"state": D, "acts": [list(x) for x in acts]}
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
                open(os.path.join(tmp, name), "wb").write(data)
            json.dump(m, open(os.path.join(tmp, "version.json"), "w", encoding="utf-8"), ensure_ascii=False)
            ovr = os.path.join(core.DIR, "app"); shutil.rmtree(ovr, ignore_errors=True); shutil.move(tmp, ovr)
        except Exception as e:
            shutil.rmtree(tmp, ignore_errors=True); return {"ok": False, "error": str(e)}
        threading.Thread(target=_restart, daemon=True).start()
        return {"ok": True}
    def plan(self): return core.day_plan()
    def stop(self): STOP.set(); return True
    def snooze(self, text, kind):
        STOP.set(); core.add_rem(text, dt.datetime.now() + dt.timedelta(minutes=5), kind); return D
    def clear_chat(self):
        D["chat"].clear(); core.save(); return D
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
    while True:
        time.sleep(4); now = dt.datetime.now(); fired = []
        for r in D["rem"]:
            if not r.get("on"): continue
            try: w = dt.datetime.strptime(r["when"], "%Y-%m-%d %H:%M")
            except ValueError: continue
            if w > now: continue
            fired.append(dict(r))
            if r["rep"] == "Один раз": r["on"] = False
            else:
                while w <= now:
                    w += dt.timedelta(days=7 if r["rep"] == "Каждую неделю" else 1)
                    while r["rep"] == "По будням" and w.weekday() > 4: w += dt.timedelta(days=1)
                r["when"] = w.strftime("%Y-%m-%d %H:%M")
        if fired:
            core.save()
            try: win.restore(); win.on_top = True; win.on_top = False
            except Exception: pass
            for r in fired:
                if not r.get("sound"): ring(r)
                try: win.evaluate_js("Krug.fire(%s)" % json.dumps(r, ensure_ascii=False))
                except Exception: pass
            try: win.evaluate_js("Krug.sync(%s)" % json.dumps({"rem": D["rem"]}, ensure_ascii=False))
            except Exception: pass

def main():
    global win
    html = open(res("ui.html"), encoding="utf-8").read()
    win = webview.create_window("Круг", html=html, js_api=Api(), width=1240, height=800, min_size=(960, 620), background_color="#0b0c10")
    webview.start(loop, storage_path=os.path.join(core.DIR, "web"))

if __name__ == "__main__":
    main()
