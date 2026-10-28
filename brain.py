# -*- coding: utf-8 -*-
"""Krug Brain — встроенный офлайн-помощник. Архитектура: parse → intent → action → verify."""
import re, random, math, difflib, ast, operator, datetime as dt

# ============================================================
# КОНСТАНТЫ
# ============================================================
DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_RU = ["января", "февраля", "марта", "апреля", "мая", "июня",
             "июля", "августа", "сентября", "октября", "ноября", "декабря"]
MON = {"янв": 1, "фев": 2, "мар": 3, "апр": 4, "мая": 5, "июн": 6,
       "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12}
WDN = ["пон", "вто", "сре", "чет", "пят", "суб", "вос"]
WDN_FULL = {"понедельник": 0, "вторник": 1, "среда": 2, "четверг": 3,
            "пятница": 4, "суббота": 5, "воскресенье": 6}

HELP = """Я Krug Brain — встроенный офлайн-помощник. Понимаю обычные фразы:
⏰ «напомни через полчаса позвонить маме» · «напомни в пятницу в 18:00 встреча» · «будильник на 7 утра по будням» · «таймер на 10 минут»
✅ «задача: сдать отчёт срочно до 5 января» · «мне нужно купить молоко» · «покажи задачи» · «сделал отчёт» · «удали задачу молоко»
📆 «добавь в расписание пн,ср 18:00 английский» · «расписание на пятницу»
📝 «заметка: идея про сайт» · «найди заметку сайт» · 🔁 «привычка: зарядка» · «отметь привычку зарядка»
🗓 «план» · «план недели» · «приоритизируй задачи» · «итоги»
🧩 «составь план изучения Python на 8 недель» · «разбей задачу написать диплом на шаги» · «план тренировок» · «режим дня»
✨ «напиши промпт для логотипа кофейни» · 🧮 «посчитай 15% от 2400» · «сколько дней до 1 января» · «выбери чай или кофе»
🎵 «создай приятный звук для будильника» · «поставь звук колокольчик на будильник» · «какой звук на будильнике»
🎨 «сделай дизайн киберпанк» · «акцент красный» · «круглее» · «звёзды на фоне» · «перерисуй интерфейс сам» (со своим ИИ)
🎮 «создай игру змейка / пинг-понг / арканоид / flappy / 2048 / тетрис» · 🦖 «создай игру динозаврик» · «сделай лендинг для кофейни»
📂 «открой калькулятор / блокнот / chrome» (всегда спрашиваю разрешение) · 🎧 «включи музыку спокойный lo-fi» · «что за песня: <строчка>»
🎓 «когда я пишу утро — план» · «научи: …» · «забудь про …» · «что ты знаешь обо мне»
🧠 «запомни: пароль от вайфая = 12345» · «что такое помодоро» · «мотивация» · «меня зовут Алекс»"""

QUOTES = [
    "Маленькие шаги каждый день сильнее редких рывков.",
    "Начни — мотивация придёт во время работы.",
    "Не идеально, а сделано. Улучшишь потом.",
    "Ты не обязан делать всё. Сделай самое важное.",
    "Дисциплина — это забота о себе из будущего.",
    "5 минут — тоже прогресс.",
]

# ============================================================
# УТИЛИТЫ
# ============================================================
_ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
        ast.USub: operator.neg, ast.FloorDiv: operator.floordiv}

def calc(e):
    """Безопасное вычисление математических выражений."""
    def ev(n):
        if isinstance(n, ast.Expression): return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return n.value
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and abs(b) > 100: raise ValueError
            return _ops[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp): return _ops[type(n.op)](ev(n.operand))
        raise ValueError
    try:
        cleaned = e.replace("^", "**").replace(",", ".").replace("×", "*").replace("÷", "/")
        return ev(ast.parse(cleaned, mode="eval"))
    except Exception:
        return None

def num(x):
    return str(int(x)) if float(x).is_integer() else f"{x:.4f}".rstrip("0").rstrip(".")

def find(items, q, key="text"):
    q = q.lower().strip()
    if not q or not items: return None
    for it in items:
        if q in str(it.get(key, "")).lower(): return it
    try:
        c = difflib.get_close_matches(q, [str(i.get(key, "")).lower() for i in items], 1, 0.5)
        if c:
            return next((i for i in items if c[0] == str(i.get(key, "")).lower()), None)
    except Exception:
        pass
    return None

def _sim(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio() if difflib else (1.0 if a == b else 0.0)

# ============================================================
# ПАРСЕР ДАТЫ/ВРЕМЕНИ
# ============================================================
def parse_when(s, now):
    """Парсит относительные и абсолютные даты из текста. Возвращает (datetime, оставшийся_текст, rep)."""
    t = " " + s + " "; rep = "Один раз"; wk = False

    def take(p):
        nonlocal t
        m = re.search(p, t, re.I)
        if m: t = t[:m.start()] + " " + t[m.end():]
        return m

    # Повтор
    if take(r"\bпо будням\b"): rep = "По будням"
    elif take(r"\b(?:каждый день|ежедневно)\b"): rep = "Каждый день"
    elif take(r"\b(?:каждую неделю|еженедельно)\b"): rep = "Каждую неделю"

    w = None
    # Относительное время
    m = take(r"через\s+((?:\d+\s*(?:мин|ч|дн|де|нед)\S*\s*)+|полчаса|полтора\s+часа|пару\s+минут|час\b|минуту)")
    if m:
        g = m[1].lower(); mins = 0
        for n, u in re.findall(r"(\d+)\s*(мин|ч|дн|де|нед)", g):
            mins += int(n) * {"мин": 1, "ч": 60, "дн": 1440, "де": 1440, "нед": 10080}[u]
        if not mins:
            mins = 30 if "полчаса" in g else 90 if "полтора" in g else 2 if "пару" in g else 1 if re.search(r"\d", g) else 60
        mins = min(mins, 3650 * 1440)
        w = (now + dt.timedelta(minutes=mins)).replace(second=0, microsecond=0)
    else:
        day = None
        if take(r"\bпослезавтра\b"): day = now.date() + dt.timedelta(days=2)
        elif take(r"\bзавтра\b"): day = now.date() + dt.timedelta(days=1)
        elif take(r"\bсегодня\b"): day = now.date()
        else:
            m = take(r"\b(?:в|во|на)?\s*(понедельник|вторник|сред[ауы]|четверг|пятниц[ауы]|суббот[ауы]|воскресенье)\b")
            if m:
                day = now.date() + dt.timedelta(days=(WDN_FULL.get(m[1][:8].lower(), -1) if len(m[1]) >= 4
                                                       else WDN.index(m[1][:3].lower()) if m[1][:3].lower() in WDN
                                                       else -1) % 7) if m and m[1][:8].lower() in WDN_FULL else (
                    now.date() + dt.timedelta(days=(WDN.index(m[1][:3].lower()) - now.weekday()) % 7))
                wk = True
            else:
                m = take(r"\b(\d{1,2})\s+(янв|фев|мар|апр|мая|июн|июл|авг|сен|окт|ноя|дек)\S*")
                if m:
                    try:
                        day = dt.date(now.year, MON[m[2].lower()], int(m[1]))
                        if day < now.date(): day = day.replace(year=now.year + 1)
                    except ValueError: day = None
        if day is None:
            m = take(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b")
            if m:
                try:
                    y = int(m[3]) if m[3] else now.year
                    if y < 100: y += 2000
                    day = dt.date(y, int(m[2]), int(m[1]))
                    if not m[3] and day < now.date(): day = day.replace(year=y + 1)
                except ValueError: day = None
        hm = None
        m = take(r"\b(?:в|во|на|к|около)?\s*(\d{1,2})[:.](\d{2})\b")
        if m:
            if int(m[1]) > 23 or int(m[2]) > 59: return None, s.strip(), rep
            hm = (int(m[1]), int(m[2]))
        else:
            m = take(r"\b(?:в|на|к)\s+(\d{1,2})(?:\s*(утра|вечера|дня|ночи|час\S*))?\b")
            if m:
                h = int(m[1]); ap = (m[2] or "").lower()
                if ap in ("вечера", "дня") and h < 12: h += 12
                if ap == "ночи" and h == 12: h = 0
                hm = (h, 0) if h <= 23 else None
        if not hm:
            m = take(r"\b(утром|днём|днем|вечером|ночью)\b")
            if m: hm = {"утр": (9, 0), "днё": (13, 0), "дне": (13, 0), "веч": (19, 0), "ноч": (23, 0)}[m[1][:3].lower()]
        if hm is None and day is None: return None, s.strip(), rep
        if day is None:
            w = now.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
            if w <= now: w += dt.timedelta(days=1)
        else:
            w = dt.datetime.combine(day, dt.time(*(hm or (9, 0))))
            if wk and w <= now: w += dt.timedelta(days=7)
    return w, re.sub(r"\s+", " ", t).strip(" ,.-—:"), rep

# ============================================================
# ИНТЕНТ-ПАКТЕРЫ — с НЕГАТИВНЫМИ ФИЛЬТРАМИ
# ============================================================
_NEG = r"(?:не\s+|ни\s+|без\s+|отмени|отмену|выход|quit|bye|пока|до\s+свидания|хватит|стоп|досвидания)"

INTENTS = [
    # --- Справка ---
    {"id": "help", "pat": re.compile(r"^(помощь|help|что\s+ты\s+умеешь|что\s+умеешь|команды|справка)", re.I),
     "neg": re.compile(_NEG, re.I), "reply": HELP},

    # --- Приветствие ---
    {"id": "greet", "pat": re.compile(r"^(привет|здравствуй|добрый\s+(день|вечер|утро)|хай|салют|hello|hi)", re.I), "neg": re.compile(_NEG, re.I)},

    # --- Благодарность ---
    {"id": "thanks", "pat": re.compile(r"^(спасибо|благодарю|спс|thanks)", re.I), "neg": re.compile(_NEG, re.I), "reply": "Всегда пожалуйста! 🙌"},

    # --- Кто ты ---
    {"id": "whoami", "pat": re.compile(r"^(кто\s+ты|ты\s+кто|ты\s+ии?|что\s+ты)", re.I), "neg": re.compile(_NEG, re.I),
     "reply": "Я Krug Brain — встроенный офлайн-помощник Круга. Выполняю команды, понимаю даты, планирую и помню факты."},

    # --- Вычисление ---
    {"id": "calc", "pat": re.compile(r"^(?:посчитай|сколько\s+будет|calc|=|(?=.*\d.*[\+\-*/^%×÷]).{3,})"),
     "neg": re.compile(_NEG, re.I)},

    # --- Загадка (монетка/кубик) ---
    {"id": "random", "pat": re.compile(r"монетк|кубик|выбери.+(?:или|,)"), "neg": re.compile(_NEG, re.I)},

    # --- Мотивация ---
    {"id": "motivation", "pat": re.compile(r"мотивац|вдохнови|поддержи|демотивац|плохо"), "neg": re.compile(_NEG, re.I)},

    # --- Показ задач ---
    {"id": "list_tasks", "pat": re.compile(r"^(?:покажи|выведи|список|мои|что\s+у\s+меня\s+по|какие).*задач|^задачи$"),
     "neg": re.compile(_NEG, re.I)},

    # --- Показ напоминаний ---
    {"id": "list_rem", "pat": re.compile(r"^(?:покажи|выведи|список|мои).*(?:напоминани|будильник)", re.I),
     "neg": re.compile(_NEG, re.I)},

    # --- Показ заметок ---
    {"id": "list_notes", "pat": re.compile(r"^(?:покажи|выведи|список|мои).*заметк", re.I),
     "neg": re.compile(_NEG, re.I)},

    # --- Показ привычек ---
    {"id": "list_habits", "pat": re.compile(r"^(?:покажи|выведи|список|мои).*привычк", re.I),
     "neg": re.compile(_NEG, re.I)},

    # --- Поиск заметок ---
    {"id": "search_notes", "pat": re.compile(r"^(?:найди|поищи)\s+(?:заметку\s+)?(.+)", re.I)},

    # --- Расписание ---
    {"id": "schedule_day", "pat": re.compile(r"расписание\s+на\s+(понедельник|вторник|среда|четверг|пятница|суббота|воскресенье|сегодня|завтра)", re.I),
     "neg": re.compile(_NEG, re.I)},
    {"id": "schedule_show", "pat": re.compile(r"^(?:расписание|покажи\s+расписание|моё\s+расписание|мое\s+расписание)", re.I),
     "neg": re.compile(_NEG, re.I)},

    # --- Удаление задачи/напоминания/заметки/привычки ---
    {"id": "delete_item", "pat": re.compile(r"^(?:удали|убери|отмени)\s+(?:все\s+)?(?:задачу|задачи|напоминание|будильник|заметку|привычку)\s*:?\s*(.+)", re.I)},
    {"id": "delete_done", "pat": re.compile(r"удали\s+(?:все\s+)?выполненн", re.I),
     "neg": re.compile(_NEG, re.I)},

    # --- Выполнение ---
    {"id": "complete_item", "pat": re.compile(r"^(?:я\s+)?(?:выполнил[а]?|сделал[а]?|закончил[а]?|заверши[ла]?|готово|отметь(?:\s+выполненной)?)\s*(?:задачу|привычку)??:?\s*(.+)", re.I)},

    # --- Звук ---
    {"id": "sound_create", "pat": re.compile(r"звук|мелоди|рингтон|сигнал|звонок"),
     "neg": re.compile(_NEG, re.I)},
    {"id": "sound_set", "pat": re.compile(r"постав|установ|назнач|смени|поменя|использу"),
     "neg": re.compile(_NEG, re.I)},

    # --- Игры ---
    {"id": "game", "pat": re.compile(r"\bигр|game|поигра|сыграем|змейк|понг|арканоид|flappy|флапп|тетрис|tetris|2048"),
     "neg": re.compile(_NEG, re.I)},
    {"id": "game_dino", "pat": re.compile(r"динозавр|dino", re.I),
     "neg": re.compile(_NEG, re.I)},

    # --- Дизайн ---
    {"id": "design", "pat": re.compile(r"(?:сделай|создай|перерисуй|обнови).*дизайн|киберпанк|уют|minimalist|минимал|неон|океан|закат|лес|сакура|золото|матрица|космос|ретро|акцент\s+\w+|круглее|звёзды|сетк", re.I),
     "neg": re.compile(_NEG, re.I)},

    # --- Напоминание/будильник ---
    {"id": "set_reminder", "pat": re.compile(r"напомни|будильн|разбуди|таймер"),
     "neg": re.compile(_NEG, re.I)},

    # --- Запомнить ---
    {"id": "mem_store", "pat": re.compile(r"^запомни:\s*(.+?)\s*(?:=|—| - | это )\s*(.+)", re.I)},
    {"id": "mem_store_val", "pat": re.compile(r"^запомни:?\s*(.+)$", re.I)},

    # --- Забыть ---
    {"id": "mem_forget", "pat": re.compile(r"^забудь\s+(?:что\s+)?(.+)", re.I)},

    # --- Показать память ---
    {"id": "mem_show", "pat": re.compile(r"^(?:что\s+ты\s+помнишь|что\s+я\s+просил\s+запомнить|мои\s+факты|что\s+ты\s+знаешь\s+обо\s+мне|память)", re.I)},

    # --- План ---
    {"id": "plan_day", "pat": re.compile(r"^(?:план(?:\s+на\s+день)?|план\s+сегодня|составь\s+план|мой\s+план)", re.I),
     "neg": re.compile(_NEG, re.I)},
    {"id": "plan_week", "pat": re.compile(r"план\s+недел|на\s+недел|расписание\s+на\s+недел", re.I),
     "neg": re.compile(_NEG, re.I)},
    {"id": "plan_priority", "pat": re.compile(r"приоритиз|расставь\s+приоритет|что\s+важнее|с\s+чего\s+начать", re.I),
     "neg": re.compile(_NEG, re.I)},
    {"id": "plan_stats", "pat": re.compile(r"итоги|итог\s+дня|статистик|как\s+я\s+справ", re.I),
     "neg": re.compile(_NEG, re.I)},

    # --- Имя ---
    {"id": "set_name", "pat": re.compile(r"меня\s+зовут\s+(\w+)", re.I)},
    {"id": "ask_name", "pat": re.compile(r"как\s+меня\s+зовут|кто\s+я", re.I), "neg": re.compile(_NEG, re.I)},

    # --- Время/дата ---
    {"id": "time", "pat": re.compile(r"который\s+час|сколько\s+времени", re.I)},
    {"id": "date", "pat": re.compile(r"какое\s+сегодня\s+число|какая\s+сегодня\s+дата|какой\s+сегодня\s+день|какой\s+день\s+недели", re.I)},

    # --- Помодоро/советы ---
    {"id": "tip", "pat": re.compile(r"помодоро|эйзенхауэр|матриц|gtd|smart|2\s+минут|лягушк|прокраст|сон|выспат|фокус|концентр|привычк|стресс|тревог", re.I),
     "neg": re.compile(_NEG, re.I)},

    # --- Промпт ---
    {"id": "make_prompt", "pat": re.compile(r"(?:напиши|сделай|создай|дай)\s+(?:мне\s+)?пр(о|м)пт(?:мпт)?", re.I),
     "neg": re.compile(_NEG, re.I)},

    # --- Перевод/объяснение ---
    {"id": "explain", "pat": re.compile(r"(?:объясни|что\s+такое|учёб|учеб|урок|изуч)", re.I),
     "neg": re.compile(_NEG, re.I)},

    # --- ИИ запрос (неBrain) ---
    {"id": "llm", "pat": re.compile(r".+", re.I)},  # catch-all — только в конце!
]

# ============================================================
# ГЛАВНЫЙ МОЗГ
# ============================================================
_MAX_DEPTH = 10

def think(m, E, _depth=0):
    """Парсит намерение → вызывает действие → верифицирует."""
    if m is None: return "Не понял команду."
    if _depth > _MAX_DEPTH:
        return "Слишком глубокая вложенность. Напишите проще."

    D = E["D"]; now = dt.datetime.now()
    uid, save, refresh = E["uid"], E["save"], E["refresh_all"]
    mem = D.setdefault("mem", {}); mem.setdefault("facts", {}); mem.setdefault("name", "")
    tasks = D.get("tasks", [])
    sched = D.get("sched", [])
    rem = D.get("rem", [])
    notes = D.get("notes", [])
    habits = D.get("habits", [])

    l = m.lower().strip().rstrip("!?. ")

    # --- Поиск намерения ---
    intent = None; intent_data = None; params = {}
    for it in INTENTS:
        if it.get("neg") and it["neg"].search(l):
            continue
        m_match = it["pat"].search(l) if it["pat"].search else it["pat"].match(l)
        if m_match:
            intent = it["id"]; intent_data = it
            if m_match.groups():
                params = {"raw": m_match.group(0), "groups": list(m_match.groups())}
            break

    # --- Выполнение по намерению ---
    if intent == "help": return intent_data["reply"]
    if intent == "greet":
        n = len([t for t in tasks if not t.get("done")])
        nx = sorted([r_.get("when", "") for r_ in rem if r_.get("on")])
        nm = (", " + mem["name"]) if mem.get("name") else ""
        return f"Привет{nm}! 👋 Открытых задач: {n}." + (f" Ближайшее напоминание: {nx[0]}." if nx else "") + " Напиши «план», чтобы собрать день."
    if intent == "thanks": return intent_data["reply"]
    if intent == "whoami": return intent_data["reply"]

    # --- Вычисление ---
    if intent == "calc":
        expr = l.replace("посчитай", "").replace("сколько будет", "").replace("calc", "").replace("=", "").strip()
        if not re.search(r"[\d]", expr):
            return "Что посчитать?"
        result = calc(expr)
        return "🧮 = " + num(result) if result is not None else "Не смог посчитать."

    # --- Случайное ---
    if intent == "random":
        if re.search(r"монетк", l): return "🪙 " + random.choice(["Орёл", "Решка"])
        if re.search(r"кубик", l): return "🎲 " + str(random.randint(1, 6))
        m_sel = re.match(r"выбери\s+(.+)", l)
        if m_sel and re.search(r"\sили\s|,", m_sel[1]):
            return "🎯 Выбираю: " + random.choice([x.strip() for x in re.split(r"\sили\s|,", m_sel[1]) if x.strip()])

    # --- Мотивация ---
    if intent == "motivation": return "💬 " + random.choice(QUOTES)

    # --- Имя ---
    if intent == "set_name":
        mem["name"] = params["groups"][0].capitalize()
        save(); E["mem_add"]("Пользователя зовут " + mem["name"], "Обо мне") if E.get("mem_add") else None
        return f"Приятно познакомиться, {mem['name']}! 🙂"
    if intent == "ask_name":
        return f"Тебя зовут {mem['name']}." if mem.get("name") else "Ты не говорил. Напиши «меня зовут …»."

    # --- Время/дата ---
    if intent == "time": return f"🕐 Сейчас {now:%H:%M}"
    if intent == "date":
        return f"📅 Сегодня {now.day} {MONTHS_RU[now.month-1]} {now.year}, {['понедельник','вторник','среда','четверг','пятница','суббота','воскресенье'][now.weekday()]}"

    # --- Память ---
    if intent == "mem_store":
        E["mem_add"](f"{params['groups'][0].strip()}: {params['groups'][1].strip()}", "Факты", pin=True) if E.get("mem_add") else D.setdefault("memory", []).append({"id": uid(), "t": f"{params['groups'][0].strip()}: {params['groups'][1].strip()}", "cat": "Факты", "ts": now.strftime("%Y-%m-%d %H:%M"), "pin": True})
        save(); return f"🧠 Запомнил: {params['groups'][0].strip()} → {params['groups'][1].strip()}"
    if intent == "mem_store_val":
        text = params["groups"][0].strip()
        return E["mem_add_msg"](text) if E.get("mem_add_msg") else f"🧠 Запомнил: {text}"
    if intent == "mem_forget":
        q = params["groups"][0].strip().lower()
        M = D.setdefault("memory", [])
        gone = [x for x in M if q in x.get("t", "").lower()]
        for x in gone: M.remove(x)
        save(); return f"🗑 Забыл: {len(gone)} записей про «{q}»." if gone else f"Про «{q}» у меня ничего нет."
    if intent == "mem_show":
        M = D.get("memory", [])
        if not M: return "Пока ничего не знаю."
        cats = ["Обо мне", "Предпочтения", "Проекты", "Люди", "Факты", "Прочее"]
        out = ["🧠 Что я знаю:"]
        for c in cats:
            xs = [x for x in M if x.get("cat") == c]
            if xs: out += [c + ":"] + ["  • " + x["t"] for x in xs[:8]]
        return "\n".join(out)

    # --- Списки ---
    if intent == "list_tasks":
        ts = sorted([t for t in tasks if not t.get("done")],
                     key=lambda t: ({"Высокий": 0, "Средний": 1, "Низкий": 2}.get(t.get("prio", "Средний"), 1), t.get("due") or "9"))
        if not ts: return "Открытых задач нет 🎉"
        return "✅ Открытые задачи:\n" + "\n".join(f"  {i}. [{t.get('prio','Ср')[0]}] {t.get('text','')}" + (f" (до {t['due']})" if t.get("due") else "") for i, t in enumerate(ts, 1))
    if intent == "list_rem":
        rs = sorted([x for x in rem if x.get("on")], key=lambda x: x.get("when", ""))
        return "⏰ Активные:\n" + "\n".join(f"  {x.get('when','')} — {x.get('text','')} ({x.get('rep','')})" for x in rs) if rs else "Активных напоминаний нет."
    if intent == "list_notes":
        return "📝 Заметки:\n" + "\n".join("  • " + n.get("title", "") for n in notes[-15:]) if notes else "Заметок пока нет."
    if intent == "list_habits":
        td = now.date().isoformat()
        return "🔁 Привычки:\n" + "\n".join(f"  {'✅' if td in h.get('log', []) else '⬜'} {h.get('text','')} (серия {len(h.get('log', []))})" for h in habits) if habits else "Привычек пока нет."

    # --- Поиск заметок ---
    if intent == "search_notes":
        q = params["groups"][0][:6].lower()
        hits = [n for n in notes if q in (n.get("title", "") + n.get("body", "")).lower()]
        return "🔎 Нашёл:\n" + "\n".join(f"  • {n.get('title','')}: {n.get('body','')[:80]}" for n in hits[:8]) if hits else "Ничего не нашёл."

    # --- Расписание ---
    if intent == "schedule_day":
        day_name = params["groups"][0].lower()
        if day_name == "сегодня": di = now.weekday()
        elif day_name == "завтра": di = (now.weekday() + 1) % 7
        else: di = WDN_FULL.get(day_name, now.weekday())
        it = sorted([x for x in sched if x.get("day", "").lower().startswith(DAYS[di][:3])], key=lambda x: x.get("time", ""))
        return f"📆 {DAYS[di]}:\n" + "\n".join(f"  {x.get('time','')} — {x.get('text','')}" for x in it) if it else f"На {DAYS[di]} ничего не запланировано."
    if intent == "schedule_show":
        rows = sorted(sched, key=lambda x: (DAYS.index(x.get("day", "")) if x.get("day", "") in DAYS else 9, x.get("time", "")))
        return "📆 Расписание:\n" + "\n".join(f"  {x.get('day','')} {x.get('time','')} — {x.get('text','')}" for x in rows) if rows else "Расписание пусто."

    # --- Удаление ---
    if intent == "delete_item":
        txt = params["groups"][1].strip() if len(params["groups"]) > 1 else params["groups"][0].strip()
        kind = params["groups"][0].strip().lower()
        # Определяем тип по первому слову
        _map = {"з": ("tasks", "text"), "н": ("rem", "text"), "б": ("rem", "text"), "ем": ("notes", "title"), "п": ("habits", "text")}
        key_name, find_key = _map.get(kind[0], ("tasks", "text"))
        src = D.get(key_name, [])
        it = find(src, txt, find_key)
        if it:
            src.remove(it); save(); refresh()
            return f"🗑 Удалил: {it.get(find_key, '')}"
        return "Не нашёл."
    if intent == "delete_done":
        n = len([t for t in tasks if t.get("done")])
        D["tasks"][:] = [t for t in tasks if not t.get("done")]
        save(); refresh(); return f"🗑 Убрал выполненных: {n}"

    # --- Выполнение ---
    if intent == "complete_item":
        txt = params["groups"][0].strip() if params["groups"] else l
        # Сначала ищем привычки
        h = find(habits, txt) if "привыч" in l else None
        if not h: h = find([t for t in tasks if not t.get("done")], txt)
        if h:
            td = now.date().isoformat()
            if td not in h.get("log", []): h["log"].append(td)
            save(); refresh()
            return f"🔥 Отмечено: {h.get('text','')} (серия {len(h.get('log', []))})" if "привыч" in l else f"✅ Выполнено: {h.get('text','')}. Так держать!"
        return "Не нашёл такое."

    # --- Звук ---
    if intent == "sound_create":
        # Проверяем негативные контексты
        if re.search(r"не\s+хочу\s+звук|без\s+звука|отмени\s+звук", l):
            return "Хорошо, без звука."
        # Ищем контекст
        if re.search(r"постав|установ|назнач", l):
            return _set_sound(l, D, E, uid, save, refresh, now)
        d = re.sub(r"^(?:ок|пожалуйста|слушай|созда\w*|сдела\w*|придума\w*|сочини\w*|сгенерир\w*|мне)?\s*", "", l, flags=re.I).strip() or "приятный звук"
        al = bool(re.search(r"будильн|разбуд|просып", l))
        return f"🎵 Сочиняю звук: «{d}». " + ("Поставлю на ближайший будильник." if al else "Добавлю в библиотеку «Звуки».")

    if intent == "sound_set":
        return _set_sound(l, D, E, uid, save, refresh, now)

    # --- Игры ---
    if intent == "game_dino":
        if re.search(r"убери|скрой|выключ", l): return "Убрал динозаврика. [[game: off]]"
        return "🦖 Динозаврик в левом нижнем углу. Прыгать: клик по полю или пробел. [[game: on]]"
    if intent == "game":
        game_name = re.sub(r"создай|сделай|игру|напиши|поиграй|сыграем\s+", "", l, flags=re.I).strip() or "змейка"
        return f"🎮 Сочиняю игру: «{game_name}». " + " [[game: {name}]]".format(name=game_name[:40])

    # --- Дизайн ---
    if intent == "design":
        provider = D.get("cfg", {}).get("provider", "")
        if provider and provider.startswith("Krug Brain"):
            return "🎨 Перерисовка с подключённым ИИ в «Настройках». Без него могу стили: киберпанк, уют, минимализм, неон, океан, закат, лес, сакура, золото, матрица, космос, ретро, акцентные цвета, скругления, звёзды, сетка."
        return f"🎨 Перерисовываю интерфейс… [[restyle: {l[:80]}]]"

    # --- Напоминание ---
    if intent == "set_reminder":
        kind = "Будильник" if re.search(r"будильн|разбуди", l) else "Напоминание"
        src = re.sub(r"таймер на", "через", m, flags=re.I)
        w, rest, rep = parse_when(src, now)
        txt = re.sub(r"^(?:\s|,|напомни(?:ть)?|мне|будильн\w*|разбуди|таймер|пожалуйста|что|чтобы|о\s+том|окей|ок|поставь|установи|заведи|будь\s+добр)+", "", rest, flags=re.I).strip()
        txt = re.sub(r"\s+(?:до|к|на|в)$", "", txt) or ("Таймер" if "таймер" in l else kind)
        if w:
            E["add_rem"](txt, w, kind, rep) if E.get("add_rem") else rem.append({"id": uid(), "text": txt, "when": w.strftime("%Y-%m-%d %H:%M"), "kind": kind, "rep": rep, "on": True})
            if E.get("save"): E["save"]()
            if E.get("refresh_all"): E["refresh_all"]()
            return f"✅ {kind}: «{txt}» — {w:%d.%m %H:%M}" + (f", {rep.lower()}" if rep != "Один раз" else "")
        mem["pending"] = {"k": "rem", "text": txt, "kind": kind}
        return f"На какое время поставить «{txt}»? (например: через 20 минут / завтра в 9:00)"

    # --- План ---
    if intent == "plan_day":
        return E["day_plan"]() if E.get("day_plan") else "Пока пусто. Добавь задачи или напиши «напомни через 10 минут выпить воды»."
    if intent == "plan_week":
        return _week_view(D, now)
    if intent == "plan_priority":
        return _matrix(D, now)
    if intent == "plan_stats":
        done = len([t for t in tasks if t.get("done")])
        op = len(tasks) - done
        td = now.date().isoformat()
        hb = len([h for h in habits if td in h.get("log", [])])
        return f"📊 Выполнено задач: {done}, осталось: {op}. Привычек сегодня: {hb}/{len(habits)}." + (" Отличный прогресс!" if done > op else " Выбери одну главную задачу и начни с неё.")

    # --- Советы ---
    if intent == "tip":
        KB = {
            "помодоро": "🍅 Помодоро: 25 мин работы → 5 мин отдыха; после 4 циклов — перерыв 15–30 мин.",
            "эйзенхауэр|матриц": "🧭 Срочно+Важно → делай сейчас. Важно, не срочно → планируй. Срочно, не важно → делегируй. Ни то ни другое → удаляй.",
            "gtd": "📥 Собери всё → реши → следующее действие → делегируй/запланируй/сделай. Раз в неделю — обзор.",
            "smart": "🎯 Конкретная, измеримая, достижимая, значимая, ограниченная по сроку.",
            "2\s+минут": "⚡ Если дело < 2 минут — делай сразу.",
            "лягушк": "🐸 Самое неприятное дело — первым с утра.",
            "прокраст": "🐢 Первый шаг на 5 минут, разбей задачу, убери отвлекающее.",
            "сон|выспат": "😴 7–9 часов, одно время подъёма, без экранов за 40 мин.",
            "фокус|концентр": "🎧 Одна задача, уведомления выключены, блок 25–50 мин.",
            "привычк": "🔁 Микро-версия (2 мин), привяжи к действию, не пропускай 2 дня.",
            "стресс|тревог": "🌿 Выпиши → раздели → один шаг. Дыхание 4-6, прогулка, сон.",
        }
        for pat, tip in KB.items():
            if re.search(pat, l, re.I): return tip
        return None  # не найден конкретный совет

    # --- Промпт ---
    if intent == "make_prompt":
        topic = l.replace("напиши", "").replace("сделай", "").replace("создай", "").replace("дай", "").replace("пр(о|м)пт", "").strip()
        if not topic: return "О чём написать промпт?"
        PT = {
            "код|програм|python|скрипт|сайт|бот": ("senior-разработчик", "Код в блоках, пояснение, граничные случаи"),
            "картин|изображ|рисун|логотип": ("арт-директор", "Сюжет, стиль, свет, камера, палитра, --ar 16:9"),
            "текст|статья|пост|реклам|письм": ("копирайтер", "3 варианта: заголовок + текст + призыв"),
            "объясни|учёб|урок|изуч": ("репетитор", "Простое объяснение, пример, 3 проверочных вопроса"),
        }
        for pat, (role, fmt) in PT.items():
            if re.search(pat, topic, re.I):
                return f"## Роль\nТы — {role}.\n\n## Задача\n{topic[0].upper() + topic[1:]}.\n\n## Формат\n{fmt}"
        return f"## Роль\nТы — эксперт в теме.\n\n## Задача\n{topic[0].upper() + topic[1:]}.\n\n## Формат\nСтруктурированный ответ, шаги, примеры."

    # --- Explain ---
    if intent == "explain":
        return "Для объяснений и учебных материалов подключите ИИ в «Настройках». Без ИИ я могу только встроенные советы: напиши «помощь»."

    # --- LLM fallback ---
    return None  # передаём на обработку внешнему ИИ

# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
def _week_view(D, now):
    L = ["🗓 Неделя:"]
    mon = now.date() - dt.timedelta(days=now.weekday())
    sched = D.get("sched", []); tasks = D.get("tasks", []); rem = D.get("rem", [])
    for i, d in enumerate(DAYS):
        day = mon + dt.timedelta(days=i); mark = " ← сегодня" if day == now.date() else ""
        it = [f"{x.get('time','')} {x.get('text','')}" for x in sorted(sched, key=lambda x: x.get("time","")) if x.get("day") == d]
        it += [f"до: {t.get('text','')}" for t in tasks if not t.get("done") and t.get("due") == day.isoformat()]
        it += [f"{r.get('when','')[11:]} {r.get('text','')}" for r in rem if r.get("on") and len(r.get("when","")) > 11 and r["when"].startswith(day.isoformat())]
        L.append(f"  {d} {day:%d.%m}{mark}: " + ("; ".join(it) if it else "—"))
    return "\n".join(L)

def _matrix(D, now):
    near = (now + dt.timedelta(days=2)).strftime("%Y-%m-%d"); q = {k: [] for k in "abcd"}
    for t in D.get("tasks", []):
        if t.get("done"): continue
        urg = t.get("prio") == "Высокий" or (t.get("due") and t["due"] <= near)
        imp = t.get("prio") != "Низкий"
        q["a" if urg and imp else "b" if imp else "c" if urg else "d"].append(t.get("text", ""))
    nm = {"a": "🔥 Сделай сейчас (срочно+важно)", "b": "📅 Запланируй (важно)",
          "c": "🤝 Делегируй / быстро (срочно)", "d": "🗑 Можно отложить или удалить"}
    out = [f"{nm[k]}:\n" + "\n".join("  • " + x for x in v) for k, v in q.items() if v]
    return "🧭 Приоритеты по матрице Эйзенхауэра:\n\n" + "\n\n".join(out) if out else "Открытых задач нет — отлично!"

def _set_sound(l, D, E, uid, save, refresh, now):
    ss = D.get("sounds", [])
    pick = next((s for s in ss if s.get("name","").lower() in l), None)
    if not pick and ss and re.search(r"последн|нов|этот|его|её|ее|созданн", l): pick = ss[-1]
    if not pick:
        w = [x for x in re.findall(r"\w{4,}", l) if not x.startswith(("звук", "будиль", "постав", "устан", "назна"))]
        pick = next((s for s in ss if any(x[:5] in s.get("name","").lower() for x in w)), None) if w else None
    if not pick:
        return "Какой звук поставить? В библиотеке: " + (", ".join(s.get("name","") for s in ss[-8:]) or "пусто, скажи «создай нежный звук для будильника»") + "."
    act = sorted([r_ for r_ in D.get("rem", []) if r_.get("on")], key=lambda r_: r_.get("when", ""))
    if re.search(r"будильн", l): act = [r_ for r_ in act if r_.get("kind") == "Будильник"] or act
    tm = re.search(r"(\d{1,2})[:.](\d{2})", l)
    if tm and act: act = [r_ for r_ in act if r_.get("when","")[11:] == f"{int(tm[1]):02d}:{tm[2]}"] or act
    if not act: return "Нет активных будильников."
    act[0]["sound"] = pick["id"]; save(); refresh()
    return f"🎵 Готово: на «{act[0].get('text','')}» ({act[0].get('when','')[11:]}) теперь играет «{pick['name']}»."

# ============================================================
# Fallback
# ============================================================
def fallback(m, E):
    D = E["D"]; mem = D.setdefault("mem", {}); l = m.lower(); out = []
    words = re.findall(r"\w{4,}", l)
    hits = [n.get("title","") for n in D.get("notes", []) if any(w[:5] in ((n.get("title","") + n.get("body","")).lower()) for w in words)][:5]
    if hits: out.append("🔎 В твоих заметках похожее: " + "; ".join(hits))
    EX = ["напомни через 10 минут выпить воды", "будильник на 7:00", "задача: купить хлеб", "покажи задачи",
          "составь план изучения английского на 8 недель", "план на день", "план недели",
          "напиши промпт для рекламного текста", "заметка: идея", "привычка: зарядка", "приоритизируй задачи"]
    try:
        c = difflib.get_close_matches(l, EX, 2, 0.4)
    except Exception: c = []
    if c: out.append("Возможно, ты имел в виду:\n" + "\n".join("• " + x for x in c))
    mem["pending"] = {"k": "save", "text": m}; mem["last_unknown"] = m
    return "\n".join(out) if out else None