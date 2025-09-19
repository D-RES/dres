#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
`ev_optimise.py`
{DESCRIPTION TO FOLLOW}
"""


###############################################################################################################
# Standard Python Libraries
import os
import numpy as np
import pandas as pd
from pypsa import Network
from datetime import datetime
import json
import random

# Custom Libraries
from .dafni_utilities import performance, message_api


###############################################################################################################
# PM

def load_ev_schedule_data(INPUT_FOLDER, filename):
    """
    Function description to follow.
    """
    t0 = performance()


    # Full path to file
    full_filename = os.path.join(INPUT_FOLDER, filename)
    
    # Open csv
    df = pd.read_csv(full_filename)

    # Create column with complete DateTime obj for Arrival and Departure
    try:
        # Spaghetti model
        df['Departure DateTime'] = [pd.to_datetime(f"2019-01-01 {row['Departure Time']}") + pd.Timedelta(days=row.Day-1) for (i,row) in df.iterrows()]
        df['Arrival DateTime'] = [pd.to_datetime(f"2019-01-01 {row['Arrival Time']}") + pd.Timedelta(days=row.Day-1) for (i,row) in df.iterrows()]
    except:
        # Data
        df['Start Date'] = pd.to_datetime(df['Start Date'])
        df['End Date'] = pd.to_datetime(df['End Date'])
    
    performance(t0)
    return df

def ev_scheduling_setup(INPUT_FOLDER, filename):
    """
    Function description to follow.
    """
    t0 = performance()


    message_api(msg="# Full path to file")
    # Full path to file
    full_filename = os.path.join(INPUT_FOLDER, filename)
    
    message_api(msg="# Open csv")
    # Open csv
    df = pd.read_csv(full_filename)

    departure_full_times = pd.to_datetime(df.iloc[:, 7], errors='coerce')
    arrival_full_times = pd.to_datetime(df.iloc[:, 8], errors='coerce')
    message_api(msg="# Some measure of energy consumption")
    column_7 = df.iloc[:, 6].values  # Some measure of energy consumption

    hours = np.arange(24)
    connected_cars = []

    message_api(msg="# For each hour, count how many cars are connected and can participate in V2G.")
    # For each hour, count how many cars are connected and can participate in V2G.
    for t in range(24):
        num_connected = 0
        for i in range(len(departure_full_times)):
            departure_hour = departure_full_times.iloc[i].hour
            arrival_hour = arrival_full_times.iloc[i].hour
            # Car not connected exactly at its departure or arrival hour
            if t == departure_hour or t == arrival_hour:
                continue
            else:
                num_connected += 1
        connected_cars.append(num_connected)

    connected_cars = np.array(connected_cars)

    message_api(msg="# Max charge/discharge power per vehicle (MW), if ENV exists, is this value, otherwise default to 0.011")
    vehicle_power = float(os.getenv("vehicle_power", 0.011))  # Max charge/discharge power per vehicle (MW), if ENV exists, is this value, otherwise default to 0.011
    message_api(msg="# Negative: max charging")
    lb_array = -connected_cars * vehicle_power  # Negative: max charging
    message_api(msg="# Positive: max discharging")
    ub_array = connected_cars * vehicle_power   # Positive: max discharging

    message_api(msg="# Calculate delta_soc to account for SOC changes due to trips")
    # Calculate delta_soc to account for SOC changes due to trips
    delta_soc = np.zeros(24)
    for t in hours:
        soc_change = 0
        for i in range(len(departure_full_times)):
            departure_hour = departure_full_times[i].hour
            arrival_hour = arrival_full_times[i].hour
            soc_consumption = column_7[i]/2/235
            if t == departure_hour:
                soc_change -= soc_consumption
            if t == arrival_hour:
                soc_change -= soc_consumption
        delta_soc[t] = soc_change

    performance(t0)
    return lb_array, ub_array, delta_soc, vehicle_power, connected_cars


###############################################################################################################
# KQ

def simulate_evs(network, INPUT_FOLDER, assets):
    """
    Function description to follow.
    """    
    t0 = performance()


    # Gets a list of all bus bars
    buses = network.buses.index.tolist()
    # Select a specific three bus bars
    selected_buses = ['KIRKWA1A']  # 'KIRKWA3A','KIRKWA1B'
    # Calculate the number of electric vehicles assigned to each bus bar
    total_ev = 235  # 235， 5625，11250，22500
    num_buses = len(selected_buses)
    # The number of electric vehicles assigned to each bus
    ev_per_bus = total_ev // num_buses
    # Residual electric vehicles (after equal distribution)
    remaining_ev = total_ev % num_buses

    # Define the parameters of an electric vehicle (assuming every electric vehicle is the same)
    ev_capacity = 0.075  # Battery capacity per electric vehicle (MWh)0.075
    # The maximum charging power (MW) of each EV is 0.022
    ev_charge_power = 0.007
    efficiency_store = 0.9  # Charging efficiency
    efficiency_dispatch = 0.9  # Discharge efficiency
    min_soc = 0.1  # Minimum SOC
    max_soc = 0.9  # Maximum SOC

    # Create a DataFrame to store the time series charge-discharge behavior of all vehicles

    p_set = pd.DataFrame(index=network.snapshots)
    q_set = pd.DataFrame(index=network.snapshots)
    # Set reactive power by power factor
    pf = 0.95  # Set power factor

    # Set charging period and discharging period
    charge_period_1_start = datetime.strptime(
        '1/1/2019 01:00', '%m/%d/%Y %H:%M')
    charge_period_1_end = datetime.strptime(
        '1/1/2019 10:00', '%m/%d/%Y %H:%M')  # 12

    charge_period_2_start = datetime.strptime(
        '1/2/2019 12:00', '%m/%d/%Y %H:%M')
    charge_period_2_end = datetime.strptime('1/2/2019 23:59', '%m/%d/%Y %H:%M')

    file_path = f"{INPUT_FOLDER}processed_ev_usage.csv"
    df = pd.read_csv(file_path)
    # Gets the data for columns 3, 7, 8 and 9 of the table
    departure_full_times = pd.to_datetime(df.iloc[:, 7], errors='coerce')
    arrival_full_times = pd.to_datetime(df.iloc[:, 8], errors='coerce')
    column_3 = df.iloc[:, 2].values
    column_7 = df.iloc[:, 6].values
    matrixSOC = np.column_stack((column_3, column_7))
    # message_api(departure_full_times)
    # message_api(matrixSOC)
    # Traverse all bus lines and add electric vehicle energy storage units
    for i, bus in enumerate(selected_buses):
        # Calculate the number of electric vehicles on the bus
        # ev_per_bus + (1 if i < remaining_ev else 0)  # 将剩余的电动汽车逐个分配到前面的母线上
        num_ev_for_bus = total_ev

        # Create an energy storage unit for each electric vehicle on the bus
        for j in range(num_ev_for_bus):
            # Create a unique name for each electric vehicle
            ev_name = f"EV_{bus}_{j + 1}"
            # Get the initial SOC
            soc = matrixSOC[j, 0]
            # Add energy storage units to the network to simulate electric vehicles
            network.add("StorageUnit",
                        name=ev_name,
                        bus=bus,
                        control='PQ',  # Operate in PQ mode
                        p_nom=ev_charge_power,  # The maximum charge/discharge power of each electric vehicle
                        # energy_nom=ev_capacity,  # The battery capacity of each electric vehicle
                        efficiency_store=efficiency_store,  # Charging efficiency
                        efficiency_dispatch=efficiency_dispatch,  # Discharge efficiency
                        # The time required for the battery to be fully charged
                        max_hours=ev_capacity / ev_charge_power,
                        state_of_charge_initial=soc,  # Initial charging state
                        cyclic_state_of_charge=True)  # Cyclic charge and discharge state

            # Initialize the charging and discharging time series of the energy storage unit
            departure_time = departure_full_times.iloc[j]
            arrival_time = arrival_full_times.iloc[j]
            charge_discharge_profile = []
            charge_period_1_start = datetime.strptime(
                '1/1/2019 00:00', '%m/%d/%Y %H:%M')
            # charge_period_1_end = datetime.strptime('1/1/2019 10:00', '%m/%d/%Y %H:%M')
            charge_period_1_end = datetime.strptime(
                departure_time.strftime('%m/%d/%Y %H:%M'), '%m/%d/%Y %H:%M')
            charge_period_2_start = datetime.strptime(
                arrival_time.strftime('%m/%d/%Y %H:%M'), '%m/%d/%Y %H:%M')
            # charge_period_2_start = datetime.strptime('1/2/2019 12:00', '%m/%d/%Y %H:%M')
            charge_period_2_end = datetime.strptime(
                '1/2/2019 23:59', '%m/%d/%Y %H:%M')
            # Calculate the charge and discharge behavior for 24 hours and adjust the power per hour according to the SOC
            for t in range(len(network.snapshots)):

                current_time = datetime.strptime(
                    network.snapshots[t], '%m/%d/%Y %H:%M')
                if charge_period_1_start <= current_time < charge_period_1_end:
                    #
                    if soc < max_soc:
                        # The charging power is negative
                        power = -min(ev_charge_power, (max_soc-soc)
                                     * ev_capacity/efficiency_store)
                        # Update SOC (Charge to increase SOC)
                        soc = min(max_soc, soc - power *
                                  efficiency_store / ev_capacity)
                    else:
                        power = 0  #
                elif charge_period_2_start <= current_time < charge_period_2_end:
                    #
                    if current_time == charge_period_2_start:
                        soc = soc-matrixSOC[j, 1]
                    if soc < max_soc:
                        # The charging power is negative
                        power = -min(ev_charge_power, (max_soc-soc)
                                     * ev_capacity/efficiency_store)
                        # Update SOC (Charge to increase SOC)
                        soc = min(max_soc, soc - power *
                                  efficiency_store / ev_capacity)
                    else:
                        power = 0  # full
                else:
                    power = 0  #

                # Add the hourly charge and discharge power to the time series
                charge_discharge_profile.append(power)

            # Save the charge-discharge time series to the DataFrame
            p_set[ev_name] = charge_discharge_profile
            q_set[ev_name] = p_set[ev_name] * np.tan(np.arccos(pf))

        # Set the charging and discharging behavior of the energy storage unit
    network.storage_units_t.p_set = p_set
    network.storage_units_t.q_set = q_set
    # Print result
    # for ev_name in p_set.columns:
        # message_api(f"{ev_name} charge and discharge behavior：")
        # message_api(p_set[ev_name])

    #
    # message_api(network.storage_units_t.p_set)
    performance(t0)


class GWO:
    def __init__(self, 
                pop_size = 10,                  # Named arguments with defaults
                dim = 24,
                max_iter = 10,
                initial_soc = 0.3,
                delta_t = 1,
                capacity = 16.45,
                min_soc = 0.1,
                max_soc = 0.9,
                vehicle_power = 0.011,
                lb_array = None,                # skip defaults for array arguments
                ub_array = None,
                charging_price = None,
                discharging_price = None,
                delta_soc = None,
                network = None
            ):
        self.pop_size = pop_size
        self.dim = dim
        self.max_iter = max_iter
        self.lb_array = lb_array
        self.ub_array = ub_array
        self.initial_soc = initial_soc
        self.delta_t = delta_t
        self.capacity = capacity
        self.min_soc = min_soc
        self.max_soc = max_soc
        self.charging_price = charging_price
        self.discharging_price = discharging_price
        self.delta_soc = delta_soc
        self.network = network
        self.vehicle_power = vehicle_power

        # Initialize leader wolves
        self.alpha_score = float("inf")
        self.alpha_pos = np.zeros(dim)
        self.beta_score = float("inf")
        self.beta_pos = np.zeros(dim)
        self.delta_score = float("inf")
        self.delta_pos = np.zeros(dim)
        
        self.best_scores = []
        self.optimal_voltage_variation = None
        self.optimal_total_cost = None
        self.archive = []  # Store non-dominated solutions

    def initialize_wolves(self):
        """
        Function description to follow.
        """
        t0 = performance()
        
        # Random initialization within bounds
        wolves = np.random.uniform(self.lb_array, self.ub_array, (self.pop_size, self.dim))
        # Try loading a previously saved best solution as a starting point
        try:
            with open("best_result_oneday_extreme_V2G.json", 'r') as file:
                best_result = json.load(file)
                wolves[0] = np.array(best_result)
                # message_api("Loaded best result as initial position.")
        except FileNotFoundError:
            # message_api("No previous best result found.")
            None
        
        # Apply SOC constraints
        for i in range(len(wolves)):
            wolves[i] = self.apply_soc_constraints(wolves[i])
        
        performance(t0)
        return wolves

    def objective_function(self, power_schedule):
        """
        Function description to follow.
        """
        t0 = performance()
        
        # Evaluate the power schedule:
        # 1. Apply SOC constraints
        # 2. Run power flow on a copy of the network
        # 3. Compute voltage deviation and cost

        # network = self.network    
        soc = self.initial_soc
        total_cost = 0

        # Update SOC and cost for each hour
        for t in range(self.dim):
            soctemporary = soc
            soc -= (power_schedule[t] * self.delta_t) / self.capacity
            if soc < self.min_soc and power_schedule[t] > 0:
                soc = np.clip(soc, self.min_soc, self.max_soc)
                power_schedule[t] = (soctemporary - soc) * self.capacity / self.delta_t
                soc = soctemporary - (power_schedule[t] * self.delta_t) / self.capacity
            elif soc > self.max_soc and power_schedule[t] < 0:
                soc = np.clip(soc, self.min_soc, self.max_soc)
                power_schedule[t] = (soctemporary - soc) * self.capacity / self.delta_t
                soc = soctemporary - (power_schedule[t] * self.delta_t) / self.capacity
            # Calculate charge and discharge costs per hour
            soc += self.delta_soc[t] # Add SOC changes for vehicle departure or arrival
            if power_schedule[t] < 0:  # Charging cost
                total_cost += abs(power_schedule[t]) * self.charging_price[t]
            else:  # Discharge revenue
                total_cost -= abs(power_schedule[t]) * self.discharging_price[t]

        # Set EV schedule to storage unit and run PF
        self.network.storage_units_t.p_set.loc[:, "KIRKWA3A_Storage"] = power_schedule
        # message_api("BREAKPOINT")
        self.network.pf()

        # Voltage deviation calculation:
        # Example: sum of (v - 1)^3 over time at a certain bus (KIRKWA3A)
        voltage_deviation = (self.network.buses_t.v_mag_pu["KIRKWA3A"] - 1)**4
        voltage_variation = voltage_deviation.sum()
        
        # Return two objectives: (voltage_variation, total_cost)
        
        performance(t0)
        return np.array([voltage_variation, total_cost])

    def pareto_sort(self, objectives):
        """
        Function description to follow.
        """
        t0 = performance()
        
        # Perform non-dominated sorting to classify solutions into Pareto fronts
        num_individuals = len(objectives)
        domination_counts = np.zeros(num_individuals, dtype=int)
        dominated_sets = [[] for _ in range(num_individuals)]
        pareto_fronts = [[]]

        for p in range(num_individuals):
            for q in range(num_individuals):
                if self.dominates(objectives[p], objectives[q]):
                    dominated_sets[p].append(q)
                elif self.dominates(objectives[q], objectives[p]):
                    domination_counts[p] += 1
            if domination_counts[p] == 0:
                pareto_fronts[0].append(p)

        i=0
        while pareto_fronts[i]:
            next_front = []
            for p in pareto_fronts[i]:
                for q in dominated_sets[p]:
                    domination_counts[q] -= 1
                    if domination_counts[q] == 0:
                        next_front.append(q)
            i+=1
            pareto_fronts.append(next_front)
        
        performance(t0)
        return pareto_fronts[:-1]

    def dominates(self, ind1, ind2):
        """
        Function description to follow.
        """
        # t0 = performance()
        
        # ind1 dominates ind2 if ind1 is strictly better in at least one objective and not worse in others
        result = all(x<=y for x,y in zip(ind1,ind2)) and any(x<y for x,y in zip(ind1,ind2))
        # performance(t0)
        return result

    def calculate_crowding_distance(self, objectives):
        """
        Function description to follow.
        """
        t0 = performance()
        
        # For handling diversity in solutions on Pareto front
        num_individuals = len(objectives)
        num_objectives = len(objectives[0])
        distances = np.zeros(num_individuals)
        for i in range(num_objectives):
            obj_values = np.array([obj[i] for obj in objectives])
            sorted_indices = np.argsort(obj_values)
            max_val = obj_values[sorted_indices[-1]]
            min_val = obj_values[sorted_indices[0]]
            distances[sorted_indices[0]] = distances[sorted_indices[-1]] = 1e6
            if max_val == min_val: 
                continue
            for j in range(1, num_individuals-1):
                distances[sorted_indices[j]] += (obj_values[sorted_indices[j+1]] - obj_values[sorted_indices[j-1]])/(max_val - min_val)
        
        performance(t0)
        return distances

    def select_alpha_beta_delta(self, wolves, objectives, pareto_fronts):
        """
        Function description to follow.
        """
        t0 = performance()
        
        # Select the top three wolves (alpha, beta, delta) considering rank, crowding, and distance to ideal point
        num_individuals = len(objectives)
        domination_ranks = np.zeros(num_individuals)
        for rank, front in enumerate(pareto_fronts):
            for idx in front:
                domination_ranks[idx] = rank

        crowding_distances = self.calculate_crowding_distance(objectives)
        objectives_array = np.array(objectives)
        message_api(msg=f"objectives_array = {objectives_array}")
        ideal_point = np.min(objectives_array, axis=0)
        message_api(msg=f"ideal_point = {ideal_point}")
        distances_to_ideal = np.linalg.norm(objectives_array - ideal_point, axis=1)
        message_api(msg=f"distances_to_ideal = {distances_to_ideal}")

        norm_domination = (domination_ranks - domination_ranks.min())/(domination_ranks.max()-domination_ranks.min()+1e-9)
        message_api(msg=f"norm_domination = {norm_domination}")
        norm_crowding = (crowding_distances - crowding_distances.min())/(crowding_distances.max()-crowding_distances.min()+1e-9)
        message_api(msg=f"norm_crowding = {norm_crowding}")
        norm_distance = (distances_to_ideal - distances_to_ideal.min())/(distances_to_ideal.max()-distances_to_ideal.min()+1e-9)
        message_api(msg=f"norm_distance = {norm_distance}")

        # Weighted combination to identify top solutions
        w1, w2, w3 = 0.5, -0.2, 0.5
        message_api(msg=f"w1, w2, w3 = {w1}, {w2}, {w3}")
        overall_scores = w1*norm_domination + w2*norm_crowding + w3*norm_distance
        message_api(msg=f"overall_scores = {overall_scores}")
        sorted_indices = np.argsort(overall_scores)
        message_api(msg=f"sorted_indices = {sorted_indices}")
        alpha_idx, beta_idx, delta_idx = sorted_indices[0], sorted_indices[1], sorted_indices[2]
        message_api(msg=f"alpha_idx, beta_idx, delta_idx = {alpha_idx}, {beta_idx}, {delta_idx}")
        
        performance(t0)
        return wolves[alpha_idx], wolves[beta_idx], wolves[delta_idx]

    def optimize(self):
        """
        Function description to follow.
        """
        t0 = performance()
        
        wolves = self.initialize_wolves()
        for iter in range(self.max_iter):
            # message_api(f"Generation {iter+1}/{self.max_iter}")
            objectives = np.array([self.objective_function(wolf) for wolf in wolves])
            pareto_fronts = self.pareto_sort(objectives.tolist())

            self.archive = self.update_external_archive(self.archive, wolves, objectives)
            self.alpha_pos, self.beta_pos, self.delta_pos = self.select_alpha_beta_delta(wolves, objectives, pareto_fronts)

            a = 2 - iter*(2/self.max_iter)

            # Update wolves positions
            for i in range(self.pop_size):
                for j in range(self.dim):
                    r1 = np.random.rand()
                    r2 = np.random.rand()

                    A1 = 2*a*r1 - a
                    C1 = 2*r2
                    D_alpha = abs(C1*self.alpha_pos[j]-wolves[i][j])
                    X1 = self.alpha_pos[j]-A1*D_alpha

                    r1 = np.random.rand()
                    r2 = np.random.rand()
                    A2 = 2*a*r1 - a
                    C2 = 2*r2
                    D_beta = abs(C2*self.beta_pos[j]-wolves[i][j])
                    X2 = self.beta_pos[j]-A2*D_beta

                    r1 = np.random.rand()
                    r2 = np.random.rand()
                    A3 = 2*a*r1 - a
                    C3 = 2*r2
                    D_delta = abs(C3*self.delta_pos[j]-wolves[i][j])
                    X3 = self.delta_pos[j]-A3*D_delta

                    wolves[i][j] = (X1+X2+X3)/3

                wolves[i] = self.apply_soc_constraints(wolves[i])

        
        performance(t0)
        return self.archive

    def apply_soc_constraints(self, power_schedule):
        """
        Function description to follow.
        """
        t0 = performance()
        
        # Adjust power schedule to ensure final SOC and no violations
        soc = self.initial_soc
        final_soc = 0.9
        for t in range(len(power_schedule)):
            power_schedule[t] = np.clip(power_schedule[t], self.lb_array[t], self.ub_array[t])
            soctemp = soc
            soc_difference = final_soc - soctemp
            power_gap = soc_difference*self.capacity/self.delta_t

            # Adjust based on final SOC target and power limits
            if power_gap > 0:
                m = int(power_gap/(self.vehicle_power*235))+1
                if (t+m)>=23:
                    if abs(power_schedule[t])<(power_gap-(m-1)*(self.vehicle_power*235)) or abs(power_schedule[t])>(self.vehicle_power*235):
                        power_schedule[t] = -random.uniform((power_gap-(m-1)*(self.vehicle_power*235)), (self.vehicle_power*235))
                    if t==23:
                        power_schedule[t] = -power_gap
            else:
                m = int(power_gap/(self.vehicle_power*235))-1
                if (t+abs(m))>=23:
                    if abs(power_schedule[t])<(power_gap-(m-1)*(self.vehicle_power*235)) or abs(power_schedule[t])>(self.vehicle_power*235):
                        power_schedule[t] = random.uniform((abs(power_gap)-(abs(m)-1)*(self.vehicle_power*235)),(self.vehicle_power*235))
                    if t==23:
                        power_schedule[t] = abs(power_gap)

            soc -= (power_schedule[t]*self.delta_t)/self.capacity
            if soc<self.min_soc and power_schedule[t]>0:
                soc = np.clip(soc, self.min_soc, self.max_soc)
                power_schedule[t]=(soctemp-soc)*self.capacity/self.delta_t
            elif soc>self.max_soc and power_schedule[t]<0:
                soc = np.clip(soc, self.min_soc, self.max_soc)
                power_schedule[t]=(soctemp-soc)*self.capacity/self.delta_t

            soc += self.delta_soc[t]
        
        performance(t0)
        return power_schedule

    def update_external_archive(self, archive, wolves, objectives, max_size=100):
        """
        Function description to follow.
        """
        t0 = performance()
        
        # Keep non-dominated solutions in an external archive
        combined_positions = list(wolves) + [ind['position'] for ind in archive]
        combined_objectives = objectives.tolist() + [ind['objective'] for ind in archive]

        pareto_fronts = self.pareto_sort(combined_objectives)
        new_archive = []
        for front in pareto_fronts:
            for idx in front:
                individual = {'position': combined_positions[idx], 'objective': combined_objectives[idx]}
                new_archive.append(individual)
            if len(new_archive)>=max_size:
                break

        if len(new_archive)>max_size:
            distances = self.calculate_crowding_distance([ind['objective'] for ind in new_archive])
            sorted_indices = np.argsort(-np.array(distances))
            new_archive = [new_archive[i] for i in sorted_indices[:max_size]]

        
        performance(t0)
        return new_archive




def save_pareto_front(pareto_front, filename="pareto_front_extreme_V2G.csv"):
    """
    Function description to follow.
    """
    t0 = performance()
    
    positions = [ind['position'] for ind in pareto_front]
    objectives = [ind['objective'] for ind in pareto_front]

    df_positions = pd.DataFrame(positions)
    df_objectives = pd.DataFrame(objectives, columns=['Voltage Variation','Cost'])
    df_pareto = pd.concat([df_positions, df_objectives], axis=1)
    df_pareto.to_csv(filename, index=False)
    # message_api(f"Pareto front data saved to {filename}")
    
    performance(t0)


def select_closest_to_ideal(pareto_front):
    """
    Function description to follow.
    """
    t0 = performance()
    
    objectives = np.array([sol['objective'] for sol in pareto_front])
    min_obj = objectives.min(axis=0)
    max_obj = objectives.max(axis=0)
    ranges = max_obj - min_obj
    ranges[ranges==0] = 1
    normalized_objectives = (objectives - min_obj)/ranges
    ideal_point = np.zeros(objectives.shape[1])
    distances = np.linalg.norm(normalized_objectives - ideal_point, axis=1)
    best_index = np.argmin(distances)
    
    performance(t0)
    return pareto_front[best_index]


