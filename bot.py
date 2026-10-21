"""Panenka - football quiz bot.
Single file, Python standard library only (no pip install needed).
Needs one environment variable: BOT_TOKEN
"""
import html
import json
import logging
import os
import random
import sqlite3
import sys
import time
import unicodedata
import urllib.error
import urllib.request

logging.basicConfig(
    level=logging.INFO, stream=sys.stdout, format="%(asctime)s %(levelname)s %(message)s"
)

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
DB_PATH = os.environ.get("DB_PATH", "panenka.db")
POINTS = {"rookie": 1, "pro": 2, "legend": 3}

# ------------------------------------------------------------------ data
# (difficulty, question, options, correct index, explanation)
QUESTIONS = [
    ("rookie", "Which country won the first FIFA World Cup in 1930?", ["Brazil", "Uruguay", "Italy", "Argentina"], 1, "Uruguay hosted and won the first World Cup."),
    ("rookie", "Which country won the 2022 World Cup in Qatar?", ["France", "Croatia", "Argentina", "Morocco"], 2, "Argentina beat France on penalties after a 3-3 draw."),
    ("rookie", "Which country has won the most World Cups?", ["Germany", "Brazil", "Italy", "Argentina"], 1, "Brazil have won the World Cup five times."),
    ("rookie", "Which club holds the record for most European Cup / Champions League titles?", ["AC Milan", "Bayern Munich", "Liverpool", "Real Madrid"], 3, "Real Madrid have won the competition more than any other club."),
    ("rookie", "Who has won the most Ballon d'Or awards?", ["Cristiano Ronaldo", "Lionel Messi", "Michel Platini", "Johan Cruyff"], 1, "Lionel Messi has won the award eight times."),
    ("rookie", "Who scored the famous 'Hand of God' goal in 1986?", ["Pelé", "Diego Maradona", "Zico", "Romário"], 1, "Maradona scored it against England in the quarter-final."),
    ("rookie", "Which country hosted the 2014 World Cup?", ["South Africa", "Russia", "Brazil", "Germany"], 2, "Germany won it, beating Argentina in the final at the Maracanã."),
    ("rookie", "What is the name of FC Barcelona's home stadium?", ["Camp Nou", "Mestalla", "San Siro", "Bernabéu"], 0, "Camp Nou has been Barça's home since 1957."),
    ("rookie", "Which country won the 2010 World Cup?", ["Netherlands", "Spain", "Germany", "Uruguay"], 1, "Spain beat the Netherlands 1-0 in the final."),
    ("rookie", "Which country did Johan Cruyff represent?", ["Belgium", "Germany", "Netherlands", "Denmark"], 2, "He led the Netherlands to the 1974 World Cup final."),
    ("pro", "Who is the all-time top scorer in World Cup history?", ["Ronaldo Nazário", "Miroslav Klose", "Gerd Müller", "Just Fontaine"], 1, "Klose scored 16 World Cup goals for Germany."),
    ("pro", "Which club is nicknamed 'The Old Lady'?", ["Juventus", "Inter Milan", "AS Roma", "Napoli"], 0, "Juventus have been called La Vecchia Signora for decades."),
    ("pro", "Which team went unbeaten through the entire 2003-04 Premier League season?", ["Chelsea", "Manchester United", "Arsenal", "Liverpool"], 2, "Arsenal became known as 'The Invincibles'."),
    ("pro", "Which country shocked Europe by winning Euro 2004?", ["Portugal", "Greece", "Czech Republic", "Sweden"], 1, "Greece beat hosts Portugal 1-0 in the final."),
    ("pro", "Which goalkeeper is the only one to have won the Ballon d'Or?", ["Gianluigi Buffon", "Manuel Neuer", "Lev Yashin", "Iker Casillas"], 2, "Lev Yashin won it in 1963."),
    ("pro", "Who is the Premier League's all-time top scorer?", ["Wayne Rooney", "Harry Kane", "Thierry Henry", "Alan Shearer"], 3, "Alan Shearer scored 260 Premier League goals."),
    ("pro", "Which was the first African nation to reach a World Cup semi-final?", ["Senegal", "Ghana", "Morocco", "Cameroon"], 2, "Morocco reached the semi-finals in 2022."),
    ("pro", "Which club did Cristiano Ronaldo start his professional career with?", ["Benfica", "Porto", "Sporting CP", "Manchester United"], 2, "He broke through at Sporting before joining Manchester United in 2003."),
    ("legend", "Who scored a hat-trick in the 1966 World Cup final?", ["Bobby Charlton", "Geoff Hurst", "Gary Lineker", "Martin Peters"], 1, "Geoff Hurst is still the only player with a hat-trick in a men's World Cup final."),
    ("legend", "Against which team did Zidane score his famous volley in the 2002 Champions League final?", ["Juventus", "Bayern Munich", "Bayer Leverkusen", "Valencia"], 2, "Real Madrid beat Leverkusen 2-1 at Hampden Park."),
    ("legend", "Which club did Maradona lead to Serie A titles in 1987 and 1990?", ["Napoli", "Juventus", "AC Milan", "Sampdoria"], 0, "Napoli's first ever Serie A titles came with Maradona."),
    ("legend", "Which country won Euro 1992 after replacing Yugoslavia at short notice?", ["Sweden", "Denmark", "Germany", "Netherlands"], 1, "Denmark beat Germany 2-0 in the final."),
]

# (name, accepted answers, clues hardest -> easiest)
PLAYERS = [
    ("Lionel Messi", ["messi", "lionel messi", "leo messi"], [
        "I was born in Rosario, Argentina, and moved to a Spanish club's academy as a young teenager.",
        "I have won eight Ballon d'Or awards and famously wore number 10 at Barcelona.",
        "I finally lifted the World Cup with my country in 2022."]),
    ("Cristiano Ronaldo", ["ronaldo", "cristiano ronaldo", "cristiano", "cr7"], [
        "I was born on the island of Madeira in Portugal.",
        "I have played for Sporting, Manchester United, Real Madrid and Juventus.",
        "I am known for the number 7 and the 'Siuuu' celebration."]),
    ("Zinedine Zidane", ["zidane", "zinedine zidane", "zizou"], [
        "I was born in Marseille to Algerian parents.",
        "I played for Juventus and Real Madrid, and scored a famous volley in the 2002 Champions League final.",
        "I scored twice in the 1998 World Cup final, and was sent off in the 2006 final."]),
    ("Pelé", ["pele", "edson arantes do nascimento"], [
        "I turned professional as a teenager with Santos.",
        "I am the only player to have won three World Cups.",
        "My birth name is Edson Arantes do Nascimento."]),
    ("Diego Maradona", ["maradona", "diego maradona", "diego armando maradona"], [
        "I was born in Buenos Aires and starred for Boca Juniors.",
        "I led Napoli to their first Serie A titles.",
        "I scored both the 'Hand of God' goal and the 'Goal of the Century' in 1986."]),
]

# (key, emoji, title, text)
RULES = [
    ("basics", "📖", "Football Basics", "Two teams of 11 players try to score more goals than the other team.\n\nA match lasts 90 minutes: two halves of 45 minutes, plus extra minutes the referee adds for stoppages.\n\nOnly the goalkeeper can use their hands, and only inside their own penalty area. Everyone else plays with feet, legs, chest and head."),
    ("goal", "🥅", "What Counts as a Goal", "A goal counts when the whole ball crosses the whole goal line, between the posts and under the crossbar.\n\nIt does not count if there was a foul or an offside before the goal, or if the ball was put in with a hand or arm."),
    ("offside", "🚩", "Offside", "A player is offside if, when a teammate passes the ball, they are closer to the opponent's goal line than both the ball and the second-last defender (the goalkeeper usually counts as one).\n\nYou can't be offside in your own half, or directly from a goal kick, throw-in or corner kick.\n\nBeing in an offside position is only a foul if you get involved in the play."),
    ("freekick", "🦵", "Free Kick", "The referee gives a free kick when a player commits a foul, like pushing, tripping or holding.\n\nDirect free kick: you can shoot straight at the goal.\nIndirect free kick: the ball must touch another player before a goal can count.\n\nOpponents must stay at least 9.15 metres (10 yards) away."),
    ("penalty", "🎯", "Penalty Kick", "A penalty is given when a defender commits a foul inside their own penalty area.\n\nThe ball is placed on the penalty spot, 11 metres from the goal. Only the kicker and the goalkeeper are involved, and the goalkeeper must keep at least one foot on the goal line until the ball is kicked."),
    ("yellow", "🟨", "Yellow Card", "A yellow card is a warning for a player who commits a serious foul, wastes time, protests, or plays in an unsporting way.\n\nThe player can keep playing. A second yellow card in the same match becomes a red card."),
    ("red", "🟥", "Red Card", "A red card means the player is sent off and must leave the pitch.\n\nIt is shown for very serious fouls, violent behaviour, stopping a clear goal chance by fouling or handling the ball, or after a second yellow card.\n\nThe team keeps playing with one player fewer and cannot replace the player who was sent off."),
    ("var", "📺", "VAR", "VAR means Video Assistant Referee. A team of officials watches the game on video and helps the referee.\n\nIt can only be used for four things: goals, penalty decisions, direct red cards, and mistaken identity.\n\nThe referee on the pitch always makes the final decision."),
    ("corner", "🚩", "Corner Kick", "When the defending team is the last to touch the ball before it crosses their own goal line (not into the goal), the attacking team gets a corner kick.\n\nThe ball is placed in the corner arc on that side. You can score directly from a corner."),
    ("throwin", "🙌", "Throw-in", "When the ball fully crosses the sideline, the team that did not touch it last gets a throw-in.\n\nThe thrower must keep both feet on the ground and throw the ball with both hands from behind and over their head.\n\nYou can't score directly from a throw-in."),
    ("goalkick", "🥾", "Goal Kick", "When the attacking team is the last to touch the ball before it crosses the goal line (not into the goal), the defending team gets a goal kick.\n\nThe ball is kicked from inside the goal area, and it is in play as soon as it moves."),
    ("handball", "✋", "Handball", "It is a handball foul if a player deliberately touches the ball with their hand or arm, or if their arm makes their body unnaturally bigger and the ball hits it.\n\nScoring a goal with the hand or arm doesn't count, even by accident.\n\nInside the penalty area, a handball by a defender usually means a penalty."),
    ("advantage", "👆", "Advantage", "If a foul happens but the fouled team is still in a good position, the referee can let play continue instead of stopping the game.\n\nIf the advantage doesn't work out within a few seconds, the referee can go back and give the foul."),
    ("extratime", "⏱️", "Extra Time and Shootout", "In knockout games, if the score is level after 90 minutes, the match can go to extra time: two halves of 15 minutes.\n\nIf it is still level, there is a penalty shootout. Each team takes 5 penalties, and the team with more goals wins. If it is still tied, it continues one penalty each until one team scores and the other misses."),
    ("subs", "🔁", "Substitutions", "A coach can replace a player on the pitch with a player from the bench.\n\nMany competitions allow up to 5 substitutions per team, but the exact number depends on the competition rules.\n\nA player who has been substituted off can't come back on, and the team must tell the referee before the change."),
]
RULES_BY_KEY = {r[0]: r for r in RULES}
RULES_MENU_TEXT = "📋 <b>Football Rules</b>\n\nTap a rule to read it in simple words:"

# ------------------------------------------------------------------ state
POLLS = {}    # poll_id -> {"correct", "points", "chat_id", "private"}
GUESSES = {}  # user_id -> {"player": (...), "shown": int}


# ------------------------------------------------------------------ telegram api
def api(method, **params):
    """Call a Telegram Bot API method. Returns the result, or None on API errors."""
    req = urllib.request.Request(
        "https://api.telegram.org/bot%s/%s" % (TOKEN, method),
        data=json.dumps(params).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8")).get("result")
    except urllib.error.HTTPError as e:
        logging.error("Telegram error %s on %s: %s", e.code, method, e.read().decode("utf-8", "ignore"))
        return None


def btn(text, data):
    return {"text": text, "callback_data": data}


def markup(rows):
    return {"inline_keyboard": rows}


def send(chat_id, text, reply_markup=None, parse_mode=None):
    params = {"chat_id": chat_id, "text": text}
    if reply_markup:
        params["reply_markup"] = reply_markup
    if parse_mode:
        params["parse_mode"] = parse_mode
    return api("sendMessage", **params)


# ------------------------------------------------------------------ storage
def db():
    return sqlite3.connect(DB_PATH)


def init_db():
    folder = os.path.dirname(DB_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with db() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, name TEXT,
                points INTEGER DEFAULT 0, correct INTEGER DEFAULT 0,
                wrong INTEGER DEFAULT 0, streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0)"""
        )


def record_result(user_id, name, points, is_correct):
    """Save a result, return (total_points, current_streak)."""
    con = db()
    try:
        with con:
            con.execute("INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)", (user_id, name))
            if is_correct:
                con.execute(
                    """UPDATE users SET name=?, points=points+?, correct=correct+1,
                       streak=streak+1, best_streak=MAX(best_streak, streak+1)
                       WHERE user_id=?""",
                    (name, points, user_id),
                )
            else:
                con.execute(
                    "UPDATE users SET name=?, wrong=wrong+1, streak=0 WHERE user_id=?",
                    (name, user_id),
                )
            return con.execute("SELECT points, streak FROM users WHERE user_id=?", (user_id,)).fetchone()
    finally:
        con.close()


def full_name(user):
    return " ".join(p for p in (user.get("first_name"), user.get("last_name")) if p) or "Player"


def normalize(text):
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.split())


# ------------------------------------------------------------------ features
def cmd_start(msg, args):
    send(
        msg["chat"]["id"],
        "⚽ Welcome to Panenka, the football quiz bot!\n\n"
        "/quiz - random question (or /quiz rookie|pro|legend)\n"
        "/guess - guess the player from clues\n"
        "/rules - football rules in simple words\n"
        "/top - leaderboard\n"
        "/me - your stats\n"
        "/help - show this message",
    )


def rules_markup():
    buttons = [btn("%s %s" % (r[1], r[2]), "rule_" + r[0]) for r in RULES]
    return markup([buttons[i:i + 2] for i in range(0, len(buttons), 2)])


def cmd_rules(msg, args):
    send(msg["chat"]["id"], RULES_MENU_TEXT, rules_markup(), "HTML")


def send_quiz(chat_id, difficulty=None):
    pool = [q for q in QUESTIONS if not difficulty or q[0] == difficulty]
    diff, question, options, answer, explanation = random.choice(pool)
    options = list(options)
    correct_text = options[answer]
    random.shuffle(options)
    correct_id = options.index(correct_text)
    msg = api(
        "sendPoll",
        chat_id=chat_id,
        question=("[%s] %s" % (diff.title(), question))[:300],
        options=options,
        type="quiz",
        correct_option_id=correct_id,
        explanation=explanation[:200],
        is_anonymous=False,
    )
    if msg and msg.get("poll"):
        POLLS[msg["poll"]["id"]] = {
            "correct": correct_id,
            "points": POINTS[diff],
            "chat_id": chat_id,
            "private": msg["chat"].get("type") == "private",
        }


def cmd_quiz(msg, args):
    difficulty = args[0].lower() if args else None
    if difficulty and difficulty not in POINTS:
        send(msg["chat"]["id"], "Choose: rookie, pro or legend.")
        return
    send_quiz(msg["chat"]["id"], difficulty)


def clue_markup():
    return markup([[btn("💡 Next clue", "guess_clue"), btn("🏳️ Give up", "guess_giveup")]])


def start_guess(chat_id, user_id):
    player = random.choice(PLAYERS)
    GUESSES[user_id] = {"player": player, "shown": 1}
    send(
        chat_id,
        "🕵️ Who is this player? (3 pts for clue 1, 2 for clue 2, 1 for clue 3)\n\n"
        "Clue 1: %s\n\nType your guess!" % player[2][0],
        clue_markup(),
    )


def cmd_guess(msg, args):
    start_guess(msg["chat"]["id"], msg["from"]["id"])


def cmd_top(msg, args):
    con = db()
    try:
        rows = con.execute(
            "SELECT name, points, best_streak FROM users ORDER BY points DESC LIMIT 10"
        ).fetchall()
    finally:
        con.close()
    if not rows:
        send(msg["chat"]["id"], "No scores yet. Try /quiz!")
        return
    medals = ["🥇", "🥈", "🥉"]
    lines = [
        "%s %s - %s pts (best streak %s)" % (medals[i] if i < 3 else "%d." % (i + 1), n, p, b)
        for i, (n, p, b) in enumerate(rows)
    ]
    send(msg["chat"]["id"], "🏆 Leaderboard\n\n" + "\n".join(lines))


def cmd_me(msg, args):
    con = db()
    try:
        row = con.execute(
            "SELECT points, correct, wrong, streak, best_streak FROM users WHERE user_id=?",
            (msg["from"]["id"],),
        ).fetchone()
    finally:
        con.close()
    if not row:
        send(msg["chat"]["id"], "You have no stats yet. Try /quiz!")
        return
    pts, correct, wrong, streak, best = row
    send(
        msg["chat"]["id"],
        "📊 %s\nPoints: %s\nCorrect: %s | Wrong: %s\nStreak: %s | Best: %s"
        % (msg["from"].get("first_name", "You"), pts, correct, wrong, streak, best),
    )


COMMANDS = {
    "start": cmd_start, "help": cmd_start, "quiz": cmd_quiz, "guess": cmd_guess,
    "rules": cmd_rules, "top": cmd_top, "me": cmd_me,
}


# ------------------------------------------------------------------ update handlers
def on_message(msg):
    text = (msg.get("text") or "").strip()
    if not text or "from" not in msg:
        return
    if text.startswith("/"):
        parts = text.split()
        cmd = parts[0][1:].split("@")[0].lower()
        handler = COMMANDS.get(cmd)
        if handler:
            handler(msg, parts[1:])
        return
    # plain text: treat as a guess if the user has an active game
    user = msg["from"]
    game = GUESSES.get(user["id"])
    if not game:
        return
    name, answers, clues = game["player"]
    if normalize(text) in {normalize(a) for a in answers}:
        points = len(clues) - game["shown"] + 1
        total, streak = record_result(user["id"], full_name(user), points, True)
        del GUESSES[user["id"]]
        send(
            msg["chat"]["id"],
            "✅ Yes, it's %s! +%d pts | Total: %s | Streak: 🔥%s" % (name, points, total, streak),
            markup([[btn("Another player ➡️", "guess_next")]]),
        )
    else:
        send(msg["chat"]["id"], "❌ Not quite, try again or tap 💡 Next clue.")


def on_callback(cb):
    api("answerCallbackQuery", callback_query_id=cb["id"])
    data = cb.get("data", "")
    message = cb.get("message")
    if not message:
        return
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    user = cb["from"]

    if data == "rules_menu":
        api("editMessageText", chat_id=chat_id, message_id=message_id, text=RULES_MENU_TEXT,
            parse_mode="HTML", reply_markup=rules_markup())
    elif data.startswith("rule_"):
        rule = RULES_BY_KEY.get(data[5:])
        if rule:
            api("editMessageText", chat_id=chat_id, message_id=message_id,
                text="%s <b>%s</b>\n\n%s" % (rule[1], rule[2], html.escape(rule[3], quote=False)),
                parse_mode="HTML", reply_markup=markup([[btn("⬅️ Back to rules", "rules_menu")]]))
    elif data == "quiz_next":
        send_quiz(chat_id)
    elif data == "guess_next":
        start_guess(chat_id, user["id"])
    elif data in ("guess_clue", "guess_giveup"):
        game = GUESSES.get(user["id"])
        if not game:
            send(chat_id, "No active game. Use /guess to start one.")
            return
        name, answers, clues = game["player"]
        if data == "guess_giveup" or game["shown"] >= len(clues):
            del GUESSES[user["id"]]
            record_result(user["id"], full_name(user), 0, False)
            send(chat_id, "It was %s! Streak reset." % name,
                 markup([[btn("Another player ➡️", "guess_next")]]))
        else:
            game["shown"] += 1
            send(chat_id, "Clue %d: %s" % (game["shown"], clues[game["shown"] - 1]), clue_markup())


def on_poll_answer(pa):
    info = POLLS.get(pa.get("poll_id"))
    option_ids = pa.get("option_ids") or []
    if not info or not option_ids:
        return
    user = pa["user"]
    is_correct = option_ids[0] == info["correct"]
    total, streak = record_result(user["id"], full_name(user), info["points"], is_correct)
    if info["private"]:
        if is_correct:
            text = "✅ Correct! +%d pts | Total: %s | Streak: 🔥%s" % (info["points"], total, streak)
        else:
            text = "❌ Wrong. Streak reset. Total: %s" % total
        send(info["chat_id"], text, markup([[btn("Next question ➡️", "quiz_next")]]))


def dispatch(update):
    if "message" in update:
        on_message(update["message"])
    elif "callback_query" in update:
        on_callback(update["callback_query"])
    elif "poll_answer" in update:
        on_poll_answer(update["poll_answer"])


# ------------------------------------------------------------------ main loop
def main():
    logging.info("Panenka LITE starting (standard library only, no pip needed)")
    if not TOKEN:
        sys.exit("Set the BOT_TOKEN environment variable first.")
    init_db()
    api("deleteWebhook")
    me = api("getMe")
    if me:
        logging.info("Logged in as @%s", me.get("username"))
    else:
        logging.error("Could not log in. Check that BOT_TOKEN is correct.")
    logging.info("Panenka is running...")

    offset = None
    while True:
        params = {"timeout": 30, "allowed_updates": ["message", "callback_query", "poll_answer"]}
        if offset is not None:
            params["offset"] = offset
        try:
            updates = api("getUpdates", **params)
        except Exception as e:  # network problem: wait and retry
            logging.error("Network error: %s", e)
            time.sleep(5)
            continue
        if updates is None:  # API error (bad token, conflict...)
            time.sleep(5)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            try:
                dispatch(update)
            except Exception:
                logging.exception("Error while handling update")


if __name__ == "__main__":
    main()
