from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from collections import defaultdict
from random import shuffle

async_mode = None
app = Flask(__name__)
socketio = SocketIO(app, async_mode=async_mode)

players = defaultdict(lambda: '') # room id
buy_in = 2
rooms = defaultdict(lambda: [get_deck(),[],buy_in,defaultdict(lambda:[buy_in,[],0]),0,0,-1]) # deck, table cards, pot, players (current bet, hand, raised), player count, turn index, running

@app.route("/<int:room>", methods = ['POST','GET'])
def room(room):
    room = str(room)
    if rooms[room][4] < 10 and rooms[room][6] == -1:
        rooms[room][4]+=1
        return render_template('index.html')
    else: return render_template('roomfull.html')

@socketio.event
def join():
    room = request.headers['Referer'].split('/')[-1]
    rooms[room][3][request.sid]
    players[request.sid] = room
    
    join_room(room)
    emit('set_data', [draw_hand(room,request.sid), list(rooms[room][3].keys()).index(request.sid) + 1, rooms[room][2], rooms[room][2]])

@socketio.on('disconnect')
def leave():
    if request.sid in players.keys():
        room = players[request.sid]
        if room in rooms and request.sid in rooms[room][3]:
            ind = list(rooms[room][3].keys()).index(request.sid)

            emit('player_removed', ind + 1, to=room)

            rooms[room][0] = rooms[room][3][request.sid][1] + rooms[room][0]

            del rooms[room][3][request.sid]
            rooms[room][4] -= 1

            if rooms[room][4] and ind < rooms[room][5] % rooms[room][4]:
                rooms[room][5] -= 1
            
            print(rooms[room][4])

            if rooms[room][4] == 1:
                emit('declare_winner', 1, to = room)
        if rooms[room][4] <= 0:
            del rooms[room]

        leave_room(room)
        del players[request.sid]

def get_deck():
    cards = []
    for suit in "SDCH":
        for card in ['2','3','4','5','6','7','8','9','10','J','K','Q','A']:
            cards.append(suit+card)

    shuffle(cards)
    return cards

def draw_hand(room, player):
    hand = []
    for i in range(2):
        hand.append(rooms[room][0].pop())

    rooms[room][3][player][1] = hand
    return hand

@socketio.event
def do_turn(action):
    if request.sid not in players or players[request.sid] not in rooms or request.sid not in rooms[players[request.sid]][3] or len(rooms[players[request.sid]][3]) < 2: 
        return
    if rooms[players[request.sid]][6] == 0: 
        return

    room = players[request.sid]
    ind = rooms[room][5] % rooms[room][4]
    if request.sid == list(rooms[room][3].keys())[ind]:
        if action == "fold":
            emit('player_removed', ind + 1, to=room)

            rooms[room][4] -= 1
            del rooms[room][3][request.sid]
            if rooms[room][4] == 1:
                emit('declare_winner', [1, 'others folded'])
                rooms[room][6] = 0
                return

            if rooms[room][5] > 0:
                rooms[room][5] %= rooms[room][4]

            del rooms[room][3][request.sid]

        elif isinstance(action, int):
            rooms[room][6] = 1
            action = max(0,int(action))
        
            rooms[room][3][request.sid][2] = bool(action)+1
            rooms[room][2] += action

            new_pot = rooms[room][2]

            rooms[room][5] = (rooms[room][5] + 1) % rooms[room][4]
            rooms[room][3][request.sid][0] = new_pot

            emit('update_pot', new_pot, to=room)
            emit('update_bet', new_pot)

        print(rooms[room][5])
        next_key = list(rooms[room][3].keys())[rooms[room][5]]
        stats = [i[2] for i in rooms[room][3].values()]

        if ((stats.count(2) == 1 and rooms[room][3][next_key][2]==2) or stats.count(2) == 0) and 0 not in stats:
            trigger_stage_change(room)

        emit('set_turn', rooms[room][5] + 1, to = room)

def trigger_stage_change(room):
    for i in rooms[room][3].values():
        i[2] = 0
    if len(rooms[room][1])<5:
        draw_card(room)
        while len(rooms[room][1]) < 3: 
            draw_card(room)
        
        emit('set_deal', rooms[room][1], to=room)

    else:
        emit('show_hands',";".join([str(i[1]) for i in rooms[room][3].values()]), to=room)

        scores = [[i,score_hand(v[1]+rooms[room][1])] for i,v in enumerate(rooms[room][3].values())]

        for i in range(6):
            top = -1
            next = []
            for j,v in enumerate(scores):
                if v[1][i] > top:
                    top = v[1][i]
                    next = [v]
                elif v[1][i] == top:
                    next.append(v)
            scores = next
        
        emit('declare_winner',[[i[0]+1 for i in scores], ['high', 'pair', 'two pair', '3 of a kind', 'straight', 'flush', 'full house', '4 of a kind', 'straight flush', 'royal flush'][scores[0][1][0]]], to=room)
        emit('declare_scores', to = room)

def score_hand(cards):
    hand = []
    for i in cards:
        suit = i[0]
        i = i[1:]
        if i=="J": i = 11
        elif i=="Q": i = 12
        elif i == "K": i = 13
        elif i == "A": i = 14
        else: i = int(i)
        hand.append([suit, i])
    
    sorted_hand = sorted([i[1] for i in hand], reverse = True)
    dict_cards = defaultdict(lambda:0)
    for i in sorted_hand: dict_cards[i]+=1
    pairs = sorted([o for o,c in dict_cards.items() if c == 2])[:2]
    triple = max([o for o,c in dict_cards.items() if c == 3]+[0])
    numbers = dict_cards.keys()

    dict_suits = defaultdict(lambda:0)
    for i in hand: dict_suits[i[0]]+=1
    flush = []
    for i,v in dict_suits.items():
        if v >= 5:
            flush = sorted([j[1] for j in hand if j[0] == i], reverse = True)
            break
    
    straight = []
    straight_flush = []
    for i,v in enumerate(sorted_hand[:-1]):
        if v == sorted_hand[i+1]+1: 
            straight.append(i)
            if v in flush:
                straight_flush.append(i)
        elif v!=sorted_hand[i]: 
            straight = []
            straight_flush = []
    
    # royal flush
    if straight[:5] == [14,13,12,11,10] and flush:
        return [9, 0, 0, 0, 0, 0]
    # straight flush
    if len(straight_flush)==5: # doesn't work - this
        return [8] + straight_flush
    # 4 of a kind (with high card)
    for c,o in dict_cards.items():
        if o == 4:
            return [7, c, max([i for i in numbers if i!=c]), 0, 0, 0]
    # full house
    if triple and pairs:
        return [6, triple, max(pairs), 0, 0, 0]
    # flush
    if flush:
        return [5] + flush[:5]
    # straight
    if len(straight) == 5:
        return [4] + straight[:5]
    # three of a kind (+ 2 other tie breakers)
    if triple:
        return [3, triple] + [i for i in numbers if i != triple]
    # two pair (+ tie breaker)
    if len(pairs) == 2:
        return [2] + pairs + [max([i for i in sorted_hand if i not in pairs])] + [0,0]
    # one pair
    if len(pairs) == 1:
        return [1] + pairs + [i for i in sorted_hand if i not in pairs][:4]
    # high card
    return [0] + sorted_hand[:5]

def draw_card(room):
    rooms[room][1].append(rooms[room][0].pop())

    return rooms[room][1]

if __name__ == "__main__":
	socketio.run(app, debug=False, host="0.0.0.0")