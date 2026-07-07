import os
import math
import time
import uuid
import datetime
import gc
import openpyxl
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class OptimizerService:
    @staticmethod
    def calculate_haversine_distance(node1: Dict[str, Any], node2: Dict[str, Any]) -> float:
        R = 6371.0  # Earth's radius in kilometers
        lat1 = math.radians(node1.get('lat', 0.0))
        lon1 = math.radians(node1.get('lng', 0.0))
        lat2 = math.radians(node2.get('lat', 0.0))
        lon2 = math.radians(node2.get('lng', 0.0))
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @staticmethod
    def parse_excel_nodes(file_path: str) -> List[Dict[str, Any]]:
        df = pd.read_excel(file_path)
        nodes = []
        
        def clean_str(val, default=''):
            if pd.isna(val):
                return default
            return str(val).strip()
            
        def clean_float(val, default=0.0):
            if pd.isna(val):
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        # Group by node_id preserving order of appearance
        grouped = df.groupby('node_id', sort=False)
        
        for node_id, group in grouped:
            if pd.isna(node_id) or not str(node_id).strip():
                continue
            
            node_id = str(node_id).strip()
            first_row = group.iloc[0]
            node_type = clean_str(first_row.get('type')).lower()
            
            raw_lat = None
            raw_lng = None
            for col in first_row.index:
                col_lower = str(col).lower().strip()
                if col_lower in ('lat', 'latitude'):
                    raw_lat = first_row[col]
                elif col_lower in ('lng', 'long', 'longitude'):
                    raw_lng = first_row[col]
                    
            node = {
                'id': node_id,
                'name': clean_str(first_row.get('name'), node_id),
                'type': node_type,
                'subtype': clean_str(first_row.get('subtype')),
                'lat': clean_float(raw_lat) if raw_lat is not None else clean_float(first_row.get('lat')),
                'lng': clean_float(raw_lng) if raw_lng is not None else clean_float(first_row.get('lng')),
                'network_id': clean_str(first_row.get('network_id'))
            }
            
            if node_type == 'farmer':
                supply_dict = {}
                for _, row in group.iterrows():
                    commodity = clean_str(row.get('commodity'))
                    supply = clean_float(row.get('supply'))
                    if commodity and supply > 0:
                        supply_dict[commodity] = supply_dict.get(commodity, 0.0) + supply
                node['products'] = [{'type': k, 'supply': v} for k, v in supply_dict.items()]
                
            elif node_type == 'hub':
                products_dict = {}
                for _, row in group.iterrows():
                    commodity = clean_str(row.get('commodity'))
                    capacity = clean_float(row.get('capacity'))
                    cost = clean_float(row.get('cost'))
                    if commodity and capacity > 0:
                        if commodity not in products_dict:
                            products_dict[commodity] = {'capacity': 0.0, 'processing_cost': cost}
                        products_dict[commodity]['capacity'] += capacity
                        products_dict[commodity]['processing_cost'] = cost
                node['products'] = [{
                    'type': k,
                    'capacity': v['capacity'],
                    'processing_cost': v['processing_cost']
                } for k, v in products_dict.items()]
                
            elif node_type == 'plant':
                inflow_dict = {}
                yield_dict = {}
                demand_dict = {}
                for _, row in group.iterrows():
                    commodity = clean_str(row.get('commodity'))
                    capacity = clean_float(row.get('capacity'))
                    cost = clean_float(row.get('cost'))
                    yield_val = clean_float(row.get('yield'))
                    demand = clean_float(row.get('demand'))
                    price = clean_float(row.get('price'))
                    
                    if capacity > 0 and commodity:
                        if commodity not in inflow_dict:
                            inflow_dict[commodity] = {'capacity': 0.0, 'processing_cost': cost}
                        inflow_dict[commodity]['capacity'] += capacity
                        inflow_dict[commodity]['processing_cost'] = cost
                    if yield_val > 0 and commodity:
                        yield_dict[commodity] = yield_dict.get(commodity, 0.0) + yield_val
                    if demand > 0 and commodity:
                        if commodity not in demand_dict:
                            demand_dict[commodity] = {'demand': 0.0, 'price': price, 'processing_cost': cost}
                        demand_dict[commodity]['demand'] += demand
                        demand_dict[commodity]['price'] = price
                        demand_dict[commodity]['processing_cost'] = cost
                
                node['inflow_milks'] = [{
                    'type': k,
                    'capacity': v['capacity'],
                    'processing_cost': v['processing_cost']
                } for k, v in inflow_dict.items()]
                node['products'] = [{'type': k, 'yield': v} for k, v in yield_dict.items()]
                node['demands'] = [{
                    'type': k,
                    'demand': v['demand'],
                    'price': v['price'],
                    'processing_cost': v['processing_cost']
                } for k, v in demand_dict.items()]
                node['capacity'] = sum(m['capacity'] for m in node['inflow_milks']) if node['inflow_milks'] else sum(d['demand'] for d in node['demands'])
                node['processing_cost'] = node['inflow_milks'][0]['processing_cost'] if node['inflow_milks'] else (node['demands'][0]['processing_cost'] if node['demands'] else 0.40)
                
            elif node_type == 'geography':
                demand_dict = {}
                for _, row in group.iterrows():
                    commodity = clean_str(row.get('commodity'))
                    demand = clean_float(row.get('demand'))
                    price = clean_float(row.get('price'))
                    if commodity and demand > 0:
                        if commodity not in demand_dict:
                            demand_dict[commodity] = {'demand': 0.0, 'price': price}
                        demand_dict[commodity]['demand'] += demand
                        demand_dict[commodity]['price'] = price
                node['products'] = [{
                    'type': k,
                    'demand': v['demand'],
                    'price': v['price']
                } for k, v in demand_dict.items()]
                
            nodes.append(node)
        return nodes

    @staticmethod
    def parse_bmc_vehicles(excel_file_path: str) -> Dict[str, Any]:
        vehicle_limits_map = {}
        if not excel_file_path or not os.path.exists(excel_file_path):
            return vehicle_limits_map
            
        try:
            xl = pd.ExcelFile(excel_file_path)
            sheet_name = None
            for s in xl.sheet_names:
                if s.lower().strip() in ('vehicle allocation', 'vehicle_allocation'):
                    sheet_name = s
                    break
            if not sheet_name:
                for s in xl.sheet_names:
                    if s.lower().strip() in ('bmcvechicle', 'bmcvehicle'):
                        sheet_name = s
                        break
                        
            if sheet_name:
                df_veh = xl.parse(sheet_name)
                id_col = None
                for col in df_veh.columns:
                    col_lower = str(col).lower().strip()
                    if col_lower in ('bmc id', 'bmc_id', 'node_id', 'id', 'node id'):
                        id_col = col
                        break
                if not id_col and len(df_veh.columns) > 0:
                    id_col = df_veh.columns[0]
                    
                if id_col:
                    col_10 = next((c for c in df_veh.columns if '10 l' in str(c).lower() and 'leave' not in str(c).lower()), None)
                    col_12 = next((c for c in df_veh.columns if ('12l' in str(c).lower() or '12 l' in str(c).lower()) and 'leave' not in str(c).lower()), None)
                    col_15 = next((c for c in df_veh.columns if '15 l' in str(c).lower() and 'leave' not in str(c).lower()), None)
                    col_18 = next((c for c in df_veh.columns if '18 l' in str(c).lower() and 'leave' not in str(c).lower()), None)
                    
                    col_lq_10 = next((c for c in df_veh.columns if '10 l' in str(c).lower() and 'leave' in str(c).lower()), None)
                    col_lq_12 = next((c for c in df_veh.columns if ('12l' in str(c).lower() or '12 l' in str(c).lower()) and 'leave' in str(c).lower()), None)
                    col_lq_15 = next((c for c in df_veh.columns if '15 l' in str(c).lower() and 'leave' in str(c).lower()), None)
                    col_lq_18 = next((c for c in df_veh.columns if '18 l' in str(c).lower() and 'leave' in str(c).lower()), None)
                    
                    col_strat = next((c for c in df_veh.columns if 'strategy' in str(c).lower()), None)
                    col_margin_low = next((c for c in df_veh.columns if 'flowlowmargin' in str(c).lower().replace(' ', '').replace('_', '')), None)
                    col_margin_high = next((c for c in df_veh.columns if 'flowhighmargin' in str(c).lower().replace(' ', '').replace('_', '')), None)
                    col_supplier = next((c for c in df_veh.columns if 'supplier' in str(c).lower()), None)
                    if not col_supplier:
                        has_subcluster = any('subcluster' in str(c).lower().replace(' ', '').replace('_', '') for c in df_veh.columns)
                        if has_subcluster:
                            col_supplier = next((c for c in df_veh.columns if 'cluster' in str(c).lower() and 'sub' not in str(c).lower()), None)

                    col_cluster = next((c for c in df_veh.columns if 'subcluster' in str(c).lower().replace(' ', '').replace('_', '')), None)
                    if not col_cluster:
                        col_cluster = next((c for c in df_veh.columns if 'cluster' in str(c).lower() and c != col_supplier), None)
                    
                    for _, row in df_veh.iterrows():
                        bmc_id = str(row[id_col]).strip()
                        if bmc_id and bmc_id.lower() != 'nan':
                            limits = {
                                '10 L': float(row[col_10]) if col_10 and pd.notna(row[col_10]) else 1000.0,
                                '12L': float(row[col_12]) if col_12 and pd.notna(row[col_12]) else 1000.0,
                                '15 L': float(row[col_15]) if col_15 and pd.notna(row[col_15]) else 1000.0,
                                '18 L': float(row[col_18]) if col_18 and pd.notna(row[col_18]) else 1000.0
                            }
                            lq_10 = float(row[col_lq_10]) if col_lq_10 and pd.notna(row[col_lq_10]) else 0.0
                            lq_12 = float(row[col_lq_12]) if col_lq_12 and pd.notna(row[col_lq_12]) else 0.0
                            lq_15 = float(row[col_lq_15]) if col_lq_15 and pd.notna(row[col_lq_15]) else 0.0
                            lq_18 = float(row[col_lq_18]) if col_lq_18 and pd.notna(row[col_lq_18]) else 0.0
                            
                            strategy = str(row[col_strat]).strip() if col_strat and pd.notna(row[col_strat]) else "Whole Milk Supply"
                            margin_low = float(row[col_margin_low]) if col_margin_low and pd.notna(row[col_margin_low]) else 5.0
                            margin_high = float(row[col_margin_high]) if col_margin_high and pd.notna(row[col_margin_high]) else 5.0
                            supplier = str(row[col_supplier]).strip() if col_supplier and pd.notna(row[col_supplier]) else ""
                            cluster = str(row[col_cluster]).strip() if col_cluster and pd.notna(row[col_cluster]) else ""
                            
                            vehicle_limits_map[bmc_id] = {
                                'limits': limits,
                                'leave_quantities': {
                                    '10 L': lq_10,
                                    '12L': lq_12,
                                    '15 L': lq_15,
                                    '18 L': lq_18
                                },
                                'strategy': strategy,
                                'margin': margin_low,
                                'margin_low': margin_low,
                                'margin_high': margin_high,
                                'supplier': supplier,
                                'cluster': cluster
                            }
                logger.info(f"Loaded vehicle limits, strategies, margins, clusters, and subclusters for {len(vehicle_limits_map)} BMCs from sheet '{sheet_name}'")
        except Exception as e:
            logger.error(f"Error parsing vehicle sheet: {e}")
            
        return vehicle_limits_map

    @staticmethod
    def get_optimal_vehicles_fallback(flow: float, vehicle_limits: Dict[str, float], distance: Optional[float] = None, strategy: str = 'Whole Milk Supply', margin: float = 5.0) -> Dict[str, int]:
        if flow <= 0:
            return {}
            
        is_long = False
        if distance is not None:
            is_long = (distance > 150.0)
            
        # Target flow based on strategy
        target_flow = flow
        if strategy == 'Least Vehicle':
            target_flow = flow * (1.0 - (margin / 100.0))
            
        res = {'18 L': 0, '15 L': 0, '12L': 0, '10 L': 0}
        rem = target_flow
        
        if is_long:
            order = [('18 L', 18000), ('15 L', 15000), ('12L', 12000), ('10 L', 10000)]
        else:
            order = [('10 L', 10000), ('12L', 12000), ('15 L', 15000), ('18 L', 18000)]
            
        # Filter order to only vehicle types that have limit > 0
        active_order = []
        for cap_name, cap_val in order:
            limit = int(vehicle_limits.get(cap_name, 1000))
            if limit > 0:
                active_order.append((cap_name, cap_val, limit))
                
        for idx, (cap_name, cap_val, limit) in enumerate(active_order):
            if rem <= 0:
                break
                
            # Check if the remaining flow can be covered by a single available vehicle of any active type
            single_veh_candidates = []
            for name, val, lim in active_order:
                avail = lim - res.get(name, 0)
                if avail > 0 and val >= rem:
                    single_veh_candidates.append((name, val))
            if single_veh_candidates:
                best_name, best_val = min(single_veh_candidates, key=lambda x: x[1])
                res[best_name] = res.get(best_name, 0) + 1
                rem -= best_val
                break
                
            if rem <= cap_val:
                # Check if there is any smaller vehicle type in active_order that can also cover rem
                has_smaller_covering = False
                for next_name, next_cap, next_limit in active_order[idx+1:]:
                    if next_cap < cap_val and next_cap >= rem:
                        has_smaller_covering = True
                        break
                
                if has_smaller_covering:
                    needed = 0
                else:
                    needed = int(math.ceil(rem / cap_val))
            elif idx == len(active_order) - 1:
                needed = int(math.ceil(rem / cap_val))
            else:
                needed = int(math.floor(rem / cap_val))
                
            taken = min(needed, limit)
            res[cap_name] = taken
            rem -= taken * cap_val
            
        if rem > 0:
            for cap_name, cap_val, limit in reversed(active_order):
                if rem <= 0:
                    break
                available = limit - res[cap_name]
                if available > 0:
                    needed = int(math.ceil(rem / cap_val))
                    taken = min(needed, available)
                    res[cap_name] += taken
                    rem -= taken * cap_val
                    
        return {k: v for k, v in res.items() if v > 0}

    @classmethod
    def get_optimal_vehicles(cls, flow: float, vehicle_limits: Dict[str, float], distance: Optional[float] = None, strategy: str = 'Whole Milk Supply', margin: float = 5.0) -> Dict[str, int]:
        if flow <= 0:
            return {}
            
        is_long = False
        if distance is not None:
            is_long = (distance > 150.0)
            
        # Target flow based on strategy
        target_flow = flow
        if strategy == 'Least Vehicle':
            target_flow = flow * (1.0 - (margin / 100.0))
            
        if is_long:
            # High capacity vehicles preferred for long distance: 18 L > 15 L > 12L > 10 L
            pref_order = [('18 L', 18000), ('15 L', 15000), ('12L', 12000), ('10 L', 10000)]
        else:
            # Low capacity vehicles preferred for short distance: 10 L > 12L > 15 L > 18 L
            pref_order = [('10 L', 10000), ('12L', 12000), ('15 L', 15000), ('18 L', 18000)]
            
        active_vehicles = []
        total_available_capacity = 0
        for name, cap in pref_order:
            limit = int(vehicle_limits.get(name, 1000))
            if limit > 0:
                active_vehicles.append((name, cap, limit))
                total_available_capacity += limit * cap
                
        if not active_vehicles:
            return {}
            
        if total_available_capacity <= target_flow:
            res = {}
            for name, cap, limit in active_vehicles:
                res[name] = limit
            return {k: v for k, v in res.items() if v > 0}
            
        try:
            from ortools.linear_solver import pywraplp
        except ImportError:
            return cls.get_optimal_vehicles_fallback(flow, vehicle_limits, distance, strategy, margin)

        # Scale flow and capacities to units of 1000 L to prevent precision issues
        target_flow_units = int(math.ceil(target_flow / 1000.0))
        
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if solver:
            # Set gap limit to 0 for absolute optimality
            solver.SetSolverSpecificParametersAsString("limits/gap = 0")
        else:
            solver = pywraplp.Solver.CreateSolver('CBC')
            if not solver:
                return cls.get_optimal_vehicles_fallback(flow, vehicle_limits, distance, strategy, margin)

        vars_map = {}
        for idx, (name, cap, limit) in enumerate(active_vehicles):
            cap_units = cap // 1000
            max_needed = int(math.ceil(target_flow_units / cap_units))
            var_limit = min(limit, max_needed)
            vars_map[name] = (solver.IntVar(0, var_limit, f"x_{name}"), cap_units, idx)

        # Constraint: sum(x_i * cap_units_i) >= target_flow_units
        solver.Add(sum(var * cap_units for var, cap_units, _ in vars_map.values()) >= target_flow_units)

        # Objective: Minimize: M1 * sum(x_i * cap_units_i) + M2 * sum(x_i) + M3 * sum(x_i * idx_i)
        # M1 = 10000 (capacity minimization dominates)
        # M2 = 100 (vehicle count minimization secondary)
        # M3 = 1 (preference penalty tertiary, idx matches pref_order)
        M1 = 10000.0
        M2 = 100.0
        M3 = 1.0
        
        obj_expr = []
        for var, cap_units, idx in vars_map.values():
            obj_expr.append(var * (M1 * cap_units + M2 + M3 * idx))
            
        solver.Minimize(solver.Sum(obj_expr))
        
        status = solver.Solve()
        
        res = {}
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            for name, (var, _, _) in vars_map.items():
                val = int(round(var.solution_value()))
                if val > 0:
                    res[name] = val
            return res
            
        return cls.get_optimal_vehicles_fallback(flow, vehicle_limits, distance, strategy, margin)

    @classmethod
    def solve_network_lp(cls, farmers: List[Dict[str, Any]], hubs: List[Dict[str, Any]], plants: List[Dict[str, Any]], geographies: List[Dict[str, Any]], transport_cost_per_km: float = 0.02, excel_file_path: Optional[str] = None) -> Dict[str, Any]:
        try:
            from ortools.linear_solver import pywraplp
        except ImportError:
            return {
                'status': 'ERROR',
                'message': 'Google OR-Tools is not installed or available in the environment.'
            }

        # Load vehicle limits from uploaded Excel file if it exists
        vehicle_limits_map = cls.parse_bmc_vehicles(excel_file_path)

        # Initialize solver
        solver = pywraplp.Solver.CreateSolver('GLOP')
        if not solver:
            return {'status': 'ERROR', 'message': 'Could not create GLOP solver.'}

        # Pre-calculate distances
        dist_cache = {}
        if excel_file_path and os.path.exists(excel_file_path):
            try:
                xl = pd.ExcelFile(excel_file_path)
                distance_sheet_name = None
                for s in xl.sheet_names:
                    if s.lower().strip() == 'distance':
                        distance_sheet_name = s
                        break
                if distance_sheet_name:
                    df_dist = xl.parse(distance_sheet_name)
                    col_hub = next((c for c in df_dist.columns if any(k in str(c).lower() for k in ['hub', 'bmc', 'mcc', 'source', 'from'])), None)
                    col_plant = next((c for c in df_dist.columns if any(k in str(c).lower() for k in ['plant', 'to', 'dest', 'target'])), None)
                    col_dist = next((c for c in df_dist.columns if any(k in str(c).lower() for k in ['dist', 'km'])), None)
                    
                    if col_hub and col_plant and col_dist:
                        def canonicalize_id(val):
                            if pd.isna(val) or val is None:
                                return ""
                            return "".join(c for c in str(val).lower() if c.isalnum())
                        
                        hub_id_map = {canonicalize_id(h['id']): h['id'] for h in hubs}
                        hub_id_map.update({canonicalize_id(h.get('name')): h['id'] for h in hubs})
                        
                        plant_id_map = {canonicalize_id(p['id']): p['id'] for p in plants}
                        plant_id_map.update({canonicalize_id(p.get('name')): p['id'] for p in plants})
                        
                        for _, row in df_dist.iterrows():
                            h_raw = canonicalize_id(row[col_hub])
                            p_raw = canonicalize_id(row[col_plant])
                            d_val = row[col_dist]
                            
                            h_id = hub_id_map.get(h_raw)
                            p_id = plant_id_map.get(p_raw)
                            
                            if h_id and p_id and pd.notna(d_val):
                                dist_cache[(h_id, p_id)] = float(d_val)
            except Exception as e:
                logger.error(f"Error loading distances from Excel sheet 'Distance': {e}")

        # Compute distances for pairs not in dist_cache
        for h in hubs:
            for p in plants:
                if (h['id'], p['id']) not in dist_cache:
                    dist_cache[(h['id'], p['id'])] = cls.calculate_haversine_distance(h, p)

        for p in plants:
            for g in geographies:
                if (p['id'], g['id']) not in dist_cache:
                    dist_cache[(p['id'], g['id'])] = cls.calculate_haversine_distance(p, g)

        def get_pair_dist(node1, node2):
            return dist_cache.get((node1['id'], node2['id']), 0.0)

        # Milk types
        milk_types = set()
        for h in hubs:
            for p in h.get('products', []):
                if 'type' in p:
                    milk_types.add(p['type'])
        if not milk_types:
            milk_types = {'Cow Milk', 'Buffalo Milk'}
        milk_types = sorted(list(milk_types))

        # Flow: Hub -> Plant per Milk Type
        flow_h_p = {}
        for h in hubs:
            h_prods = h.get('products', [])
            h_types = {p['type'] for p in h_prods if 'type' in p}
            for p in plants:
                p_demands = p.get('demands', [])
                p_demand_types = {d['type'] for d in p_demands if 'type' in d}
                
                p_products = p.get('products', [])
                p_milk_types = set()
                for prod in p_products:
                    if 'type' in prod:
                        ptype = prod['type']
                        if ptype.endswith(' Cheese'):
                            p_milk_types.add(ptype[:-7] + ' Milk')
                        elif 'buffalo' in ptype.lower():
                            p_milk_types.add('Buffalo Milk')
                        else:
                            p_milk_types.add('Cow Milk')
                
                common_milk = h_types.intersection(p_milk_types.union(p_demand_types))
                if common_milk:
                    dist = get_pair_dist(h, p)
                    if dist <= 500.0:
                        for m in common_milk:
                            clean_m = m.replace(' ', '_').replace('-', '_')
                            name = f"flow_H_{h['id']}_P_{p['id']}_{clean_m}"
                            flow_h_p[(h['id'], p['id'], m)] = solver.NumVar(0, solver.infinity(), name)

        # Flow: Plant -> Geography per Finished Product Type
        flow_p_g = {}
        for p in plants:
            p_products = p.get('products', [])
            for g in geographies:
                g_products = g.get('products', [])
                common_types = set(prod['type'] for prod in p_products if 'type' in prod).intersection(set(prod['type'] for prod in g_products if 'type' in prod))
                if common_types:
                    dist = get_pair_dist(p, g)
                    if dist <= 500.0:
                        for ptype in common_types:
                            clean_ptype = ptype.replace(' ', '_').replace('-', '_')
                            name = f"flow_P_{p['id']}_G_{g['id']}_{clean_ptype}"
                            flow_p_g[(p['id'], g['id'], ptype)] = solver.NumVar(0, solver.infinity(), name)

        # Constraints & Slack variables
        slack_vars = []

        # 1. Hub supply limits (per milk type)
        for h in hubs:
            h_prods = h.get('products', [])
            capacity_dict = {p['type']: p.get('capacity', 0) for p in h_prods if 'type' in p}
            
            for m in milk_types:
                flow_out_vars = [flow_h_p[(h['id'], p['id'], m)] for p in plants if (h['id'], p['id'], m) in flow_h_p]
                cap_limit = capacity_dict.get(m, 0)
                if cap_limit > 0:
                    if flow_out_vars:
                        slack = solver.NumVar(0, solver.infinity(), f"slack_hub_{h['id']}_{m.replace(' ', '_')}")
                        solver.Add(sum(flow_out_vars) + slack == cap_limit)
                        slack_vars.append(slack * 10000000.0)
                        
                        # Even Distribution Rule
                        eligible_plants = [p for p in plants if (h['id'], p['id'], m) in flow_h_p]
                        if len(eligible_plants) > 1:
                            clean_m = m.replace(' ', '_').replace('-', '_')
                            for i in range(len(eligible_plants)):
                                for j in range(i + 1, len(eligible_plants)):
                                    p1 = eligible_plants[i]
                                    p2 = eligible_plants[j]
                                    
                                    inflow_milks1 = p1.get('inflow_milks', [])
                                    cap_dict1 = {x['type']: x.get('capacity', 0) for x in inflow_milks1 if 'type' in x}
                                    cap1 = cap_dict1.get(m, 0)
                                    if cap1 <= 0:
                                        demands1 = p1.get('demands', []) or []
                                        demands_dict1 = {x['type']: x.get('demand', 0) for x in demands1 if 'type' in x}
                                        cap1 = demands_dict1.get(m, 0)
                                    if cap1 <= 0:
                                        cap1 = p1.get('capacity', 0)
                                    if cap1 <= 0:
                                        cap1 = 1.0
                                        
                                    inflow_milks2 = p2.get('inflow_milks', [])
                                    cap_dict2 = {x['type']: x.get('capacity', 0) for x in inflow_milks2 if 'type' in x}
                                    cap2 = cap_dict2.get(m, 0)
                                    if cap2 <= 0:
                                        demands2 = p2.get('demands', []) or []
                                        demands_dict2 = {x['type']: x.get('demand', 0) for x in demands2 if 'type' in x}
                                        cap2 = demands_dict2.get(m, 0)
                                    if cap2 <= 0:
                                        cap2 = p2.get('capacity', 0)
                                    if cap2 <= 0:
                                        cap2 = 1.0
                                    
                                    total_inflow_p1 = sum(flow_h_p[(h_other['id'], p1['id'], m)] for h_other in hubs if (h_other['id'], p1['id'], m) in flow_h_p)
                                    total_inflow_p2 = sum(flow_h_p[(h_other['id'], p2['id'], m)] for h_other in hubs if (h_other['id'], p2['id'], m) in flow_h_p)
                                    
                                    diff = solver.NumVar(0, solver.infinity(), f"diff_H_{h['id']}_P1_{p1['id']}_P2_{p2['id']}_{clean_m}")
                                    solver.Add(total_inflow_p1 * (1.0 / cap1) - total_inflow_p2 * (1.0 / cap2) <= diff)
                                    solver.Add(total_inflow_p2 * (1.0 / cap2) - total_inflow_p1 * (1.0 / cap1) <= diff)
                                    slack_vars.append(diff * 100000.0)
                else:
                    if flow_out_vars:
                        solver.Add(sum(flow_out_vars) == 0)

        # Helper yield factor
        def get_yield_factor(product_type: str) -> float:
            ptype = (product_type or '').strip().lower()
            if 'cheese' in ptype:
                return 0.10
            elif 'khoya' in ptype:
                return 0.20
            elif 'butter' in ptype:
                return 0.06
            elif 'milk powder' in ptype:
                return 0.12
            return 1.0

        # Helper milk type mapping
        def get_milk_type_for_product(product_type: str) -> str:
            ptype = (product_type or '').strip()
            if ptype.endswith(' Cheese'):
                return ptype[:-7] + ' Milk'
            ptype_lower = ptype.lower()
            if 'buffalo' in ptype_lower:
                return 'Buffalo Milk'
            return 'Cow Milk'

        # 2. Plant capacity & flow conservation
        for p in plants:
            p_products = p.get('products', [])
            p_yields = {prod['type']: prod.get('yield', get_yield_factor(prod['type'])) for prod in p_products if 'type' in prod}
            
            p_demands = p.get('demands', [])
            demand_dict = {d['type']: d.get('demand', 0) for d in p_demands if 'type' in d}
            
            inflow_milks = p.get('inflow_milks', [])
            if not inflow_milks:
                if p_demands:
                    inflow_milks = [{'type': d['type'], 'capacity': d['demand']} for d in p_demands]
                else:
                    inflow_milks = [{'type': m, 'capacity': p.get('capacity', 10000)} for m in milk_types]
            capacity_dict = {m['type']: m.get('capacity', 0) for m in inflow_milks if 'type' in m}
            
            for m in milk_types:
                flow_in_m = sum(flow_h_p[(h['id'], p['id'], m)] for h in hubs if (h['id'], p['id'], m) in flow_h_p)
                
                if m in demand_dict:
                    over_cap = solver.NumVar(0, solver.infinity(), f"over_cap_{p['id']}_{m.replace(' ', '_')}")
                    solver.Add(flow_in_m - over_cap <= demand_dict[m])
                    slack_vars.append(over_cap * 1000000.0)
                else:
                    outflow_milk_equivalent = []
                    for g in geographies:
                        g_products = g.get('products', [])
                        common_types = set(p_yields.keys()).intersection(set(prod['type'] for prod in g_products if 'type' in prod))
                        for ptype in common_types:
                            if get_milk_type_for_product(ptype) == m:
                                yf = p_yields[ptype]
                                if yf <= 0:
                                    yf = 1.0
                                if (p['id'], g['id'], ptype) in flow_p_g:
                                    outflow_milk_equivalent.append(flow_p_g[(p['id'], g['id'], ptype)] * (1.0 / yf))
                    
                    solver.Add(flow_in_m == sum(outflow_milk_equivalent))
                    
                    cap_limit = capacity_dict.get(m, 0)
                    if cap_limit > 0:
                        over_cap = solver.NumVar(0, solver.infinity(), f"over_cap_{p['id']}_{m.replace(' ', '_')}")
                        solver.Add(flow_in_m - over_cap <= cap_limit)
                        slack_vars.append(over_cap * 1000000.0)
                    else:
                        solver.Add(flow_in_m == 0)

            # Plant 20% minimum fulfillment constraint
            total_capacity = sum(capacity_dict.values()) if capacity_dict else p.get('capacity', 0)
            if total_capacity > 0:
                inflow_vars = [flow_h_p[(h['id'], p['id'], m)] for h in hubs for m in milk_types if (h['id'], p['id'], m) in flow_h_p]
                if inflow_vars:
                    plant_slack = solver.NumVar(0, solver.infinity(), f"slack_plant_{p['id']}")
                    solver.Add(sum(inflow_vars) + plant_slack >= 0.20 * total_capacity)
                    slack_vars.append(plant_slack * 10000000.0)

        # 3. Geography demand limit
        for g in geographies:
            g_products = g.get('products', [])
            for g_prod in g_products:
                ptype = g_prod.get('type')
                if not ptype:
                    continue
                demand_val = g_prod.get('demand', 0)
                
                flows_for_prod = [flow_p_g[(p['id'], g['id'], ptype)] for p in plants if (p['id'], g['id'], ptype) in flow_p_g]
                if flows_for_prod:
                    over_geo = solver.NumVar(0, solver.infinity(), f"over_geo_{g['id']}_{ptype.replace(' ', '_')}")
                    solver.Add(sum(flows_for_prod) - over_geo <= demand_val)
                    slack_vars.append(over_geo * 1000000.0)

        # Objective: Maximize Profit
        # 1. Revenue
        revenue_items = []
        for g in geographies:
            g_products = g.get('products', [])
            g_prices = {prod['type']: prod.get('price', 0.0) for prod in g_products if 'type' in prod}
            for p in plants:
                for ptype, price in g_prices.items():
                    if (p['id'], g['id'], ptype) in flow_p_g:
                        revenue_items.append(flow_p_g[(p['id'], g['id'], ptype)] * price)
                        
        for p in plants:
            p_demands = p.get('demands', [])
            for d in p_demands:
                m = d['type']
                price = d.get('price', 0.0)
                flow_in_m_vars = [flow_h_p[(h['id'], p['id'], m)] for h in hubs if (h['id'], p['id'], m) in flow_h_p]
                if flow_in_m_vars:
                    revenue_items.append(sum(flow_in_m_vars) * price)
                    
        revenue_expr = sum(revenue_items)

        # 2. Transport Costs
        trans_cost_expr = []
        for (h_id, p_id, m), flow_var in flow_h_p.items():
            h_node = next(x for x in hubs if x['id'] == h_id)
            p_node = next(x for x in plants if x['id'] == p_id)
            dist = get_pair_dist(h_node, p_node)
            effective_dist = 0.0 if dist <= 500.0 else dist
            cost_per_unit = effective_dist * transport_cost_per_km
            trans_cost_expr.append(flow_var * cost_per_unit)
            
        for (p_id, g_id, ptype), flow_var in flow_p_g.items():
            p_node = next(x for x in plants if x['id'] == p_id)
            g_node = next(x for x in geographies if x['id'] == g_id)
            dist = get_pair_dist(p_node, g_node)
            effective_dist = 0.0 if dist <= 500.0 else dist
            cost_per_unit = effective_dist * transport_cost_per_km
            trans_cost_expr.append(flow_var * cost_per_unit)

        # 3. Processing Costs
        proc_cost_expr = []
        for h in hubs:
            h_prods = h.get('products', [])
            cost_dict = {p['type']: p.get('processing_cost', 0.0) for p in h_prods if 'type' in p}
            for m in milk_types:
                flow_out_m = sum(flow_h_p[(h['id'], p['id'], m)] for p in plants if (h['id'], p['id'], m) in flow_h_p)
                proc_cost_expr.append(flow_out_m * cost_dict.get(m, 0.0))
                
        for p in plants:
            inflow_milks = p.get('inflow_milks', [])
            if not inflow_milks:
                p_demands = p.get('demands', [])
                if p_demands:
                    inflow_milks = [{'type': d['type'], 'processing_cost': d.get('processing_cost', 0.40)} for d in p_demands]
                else:
                    inflow_milks = [{'type': m, 'processing_cost': p.get('processing_cost', 0.50)} for m in milk_types]
            cost_dict = {m['type']: m.get('processing_cost', 0.0) for m in inflow_milks if 'type' in m}
            for m in milk_types:
                flow_in_m = sum(flow_h_p[(h['id'], p['id'], m)] for h in hubs if (h['id'], p['id'], m) in flow_h_p)
                proc_cost_expr.append(flow_in_m * cost_dict.get(m, 0.40))

        solver.Maximize(revenue_expr - sum(proc_cost_expr) - sum(slack_vars))

        status = solver.Solve()

        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            routes = []

            # Extract Hub -> Plant flows
            for (h_id, p_id, m), flow_var in flow_h_p.items():
                val = flow_var.solution_value()
                if val > 0.1:
                    h_node = next(x for x in hubs if x['id'] == h_id)
                    p_node = next(x for x in plants if x['id'] == p_id)
                    dist = get_pair_dist(h_node, p_node)
                    cost = dist * transport_cost_per_km * val
                    clean_m = m.replace(' ', '_').replace('-', '_')
                    
                    # Calculate optimal vehicles
                    bmc_info = vehicle_limits_map.get(h_id, {})
                    if isinstance(bmc_info, dict) and 'limits' in bmc_info:
                        limits = bmc_info['limits']
                        strategy = bmc_info.get('strategy', 'Whole Milk Supply')
                        margin_high = bmc_info.get('margin_high', 5.0)
                    else:
                        limits = bmc_info
                        strategy = 'Whole Milk Supply'
                        margin_high = 5.0
                        
                    optimal_veh = cls.get_optimal_vehicles(val, limits, distance=dist, strategy=strategy, margin=margin_high)
                    c_10 = optimal_veh.get('10 L', 0)
                    c_12 = optimal_veh.get('12L', 0)
                    c_15 = optimal_veh.get('15 L', 0)
                    c_18 = optimal_veh.get('18 L', 0)
                    total_veh = c_10 + c_12 + c_15 + c_18
                    total_cap = c_10*10000 + c_12*12000 + c_15*15000 + c_18*18000
                    excess = total_cap - val if total_veh > 0 else 0.0
                    
                    routes.append({
                        'id': f"route_{h_id}_{p_id}_{clean_m}",
                        'from_id': h_id,
                        'to_id': p_id,
                        'from_type': 'hub',
                        'to_type': 'plant',
                        'flow': round(val, 2),
                        'product_type': m,
                        'unit': 'L',
                        'distance': round(dist, 2),
                        'cost': round(cost, 2),
                        'vehicles_10_l': c_10,
                        'vehicles_12_l': c_12,
                        'vehicles_15_l': c_15,
                        'vehicles_18_l': c_18,
                        'total_vehicles': total_veh,
                        'total_vehicle_capacity': total_cap,
                        'excess_vehicle_capacity': round(excess, 2)
                    })

            # Extract Plant -> Geography flows
            for (p_id, g_id, ptype), flow_var in flow_p_g.items():
                val = flow_var.solution_value()
                if val > 0.1:
                    p_node = next(x for x in plants if x['id'] == p_id)
                    g_node = next(x for x in geographies if x['id'] == g_id)
                    dist = get_pair_dist(p_node, g_node)
                    cost = dist * transport_cost_per_km * val
                    unit = 'kg' if any(k in ptype.strip().lower() for k in ['cheese', 'khoya', 'butter', 'milk powder']) else 'L'
                    routes.append({
                        'id': f"route_{p_id}_{g_id}_{ptype.replace(' ', '_')}",
                        'from_id': p_id,
                        'to_id': g_id,
                        'from_type': 'plant',
                        'to_type': 'geography',
                        'flow': round(val, 2),
                        'product_type': ptype,
                        'unit': unit,
                        'distance': round(dist, 2),
                        'cost': round(cost, 2)
                    })

            obj_val = solver.Objective().Value()
            
            # Aggregate metrics
            total_revenue = 0.0
            for (p_id, g_id, ptype), flow_var in flow_p_g.items():
                val = flow_var.solution_value()
                if val > 0.1:
                    g_node = next(g for g in geographies if g['id'] == g_id)
                    price = next((prod.get('price', 0.0) for prod in g_node.get('products', []) if prod.get('type') == ptype), g_node.get('price', 0.0))
                    total_revenue += val * price

            for p in plants:
                p_demands = p.get('demands', [])
                for d in p_demands:
                    m = d['type']
                    price = d.get('price', 0.0)
                    flow_in_val = sum(flow_h_p[(h['id'], p['id'], m)].solution_value() for h in hubs if (h['id'], p['id'], m) in flow_h_p)
                    if flow_in_val > 0.1:
                        total_revenue += flow_in_val * price

            total_transport_cost = sum(r['cost'] for r in routes)

            total_hub_proc_cost = 0.0
            for h in hubs:
                h_prods = h.get('products', [])
                cost_dict = {p['type']: p.get('processing_cost', 0.0) for p in h_prods if 'type' in p}
                for m in milk_types:
                    flow_out_m = sum(flow_h_p[(h['id'], p['id'], m)].solution_value() for p in plants if (h['id'], p['id'], m) in flow_h_p)
                    total_hub_proc_cost += flow_out_m * cost_dict.get(m, 0.0)

            total_plant_proc_cost = 0.0
            for p in plants:
                inflow_milks = p.get('inflow_milks', [])
                if not inflow_milks:
                    p_demands = p.get('demands', [])
                    if p_demands:
                        inflow_milks = [{'type': d['type'], 'processing_cost': d.get('processing_cost', 0.40)} for d in p_demands]
                    else:
                        inflow_milks = [{'type': m, 'processing_cost': p.get('processing_cost', 0.50)} for m in milk_types]
                cost_dict = {m['type']: m.get('processing_cost', 0.0) for m in inflow_milks if 'type' in m}
                for m in milk_types:
                    flow_in_m = sum(flow_h_p[(h['id'], p['id'], m)].solution_value() for h in hubs if (h['id'], p['id'], m) in flow_h_p)
                    total_plant_proc_cost += flow_in_m * cost_dict.get(m, 0.40)

            total_proc_cost = total_hub_proc_cost + total_plant_proc_cost

            # Flow summary per node
            node_metrics = {}
            for h in hubs:
                out_val = sum(flow_h_p[(h['id'], p['id'], m)].solution_value() for p in plants for m in milk_types if (h['id'], p['id'], m) in flow_h_p)
                node_metrics[h['id']] = {
                    'inflow': 0.0,
                    'outflow': round(out_val, 2)
                }
            for p in plants:
                in_val = sum(flow_h_p[(h['id'], p['id'], m)].solution_value() for h in hubs for m in milk_types if (h['id'], p['id'], m) in flow_h_p)
                outflow_milk = 0.0
                p_demands = p.get('demands', [])
                if p_demands:
                    outflow_milk = in_val
                else:
                    p_yields = {prod['type']: prod.get('yield', get_yield_factor(prod['type'])) for prod in p_products if 'type' in prod}
                    for (p_id, g_id, ptype), flow_var in flow_p_g.items():
                        if p_id == p['id']:
                            yf = p_yields.get(ptype, 1.0)
                            if yf <= 0:
                                yf = 1.0
                            outflow_milk += flow_var.solution_value() / yf

                node_metrics[p['id']] = {
                    'inflow': round(in_val, 2),
                    'outflow': round(outflow_milk, 2)
                }
            for g in geographies:
                inflow_milk = 0.0
                for (p_id, g_id, ptype), flow_var in flow_p_g.items():
                    if g_id == g['id']:
                        p_node = next(x for x in plants if x['id'] == p_id)
                        p_products = p_node.get('products', [])
                        yf = next((prod.get('yield', get_yield_factor(ptype)) for prod in p_products if prod.get('type') == ptype), 1.0)
                        if yf <= 0:
                            yf = 1.0
                        inflow_milk += flow_var.solution_value() / yf

                node_metrics[g['id']] = {
                    'inflow': round(inflow_milk, 2),
                    'outflow': 0.0
                }

            return {
                'status': 'OPTIMAL',
                'summary': {
                    'profit': round(obj_val, 2),
                    'revenue': round(total_revenue, 2),
                    'transport_cost': round(total_transport_cost, 2),
                    'processing_cost': round(total_proc_cost, 2),
                    'hub_processing_cost': round(total_hub_proc_cost, 2),
                    'plant_processing_cost': round(total_plant_proc_cost, 2)
                },
                'routes': routes,
                'node_metrics': node_metrics
            }
        else:
            return {
                'status': 'INFEASIBLE',
                'message': 'The model is infeasible or unbounded. Check capacities, supplies, and product compatibility.'
            }

    @classmethod
    async def process_job(cls, job_id: str, input_filepath: str, output_filepath: str) -> Dict[str, Any]:
        start_time = time.time()
        
        # 1. Parse nodes
        nodes = cls.parse_excel_nodes(input_filepath)
        if not nodes:
            raise ValueError("No valid nodes found in the Excel workbook.")
            
        farmers = [n for n in nodes if n['type'] == 'farmer']
        hubs = [n for n in nodes if n['type'] == 'hub']
        plants = [n for n in nodes if n['type'] == 'plant']
        geographies = [n for n in nodes if n['type'] == 'geography']

        # 2. Run solver
        res = cls.solve_network_lp(farmers, hubs, plants, geographies, 0.02, input_filepath)
        
        if res.get('status') not in ('OPTIMAL', 'FEASIBLE'):
            raise ValueError(f"Linear solver failed with status: {res.get('status')}. Message: {res.get('message', '')}")
            
        # 3. Post-Solver vehicle pool strategy logic
        vehicle_limits_map = cls.parse_bmc_vehicles(input_filepath)
        
        subcluster_vehicle_pools = {}
        for bmc_id, info in vehicle_limits_map.items():
            s = info.get('supplier', '')
            c = info.get('cluster', '')
            key = (s, c)
            if key not in subcluster_vehicle_pools:
                subcluster_vehicle_pools[key] = {'10 L': 0.0, '12L': 0.0, '15 L': 0.0, '18 L': 0.0}
            limits = info['limits']
            subcluster_vehicle_pools[key]['10 L'] += limits.get('10 L', 0.0)
            subcluster_vehicle_pools[key]['12L'] += limits.get('12L', 0.0)
            subcluster_vehicle_pools[key]['15 L'] += limits.get('15 L', 0.0)
            subcluster_vehicle_pools[key]['18 L'] += limits.get('18 L', 0.0)

        # Hub capacities
        bmc_capacities = {}
        for h in hubs:
            h_prods = h.get('products', [])
            for p in h_prods:
                if 'type' in p:
                    bmc_capacities[(h['id'], p['type'])] = p.get('capacity', 0.0)

        # Sum total flow out of each BMC per milk type
        total_flow_from_bmc = {}
        for r in res.get('routes', []):
            if r.get('from_type') == 'hub':
                key = (r['from_id'], r['product_type'])
                total_flow_from_bmc[key] = total_flow_from_bmc.get(key, 0.0) + r['flow']

        hub_routes = [r for r in res.get('routes', []) if r.get('from_type') == 'hub']
        
        def get_subcluster_key(r):
            bmc_info = vehicle_limits_map.get(r['from_id'], {})
            return (bmc_info.get('supplier', ''), bmc_info.get('cluster', ''))
            
        hub_routes.sort(key=lambda x: (get_subcluster_key(x), -x['flow']))

        # Apply strategy allocation & pool checks
        for r in hub_routes:
            c, sc = get_subcluster_key(r)
            key = (c, sc)
            
            limits = subcluster_vehicle_pools.get(key, {'10 L': 1000.0, '12L': 1000.0, '15 L': 1000.0, '18 L': 1000.0})
            
            bmc_info = vehicle_limits_map.get(r['from_id'], {})
            margin_low = bmc_info.get('margin_low', 5.0)
            margin_high = bmc_info.get('margin_high', 5.0)
            strategy = bmc_info.get('strategy', 'Whole Milk Supply')
            
            r['margin_low'] = margin_low
            r['margin_high'] = margin_high
            
            q = r['flow']
            min_flow = q * (1.0 - margin_high / 100.0)
            max_flow = q * (1.0 + margin_low / 100.0)
            r['min_flow_quantity'] = min_flow
            r['max_flow_quantity'] = max_flow
            
            left_qty = bmc_capacities.get((r['from_id'], r['product_type']), 0.0) - total_flow_from_bmc.get((r['from_id'], r['product_type']), 0.0)
            
            optimal_veh = cls.get_optimal_vehicles(q, limits, distance=r['distance'], strategy=strategy, margin=margin_high)
            c_10 = optimal_veh.get('10 L', 0)
            c_12 = optimal_veh.get('12L', 0)
            c_15 = optimal_veh.get('15 L', 0)
            c_18 = optimal_veh.get('18 L', 0)
            total_veh = c_10 + c_12 + c_15 + c_18
            total_cap = c_10*10000 + c_12*12000 + c_15*15000 + c_18*18000
            excess_qty = total_cap - q if total_veh > 0 else 0.0
            
            do_not_supply = False
            reason_override = None
            
            if total_veh == 0 and q > 0.1:
                do_not_supply = True
                reason_override = "No vehicles available in the sub-cluster pool"
            elif left_qty > min_flow:
                do_not_supply = True
                reason_override = f"Left quantity on BMC ({left_qty:.2f} L) is greater than MinimumFlowQuantity ({min_flow:.2f} L)"
            elif excess_qty > max_flow:
                do_not_supply = True
                reason_override = f"Excess vehicle capacity ({excess_qty:.2f} L) is greater than MaximumFlowQuantity ({max_flow:.2f} L)"
            
            if do_not_supply:
                r['vehicles_10_l'] = 0
                r['vehicles_12_l'] = 0
                r['vehicles_15_l'] = 0
                r['vehicles_18_l'] = 0
                r['total_vehicles'] = 0
                r['total_vehicle_capacity'] = 0.0
                r['excess_vehicle_capacity'] = 0.0
                r['vehicle_reason'] = reason_override
            else:
                r['vehicles_10_l'] = c_10
                r['vehicles_12_l'] = c_12
                r['vehicles_15_l'] = c_15
                r['vehicles_18_l'] = c_18
                r['total_vehicles'] = total_veh
                r['total_vehicle_capacity'] = total_cap
                r['excess_vehicle_capacity'] = round(excess_qty, 2)
                r['vehicle_reason'] = "Supplied"
                
                limits['10 L'] -= c_10
                limits['12L'] -= c_12
                limits['15 L'] -= c_15
                limits['18 L'] -= c_18
        
        for r in res.get('routes', []):
            if r.get('from_type') != 'hub':
                r['margin_low'] = 5.0
                r['margin_high'] = 5.0
                r['min_flow_quantity'] = r['flow'] * 0.95
                r['max_flow_quantity'] = r['flow'] * 1.05
                r['vehicle_reason'] = "Not Applicable (Plant to Geography Route)"

        # 4. Generate Result sheets using Pandas and Openpyxl
        # 4.1. Summary Sheet
        summary_data = [
            {'Metric': 'Solver Status', 'Value': res['status']},
            {'Metric': 'Net Daily Profit (₹)', 'Value': res['summary']['profit']},
            {'Metric': 'Total Revenue (₹)', 'Value': res['summary']['revenue']},
            {'Metric': 'Total Transport Cost (₹)', 'Value': res['summary']['transport_cost']},
            {'Metric': 'Total Processing Cost (₹)', 'Value': res['summary']['processing_cost']},
            {'Metric': 'Hub Processing Cost (₹)', 'Value': res['summary']['hub_processing_cost']},
            {'Metric': 'Plant Processing Cost (₹)', 'Value': res['summary']['plant_processing_cost']},
            {'Metric': 'Total Nodes', 'Value': len(nodes)},
            {'Metric': 'Processing Time (seconds)', 'Value': round(time.time() - start_time, 2)}
        ]
        df_summary = pd.DataFrame(summary_data)

        # 4.2. Nodes Sheet
        nodes_data = []
        inflow_lookup = {}
        outflow_lookup = {}
        for r in res.get('routes', []):
            fid = r['from_id']
            tid = r['to_id']
            ptype = r['product_type']
            flow_val = r['flow']
            inflow_lookup[(tid, ptype)] = inflow_lookup.get((tid, ptype), 0.0) + flow_val
            outflow_lookup[(fid, ptype)] = outflow_lookup.get((fid, ptype), 0.0) + flow_val

        for n in nodes:
            nid = n['id']
            ntype = n['type']
            if ntype == 'farmer':
                continue
            elif ntype == 'hub':
                for p in n.get('products', []):
                    comm = p['type']
                    limit = p.get('capacity', 0.0)
                    inflow = inflow_lookup.get((nid, comm), 0.0)
                    outflow = outflow_lookup.get((nid, comm), 0.0)
                    nodes_data.append({
                        'Node ID': nid,
                        'Name': n['name'],
                        'Type': ntype,
                        'Subtype': n.get('subtype', ''),
                        'Latitude': n['lat'],
                        'Longitude': n['lng'],
                        'Commodity': comm,
                        'Inflow Throughput': round(inflow, 2),
                        'Outflow Throughput': round(outflow, 2),
                        'Capacity / Supply Limit': limit
                    })
            elif ntype == 'plant':
                p_demands = n.get('demands', [])
                if p_demands:
                    for d in p_demands:
                        comm = d['type']
                        limit = d.get('demand', 0.0)
                        inflow = inflow_lookup.get((nid, comm), 0.0)
                        nodes_data.append({
                            'Node ID': nid,
                            'Name': n['name'],
                            'Type': ntype,
                            'Subtype': n.get('subtype', ''),
                            'Latitude': n['lat'],
                            'Longitude': n['lng'],
                            'Commodity': comm,
                            'Inflow Throughput': round(inflow, 2),
                            'Outflow Throughput': round(inflow, 2),
                            'Capacity / Supply Limit': limit
                        })
                else:
                    for m in n.get('inflow_milks', []):
                        comm = m['type']
                        limit = m.get('capacity', 0.0)
                        inflow = inflow_lookup.get((nid, comm), 0.0)
                        outflow = outflow_lookup.get((nid, comm), 0.0)
                        nodes_data.append({
                            'Node ID': nid,
                            'Name': n['name'],
                            'Type': ntype,
                            'Subtype': n.get('subtype', ''),
                            'Latitude': n['lat'],
                            'Longitude': n['lng'],
                            'Commodity': comm,
                            'Inflow Throughput': round(inflow, 2),
                            'Outflow Throughput': round(outflow, 2),
                            'Capacity / Supply Limit': limit
                        })
            elif ntype == 'geography':
                for p in n.get('products', []):
                    comm = p['type']
                    limit = p.get('demand', 0.0)
                    inflow = inflow_lookup.get((nid, comm), 0.0)
                    outflow = outflow_lookup.get((nid, comm), 0.0)
                    nodes_data.append({
                        'Node ID': nid,
                        'Name': n['name'],
                        'Type': ntype,
                        'Subtype': n.get('subtype', ''),
                        'Latitude': n['lat'],
                        'Longitude': n['lng'],
                        'Commodity': comm,
                        'Inflow Throughput': round(inflow, 2),
                        'Outflow Throughput': round(outflow, 2),
                        'Capacity / Supply Limit': limit
                    })
        df_nodes = pd.DataFrame(nodes_data)

        # 4.3. Routes Sheet
        routes_data = []
        for r in res.get('routes', []):
            from_node = next((n for n in nodes if n['id'] == r['from_id']), {'name': 'Unknown'})
            to_node = next((n for n in nodes if n['id'] == r['to_id']), {'name': 'Unknown'})
            
            supplier = ""
            cluster = ""
            strategy = ""
            margin_low = r.get('margin_low', 5.0)
            margin_high = r.get('margin_high', 5.0)
            
            lq_10 = 0.0
            lq_12 = 0.0
            lq_15 = 0.0
            lq_18 = 0.0
            if r.get('from_type') == 'hub':
                bmc_info = vehicle_limits_map.get(r['from_id'], {})
                supplier = bmc_info.get('supplier', '')
                cluster = bmc_info.get('cluster', '')
                strategy = bmc_info.get('strategy', '')
                margin_low = bmc_info.get('margin_low', 5.0)
                margin_high = bmc_info.get('margin_high', 5.0)
                lq_dict = bmc_info.get('leave_quantities', {})
                lq_10 = lq_dict.get('10 L', 0.0)
                lq_12 = lq_dict.get('12L', 0.0)
                lq_15 = lq_dict.get('15 L', 0.0)
                lq_18 = lq_dict.get('18 L', 0.0)
                
            routes_data.append({
                'Route ID': r['id'],
                'From Node ID': r['from_id'],
                'From Name': from_node.get('name', 'Unknown'),
                'From Type': r['from_type'],
                'From Latitude': from_node.get('lat'),
                'From Longitude': from_node.get('lng'),
                'To Node ID': r['to_id'],
                'To Name': to_node.get('name', 'Unknown'),
                'To Type': r['to_type'],
                'To Latitude': to_node.get('lat'),
                'To Longitude': to_node.get('lng'),
                'Product / Milk Type': r['product_type'],
                'Flow': r['flow'],
                'Unit': r['unit'],
                'MinimumFlowQuantity': round(r.get('min_flow_quantity', r['flow']), 2),
                'MaximumFlowQuantity': round(r.get('max_flow_quantity', r['flow']), 2),
                'VehicleReason': r.get('vehicle_reason', 'Supplied'),
                'Distance (km)': r['distance'],
                'Transport Cost (₹)': r['cost'],
                'Status': 'ACTIVE',
                'Reason': 'Optimal Flow',
                '10 L Vehicles': r.get('vehicles_10_l', 0) if r['from_type'] == 'hub' else 0,
                '12L Vehicles': r.get('vehicles_12_l', 0) if r['from_type'] == 'hub' else 0,
                '15 L Vehicles': r.get('vehicles_15_l', 0) if r['from_type'] == 'hub' else 0,
                '18 L Vehicles': r.get('vehicles_18_l', 0) if r['from_type'] == 'hub' else 0,
                'Total Vehicles': r.get('total_vehicles', 0) if r['from_type'] == 'hub' else 0,
                'Total Vehicle Capacity (L)': r.get('total_vehicle_capacity', 0) if r['from_type'] == 'hub' else 0,
                'Excess Vehicle Capacity (L)': r.get('excess_vehicle_capacity', 0) if r['from_type'] == 'hub' else 0,
                'Supplier': supplier,
                'Cluster': cluster,
                'Strategy': strategy,
                'FlowLowMarginPercentage': margin_low,
                'FlowHighMarginPercentage': margin_high,
                '10 L LeaveQuantity': lq_10,
                '12L LeaveQuantity': lq_12,
                '15 L LeaveQuantity': lq_15,
                '18 L LeaveQuantity': lq_18
            })
        df_routes = pd.DataFrame(routes_data)

        # 4.4. Plant Consumption Report
        df_plants = df_nodes[df_nodes['Type'] == 'plant']
        unique_commodities = sorted(df_nodes['Commodity'].unique()) if not df_nodes.empty else []
        
        plant_report_rows = []
        if not df_plants.empty:
            for (plant_id, plant_name), group in df_plants.groupby(['Node ID', 'Name']):
                row_dict = {'Plant ID': plant_id, 'Plant Name': plant_name}
                for comm in unique_commodities:
                    comm_row = group[group['Commodity'] == comm]
                    if not comm_row.empty:
                        demand = comm_row.iloc[0]['Capacity / Supply Limit']
                        supply = comm_row.iloc[0]['Inflow Throughput']
                        demand = float(demand) if pd.notna(demand) else 0.0
                        supply = float(supply) if pd.notna(supply) else 0.0
                    else:
                        demand = 0.0
                        supply = 0.0
                        
                    pct = round((supply / demand * 100.0), 2) if demand > 0 else ""
                    
                    row_dict[f'{comm} {{Demand}}'] = demand
                    row_dict[f'{comm} {{Supply}}'] = supply
                    row_dict[f'{comm} {{Received Percentage}}'] = pct
                plant_report_rows.append(row_dict)
        df_plant_report = pd.DataFrame(plant_report_rows)

        # 4.5. BMC Supply Report
        df_hubs = df_nodes[df_nodes['Type'] == 'hub']
        hub_report_rows = []
        if not df_hubs.empty:
            for (hub_id, hub_name), group in df_hubs.groupby(['Node ID', 'Name']):
                row_dict = {'BMC ID': hub_id, 'BMC Name': hub_name}
                for comm in unique_commodities:
                    comm_row = group[group['Commodity'] == comm]
                    if not comm_row.empty:
                        stock = comm_row.iloc[0]['Capacity / Supply Limit']
                        supply = comm_row.iloc[0]['Outflow Throughput']
                        stock = float(stock) if pd.notna(stock) else 0.0
                        supply = float(supply) if pd.notna(supply) else 0.0
                    else:
                        stock = 0.0
                        supply = 0.0
                        
                    pct = round((supply / stock * 100.0), 2) if stock > 0 else ""
                    
                    row_dict[f'{comm} {{Stock}}'] = stock
                    row_dict[f'{comm} {{Supply}}'] = supply
                    row_dict[f'{comm} {{Supply Percentage}}'] = pct
                hub_report_rows.append(row_dict)
        df_hub_report = pd.DataFrame(hub_report_rows)

        # 4.6. Hub To Plant
        df_hub_to_plant = df_routes[
            (df_routes['Reason'] == 'Optimal Flow') & 
            (df_routes['From Type'] == 'hub') & 
            (df_routes['To Type'] == 'plant')
        ]

        # 4.7. BMC Wise Allocation Matrix
        flow_map = {}
        for r in res.get('routes', []):
            if r.get('from_type') == 'hub' and r.get('to_type') == 'plant':
                flow_map[(r['from_id'], r['to_id'], r['product_type'])] = r['flow']

        bmc_allocation_rows = []
        for h in hubs:
            h_prods = h.get('products', [])
            hub_commodities = set(p_item['type'] for p_item in h_prods if p_item.get('type'))
            for (from_id, to_id, prod_type) in flow_map:
                if from_id == h['id']:
                    hub_commodities.add(prod_type)
                    
            for m in sorted(list(hub_commodities)):
                total_flow = sum(flow_map.get((h['id'], p['id'], m), 0.0) for p in plants)
                row_dict = {
                    'BMC': h.get('name', h['id']),
                    'Product': m,
                    'Quantity': round(total_flow, 2)
                }
                for p in plants:
                    p_name = p.get('name', p['id'])
                    flow_val = flow_map.get((h['id'], p['id'], m), 0.0)
                    row_dict[p_name] = round(flow_val, 2)
                bmc_allocation_rows.append(row_dict)
                
        df_bmc_wise_alloc = pd.DataFrame(bmc_allocation_rows)

        # 4.8. Plant Wise Allocation Matrix
        plant_allocation_rows = []
        for p in plants:
            p_commodities = {}
            p_demands = p.get('demands', [])
            if p_demands:
                for d in p_demands:
                    p_commodities[d['type']] = d.get('demand', 0.0)
            else:
                inflow_milks = p.get('inflow_milks', [])
                for m in inflow_milks:
                    if 'type' in m:
                        p_commodities[m['type']] = m.get('capacity', 0.0)
                        
            for (from_id, to_id, prod_type) in flow_map:
                if to_id == p['id'] and prod_type not in p_commodities:
                    p_commodities[prod_type] = 0.0
                    
            for m, req_qty in sorted(p_commodities.items()):
                fulfilled_qty = sum(flow_map.get((h['id'], p['id'], m), 0.0) for h in hubs)
                pct = round((fulfilled_qty / req_qty * 100.0), 2) if req_qty > 0 else ""
                row_dict = {
                    'Plant': p.get('name', p['id']),
                    'Product': m,
                    'Required Quantity': round(req_qty, 2),
                    'Fullfilled Quantity': round(fulfilled_qty, 2),
                    'Fullfilled Percentage': pct
                }
                for h in hubs:
                    h_name = h.get('name', h['id'])
                    flow_val = flow_map.get((h['id'], p['id'], m), 0.0)
                    row_dict[h_name] = round(flow_val, 2)
                plant_allocation_rows.append(row_dict)
                
        df_plant_wise_alloc = pd.DataFrame(plant_allocation_rows)

        # 4.9. BMC Vehicle Allocation Sheet
        df_veh_alloc = df_hub_to_plant[[
            'From Node ID', 'From Name', 
            'Supplier', 'Cluster', 'Strategy', 
            'FlowLowMarginPercentage', 'FlowHighMarginPercentage',
            'To Node ID', 'To Name', 
            'Product / Milk Type', 'Flow', 'Unit', 
            'MinimumFlowQuantity', 'MaximumFlowQuantity', 'VehicleReason',
            'Distance (km)', 'Transport Cost (₹)',
            '10 L Vehicles', '12L Vehicles', '15 L Vehicles', '18 L Vehicles', 
            'Total Vehicles', 'Total Vehicle Capacity (L)', 'Excess Vehicle Capacity (L)'
        ]].copy()
        df_veh_alloc = df_veh_alloc.rename(columns={
            'From Node ID': 'BMC ID',
            'From Name': 'BMC Name',
            'To Node ID': 'Plant ID',
            'To Name': 'Plant Name',
            'Flow': 'Flow Quantity',
            '10 L Vehicles': '10 L',
            '12L Vehicles': '12 L',
            '15 L Vehicles': '15 L',
            '18 L Vehicles': '18 L'
        })
        for col in ['10 L', '12 L', '15 L', '18 L']:
            if col in df_veh_alloc.columns:
                df_veh_alloc[col] = df_veh_alloc[col].fillna(0).astype(int)
        
        df_veh_alloc['10 L Capacity'] = df_veh_alloc['10 L'] * 10
        df_veh_alloc['12L Capacity'] = df_veh_alloc['12 L'] * 12
        df_veh_alloc['15 L Capacity'] = df_veh_alloc['15 L'] * 15
        df_veh_alloc['18 L Capacity'] = df_veh_alloc['18 L'] * 18
        
        columns_order = [
            'BMC ID', 'BMC Name', 'Supplier', 'Cluster', 'Strategy', 
            'FlowLowMarginPercentage', 'FlowHighMarginPercentage',
            '10 L', '12 L', '15 L', '18 L',
            '10 L Capacity', '12L Capacity', '15 L Capacity', '18 L Capacity',
            'Plant ID', 'Plant Name', 'Product / Milk Type', 'Flow Quantity', 'Unit', 
            'MinimumFlowQuantity', 'MaximumFlowQuantity', 'VehicleReason',
            'Distance (km)', 'Transport Cost (₹)',
            'Total Vehicles', 'Total Vehicle Capacity (L)', 'Excess Vehicle Capacity (L)'
        ]
        columns_order = [c for c in columns_order if c in df_veh_alloc.columns]
        df_veh_alloc = df_veh_alloc.reindex(columns=columns_order)

        # Write all sheets
        with pd.ExcelWriter(output_filepath, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            df_nodes.to_excel(writer, sheet_name='Nodes', index=False)
            df_routes.to_excel(writer, sheet_name='Routes', index=False)
            df_plant_report.to_excel(writer, sheet_name='Plant Consumption Report', index=False)
            df_hub_report.to_excel(writer, sheet_name='BMC Supply Report', index=False)
            df_hub_to_plant.to_excel(writer, sheet_name='Hub To Plant', index=False)
            df_bmc_wise_alloc.to_excel(writer, sheet_name='BMC Wise Allocation', index=False)
            df_plant_wise_alloc.to_excel(writer, sheet_name='Plant Wise Allocation', index=False)
            df_veh_alloc.to_excel(writer, sheet_name='BMC Vehicle Allocation', index=False)

        gc.collect()
        return {
            'summary': res['summary'],
            'total_records': len(nodes),
            'processed_records': len(df_routes)
        }
