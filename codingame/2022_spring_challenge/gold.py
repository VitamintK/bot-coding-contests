from enum import Enum
import sys
import math
from collections import namedtuple, defaultdict
import random

random.seed(5)

CONTROL_RANGE = 2200
SHIELD_RANGE = 2200
WIND_RANGE = 1280
WIND_EFFECT = 2200
BASE_RADIUS = 5000
DAMAGE_RANGE = 800
SCORE_RADIUS = 300
W, H = 17630, 9000
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
homes = [
    [(base_x+6000*flip, base_y+4000*flip)],
    [(base_x + 8000*flip, base_y+1000*flip)],
    [(base_x + 5500 * flip, base_y + 8000*flip)]
]

homes_2 = [
    [(base_x+2000*flip, base_y+2000*flip)],
    [(base_x + 5500*flip, base_y+1400*flip)],
    [(base_x+1200*flip, base_y+5500*flip)],
]
foxhole_1_mid = (other_x - 3500 * flip, other_y - 3500 * flip)
foxhole_1_left = (other_x - 5000 * flip, other_y - 1000 * flip)
foxhole_1_right = (other_x - 1000 * flip, other_y - 5000 * flip)
foxholes_2 = [
    (other_x - 1400 * flip, other_y - 1400 * flip),
    (other_x - 1500 * flip, other_y - 100 * flip),
    (other_x - 100 * flip, other_y - 1500 * flip),
]

base_love = [1,0,0]
defend_love = [2.3, 0.8, 0.3]
home_love = [1, 1, 1]
farm_love = [0.2, 0.3, 1]
extroversion = [0, 0.1, 1]
wind_love = [0.6, 0.3, 0.1]
shield_self_love = [1,0,0]

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

def within_bounds(position):
    x,y = position
    return 0<=x<W and 0<=y<H

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
        self.foxholes = [foxhole_1_mid]
        self.should_shield_base = False
        self.opp_turtling = False
        self.which_opp_corner = 0
        self.opponent_danger = 0
        self.opponent_base_shields = 0
        self.opponent_in_my_base = 0
    def toggle_which_opponent_corner(self):
        self.which_opp_corner += 1
        self.which_opp_corner %= 3
    def set_foxhole(self):
        if self.opponent_danger > 50:
            self.foxholes = foxholes_2
        else:
            period = (self.timestep//7)%3
            self.foxholes = [[foxhole_1_mid], [foxhole_1_right], [foxhole_1_left]][period]
    def get_safe_distance(self):
        if self.opponent_in_my_base>0:
            return 6000
        else:
            return 10000

state = State()
# game loop
while True:
    state.timestep += 1
    state.opponent_danger *= 0.8
    state.set_foxhole()
    state.opponent_in_my_base -= 1
    state.opponent_base_shields -= 1
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
            if distance_from_opp_base(entity) < 5500 and entity.shield_life > 0:
                state.opponent_base_shields = 10
    for i, hero in enumerate(my_heroes):
        if hero.is_controlled and distance_from_base(hero) < 5000:
            state.should_shield_base = True
        action_scores = defaultdict(float)
        action_metadata = defaultdict(lambda: {'targets': []})
        # action_scores[Action(ActionType.WAIT)] = 0
        for opp_hero in opp_heroes:
            # make opponent go away
            # if distance_from_base(opp_hero) < 7000 and distance_fn(opp_hero, hero) < WIND_RANGE and opp_hero.shield_life == 0 and mana > 80:
            #     action_scores[Action(ActionType.WIND_TO_OPP)] += 50
            # shield self
            if state.should_shield_base and distance_from_base(hero) < 5500 and distance_fn(opp_hero, hero) < CONTROL_RANGE and mana > 10 and hero.shield_life == 0:
                action_scores[Action(ActionType.SHIELD, target_id=hero.id)] = 200 * shield_self_love[i]
            # disrupt enemies with Wind
            if distance_fn(opp_hero, hero) < WIND_RANGE-400 and opp_hero.shield_life == 0 and mana > 10:
                for monster in monsters:
                    if monster.shield_life>0 and distance_from_opp_base(monster) < 5000 and distance_fn(monster, opp_hero) < WIND_RANGE:
                        close_bonus = 10 if distance_from_opp_base(monster) < 2500 else 0
                        action_scores[Action(ActionType.WIND, target_id=opp_hero.id, x=base_x, y=base_y)] += 70 + close_bonus
            # disrupt enemy defenses wih Control
            if distance_fn(opp_hero, hero) < CONTROL_RANGE and opp_hero.shield_life == 0 and mana > 10 and distance_from_opp_base(opp_hero) < 7500:
                attack_bonus = (state.opponent_danger-80) if state.opponent_danger>80 else -50
                time_bonus = -50 if state.timestep < 90 else 0
                mana_bonus = min(mana-29, 49)
                x = opp_hero.x - (other_x - opp_hero.x)
                y = opp_hero.y - (other_y - opp_hero.y)
                bonus = 5 if distance_from_opp_base(opp_hero) < 5000 else -40
                action_scores[Action(ActionType.CONTROL_AWAY, target_id=opp_hero.id, x=x, y=y)] += bonus + (random.random()-0.8) * 50 + attack_bonus + mana_bonus
        for monster in monsters:
            # last-ditch defense of our base
            if distance_from_base(monster) < 1400 and distance_fn(monster, hero) < WIND_RANGE and monster.shield_life == 0 and mana >= 10:
                if distance_fn(monster, hero) < 800 and monster.health <= 2:
                    pass
                else:
                    action_scores[Action(ActionType.WIND_TO_OPP)] += 600
            # use control for last-ditch defense if wind is out of range
            if SCORE_RADIUS+400 < distance_from_base(monster) < SCORE_RADIUS + 400 + 400 and distance_fn(monster, hero) < CONTROL_RANGE and monster.shield_life == 0 and mana >= 0:
                action = Action(ActionType.CONTROL_TO_OPP, target_id=monster.id)
                action_metadata[action]['targets'].append(monster)
                action_scores[action] += 400
            # preventative winding if opponent is attacking
            if distance_from_base(monster) < BASE_RADIUS and distance_fn(monster, hero) < WIND_RANGE and monster.shield_life==0 and mana >= 10 and state.opponent_in_my_base>0:
                if distance_fn(monster, hero) < 800 and monster.health <= 2:
                    pass
                else:
                    mana_bonus = min(max(0, mana-40), 20)
                    urgent_bonus = 0
                    # x,y = monster.x+monster.vx, monster.y+monster.vy
                    x,y = monster.x, monster.y
                    for opp_hero in opp_heroes:
                        if distance_from_position(opp_hero, (x,y)) <= WIND_RANGE and (distance_fn(hero, opp_hero) > WIND_RANGE or math.dist((x,y), (base_x, base_y))<=WIND_EFFECT+SCORE_RADIUS):
                            urgent_bonus += 150
                    action_scores[Action(ActionType.WIND_TO_OPP)] += (95 + mana_bonus + urgent_bonus) * 1.66 * wind_love[i]
            # push out of base to get more wild mana
            if distance_fn(monster, hero) < WIND_RANGE and 2000 < distance_from_base(monster) < BASE_RADIUS and monster.shield_life == 0 and mana >= 10:
                action_scores[Action(ActionType.WIND_TO_OPP, target_id=monster)] += wind_love[i] * 40 + min(mana, 25)
            d = distance_from_base(monster)
            normalized_base_distance = 1 - math.sqrt(min(d, 10000)/10000)
            normalized_hero_distance = math.sqrt(min(distance_fn(hero, monster), 10000)/10000)
            # x,y = target_towards((hero.x, hero.y), project_position(monster, 400), 799)
            x,y = target_towards((hero.x, hero.y), (monster.x, monster.y), 800)
            # Kill monster if it's a threat
            if monster.threat_for==1:
                value = 150 * normalized_base_distance * defend_love[i] - 25 * normalized_hero_distance
                if len(actions_for_entity[monster.id]) > 0:
                    value -= 18
                action_scores[Action(ActionType.MOVE, target_id=monster.id, x=x, y=y)] += value
            # Control faraway monsters to attack
            if state.timestep > 70 and distance_from_base(monster)>4900 and  mana > 20 and distance_fn(monster, hero) < CONTROL_RANGE and monster.shield_life==0 and monster.threat_for!=2 and len(actions_for_entity[monster.id])==0:
                health_bonus = monster.health*2 - 40 if monster.health >= 6 else -100
                action = Action(ActionType.CONTROL_TO_OPP, target_id=monster.id)
                action_metadata[action]['targets'].append(monster)
                action_scores[action] = 40 + min(mana-40, 35) + health_bonus
            # Wind monsters to attack
            if monster.shield_life==0 and BASE_RADIUS < distance_from_opp_base(monster) < BASE_RADIUS+2200 and distance_fn(hero, monster) < WIND_RANGE and mana > 20:
                time_penalty = 100 if state.timestep < 80 else -20
                redirect_bonus = 20 if monster.threat_for==0 else -10
                hp_bonus = monster.health * 7
                action = Action(ActionType.WIND_MONSTER_INTO_BASE)
                action_metadata[action]['targets'].append(monster)
                action_scores[action] += min((mana-10)*3, 45) - time_penalty + hp_bonus - 25
            # Wind monster to score a guaranteed point
            if monster.shield_life==0 and distance_from_opp_base(monster) < WIND_EFFECT + SCORE_RADIUS and distance_fn(hero, monster) < WIND_RANGE and mana >= 10:
                dx = other_x - monster.x
                dy = other_y - monster.y
                action_scores[Action(ActionType.WIND, target_id=monster.id, x=hero.x+dx, y=hero.y+dy)] += 70
            # Wind monster if opponent defenders are shielded or far away
            if monster.shield_life==0 and distance_from_opp_base(monster) <= 5000 and distance_fn(hero, monster) < WIND_RANGE and mana >= 10:
                dx = other_x - monster.x
                dy = other_y - monster.y
                heroes_shielded = 0
                heroes_unshielded = 0
                heroes_unhelpful = 0
                for opp_hero in opp_heroes:
                    if opp_hero.shield_life > 0 and distance_fn(opp_hero, hero) < WIND_RANGE:
                        heroes_shielded += 1
                    elif opp_hero.shield_life == 0 and distance_fn(opp_hero, hero) < WIND_RANGE:
                        heroes_unshielded += 1
                    elif distance_from_opp_base(opp_hero) - distance_from_opp_base(monster) + 2200 > 1000:
                        heroes_unhelpful += 1
                bonus = 0
                if heroes_unhelpful==3:
                    bonus += 200
                if heroes_shielded > 0 and heroes_unshielded == 0:
                    bonus += 200
                action_scores[Action(ActionType.WIND, target_id=monster.id, x=hero.x+dx, y=hero.y+dy)] += bonus
                
            # Shield a monster for offense
            if monster.threat_for==2 and distance_from_opp_base(monster) < 5800 and distance_fn(hero, monster) < SHIELD_RANGE and mana >= 20 and monster.shield_life==0:
                time_penalty = 60 if state.timestep < 80 else 0
                hp_bonus = monster.health * 4.5
                distance_bonus = 20 if distance_from_opp_base(monster) < 3000 else 0
                shield_penalty = monster.shield_life * 25
                action_scores[Action(ActionType.SHIELD, target_id=monster.id)] += hp_bonus - shield_penalty - time_penalty + distance_bonus + 10

        # Go fuck with opponent
        if state.timestep > 35:
            homes[2] = state.foxholes
            homes[0] = homes_2[0]
            homes[1] = homes_2[1]
        if state.timestep > 90:
            if mana < 20:
                home_love[2] = 0.5
            else:
                home_love[2] = 5
        # Go home
        for home in homes[i]:
            x,y = target_towards((hero.x, hero.y), home, 799)
            action = Action(ActionType.MOVE, x=x, y=y)
            if action not in action_scores:
                action_scores[action] += 8 * home_love[i]
        for dx in range(-800, 801, 80):
            for dy in range(-800, 801, 80):
                if math.dist((0,0), (dx,dy)) > 800:
                    continue
                if not (0 <= hero.x + dx <= W) or not (0 <= hero.y + dy <= H):
                    continue
                action = Action(ActionType.MOVE, x=hero.x+dx, y=hero.y+dy)
                if action not in action_scores:
                    action_scores[action] = 8 * home_love[i] * 0.7

        for action in action_scores:
            if action.type != ActionType.MOVE:
                continue
            # calculate positional farming bonuses
            delta = distance_from_position(hero, foxhole_1_mid) - math.dist((action.x, action.y), foxhole_1_mid)
            delta = max(delta, -2000)
            farming_bonus = extroversion[i] * delta/2000 * 50
            far_from_base_penalty = base_love[i]*math.dist((action.x,action.y),(base_x,base_y))*(300/5000) if math.dist((base_x, base_y), (action.x, action.y)) > state.get_safe_distance() else 0
            far_from_home_penalty = 300
            for home in homes[i]:
                far_from_home_penalty = min(far_from_home_penalty, home_love[i] * math.dist((action.x,action.y), home)/5000 * 10)
            action_scores[action] -= far_from_base_penalty
            for monster in monsters:
                # do get close to monster so I can spell it
                monster_distance = distance_from_position(monster, (action.x, action.y))
                if monster_distance <= WIND_RANGE:
                    action_scores[action] += 7
                if monster_distance <= CONTROL_RANGE:
                    action_scores[action] += 7
                if monster_distance <= DAMAGE_RANGE:
                    d = distance_from_base(monster)
                    # don't harm monster if it can get us a point
                    if monster.near_base==1 and monster.threat_for==2:
                        action_scores[action] -= 35
                    # do harm monster if it can get us mana
                    if d > BASE_RADIUS:
                        attack_penalty = max(1-distance_from_opp_base(monster)/5000, 0.05)*400 if monster.threat_for==2 else 0
                        on_it_penalty = 28 if len(actions_for_entity[monster.id]) > 0 else 0
                        action_scores[action] += 90 * farm_love[i] - normalized_hero_distance * 25 + farming_bonus - attack_penalty - on_it_penalty - far_from_home_penalty
                    # do harm monster to defend base
                    if monster.threat_for==1:
                        # calculate defense bonus
                        # d = math.dist((base_x, base_y), (action.x, action.y))
                        if len(actions_for_entity[monster.id]) > 0 and monster.health <= 2:
                            pass
                        else:
                            d = distance_from_base(monster)
                            normalized_base_distance = 1 - math.sqrt(min(d, 10000)/10000)
                            normalized_hero_distance = math.sqrt(min(distance_fn(hero, monster), 10000)/10000)
                            defense_value = 150 * normalized_base_distance * defend_love[i] - 25 * normalized_hero_distance
                            action_scores[action] = max(action_scores[action], defense_value)
                            action_scores[action] += 10
                            action_metadata[action]['targets'].append(monster)
        
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
            for target in action_metadata[action]['targets']:
                dy, dx = other_y - target.y, other_x - target.x
                ok = True
                for target2 in action_metadata[action]['targets']:
                    nx, ny = target2.x+dx, target2.y+dy
                    if not within_bounds((nx,ny)):
                        ok = False
                        break
                if ok:
                    break
            print(f"SPELL WIND {hero.x+dx} {hero.y+dy} {score}")
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
            if distance_from_opp_base(action_metadata[action]['targets'][0]) < 6000:
                 print(f"SPELL CONTROL {action.target_id} {other_x} {other_y} {score}")
            else:
                print(f"SPELL CONTROL {action.target_id} {opp_base_corners[state.which_opp_corner][0]} {opp_base_corners[state.which_opp_corner][1]} {score}")
                state.toggle_which_opponent_corner()
            mana -= 10
        elif action.type==ActionType.WIND:
            print(f"SPELL WIND {action.x} {action.y} {score}")
            mana-=10
        if action.target_id is not None:
            actions_for_entity[action.target_id].append(action)
