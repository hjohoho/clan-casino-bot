import requests
import json
import random
import sqlite3
import time
import math
import hashlib
from datetime import datetime, timedelta

BOT_TOKEN = "8708846637:AAETwsr-2xu3g7fYlFfCPi8XfxbD3OhlSV0"
ADMIN_IDS = [1462367346, 8785617232]
THREAD_ID = 29601

GOLD_TO_POINTS = 10
MAX_BET_POINTS = 1000
MIN_WITHDRAW_POINTS = 200

conn = sqlite3.connect("clan_casino.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0, last_bonus TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS casino_reserve (id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)")
cursor.execute("CREATE TABLE IF NOT EXISTS user_stats (user_id INTEGER PRIMARY KEY, consecutive_wins INTEGER DEFAULT 0, total_bet INTEGER DEFAULT 0, total_win INTEGER DEFAULT 0)")
cursor.execute("INSERT OR IGNORE INTO casino_reserve (id, balance) VALUES (1, 0)")
conn.commit()

def get_balance(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    r = cursor.fetchone()
    if r:
        return r[0]
    cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    return 0

def update_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def get_reserve():
    cursor.execute("SELECT balance FROM casino_reserve WHERE id = 1")
    r = cursor.fetchone()
    return r[0] if r else 0

def gold_to_points(gold):
    return gold * GOLD_TO_POINTS

def points_to_gold(points):
    return points // GOLD_TO_POINTS

def can_claim_bonus(user_id):
    cursor.execute("SELECT last_bonus FROM users WHERE user_id = ?", (user_id,))
    r = cursor.fetchone()
    if not r or not r[0]:
        return True
    try:
        last = datetime.strptime(r[0], "%Y-%m-%d")
        return (datetime.now() - last).days >= 1
    except:
        return True

def set_bonus_claimed(user_id):
    cursor.execute("UPDATE users SET last_bonus = ? WHERE user_id = ?", (datetime.now().strftime("%Y-%m-%d"), user_id))
    conn.commit()

def send_message(chat_id, text, keyboard=None, thread_id=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if thread_id:
        data["message_thread_id"] = thread_id
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)
    try:
        requests.post(url, json=data, timeout=10)
    except:
        pass

def edit_message(chat_id, message_id, text, keyboard=None, thread_id=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    data = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    if thread_id:
        data["message_thread_id"] = thread_id
    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)
    try:
        requests.post(url, json=data, timeout=10)
    except:
        pass

def send_dice(chat_id, emoji, thread_id=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDice"
    data = {"chat_id": chat_id, "emoji": emoji}
    if thread_id:
        data["message_thread_id"] = thread_id
    try:
        r = requests.post(url, json=data, timeout=10)
        return r.json()
    except:
        return {}

def mention(user_id, username):
    return f'<a href="tg://user?id={user_id}">{username}</a>'

def get_top():
    cursor.execute("SELECT username, balance FROM users WHERE balance > 0 ORDER BY balance DESC LIMIT 10")
    return cursor.fetchall()

def get_user_stats(user_id):
    cursor.execute("SELECT consecutive_wins, total_bet, total_win FROM user_stats WHERE user_id = ?", (user_id,))
    r = cursor.fetchone()
    if r:
        return {"consecutive_wins": r[0], "total_bet": r[1], "total_win": r[2]}
    cursor.execute("INSERT INTO user_stats (user_id) VALUES (?)", (user_id,))
    conn.commit()
    return {"consecutive_wins": 0, "total_bet": 0, "total_win": 0}

def update_user_stats(user_id, bet, win, is_win):
    cursor.execute("UPDATE user_stats SET total_bet = total_bet + ?, total_win = total_win + ? WHERE user_id = ?", (bet, win, user_id))
    if is_win:
        cursor.execute("UPDATE user_stats SET consecutive_wins = consecutive_wins + 1 WHERE user_id = ?", (user_id,))
    else:
        cursor.execute("UPDATE user_stats SET consecutive_wins = 0 WHERE user_id = ?", (user_id,))
    conn.commit()

def play_slots(chat_id, user_id, bet_points):
    reel1 = random.randint(1, 9)
    reel2 = random.randint(1, 9)
    reel3 = random.randint(1, 9)
    symbols = {1: "🍒", 2: "🍋", 3: "🍊", 4: "🍇", 5: "💎", 6: "🔔", 7: "7️⃣", 8: "⭐", 9: "🎰"}
    display = f"{symbols.get(reel1, '?')} | {symbols.get(reel2, '?')} | {symbols.get(reel3, '?')}"
    if reel1 == 7 and reel2 == 7 and reel3 == 7:
        win_points = int(bet_points * 3)
        commission = int(win_points * 0.05)
        final_win_points = win_points - commission
        update_balance(user_id, final_win_points - bet_points)
        update_user_stats(user_id, bet_points, final_win_points, True)
        send_message(chat_id, f"🎰 <b>АВТОМАТ</b>\n{display}\n🎉 ДЖЕКПОТ! 777!\n✅ ВЫИГРЫШ: ×3\n+{final_win_points} очков", thread_id=THREAD_ID)
        return True
    if reel1 == reel2 == reel3:
        win_points = int(bet_points * 2)
        commission = int(win_points * 0.05)
        final_win_points = win_points - commission
        update_balance(user_id, final_win_points - bet_points)
        update_user_stats(user_id, bet_points, final_win_points, True)
        send_message(chat_id, f"🎰 <b>АВТОМАТ</b>\n{display}\n✅ ТРИ ОДИНАКОВЫХ!\n✅ ВЫИГРЫШ: ×2\n+{final_win_points} очков", thread_id=THREAD_ID)
        return True
    update_balance(user_id, -bet_points)
    update_user_stats(user_id, bet_points, 0, False)
    send_message(chat_id, f"🎰 <b>АВТОМАТ</b>\n{display}\n❌ ПРОИГРЫШ: {bet_points} очков", thread_id=THREAD_ID)
    return True

def play_basketball(chat_id, user_id, bet_points):
    r = send_dice(chat_id, "🏀", THREAD_ID)
    if not r.get("ok"):
        return False
    val = r["result"]["dice"]["value"]
    if val >= 4:
        win_points = int(bet_points * 2)
        commission = int(win_points * 0.05)
        final_win_points = win_points - commission
        update_balance(user_id, final_win_points - bet_points)
        update_user_stats(user_id, bet_points, final_win_points, True)
        send_message(chat_id, f"🏀 <b>БАСКЕТБОЛ</b>\nВыпало: {val}\n✅ ПОПАЛ!\n✅ ВЫИГРЫШ: +{final_win_points} очков", thread_id=THREAD_ID)
    else:
        update_balance(user_id, -bet_points)
        update_user_stats(user_id, bet_points, 0, False)
        send_message(chat_id, f"🏀 <b>БАСКЕТБОЛ</b>\nВыпало: {val}\n❌ МИМО!\n❌ ПРОИГРЫШ: {bet_points} очков", thread_id=THREAD_ID)
    return True

def play_football(chat_id, user_id, bet_points):
    r = send_dice(chat_id, "⚽", THREAD_ID)
    if not r.get("ok"):
        return False
    val = r["result"]["dice"]["value"]
    if val >= 4:
        win_points = int(bet_points * 2)
        commission = int(win_points * 0.05)
        final_win_points = win_points - commission
        update_balance(user_id, final_win_points - bet_points)
        update_user_stats(user_id, bet_points, final_win_points, True)
        send_message(chat_id, f"⚽ <b>ФУТБОЛ</b>\nВыпало: {val}\n✅ ГОЛ!\n✅ ВЫИГРЫШ: +{final_win_points} очков", thread_id=THREAD_ID)
    else:
        update_balance(user_id, -bet_points)
        update_user_stats(user_id, bet_points, 0, False)
        send_message(chat_id, f"⚽ <b>ФУТБОЛ</b>\nВыпало: {val}\n❌ МИМО!\n❌ ПРОИГРЫШ: {bet_points} очков", thread_id=THREAD_ID)
    return True

def play_cube(chat_id, user_id, bet_points, choice):
    r = send_dice(chat_id, "🎲", THREAD_ID)
    if not r.get("ok"):
        return False
    val = r["result"]["dice"]["value"]
    if choice == "even":
        win = val % 2 == 0
        multiplier = 1.5
    elif choice == "odd":
        win = val % 2 != 0
        multiplier = 1.5
    else:
        win = val == int(choice)
        multiplier = 5
    if win:
        win_points = int(bet_points * multiplier)
        commission = int(win_points * 0.05)
        final_win_points = win_points - commission
        update_balance(user_id, final_win_points - bet_points)
        update_user_stats(user_id, bet_points, final_win_points, True)
        send_message(chat_id, f"🎲 <b>КУБИК</b>\nВыпало: {val}\n✅ ВЫИГРЫШ: ×{multiplier}\n+{final_win_points} очков", thread_id=THREAD_ID)
    else:
        update_balance(user_id, -bet_points)
        update_user_stats(user_id, bet_points, 0, False)
        send_message(chat_id, f"🎲 <b>КУБИК</b>\nВыпало: {val}\n❌ ПРОИГРЫШ: {bet_points} очков", thread_id=THREAD_ID)
    return True

def roulette_menu():
    return {"inline_keyboard": [
        [{"text": "1️⃣-1️⃣2️⃣ (×2)", "callback_data": "roulette_1st12"}],
        [{"text": "1️⃣3️⃣-2️⃣4️⃣ (×2)", "callback_data": "roulette_2nd12"}],
        [{"text": "2️⃣5️⃣-3️⃣6️⃣ (×2)", "callback_data": "roulette_3rd12"}],
        [{"text": "⭕ ЧЁТ (×1.5)", "callback_data": "roulette_even"}],
        [{"text": "⭕ НЕЧЁТ (×1.5)", "callback_data": "roulette_odd"}],
        [{"text": "⭕ 1-18 (×1.5)", "callback_data": "roulette_low"}],
        [{"text": "⭕ 19-36 (×1.5)", "callback_data": "roulette_high"}],
        [{"text": "🔴 КРАСНОЕ (×1.5)", "callback_data": "roulette_red"}],
        [{"text": "⚫ ЧЕРНОЕ (×1.5)", "callback_data": "roulette_black"}]
    ]}

def roulette_spin():
    return random.randint(0, 36)

def roulette_check(number, bet_type):
    red = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
    black = [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]
    if bet_type == "red":
        return number in red
    elif bet_type == "black":
        return number in black
    elif bet_type == "even":
        return number != 0 and number % 2 == 0
    elif bet_type == "odd":
        return number != 0 and number % 2 != 0
    elif bet_type == "low":
        return 1 <= number <= 18
    elif bet_type == "high":
        return 19 <= number <= 36
    elif bet_type == "1st12":
        return 1 <= number <= 12
    elif bet_type == "2nd12":
        return 13 <= number <= 24
    elif bet_type == "3rd12":
        return 25 <= number <= 36
    return False

def roulette_payout(bet_type):
    if bet_type in ["1st12", "2nd12", "3rd12"]:
        return 2
    return 1.5

def play_roulette(chat_id, user_id, bet_points, bet_type):
    number = roulette_spin()
    win = roulette_check(number, bet_type)
    payout = roulette_payout(bet_type)
    red = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
    black = [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]
    if number == 0:
        display = "🟢 0"
    elif number in red:
        display = f"🔴 {number}"
    else:
        display = f"⚫ {number}"
    if win:
        win_points = int(bet_points * payout)
        commission = int(win_points * 0.05)
        final_win_points = win_points - commission
        update_balance(user_id, final_win_points - bet_points)
        update_user_stats(user_id, bet_points, final_win_points, True)
        text = f"🎰 <b>РУЛЕТКА</b>\n{display}\n✅ ВЫИГРЫШ: ×{payout}\n+{final_win_points} очков"
    else:
        update_balance(user_id, -bet_points)
        update_user_stats(user_id, bet_points, 0, False)
        text = f"🎰 <b>РУЛЕТКА</b>\n{display}\n❌ ПРОИГРЫШ: {bet_points} очков"
    send_message(chat_id, text, thread_id=THREAD_ID)
    send_message(chat_id, "Выберите следующую игру:", end_game_menu("roulette", bet_points), thread_id=THREAD_ID)
    return True

def get_ladder_multiplier(step, stones):
    if stones == 3:
        return round(1.0 + step * 0.15, 2)
    else:
        return round(1.0 + step * 0.35, 2)

def get_crash_chance(step, stones):
    if stones == 3:
        base, growth = 0.10, 0.07
    else:
        base, growth = 0.15, 0.09
    chance = base + (step - 1) * growth
    return min(chance, 0.95)

def ladder_stones_menu():
    return {"inline_keyboard": [
        [{"text": "🪨 3 камня (×1.15→×2.50)", "callback_data": "ladder_stones_3"}],
        [{"text": "🪨🪨 5 камней (×1.35→×4.50)", "callback_data": "ladder_stones_5"}]
    ]}

def ladder_menu(step, current_multiplier, stones, bet, username):
    next_step = step + 1
    next_multiplier = get_ladder_multiplier(next_step, stones)
    text = (
        f"🪜 <b>ЛЕСЕНКА</b>\n"
        f"👤 <b>{username}</b>\n"
        f"💰 Ставка: {bet} очков\n"
        f"📈 Множитель: <b>×{current_multiplier:.2f}</b>\n"
        f"💰 Выигрыш: {int(bet * current_multiplier)} очков\n\n"
        f"⬆️ Поднимайтесь или забирайте!"
    )
    keyboard = {"inline_keyboard": [
        [{"text": f"🪜 ПОДНЯТЬСЯ (×{next_multiplier:.2f})", "callback_data": "ladder_up"}],
        [{"text": f"💰 ЗАБРАТЬ (×{current_multiplier:.2f})", "callback_data": "ladder_cashout"}]
    ]}
    return text, keyboard

# ==================== МИНЕР ====================

def is_mine_hidden(user_id, step, total_cells, bombs_count, is_all_in=False):
    return random.random() < (bombs_count / total_cells)

MULTIPLIERS_3x3 = {
    3: {2: 1.2, 3: 1.4, 4: 1.7, 5: 2.0, 6: 2.3, 7: 2.7},
    5: {2: 1.6, 3: 2.0, 4: 2.6, 5: 3.2, 6: 4.0, 7: 5.0}
}

MULTIPLIERS_5x5 = {
    3: {2: 1.1, 3: 1.2, 4: 1.3, 5: 1.5, 6: 1.7, 7: 1.9, 8: 2.1, 9: 2.3, 10: 2.5,
        11: 2.7, 12: 2.9, 13: 3.1, 14: 3.3, 15: 3.5, 16: 3.7, 17: 3.9, 18: 4.1, 19: 4.3, 20: 4.5},
    5: {2: 1.2, 3: 1.4, 4: 1.6, 5: 1.8, 6: 2.0, 7: 2.2, 8: 2.4, 9: 2.6, 10: 2.8,
        11: 3.0, 12: 3.2, 13: 3.4, 14: 3.6, 15: 3.8, 16: 4.0, 17: 4.2, 18: 4.4, 19: 4.6, 20: 4.8},
    7: {2: 1.3, 3: 1.6, 4: 1.9, 5: 2.2, 6: 2.5, 7: 2.8, 8: 3.1, 9: 3.4, 10: 3.7,
        11: 4.0, 12: 4.3, 13: 4.6, 14: 4.9, 15: 5.2, 16: 5.5, 17: 5.8, 18: 6.1},
    10: {2: 1.5, 3: 2.0, 4: 2.5, 5: 3.0, 6: 3.5, 7: 4.0, 8: 4.5, 9: 5.0, 10: 5.5,
         11: 6.0, 12: 6.5, 13: 7.0, 14: 7.5}
}

def get_multiplier(size, bombs, steps):
    if steps < 2:
        return 1.0
    if size == "3x3":
        return MULTIPLIERS_3x3.get(bombs, {}).get(steps, 1.0)
    else:
        return MULTIPLIERS_5x5.get(bombs, {}).get(steps, 1.0)

def calculate_win(bet_points, size, bombs, steps):
    if steps < 2:
        return 0
    coef = get_multiplier(size, bombs, steps)
    return math.floor(bet_points * coef * 0.95)

def mines_size_menu():
    return {"inline_keyboard": [
        [{"text": "💣 Минер 3×3", "callback_data": "mines_3x3"}],
        [{"text": "💣 Минер 5×5", "callback_data": "mines_5x5"}]
    ]}

def mines_bombs_menu(size):
    if size == "3x3":
        return {"inline_keyboard": [
            [{"text": "💣 3 бомбы", "callback_data": f"mines_bombs_{size}_3"}],
            [{"text": "💣💣 5 бомб", "callback_data": f"mines_bombs_{size}_5"}]
        ]}
    else:
        return {"inline_keyboard": [
            [{"text": "💣 3 бомбы", "callback_data": f"mines_bombs_{size}_3"}],
            [{"text": "💣💣 5 бомб", "callback_data": f"mines_bombs_{size}_5"}],
            [{"text": "💣💣💣 7 бомб", "callback_data": f"mines_bombs_{size}_7"}],
            [{"text": "💣💣💣💣 10 бомб", "callback_data": f"mines_bombs_{size}_10"}]
        ]}

def mines_field_menu(opened, size, max_cells, bombs_positions=None, game_over=False):
    if max_cells is None or max_cells == 0:
        max_cells = 9
    cols = 3 if max_cells == 9 else 5
    keyboard = []
    cell_index = 0
    for row in range(cols):
        row_buttons = []
        for col in range(cols):
            if cell_index >= max_cells:
                break
            if game_over and cell_index in bombs_positions:
                row_buttons.append({"text": "💣", "callback_data": f"mine_cell_{cell_index}"})
            elif cell_index in opened:
                row_buttons.append({"text": "✅", "callback_data": f"mine_cell_{cell_index}"})
            else:
                row_buttons.append({"text": "⬜", "callback_data": f"mine_cell_{cell_index}"})
            cell_index += 1
        if row_buttons:
            keyboard.append(row_buttons)
    if not game_over:
        keyboard.append([{"text": "💰 ЗАБРАТЬ", "callback_data": "mine_cashout"}])
    return {"inline_keyboard": keyboard}

def game_choice_menu():
    return {"inline_keyboard": [
        [{"text": "🎰 Автомат", "callback_data": "game_slots"}],
        [{"text": "🏀 Баскетбол", "callback_data": "game_basketball"}],
        [{"text": "⚽ Футбол", "callback_data": "game_football"}],
        [{"text": "🎲 Кубик", "callback_data": "game_cube"}],
        [{"text": "🎰 Рулетка", "callback_data": "game_roulette"}],
        [{"text": "🪜 Лесенка", "callback_data": "game_ladder"}],
        [{"text": "💣 Минер", "callback_data": "game_mines"}],
        [{"text": "🎫 Лотерея", "callback_data": "lottery_menu"}],
        [{"text": "🎁 Бонус (10 очков/день)", "callback_data": "bonus"}],
        [{"text": "💰 Баланс", "callback_data": "balance"}],
        [{"text": "💳 Вывод", "callback_data": "withdraw"}]
    ]}

def cube_menu():
    return {"inline_keyboard": [
        [{"text": "🎲 ЧЁТНОЕ (×1.5)", "callback_data": "cube_even"}],
        [{"text": "🎲 НЕЧЁТНОЕ (×1.5)", "callback_data": "cube_odd"}],
        [{"text": "1️⃣ (×5)", "callback_data": "cube_1"}],
        [{"text": "2️⃣ (×5)", "callback_data": "cube_2"}],
        [{"text": "3️⃣ (×5)", "callback_data": "cube_3"}],
        [{"text": "4️⃣ (×5)", "callback_data": "cube_4"}],
        [{"text": "5️⃣ (×5)", "callback_data": "cube_5"}],
        [{"text": "6️⃣ (×5)", "callback_data": "cube_6"}]
    ]}

def end_game_menu(game, bet):
    return {"inline_keyboard": [
        [{"text": "🔄 СЫГРАТЬ ЕЩЁ", "callback_data": f"replay_{game}_{bet}"}],
        [{"text": "🏠 В МЕНЮ", "callback_data": "menu"}]
    ]}

# ==================== ЛОТЕРЕЯ ====================

lottery_data = {
    "active": False,
    "players": {},
    "max_players": 10,
    "lottery_id": 1
}

def lottery_menu():
    return {"inline_keyboard": [
        [{"text": f"🎫 Билет 5г (лотерея #{lottery_data['lottery_id']})", "callback_data": "lottery_5g"}],
        [{"text": f"🎫 Билет 10г (лотерея #{lottery_data['lottery_id']})", "callback_data": "lottery_10g"}],
        [{"text": "👥 Участники", "callback_data": "lottery_players"}],
        [{"text": "🏆 Розыгрыш (админ)", "callback_data": "lottery_draw"}],
        [{"text": "⏹ Остановить (админ)", "callback_data": "lottery_stop"}],
        [{"text": "🔙 Назад", "callback_data": "menu"}]
    ]}

def lottery_start(chat_id, user_id, ticket_price, lottery_id):
    global lottery_data
    
    if lottery_data["lottery_id"] != lottery_id:
        send_message(chat_id, f"❌ Лотерея #{lottery_id} уже завершена! Сейчас активна лотерея #{lottery_data['lottery_id']}", thread_id=THREAD_ID)
        return
    
    if len(lottery_data["players"]) >= lottery_data["max_players"]:
        send_message(chat_id, f"❌ Максимум {lottery_data['max_players']} игроков!", thread_id=THREAD_ID)
        return
    
    points_needed = ticket_price * GOLD_TO_POINTS
    balance = get_balance(user_id)
    if balance < points_needed:
        send_message(chat_id, f"❌ Недостаточно очков! Нужно: {points_needed}", thread_id=THREAD_ID)
        return
    
    if user_id in lottery_data["players"]:
        send_message(chat_id, f"❌ Ты уже купил билет в лотерею #{lottery_id}!", thread_id=THREAD_ID)
        return
    
    update_balance(user_id, -points_needed)
    
    username = cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
    lottery_data["players"][user_id] = {"username": username, "ticket": ticket_price}
    
    if not lottery_data["active"]:
        lottery_data["active"] = True
    
    send_message(chat_id, f"✅ {mention(user_id, username)} купил билет за {ticket_price} голды в лотерею #{lottery_id}!\n👥 Игроков: {len(lottery_data['players'])}/{lottery_data['max_players']}", thread_id=THREAD_ID)

def lottery_add_player(chat_id, admin_id, target_username, ticket_price):
    global lottery_data
    
    if admin_id not in ADMIN_IDS:
        send_message(chat_id, "⛔ Только админ!", thread_id=THREAD_ID)
        return
    
    if len(lottery_data["players"]) >= lottery_data["max_players"]:
        send_message(chat_id, f"❌ Максимум {lottery_data['max_players']} игроков!", thread_id=THREAD_ID)
        return
    
    cursor.execute("SELECT user_id, balance FROM users WHERE username LIKE ?", (f"%{target_username}%",))
    r = cursor.fetchone()
    if not r:
        send_message(chat_id, f"❌ Игрок {target_username} не найден!", thread_id=THREAD_ID)
        return
    
    user_id, balance = r
    points_needed = ticket_price * GOLD_TO_POINTS
    if balance < points_needed:
        send_message(chat_id, f"❌ У игрока {target_username} недостаточно очков!", thread_id=THREAD_ID)
        return
    
    if user_id in lottery_data["players"]:
        send_message(chat_id, f"❌ {target_username} уже в лотерее!", thread_id=THREAD_ID)
        return
    
    update_balance(user_id, -points_needed)
    username = cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,)).fetchone()[0]
    lottery_data["players"][user_id] = {"username": username, "ticket": ticket_price}
    
    if not lottery_data["active"]:
        lottery_data["active"] = True
    
    send_message(chat_id, f"✅ Админ добавил {mention(user_id, username)} в лотерею #{lottery_data['lottery_id']}!\n👥 Игроков: {len(lottery_data['players'])}/{lottery_data['max_players']}", thread_id=THREAD_ID)

def lottery_players(chat_id):
    global lottery_data
    
    if not lottery_data["active"]:
        send_message(chat_id, "❌ Лотерея не активна!", thread_id=THREAD_ID)
        return
    
    players = lottery_data["players"]
    if not players:
        send_message(chat_id, "👥 Пока нет участников!", thread_id=THREAD_ID)
        return
    
    text = f"👥 <b>УЧАСТНИКИ ЛОТЕРЕИ #{lottery_data['lottery_id']}</b>\n\n"
    for uid, data in players.items():
        text += f"• {data['username']} — {data['ticket']} голды\n"
    text += f"\nВсего: {len(players)}/{lottery_data['max_players']} игроков"
    send_message(chat_id, text, thread_id=THREAD_ID)

def lottery_draw(chat_id, admin_id):
    global lottery_data
    
    if admin_id not in ADMIN_IDS:
        send_message(chat_id, "⛔ Только админ!", thread_id=THREAD_ID)
        return
    
    if not lottery_data["active"]:
        send_message(chat_id, "❌ Лотерея не активна!", thread_id=THREAD_ID)
        return
    
    players = lottery_data["players"]
    if len(players) < 4:
        for uid, data in players.items():
            refund = data["ticket"] * GOLD_TO_POINTS
            update_balance(uid, refund)
        send_message(chat_id, f"❌ Недостаточно игроков ({len(players)}/4). Возврат очков.", thread_id=THREAD_ID)
        lottery_data = {"active": False, "players": {}, "max_players": 10, "lottery_id": lottery_data["lottery_id"] + 1}
        return
    
    winner_id = random.choice(list(players.keys()))
    winner_data = players[winner_id]
    
    total_tickets = sum(p["ticket"] for p in players.values())
    commission = total_tickets // len(players)
    prize = (total_tickets - commission) * GOLD_TO_POINTS
    
    update_balance(winner_id, prize)
    
    players_list = "\n".join(f"• {p['username']} — {p['ticket']} голды" for p in players.values())
    send_message(chat_id, f"🎉 <b>ЛОТЕРЕЯ #{lottery_data['lottery_id']} ЗАВЕРШЕНА!</b>\n\n👥 Участники:\n{players_list}\n\n🏆 <b>ПОБЕДИТЕЛЬ:</b> {mention(winner_id, winner_data['username'])}\n💰 Выигрыш: {prize} очков ({prize//GOLD_TO_POINTS} голды)\n💸 Комиссия казино: {commission} голды", thread_id=THREAD_ID)
    
    lottery_data = {"active": False, "players": {}, "max_players": 10, "lottery_id": lottery_data["lottery_id"] + 1}

def lottery_stop(chat_id, admin_id):
    global lottery_data    
    if admin_id not in ADMIN_IDS:
        send_message(chat_id, "⛔ Только админ!", thread_id=THREAD_ID)
        return
    
    if not lottery_data["active"]:
        send_message(chat_id, "❌ Лотерея не активна!", thread_id=THREAD_ID)
        return
    
    players = lottery_data["players"]
    if players:
        for uid, data in players.items():
            refund = data["ticket"] * GOLD_TO_POINTS
            update_balance(uid, refund)
        send_message(chat_id, f"⏹ <b>ЛОТЕРЕЯ #{lottery_data['lottery_id']} ОСТАНОВЛЕНА</b>\nВозврат очков всем участникам.", thread_id=THREAD_ID)
    else:
        send_message(chat_id, f"⏹ Лотерея #{lottery_data['lottery_id']} остановлена. Участников не было.", thread_id=THREAD_ID)
    
    lottery_data = {"active": False, "players": {}, "max_players": 10, "lottery_id": lottery_data["lottery_id"] + 1}

# ==================== СОСТОЯНИЯ ====================

last_bet = {}
last_game = {}
mines_state = {}
ladder_state = {}
withdraw_mode = {}
is_all_in = {}

def process_game(chat_id, user_id, game, amount_points, all_in=False):
    if game == "basketball":
        play_basketball(chat_id, user_id, amount_points)
        send_message(chat_id, "Выберите следующую игру:", end_game_menu(game, amount_points), thread_id=THREAD_ID)
        return
    elif game == "football":
        play_football(chat_id, user_id, amount_points)
        send_message(chat_id, "Выберите следующую игру:", end_game_menu(game, amount_points), thread_id=THREAD_ID)
        return
    elif game == "slots":
        play_slots(chat_id, user_id, amount_points)
        send_message(chat_id, "Выберите следующую игру:", end_game_menu(game, amount_points), thread_id=THREAD_ID)
        return
    elif game == "roulette":
        send_message(chat_id, f"🎰 <b>РУЛЕТКА</b>\nСтавка: {amount_points} очков\n\nВыберите ставку:", roulette_menu(), thread_id=THREAD_ID)
        return
    elif game == "ladder":
        ladder_state[user_id] = {"bet": amount_points, "step": 0, "multiplier": 1.0, "stones": 0}
        send_message(chat_id, f"🪜 <b>ЛЕСЕНКА</b>\nСтавка: {amount_points} очков\n\nВыберите количество камней:", ladder_stones_menu(), thread_id=THREAD_ID)
        return
    elif game == "mines":
        mines_state[user_id] = {
            "bet_points": amount_points,
            "size": "3x3",
            "bombs": 0,
            "opened": [],
            "steps": 0,
            "max_cells": 9,
            "bombs_positions": [],
            "all_in": all_in
        }
        send_message(chat_id, f"💣 <b>МИНЕР</b>\nСтавка: {amount_points} очков\n\nВыберите размер поля:", mines_size_menu(), thread_id=THREAD_ID)
        return
    elif game == "cube":
        send_message(chat_id, f"🎲 <b>КУБИК</b>\nСтавка: {amount_points} очков\n\nВыберите ставку:", cube_menu(), thread_id=THREAD_ID)
        return

def handle_message(update):
    if "message" not in update:
        return
    m = update["message"]
    chat_id = m["chat"]["id"]
    user_id = m["from"]["id"]
    username = m["from"].get("username") or m["from"].get("first_name", "Unknown")
    cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
    conn.commit()
    if "text" not in m:
        return
    text = m["text"].strip()

    if text == "/start":
        withdraw_mode[user_id] = False
        balance = get_balance(user_id)
        send_message(chat_id, f"Привет, {mention(user_id, username)}!\n💰 Баланс: {balance} очков\n📌 10 очков = 1 голда\n📌 Макс. ставка: 1000 очков\n📌 Вывод от 200 очков\n\nВыберите игру:", game_choice_menu(), thread_id=THREAD_ID)
        return

    if text == "/balance":
        balance = get_balance(user_id)
        send_message(chat_id, f"💰 {mention(user_id, username)}, ваш баланс: {balance} очков", thread_id=THREAD_ID)
        return

    if text == "/top":
        top = get_top()
        if not top:
            send_message(chat_id, "👥 Пока нет игроков с балансом > 0", thread_id=THREAD_ID)
            return
        msg = "👥 <b>ТОП ИГРОКОВ</b>\n"
        for i, (name, bal) in enumerate(top, 1):
            msg += f"{i}. {name} – {bal} очков\n"
        send_message(chat_id, msg, thread_id=THREAD_ID)
        return

    if text.startswith("/addgold"):
        if user_id not in ADMIN_IDS:
            send_message(chat_id, "⛔ Только админ!", thread_id=THREAD_ID)
            return
        try:
            p = text.split()
            target = p[1].replace("@", "")
            gold = int(p[2])
            points = gold_to_points(gold)
            cursor.execute("UPDATE users SET balance = balance + ? WHERE username LIKE ?", (points, f"%{target}%"))
            conn.commit()
            send_message(chat_id, f"✅ + {points} очков ({gold} голды) для {target}", thread_id=THREAD_ID)
        except:
            send_message(chat_id, "❌ /addgold @username 10", thread_id=THREAD_ID)
        return

    if text.startswith("/resetbalance"):
        if user_id not in ADMIN_IDS:
            send_message(chat_id, "⛔ Только админ!", thread_id=THREAD_ID)
            return
        try:
            p = text.split()
            if len(p) != 2:
                send_message(chat_id, "❌ /resetbalance @username", thread_id=THREAD_ID)
                return
            target = p[1].replace("@", "")
            cursor.execute("UPDATE users SET balance = 0 WHERE username LIKE ?", (f"%{target}%"))
            conn.commit()
            send_message(chat_id, f"✅ Баланс {target} сброшен до 0", thread_id=THREAD_ID)
        except:
            send_message(chat_id, "❌ /resetbalance @username", thread_id=THREAD_ID)
        return

    if text.startswith("/addtolottery"):
        if user_id not in ADMIN_IDS:
            send_message(chat_id, "⛔ Только админ!", thread_id=THREAD_ID)
            return
        try:
            parts = text.split()
            if len(parts) != 3:
                send_message(chat_id, "❌ /addtolottery @username 5", thread_id=THREAD_ID)
                return
            target = parts[1].replace("@", "")
            ticket_price = int(parts[2])
            if ticket_price not in [5, 10]:
                send_message(chat_id, "❌ Цена билета: 5 или 10 голды!", thread_id=THREAD_ID)
                return
            lottery_add_player(chat_id, user_id, target, ticket_price)
        except:
            send_message(chat_id, "❌ /addtolottery @username 5", thread_id=THREAD_ID)
        return

    if text.startswith("/stoplottery"):
        if user_id not in ADMIN_IDS:
            send_message(chat_id, "⛔ Только админ!", thread_id=THREAD_ID)
            return
        lottery_stop(chat_id, user_id)
        return

    if withdraw_mode.get(user_id, False):
        try:
            points = int(text)
            if points < MIN_WITHDRAW_POINTS:
                send_message(chat_id, f"❌ Минимальный вывод — {MIN_WITHDRAW_POINTS} очков!", thread_id=THREAD_ID)
                withdraw_mode[user_id] = False
                return
            bal = get_balance(user_id)
            if points > bal:
                send_message(chat_id, f"❌ У вас только {bal} очков!", thread_id=THREAD_ID)
                withdraw_mode[user_id] = False
                return
            gold = points_to_gold(points)
            username = m["from"].get("username") or m["from"].get("first_name", "Unknown")
            send_message(1462367346, f"💰 <b>ЗАЯВКА НА ВЫВОД</b>\n\n{mention(user_id, username)}\n💰 {points} очков ({gold} голды)\n📅 {time.strftime('%d.%m.%Y %H:%M')}")
            send_message(chat_id, f"✅ Заявка на {points} очков отправлена!\n\nВыберите игру:", game_choice_menu(), thread_id=THREAD_ID)
            withdraw_mode[user_id] = False
        except:
            send_message(chat_id, "❌ Введите число!", thread_id=THREAD_ID)
        return

    if text.lower() == "все":
        points = get_balance(user_id)
        if points <= 0:
            send_message(chat_id, "❌ У вас 0 очков!", thread_id=THREAD_ID)
            return
        if points > MAX_BET_POINTS:
            points = MAX_BET_POINTS
            send_message(chat_id, f"⚠️ Снижено до {MAX_BET_POINTS} очков", thread_id=THREAD_ID)
        last_bet[user_id] = points
        is_all_in[user_id] = True
        game = last_game.get(user_id, "slots")
        process_game(chat_id, user_id, game, points, True)
        return

    if text.isdigit():
        points = int(text)
        if points <= 0:
            send_message(chat_id, "❌ Ставка должна быть больше 0!", thread_id=THREAD_ID)
            return
        if points > MAX_BET_POINTS:
            send_message(chat_id, f"❌ Максимум {MAX_BET_POINTS} очков!", thread_id=THREAD_ID)
            return
        if get_balance(user_id) < points:
            send_message(chat_id, f"❌ У вас {get_balance(user_id)} очков!", thread_id=THREAD_ID)
            return
        last_bet[user_id] = points
        is_all_in[user_id] = False
        game = last_game.get(user_id, "slots")
        process_game(chat_id, user_id, game, points, False)
        return

def handle_callback(update):
    if "callback_query" not in update:
        return
    c = update["callback_query"]
    chat_id = c["message"]["chat"]["id"]
    user_id = c["from"]["id"]
    data = c["data"]

    if data == "balance":
        balance = get_balance(user_id)
        send_message(chat_id, f"💰 <b>ВАШ БАЛАНС</b>\n\n{balance} очков ({balance//GOLD_TO_POINTS} голды)", thread_id=THREAD_ID)
        return

    if data == "top":
        top = get_top()
        if not top:
            send_message(chat_id, "👥 Пока нет игроков с балансом > 0", thread_id=THREAD_ID)
            return
        msg = "👥 <b>ТОП ИГРОКОВ</b>\n"
        for i, (name, bal) in enumerate(top, 1):
            msg += f"{i}. {name} – {bal} очков\n"
        send_message(chat_id, msg, thread_id=THREAD_ID)
        return

    if data == "withdraw":
        withdraw_mode[user_id] = True
        send_message(chat_id, f"💳 <b>ВЫВОД ОЧКОВ</b>\nВведите сумму (мин. {MIN_WITHDRAW_POINTS} очков):", thread_id=THREAD_ID)
        return

    if data == "bonus":
        if not can_claim_bonus(user_id):
            cursor.execute("SELECT last_bonus FROM users WHERE user_id = ?", (user_id,))
            r = cursor.fetchone()
            last = r[0] if r else "никогда"
            send_message(chat_id, f"🎁 <b>БОНУС УЖЕ ПОЛУЧЕН!</b>\n\nТы уже получил бонус сегодня ({last}).\nВозвращайся завтра!", thread_id=THREAD_ID)
            return
        update_balance(user_id, 10)
        set_bonus_claimed(user_id)
        send_message(chat_id, "🎁 <b>БОНУС ПОЛУЧЕН!</b>\n\nТебе начислено 10 очков!\nВозвращайся завтра за новым бонусом!", thread_id=THREAD_ID)
        return

    if data == "game_slots":
        last_game[user_id] = "slots"
        send_message(chat_id, f"🎰 <b>АВТОМАТ</b>\nВведите ставку (макс. {MAX_BET_POINTS} очков):", thread_id=THREAD_ID)
        return

    if data == "game_basketball":
        last_game[user_id] = "basketball"
        send_message(chat_id, f"🏀 <b>БАСКЕТБОЛ</b>\nВведите ставку (макс. {MAX_BET_POINTS} очков):", thread_id=THREAD_ID)
        return

    if data == "game_football":
        last_game[user_id] = "football"
        send_message(chat_id, f"⚽ <b>ФУТБОЛ</b>\nВведите ставку (макс. {MAX_BET_POINTS} очков):", thread_id=THREAD_ID)
        return

    if data == "game_cube":
        last_game[user_id] = "cube"
        send_message(chat_id, f"🎲 <b>КУБИК</b>\nВведите ставку (макс. {MAX_BET_POINTS} очков):", thread_id=THREAD_ID)
        return

    if data == "game_roulette":
        last_game[user_id] = "roulette"
        send_message(chat_id, f"🎰 <b>РУЛЕТКА</b>\nВведите ставку (макс. {MAX_BET_POINTS} очков):", thread_id=THREAD_ID)
        return

    if data == "game_ladder":
        last_game[user_id] = "ladder"
        send_message(chat_id, f"🪜 <b>ЛЕСЕНКА</b>\nВведите ставку (макс. {MAX_BET_POINTS} очков):", thread_id=THREAD_ID)
        return

    if data == "game_mines":
        last_game[user_id] = "mines"
        send_message(chat_id, f"💣 <b>МИНЕР</b>\nВведите ставку (макс. {MAX_BET_POINTS} очков):", thread_id=THREAD_ID)
        return

    if data == "lottery_menu":
        send_message(chat_id, f"🎫 <b>ЛОТЕРЕЯ #{lottery_data['lottery_id']}</b>\n\nВыберите действие:", lottery_menu(), thread_id=THREAD_ID)
        return

    if data == "menu":
        send_message(chat_id, "🏠 Возвращаемся в меню", game_choice_menu(), thread_id=THREAD_ID)
        return

    if data.startswith("roulette_"):
        bet_type = data.replace("roulette_", "")
        points = last_bet.get(user_id, 0)
        if points == 0:
            send_message(chat_id, "❌ Сначала сделайте ставку!", thread_id=THREAD_ID)
            return
        play_roulette(chat_id, user_id, points, bet_type)
        send_message(chat_id, "Выберите следующую игру:", end_game_menu("roulette", points), thread_id=THREAD_ID)
        last_bet[user_id] = 0
        return

    if data.startswith("cube_"):
        choice = data.split("_")[1]
        points = last_bet.get(user_id, 0)
        if points == 0:
            send_message(chat_id, "❌ Сначала сделайте ставку!", thread_id=THREAD_ID)
            return
        play_cube(chat_id, user_id, points, choice)
        send_message(chat_id, "Выберите следующую игру:", end_game_menu("cube", points), thread_id=THREAD_ID)
        last_bet[user_id] = 0
        return

    if data == "ladder_stones_3":
        if user_id not in last_bet or last_bet.get(user_id, 0) == 0:
            send_message(chat_id, "❌ Сначала сделайте ставку!", thread_id=THREAD_ID)
            return
        if user_id not in ladder_state:
            send_message(chat_id, "❌ Ошибка! Начните игру заново.", thread_id=THREAD_ID)
            return
        stones = 3
        ladder_state[user_id]["stones"] = stones
        username = c["from"].get("username") or c["from"].get("first_name", "Unknown")
        bet = ladder_state[user_id]["bet"]
        text, keyboard = ladder_menu(0, 1.0, stones, bet, username)
        send_message(chat_id, text, keyboard, thread_id=THREAD_ID)
        return

    if data == "ladder_stones_5":
        if user_id not in last_bet or last_bet.get(user_id, 0) == 0:
            send_message(chat_id, "❌ Сначала сделайте ставку!", thread_id=THREAD_ID)
            return
        if user_id not in ladder_state:
            send_message(chat_id, "❌ Ошибка! Начните игру заново.", thread_id=THREAD_ID)
            return
        stones = 5
        ladder_state[user_id]["stones"] = stones
        username = c["from"].get("username") or c["from"].get("first_name", "Unknown")
        bet = ladder_state[user_id]["bet"]
        text, keyboard = ladder_menu(0, 1.0, stones, bet, username)
        send_message(chat_id, text, keyboard, thread_id=THREAD_ID)
        return

    if data == "ladder_up":
        if user_id not in ladder_state:
            send_message(chat_id, "❌ Игра не активна!", thread_id=THREAD_ID)
            return
        state = ladder_state[user_id]
        stones = state.get("stones", 3)
        next_step = state["step"] + 1
        crash_chance = get_crash_chance(next_step, stones)
        if random.random() < crash_chance:
            update_balance(user_id, -state["bet"])
            update_user_stats(user_id, state["bet"], 0, False)
            send_message(chat_id, f"💀 <b>КАМЕНЬ УПАЛ!</b>\n❌ ПРОИГРЫШ: {state['bet']} очков\n\nВыберите следующую игру:", game_choice_menu(), thread_id=THREAD_ID)
            del ladder_state[user_id]
            return
        state["step"] = next_step
        state["multiplier"] = get_ladder_multiplier(next_step, stones)
        username = c["from"].get("username") or c["from"].get("first_name", "Unknown")
        text, keyboard = ladder_menu(next_step, state["multiplier"], stones, state["bet"], username)
        send_message(chat_id, text, keyboard, thread_id=THREAD_ID)
        return

    if data == "ladder_cashout":
        if user_id not in ladder_state:
            send_message(chat_id, "❌ Игра не активна!", thread_id=THREAD_ID)
            return
        state = ladder_state[user_id]
        if state["step"] == 0:
            send_message(chat_id, "❌ Сделайте хотя бы 1 шаг!", thread_id=THREAD_ID)
            return
        win = int(state["bet"] * state["multiplier"])
        commission = int(win * 0.05)
        final_win = win - commission
        update_balance(user_id, final_win - state["bet"])
        update_user_stats(user_id, state["bet"], final_win, True)
        send_message(chat_id, f"💰 <b>ВЫ ЗАБРАЛИ ВЫИГРЫШ!</b>\nМножитель: ×{state['multiplier']:.2f}\n+{final_win} очков\n\nВыберите следующую игру:", end_game_menu("ladder", state["bet"]), thread_id=THREAD_ID)
        del ladder_state[user_id]
        return

    # ==================== МИНЕР ====================

    if data == "mines_3x3":
        if user_id not in mines_state:
            send_message(chat_id, "❌ Сначала сделайте ставку!", thread_id=THREAD_ID)
            return
        mines_state[user_id]["size"] = "3x3"
        mines_state[user_id]["max_cells"] = 9
        send_message(chat_id, f"💣 <b>МИНЕР 3x3</b>\nСтавка: {mines_state[user_id]['bet_points']} очков\n\nВыберите количество бомб:", mines_bombs_menu("3x3"), thread_id=THREAD_ID)
        return

    if data == "mines_5x5":
        if user_id not in mines_state:
            send_message(chat_id, "❌ Сначала сделайте ставку!", thread_id=THREAD_ID)
            return
        mines_state[user_id]["size"] = "5x5"
        mines_state[user_id]["max_cells"] = 25
        send_message(chat_id, f"💣 <b>МИНЕР 5x5</b>\nСтавка: {mines_state[user_id]['bet_points']} очков\n\nВыберите количество бомб:", mines_bombs_menu("5x5"), thread_id=THREAD_ID)
        return

    if data.startswith("mines_bombs_"):
        parts = data.split("_")
        size = parts[2]
        bombs = int(parts[3])
        if user_id not in mines_state:
            send_message(chat_id, "❌ Сначала сделайте ставку!", thread_id=THREAD_ID)
            return
        max_cells = 9 if size == "3x3" else 25
        bombs = min(bombs, max_cells - 1)
        state = mines_state[user_id]
        state["bombs"] = bombs
        state["opened"] = []
        state["steps"] = 0
        state["max_cells"] = max_cells
        state["bombs_positions"] = random.sample(range(max_cells), bombs)
        send_message(chat_id, f"💣 <b>МИНЕР {size}</b>\nБомб: {bombs}\nСтавка: {state['bet_points']} очков\n\n⬜ — не открыто", mines_field_menu([], size, max_cells), thread_id=THREAD_ID)
        return

    if data.startswith("mine_cell_"):
        cell = int(data.split("_")[2])
        if user_id not in mines_state:
            send_message(chat_id, "❌ Игра не активна!", thread_id=THREAD_ID)
            return
        state = mines_state[user_id]
        if cell in state["opened"]:
            send_message(chat_id, "❌ Уже открыто!", thread_id=THREAD_ID)
            return
        
        if is_mine_hidden(user_id, state["steps"], state["max_cells"], state["bombs"], state.get("all_in", False)):
            state["opened"].append(cell)
            state["steps"] += 1
            
            multiplier = get_multiplier(state["size"], state["bombs"], state["steps"])
            win_points = calculate_win(state["bet_points"], state["size"], state["bombs"], state["steps"])
            
            if state["steps"] == 1:
                send_message(chat_id, f"✅ <b>Клетка {cell+1} пустая!</b>\nШаг 1 (×1.0)\n\nПродолжайте!", mines_field_menu(state["opened"], state["size"], state["max_cells"]), thread_id=THREAD_ID)
            else:
                send_message(chat_id, f"✅ <b>Клетка {cell+1} пустая!</b>\nШаг {state['steps']}\nМножитель: ×{multiplier:.2f}\nПотенциальный выигрыш: {win_points} очков", mines_field_menu(state["opened"], state["size"], state["max_cells"]), thread_id=THREAD_ID)
            return
        else:
            update_balance(user_id, -state["bet_points"])
            update_user_stats(user_id, state["bet_points"], 0, False)
            text_msg = f"💥 <b>БАХ! МИНА!</b>\n❌ ПРОИГРЫШ: {state['bet_points']} очков"
            edit_message(chat_id, c["message"]["message_id"], text_msg, mines_field_menu(state["opened"], state["size"], state["max_cells"], state["bombs_positions"], True), thread_id=THREAD_ID)
            send_message(chat_id, text_msg, game_choice_menu(), thread_id=THREAD_ID)
            del mines_state[user_id]
            return

    if data == "mine_cashout":
        if user_id not in mines_state:
            send_message(chat_id, "❌ Игра не активна!", thread_id=THREAD_ID)
            return
        state = mines_state[user_id]
        if state["steps"] < 2:
            send_message(chat_id, "❌ Откройте 2 клетки!", thread_id=THREAD_ID)
            return
        
        win_points = calculate_win(state["bet_points"], state["size"], state["bombs"], state["steps"])
        commission = int(win_points * 0.05)
        final_win = win_points - commission
        update_balance(user_id, final_win - state["bet_points"])
        update_user_stats(user_id, state["bet_points"], final_win, True)
        send_message(chat_id, f"💰 <b>ВЫ ЗАБРАЛИ ВЫИГРЫШ!</b>\n✅ +{final_win} очков\n\nВыберите следующую игру:", end_game_menu("mines", state["bet_points"]), thread_id=THREAD_ID)
        del mines_state[user_id]
        return

    # ==================== ЛОТЕРЕЯ ====================

    if data == "lottery_5g":
        lottery_start(chat_id, user_id, 5, lottery_data["lottery_id"])
        return

    if data == "lottery_10g":
        lottery_start(chat_id, user_id, 10, lottery_data["lottery_id"])
        return

    if data == "lottery_players":
        lottery_players(chat_id)
        return

    if data == "lottery_draw":
        lottery_draw(chat_id, user_id)
        return

    if data == "lottery_stop":
        lottery_stop(chat_id, user_id)
        return

    # ==================== ПОВТОР ИГРЫ ====================

    if data.startswith("replay_"):
        parts = data.split("_")
        if len(parts) < 3:
            send_message(chat_id, "❌ Ошибка повтора!", thread_id=THREAD_ID)
            return
        game = parts[1]
        try:
            bet = int(parts[2])
        except:
            bet = last_bet.get(user_id, 0)
            if bet <= 0:
                send_message(chat_id, "❌ Неверная ставка для повтора!", thread_id=THREAD_ID)
                return
        if get_balance(user_id) < bet:
            send_message(chat_id, f"❌ У вас {get_balance(user_id)} очков, а нужно {bet}!", thread_id=THREAD_ID)
            return
        last_bet[user_id] = bet
        process_game(chat_id, user_id, game, bet, False)
        return

    if data == "menu":
        send_message(chat_id, "🏠 Возвращаемся в меню", game_choice_menu(), thread_id=THREAD_ID)
        return

def main():
    print("🎰 КАЗИНО БОТ ЗАПУЩЕН!")
    offset = 0
    while True:
        try:
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates", params={"offset": offset, "timeout": 30})
            data = r.json()
            updates = data.get("result", [])
            for u in updates:
                if "message" in u:
                    handle_message(u)
                if "callback_query" in u:
                    handle_callback(u)
                offset = u["update_id"] + 1
        except Exception as e:
            print("Ошибка:", e)
            time.sleep(5)

if __name__ == "__main__":
    main()
