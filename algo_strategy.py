import gamelib
import random
import math
import warnings
from sys import maxsize
import json

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))
        self.previous_health = None
        self.current_health = None
        self.scored_on_locations = []  # Store breach locations
        self.health_lost_last_turn = 0
        self.health_lost_two_turns_ago = 0 
        self.no_attack_turns_remaining = 0 
        self.stored_damaged_location = None
        self.stored_attack_location = None
        self.hit_hard = 0
        self.reinforce_location = None
        self.reinforce_turns_left = 0
        self.first_damaged_location = None
        self.first_attacker_location = None
        self.breach_history = []
        self.breach_count = 0
        self.breached_location = None
        self.breaches = []
        self.individual_scored_on_locations = []
        self.send = False

        self.damage_history = {}  # Store last two damage locations
        self.reinforce_edge_turns_left = 0
        self.reinforce_focus_side = None
        self.turns_since_last_attack = 0
        self.last_attack_detected = False


    def on_game_start(self, config):
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        self.damage_taken = 0
        self.oldest_key = None
        self.got_breached = False

        # Observe the opponent and adjust defenses accordingly
        self.side_offensive = False
        self.central_offensive = False

    def on_turn(self, turn_state):
        try:
            game_state = gamelib.GameState(self.config, turn_state)
            gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
            game_state.suppress_warnings(True)  # Comment or remove this line to enable warnings.

            # Calculate the difference in health between turns

            self.current_health = game_state.my_health  # Store current health
            self.health_lost_two_turns_ago = self.health_lost_last_turn
            self.current_health = game_state.my_health  # Store current health
            if self.previous_health is not None:
                self.health_lost_last_turn = self.previous_health - self.current_health

            if self.hit_hard > 0:
                self.hit_hard -= 1
            # Update turns since last attack
            if self.last_attack_detected:
                self.turns_since_last_attack += 1
                self.last_attack_detected = False


            # Execute the strategy
            self.strategy(game_state)

            # Update previous health for the next turn
            self.previous_health = self.current_health
            game_state.submit_turn()

        except Exception as e:
            gamelib.debug_write(f"Exception occurred: {e}")

    def strategy(self, game_state: gamelib.GameState):
        best_start_location, path_risk = self.select_optimal_path(game_state)
        if game_state.get_resource(MP) > 7 and (game_state.get_resource(MP)) * 15 - path_risk >= 45 and not game_state.turn_number == 1:
            if (game_state.get_resource(SP, 1) > 8):
                start_location, path_risk = self.find_second_best_optimal_path(game_state)
                self.place_and_delete_support_near_scouts(game_state, start_location)
                game_state.attempt_spawn(SCOUT, start_location, math.floor(game_state.get_resource(MP)))
            self.place_and_delete_support_near_scouts(game_state, best_start_location)
            game_state.attempt_spawn(SCOUT, best_start_location, math.floor(game_state.get_resource(MP)))
        self.send = False
        if game_state.enemy_health <= 5:
            self.send = True
        ran = False

        if ((game_state.get_resource(MP)) * 15) - path_risk >= game_state.enemy_health * 15:
            self.place_and_delete_support_near_scouts(game_state, best_start_location)
            game_state.attempt_spawn(SCOUT, best_start_location, math.floor(game_state.get_resource(MP)))
        self.setup_defense(game_state)

        # # ABUSE ATTACK
        # locations_to_check = [
        #     [4, 15], [4,14]
        # ]

        # # Define the row to check for exactly one turret
        # row_to_check = [[4, 15], [3, 15], [2, 15], [1, 15], [0, 15], [5, 15], [5, 16]]

        # # Initialize flags
        # all_conditions_met = True
        # turret_count_in_row = 0

        # # Check each location for non-turret units
        # for location in locations_to_check:
        #     if not game_state.contains_stationary_unit(location):
        #         all_conditions_met = False
        #         break

        # # Count turrets in the specified row
        # for location in row_to_check:
        #     if game_state.contains_stationary_unit(location):
        #         units_at_location = game_state.game_map[location[0], location[1]]
        #         if any(unit.unit_type == TURRET for unit in units_at_location):
        #             turret_count_in_row += 1

        # if all_conditions_met and not self.send and turret_count_in_row == 1 and game_state.turn_number == 3 and game_state.get_resource(MP, 1) >= 8 and (game_state.get_resource(MP)) * 15 - path_risk >= 15:
        #     # Your code to execute if all conditions are met
        #     self.place_and_delete_support_near_scouts(game_state, [0, 13])
        #     game_state.attempt_spawn(SCOUT, [0, 13], math.floor(game_state.get_resource(MP)))

        # # Define the locations to check
        # locations_to_check = [
        #     [4, 16], [4, 17], [3, 15], [3 , 14], [4, 15],
        #     [1, 14], [1, 15], [2, 14], [4, 14], [2, 15], [2, 16], [5, 16], [4, 16], [3, 16]
        # ]

        # # Initialize a flag to determine if all conditions are met
        # all_conditions_met = True
        # number_turr = 0
        # for location in locations_to_check:
        #     # Check if there's a stationary unit at the location
        #     if game_state.contains_stationary_unit(location):
        #         units_at_location = game_state.game_map[location[0], location[1]]
        #         # Check if any of the units at this location is a turret
        #         if any(unit.unit_type == TURRET for unit in units_at_location):
        #             number_turr += 1
        #             if number_turr >= 2:
        #                 all_conditions_met = False
        #                 break

        # # Check the turn number and available SP, and combine it with the previous checks
        # if all_conditions_met and game_state.turn_number > 3 and not self.send and not game_state.get_resource(SP, 1) >= 8 and self.breached_location and self.breached_location[1] != 13 and (game_state.get_resource(MP)) * 15 - path_risk >= 15 :
        #     # Your code to execute if all conditions are met
        #     self.place_and_delete_support_near_scouts(game_state, [0, 13])
        #     game_state.attempt_spawn(SCOUT, [0, 13], math.floor(game_state.get_resource(MP)))
        #     ran = True

        # # RIGHT SIDE
        # locations_to_check = [
        #     [23, 15], [23,14]
        # ]

        # # Define the row to check for exactly one turret
        # row_to_check = [[21, 15], [22, 15], [23, 15], [24, 15], [25, 15], [26, 15]]

        # # Initialize flags
        # all_conditions_met = True
        # turret_count_in_row = 0

        # # Check each location for non-turret units
        # for location in locations_to_check:
        #     if not game_state.contains_stationary_unit(location):
        #         all_conditions_met = False
        #         break

        # # Count turrets in the specified row
        # for location in row_to_check:
        #     if game_state.contains_stationary_unit(location):
        #         units_at_location = game_state.game_map[location[0], location[1]]
        #         if any(unit.unit_type == TURRET for unit in units_at_location):
        #             turret_count_in_row += 1

        # if all_conditions_met and turret_count_in_row == 1 and not self.send and game_state.turn_number == 3 and game_state.get_resource(MP, 1) >= 8 and (game_state.get_resource(MP)) * 15 - path_risk >= 15:
        #     # Your code to execute if all conditions are met
        #     self.place_and_delete_support_near_scouts(game_state, [27, 13])
        #     game_state.attempt_spawn(SCOUT, [27, 13], math.floor(game_state.get_resource(MP)))

        # # Define the locations to check
        # locations_to_check = [
        #     [23, 16], [23, 17], [25, 14], [27, 13], 
        #     [26, 13], [24, 15], [24, 14], [23, 14], [22, 15], [24, 14], [23, 14]
        # ]

        # # Initialize a flag to determine if all conditions are met
        # all_conditions_met = True
        # number_turr = 0
        # for location in locations_to_check:
        #     # Check if there's a stationary unit at the location
        #     if game_state.contains_stationary_unit(location):
        #         units_at_location = game_state.game_map[location[0], location[1]]
        #         # Check if any of the units at this location is a turret
        #         if any(unit.unit_type == TURRET for unit in units_at_location):
        #             number_turr += 1
        #             if number_turr >= 2:
        #                 all_conditions_met = False
        #                 break

        # # Check the turn number and available SP, and combine it with the previous checks
        # if all_conditions_met and game_state.turn_number > 3 and not self.send and not game_state.get_resource(SP, 1) >= 8 and self.breached_location and self.breached_location[1] != 13 and (game_state.get_resource(MP)) * 15 - path_risk >= 15:
        #     # Your code to execute if all conditions are met          
        #     if not ran:
        #         self.place_and_delete_support_near_scouts(game_state, [27, 13])
        #         game_state.attempt_spawn(SCOUT, [27, 13], math.floor(game_state.get_resource(MP)))

        # if game_state.get_resource(MP) >= 6:
        #     best_start_location, path_risk = self.select_optimal_path(game_state)
        #     if (game_state.get_resource(MP)) * 15 - path_risk >= 60 and not self.send:
        #         self.place_and_delete_support_near_scouts(game_state, best_start_location)
        #         gamelib.debug_write("Here1")
        #         game_state.attempt_spawn(SCOUT, best_start_location, math.floor(game_state.get_resource(MP)))
            
        # Step 3: Handle the reinforcement process if needed
        # if self.reinforce_turns_left > 0 and self.reinforce_location is not None:
        #     if game_state.turn_number == 1:
        #         self.reinforce_turns_left = 0
        #     else:
        #         if self.reinforce_turns_left == 1:
        #             best_start_location, path_risk = self.select_optimal_path(game_state)
        #             if (game_state.get_resource(MP)) * 15 - path_risk >= 60:
        #                 if (game_state.get_resource(SP, 1) > 8):
        #                     start_location, path_risk = self.find_second_best_optimal_path
        #                     self.place_and_delete_support_near_scouts(game_state, start_location)
        #                     game_state.attempt_spawn(SCOUT, start_location, math.floor(game_state.get_resource(MP)))
        #                 self.place_and_delete_support_near_scouts(game_state, best_start_location)
        #                 self.reinforce_damaged_turret(game_state, self.reinforce_location, self.reinforce_attack)
        #             self.reinforce_turns_left -= 1
        # elif hasattr(self, 'first_damaged_location') and self.first_damaged_location is not None:
        #     if game_state.turn_number == 1:
        #         self.reinforce_turns_left = 0
        #     else:
        #         self.reinforce_damaged_turret(game_state, self.first_damaged_location, self.first_attacker_location)
        #         self.reinforce_location = self.first_damaged_location
        #         self.reinforce_attack = self.first_attacker_location
        #         self.reinforce_turns_left = 2 

        # if game_state.turn_number == 1:
        #         self.reinforce_turns_left = 0
        # else:
        #     if self.first_damaged_location and 9 <= self.first_damaged_location[0] <= 17 and self.health_lost_last_turn >= 3:
        #         refunded = self.refund_turret_from_cluster(game_state)
        #         if refunded:
        #             self.reinforce_middle_defense(game_state)
        #     elif self.first_damaged_location and 0 <= self.first_damaged_location[0] <= 4 and self.health_lost_last_turn >= 3:
        #         refunded = self.refund_turret_from_cluster(game_state)
        #         if refunded:
        #             self.reinforce_left_defense(game_state)
        #     elif self.first_damaged_location and 5 <= self.first_damaged_location[0] <= 9 and self.health_lost_last_turn >= 3:
        #         refunded = self.refund_turret_from_cluster(game_state)
        #         if refunded:
        #             self.reinforce_left_middle_defense(game_state)
        #     elif self.first_damaged_location and 22 <= self.first_damaged_location[0] <=  26 and self.health_lost_last_turn >= 3:
        #         refunded = self.refund_turret_from_cluster(game_state)
        #         if refunded:
        #             self.reinforce_right_defense(game_state)
        #     elif self.first_damaged_location and 17 <= self.first_damaged_location[0] <=  22 and self.health_lost_last_turn >= 3:
        #         refunded = self.refund_turret_from_cluster(game_state)
        #         if refunded:
        #             self.reinforce_right_middle_defense(game_state)

        self.setup_defense2(game_state)
        self.first_damaged_location = None
        self.first_attacker_location = None
        # Step 4: Execute the attack strategy after the defense setup
        self.attack_strategy(game_state)
    
    def refund_turret_from_cluster(self, game_state: gamelib.GameState):
        # Define the locations of the left and right cluster turrets
        left_cluster_positions = [ [3, 12],[4, 12], [5, 12]]  # Adjust according to your setup
        right_cluster_positions = [ [24, 12],[23, 12], [22, 12]]  # Adjust according to your setup


        # Check the left cluster first
        left_turret_count = sum(1 for pos in left_cluster_positions if self.has_turret(game_state, pos))
        if left_turret_count >= 3:
            return self.remove_turret_from_cluster(game_state, left_cluster_positions)

        # If the left cluster doesn't have 3 turrets, check the right cluster
        right_turret_count = sum(1 for pos in right_cluster_positions if self.has_turret(game_state, pos))
        if right_turret_count >= 3:
            return self.remove_turret_from_cluster(game_state, right_cluster_positions)

        return False
    
    def has_turret(self, game_state: gamelib.GameState, pos):
        if game_state.contains_stationary_unit(pos):
            units = game_state.game_map[pos[0], pos[1]]
            for unit in units:
                if unit.unit_type == TURRET:
                    return True
        return False
    
    def find_second_best_optimal_path(self, game_state: gamelib.GameState):
        best_start_location = None
        second_best_start_location = None
        lowest_risk = float('inf')
        second_lowest_risk = float('inf')

        # Define all possible starting points
        start_locations_left = [[0, 13], [1, 12], [2, 11], [3, 10], [4, 9], [5, 8], [6, 7], [7, 6], [8, 5], [9, 4], 
                                [10, 3], [11, 2], [12, 1], [13, 0]]
        start_locations_right = [[14, 0], [15, 1], [16, 2], [17, 3], [18, 4], [19, 5], [20, 6], [21, 7], [22, 8], [23, 9], 
                                [24, 10], [25, 11], [26, 12], [27, 13]]

        all_start_locations = start_locations_left + start_locations_right

        for start_location in all_start_locations:
            path = game_state.find_path_to_edge(start_location)
            
            if not path or len(path) < 2:
                continue  # Skip paths that are blocked or too short

            turret_risk = self.calculate_turret_risk(game_state, path)
            total_risk = turret_risk 

            # Find the best path
            if total_risk < lowest_risk or (total_risk == lowest_risk and abs(start_location[0] - 13) < abs(best_start_location[0] - 13)):
                lowest_risk = total_risk
                best_start_location = start_location

        # Now, find the second-best path on the opposite side
        opposite_side = start_locations_left if best_start_location in start_locations_right else start_locations_right

        for start_location in opposite_side:
            path = game_state.find_path_to_edge(start_location)
            
            if not path or len(path) < 2:
                continue  # Skip paths that are blocked or too short

            turret_risk = self.calculate_turret_risk(game_state, path)
            total_risk = turret_risk 

            # Update second-best path only if it's on the opposite side
            if total_risk < second_lowest_risk or (total_risk == second_lowest_risk and abs(start_location[0] - 13) < abs(second_best_start_location[0] - 13)):
                second_lowest_risk = total_risk
                second_best_start_location = start_location

        # If no valid second-best path is found, fall back to a default path on the opposite side
        if not second_best_start_location:
            second_best_start_location = [13, 0] if best_start_location in start_locations_right else [14, 0]

        return second_best_start_location, second_lowest_risk



    def should_use_support(self, game_state: gamelib.GameState) -> bool:
        """
        Determine if the support unit should be used this turn.
        Conditions include:
        - Health lost in the previous turn is minimal.
        - We are not in a "hit hard" recovery period.
        - There is enough MP to deploy the number of scouts needed for an attack this turn.
        """
        # Calculate the risk of the path and determine the number of scouts needed
        if self.health_lost_last_turn != 0:
            return False
        best_start_location, path_risk = self.select_optimal_path(game_state)
        num_scouts = self.determine_scout_count(path_risk, game_state)

        # Check if we have enough MP to deploy the calculated number of scouts
        can_attack = game_state.get_resource(MP) >= num_scouts

        # Only use support if we're planning to attack and meet the health conditions
        return can_attack
    

    def reinforce_middle_defense(self, game_state: gamelib.GameState):
        # Positions for reinforcing the middle (adjust as needed)
        middle_turrets = [[12, 11], [15, 11]]
        middle_walls = [[12, 12]]

        for pos in middle_turrets:
            game_state.attempt_spawn(TURRET, pos)
            game_state.attempt_upgrade(pos)
    
    def reinforce_left_defense(self, game_state: gamelib.GameState):
        # Positions for reinforcing the middle (adjust as needed)
        left_turrets = [[1, 13], [12, 13]]

        for pos in left_turrets:
            game_state.attempt_spawn(TURRET, pos)
            game_state.attempt_upgrade(pos)
    
    def reinforce_left_middle_defense(self, game_state: gamelib.GameState):
        # Positions for reinforcing the middle (adjust as needed)
        left_turrets = [[6, 13], [7, 13]]

        for pos in left_turrets:
        
            game_state.attempt_spawn(TURRET, pos)
            
            game_state.attempt_upgrade(pos)

    def reinforce_right_defense(self, game_state: gamelib.GameState):
        # Positions for reinforcing the middle (adjust as needed)
        right_turrets = [[26, 13], [15, 13]]

        for pos in right_turrets:
            game_state.attempt_spawn(TURRET, pos)
    
            game_state.attempt_upgrade(pos)

    def reinforce_right_middle_defense(self, game_state: gamelib.GameState):
        # Positions for reinforcing the middle (adjust as needed)
        right_turrets = [[21, 13], [20, 13]]

        for pos in right_turrets:
            game_state.attempt_spawn(TURRET, pos)
            game_state.attempt_upgrade(pos)


    def reinforce_damaged_turret(self, game_state: gamelib.GameState, damaged_location, attacker_location):
        units_at_location = game_state.game_map[[25, 12]]
        if game_state.contains_stationary_unit([25, 12]):
            for unit in units_at_location:
                if unit.unit_type == SUPPORT:
                    game_state.attempt_remove([25, 12])
        if damaged_location is None or attacker_location is None:
            gamelib.debug_write("Error: damaged_location or attacker_location is None. Cannot reinforce.")
            return

        sp_reserved_for_support = 4 if self.should_use_support(game_state) else 0

        # Define groups of positions for reinforcement, based on x-axis ranges
        reinforcement_groups = [
            {"x_range": range(0, 5), "turrets": [[3, 12], [5, 12]], "walls": [[3, 13], [5, 13]]},
            {"x_range": range(5, 15), "turrets": [[9, 12], [11, 12]], "walls": [[9, 13], [11, 13]]},
            {"x_range": range(15, 22), "turrets": [[16, 12], [18, 12]], "walls": [[16, 13], [18, 13]]},
            {"x_range": range(22, 28), "turrets": [[24, 12], [22, 12]], "walls": [[24, 13], [22, 13]]}
        ]

        # Iterate through the groups to find the relevant one based on the damaged location
        for group in reinforcement_groups:
            if damaged_location[0] in group["x_range"]:
                turrets = group["turrets"]
                walls = group["walls"]

                if 5 <= damaged_location[0] <= 14:
                    if damaged_location[0] < 10:
                        for wall_pos, turret_pos in reversed(list(zip(walls, turrets))):
                            # Place and upgrade the turret

                            # Place and upgrade the wall
                            if game_state.game_map.in_arena_bounds(wall_pos):
                                if game_state.get_resource(SP) - sp_reserved_for_support - 2 >= 0:
                                    game_state.attempt_spawn(WALL, wall_pos)
                                if game_state.get_resource(SP) - sp_reserved_for_support - 2 >= 0:
                                    game_state.attempt_upgrade(wall_pos)
                            
                            if game_state.game_map.in_arena_bounds(turret_pos):
                                if game_state.get_resource(SP) - sp_reserved_for_support - 3 >= 0:
                                    game_state.attempt_spawn(TURRET, turret_pos)
                                if game_state.get_resource(SP) - sp_reserved_for_support - 5 >= 0:
                                    game_state.attempt_upgrade(turret_pos)
                if 15 <= damaged_location[0] <= 21:
                    if damaged_location[0] < 17:
                        for wall_pos, turret_pos in reversed(list(zip(walls, turrets))):
                            # Place and upgrade the turret

                            # Place and upgrade the wall
                            if game_state.game_map.in_arena_bounds(wall_pos):
                                if game_state.get_resource(SP) - sp_reserved_for_support - 2 >= 0:
                                    game_state.attempt_spawn(WALL, wall_pos)
                                if game_state.get_resource(SP) - sp_reserved_for_support - 2 >= 0:
                                    game_state.attempt_upgrade(wall_pos)
                            
                            if game_state.game_map.in_arena_bounds(turret_pos):
                                if game_state.get_resource(SP) - sp_reserved_for_support - 3 >= 0:
                                    game_state.attempt_spawn(TURRET, turret_pos)
                                if game_state.get_resource(SP) - sp_reserved_for_support - 5 >= 0:
                                    game_state.attempt_upgrade(turret_pos)


                # Iterate through turrets and their corresponding walls together
                for wall_pos, turret_pos in zip(walls, turrets):
                    # Place and upgrade the turret

                    # Place and upgrade the wall
                    if game_state.game_map.in_arena_bounds(wall_pos):
                        if game_state.get_resource(SP) - sp_reserved_for_support - 2 >= 0:
                            game_state.attempt_spawn(WALL, wall_pos)
                        if game_state.get_resource(SP) - sp_reserved_for_support - 2 >= 0:
                            game_state.attempt_upgrade(wall_pos)
                    
                    if game_state.game_map.in_arena_bounds(turret_pos):
                        if game_state.get_resource(SP) - sp_reserved_for_support - 3 >= 0:
                            game_state.attempt_spawn(TURRET, turret_pos)
                        if game_state.get_resource(SP) - sp_reserved_for_support - 5 >= 0:
                            game_state.attempt_upgrade(turret_pos)
                
                break
    

    def detect_enemy_support(self, game_state):
        """
        Detects enemy support units in key locations.
        Returns True if support units are detected, indicating a focused attack on the edges.
        """
        support_locations = [
            [12, 26], [13, 27],[13, 26], [13, 25], [13, 24], [13, 23], [13, 22], [14,22],
            [14, 26], [14, 25], [14, 24], [14, 23], [14, 27], [15, 26]
        ]
        
        for location in support_locations:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location[0], location[1]]:
                    if unit.unit_type == SUPPORT and unit.player_index == 1:
                        return True
        return False

    def upgrade_initial_walls(self, game_state):
        sp_reserved_for_support = 4 if self.should_use_support(game_state) else 0
        initial_wall_locations = [
            [4, 13], [17, 13], [10, 13], [23, 13]  # Walls in front of edge turrets
        ]
        for loc in initial_wall_locations:
            if game_state.get_resource(SP) - sp_reserved_for_support - 2 >= 0:  # Cost of placing a wall
                game_state.attempt_upgrade(loc)


    def place_turret(self, game_state, region):
        """
        Places a turret in the specified region: 'left' or 'right' along y = 10.
        """
        if region == "left":
            locations = [[6, 10], [8, 10], [10, 10]]  # Positions for the left region
        elif region == "right":
            locations = [[21, 10], [19, 10], [17, 10]]  # Positions for the right region

        for location in locations:
            if game_state.can_spawn(TURRET, location):
                game_state.attempt_spawn(TURRET, location)
                return location  # Return the location where the turret was placed

        return None  # No turret was placed if all p


    def select_optimal_path(self, game_state: gamelib.GameState):
        best_start_location = None
        lowest_risk = float('inf')

        # Define all possible starting points
        start_locations_left = [[0, 13], [1, 12], [2, 11], [3, 10], [4, 9], [5, 8], [6, 7], [7, 6], [8, 5], [9, 4], 
                                [10, 3], [11, 2], [12, 1], [13, 0]]
        start_locations_right = [[14, 0], [15, 1], [16, 2], [17, 3], [18, 4], [19, 5], [20, 6], [21, 7], [22, 8], [23, 9], 
                                [24, 10], [25, 11], [26, 12], [27, 13]]

        all_start_locations = start_locations_left + start_locations_right

        for start_location in all_start_locations:
            path = game_state.find_path_to_edge(start_location)
            
            if not path or len(path) < 2:
                continue  # Skip paths that are blocked or too short

            turret_risk = self.calculate_turret_risk(game_state, path)
            total_risk = turret_risk 

            # Prioritize paths closer to the center if the risks are similar
            if total_risk < lowest_risk or (total_risk == lowest_risk and abs(start_location[0] - 13) < abs(best_start_location[0] - 13)):
                lowest_risk = total_risk
                best_start_location = start_location

        # If no valid path is found, fall back to a default path
        if not best_start_location:
            best_start_location = [13, 0]  # Default to the center if no other valid paths

        return best_start_location, lowest_risk

    def calculate_turret_risk(self, game_state: gamelib.GameState, path):
        risk = 0
        for path_location in path:
            attackers = game_state.get_attackers(path_location, 0)

            for attacker in attackers:
                # Determine the turret's range and damage based on whether it is upgraded
                if attacker.upgraded:
                    turret_range = 4.5
                    turret_damage = 14
                else:
                    turret_range = 2.5
                    turret_damage = 6

                # Calculate the distance from the path location to the turret
                distance = game_state.game_map.distance_between_locations(path_location, [attacker.x, attacker.y])

                # Only consider turrets within their respective attack range
                if distance <= turret_range:
                    # Calculate risk inversely proportional to the distance
                    # Calculate the risk contribution of this turret
                    risk += turret_damage

        return risk

    def attack_strategy(self, game_state: gamelib.GameState):
        # Step 1: Select the optimal path that won't trap scouts
        best_start_location, path_risk = self.select_optimal_path(game_state)

        if best_start_location:
            # Step 2: Clear any friendly units along the path
            path = game_state.find_path_to_edge(best_start_location)
            if path:
                for location in path:
                    if game_state.contains_stationary_unit(location):
                        game_state.attempt_remove(location)  # Remove any friendly unit at this location

            # Step 3: Determine attack strategy based on path risk and available MP
            num_scouts = self.determine_scout_count(path_risk, game_state)  # Determine number of scouts based on risk

            # Step 4: Launch the attack if we have enough MP
        
            if self.health_lost_last_turn == 0 and self.hit_hard == 0:
                if game_state.get_resource(MP) >= num_scouts and game_state.get_resource(SP) >= 4:
                    if (game_state.get_resource(MP)) * 15 - path_risk >= 30 and not self.send:
                        if (game_state.get_resource(SP, 1) > 8):
                            start_location, path_risk = self.find_second_best_optimal_path(game_state)
                            self.place_and_delete_support_near_scouts(game_state, start_location)
                            game_state.attempt_spawn(SCOUT, start_location, math.floor(game_state.get_resource(MP)))
                        self.place_and_delete_support_near_scouts(game_state, best_start_location)
                        game_state.attempt_spawn(SCOUT, best_start_location, math.floor(game_state.get_resource(MP)))
                elif game_state.get_resource(MP, 1) >= 8:
                    game_state.attempt_spawn(INTERCEPTOR, (18, 22), 2)
                    game_state.attempt_spawn(INTERCEPTOR, (9, 22), 2)
            elif self.health_lost_last_turn >= 5 and game_state.get_resource(MP, 1) >= 8:
                game_state.attempt_spawn(INTERCEPTOR, (18, 22), 2)
                game_state.attempt_spawn(INTERCEPTOR, (9, 22), 2)
                self.hit_hard = 1



    def place_and_delete_support_near_scouts(self, game_state, scout_location):
        """
        Places a support unit near the scout location in a way that does not block the scout's path and immediately deletes it after it provides its effect.
        """
        x, y = scout_location

        # Find the path that the scout would take to the edge
        path = game_state.find_path_to_edge(scout_location)

        if not path:
            # If no valid path is found, log an error and return
            gamelib.debug_write("No valid path found for the scout.")
            return

        # Determine potential support locations around the scout's initial position
        if x > 13:
            # Right side attack: prefer placing support to the left and away from the path
            possible_locations = [
                [x - 2, y - 1],  # Left and down
                [x - 2, y + 1],  # Left and up
                [x - 1, y - 1],  # Directly down
                [x - 1, y + 1],  # Directly up
            ]
        else:
            # Left side attack: prefer placing support to the right and away from the path
            possible_locations = [
                [x + 2, y - 1],  # Right and down
                [x + 2, y + 1],  # Right and up
                [x + 1, y - 1],  # Directly down
                [x + 1, y + 1],  # Directly up
            ]

        # Filter out any locations that are directly on the scout's path
        support_location = None
        for loc in possible_locations:
            if game_state.game_map.in_arena_bounds(loc) and loc not in path:
                support_location = loc
                break

        # If a valid support location is found, place and remove the support unit
        if support_location:
            game_state.attempt_spawn(SUPPORT, support_location)
            game_state.attempt_remove(support_location)
        else:
            gamelib.debug_write("No valid support location found that is not in the scout's path.")


    def determine_scout_count(self, path_risk, game_state: gamelib.GameState):
        """
        Determine the number of scouts to deploy based on the risk level of the selected path.
        The number of scouts scales with the risk, ensuring enough force is applied to breach defenses.
        """
        # Define thresholds based on empirical or experimental data

        if (game_state.get_resource(MP)) * 15 - path_risk >= 6 * 15:
            return 1
        else: return 1000

    def get_number_turrets_in_area(self, game_state):
        return min(self.detect_unit(game_state, player_index=1, unit_type=TURRET, valid_x=[i for i in range(0, 11)],
                                    valid_y=[i for i in range(14, 20)]),
                   self.detect_unit(game_state, player_index=1, unit_type=TURRET, valid_x=[i for i in range(17, 28)],
                                    valid_y=[i for i in range(14, 20)]))

    def setup_defense(self, game_state: gamelib.GameState):
        # Step 1: Place and upgrade initial turrets on the edges
        best_start_location, path_risk = self.select_optimal_path(game_state)
        if self.health_lost_two_turns_ago and (game_state.get_resource(MP)) * 15 - path_risk >= 15 >= 5 or game_state.turn_number == 2 and game_state.get_resource(MP) > 7 and (game_state.get_resource(MP)) * 15 - path_risk >= 15:
            gamelib.debug_write("Here16")
            if (game_state.get_resource(SP, 1) > 8):
                start_location, path_risk = self.find_second_best_optimal_path(game_state)
                self.place_and_delete_support_near_scouts(game_state, start_location)
                game_state.attempt_spawn(SCOUT, start_location, math.floor(game_state.get_resource(MP)))
            best_start_location, path_risk = self.select_optimal_path(game_state)
            self.place_and_delete_support_near_scouts(game_state, best_start_location)
            game_state.attempt_spawn(SCOUT, best_start_location, math.floor(game_state.get_resource(MP)))

        if game_state.turn_number == 3 and game_state.get_resource(MP) > 10 and (game_state.get_resource(MP)) * 15 - path_risk >= 15:
            gamelib.debug_write("Here16")
            best_start_location, path_risk = self.select_optimal_path(game_state)
            self.place_and_delete_support_near_scouts(game_state, best_start_location)
            game_state.attempt_spawn(SCOUT, best_start_location, math.floor(game_state.get_resource(MP)))

        initial_turret_locations = [
            [5, 13], [22, 13], [13, 12],
            [4, 13], [23, 13], [14, 12], [3, 13], [24, 13], [12, 12], [2, 13], [25, 13], [15, 12], [12, 12]  # Turret locations
        ]

        for loc in initial_turret_locations:
            # Check if there's a turret at the location and its health
            if game_state.contains_stationary_unit(loc):
                units = game_state.game_map[loc[0], loc[1]]
                for unit in units:
                    if unit.unit_type == TURRET and unit.health < 38:
                        # Remove the turret if its health is less than 38
                        game_state.attempt_remove(loc)
            
            # Spawn and upgrade turrets if resources allow
            if game_state.get_resource(SP) >= 5:  # Cost of upgrading a turret
                game_state.attempt_upgrade(loc)
            if game_state.get_resource(SP) >= 3:  # Cost of placing a turret
                game_state.attempt_spawn(TURRET, loc)
            if game_state.get_resource(SP) >= 5:  # Cost of upgrading a turret
                game_state.attempt_upgrade(loc)

    def setup_defense2(self, game_state: gamelib.GameState):
        sp_reserved_for_support = 4 if self.should_use_support(game_state) else 0
        # Step 1: Place and upgrade initial turrets on the edges
        initial_turret_locations = [
            [5, 13], [22, 13], [13, 12],
            [4, 13], [23, 13], [14, 12], [3, 13], [24, 13], [12, 12], [2, 13], [25, 13], [15, 12], [12, 12]  # Turret locations
        ]
        # Zip the turret and wall locations together and iterate through them
        for turret_loc in initial_turret_locations:
            # Place and upgrade the turret
            # Place and upgrade the wall
            if game_state.get_resource(SP) - sp_reserved_for_support - 3 >= 0:
                game_state.attempt_spawn(TURRET, turret_loc)
            if game_state.get_resource(SP) - sp_reserved_for_support - 5 >= 0:
                game_state.attempt_upgrade(turret_loc)

        
        
        # self.ensure_upgraded_turrets_in_radius(game_state)
  

        # next_turret_locations = [[2, 13], [25, 13]]

        # for loc in next_turret_locations:
        #     if game_state.get_resource(SP) - sp_reserved_for_support - 3 >= 0:  # Cost of placing a wall
        #         game_state.attempt_spawn(TURRET, loc)
                 

        # if self.stored_damaged_location:
        #     self.reinforce_damaged_turret(game_state, self.stored_damaged_location, self.stored_attack_location)

        # # Step 3: Decide whether to place remaining walls based on enemy wall placements
        # if self.should_place_remaining_walls(game_state):
        #     remaining_wall_locations = [
        #         [0, 13], [1, 13], [2, 13], [3, 13],  # Additional left-side walls
        #         [27, 13], [26, 13], [25, 13], [24, 13]  # Additional right-side walls
        #     ]
        #     for wall in remaining_wall_locations:
                    
        #         if game_state.get_resource(SP) - sp_reserved_for_support - 2 >= 0: 
        #             game_state.attempt_spawn(WALL, wall)

        # # Step 4: Place and upgrade additional turrets and walls in a reinforced pattern
        # reinforcement_positions = [
        #     ([12, 12], [14, 11]),  # First left-side reinforcement turret and wall
        #     ([9, 10], [16, 10]),  # First right-side reinforcement turret and wall
        #     ([7, 11], [20, 11]),  # Second left-side reinforcement turret and wall
        #     ([7, 10], [20, 10]),  # Second right-side reinforcement turret and wall
        #     ([8, 10], [8, 9]),   # Third left-side reinforcement turret and wall
        #     ([19, 10], [19, 9]),   # Third right-side reinforcement turret and wall
        #     ([9, 9], [9, 8]),    # Fourth left-side reinforcement turret and wall
        #     ([18, 9], [18, 8]),    # Fourth right-side reinforcement turret and wall
        #     ([5, 12], [5, 11]),  # Additional left-side reinforcement turret and wall
        #     ([22, 12], [22, 11]),  # Additional right-side reinforcement turret and wall
        # ]
        
        # # Loop through reinforcement positions to place and upgrade turrets and walls sequentially
        # for turret_position in reinforcement_positions:
        #     if game_state.get_resource(SP) - sp_reserved_for_support - 3 >= 0: 
        #         game_state.attempt_spawn(TURRET, turret_position)
        #         if game_state.get_resource(SP) - sp_reserved_for_support - 5 >= 0: 
        #             game_state.attempt_upgrade(turret_position)
        

    def should_place_remaining_walls(self, game_state):
        """
        Checks if the enemy has walls in the specified rows to determine
        if we should place the remaining walls.
        """
        # Left side check
        for x in range(0, 4):
            if game_state.contains_stationary_unit([x, 14]):
                return True
        
        # Right side check
        for x in range(23, 27):
            if game_state.contains_stationary_unit([x, 14]):
                return True
        
        # If no walls detected on both sides, do not place remaining walls
        return False

# REAL FANCY STUFF
    def count_turrets_on_path(self, game_state: gamelib.GameState, location):
        """
        Estimate the damage risk on a path by counting the number of enemy turrets that can attack any point along the path.
        """
        try:
            turret_count = 0
            path = game_state.find_path_to_edge(location)
            
            for path_location in path:
                # Get turrets that can attack this path location
                attackers = game_state.get_attackers(path_location, player_index=0)
                for attacker in attackers:
                    if attacker.unit_type == TURRET and attacker.player_index == 1:  # Ensure it's an enemy turret
                        if attacker.upgraded:
                            turret_count += 2  # Heavier weight for upgraded turrets
                        else:
                            turret_count += 1
            
            return turret_count

        except Exception as e:
            gamelib.debug_write(f"Error in count_turrets_on_path: {e}")
            return 100  # Return a high value to indicate a risky path

  
   

    """
    Function Get_Stats Takes in a list of locations (relevant_locations) and possibly a list of other parameters (Need) you can inquire about the base (Health, location of those turrets etc)
     It returns a dictionary with the following keys:
    1. 'Enemy Damage' = Damage to Expect from enemy turrets at each of those locations
    2. 'Our Damage' = Damage we can deal to enemy mobile units from our turrets  at each of those locations
    3. 'Enemy Support' = 'Total support the enemy can provide to each unit at each location
    4. 'Our Support' = 'Total support we can provide to each unit at each location
    """

    def Get_Stats(self, game_state, relevant_locations, Need=None):
        DE, DU, SE, SU, enemy_T = self.Map_Entire_Base(game_state, relevant_locations)
        Damage_And_Support = {
            'Enemy Damage': DE,
            'Our Damage': DU,
            'Enemy Support': SE,
            'Our Support': SU
        }
        return Damage_And_Support

    def Map_Entire_Base(self, game_state, relevant_locations):
        Damage_By_Enemy = [0] * len(relevant_locations)
        Support_By_Us = [0] * len(relevant_locations)
        Support_by_Enemy = [0] * len(relevant_locations)
        Damage_By_Us = [0] * len(relevant_locations)
        list_of_enemy = []
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    for locs in relevant_locations:
                        if unit.unit_type == "DF" and unit.player_index == 1 and game_state.game_map.distance_between_locations(
                                location, locs) <= unit.attackRange:  # Enemy Turret
                            Damage_By_Enemy[relevant_locations.index(locs)] += 32 if unit.upgraded else 16
                            list_of_enemy.append(unit)
                        elif unit.unit_type == "EF" and unit.player_index == 0 and game_state.game_map.distance_between_locations(
                                location, locs) <= unit.shieldRange:  # Friendly Support
                            Support_By_Us[relevant_locations.index(locs)] += unit.shieldPerUnit + 0.34 * unit.y
                        elif unit.unit_type == "EF" and unit.player_index == 1 and game_state.game_map.distance_between_locations(
                                location, locs) <= unit.shieldRange:  # Enemy Support
                            Support_by_Enemy[relevant_locations.index(locs)] += unit.shieldPerUnit + 0.34 * (
                                        27 - unit.y)
                        elif unit.unit_type == "DF" and unit.player_index == 0 and game_state.game_map.distance_between_locations(
                                location, locs) <= unit.attackRange:  # Friendly Turret
                            Damage_By_Us[relevant_locations.index(locs)] += 32 if unit.upgraded else 16
        return Damage_By_Enemy, Damage_By_Us, Support_by_Enemy, Support_By_Us, list_of_enemy

    def on_action_frame(self, turn_string):
        state = json.loads(turn_string)
        events = state["events"]
        attacks = events.get("attack", [])
        self.breaches = events.get("breach", [])

        # Track where our defenses take damage
        for attack in attacks:
            attacker_location = attack[0]
            target_location = attack[1]
            attacker_unit_type = attack[3]
            attacking_player = attack[6]

            if attacking_player == 2 and attacker_unit_type == 3:  # The enemy is attacking us
                # Record the first damaged location if not already set
                if self.first_damaged_location is None:
                    self.first_damaged_location = target_location
                    self.first_attacker_location = attacker_location

                # Always update the stored damage and attack locations
                self.stored_damaged_location = target_location
                self.stored_attack_location = attacker_location


                # Detect the attack and reset the turn counter
                self.last_attack_detected = True
                self.turns_since_last_attack = 0

                # Log this event for debugging purposes
                gamelib.debug_write(f"First hit recorded at {target_location} by an attacker from {attacker_location}")

        for breach in self.breaches:
            self.got_breached = True
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            damage = breach[1]
            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                self.breached_location = location
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(self.scored_on_locations))
                self.damage_taken = damage
                self.breach_count += 1

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()