import sys
import json
import json
import time
import math
import statistics
from copy import copy
from itertools import product, chain


""" Global Variables """
LOCAL = True
DEBUG = False
LOCAL_COUNTER = 0

logger = None
if LOCAL:
    import logging
    logging.basicConfig(level=logging.DEBUG, filename="output.log", filemode="w")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)


""" Utility Methods """
def input_():
    data = """13
    69 BREW -2 -2 -2 0 13 0 0 0 0
    63 BREW 0 0 -3 -2 17 0 0 0 0
    66 BREW -2 -1 0 -1 9 0 0 0 0
    60 BREW 0 0 -5 0 15 0 0 0 0
    45 BREW -2 0 -2 0 8 0 0 0 0
    78 CAST 2 0 0 0 0 -1 -1 1 0
    79 CAST -1 1 0 0 0 -1 -1 1 0
    80 CAST 0 -1 1 0 0 -1 -1 1 0
    81 CAST 0 0 -1 1 0 -1 -1 1 0
    82 OPPONENT_CAST 2 0 0 0 0 -1 -1 0 0
    83 OPPONENT_CAST -1 1 0 0 0 -1 -1 1 0
    84 OPPONENT_CAST 0 -1 1 0 0 -1 -1 1 0
    85 OPPONENT_CAST 0 0 -1 1 0 -1 -1 1 0
    4 0 0 1 0
    6 0 1 0 0
    """.split('\n')

    if LOCAL:
        global LOCAL_COUNTER
        response = data[LOCAL_COUNTER].strip()
        LOCAL_COUNTER += 1
        return response

    else:
        _input = input()
        if DEBUG:
            debug(_input)
        return _input

def debug(data):
    if DEBUG:
        print(str(data), file=sys.stderr, flush=True)

def transpose(data):
    t_data = {}
    for k,v in data.items():
        if v in t_data:
            t_data[v].append(k)
        else:
            t_data[v] = [k]
    return t_data


""" Utility Classes """
class Timer:
    MAX = 0.5

    def __init__(self, name):
        self.name = name
        self._start_time = time.perf_counter()
        self._last_report = self._start_time

    def report(self, msg=None):
        now = time.perf_counter()

        elapsed_time = now - self._start_time
        elapsed_percent = round(elapsed_time/Timer.MAX,2)*100

        elapsed_last = now - self._last_report
        last_percent = round(elapsed_last/Timer.MAX,2)*100

        priority = ''
        if last_percent >= 5:
            priority += '!'
        if last_percent >= 15:
            priority += '!'
        if last_percent >= 50:
            priority += '!'
        if last_percent >= 100:
            priority += '!!'

        debug(
            '[{}] {} {}: {:=0.2f}s {:=0.2f}% ({:=0.2f}s {:=0.2f}%)'.format(
                self.name, priority, msg or "Elapsed Time", 
                elapsed_time, elapsed_percent,
                elapsed_last, last_percent
            )
        )

        self._last_report = now


class Tree(dict):
    def rget(self, route, default=None):
        if len(route) < 1:
            return
        
        cache = self
        for key in route:
            cache = cache.get(key)
            if cache is None:
                return
        return cache.get(None)

    def rput(self, route, value):
        if len(route) < 1:
            return
        
        cache = self
        if len(route) > 1:
            for key in route[:-1]:
                cache = cache.setdefault(key, {})
        cache = cache.setdefault(route[-1], {})
        cache[None] = value


""" Game Classes """
class Delta:

    @property
    def worth(self):
        return self.price + sum(self.data[1:])

    @property
    def size(self):
        return round(math.sqrt(sum(d**2 for d in self)), 4)

    """ Instance Methods """
    def __init__(self, data=None, price=0):
        data = [0,0,0,0] if data is None else data

        self.data = data
        self.price = price

    def __repr__(self):
        return f'<Delta {self.data} {self.price}|{self.worth}r>'

    def __hash__(self):
        return hash((*self.data, self.price))
    
    def __eq__(self, other):
        return (
            all(x==y for x,y in zip(self.data, other.data)) and
            self.price==other.price
        )


    """ Copy Methods """
    def __copy__(self):
        return Delta(data=copy(self.data), price=self.price)


    """ Container Methods """
    def __len__(self):
        return len(self.data)

    def __iter__(self):
        yield from self.data


    """ Maths Methods """
    def __neg__(self):
        return Delta(
            data=[-k for k in self],
            price=-self.price
        )

    def __abs__(self):
        return Delta(
            data=[abs(k) for k in self],
            price=abs(self.price)
        )

    def __add__(self, other):
        return Delta(
            data=[s+o for s,o in zip(self.data, other.data)],
            price=self.price + other.price
        )

    def __sub__(self, other):
        return Delta(
            data=[s-o for s,o in zip(self.data, other.data)],
            price=self.price - other.price
        )

    def __truediv__(self, other):
        return Delta(
            data=[s/other for s in self.data],
            price=self.price/other
        )
    
    def __mul__(self, other):
        return Delta(
            data=[s*other for s in self.data],
            price=self.price*other
        )

    def __matmul__(self, other):
        return sum(s*o for s,o in zip(self.data, other.data))

    def normalize(self):
        if self.size == 0:
            return Delta()
        return self/self.size


class Recipe(Delta):
    def __init__(self):
        self._raw_data = str(input_()).split()
        """
        _raw_data:
        00:     action_id 
        01:     action_type
        02-05:  delta
        06:     price
        07:     tome_index
        08:     tax_count
        09:     castable
        10:     repeatable
        """
        super().__init__(
            data=[int(s) for s in self._raw_data[2:6]],
            price=int(self._raw_data[6])
        )
        self.id = int(self._raw_data[0])
        self.kind = str(self._raw_data[1]).lower().strip()
        self.tome_index = None
        self.tax = None
        self.castable = bool(int(self._raw_data[9]))
        self.repeatable = None

    def __repr__(self):
        return f'<Recipe {self.data} {self.price}|{self.worth}r>'

    def __pow__(self, other):
        sdelta = self + other
        sdelta.data = [-d if d <=0 else 0 for d in sdelta]
        return sdelta


class Player(Delta):

    @property
    def valid(self):
        return all(s>=0 for s in self) and sum(self.data) <= 10
   

    def __init__(self):
        self._raw_data = str(input_()).split()

        super().__init__(
            data=[int(s) for s in self._raw_data[:-1]],
            price=int(self._raw_data[-1])
        )

    def __repr__(self):
        return f'<Player {self.data} {self.price}|{self.worth}r>'


""" Compiled Features """
TURN, BUFFER_SIZE, MOVE_BUFFER = 0, 3, [80, 81, 'X']
WEIGHTS = {}
BREWS, BREWS_UPDATE = {}, False
# CHOSEN_TURNS = {
#     0: 79,
#     1: 80,
#     2: 81
# }
CHOSEN_TURNS = {}

# Global Features
G_OPTIONS = {}

# Player features
P_CASTS, P_OPTIONS, P_CASTS_UPDATE = {}, {}, False

# Opponent features
O_CASTS, O_OPTIONS, O_CASTS_UPDATE = {}, {}, False

# Cacheing features
SEEN_CACHE = Tree()
WEIGHTS = {}

# Methods
def calc_delta(option, casts): 
    delta = Delta()
    # result = Delta()
    for cast in option:
        if cast != 'X':
            delta += casts[cast]
    return delta

def iter_options(casts):
    # Get the cartesian product of this list of casts (to account for 
    # refresh) The 'X' marks when to refresh, and counts as a move

    # Initialize weights
    global WEIGHTS
    WEIGHTS = {k:0 for k in list(casts.keys()) + ['X']}

    # Helper Methods
    def iter_casts():
        # Generate combinations of all lengths
        def iter_option(option):
            yield option
            for k in casts:
                if not k in option:
                    yield from iter_option(option + (k,))
                
        # Seed results & return
        for k in casts:
            yield from iter_option((k,))

    def clean_option(key):
        _key = []
        for k in key:
            if len(_key) > 0:
                if k == 'X' and _key[-1] == 'X':
                    continue
            _key.append(k)
        return tuple(_key)

    def calc_weights(option): # options is a list of options
        """
        the algorithm here is simply: count how many require this cast 
        earliest on. More the better because there are 4 placements, we will
        effectively take (4-k)^2 where k is index and sum these all together
        everytime it appears.
        """
        for i,cast in enumerate(option):
            if cast != 'X':
                WEIGHTS[cast] += (4-i)**2

    # Chain list
    keys = chain(
        (
            clean_option(e) for e in iter_casts()
        ),
        (
            clean_option(e[0]+('X',)+e[1]) for e in product(
                iter_casts(), iter_casts()
            )
        )
        # (
        #     clean_option(e[0]+('X',)+e[1]+('X',)+e[2]) for e in product(
        #         iter_casts(), iter_casts(), ((k,) for k in casts.keys())
        #     )
        # )
    )

    # Append all
    for key in keys:
        seen = SEEN_CACHE.rget(key)
        if seen is not None:
            yield (key, seen)
        else:
            option = calc_delta(key, casts)
            SEEN_CACHE.rput(key, option)
            calc_weights(key)
            yield (key, option)

def initialize_options():
    # Ignore all oponent stuff for now

    global WEIGHTS, G_OPTIONS

    # Helper Methods
    def calc_com(option):
        try:
            return round(
                sum(i*WEIGHTS[o] for i,o in enumerate(option))/
                sum(WEIGHTS[o] for o in option),
                4
            )
        except ZeroDivisionError:
            return float(len(option)) # If only X's, then return the far right most value

    def convert_option(option):
        if option is None:
            return ('WAIT',)

        _option = ()
        for cast in option:
            if cast == 'X':
                _option += ('REST',)
            else:
                _option += (f'CAST {cast}',)
        return _option

    # Get shortened list of paths to each delta & transpose
    t_results, t_minlen = {}, {}
    for option, delta in iter_options(P_CASTS):
        if len(option) >= BUFFER_SIZE+1: # We are going to check our buffer against these for next move
            if delta in t_results:
                if len(option) < t_minlen[delta]:
                    t_results[delta] = [option]
                    t_minlen[delta] = len(option)
                else:
                    t_results[delta].append(option)
            else:
                t_results[delta] = [option]
                t_minlen[delta] = len(option)

    # Generate optimized results & cache by sub option
    buffer_cache = {}
    for options in t_results.values():
        opop = min(options, key=lambda o: calc_com(o))
        sub_options = (
            (opop[i:i+BUFFER_SIZE], opop[i+BUFFER_SIZE])
            for i in range(len(opop)-BUFFER_SIZE)
        )
        for option, next_option in sub_options:
            option_cache = buffer_cache.setdefault(option, {})
            option_cache[(next_option,)] = (
                Delta() if next_option == 'X' else P_CASTS[next_option]
            )

    # Only add paths to the global options if there is a next path
    # Add a weight that represents how dramatic of a change it was
    for option, data in buffer_cache.items():
        option_cache = G_OPTIONS.setdefault(option, {})
        for next_option, delta in data.items():
            key = option[1:]+next_option
            if key in buffer_cache:
                option_cache[next_option] = delta

    # G_OPTIONS = buffer_cache

def update_brews():
    # Generate optimized results, apply brews, and return transpose
    """
    This where the "magic" happens:
    We will store everything by 3-move substrings, and then by the "next"
    move. This list will then have all possible outcomes & their metrics
    So like:

        {
            "79:80:81": {
                "X": [
                    <Delta [-2, 1, -1, 2] 0|2r> <Recipe [-2, 0, -2, 0] 8|6r> <Delta [4, 0, 3, 0] 8|11r>
                    <Delta [-1, -1, 0, 2] 0|1r> <Recipe [-2, -2, -2, 0] 13|9r> <Delta [3, 3, 2, 0] 13|18r>
                    <Delta [-1, -1, 0, 2] 0|1r> <Recipe [0, 0, -3, -2] 17|12r> <Delta [1, 1, 3, 0] 17|21r>
                    <Delta [-1, -1, 0, 2] 0|1r> <Recipe [-2, -1, 0, -1] 9|7r> <Delta [3, 2, 0, 0] 9|11r>
                ]
            }
        }
    """
    global P_OPTIONS

    # for option, data in G_OPTIONS.items():
    #     for next_option, ops in data.items():
    #         option_cache = P_OPTIONS.setdefault(option, {})
    #         brews_cache = option_cache.setdefault(next_option, {})
    #         for brew in BREWS.values():
    #             if not brew in brews_cache:
    #                 brews_cache[brew] = [brew**delta]

    #         print('>>', next_option, len(ops))
    #         print(ops)
    #         print(len(ops))


    # for delta, options in t_results.items():
    #     opop = min(options, key=lambda o: calc_com(o))
    #     sub_options = (
    #         (opop[i:i+BUFFER_SIZE], opop[i+BUFFER_SIZE])
    #         for i in range(len(opop)-BUFFER_SIZE)
    #     )
    #     for option, next_option in sub_options:
    #         option_cache = P_OPTIONS.setdefault(option, {})
    #         brews_cache = option_cache.setdefault(next_option, {})
    #         for brew in BREWS.values():
    #             if not brew in brews_cache:
    #                 brews_cache[brew] = brew**delta
    
    # for option, data in P_OPTIONS.items():
    #     for next_option, brews in data.items():
    #         print(option, next_option, list(brews.values()))

    # print(json.dumps(P_OPTIONS, indent=2, default=str))
    pass

def encode_turn(token):
    if token in P_CASTS:
        return f'CAST {token}'
    elif token in BREWS:
        return f'BREW {token}'
    elif token == 'X':
        return 'REST'
    return 'WAIT'

def decode_turn(token):
    if isinstance(token, (tuple, list)):
        token = token[0]

    if 'CAST' in token or 'BREW' in token:
        return int(token.replace('CAST','').strip())
    elif token == 'REST':
        return 'X'
    return 'W'

def next_turn(player):
    global MOVE_BUFFER

    # If turn is chosen, use it
    if TURN in CHOSEN_TURNS:
        return encode_turn(CHOSEN_TURNS[TURN])

    move = None
    options = G_OPTIONS.get(tuple(MOVE_BUFFER))
    
    # If only one possible turn, use it
    if len(list(options.keys())) == 1:
        return list(options.keys())[0]

    # Check the next 2 rounds and see where you end up
    for move in options.values():
        options_2 = [MOVE_BUFFER]
        
    




    
    
    # if not options:
    #     MOVE_BUFFER = [79, 80, 81]
    #     return 'X'




    # move = 'WAIT'
    
    return move


""" Game Loop """
while True:
    timer = Timer('Game')

    # Get all known recipes
    recipe_count = int(input_())
    for _ in range(recipe_count):
        # Create recipe object
        recipe = Recipe()

        # Handle if brew
        if recipe.kind == 'brew':
            if not recipe.id in BREWS:
                BREWS[recipe.id] = recipe
                BREWS_UPDATE = True

        # Handle if player cast
        elif recipe.kind == 'cast':
            if not recipe.id in P_CASTS:
                P_CASTS[recipe.id] = recipe
                P_CASTS_UPDATE = True

        # Handle if opponent cast
        elif recipe.kind == 'opponent_cast':
            if not recipe.id in O_CASTS:
                O_CASTS[recipe.id] = recipe
                O_CASTS_UPDATE = True

    timer.report('Initialized recipes')
    
    # Get players
    player, oponent = Player(), Player()
    timer.report('Initialized players')

    # Initialize options
    if TURN == 0:
        initialize_options()
        timer.report('Initialized Options')

    # Update brews
    if BREWS_UPDATE:
        update_brews()
        timer.report('Initialized Brews')




    # Get movement toward each current brew
    # options = {}
    # raw_options = player.get_cast_options()
    # timer.report('Retrieved raw options')

    # for option, cast in raw_options.items():
    #     for brew_id, brew in brews.items():
    #         brew_player = (brew**player.inventory)
    #         brew_cast = (brew**cast)
    #         movement = round(brew_player.size - brew_cast.size,4)
    #         step = round(movement / len(option),4)

    #         new_player = player.inventory + brew
    #         income = new_player.worth - player.inventory.worth
    #         gain = round(income / len(option),4)
            
    #         if option in options:
    #             options[option].append((step, gain))
    #         else:
    #             options[option] = [(step, gain)]

    # timer.report('Solved gain')

    # # Organized options by fitness & convert options

    # option_fitness = {None: 0.0} # Insert fallback wait state
    # for option, stats in options.items():
    #     steps, gains = [v[0] for v in stats], [v[1] for v in stats]
    #     s_std, g_gtd = statistics.stdev(steps), statistics.stdev(gains)
    #     fitness = round(((1+s_std)**2)*((1+g_gtd)**2), 4)
    #     option_fitness[option] = fitness
    # t_option_fitness = transpose(option_fitness)
    # sorted_options = {
    #     convert_option(t_option_fitness[f][0]):f for f in 
    #     sorted(option_fitness.values(), reverse=True)
    # }
    # timer.report('Solved & sorted fitness')

    # # Try to get a brew, if possible. Otherwise, do best action
    # brew_worths = {}
    # for brew_id, brew in brews.items():
    #     brew_player = brew**player.inventory
    #     if brew_player.size == 0:
    #         brew_worths[abs(brew_player.worth)] = brew_id

    # if brew_worths:
    #     optimized_brews = {
    #         brew_worths[w]:w for w in sorted(brew_worths.keys(), reverse=True)
    #     }
    #     optimal_brew = list(optimized_brews.keys())[0]
    #     print(f'BREW {optimal_brew}')

    # else:
    #     optimal_action = list(sorted_options.keys())[0][0]
    #     print(optimal_action) 

    move = next_turn(player)
    if not move:
        debug('No turn provided')
        move = 'W'

    print(encode_turn(move))
    debug(MOVE_BUFFER)

    # Turn cleanup
    TURN += 1
    BREWS_UPDATE, P_CASTS_UPDATE, O_CASTS_UPDATE = False, False, False
    MOVE_BUFFER.append(decode_turn(move))
    if len(MOVE_BUFFER) > 3:
        MOVE_BUFFER.pop(0)
    if LOCAL:
        break
