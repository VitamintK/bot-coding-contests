import sys
import math
from collections import namedtuple

# Auto-generated code below aims at helping you parse
# the standard input according to the problem statement.

# base_x: The corner of the map representing your base
base_x, base_y = [int(i) for i in input().split()]
other_x, other_y = [17630-base_x, 9000-base_y]
heroes_per_player = int(input())  # Always 3
flip = 1 if base_x == 0 else -1
home = [(base_x + 4000*flip, base_y+1000*flip),
(base_x + 4000 * flip, base_y + 4000*flip), (base_x+1000*flip, base_y+4000*flip)]

def distance_from_base(entity):
    return pow(entity.x-base_x, 2) + pow(entity.y-base_y,2)

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

# game loop
while True:
    for i in range(2):
        # health: Your base health
        # mana: Ignore in the first league; Spend ten mana to cast a spell
        health, mana = [int(j) for j in input().split()]
    current_heroes = []
    entity_count = int(input())  # Amount of heros and monsters you can see
    monsters = []
    for i in range(entity_count):
        # _id: Unique identifier
        # _type: 0=monster, 1=your hero, 2=opponent hero
        # x: Position of this entity
        # shield_life: Ignore for this league; Count down until shield spell fades
        # is_controlled: Ignore for this league; Equals 1 when this entity is under a control spell
        # health: Remaining health of this monster
        # vx: Trajectory of this monster
        # near_base: 0=monster with no target yet, 1=monster targeting a base
        # threat_for: Given this monster's trajectory, is it a threat to 1=your base, 2=your opponent's base, 0=neither
        # _id, _type, x, y, shield_life, is_controlled, health, vx, vy, near_base, threat_for = 
        entity = Entity(*[int(j) for j in input().split()])
        if entity.type == 1:
            current_heroes.append(entity)
        if entity.type == 0:
            monsters.append(entity)
    for i, hero in enumerate(current_heroes):
        if any(distance_from_base(monster) < 1000*1000 for monster in monsters):
            print(f"SPELL WIND {other_x} {other_y} USE WIND")
            continue
        if len(monsters) > 0:
            best = min(monsters, key=distance_from_base)
            x,y = target_towards((hero.x, hero.y), project_position(best, 400), 799)
        else:
            x,y = target_towards((hero.x, hero.y), home[i], 799)
        # Write an action using print
        # To debug: print("Debug messages...", file=sys.stderr, flush=True)
        print(f"MOVE {x} {y}")\
        # In the first league: MOVE <x> <y> | WAIT; In later leagues: | SPELL <spellParams>;
