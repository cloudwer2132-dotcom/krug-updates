# -*- coding: utf-8 -*-
"""Krug Brain — умный офлайн-помощник с контекстом и структурой."""
import re, random, math, difflib, ast, operator, datetime as dt

# ============================================================
# КОНСТАНТЫ
# ============================================================
DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_RU = ["января","февраля","марта","апреля","мая","июня",
             "июля","августа","сентября","октября","ноября","декабря"]
MON = {"янв":1,"фев":2,"мар":3,"апр":4,"мая":5,"июн":6,"июл":7,"авг":8,"сен":9,"окт":10,"ноя":11,"дек":12}
WDN = ["пон","вто","сре","чет","пят","суб","вос"]

HELP = """Я Krug Brain — умный помощник. Понимаю фразы как люди:
⏰ «напомни через 15 минут позвонить маме» · «будильник на 7 утра по будням»
✅ «задача: сдать отчёт срочно» · «сделал отчёт» · «удали задачу молоко»
📆 «добавь в расписание пн,ср 18:00 английский»
📝 «заметка: идея про сайт» · 🔁 «привычка: зарядка»
🧮 «посчитай 15% от 2400» · 🎮 «игру змейка» · 🎨 «дизайн киберпанк»
🧠 «запомни: мой email alex@mail.ru» · «что ты обо мне знаешь»
Скажи «помощь» чтобы увидеть всё."""

# ============================================================
# УТИЛИТЫ
# ============================================================
_ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod, ast.USub: operator.neg}

def calc(e):
    try:
        def ev(n):
            if isinstance(n, ast.Expression): return ev(n.body)
            if isinstance(n, ast.Constant) and isinstance(n.value,(int,float)): return n.value
            if isinstance(n, ast.BinOp):
                a,b = ev(n.left), ev(n.right)
                if isinstance(n.op, ast.Pow) and abs(b) > 100: raise ValueError
                return _ops[type(n.op)](a,b)
            if isinstance(n, ast.UnaryOp): return _ops[type(n.op)](ev(n.operand))
            raise ValueError
        cleaned = e.replace("^","**").replace(",",".").replace("×","*").replace("÷","/")
        return ev(ast.parse(cleaned, mode="eval"))
    except: return None

def num(x): return str(int(x)) if float(x).is_integer() else f"{x:.4f}".rstrip("0").rstrip(".")

def find(items, q, key="text"):
    if not q or not items: return None
    q = q.lower()
    for it in items:
        if q in str(it.get(key,"")).lower(): return it
    try:
        c = difflib.get_close_matches(q, [str(i.get(key,"")).lower() for i in items], 1, 0.5)
        if c: return next((i for i in items if c[0]==str(i.get(key,"")).lower()), None)
    except: pass
    return None

# ============================================================
# ПАМЯТЬ КОНТЕКСТА
# ============================================================
class Context:
    """Хранит состояние диалога: что пользователь хотел, какие pending-операции."""
    def __init__(self):
        self.pending = None  # pending operation
        self.last_action = None  # что было сделано в прошлом шаге
        self.conversation = []  # последние N реплик
        self.learned = []  # факты из этого диалога

    def store_pending(self, kind, text, **kwargs):
        """Сохраняет pending-операцию: "добавь в задачи — потом: купить хлеб"."""
        self.pending = {"kind": kind, "text": text, **kwargs}

    def clear_pending(self):
        self.pending = None

    def record_action(self, action, details=""):
        self.last_action = {"action": action, "details": details, "ts": dt.datetime.now()}

    def add_conversation(self, role, text):
        self.conversation.append({"role": role, "text": text[:100]})
        if len(self.conversation) > 10:
            self.conversation = self.conversation[-10:]

_CONTEXT = Context()

# ============================================================
# ПАРСЕР ДАТЫ
# ============================================================
def parse_when(s, now):
    t = " "+s+" "; rep = "Один раз"; wk = False
    def take(p):
        nonlocal t
        m = re.search(p, t, re.I)
        if m: t = t[:m.start()]+" "+t[m.end():]
        return m

    if take(r"\bпо будням\b"): rep = "По будням"
    elif take(r"\b(?:каждый день|ежедневно)\b"): rep = "Каждый день"
    elif take(r"\b(?:каждую неделю|еженедельно)\b"): rep = "Каждую неделю"

    w = None
    m = take(r"через\s+((?:\d+\s*(?:мин|ч|дн|де|нед)\S*\s*)+|полчаса|полтора\s+часа|пару\s+минут|час\b|минуту)")
    if m:
        g = m[1].lower(); mins = 0
        for n,u in re.findall(r"(\d+)\s*(мин|ч|дн|де|нед)", g):
            mins += int(n)*{"мин":1,"ч":60,"дн":1440,"де":1440,"нед":10080}[u]
        if not mins: mins = 30 if "полчаса" in g else 90 if "полтора" in g else 2 if "пару" in g else 60
        w = (now + dt.timedelta(minutes=min(mins, 5256000))).replace(second=0, microsecond=0)
    else:
        day = None
        if take(r"\bпослезавтра\b"): day = now.date()+dt.timedelta(days=2)
        elif take(r"\bзавтра\b"): day = now.date()+dt.timedelta(days=1)
        elif take(r"\bсегодня\b"): day = now.date()
        else:
            m = take(r"\b(?:в|во|на)?\s*(понедельник|вторник|сред[ауы]|четверг|пятниц[ауы]|суббот[ауы]|воскресенье)\b")
            if m:
                idx = WDN.index(m[1][:3].lower()) if m[1][:3].lower() in WDN else -1
                if idx >= 0:
                    day = now.date() + dt.timedelta(days=(idx - now.weekday()) % 7)
                    wk = True
            else:
                m = take(r"\b(\d{1,2})\s+(янв|фев|мар|апр|мая|июн|июл|авг|сен|окт|ноя|дек)\S*")
                if m:
                    try:
                        day = dt.date(now.year, MON[m[2].lower()], int(m[1]))
                        if day < now.date(): day = day.replace(year=now.year+1)
                    except: day = None
        if not day:
            m = take(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b")
            if m:
                try:
                    y = int(m[3]) if m[3] else now.year
                    if y < 100: y += 2000
                    day = dt.date(y, int(m[2]), int(m[1]))
                    if not m[3] and day < now.date(): day = day.replace(year=y+1)
                except: pass
        hm = None
        m = take(r"\b(?:в|во|на|к|около)?\s*(\d{1,2})[:.](\d{2})\b")
        if m:
            if 0 <= int(m[1]) <= 23 and 0 <= int(m[2]) <= 59: hm = (int(m[1]), int(m[2]))
        else:
            m = take(r"\b(?:в|на|к)\s+(\d{1,2})(?:\s*(утра|вечера|дня|ночи)?)?\b")
            if m:
                h = int(m[1]); ap = (m[2] or "").lower()
                if ap in ("вечера","дня") and h < 12: h += 12
                if ap == "ночи" and h == 12: h = 0
                if h <= 23: hm = (h, 0)
        if not hm:
            m = take(r"\b(утром|днём|днем|вечером|ночью)\b")
            if m: hm = {"утр":(9,0),"днё":(13,0),"дне":(13,0),"веч":(19,0),"ноч":(23,0)}[m[1][:3].lower()]
        if not hm and not day: return None, s.strip(), rep
        if not day:
            w = now.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
            if w <= now: w += dt.timedelta(days=1)
        else:
            w = dt.datetime.combine(day, dt.time(*(hm or (9,0))))
            if wk and w <= now: w += dt.timedelta(days=7)
    return w, re.sub(r"\s+", " ", t).strip(" ,.-—:"), rep

# ============================================================
# НЕГАТИВНЫЕ ФИЛЬТРЫ
# ============================================================
_NEG_PAT = re.compile(r"^(?:не\s+|ни\s+|без\s+|отмени|отмену|выйти|bye|пока|хватит|стоп|выключ|отменяю|нет)\b")

def is_negative(l):
    """Проверяет негативный контекст."""
    if _NEG_PAT.search(l): return True
    if re.search(r"не\s+хочу|не\s+надо|не\s+нужно|без\s+|отмена|выход", l, re.I): return True
    return False

# ============================================================
# ИНТЕНТ-СИСТЕМА
# ============================================================
class Intent:
    def __init__(self, name, pattern, handler, neg=False, priority=0):
        self.name = name
        self.pattern = re.compile(pattern, re.I)
        self.handler = handler
        self.neg = neg  # игнорировать при негативе
        self.priority = priority

# Регистрация намерений
INTENTS = [
    # --- Справка ---
    Intent("help", r"^(помощь|help|что\s+ты\s+умеешь|команды|справка)",
           lambda E, l: HELP, neg=True),

    # --- Приветствие ---
    Intent("greet", r"^(привет|здравствуй|добрый\s+(день|вечер|утро)|хай|hello|hi)\b",
           lambda E, l: _handle_greet(E)),

    # --- Благодарность ---
    Intent("thanks", r"^(спасибо|благодарю|спс|thanks)\b",
           lambda E, l: "Всегда пожалуйста! 🙌", neg=True),

    # --- Кто ты ---
    Intent("whoami", r"^(кто\s+ты|ты\s+кто|что\s+ты\s+такое)\b",
           lambda E, l: "Я Krug Brain — встроенный умный помощник. Понимаю команды, даты, задачи, напоминания, планирование, музыку, игры и многое другое.", neg=True),

    # --- Вычисление ---
    Intent("calc", r"^(?:посчитай|сколько\s+будет|посчитай|сколько\s+процент|посчитай\s+(\d+)\s*%\s*от)\s*(.+)",
           lambda E, l: _handle_calc(l)),

    # --- Случайное ---
    Intent("random", r"(?:монетк|кубик)\b",
           lambda E, l: "🪙 "+random.choice(["Орёл","Решка"]) if "монетк" in l else "🎲 "+str(random.randint(1,6)), neg=True),
    Intent("random_choice", r"выбери\s+(.+?)(?:\s+или\s+|,)\s*(.+)",
           lambda E, l: "🎯 "+random.choice([x.strip() for x in re.sub(r".*?\s+или\s+|,","|",l).split("|") if x.strip()])),

    # --- Мотивация ---
    Intent("motivation", r"мотивац|вдохнови|поддержи",
           lambda E, l: "💬 "+random.choice(["Маленькие шаги каждый день сильнее редких рывков.","Начни — мотивация придёт во время работы.","Не идеально, а сделано.","Ты не обязан делать всё. Сделай самое важное.","Дисциплина — это забота о себе из будущего."]), neg=True),

    # --- Контекстные ответы (yes/no/done в контексте) ---
    Intent("context_yes", r"^(да|давай|добавь|добавь в задачи|добавить|ок|хорошо|сделай)\b",
           lambda E, l: _handle_context(E, "accept")),
    Intent("context_no", r"^(нет|не надо|не нужно|отмена|отменяю|стоп|хватит|выключ|не)\b",
           lambda E, l: _handle_context(E, "deny")),

    # --- Показать списки ---
    Intent("list_tasks", r"^(?:покажи|выведи|список|мои|что\s+у\s+меня\s+по).*задач",
           lambda E, l: _handle_list_tasks(E)),
    Intent("list_rem", r"^(?:покажи|выведи|список|мои).*(?:напоминани|будильник)\b",
           lambda E, l: _handle_list_rem(E)),
    Intent("list_notes", r"^(?:покажи|выведи|список|мои).*заметк",
           lambda E, l: _handle_list_notes(E)),
    Intent("list_habits", r"^(?:покажи|выведи|список|мои).*привычк",
           lambda E, l: _handle_list_habits(E)),

    # --- Поиск заметок ---
    Intent("search_notes", r"^(?:найди|поищи)\s+(?:заметку\s+)?(.+)",
           lambda E, l: _handle_search_notes(E, l)),

    # --- Расписание ---
    Intent("sched_day", r"расписание\s+на\s+(?:понедельник|вторник|среда|четверг|пятница|суббота|воскресенье|сегодня|завтра)",
           lambda E, l: _handle_sched_day(E, l)),
    Intent("sched_show", r"^(расписание|покажи\s+расписание|моё\s+расписание)\b",
           lambda E, l: _handle_sched_show(E)),

    # --- Удаление ---
    Intent("delete_task", r"^(?:удали|убери|отмени)\s+(?:задачу|задачи)\s*:?\s*(.+)",
           lambda E, l: _handle_delete(E, "tasks", l)),
    Intent("delete_rem", r"^(?:удали|убери|отмени)\s+(?:напоминание|будильник)\s*:?\s*(.+)",
           lambda E, l: _handle_delete(E, "rem", l)),
    Intent("delete_note", r"^(?:удали|убери|отмени)\s+(?:заметку)\s*:?\s*(.+)",
           lambda E, l: _handle_delete(E, "notes", l)),
    Intent("delete_done", r"удали\s+(?:все\s+)?выполненн",
           lambda E, l: _handle_delete_done(E), neg=True),

    # --- Выполнение ---
    Intent("complete", r"^(?:я\s+)?(?:выполнил[а]?|сделал[а]?|закончил[а]?|завершил[а]?|готово|отметь\s+выполненной)\s*:?\s*(.+)",
           lambda E, l: _handle_complete(E, l)),

    # --- Звук ---
    Intent("sound_create", r"(?:звук|мелоди|рингтон|сигнал|звонок).*(?:создай|сделай|напиши|сгенерир)\b",
           lambda E, l: _handle_sound_create(E, l)),
    Intent("sound_set", r"(?:постав|установ|назнач|смени|поменя|использу).*(?:звук|мелоди|колокол|сигнал)",
           lambda E, l: _handle_sound_set(E, l)),
    Intent("sound_check", r"(?:какой\s+звук|что\s+за\s+звук|какая\s+мелоди)",
           lambda E, l: _handle_sound_check(E)),

    # --- Игры ---
    Intent("game", r"(?:игру\s+)?(?:змейк|змейка|пинг|понг|арканоид|тетрис|tetris|flappy|флапп|2048)\b",
           lambda E, l: _handle_game(E, l)),
    Intent("game_dino", r"(?:игру\s+)?(?:динозавр|dino)\b",
           lambda E, l: "🦖 Динозаврик в левом нижнем углу (Canvas). Клик или пробел — прыжок."),

    # --- Дизайн ---
    Intent("design", r"(?:сделай|создай|перерисуй|обнови)\s+(?:дизайн|интерфейс|скин|оформление)|киберпанк|уют|minimalist|минимал|неон|океан|закат|лес|сакура|золото|матрица|космос|ретро|акцент\s+\w+|круглее|звёзды\s+на\s+фоне|сетк",
           lambda E, l: "🎨 Перерисовка через подключённый ИИ (Настройки). Без ИИ: могу применить стили «"+", ".join(["киберпанк","уют","минимализм","неон","океан","закат","лес","сакура","золото","матрица","космос","ретро"])+"»."),

    # --- Напоминание ---
    Intent("set_reminder", r"напомни|будильн|разбуди|таймер",
           lambda E, l: _handle_set_reminder(E, l)),

    # --- Память ---
    Intent("mem_store", r"^запомни:\s*(.+?)\s*(?:=|—| - | это )\s*(.+)",
           lambda E, l: _handle_mem_store(E, l)),
    Intent("mem_store_val", r"^запомни:\s*(.+)",
           lambda E, l: _handle_mem_store_val(E, l)),
    Intent("mem_forget", r"^забудь\s+(?:что\s+)?(.+)",
           lambda E, l: _handle_mem_forget(E, l)),
    Intent("mem_show", r"^(?:что\s+ты\s+помнишь|что\s+я\s+просил\s+запомнить|мои\s+факты|что\s+ты\s+знаешь\s+обо\s+мне|память|что\s+ты\s+знаешь)\b",
           lambda E, l: _handle_mem_show(E)),

    # --- План ---
    Intent("plan_day", r"^(?:план(?:\s+на\s+день)?|план\s+сегодня|составь\s+план|мой\s+план)\b",
           lambda E, l: E.get("day_plan", lambda: "Пока пусто. Добавь задачи или напоминания.")),
    Intent("plan_week", r"план\s+недел|на\s+недел|расписание\s+на\s+недел",
           lambda E, l: _handle_plan_week(E)),
    Intent("plan_priority", r"приоритиз|расставь\s+приоритет|что\s+важнее|с\s+чего\s+начать",
           lambda E, l: _handle_plan_priority(E)),
    Intent("plan_stats", r"итоги|статистик|как\s+я\s+справ",
           lambda E, l: _handle_plan_stats(E)),

    # --- Имя ---
    Intent("set_name", r"меня\s+зовут\s+(\w+)",
           lambda E, l: _handle_set_name(E, l)),
    Intent("ask_name", r"как\s+меня\s+зовут|кто\s+я",
           lambda E, l: "Тебя зовут "+(E["D"].get("mem",{}).get("name","") or "Не помню. Напиши «меня зовут …».")),

    # --- Время/дата ---
    Intent("time", r"который\s+час|сколько\s+времени",
           lambda E, l: f"🕐 Сейчас {dt.datetime.now():%H:%M}"),
    Intent("date", r"какое\s+сегодня\s+число|какая\s+сегодня\s+дата|какой\s+сегодня\s+день",
           lambda E, l: f"📅 Сегодня {dt.datetime.now().day} {MONTHS_RU[dt.datetime.now().month-1]} {dt.datetime.now().year}, {['понедельник','вторник','среда','четверг','пятница','суббота','воскресенье'][dt.datetime.now().weekday()]}"),

    # --- Советы ---
    Intent("tip", r"помодоро|эйзенхауэр|gtd|smart.*правило|лягушк|прокраст.*совет|сон.*совет|фокус.*совет|привычк.*совет|стресс.*совет",
           lambda E, l: _handle_tips(E, l)),

    # --- Промпт ---
    Intent("make_prompt", r"(?:напиши|сделай|создай|дай)\s+(?:мне\s+)?пр(о|м)пт(?:мпт)?\s*(?:для|на|про|на\s+пиш.+для)\s*(.+)",
           lambda E, l: _handle_make_prompt(E, l)),

    # --- Перевод/объяснение ---
    Intent("explain", r"(?:объясни|что\s+такое)\s+(.+)",
           lambda E, l: "Для объяснений подключите ИИ в «Настройках». Без ИИ я умею встроенные советы — напиши «помощь»."),
]

# ============================================================
# ГЛАВНЫЙ МОЗГ
# ============================================================
def think(m, E, _depth=0):
    """Парсит намерение → выполняет → возвращает ответ."""
    if m is None: return "Не понял команду."
    if _depth > 10: return "Напишите проще."

    D = E["D"]; now = dt.datetime.now()
    uid = E["uid"]; save = E["save"]; refresh = E["refresh_all"]
    mem = D.setdefault("mem", {}); mem.setdefault("facts", {}); mem.setdefault("name", "")
    tasks = D.get("tasks", [])
    sched = D.get("sched", [])
    rem = D.get("rem", [])
    notes = D.get("notes", [])
    habits = D.get("habits", [])
    sounds = D.get("sounds", [])

    # Контекст: pending-операции
    pending = _CONTEXT.pending

    l = m.lower().strip().rstrip("!?. ")

    # 1. Сначала проверяем контекстные команды (да/нет/сделано)
    ctx_result = _try_context(pending, l, D, E, uid, save, refresh, now, tasks, notes, habits)
    if ctx_result is not None: return ctx_result

    # 2. Ищем намерение
    best = None; best_match = None; best_pos = 999
    for intent in INTENTS:
        if intent.neg and is_negative(l): continue
        mm = intent.pattern.search(l)
        if mm and mm.start() < best_pos:
            best = intent; best_match = mm; best_pos = mm.start()

    # 3. Выполняем
    if best:
        return best.handler(E, l, D, now, uid, save, refresh, tasks, sched, rem, notes, habits, sounds)

    # 4. Если ничего не нашли — fallback
    return _fallback(l, D, E)

def _try_context(pending, l, D, E, uid, save, refresh, now, tasks, notes, habits):
    """Пытается выполнить pending-операцию из контекста."""
    if not pending: return None

    # "да/добавь/добавь в задачи" → принять
    if re.match(r"^(?:да|давай|добавь\s+(?:в\s+)?задачи?|добавить|ок|хорошо)\b", l):
        if pending["kind"] == "rem":
            w, rest, rep = parse_when("через 10 минут", now)
            if w:
                E["add_rem"](pending["text"], w, pending["kind"], rep) if E.get("add_rem") else rem.append({"id":uid(),"text":pending["text"],"when":w.strftime("%Y-%m-%d %H:%M"),"kind":pending["kind"],"rep":rep,"on":True})
                save(); refresh()
                _CONTEXT.clear_pending()
                _CONTEXT.record_action("set_reminder", pending["text"])
                return f"✅ Поставил: «{pending['text']}» на {w:%d.%m %H:%M}"
        elif pending["kind"] == "tasks":
            for t in pending.get("items", []):
                tasks.append({"id":uid(),"text":t,"prio":"Средний","due":"","done":False})
            save(); refresh()
            _CONTEXT.clear_pending()
            _CONTEXT.record_action("add_tasks", str(len(pending["items"]))+" задач")
            return f"✅ Добавил {len(pending['items'])} задач"
        elif pending["kind"] == "save":
            if l.startswith("задач"): tasks.append({"id":uid(),"text":pending["text"],"prio":"Средний","due":"","done":False})
            else: notes.append({"id":uid(),"title":pending["text"][:40],"body":pending["text"]})
            save(); refresh()
            _CONTEXT.clear_pending()
            _CONTEXT.record_action("save", pending["text"])
            return "✅ Сохранил"
        else:
            _CONTEXT.clear_pending()
            return "Хорошо, отменяю."

    # "нет/не надо/отмена" → отменить
    if re.match(r"^(?:нет|не\s+надо|не\s+нужно|отмена|отменяю|стоп|хватит)\b", l):
        _CONTEXT.clear_pending()
        _CONTEXT.record_action("cancel", "пользователь отменил")
        return "Хорошо, отменяю."

    return None

def _handle_greet(E):
    D = E["D"]; tasks = D.get("tasks",[]); rem = D.get("rem",[]); mem = D.setdefault("mem",{})
    n = len([t for t in tasks if not t.get("done")])
    nx = sorted([r_.get("when","") for r_ in rem if r_.get("on")])
    nm = (", "+mem.get("name","")) if mem.get("name") else ""
    return f"Привет{nm}! 👋 Открытых задач: {n}."+(f" Ближайшее: {nx[0]}." if nx else "")+" Напиши «план» для дня."

def _handle_calc(l):
    expr = re.sub(r"^(?:посчитай|сколько\s+будет|посчитай\s+\d+\s*%\s*от|сколько\s+процент)\s*", "", l)
    # Процент
    m = re.match(r"(\d+(?:[.,]\d+)?)\s*%\s*от\s*(\d+(?:[.,]\d+)?)", l)
    if m: return "🧮 = "+num(float(m[1].replace(",","."))*float(m[2].replace(",","."))/100)
    if not re.search(r"\d", expr): return "Что посчитать?"
    result = calc(expr)
    return "🧮 = "+num(result) if result is not None else "Не смог посчитать."

def _handle_list_tasks(E):
    tasks = E["D"].get("tasks",[])
    ts = sorted([t for t in tasks if not t.get("done")], key=lambda t:({"Высокий":0,"Средний":1,"Низкий":2}.get(t.get("prio","Ср"),1),t.get("due") or "9"))
    if not ts: return "Открытых задач нет 🎉"
    return "✅ Задачи:\n"+"\n".join(f"  {i}. [{t.get('prio','Ср')[0]}] {t.get('text','')}"+" (до "+t["due"]+")" if t.get("due") else "" for i,t in enumerate(ts,1))

def _handle_list_rem(E):
    rem = E["D"].get("rem",[])
    rs = sorted([x for x in rem if x.get("on")], key=lambda x:x.get("when",""))
    return "⏰ Активные:\n"+"\n".join(f"  {x.get('when','')} — {x.get('text','')} ({x.get('rep','')})" for x in rs) if rs else "Активных напоминаний нет."

def _handle_list_notes(E):
    notes = E["D"].get("notes",[])
    return "📝 Заметки:\n"+"\n".join("  • "+n.get("title","") for n in notes[-15:]) if notes else "Заметок пока нет."

def _handle_list_habits(E):
    habits = E["D"].get("habits",[]); now = dt.datetime.now(); td = now.date().isoformat()
    return "🔁 Привычки:\n"+"\n".join(f"  {'✅' if td in h.get('log',[]) else '⬜'} {h.get('text','')} (серия {len(h.get('log',[]))})" for h in habits) if habits else "Привычек пока нет."

def _handle_search_notes(E, l):
    notes = E["D"].get("notes",[]); m = re.match(r"^(?:найди|поищи)\s+(?:заметку\s+)?(.+)", l)
    q = (m.groups()[0] if m else l)[:6].lower()
    hits = [n for n in notes if q in (n.get("title","")+n.get("body","")).lower()]
    return "🔎 Нашёл:\n"+"\n".join(f"  • {n.get('title','')}: {n.get('body','')[:80]}" for n in hits[:8]) if hits else "Ничего не нашёл."

def _handle_sched_day(E, l):
    sched = E["D"].get("sched",[]); now = dt.datetime.now()
    m = re.match(r".*(понедельник|вторник|среда|четверг|пятница|суббота|воскресенье|сегодня|завтра)", l, re.I)
    day_name = m.group(1).lower() if m else "сегодня"
    if day_name == "сегодня": di = now.weekday()
    elif day_name == "завтра": di = (now.weekday()+1)%7
    else: di = WDN.index(day_name[:3].lower()) if day_name[:3].lower() in WDN else now.weekday()
    it = sorted([x for x in sched if x.get("day","")==DAYS[di]], key=lambda x:x.get("time",""))
    return f"📆 {DAYS[di]}:\n"+("\n".join(f"  {x.get('time','')} — {x.get('text','')}" for x in it) if it else f"На {DAYS[di]} ничего не запланировано.")

def _handle_sched_show(E):
    sched = E["D"].get("sched",[])
    rows = sorted(sched, key=lambda x:(DAYS.index(x.get("day","")) if x.get("day","") in DAYS else 9, x.get("time","")))
    return "📆 Расписание:\n"+("\n".join(f"  {x.get('day','')} {x.get('time','')} — {x.get('text','')}" for x in rows) if rows else "Расписание пусто.")

def _handle_delete(E, kind, l):
    D = E["D"]; tasks = D.get("tasks",[]) if kind == "tasks" else D.get(kind, [])
    m = re.match(r"^(?:удали|убери|отмени)\s+(?:задачу|напоминание|заметку)\s*:?\s*(.+)", l, re.I)
    txt = (m.group(1) if m else l).strip()
    it = find(tasks, txt, "title" if kind == "notes" else "text")
    if it:
        tasks.remove(it); E["save"](); E["refresh_all"]()
        return "🗑 Удалил: "+it.get("text",it.get("title",""))
    return "Не нашёл."

def _handle_delete_done(E):
    tasks = E["D"].get("tasks",[]); n = len([t for t in tasks if t.get("done")])
    E["D"]["tasks"][:] = [t for t in tasks if not t.get("done")]; E["save"](); E["refresh_all"]()
    return f"🗑 Убрал выполненных: {n}"

def _handle_complete(E, l):
    D = E["D"]; tasks = D.get("tasks",[]); habits = D.get("habits",[]); now = dt.datetime.now(); td = now.date().isoformat()
    m = re.match(r".*(?:задачу|привычку)??:?\s*(.+)", l, re.I)
    txt = (m.group(1) if m else l).strip()
    # Сначала привычки
    h = find(habits, txt) if "привыч" in l else None
    if not h: h = find([t for t in tasks if not t.get("done")], txt)
    if h:
        if "привыч" in l:
            if td not in h.get("log",[]): h["log"].append(td)
        else:
            h["done"] = True
        E["save"](); E["refresh_all"]()
        return f"{'🔥' if 'привыч' in l else '✅'} {'Отмечено' if 'привыч' in l else 'Выполнено'}: {h.get('text','')}. Так держать!"
    return "Не нашёл такое."

def _handle_sound_create(E, l):
    d = re.sub(r".*(?:создай|сделай|напиши|сгенерир)\s+", "", l).strip() or "приятный звук"
    al = bool(re.search(r"будильн|разбуд|просып", l))
    return f"🎵 Сочиняю: «{d}»." + (" Поставлю на будильник." if al else " Добавлю в библиотеку.")

def _handle_sound_set(E, l):
    sounds = E["D"].get("sounds",[]); rem = E["D"].get("rem",[])
    pick = next((s for s in sounds if s.get("name","").lower() in l), None)
    if not pick and sounds: pick = sounds[-1]
    if not pick: return "Нет звуков. Сначала создай."
    act = sorted([r for r in rem if r.get("on")], key=lambda x:x.get("when",""))
    if re.search(r"будильн", l): act = [r for r in act if r.get("kind")=="Будильник"] or act
    if not act: return "Нет активных напоминаний."
    act[0]["sound"] = pick["id"]; E["save"](); E["refresh_all"]()
    return f"🎵 Поставил «{pick['name']}» на «{act[0].get('text','')}»."

def _handle_sound_check(E):
    sounds = E["D"].get("sounds",[]); rem = E["D"].get("rem",[])
    act = sorted([r for r in rem if r.get("on")], key=lambda x:x.get("when",""))
    if not act: return "Нет активных напоминаний."
    s0 = next((x for x in sounds if x["id"]==act[0].get("sound")), None)
    return f"Звук: «{s0.get('name','')}»" if s0 else "Обычный."

def _handle_game(E, l):
    game = re.sub(r".*(?:игру\s+)?(?:змейк|змейка|пинг|понг|арканоид|тетрис|flappy|2048).*", "", l).strip() or "змейка"
    return f"🎮 Игру «{game}» в левом нижнем углу (Canvas). Клик/пробел — играть."

def _handle_set_reminder(E, l):
    D = E["D"]; now = dt.datetime.now(); rem = D.get("rem",[])
    kind = "Будильник" if re.search(r"будильн|разбуди", l) else "Напоминание"
    src = re.sub(r"таймер на", "через", l, flags=re.I)
    w, rest, rep = parse_when(src, now)
    txt = re.sub(r".*(?:напомни|будильн|разбуди|таймер|пожалуйста|ок|поставь|установи).*","", rest, flags=re.I).strip()
    txt = txt or ("Будильник" if kind=="Будильник" else kind)
    if w:
        E["add_rem"](txt, w, kind, rep) if E.get("add_rem") else rem.append({"id":E["uid"](),"text":txt,"when":w.strftime("%Y-%m-%d %H:%M"),"kind":kind,"rep":rep,"on":True})
        E["save"](); E["refresh_all"]()
        return f"✅ {kind}: «{txt}» — {w:%d.%m %H:%M}" + (f", {rep.lower()}" if rep != "Один раз" else "")
    # Pending
    _CONTEXT.store_pending("rem", txt, kind=kind)
    return f"На какое время: «{txt}»? (через 20 минут / завтра в 9:00)"

def _handle_mem_store(E, l):
    m = re.match(r"^запомни:\s*(.+?)\s*(?:=|—| - | это )\s*(.+)", l, re.I)
    if not m: return None
    k, v = m.group(1).strip(), m.group(2).strip()
    E["mem_add"](f"{k}: {v}", "Факты", pin=True) if E.get("mem_add") else None
    E["save"]()
    return f"🧠 Запомнил: {k} → {v}"

def _handle_mem_store_val(E, l):
    m = re.match(r"^запомни:\s*(.+)", l, re.I)
    if not m: return None
    text = m.group(1).strip()
    if E.get("mem_add_msg"): return E["mem_add_msg"](text)
    E["save"]()
    return f"🧠 Запомнил: {text[:60]}"

def _handle_mem_forget(E, l):
    m = re.match(r"^забудь\s+(?:что\s+)?(.+)", l, re.I)
    if not m: return None
    q = m.group(1).strip().lower()
    M = E["D"].setdefault("memory",[])
    gone = [x for x in M if q in x.get("t","").lower()]
    for x in gone: M.remove(x)
    E["save"]()
    return f"🗑 Забыл: {len(gone)} записей." if gone else f"Про «{q}» ничего нет."

def _handle_mem_show(E):
    M = E["D"].get("memory",[])
    if not M: return "Пока ничего не знаю."
    cats = ["Обо мне","Предпочтения","Проекты","Люди","Факты","Прочее"]
    out = ["🧠 Что я знаю:"]
    for c in cats:
        xs = [x for x in M if x.get("cat")==c]
        if xs: out += [c+":"] + ["  • "+x["t"] for x in xs[:6]]
    return "\n".join(out)

def _handle_plan_week(E):
    D = E["D"]; now = dt.datetime.now(); sched = D.get("sched",[]); tasks = D.get("tasks",[]); rem = D.get("rem",[])
    L = ["🗓 Неделя:"]; mon = now.date()-dt.timedelta(days=now.weekday())
    for i,d in enumerate(DAYS):
        day = mon+dt.timedelta(days=i); mark = " ← сегодня" if day==now.date() else ""
        it = [f"{x.get('time','')} {x.get('text','')}" for x in sorted(sched, key=lambda x:x.get("time","")) if x.get("day")==d]
        it += [f"до: {t.get('text','')}" for t in tasks if not t.get("done") and t.get("due")==day.isoformat()]
        L.append(f"  {d} {day:%d.%m}{mark}: "+("; ".join(it) if it else "—"))
    return "\n".join(L)

def _handle_plan_priority(E):
    D = E["D"]; near = (dt.datetime.now()+dt.timedelta(days=2)).strftime("%Y-%m-%d"); tasks = D.get("tasks",[]); q = {k:[] for k in "abcd"}
    for t in tasks:
        if t.get("done"): continue
        urg = t.get("prio")=="Высокий" or (t.get("due") and t["due"]<=near)
        imp = t.get("prio") != "Низкий"
        q["a" if urg and imp else "b" if imp else "c" if urg else "d"].append(t.get("text",""))
    nm = {"a":"🔥 Сделай сейчас","b":"📅 Запланируй","c":"🤝 Делегируй","d":"🗑 Удали"}
    out = [f"{nm[k]}:\n"+"\n".join("  • "+x for x in v) for k,v in q.items() if v]
    return "🧭 Приоритеты:\n\n"+"\n\n".join(out) if out else "Открытых задач нет."

def _handle_plan_stats(E):
    D = E["D"]; tasks = D.get("tasks",[]); habits = D.get("habits",[]); now = dt.datetime.now(); td = now.date().isoformat()
    done = len([t for t in tasks if t.get("done")]); op = len(tasks)-done
    hb = len([h for h in habits if td in h.get("log",[])])
    return f"📊 Задач выполнено: {done}/{len(tasks)}. Привычек сегодня: {hb}/{len(habits)}. "+("Отличный прогресс!" if done > op else " Выбери одну главную задачу.")

def _handle_set_name(E, l):
    D = E["D"]; m = re.search(r"зовут\s+(\w+)", l, re.I)
    if m:
        name = m.group(1).capitalize(); D.setdefault("mem",{})["name"] = name
        E["save"]()
        if E.get("mem_add"): E["mem_add"]("Пользователя зовут "+name, "Обо мне")
        return f"Приятно познакомиться, {name}! 🙂"
    return "Как тебя зовут?"

def _handle_tips(E, l):
    tips = {
        "помодоро": "🍅 Помодоро: 25 мин работы → 5 мин отдыха; 4 цикла → перерыв 15-30 мин. Таймер во вкладке «Фокус».",
        "эйзенхауэр": "🧭 Срочно+Важно → делай. Важно → планируй. Срочно → делегируй. Ни то → удаляй.",
        "gtd": "📥 Собери всё → реши → следующее действие → делегируй/запланируй/сделай. Раз в неделю — обзор.",
        "smart": "🎯 Конкретная, измеримая, достижимая, значимая, с дедлайном.",
        "лягушк": "🐸 Самое неприятное дело — первым с утра.",
        "прокраст": "🐢 Первый шаг на 5 минут. Разбей задачу. Убери отвлекающее.",
        "сон": "😴 7-9 часов, без экранов за 40 мин до сна, прохладная комната.",
        "фокус": "🎧 Одна задача, уведомления выключены, блок 25-50 мин.",
        "привычк": "🔁 Микро-версия (2 мин). Привяжи к действию. Не пропускай 2 дня.",
        "стресс": "🌿 Выпиши тревоги → раздели на «могу»/«не могу» → шаг по первому.",
    }
    for k,tip in tips.items():
        if k in l: return tip
    return "Нет совета для этого запроса."

def _handle_make_prompt(E, l):
    m = re.search(r"пр(о|м)пт(?:мпт)?\s*(?:для|на|про|на\s+пиш.+для)\s*(.+)", l, re.I)
    topic = (m.group(1) if m else l).strip()
    if not topic: return "Для чего промпт?"
    roles = {
        "код|програм|python|скрипт|сайт|бот": ("senior-разработчик","Код в блоках, пояснение, граничные случаи"),
        "картин|рисун|логотип|дизайн": ("арт-директор","Сюжет, стиль, свет, камера, палитра"),
        "текст|статья|пост|реклам|письм": ("копирайтер","3 варианта: заголовок + текст + призыв"),
        "объясни|учёб|урок": ("репетитор","Простое объяснение, пример, 3 вопроса"),
    }
    for pat,(role,fmt) in roles.items():
        if re.search(pat, topic, re.I):
            return f"## Роль\nТы — {role}.\n\n## Задача\n{topic[0].upper()+topic[1:]}\n\n## Формат\n{fmt}"
    return f"## Роль\nТы — эксперт.\n\n## Задача\n{topic[0].upper()+topic[1:]}\n\n## Формат\nСтруктурированный ответ."

def _fallback(l, D, E):
    out = []
    # Проверяем заметки на похожие темы
    notes = D.get("notes",[]); words = re.findall(r"\w{4,}", l)
    hits = [n.get("title","") for n in notes if any(w[:5] in (n.get("title","")+n.get("body","")).lower() for w in words)][:3]
    if hits: out.append("🔎 В заметках: "+"; ".join(hits))
    # Предлагаем похожие команды
    EX = ["напомни через 10 минут выпить воды","будильник на 7:00","задача: купить хлеб","покажи задачи","план на день","составь план изучения английского","заметка: идея","привычка: зарядка","приоритизируй задачи","разбей задачу на шаги","что такое помодоро","мотивация"]
    try:
        c = difflib.get_close_matches(l, EX, 2, 0.4)
        if c: out.append("Возможно, ты имел в виду:\n"+"\n".join("• "+x for x in c))
    except: pass
    # Запоминаем что не поняли
    _CONTEXT.store_pending("save", l)
    return "\n".join(out) if out else None
