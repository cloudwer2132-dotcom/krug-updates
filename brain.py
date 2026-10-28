# -*- coding: utf-8 -*-
"""Krug Brain — встроенный офлайн-помощник: понимает русские команды и даты, планирует, считает, пишет промпты, помнит факты."""
import re, random, math, difflib, ast, operator, datetime as dt

DAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MON = {"янв": 1, "фев": 2, "мар": 3, "апр": 4, "мая": 5, "июн": 6, "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12}
WDN = ["пон", "вто", "сре", "чет", "пят", "суб", "вос"]
MONTHS_RU = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]

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

EX = ["напомни через 10 минут выпить воды", "будильник на 7:00", "задача: купить хлеб", "покажи задачи", "составь план изучения английского на 8 недель",
      "план на день", "план недели", "напиши промпт для рекламного текста", "заметка: идея", "привычка: зарядка", "приоритизируй задачи",
      "разбей задачу написать отчёт на шаги", "что такое помодоро", "посчитай 2+2", "мотивация", "итоги дня"]

KB = {
    r"помодоро": "🍅 Помодоро: 25 минут работы без отвлечений → 5 минут отдыха; после 4 циклов — перерыв 15–30 минут. Телефон убери, одна задача на цикл. Таймер есть во вкладке «Фокус».",
    r"эйзенхауэр|матриц": "🧭 Матрица Эйзенхауэра: срочно+важно — делай сейчас; важно, не срочно — планируй (главное для роста); срочно, не важно — делегируй; ни то ни другое — удаляй. Напиши «приоритизируй задачи».",
    r"gtd": "📥 GTD: собери всё в «входящие» → реши, что это за задача → следующее конкретное действие → делегируй/запланируй/сделай. Раз в неделю — обзор списков.",
    r"smart": "🎯 SMART-цель: конкретная, измеримая, достижимая, значимая, ограниченная по сроку. Не «выучить английский», а «дойти до B1 к 1 июня: 30 мин в день + 2 урока в неделю».",
    r"двух минут|2 минут": "⚡ Правило двух минут: если дело занимает меньше 2 минут — делай сразу, не записывай.",
    r"лягушк": "🐸 «Съешь лягушку»: самое неприятное и важное дело — первым с утра, пока есть энергия.",
    r"прокраст|откладыв": "🐢 Против прокрастинации: сделай первый шаг на 5 минут, разбей задачу на мелкие («разбей задачу …»), убери отвлекающее, назначь точное время начала, награди себя после.",
    r"сон|выспат|спать": "😴 Сон: 7–9 часов, одно время подъёма, без экранов за 40–60 минут до сна, прохладная тёмная комната, кофеин — не позже 14–15 часов.",
    r"фокус|концентр": "🎧 Фокус: одна задача, уведомления выключены, рабочий блок 25–50 минут, вода рядом, чёткий критерий «готово».",
    r"привычк": "🔁 Привычки: начинай с микро-версии (2 минуты), привяжи к существующему действию («после кофе — зарядка»), не пропускай два дня подряд. Серии видны во вкладке «Привычки».",
    r"стресс|тревог": "🌿 При стрессе: выпиши, что тревожит → раздели на «могу повлиять» / «не могу» → один маленький шаг по первому. Дыхание 4-6, прогулка, сон. Если тяжело долго — поговори со специалистом.",
}
QUOTES = ["Маленькие шаги каждый день сильнее редких рывков.", "Начни — мотивация придёт во время работы.", "Не идеально, а сделано. Улучшишь потом.",
          "Ты не обязан делать всё. Сделай самое важное.", "Дисциплина — это забота о себе из будущего.", "5 минут — тоже прогресс."]

PT = {r"код|програм|python|скрипт|сайт|бот|баг|функци": ("senior-разработчик", "Сначала короткий план, затем код в блоках, затем объяснение и граничные случаи", "Не выдумывай API; укажи версии и допущения; код должен запускаться"),
      r"картин|изображ|рисун|логотип|постер|midjourney|иллюстр": ("арт-директор и промпт-инженер для генерации изображений", "Один абзац: сюжет, стиль, свет, камера/ракурс, палитра, композиция + параметры (--ar 16:9). Дай 3 варианта", "Без текста на изображении и лишних объектов"),
      r"текст|статья|пост|реклам|письм|описани|слоган|сценари": ("сильный редактор-копирайтер", "3 варианта: короткий, средний, расширенный + цепляющий заголовок", "Без воды и клише, живой язык, под целевую аудиторию"),
      r"объясни|учёб|учеб|урок|экзамен|изуч|реферат": ("терпеливый репетитор", "Простое объяснение → аналогия → пример → 3 проверочных вопроса с ответами", "Если что-то неясно — сначала спроси"),
      r"анализ|данн|отчёт|отчет|рынок|конкурент|сравни": ("аналитик", "Резюме в 3 строки → таблица → риски → рекомендации → следующие шаги", "Отделяй факты от предположений, указывай источники"),
      r"перевод|переведи": ("профессиональный переводчик", "Сначала только перевод, затем заметки о неоднозначных местах", "Сохрани тон, термины и форматирование")}

TPL = {
    "тренировк": "💪 План тренировок (3 дня/нед, по 45–60 мин):\n  Пн — верх тела: отжимания, подтягивания/тяга, жим, планка\n  Ср — ноги и кор: приседания, выпады, ягодичный мостик, скручивания\n  Пт — всё тело + кардио 15 мин\n  Каждый раз: разминка 5–10 мин и растяжка 5 мин. Прогрессия: +1–2 повтора в неделю. Если есть травмы или болезни — сначала врач.",
    "режим дня": "🕰 Пример режима дня:\n  07:00 подъём, вода, зарядка · 07:30 душ, завтрак · 08:30–12:00 главная работа (блоки 50/10)\n  12:00 обед и прогулка · 13:00–16:30 обычные задачи, почта · 16:30–18:00 учёба/проекты\n  18:00 спорт · 19:30 ужин, семья · 21:00 план на завтра · 22:30 отбой без экранов",
}

# ---------- дата и время ----------
def parse_when(s, now):
    t = " " + s + " "; rep = "Один раз"; wk = False
    def take(p):
        nonlocal t
        m = re.search(p, t, re.I)
        if m: t = t[:m.start()] + " " + t[m.end():]
        return m
    if take(r"\bпо будням\b"): rep = "По будням"
    elif take(r"\b(?:каждый день|ежедневно)\b"): rep = "Каждый день"
    elif take(r"\b(?:каждую неделю|еженедельно)\b"): rep = "Каждую неделю"
    w = None
    m = take(r"через\s+((?:\d+\s*(?:мин|ч|дн|де|нед)\S*\s*)+|полчаса|полтора\s+часа|пару\s+минут|час\b|минуту)")
    if m:
        g = m[1].lower(); mins = 0
        for n, u in re.findall(r"(\d+)\s*(мин|ч|дн|де|нед)", g):
            mins += int(n) * {"мин": 1, "ч": 60, "дн": 1440, "де": 1440, "нед": 10080}[u]
        if not mins: mins = 30 if "полчаса" in g else 90 if "полтора" in g else 2 if "пару" in g else 1 if "минуту" in g else 1 if re.search(r"\d", g) else 60
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
                day = now.date() + dt.timedelta(days=(WDN.index(m[1][:3].lower()) - now.weekday()) % 7); wk = True
            else:
                m = take(r"\b(\d{1,2})\s+(янв|фев|мар|апр|мая|июн|июл|авг|сен|окт|ноя|дек)\S*")
                if m:
                    try:
                        day = dt.date(now.year, MON[m[2].lower()], int(m[1]))
                        if day < now.date(): day = day.replace(year=now.year + 1)
                    except ValueError: day = None
        if day is None:
            m = take(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b") or take(r"\b(2[4-9]|3[01])\.(\d{1,2})()\b")
            if m:
                try:
                    y = int(m[3]) if m[3] else now.year
                    if y < 100: y += 2000
                    day = dt.date(y, int(m[2]), int(m[1]))
                    if not m[3] and day < now.date(): day = day.replace(year=y + 1)
                except ValueError: day = None
        hm = None
        m = take(r"\b(?:в|на|к|около)?\s*(\d{1,2})[:.](\d{2})\b")
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

# ---------- утилиты ----------
_ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod, ast.USub: operator.neg, ast.FloorDiv: operator.floordiv}
def calc(e):
    def ev(n):
        if isinstance(n, ast.Expression): return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return n.value
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and abs(b) > 100: raise ValueError
            return _ops[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp): return _ops[type(n.op)](ev(n.operand))
        raise ValueError
    return ev(ast.parse(e.replace("^", "**").replace(",", ".").replace("×", "*").replace("÷", "/"), mode="eval"))

def num(x): return str(int(x)) if float(x).is_integer() else f"{x:.4f}".rstrip("0").rstrip(".")

def find(items, q, key="text"):
    q = q.lower().strip()
    if not q: return None
    for it in items:
        if q in it[key].lower(): return it
    c = difflib.get_close_matches(q, [i[key].lower() for i in items], 1, 0.5)
    return next((i for i in items if c and i[key].lower() == c[0]), None)

def make_prompt(topic):
    for pat, (role, fmt, lim) in PT.items():
        if re.search(pat, topic, re.I): break
    else: role, fmt, lim = "опытный эксперт в теме запроса", "Структурированный ответ: шаги, примеры, итог", "Если данных не хватает — сначала задай уточняющие вопросы"
    return (f"## Роль\nТы — {role}.\n\n## Задача\n{topic[0].upper() + topic[1:]}.\n\n## Контекст\n(добавь: для кого, цель, что уже известно, что пробовал)\n\n"
            f"## Формат ответа\n{fmt}\n\n## Ограничения\n{lim}\n\n## Порядок работы\nЕсли данных не хватает — задай до 3 уточняющих вопросов. Затем дай ответ и коротко проверь его на ошибки.")

def study_plan(topic, n, unit):
    ph = [("Цель и карта темы", "сформулируй SMART-цель и критерий успеха, выбери 2–3 лучших источника, составь карту подтем"),
          ("Основы", "базовый материал + конспект своими словами, 30–60 минут в день"),
          ("Практика", "упражнения и задачи, ошибки записывай в заметки"),
          ("Мини-проект", "собери что-то реальное по теме — лучшее закрепление"),
          ("Повторение и пробелы", "разбор ошибок, повторения через 1-3-7-14 дней"),
          ("Итог", "проверка по критерию успеха, выводы, следующий шаг")]
    L = [f"🧩 План: {topic} — {n} {unit}", ""]
    for i, (nm, d) in enumerate(ph):
        a = int(i * n / 6) + 1; b = max(a, int((i + 1) * n / 6))
        L.append(f"  {unit.split('.')[0].capitalize()} {a}" + (f"–{b}" if b > a else "") + f": {nm} — {d}")
    L += ["", "Совет: занимайся в одно и то же время, а раз в неделю делай мини-обзор прогресса."]
    return "\n".join(L), [f"{topic}: {nm}" for nm, _ in ph]

def steps_for(task):
    st = ["Определи результат: как поймёшь, что «готово» (1 предложение)", "Собери всё нужное: материалы, доступы, людей (15 мин)",
          "Сделай «грязную» минимальную версию за один подход (25 мин)", "Разбей остальное на блоки по 25–50 минут и расставь по дням",
          "Выполни основной блок работы без отвлечений", "Проверь по критерию «готово», исправь слабые места", "Заверши: отправь/сдай/опубликуй и отметь выполненным"]
    return [f"{task}: {s}" for s in st]

def week_view(D, now):
    L = ["🗓 Неделя:"]
    mon = now.date() - dt.timedelta(days=now.weekday())
    sched = D.get("sched", []); tasks = D.get("tasks", []); rem = D.get("rem", [])
    for i, d in enumerate(DAYS):
        day = mon + dt.timedelta(days=i); mark = " ← сегодня" if day == now.date() else ""
        it = [f"{x.get('time','')} {x.get('text','')}" for x in sorted(sched, key=lambda x: x.get("time","")) if x.get("day") == d]
        it += [f"до: {t['text']}" for t in tasks if not t.get("done") and t.get("due") == day.isoformat()]
        it += [f"{r.get('when','')[11:]} {r.get('text','')}" for r in rem if r.get("on") and len(r.get("when","")) > 11 and r["when"].startswith(day.isoformat())]
        L.append(f"  {d} {day:%d.%m}{mark}: " + ("; ".join(it) if it else "—"))
    return "\n".join(L)

def matrix(D, now):
    near = (now + dt.timedelta(days=2)).strftime("%Y-%m-%d"); q = {k: [] for k in "abcd"}
    for t in D.get("tasks", []):
        if t.get("done"): continue
        urg = t.get("prio") == "Высокий" or (t.get("due") and t["due"] <= near); imp = t.get("prio") != "Низкий"
        q["a" if urg and imp else "b" if imp else "c" if urg else "d"].append(t.get("text", ""))
    nm = {"a": "🔥 Сделай сейчас (срочно+важно)", "b": "📅 Запланируй (важно)", "c": "🤝 Делегируй / быстро (срочно)", "d": "🗑 Можно отложить или удалить"}
    out = [f"{nm[k]}:\n" + "\n".join("  • " + x for x in v) for k, v in q.items() if v]
    return "🧭 Приоритеты по матрице Эйзенхауэра:\n\n" + "\n\n".join(out) if out else "Открытых задач нет — отлично!"

# ---------- главный мозг ----------
_MAX_DEPTH = 10  # защита от рекурсии

def think(m, E, _depth=0):
    """Встроенный мозг с защитой от рекурсии."""
    if m is None: return "Не понял команду."
    if _depth > _MAX_DEPTH:
        return "Слишком глубокая вложенность команд. Напишите проще."
    D = E["D"]; now = dt.datetime.now(); l = m.lower().strip().rstrip("!?. ")
    uid, save, refresh = E["uid"], E["save"], E["refresh_all"]
    mem = D.setdefault("mem", {}); mem.setdefault("facts", {}); mem.setdefault("name", "")
    # Безопасные доступы к спискам — .get с default []
    tasks = D.get("tasks", [])
    sched = D.get("sched", [])
    rem = D.get("rem", [])
    notes = D.get("notes", [])
    habits = D.get("habits", [])
    R = lambda p: re.search(p, l)
    def task(txt, prio="Средний", due=""):
        tasks.append({"id": uid(), "text": txt, "prio": prio, "due": due, "done": False})
    pend = mem.pop("pending", None)
    if pend:
        if pend["k"] == "rem" and not R(r"напомни|будильн|разбуди|таймер|задач|заметк|привычк|покажи|план"):
            w, _, rep = parse_when(m, now)
            if w: E["add_rem"](pend["text"], w, pend["kind"], rep); return f"✅ Поставил: «{pend['text']}» на {w:%d.%m %H:%M}"
        elif pend["k"] == "tasks" and l in ("да", "добавь", "добавь в задачи", "давай", "ок", "хорошо", "добавить"):
            for t in pend["items"]: task(t)
            save(); refresh(); return f"✅ Добавил задач: {len(pend['items'])}"
        elif pend["k"] == "save" and l.startswith(("задач", "замет")):
            if l.startswith("задач"): task(pend["text"])
            else: notes.append({"id": uid(), "title": pend["text"][:40], "body": pend["text"]})
            save(); refresh(); return "✅ Сохранил"
    r = re.match(r"^(?:когда я (?:пишу|говорю)|если я (?:пишу|говорю))\s*[:«\"]?\s*(.+?)[»\"]?\s*(?:=|—|->|→|,|то|значит|это)\s*(.+)$", m, re.I)
    if r: return E["learn_rule"](r[1], r[2])
    r = re.match(r"^научи(?:сь)?[:,]?\s*(.+)$", m, re.I)
    if r and mem.get("last_unknown"): return E["learn_rule"](mem.pop("last_unknown"), r[1])
    rl = E["match_rule"](m)
    if rl is not None: return rl
    r = re.match(r"^забудь\s+(?:что\s+)?(.+)$", m, re.I)
    if r and not R(r"про это|всё|все"): return E["mem_forget"](r[1])
    if l in ("помощь", "/help", "help", "что ты умеешь", "что умеешь", "команды"): return HELP
    r = re.match(r"меня зовут\s+(\w+)", m, re.I)
    if r: mem["name"] = r[1].capitalize(); save(); E["mem_add"]("Пользователя зовут " + mem["name"], "Обо мне"); return f"Приятно познакомиться, {mem['name']}! 🙂"
    if l in ("как меня зовут", "кто я"): return f"Тебя зовут {mem['name']}." if mem["name"] else "Ты не говорил. Напиши «меня зовут …»."
    nm = (", " + mem["name"]) if mem["name"] else ""
    if re.match(r"^(привет|здравствуй|добрый (день|вечер)|доброе утро|хай|салют)", l):
        n = len([t for t in tasks if not t.get("done")])
        nx = sorted([r_.get("when", "") for r_ in rem if r_.get("on")])
        return f"Привет{nm}! 👋 Открытых задач: {n}." + (f" Ближайшее напоминание: {nx[0]}." if nx else "") + " Напиши «план», чтобы собрать день."
    if l in ("спасибо", "благодарю", "спс"): return "Всегда пожалуйста! 🙌"
    if l.startswith("как дела"): return "Работаю без сбоев и готов помогать! Что планируем?"
    if l in ("кто ты", "ты кто", "ты ии"):
        return ("Я Krug Brain — встроенный офлайн-помощник Круга. Это не большая нейросеть: я точно выполняю команды, понимаю даты, планирую и помню твои факты. "
                "Для свободных умных ответов подключи ИИ в «Настройках».")
    r = re.match(r"запомни:?\s*(.+?)\s*(?:=|—| - | это )\s*(.+)$", m, re.I)
    if r: mem["facts"][r[1].strip().lower()] = r[2].strip(); E["mem_add"](f"{r[1].strip()}: {r[2].strip()}", "Факты"); save(); return f"🧠 Запомнил: {r[1]} → {r[2]}"
    r = re.match(r"запомни:?\s*(.+)$", m, re.I)
    if r: return E["mem_add_msg"](r[1])
    if l in ("что ты помнишь", "что я просил запомнить", "мои факты", "что ты знаешь обо мне", "память"):
        return E["mem_list"]()
    for k, v in mem["facts"].items():
        if l == k or l in (f"что такое {k}", f"{k}?", f"что ты знаешь про {k}"): return f"🧠 {k}: {v}"
    if R(r"который час|сколько времени"): return f"🕐 Сейчас {now:%H:%M}"
    if R(r"какое сегодня число|какая сегодня дата|какой сегодня день|какой день недели"):
        return f"📅 Сегодня {now.day} {MONTHS_RU[now.month - 1]} {now.year}, {['понедельник','вторник','среда','четверг','пятница','суббота','воскресенье'][now.weekday()]}"
    r = R(r"сколько дней до (\d{1,2})\s+(янв|фев|мар|апр|мая|июн|июл|авг|сен|окт|ноя|дек)")
    if r:
        try:
            d = dt.date(now.year, MON[r[2]], int(r[1]))
            if d < now.date(): d = d.replace(year=now.year + 1)
            return f"⏳ До {d:%d.%m.%Y} — {(d - now.date()).days} дн."
        except ValueError: pass
    r = R(r"(\d+(?:[.,]\d+)?)\s*%\s*от\s*(\d+(?:[.,]\d+)?)")
    if r: return "🧮 = " + num(float(r[1].replace(",", ".")) * float(r[2].replace(",", ".")) / 100)
    r = re.match(r"^(?:посчитай|сколько будет|calc|=)\s*(.+)$", l) or (re.fullmatch(r"[\d\s+\-*/().,^%×÷]{3,}", l) and re.match(r"(.+)", l))
    if r:
        try: return "🧮 = " + num(calc(r[1]))
        except Exception: return "Не смог посчитать это выражение."
    if R(r"монетк"): return "🪙 " + random.choice(["Орёл", "Решка"])
    if R(r"кубик"): return "🎲 " + str(random.randint(1, 6))
    r = re.match(r"^выбери\s+(.+)$", l)
    if r and re.search(r"\sили\s|,", r[1]): return "🎯 Выбираю: " + random.choice([x.strip() for x in re.split(r"\sили\s|,", r[1]) if x.strip()])
    if R(r"мотивац|вдохнови|поддержи"): return "💬 " + random.choice(QUOTES)
    # списки
    if R(r"^(?:покажи|выведи|список|мои|что у меня по|какие)\s.*задач|^задачи$"):
        ts = sorted([t for t in tasks if not t.get("done")], key=lambda t: ({"Высокий": 0, "Средний": 1, "Низкий": 2}.get(t.get("prio", "Средний"), 1), t.get("due") or "9"))
        return "✅ Открытые задачи:\n" + "\n".join(f"  {i}. [{t.get('prio','Средний')[0]}] {t.get('text','')}" + (f" (до {t['due']})" if t.get("due") else "") for i, t in enumerate(ts, 1)) if ts else "Открытых задач нет 🎉"
    if R(r"^(?:покажи|выведи|список|мои)\s.*(?:напоминани|будильник)"):
        rs = sorted([x for x in rem if x.get("on")], key=lambda x: x.get("when", ""))
        return "⏰ Активные:\n" + "\n".join(f"  {x.get('when','')} — {x.get('text','')} ({x.get('rep','')})" for x in rs) if rs else "Активных напоминаний нет."
    if R(r"^(?:покажи|выведи|список|мои)\s.*заметк"):
        return "📝 Заметки:\n" + "\n".join("  • " + n.get("title", "") for n in notes[-15:]) if notes else "Заметок пока нет."
    if R(r"^(?:покажи|выведи|список|мои)\s.*привычк"):
        td = now.date().isoformat()
        return "🔁 Привычки:\n" + "\n".join(f"  {'✅' if td in h.get('log', []) else '⬜'} {h.get('text','')} (серия {len(h.get('log', []))})" for h in habits) if habits else "Привычек пока нет."
    r = re.match(r"^(?:найди|поищи)\s+(?:заметку\s+)?(.+)$", l)
    if r:
        q = r[1][:6]; hits = [n for n in notes if q in ((n.get("title","") + n.get("body","")).lower())]
        return "🔎 Нашёл:\n" + "\n".join(f"  • {n.get('title','')}: {n.get('body','')[:80]}" for n in hits[:8]) if hits else "Ничего не нашёл в заметках."
    r = R(r"расписание на (понедельник|вторник|сред\w+|четверг|пятниц\w+|суббот\w+|воскресенье|сегодня|завтра)")
    if r:
        i = now.weekday() if r[1] == "сегодня" else (now.weekday() + 1) % 7 if r[1] == "завтра" else WDN.index(r[1][:3])
        it = sorted([x for x in sched if x.get("day") == DAYS[i]], key=lambda x: x.get("time", ""))
        return f"📆 {DAYS[i]}:\n" + "\n".join(f"  {x.get('time','')} — {x.get('text','')}" for x in it) if it else f"На {DAYS[i]} ничего не запланировано."
    # действия над элементами
    _TASK_MAP = {"з": ("tasks", "text"), "н": ("rem", "text"), "б": ("rem", "text"), "ем": ("notes", "title"), "п": ("habits", "text")}
    r = re.match(r"^(?:удали|убери|отмени)\s+(задачу|напоминание|будильник|заметку|привычку)\s*:?\s*(.+)$", m, re.I)
    if r:
        k = ("ем" if r[1].lower().startswith("заме") else r[1][0].lower())
        key_name, find_key = _TASK_MAP.get(k, ("tasks", "text"))
        src = D.get(key_name, [])
        it = find(src, r[2], find_key)
        if it:
            src.remove(it); save(); refresh(); return "🗑 Удалил: " + it.get(find_key, it.get("title", ""))
        return "Не нашёл такое."
    if R(r"удали (?:все )?выполненн"):
        n = len([t for t in tasks if t.get("done")]); D["tasks"][:] = [t for t in tasks if not t.get("done")]; save(); refresh(); return f"🗑 Убрал выполненных: {n}"
    r = re.match(r"^(?:я\s+)?(?:выполнил[а]?|сделал[а]?|закончил[а]?|заверши|завершил[а]?|готово|отметь(?:\s+выполненной)?)\s*(?:задачу|привычку)?:?\s*(.+)$", m, re.I)
    if r:
        h = find(habits, r[1]) if ("привыч" in l or not find([t for t in tasks if not t.get("done")], r[1])) else None
        if h:
            td = now.date().isoformat()
            if td not in h.get("log", []): h["log"].append(td)
            save(); refresh(); return f"🔥 Отмечено: {h.get('text','')} (серия {len(h.get('log', []))})"
        t = find([t for t in tasks if not t.get("done")], r[1])
        if t: t["done"] = True; save(); refresh(); return f"✅ Выполнено: {t.get('text','')}. Так держать{nm}!"
    # --- звуки, игры, дизайн, самостоятельное оформление ---
    snd = R(r"звук|мелоди|рингтон|сигнал|звонок"); want = R(r"созда|сдела|придума|сочин|сгенерир|хочу|нужен|нужна|нужно")
    GAMEW = R(r"\bигр|game|поигра|сыграем|змейк|понг|арканоид|flappy|флапп|тетрис|tetris|2048")
    setv = R(r"постав|установ|назнач|смени|поменя|использу"); ss = D.get("sounds", [])
    if snd and want and not R(r"сайт|лендинг") and not GAMEW:
        d = re.sub(r"^(?:ок(?:ей)?[,\s]+|пожалуйста[,\s]+|слушай[,\s]+)?(?:созда\w*|сдела\w*|придума\w*|сочини\w*|сгенерир\w*)\s+(?:мне\s+)?", "", m.strip(), flags=re.I) or m
        if R(r"\bне\b.*постав.*\bа\b.*созда"): d = "приятный звук будильника"
        al = bool(R(r"будильн|разбуд|просып")) or "будильника" in d
        return f"🎵 Сочиняю звук: «{d}». " + ("Поставлю на ближайший будильник." if al else "Добавлю в библиотеку «Звуки».") + f" [[sound: {d}||{'alarm' if al else 'lib'}]]"
    if snd and setv:
        pick = next((s for s in ss if s.get("name","").lower() in l), None)
        if not pick and ss and R(r"последн|нов|этот|его|её|ее|созданн"): pick = ss[-1]
        if not pick:
            w = [x for x in re.findall(r"\w{4,}", l) if not x.startswith(("звук", "будиль", "постав", "устан", "назна"))]
            pick = next((s for s in ss if any(x[:5] in s.get("name","").lower() for x in w)), None) if w else None
        if not pick: return "Какой звук поставить? В библиотеке: " + (", ".join(s.get("name","") for s in ss[-8:]) or "пусто, скажи «создай нежный звук для будильника»") + "."
        act = sorted([r_ for r_ in rem if r_.get("on")], key=lambda r_: r_.get("when", ""))
        if R(r"будильн"): act = [r_ for r_ in act if r_.get("kind") == "Будильник"] or act
        tm = re.search(r"(\d{1,2})[:.](\d{2})", l)
        if tm and act: act = [r_ for r_ in act if r_.get("when","")[11:] == f"{int(tm[1]):02d}:{tm[2]}"] or act
        if not act: return "Нет активных будильников и напоминаний. Сначала поставь будильник."
        act[0]["sound"] = pick["id"]; save(); refresh()
        return f"🎵 Готово: на «{act[0].get('text','')}» ({act[0].get('when','')[11:]}) теперь играет «{pick['name']}»."
    if R(r"какой звук|что за звук|какая мелоди") and R(r"будильн|напомин"):
        act = sorted([r_ for r_ in rem if r_.get("on")], key=lambda r_: r_.get("when", ""))
        if not act: return "Активных будильников нет."
        s0 = next((x for x in ss if x["id"] == act[0].get("sound")), None)
        return f"⏰ Ближайший: «{act[0].get('text','')}» в {act[0].get('when','')[11:]}. " + (f"Звук: «{s0['name']}»." if s0 else "Звук обычный.") + " Другой? Скажи: «создай нежный звук для будильника»."
    if R(r"динозавр|dino"):
        if R(r"убери|скрой|выключ|закрой|удали"): return "Убрал динозаврика. [[game: off]]"
        return "🦖 Динозаврик в левом нижнем углу. Прыгать: клик по полю или пробел. [[game: on]]"
    gk = pick_game(l)
    if gk and (want or R(r"поигра|запусти|открой|сыграем|включи|\bигр")) and not E.get("LLM"):
        return E["make_game_ask"](gk)
    if GAMEW and (want or R(r"поигра|сыграем")) and not E.get("LLM"):
        return ("🎮 Без подключённого ИИ я сразу создаю готовые игры: змейка, пинг-понг, арканоид, flappy, 2048, тетрис и динозаврик. "
                "Скажи, например: «создай игру змейка». Свою особенную игру Круг придумает с подключённым ИИ (Настройки → бесплатный OpenRouter).")
    ap = re.match(r"^(?:пожалуйста[, ]+)?(?:открой|запусти|включи|открыть|запустить)\s+(?:мне\s+)?(?:приложени[ея]\s+|программу\s+)?(.+)$", l)
    if ap and not R(r"музык|песн|трек|плейлист|задач|заметк|расписан|напоминан|привычк|настройк|проект|дизайн|фокус|звук|памят|голос"):
        r_ = E["open_app"](ap[1])
        if r_: return r_
    if R(r"музык|песн[юиь]|трек|плейлист") and R(r"включи|поставь|запусти|найди|сыграй|послушать|что за|определи|угадай|как называется|подбери") and not R(r"будильн|напомин|звонок|рингтон") and not E.get("LLM"):
        return E["music_cmd"](m)
    self_ui = R(r"приложени|интерфейс|себе|твой|твоё|твое|свой|оформлен|внешн|облик|тему|тема|стиль|цвет")
    studio = R(r"студи\w*\s+дизайн|в\s+дизайне|во\s+вкладке\s+дизайн")
    if want and not GAMEW and (studio or (not E.get("LLM") and (R(r"сайт|лендинг|визитк|постер|логотип") or (R(r"дизайн") and R(r"\bдля\b") and not self_ui)))):
        k = "card" if R(r"визитк|постер") else "logo" if R(r"логотип") else "anim" if R(r"анимаци") else "landing"
        return f"🎨 Создаю в студии дизайна: «{m}». [[design: {k}|{m}]]"
    ui_ctx = R(r"дизайн|тем[ауыо]|стил[ьяе]|оформлен|внешн|интерфейс|облик|приложени")
    if ui_ctx and R(r"верни|сброс|стандарт|по умолчанию"): return "🎨 Возвращаю стандартный вид. [[ui: reset]]"
    cols = {"красн": "#ff4d5e", "оранж": "#ff9a3c", "жёлт": "#ffd24a", "желт": "#ffd24a", "зелён": "#3ddc84", "зелен": "#3ddc84", "голуб": "#22d3ee", "бирюз": "#22d3ee", "син": "#4d8dff", "фиолет": "#a066ff", "розов": "#ff6fb5", "бел": "#f5f5f5"}
    if R(r"акцент|основн\w* цвет|цвет\w* (?:приложени|интерфейс|кнопок)") or (R(r"цвет") and R(r"интерфейс|приложени")):
        for k, v in cols.items():
            if R(k): return f"🎨 Меняю акцентный цвет. [[ui: accent={v}]]"
    if ui_ctx and R(r"светл"): return "☀ Светлая тема. [[ui: theme=light]]"
    if ui_ctx and R(r"тёмн|темн"): return "🌙 Тёмная тема. [[ui: theme=dark]]"
    if R(r"круглее|скругл"): return "Скругляю углы. [[ui: radius=28px]]"
    if R(r"острее|квадратн|угловат"): return "Делаю углы острее. [[ui: radius=4px]]"
    if R(r"крупнее|больше шрифт|увелич\w* шрифт|крупный шрифт"): return "Увеличиваю шрифт. [[ui: fs=17px]]"
    if R(r"мельче|меньше шрифт|уменьш\w* шрифт"): return "Уменьшаю шрифт. [[ui: fs=13.5px]]"
    if R(r"фон|эффект") and R(r"звёзд|звезд|сетк|свечени|убери|без|выключ"):
        fx = "stars" if R(r"звёзд|звезд") else "grid" if R(r"сетк") else "glow" if R(r"свечени") else "none"
        return f"✨ Меняю эффект фона. [[ui: fx={fx}]]"
    STYLES = {"киберпанк": "киберпанк", "уют|тепл|тёпл": "уют", "минимал": "минимализм", "неон": "неон", "океан|морск": "океан", "закат": "закат", "лес|природ": "лес", "сакур": "сакура", "золот|премиум|люкс": "золото", "матриц|хакер": "матрица", "космос|космич": "космос", "ретро|пиксел": "ретро"}
    if ui_ctx or R(r"в стиле"):
        for pat, name in STYLES.items():
            if R(pat): return f"🎨 Применяю стиль «{name}». [[ui: preset={name}]]"
    if R(r"дизайн|интерфейс|оформлен|внешн\w* вид|облик") and R(r"придума|перепиш|перерис|переделай|измени|сам|как хочешь|по-своему|обнови|освежи|сделай") and self_ui:
        if D.get("cfg", {}).get("provider", "").startswith("Krug Brain"):
            return "🎨 Свободную перерисовку интерфейса делает подключённый ИИ (Настройки). Без него могу применить стили: киберпанк, уют, минимализм, неон, океан, закат, лес, сакура, золото, матрица, космос, ретро; сменить акцентный цвет («акцент красный»), скруглить углы, включить звёзды или сетку на фоне."
        return f"🎨 Перерисовываю интерфейс… [[restyle: {m}]]"
    if l in ("расписание", "покажи расписание", "моё расписание", "мое расписание", "что в расписании"):
        rows = sorted(sched, key=lambda x: (DAYS.index(x.get("day","")) if x.get("day","") in DAYS else 9, x.get("time","")))
        return ("📆 Расписание:\n" + "\n".join(f"  {x.get('day','')} {x.get('time','')} — {x.get('text','')}" for x in rows)) if rows else "Расписание пусто. Скажи: «добавь в расписание пн,ср 18:00 английский»."
    # напоминания, будильники, таймеры
    if R(r"напомни|будильн|разбуди|таймер"):
        kind = "Будильник" if R(r"будильн|разбуди") else "Напоминание"
        src = re.sub(r"таймер на", "через", m, flags=re.I)
        w, rest, rep = parse_when(src, now)
        txt = re.sub(r"^(?:\s|,|напомни(?:ть)?|мне|будильн\w*|разбуди|меня|таймер|пожалуйста|что|чтобы|о том|окей|ок|поставь|установи|заведи|будь добр)+", "", rest, flags=re.I).strip()
        txt = re.sub(r"\s+(?:до|к|на|в)$", "", txt) or ("Таймер" if "таймер" in l else kind)
        if w: E["add_rem"](txt, w, kind, rep); return f"✅ {kind}: «{txt}» — {w:%d.%m %H:%M}" + (f", {rep.lower()}" if rep != "Один раз" else "")
        mem["pending"] = {"k": "rem", "text": txt, "kind": kind}; return f"На какое время поставить «{txt}»? (например: через 20 минут / завтра в 9:00)"
    # расписание
    r = re.match(r"^(?:добавь\s+в\s+расписание|расписание)[:\s]+((?:(?:пн|вт|ср|чт|пт|сб|вс)[\s,]*)+)\s*(\d{1,2})[:.](\d{2})\s+(.+)$", m, re.I)
    if r:
        ds = [d.capitalize() for d in re.findall(r"(пн|вт|ср|чт|пт|сб|вс)", r[1].lower())]
        sched_entry = {"id": uid(), "day": d, "time": f"{int(r[2]):02d}:{r[3]}", "text": r[4]} if (d := (ds[0] if ds else "")) else {}
        for d2 in ds: D["sched"].append({"id": uid(), "day": d2, "time": f"{int(r[2]):02d}:{r[3]}", "text": r[4]})
        save(); refresh(); return f"📆 Добавил в расписание: {', '.join(ds)} {int(r[2]):02d}:{r[3]} — {r[4]}"
    # заметки, привычки, задачи
    r = re.match(r"^(?:добавь |создай |запиши )?заметк[ауи]?[:\s-]+(.+)", m, re.I)
    if r: notes.append({"id": uid(), "title": r[1][:40], "body": r[1]}); save(); refresh(); return "📝 Заметка сохранена"
    r = re.match(r"^(?:добавь |создай )?привычк[ауи]?[:\s-]+(.+)", m, re.I)
    if r and not l.startswith("отметь"): habits.append({"id": uid(), "text": r[1], "log": []}); save(); refresh(); return f"🔁 Привычка добавлена: {r[1]}"
    r = re.match(r"^(?:добавь |создай |запиши |поставь )?(?:мне )?задач[ауи]?[:\s-]+(.+)", m, re.I) or re.match(r"^(?:мне\s+)?(?:надо|нужно|не забыть|не забудь)\s+(.{3,})", m, re.I)
    if r:
        txt = r[1]; prio = "Высокий" if re.search(r"срочно|важно|!!", txt, re.I) else "Низкий" if re.search(r"не срочно|потом|когда-нибудь", txt, re.I) else "Средний"
        txt = re.sub(r"\b(?:не срочно|срочно|важно|потом|когда-нибудь)\b|!!", "", txt, flags=re.I)
        w, rest, _ = parse_when(txt, now); due = w.strftime("%Y-%m-%d") if w else ""
        txt = re.sub(r"\s+(?:до|к|на|в|числа)$", "", re.sub(r"\s+", " ", rest if w else txt).strip(" ,.-—:")) or r[1]
        task(txt, prio, due); save(); refresh(); return f"✅ Задача: {txt}" + (f" · приоритет {prio}" if prio != "Средний" else "") + (f" · до {due}" if due else "")
    # планирование
    if R(r"план недел|на неделю"): return week_view(D, now)
    if l in ("план", "/план", "план на день", "составь план", "план на сегодня", "мой план") or R(r"^(?:составь|покажи|сделай) план (?:на день|на сегодня)"): return E["day_plan"]()
    if R(r"приоритиз|расставь приоритет|что важнее|с чего начать день"): return matrix(D, now)
    if R(r"итоги|итог дня|статистик|как я справ"):
        done = len([t for t in tasks if t.get("done")]); op = len(tasks) - done; td = now.date().isoformat()
        hb = len([h for h in habits if td in h.get("log", [])])
        return f"📊 Выполнено задач: {done}, осталось: {op}. Привычек сегодня: {hb}/{len(habits)}." + (" Отличный прогресс!" if done > op else " Выбери одну главную задачу и начни с неё.")
    if E.get("LLM"): return None
    for k, v in TPL.items():
        if k in l and R(r"план|состав|режим|распорядок"): return v
    r = re.match(r"^(?:составь|сделай|построй|создай|дай)\s+(?:мне\s+)?план\s+(?:изучения|освоения|подготовки к|подготовки|для|по|на)?\s*(.+)$", m, re.I)
    if r:
        topic = r[1]; n, unit = 6, "нед."
        q = re.search(r"\s*(?:на|за)\s+(\d+)\s*(дн|нед|мес)\S*", topic, re.I)
        if q:
            n = int(q[1]); unit = {"дн": "дн.", "нед": "нед.", "мес": "мес."}[q[2].lower()]; topic = topic.replace(q[0], "")
        n = max(1, min(n, 52)); txt, items = study_plan(topic.strip(" ,."), n, unit)
        mem["pending"] = {"k": "tasks", "items": items}; return txt + "\n\nДобавить эти этапы в задачи? Напиши «да»."
    r = re.match(r"^(?:разбей|декомпозируй|распиши)\s+(?:задачу\s+)?(.+?)(?:\s+на\s+(?:шаги|этапы|подзадачи))?$", m, re.I) or re.match(r"^(?:как (?:мне )?(?:сделать|выполнить|начать)|с чего начать)\s+(.+)$", m, re.I)
    if r:
        st = steps_for(r[1].strip()); mem["pending"] = {"k": "tasks", "items": st}
        return f"🪜 Шаги для «{r[1].strip()}»:\n" + "\n".join(f"  {i}. {s.split(': ', 1)[1]}" for i, s in enumerate(st, 1)) + "\n\nДобавить шаги в задачи? Напиши «да»."
    r = re.match(r"^(?:напиши|составь|сделай|создай|придумай|дай)\s+(?:мне\s+)?промпт(?:\s+(?:для|на|про|чтобы|по))?\s*(.+)$", m, re.I)
    if r: return "✨ Готовый промпт (скопируй в любой ИИ):\n\n" + make_prompt(r[1].strip()) + "\n\nТочнее настроить можно во вкладке «Промпты»."
    if R(r"что такое|расскажи про|объясни|совет|как (?:не )?(?:откладывать|выспаться|сосредоточиться)|метод"):
        for pat, txt in KB.items():
            if re.search(pat, l): return txt
    return None

def fallback(m, E):
    D = E["D"]; mem = D.setdefault("mem", {}); l = m.lower(); out = []
    words = re.findall(r"\w{4,}", l)
    hits = [n.get("title","") for n in D.get("notes", []) if any(w[:5] in ((n.get("title","") + n.get("body","")).lower()) for w in words)][:5]
    if hits: out.append("🔎 В твоих заметках похожее: " + "; ".join(hits))
    c = difflib.get_close_matches(l, EX, 2, 0.4)
    if c: out.append("Возможно, ты имел в виду:\n" + "\n".join("• " + x for x in c))
    mem["pending"] = {"k": "save", "text": m}; mem["last_unknown"] = m
    out.append("Эту фразу я пока не умею. Можно:\n• написать «задача» или «заметка» — сохраню как есть;\n• научить меня: «научи: <ответ или команда>» — запомню и в следующий раз отвечу сам.\n"
               "Для умных свободных ответов подключи ИИ: Настройки → бесплатный OpenRouter. Команды — «помощь».")
    return "\n\n".join(out)


# ---------- готовые игры (работают без ИИ и без интернета) ----------
_PAGE = r'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>@@TITLE@@</title>
<style>*{box-sizing:border-box;margin:0}body{min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at 30% 20%,#1b1f4a,#0a0b1a 70%);color:#eef;font:16px system-ui,sans-serif;user-select:none}.w{text-align:center;padding:10px}h1{font-size:20px;margin-bottom:8px;letter-spacing:1px}canvas{display:block;margin:0 auto;background:#0d1030;border:2px solid #3b4290;border-radius:14px;box-shadow:0 0 40px #5b6cff55;max-width:96vw;max-height:78vh;touch-action:none}p{color:#9aa3d8;font-size:13px;margin-top:10px}</style>
<div class="w"><h1>@@TITLE@@</h1><canvas id="c" width="@@W@@" height="@@H@@"></canvas><p>@@HINT@@</p></div><script>
const c=document.getElementById('c'),x=c.getContext('2d'),W=c.width,H=c.height;
const LS={g:k=>{try{return +localStorage.getItem(k)||0}catch(e){return 0}},s:(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}}};
const rr=(a,b,w,h,r)=>{x.beginPath();x.roundRect?x.roundRect(a,b,w,h,r):x.rect(a,b,w,h)};
const pos=e=>{const r=c.getBoundingClientRect();return{x:(e.clientX-r.left)*W/r.width,y:(e.clientY-r.top)*H/r.height}};
const ov=(t,s)=>{x.fillStyle='#000b';x.fillRect(0,0,W,H);x.fillStyle='#fff';x.textAlign='center';x.font='bold 30px system-ui';x.fillText(t,W/2,H/2-8);x.font='16px system-ui';x.fillStyle='#b9c0ff';x.fillText(s,W/2,H/2+24);x.textAlign='left'};
const bg=()=>{x.fillStyle='#0d1030';x.fillRect(0,0,W,H)};
@@JS@@
</script></html>'''

_SNAKE = r'''
const N=24,S=W/N;let sn,dir={x:1,y:0},nd=dir,food,score=0,best=LS.g('snk'),over=true,last=0,delay=110;
const put=()=>{do{food={x:Math.random()*N|0,y:Math.random()*N|0}}while(sn.some(s=>s.x==food.x&&s.y==food.y))};
function reset(){sn=[{x:10,y:12},{x:9,y:12},{x:8,y:12}];dir=nd={x:1,y:0};score=0;over=false;delay=110;put()}
function step(){dir=nd;const h={x:sn[0].x+dir.x,y:sn[0].y+dir.y};
 if(h.x<0||h.y<0||h.x>=N||h.y>=N||sn.some(s=>s.x==h.x&&s.y==h.y)){over=true;if(score>best){best=score;LS.s('snk',best)}return}
 sn.unshift(h);if(h.x==food.x&&h.y==food.y){score++;delay=Math.max(55,delay-3);put()}else sn.pop()}
function draw(){bg();x.strokeStyle='#ffffff08';for(let i=0;i<=N;i++){x.beginPath();x.moveTo(i*S,0);x.lineTo(i*S,H);x.moveTo(0,i*S);x.lineTo(W,i*S);x.stroke()}
 x.fillStyle='#ff5d73';x.shadowColor='#ff5d73';x.shadowBlur=14;x.beginPath();x.arc(food.x*S+S/2,food.y*S+S/2,S/2-3,0,7);x.fill();x.shadowBlur=0;
 sn.forEach((s,i)=>{x.fillStyle='hsl('+(150+i*4)+',80%,'+Math.max(30,60-i*.6)+'%)';rr(s.x*S+1,s.y*S+1,S-2,S-2,6);x.fill()});
 x.fillStyle='#fff';x.font='bold 16px system-ui';x.fillText('Счёт '+score+'   Рекорд '+best,10,22);
 if(over)ov(score?'Игра окончена':'ЗМЕЙКА','Пробел или касание — начать')}
function loop(t){if(!over&&t-last>delay){last=t;step()}draw();requestAnimationFrame(loop)}
const KM={ArrowUp:[0,-1],KeyW:[0,-1],ArrowDown:[0,1],KeyS:[0,1],ArrowLeft:[-1,0],KeyA:[-1,0],ArrowRight:[1,0],KeyD:[1,0]};
addEventListener('keydown',e=>{const k=KM[e.code];if(k){if(k[0]!=-dir.x||k[1]!=-dir.y)nd={x:k[0],y:k[1]};e.preventDefault()}if(e.code=='Space'){e.preventDefault();if(over)reset()}});
let tx=null,ty=0;c.addEventListener('pointerdown',e=>{if(over){reset();return}tx=e.clientX;ty=e.clientY});
c.addEventListener('pointerup',e=>{if(tx==null)return;const dx=e.clientX-tx,dy=e.clientY-ty;tx=null;if(Math.max(Math.abs(dx),Math.abs(dy))<20)return;const k=Math.abs(dx)>Math.abs(dy)?[Math.sign(dx),0]:[0,Math.sign(dy)];if(k[0]!=-dir.x||k[1]!=-dir.y)nd={x:k[0],y:k[1]}});
reset();over=true;requestAnimationFrame(loop);
'''

_PONG = r'''
const PH=80;let py=H/2-PH/2,ay=py,ball={x:W/2,y:H/2,vx:5,vy:2},sc=[0,0],state=0,keys={},trail=[],msg='';
const serve=d=>{ball={x:W/2,y:H/2,vx:5*d,vy:Math.random()*5-2.5};trail=[]};
function start(){sc=[0,0];serve(1);state=1;msg=''}
function upd(){
 if(keys.ArrowUp||keys.KeyW)py-=7;if(keys.ArrowDown||keys.KeyS)py+=7;py=Math.max(0,Math.min(H-PH,py));
 ay+=Math.max(-4.4,Math.min(4.4,ball.y-PH/2-ay));ay=Math.max(0,Math.min(H-PH,ay));
 ball.x+=ball.vx;ball.y+=ball.vy;
 if(ball.y<6||ball.y>H-6){ball.vy*=-1;ball.y=Math.max(6,Math.min(H-6,ball.y))}
 trail.push([ball.x,ball.y]);if(trail.length>14)trail.shift();
 if(ball.vx<0&&ball.x-6<=30&&ball.x>14&&ball.y>py-6&&ball.y<py+PH+6){ball.vx=Math.min(13,-ball.vx*1.07);ball.vy=(ball.y-(py+PH/2))/(PH/2)*6}
 if(ball.vx>0&&ball.x+6>=W-30&&ball.x<W-14&&ball.y>ay-6&&ball.y<ay+PH+6){ball.vx=-Math.min(13,ball.vx*1.07);ball.vy=(ball.y-(ay+PH/2))/(PH/2)*6}
 if(ball.x<-10){sc[1]++;serve(1)}if(ball.x>W+10){sc[0]++;serve(-1)}
 if(sc[0]>=7||sc[1]>=7){state=2;msg=sc[0]>=7?'Ты победил! 🎉':'Победил компьютер'}}
function draw(){bg();x.strokeStyle='#ffffff25';x.setLineDash([8,10]);x.beginPath();x.moveTo(W/2,0);x.lineTo(W/2,H);x.stroke();x.setLineDash([]);
 x.fillStyle='#6ea8ff';rr(20,py,10,PH,5);x.fill();x.fillStyle='#ff8fb8';rr(W-30,ay,10,PH,5);x.fill();
 trail.forEach((t,i)=>{x.fillStyle='rgba(255,255,255,'+(i/trail.length*.35)+')';x.beginPath();x.arc(t[0],t[1],6*i/trail.length+1,0,7);x.fill()});
 x.fillStyle='#fff';x.beginPath();x.arc(ball.x,ball.y,6,0,7);x.fill();
 x.font='bold 44px system-ui';x.textAlign='center';x.fillStyle='#ffffff55';x.fillText(sc[0],W/2-60,56);x.fillText(sc[1],W/2+60,56);x.textAlign='left';
 if(state==0)ov('ПИНГ-ПОНГ','Пробел или клик — старт. Игра до 7');if(state==2)ov(msg,'Пробел или клик — ещё раз')}
function loop(){if(state==1)upd();draw();requestAnimationFrame(loop)}
addEventListener('keydown',e=>{keys[e.code]=1;if(e.code=='Space'){e.preventDefault();if(state!=1)start()}if(e.code.startsWith('Arrow'))e.preventDefault()});
addEventListener('keyup',e=>keys[e.code]=0);
c.addEventListener('pointermove',e=>{if(state==1)py=Math.max(0,Math.min(H-PH,pos(e).y-PH/2))});
c.addEventListener('pointerdown',e=>{if(state!=1)start()});
loop();
'''

_BREAKOUT = r'''
const PW=90;let px=W/2-PW/2,ball={x:W/2,y:H-44,vx:0,vy:0,stuck:true},bricks=[],score=0,lives=3,state=0,keys={},best=LS.g('brk'),lvl=1;
function build(){bricks=[];for(let r=0;r<6;r++)for(let i=0;i<10;i++)bricks.push({x:i*48+4,y:50+r*24,w:40,h:18,c:'hsl('+(r*50+200)+',80%,60%)',a:true})}
function park(){ball={x:px+PW/2,y:H-44,vx:0,vy:0,stuck:true}}
function newGame(){score=0;lives=3;lvl=1;build();px=W/2-PW/2;park();state=1}
function launch(){if(ball.stuck){ball.stuck=false;ball.vx=(Math.random()*2-1)*3;ball.vy=-(5+lvl*.4)}}
function upd(){
 if(keys.ArrowLeft||keys.KeyA)px-=8;if(keys.ArrowRight||keys.KeyD)px+=8;px=Math.max(0,Math.min(W-PW,px));
 if(ball.stuck){ball.x=px+PW/2;return}
 ball.x+=ball.vx;ball.y+=ball.vy;
 if(ball.x<6||ball.x>W-6){ball.vx*=-1;ball.x=Math.max(6,Math.min(W-6,ball.x))}if(ball.y<6){ball.vy=Math.abs(ball.vy)}
 if(ball.vy>0&&ball.y+6>=H-30&&ball.y<H-14&&ball.x>px-4&&ball.x<px+PW+4){ball.vy=-Math.abs(ball.vy);ball.vx=(ball.x-(px+PW/2))/(PW/2)*6}
 for(const b of bricks){if(b.a&&ball.x+6>b.x&&ball.x-6<b.x+b.w&&ball.y+6>b.y&&ball.y-6<b.y+b.h){b.a=false;score+=10;ball.vy*=-1;break}}
 if(!bricks.some(b=>b.a)){lvl++;build();park()}
 if(ball.y>H+10){lives--;if(lives<=0){state=2;if(score>best){best=score;LS.s('brk',best)}}else park()}}
function draw(){bg();bricks.forEach(b=>{if(b.a){x.fillStyle=b.c;rr(b.x,b.y,b.w,b.h,4);x.fill()}});
 x.fillStyle='#6ea8ff';rr(px,H-30,PW,12,6);x.fill();x.fillStyle='#fff';x.beginPath();x.arc(ball.x,ball.y,6,0,7);x.fill();
 x.font='bold 15px system-ui';x.fillText('Счёт '+score+'  Рекорд '+best+'  Жизни '+'♥'.repeat(Math.max(0,lives))+'  Уровень '+lvl,10,24);
 if(state==0)ov('АРКАНОИД','Пробел или клик — старт');if(state==2)ov('Игра окончена','Счёт '+score+'. Пробел — заново');if(state==1&&ball.stuck){x.fillStyle='#b9c0ff';x.font='14px system-ui';x.textAlign='center';x.fillText('Пробел или клик — запуск мяча',W/2,H-70);x.textAlign='left'}}
function loop(){if(state==1)upd();draw();requestAnimationFrame(loop)}
addEventListener('keydown',e=>{keys[e.code]=1;if(e.code=='Space'){e.preventDefault();if(state!=1)newGame();else launch()}if(e.code.startsWith('Arrow'))e.preventDefault()});
addEventListener('keyup',e=>keys[e.code]=0);
c.addEventListener('pointermove',e=>{if(state==1)px=Math.max(0,Math.min(W-PW,pos(e).x-PW/2))});
c.addEventListener('pointerdown',e=>{if(state!=1)newGame();else launch()});
build();loop();
'''

_FLAPPY = r'''
let by=H/2,vy=0,pipes=[],score=0,best=LS.g('flp'),state=0,fr=0,cl=[{x:60,y:90},{x:260,y:140},{x:380,y:60}];
function reset(){by=H/2;vy=0;pipes=[];score=0;fr=0}
function flap(){if(state==2){reset();state=0;return}state=1;vy=-7.2}
function upd(){vy+=.42;by+=vy;fr++;if(fr%88==1)pipes.push({x:W,y:80+Math.random()*(H-330),g:140,s:false});
 pipes.forEach(p=>p.x-=2.6);pipes=pipes.filter(p=>p.x>-70);
 for(const p of pipes){if(!p.s&&p.x+52<80){p.s=true;score++}if(92>p.x&&68<p.x+52&&(by-12<p.y||by+12>p.y+p.g))state=2}
 if(by>H-40||by<-30)state=2;if(state==2&&score>best){best=score;LS.s('flp',best)}}
function draw(){const g=x.createLinearGradient(0,0,0,H);g.addColorStop(0,'#5ec8ff');g.addColorStop(1,'#bdeeff');x.fillStyle=g;x.fillRect(0,0,W,H);
 x.fillStyle='#ffffffaa';cl.forEach(k=>{if(state==1)k.x-=.4;if(k.x<-60)k.x=W+60;x.beginPath();x.arc(k.x,k.y,22,0,7);x.arc(k.x+24,k.y+6,18,0,7);x.arc(k.x-22,k.y+8,16,0,7);x.fill()});
 pipes.forEach(p=>{x.fillStyle='#3cc35a';x.fillRect(p.x,0,52,p.y);x.fillRect(p.x,p.y+p.g,52,H);x.fillStyle='#2a9a44';x.fillRect(p.x-4,p.y-22,60,22);x.fillRect(p.x-4,p.y+p.g,60,22)});
 x.fillStyle='#d9b36b';x.fillRect(0,H-40,W,40);x.fillStyle='#8bd450';x.fillRect(0,H-40,W,8);
 x.save();x.translate(80,by);x.rotate(Math.max(-.5,Math.min(1,vy/12)));x.fillStyle='#ffd23f';x.beginPath();x.arc(0,0,13,0,7);x.fill();x.fillStyle='#fff';x.beginPath();x.arc(5,-4,5,0,7);x.fill();x.fillStyle='#222';x.beginPath();x.arc(7,-4,2,0,7);x.fill();x.fillStyle='#ff7a3c';x.beginPath();x.moveTo(11,0);x.lineTo(21,3);x.lineTo(11,7);x.fill();x.restore();
 x.fillStyle='#fff';x.strokeStyle='#0006';x.lineWidth=4;x.font='bold 40px system-ui';x.textAlign='center';x.strokeText(score,W/2,60);x.fillText(score,W/2,60);x.textAlign='left';x.lineWidth=1;
 if(state==0)ov('FLAPPY','Пробел, клик или касание — взмах');if(state==2)ov('Конец игры','Счёт '+score+'  Рекорд '+best+'. Пробел — ещё раз')}
function loop(){if(state==1)upd();else if(state==0)by=H/2+Math.sin(Date.now()/250)*8;draw();requestAnimationFrame(loop)}
addEventListener('keydown',e=>{if(e.code=='Space'||e.code=='ArrowUp'){e.preventDefault();flap()}});
c.addEventListener('pointerdown',flap);loop();
'''

_TETRIS = r'''
const C=10,R=20,S=24,OX=12;let grid,cur,nxt,score=0,lines=0,best=LS.g('ttr'),state=0,last=0,delay=600;
const SH={I:[[1,1,1,1]],O:[[1,1],[1,1]],T:[[0,1,0],[1,1,1]],S:[[0,1,1],[1,1,0]],Z:[[1,1,0],[0,1,1]],J:[[1,0,0],[1,1,1]],L:[[0,0,1],[1,1,1]]};
const CL={I:'#4dd8ff',O:'#ffd84d',T:'#b04dff',S:'#4dff88',Z:'#ff4d6a',J:'#4d6aff',L:'#ff9a3c'};
const rnd=()=>{const k=Object.keys(SH)[Math.random()*7|0];return{k,m:SH[k].map(r=>r.slice()),x:3,y:0}};
const rot=m=>m[0].map((_,i)=>m.map(r=>r[i]).reverse());
const ok=(m,x,y)=>m.every((r,j)=>r.every((v,i)=>!v||(x+i>=0&&x+i<C&&y+j<R&&(y+j<0||!grid[y+j][x+i]))));
function reset(){grid=Array.from({length:R},()=>Array(C).fill(0));score=0;lines=0;delay=600;nxt=rnd();spawn();state=1}
function spawn(){cur=nxt;nxt=rnd();cur.x=3;cur.y=0;if(!ok(cur.m,cur.x,cur.y)){state=2;if(score>best){best=score;LS.s('ttr',best)}}}
function lock(){cur.m.forEach((r,j)=>r.forEach((v,i)=>{if(v&&cur.y+j>=0)grid[cur.y+j][cur.x+i]=cur.k}));let n=0;for(let j=R-1;j>=0;j--)if(grid[j].every(v=>v)){grid.splice(j,1);grid.unshift(Array(C).fill(0));n++;j++}if(n){lines+=n;score+=[0,100,300,500,800][n];delay=Math.max(120,600-lines*18)}spawn()}
const step=()=>{if(ok(cur.m,cur.x,cur.y+1))cur.y++;else lock()};
const mv=d=>{if(ok(cur.m,cur.x+d,cur.y))cur.x+=d};
function rt(){const m=rot(cur.m);for(const k of [0,-1,1,-2,2])if(ok(m,cur.x+k,cur.y)){cur.m=m;cur.x+=k;return}}
function drop(){while(ok(cur.m,cur.x,cur.y+1))cur.y++;lock()}
const cell=(x0,y0,col)=>{x.fillStyle=col;rr(x0+1,y0+1,S-2,S-2,5);x.fill()};
function draw(){bg();x.strokeStyle='#ffffff10';for(let i=0;i<=C;i++){x.beginPath();x.moveTo(OX+i*S,0);x.lineTo(OX+i*S,R*S);x.stroke()}for(let j=0;j<=R;j++){x.beginPath();x.moveTo(OX,j*S);x.lineTo(OX+C*S,j*S);x.stroke()}
 if(grid){grid.forEach((r,j)=>r.forEach((v,i)=>{if(v)cell(OX+i*S,j*S,CL[v])}));
  if(state==1){let gy=cur.y;while(ok(cur.m,cur.x,gy+1))gy++;cur.m.forEach((r,j)=>r.forEach((v,i)=>{if(v){x.globalAlpha=.25;cell(OX+(cur.x+i)*S,(gy+j)*S,CL[cur.k]);x.globalAlpha=1}}));
   cur.m.forEach((r,j)=>r.forEach((v,i)=>{if(v)cell(OX+(cur.x+i)*S,(cur.y+j)*S,CL[cur.k])}))}}
 x.fillStyle='#fff';x.font='bold 15px system-ui';x.fillText('Счёт',270,40);x.font='bold 24px system-ui';x.fillText(score,270,68);x.font='14px system-ui';x.fillStyle='#9aa3d8';x.fillText('Линии '+lines,270,92);x.fillText('Рекорд '+best,270,112);x.fillText('Дальше:',270,150);
 if(nxt)nxt.m.forEach((r,j)=>r.forEach((v,i)=>{if(v)cell(270+i*S,165+j*S,CL[nxt.k])}));
 if(state==0)ov('ТЕТРИС','Пробел или касание — старт');if(state==2)ov('Игра окончена','Счёт '+score+'. Пробел — заново')}
function loop(t){if(state==1&&t-last>delay){last=t;step()}draw();requestAnimationFrame(loop)}
addEventListener('keydown',e=>{if(e.code=='Space'){e.preventDefault();if(state!=1)reset();else drop();return}if(state!=1)return;
 if(e.code=='ArrowLeft'||e.code=='KeyA'){mv(-1);e.preventDefault()}if(e.code=='ArrowRight'||e.code=='KeyD'){mv(1);e.preventDefault()}
 if(e.code=='ArrowDown'||e.code=='KeyS'){step();e.preventDefault()}if(e.code=='ArrowUp'||e.code=='KeyW'){rt();e.preventDefault()}});
let tx=null,ty=0;c.addEventListener('pointerdown',e=>{if(state!=1){reset();return}tx=e.clientX;ty=e.clientY});
c.addEventListener('pointerup',e=>{if(tx==null||state!=1)return;const dx=e.clientX-tx,dy=e.clientY-ty;tx=null;if(Math.abs(dx)<18&&Math.abs(dy)<18)rt();else if(Math.abs(dx)>Math.abs(dy))mv(dx<0?-1:1);else if(dy>0)drop()});
loop(0);
'''

_G2048 = r'''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>2048</title>
<style>*{box-sizing:border-box;margin:0}body{min-height:100vh;display:grid;place-items:center;background:radial-gradient(circle at 30% 20%,#1b1f4a,#0a0b1a 70%);color:#eef;font:16px system-ui,sans-serif;user-select:none}.w{width:min(92vw,420px)}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}h1{font-size:44px}.sc{background:#1b1f4a;border-radius:10px;padding:6px 14px;text-align:center;font-size:12px;color:#9aa3d8}.sc b{display:block;font-size:20px;color:#fff}
#g{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;background:#12153a;padding:10px;border-radius:14px;touch-action:none;position:relative}.t{aspect-ratio:1;border-radius:10px;display:grid;place-items:center;font-weight:800;font-size:clamp(20px,6vw,32px);background:#1e2250;color:#fff;transition:background .15s}
button{margin-top:14px;background:linear-gradient(120deg,#6ea8ff,#b78cff);border:0;color:#fff;border-radius:12px;padding:10px 20px;font:inherit;font-weight:700;cursor:pointer}#o{position:absolute;inset:0;background:#000b;border-radius:14px;display:none;place-items:center;font-size:28px;font-weight:800}p{color:#9aa3d8;font-size:13px;margin-top:10px}</style>
<div class="w"><div class="top"><h1>2048</h1><div style="display:flex;gap:8px"><div class="sc">СЧЁТ<b id="s">0</b></div><div class="sc">РЕКОРД<b id="b">0</b></div></div></div><div id="g"><div id="o">Игра окончена</div></div><button onclick="reset()">Новая игра</button><p>Стрелки или WASD, на телефоне — свайп</p></div><script>
const LS={g:k=>{try{return +localStorage.getItem(k)||0}catch(e){return 0}},s:(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}}};
const COL={0:'#1e2250',2:'#3b4cca',4:'#4c6ef5',8:'#7950f2',16:'#be4bdb',32:'#f06595',64:'#ff6b6b',128:'#fd7e14',256:'#fab005',512:'#82c91e',1024:'#12b886',2048:'#15aabf'};
let g,score=0,best=LS.g('2048'),over=false;const G=document.getElementById('g');
function add(){const e=[];g.forEach((r,i)=>r.forEach((v,j)=>{if(!v)e.push([i,j])}));if(!e.length)return;const p=e[Math.random()*e.length|0];g[p[0]][p[1]]=Math.random()<.9?2:4}
function reset(){g=[[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]];score=0;over=false;add();add();draw()}
function slide(row){const a=row.filter(v=>v);let s=0;for(let i=0;i<a.length-1;i++)if(a[i]==a[i+1]){a[i]*=2;s+=a[i];a.splice(i+1,1)}while(a.length<4)a.push(0);return[a,s]}
function can(){for(let i=0;i<4;i++)for(let j=0;j<4;j++){if(!g[i][j])return true;if(j<3&&g[i][j]==g[i][j+1])return true;if(i<3&&g[i][j]==g[i+1][j])return true}return false}
function move(d){if(over)return;let gain=0;const n=g.map(r=>r.slice());
 for(let k=0;k<4;k++){let line=[0,1,2,3].map(i=>d%2==0?g[k][i]:g[i][k]);if(d>=2)line.reverse();const res=slide(line);gain+=res[1];const r=res[0];if(d>=2)r.reverse();r.forEach((v,i)=>{if(d%2==0)n[k][i]=v;else n[i][k]=v})}
 if(!n.some((r,i)=>r.some((v,j)=>v!=g[i][j])))return;g=n;score+=gain;add();if(score>best){best=score;LS.s('2048',best)}over=!can();draw()}
function draw(){G.querySelectorAll('.t').forEach(e=>e.remove());const o=document.getElementById('o');g.forEach(r=>r.forEach(v=>{const t=document.createElement('div');t.className='t';t.style.background=COL[v]||'#15aabf';t.textContent=v||'';G.insertBefore(t,o)}));
 document.getElementById('s').textContent=score;document.getElementById('b').textContent=best;o.style.display=over?'grid':'none'}
const KM={ArrowLeft:0,KeyA:0,ArrowUp:1,KeyW:1,ArrowRight:2,KeyD:2,ArrowDown:3,KeyS:3};
addEventListener('keydown',e=>{if(e.code in KM){e.preventDefault();move(KM[e.code])}});
let sx=null,sy=0;G.addEventListener('pointerdown',e=>{sx=e.clientX;sy=e.clientY});
G.addEventListener('pointerup',e=>{if(sx==null)return;const dx=e.clientX-sx,dy=e.clientY-sy;sx=null;if(Math.max(Math.abs(dx),Math.abs(dy))<24)return;move(Math.abs(dx)>Math.abs(dy)?(dx<0?0:2):(dy<0?1:3))});
reset();
</script></html>'''

GAMES = {
    "snake": ("Змейка", _SNAKE, 480, 480, "Стрелки или WASD, на телефоне — свайп"),
    "pong": ("Пинг-понг", _PONG, 640, 400, "Стрелки / W S или мышь. До 7 очков"),
    "breakout": ("Арканоид", _BREAKOUT, 480, 560, "Стрелки или мышь, пробел — запуск мяча"),
    "flappy": ("Flappy", _FLAPPY, 360, 540, "Пробел, клик или касание"),
    "2048": ("2048", None, 0, 0, ""),
    "tetris": ("Тетрис", _TETRIS, 360, 480, "Стрелки: движение и поворот ↑, пробел — сбросить вниз; на телефоне — свайпы и тап"),
}
GK = {"tetris": r"тетрис|tetris", "snake": r"змейк|snake", "pong": r"понг|pong|теннис", "breakout": r"арканоид|breakout|кирпич", "flappy": r"flappy|флапп|птиц|птичк", "2048": r"2048"}

def game_html(kind):
    t, js, w, h, hint = GAMES[kind]
    if kind == "2048": return _G2048
    return _PAGE.replace("@@TITLE@@", t).replace("@@W@@", str(w)).replace("@@H@@", str(h)).replace("@@HINT@@", hint).replace("@@JS@@", js)

def pick_game(l):
    for k, p in GK.items():
        if re.search(p, l): return k
    return None
