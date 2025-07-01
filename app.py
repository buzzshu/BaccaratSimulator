import random
from collections import Counter
from flask import Flask, render_template, request, jsonify
import sys, os

base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
app = Flask(__name__, template_folder=os.path.join(base_path, 'templates'))

# --- 百家樂邏輯 ---
def card_value(card):
    return min(card, 10) % 10

def total(cards):
    return sum(card_value(c) for c in cards) % 10

def banker_draws(banker, player_third):
    b_total = total(banker)
    if not player_third:
        return b_total <= 5
    pt = card_value(player_third[0])
    if b_total <= 2: return True
    if b_total == 3: return pt != 8
    if b_total == 4: return 2 <= pt <= 7
    if b_total == 5: return 4 <= pt <= 7
    if b_total == 6: return 6 <= pt <= 7
    return False

def create_shoe(num_decks=8):
    shoe = [i for i in range(1, 14)] * 4 * num_decks
    random.shuffle(shoe)
    burn = card_value(shoe[0])
    shoe = shoe[1 + burn:]
    return shoe

def play_game_from_shoe(shoe):
    while True:
        if len(shoe) < 6:
            shoe[:] = create_shoe()
            continue

        try:
            player = [shoe.pop(), shoe.pop()]
            banker = [shoe.pop(), shoe.pop()]
        except IndexError:
            shoe[:] = create_shoe()
            continue

        player_third, banker_third = [], []

        if total(player) <= 5:
            if len(shoe) == 0:
                shoe[:] = create_shoe()
            try:
                card = shoe.pop()
                if card is not None:
                    player_third = [card]
                    player.append(card)
            except IndexError:
                continue

        if banker_draws(banker, player_third):
            if len(shoe) == 0:
                shoe[:] = create_shoe()
            try:
                card = shoe.pop()
                if card is not None:
                    banker_third = [card]
                    banker.append(card)
            except IndexError:
                continue

        # 確保沒有 None 值進入 total()
        if any(c is None for c in player + banker):
            continue

        p_total = total(player)
        b_total = total(banker)

        if p_total > b_total:
            return "Player"
        elif b_total > p_total:
            return "Banker"
        else:
            return "Tie"


def simulate_strategy(rounds=10000, base_bet=10, strategy="fixed", initial_funds=10000,
                      bet_target="Player", rebate_rate=0.0):
    shoe = create_shoe()
    balance = initial_funds
    bet = base_bet
    stats = Counter()
    last_result = "Player"
    total_bet = 0
    total_payout = 0
    total_rebate = 0

    for _ in range(rounds):
        if balance < bet:
            break

        result = play_game_from_shoe(shoe)
        stats[result] += 1
        current_bet = last_result if bet_target == "Follow" and last_result != "Tie" else bet_target
        payout = 0
        win = False
        total_bet += bet

        if result == current_bet:
            payout = bet * 1.95 if current_bet == "Banker" else bet * 2
            win = True
        elif result == "Tie":
            payout = bet
            win = True
        else:
            payout = 0
            win = False

        rebate = bet * rebate_rate
        total_rebate += rebate
        total_payout += payout
        balance = balance - bet + payout + rebate
        last_result = result
        bet = base_bet if strategy == "fixed" or win else min(balance, bet * 2)
        if balance <= 0:
            break

    return total_bet, total_payout, total_rebate

def batch_simulate(batch_size=100, rounds_per_sim=10000, base_bet=10,
                   strategy="fixed", initial_funds=10000, bet_target="Player", rebate_rate=0.0):
    rtp_list = []
    for _ in range(batch_size):
        tb, tp, tr = simulate_strategy(
            rounds=rounds_per_sim,
            base_bet=base_bet,
            strategy=strategy,
            initial_funds=initial_funds,
            bet_target=bet_target,
            rebate_rate=rebate_rate
        )
        rtp = (tp + tr) / tb if tb > 0 else 0
        rtp_list.append(rtp)

    over_100_count = sum(1 for r in rtp_list if r > 1.0)
    avg_rtp = sum(rtp_list) / len(rtp_list)
    min_rtp = min(rtp_list)
    max_rtp = max(rtp_list)

    return {
        "over_100_ratio": over_100_count / batch_size,
        "avg_rtp": avg_rtp,
        "min_rtp": min_rtp,
        "max_rtp": max_rtp,
        "rtp_list": rtp_list
    }

# --- Flask 路由 ---
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/simulate', methods=['POST'])
def simulate():
    data = request.json
    result = batch_simulate(
        batch_size=int(data.get("batch_size", 100)),
        rounds_per_sim=int(data.get("rounds_per_sim", 10000)),
        base_bet=int(data.get("base_bet", 10)),
        strategy=data.get("strategy", "fixed"),
        initial_funds=int(data.get("initial_funds", 10000)),
        bet_target=data.get("bet_target", "Player"),
        rebate_rate=float(data.get("rebate_rate", 0.0))
    )
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=8504)  # 或改為 0.0.0.0 對外開放
