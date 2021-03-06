from enum import Enum
import sys
import math
from collections import namedtuple, defaultdict
import random

random.seed(5)

# Auto-generated code below aims at helping you parse
# the standard input according to the problem statement.

CONTROL_RANGE = 2200
SHIELD_RANGE = 2200
WIND_RANGE = 1280
BASE_RADIUS = 5000
# base_x: The corner of the map representing your base
base_x, base_y = [int(i) for i in input().split()]
other_x, other_y = [17630-base_x, 9000-base_y]
heroes_per_player = int(input())  # Always 3
flip = 1 if base_x == 0 else -1
base_corners = [
    (base_x + 4600 * flip, base_y),
    (base_x, base_y+4600*flip),
    (base_x, base_y)
]
opp_base_corners = [
    (other_x - 4600*flip, other_y),
    (other_x, other_y - 4600*flip),
    (other_x, other_y)
]
home = [
    (base_x + 5500*flip, base_y+1400*flip),
    (base_x+1200*flip, base_y+5500*flip),
    (base_x + 8000 * flip, base_y + 6000*flip)
]
foxhole_1_mid = (other_x - 3500 * flip, other_y - 3500 * flip)
foxhole_1_left = (other_x - 5000 * flip, other_y - 1000 * flip)
foxhole_1_right = (other_x - 1000 * flip, other_y - 5000 * flip)
foxhole_2 = (other_x - 1400 * flip, other_y - 1400 * flip)

def distance_from_position(entity, position):
    return math.dist((entity.x, entity.y), position)

def distance_from_base(entity):
    return math.sqrt(pow(entity.x-base_x, 2) + pow(entity.y-base_y,2))

def distance_from_opp_base(entity):
    return math.dist((entity.x, entity.y), (other_x, other_y))

def distance_fn(entity1, entity2):
    return math.dist((entity1.x, entity1.y), (entity2.x, entity2.y))

def project_position(monster, distance):
    assert monster.type == 0
    vx, vy = monster.vx, monster.vy
    mag = math.sqrt(vx*vx + vy*vy)
    vx/=mag
    vy/=mag
    return int(monster.x+vx*distance), int(monster.y+vy*distance)

def target_towards(cur_position, target_position, max_distance):
    cx, cy = cur_position
    tx, ty = target_position
    dx, dy = tx-cx, ty-cy
    mag = math.sqrt(dx*dx + dy*dy)
    if mag < max_distance:
        return target_position
    dx/=mag
    dy/=mag
    return int(cx+dx*max_distance), int(cy+dy*max_distance)

Entity = namedtuple('Entity', ['id', 'type', 'x', 'y', 'shield_life', 'is_controlled', 'health',
'vx', 'vy', 'near_base', 'threat_for'])
Action = namedtuple('Action', ['type', 'target_id', 'x', 'y'], defaults=[None, None, None])

class ActionType(Enum):
    WIND_TO_OPP = 0
    MOVE = 1
    CONTROL_TO_OPP = 2
    WAIT = 3
    SHIELD = 4
    CONTROL_AWAY = 5
    WIND = 6
    WIND_MONSTER_INTO_BASE = 7

class State:
    def __init__(self):
        self.timestep = 0
        self.foxhole = foxhole_1_mid
        self.should_shield_base = False
        self.opp_turtling = False
        self.which_opp_corner = 0
        self.opponent_danger = 0
        self.opponent_in_my_base = 0
    def toggle_which_opponent_corner(self):
        self.which_opp_corner += 1
        self.which_opp_corner %= 3
    def set_foxhole(self):
        if self.opponent_danger > 50:
            self.foxhole = foxhole_2
        else:
            period = (self.timestep//10)%3
            self.foxhole = [foxhole_1_mid, foxhole_1_right, foxhole_1_left][period]
    def get_safe_distance(self):
        if self.opponent_in_my_base>0:
            return 6000
        else:
            return 10000

base_love = [1,0,0]
defend_love = [2, 0.8, 0.3]
home_love = [1, 1, 1]
farm_love = [0.2, 0.3, 1]
extroversion = [0, 0.1, 1]
wind_love = [0.6, 0.3, 0.1]

state = State()
# game loop
while True:
    state.timestep += 1
    state.opponent_danger *= 0.8
    state.set_foxhole()
    state.opponent_in_my_base -= 1
    # health: Your base health
    # mana: Ignore in the first league; Spend ten mana to cast a spell
    health, mana = [int(j) for j in input().split()]
    opp_health, opp_mana = [int(j) for j in input().split()]

    my_heroes = []
    opp_heroes = []
    entity_count = int(input())  # Amount of heros and monsters you can see
    monsters = []
    actions_for_entity = defaultdict(list)
    entities_by_id = dict()
    for i in range(entity_count):
        # id: Unique identifier
        # type: 0=monster, 1=your hero, 2=opponent hero
        # x: Position of this entity
        # shield_life: Ignore for this league; Count down until shield spell fades
        # is_controlled: Ignore for this league; Equals 1 when this entity is under a control spell
        # health: Remaining health of this monster
        # vx: Trajectory of this monster
        # near_base: 0=monster with no target yet, 1=monster targeting a base
        # threat_for: Given this monster's trajectory, is it a threat to 1=your base, 2=your opponent's base, 0=neither
        # _id, _type, x, y, shield_life, is_controlled, health, vx, vy, near_base, threat_for = 
        entity = Entity(*[int(j) for j in input().split()])
        entities_by_id[entity.id] = entity
        if entity.type == 1:
            my_heroes.append(entity)
        if entity.type == 0:
            monsters.append(entity)
            if entity.near_base==1:
                if entity.threat_for==2:
                    state.opponent_danger += entity.health * (2 if entity.shield_life!=0 else 1)
        if entity.type == 2:
            opp_heroes.append(entity)
            if distance_from_base(entity) < 5500:
                state.opponent_in_my_base = 5
    for i, hero in enumerate(my_heroes):
        if hero.is_controlled and distance_from_base(hero) < 5000:
            state.should_shield_base = True
        action_scores = defaultdict(float)
        action_scores[Action(ActionType.WAIT)] = 1
        for opp_hero in opp_heroes:
            # make opponent go away
            # if distance_from_base(opp_hero) < 7000 and distance_fn(opp_hero, hero) < WIND_RANGE and opp_hero.shield_life == 0 and mana > 80:
            #     action_scores[Action(ActionType.WIND_TO_OPP)] += 50
            # shield self
            if state.should_shield_base and distance_from_base(hero) < 5500 and distance_fn(opp_hero, hero) < CONTROL_RANGE and mana > 10 and hero.shield_life == 0:
                action_scores[Action(ActionType.SHIELD, target_id=hero.id)] = 200
            # disrupt enemies with Wind
            if distance_fn(opp_hero, hero) < WIND_RANGE and opp_hero.shield_life == 0 and mana > 10:
                for monster in monsters:
                    if monster.shield_life>0 and distance_from_opp_base(monster) < 5000 and distance_fn(monster, opp_hero) < WIND_RANGE:
                        close_bonus = 10 if distance_from_opp_base(monster) < 2500 else 0
                        action_scores[Action(ActionType.WIND, target_id=opp_hero.id, x=base_x, y=base_y)] += 70 + close_bonus
            # disrupt enemy defenses wih Control
            if distance_fn(opp_hero, hero) < CONTROL_RANGE and opp_hero.shield_life == 0 and opp_hero.is_controlled==0 and mana > 10:
                attack_bonus = 10 if state.opponent_danger>90 else -50
                time_bonus = -50 if state.timestep < 90 else 0
                mana_bonus = min(mana-29, 49)
                x = opp_hero.x - (other_x - opp_hero.x)
                y = opp_hero.y - (other_y - opp_hero.y)
                bonus = 5 if distance_from_opp_base(opp_hero) < 5000 else -40
                action_scores[Action(ActionType.CONTROL_AWAY, target_id=opp_hero.id, x=x, y=y)] += bonus + (random.random()-0.8) * 50 + attack_bonus + mana_bonus
        # print(mana, file=sys.stderr, flush=True)
        for monster in monsters:
            # last-ditch defense of our base
            if distance_from_base(monster) < 1500 and distance_fn(monster, hero) < 1280 and monster.shield_life == 0 and mana >= 10:
                # print(f"SPELL WIND {other_x} {other_y} BEGONE")
                action_scores[Action(ActionType.WIND_TO_OPP)] += 600
            # preventative winding if opponent is attacking
            if distance_from_base(monster) < BASE_RADIUS and distance_fn(monster, hero) < WIND_RANGE and monster.shield_life==0 and mana >= 10 and state.opponent_in_my_base>0:
                action_scores[Action(ActionType.WIND_TO_OPP)] += 100
            # push out of base to get more wild mana
            if distance_fn(monster, hero) < WIND_RANGE and 2000 < distance_from_base(monster) < BASE_RADIUS and monster.shield_life == 0 and mana >= 10:
                action_scores[Action(ActionType.WIND_TO_OPP, target_id=monster)] += wind_love[i] * 40 + min(mana, 25)
            d = distance_from_base(monster)
            normalized_base_distance = 1 - math.sqrt(min(d, 10000)/10000)
            normalized_hero_distance = math.sqrt(min(distance_fn(hero, monster), 10000)/10000)
            x,y = target_towards((hero.x, hero.y), project_position(monster, 400), 799)
            # Kill monster if it's a threat
            if monster.threat_for==1:
                value = 150 * normalized_base_distance * defend_love[i] - 25 * normalized_hero_distance
                if len(actions_for_entity[monster.id]) > 0:
                    value -= 20
                action_scores[Action(ActionType.MOVE, target_id=monster.id, x=x, y=y)] += value
            # Kill monster to farm it
            if d > BASE_RADIUS:
                delta = distance_from_position(hero, foxhole_1_mid) - distance_from_position(monster, foxhole_1_mid)
                delta = max(delta, -2000)
                # print(monster.id, delta, file=sys.stderr, flush=True)
                farming_bonus = extroversion[i] * delta/2000 * 50
                attack_penalty = max(1-distance_from_opp_base(monster)/5000, 0.05)*400 if monster.threat_for==2 else 0
                far_from_base_penalty = 100*base_love[i] if distance_from_base(monster) > state.get_safe_distance() else 0
                on_it_penalty = 20 if len(actions_for_entity[monster.id]) > 0 else 0
                action_scores[Action(ActionType.MOVE, target_id=monster.id, x=x, y=y)] += 90 * farm_love[i] - normalized_hero_distance * 25 + farming_bonus - attack_penalty - far_from_base_penalty - on_it_penalty
            # Control faraway monsters to attack
            if state.timestep > 100 and distance_from_base(monster)>4900 and  mana > 20 and distance_fn(monster, hero) < CONTROL_RANGE and monster.shield_life==0 and monster.threat_for!=2 and len(actions_for_entity[monster.id])==0:
                health_bonus = monster.health*2 - 40
                action_scores[Action(ActionType.CONTROL_TO_OPP, target_id=monster.id)] = 40 + min(mana-40, 35) + health_bonus
            # Wind monsters to attack
            if monster.shield_life==0 and BASE_RADIUS < distance_from_opp_base(monster) < BASE_RADIUS+2200 and distance_fn(hero, monster) < WIND_RANGE and mana > 20:
                time_penalty = 100 if state.timestep < 107 else -20
                redirect_bonus = 20 if monster.threat_for==0 else -10
                hp_bonus = monster.health * 6
                action_scores[Action(ActionType.WIND_MONSTER_INTO_BASE)] += min((mana-10)*3, 45) - time_penalty + hp_bonus
                # action_scores[Action(ActionType.CONTROL_TO_OPP, target_id=monster.id)] += (mana-10) - time_penalty
            # Wind monster to score a guaranteed point
            if monster.shield_life==0 and distance_from_opp_base(monster) < 2200 + 300 and distance_fn(hero, monster) < WIND_RANGE and mana >= 10:
                dx = other_x - monster.x
                dy = other_y - monster.y
                action_scores[Action(ActionType.WIND, target_id=monster.id, x=hero.x+dx, y=hero.y+dy)] += 70
            # Make a monster strong for offense
            if monster.threat_for==2 and distance_from_opp_base(monster) < 5800 and distance_fn(hero, monster) < SHIELD_RANGE and mana > 20 and monster.shield_life==0:
                time_penalty = 60 if state.timestep < 107 else 0
                hp_bonus = monster.health * 4.5
                # distance_bonus = 50 if 
                shield_penalty = monster.shield_life * 25
                action_scores[Action(ActionType.SHIELD, target_id=monster.id)] += hp_bonus - shield_penalty - time_penalty + 10

        # Go fuck with opponent
        if state.timestep > 35:
            home[2] = state.foxhole
            home[0] = (base_x+2000*flip, base_y+2000*flip)
        if state.timestep > 90:
            if mana < 20:
                home_love[2] = 0
            else:
                home_love[2] = 8
        #     x,y = target_towards((hero.x, hero.y), foxhole, 799)
        #     action_scores[Action(ActionType.MOVE, x=x, y=y)] += extroversion[i] * 100
        # Go home
        x,y = target_towards((hero.x, hero.y), home[i], 799)
        action_scores[Action(ActionType.MOVE, x=x, y=y)] += 8 * home_love[i]
        print('top 4', file=sys.stderr, flush=True)
        for action, score in list(sorted(action_scores.items(), key=lambda x: x[1], reverse=True))[:4]:
            print(action, score, file=sys.stderr, flush=True)
        flavor = "going..."
        action, score = max(action_scores.items(), key=lambda x: x[1])
        score = int(score)
        if action.type == ActionType.MOVE:
            print(f"MOVE {action.x} {action.y} {score}")
        elif action.type == ActionType.WIND_TO_OPP:
            print(f"SPELL WIND {other_x} {other_y} {score}")
            mana -= 10
        elif action.type == ActionType.WIND_MONSTER_INTO_BASE:
            print(f"SPELL WIND {other_x} {other_y} {score}")
            mana -= 10
            state.opponent_danger += 60
        elif action.type == ActionType.SHIELD:
            print(f"SPELL SHIELD {action.target_id} {score}")
            mana -= 10
        elif action.type == ActionType.WAIT:
            print(f"WAIT {score}")
        elif action.type == ActionType.CONTROL_AWAY:
            print(f"SPELL CONTROL {action.target_id} {action.x} {action.y} {score}")
            mana -= 10
        elif action.type == ActionType.CONTROL_TO_OPP:
            print(f"SPELL CONTROL {action.target_id} {opp_base_corners[state.which_opp_corner][0]} {opp_base_corners[state.which_opp_corner][1]} {score}")
            state.toggle_which_opponent_corner()
            mana -= 10
        elif action.type==ActionType.WIND:
            print(f"SPELL WIND {action.x} {action.y} {score}")
            mana-=10
        if action.target_id is not None:
            actions_for_entity[action.target_id].append(action)
        # In the first league: MOVE <x> <y> | WAIT; In later leagues: | SPELL <spellParams>;
