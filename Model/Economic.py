from pyomo.environ import *
from pyomo.core import *
from pyomo.opt import SolverFactory
from datetime import timedelta
import pandas as pd
import numpy as np
import re
import sys

def Cost_Emissions_Obj_Ctr(model,t_tt_combinations):
    ########################
    # Objective Function   #
    ########################

    def Objective_rule(model):
        return model.V_cost_total

    model.OBJ = Objective(rule=Objective_rule, sense=minimize)

    ############################################
    # Cost and emission variables definition   #
    ############################################
    def Total_cost_definition_rule(model):
        return model.V_cost_total == sum(model.V_cost[sector, area, year] for sector in model.SECTOR for area in model.AREAS for year in model.YEAR)

    model.Total_cost_definitionCtr = Constraint(rule=Total_cost_definition_rule)

    def Total_emissions_definition_rule(model):
        return model.V_emissions_total == sum(
            model.V_emissions[sector,area, year] for sector in model.SECTOR for area in model.AREAS for year in model.YEAR)

    model.Total_emissions_definitionCtr = Constraint(rule=Total_emissions_definition_rule)

    def Cost_definition_rule(model, sector, area, year):
        return model.V_cost[sector, area, year] == sum(
            model.P_flow_cost_r[resource,sector, area, year] * model.V_resource_imports[resource,sector, area, year]
            for resource in model.RESOURCES) + \
               sum(sum(model.P_flow_cost_t[tech,sector, area, year] * model.V_technology_use_coef[tech, tech_type,sector, area, year] \
                       for tech_type in t_tt_combinations[tech]) for tech in model.TECHNOLOGIES) + \
               sum(model.V_technology_cost[tech,sector, area, year] for tech in model.TECHNOLOGIES) + \
               sum(model.P_opex_cost[tech,sector, area, year] * model.V_technology_use_coef_capacity[tech,sector, area, year] for tech
                   in model.TECHNOLOGIES) + \
               model.V_carbon_cost[sector,area,year] + \
               model.V_ccs_capex_cost[sector,area,year] + model.V_ccs_opex_cost[sector,area,year]


    model.Cost_definitionCtr = Constraint(model.SECTOR,model.AREAS, model.YEAR, rule=Cost_definition_rule)

    def Technology_cost_definition_rule(model, tech,sector, area, year):
        Tot = 0
        for y in model.YEAR:
            subTot = 0
            tech_exists = False
            for resource in model.RESOURCES:
                for tech_type in model.TECH_TYPE:
                    if model.P_conversion_factor[tech, tech_type, sector, resource, y] != 0:
                        tech_exists = True
            if tech_exists:
                if y <= year:
                    if model.P_lifetime[tech,sector, area, y] != 0 or model.P_construction_time[tech,sector, area, y] != 0:
                        n =  model.P_lifetime[tech,sector, area, y] #+model.P_construction_time[tech,sector, area, y]
                        i = model.P_discount_rate[tech,sector, area, y]
                        CRF = i * (i + 1) ** n / ((1 + i) ** n - 1)
                        # ROI_ratio = 0
                        if y + n - year - model.P_tech_age[tech,sector, area, y] > 0:
                            # ROI_ratio = CRF * (y + n - year)
                            subTot += model.P_capex[tech,sector, area, y] * CRF * model.V_added_capacity[tech,sector, area, y]
            Tot += subTot


        return model.V_technology_cost[tech,sector, area, year] == Tot

    model.Technology_cost_definitionCtr = Constraint(model.TECHNOLOGIES, model.SECTOR, model.AREAS, model.YEAR,
                                                     rule=Technology_cost_definition_rule)


    def Emissions_definition_rule(model,sector, area, year):
        return model.V_emissions[sector,area, year] == sum(sum(
            model.V_emissions_tech_type[tech, tech_type,sector, area, year] for tech_type in
            t_tt_combinations[tech])-model.V_captured_emissions[tech,sector,area,year] for tech in model.TECHNOLOGIES) + \
               sum(model.P_emissions_r[resource,sector, area, year] * model.V_resource_imports[resource,sector, area, year] for resource
                   in model.RESOURCES)+model.V_resource_exports["CO",sector,area,year]*1.6 #coef for CO2eq assuming CO oxydation // indeed, if not consumed, CO is released into the atmosphere

    model.Emissions_definitionCtr = Constraint(model.SECTOR,model.AREAS, model.YEAR, rule=Emissions_definition_rule)

    def Emissions_no_ccs_definition_rule(model,sector, area, year):
        return model.V_emissions_no_ccs[sector,area, year] == sum(sum(
            model.V_emissions_tech_type[tech, tech_type,sector, area, year] for tech_type in
            t_tt_combinations[tech]) for tech in model.TECHNOLOGIES) + \
               sum(model.P_emissions_r[resource,sector, area, year] * model.V_resource_imports[resource,sector, area, year] for resource
                   in model.RESOURCES)+model.V_resource_exports["CO",sector,area,year]*1.6 #coef for CO2eq assuming CO oxydation // indeed, if not consumed, CO is released into the atmosphere

    model.Emissions_no_ccs_definitionCtr = Constraint(model.SECTOR,model.AREAS, model.YEAR, rule=Emissions_no_ccs_definition_rule)

    def Technology_emissions_definition_1st_rule(model, tech, tech_type,sector, area, year):
        if tech_type in t_tt_combinations[tech]:
            return model.V_emissions_tech_type[tech, tech_type,sector, area, year] == model.V_emissions_tech_type_plus[
                tech, tech_type,sector, area, year] + model.V_emissions_tech_type_minus[tech, tech_type, sector, area, year]
        else:
            return Constraint.Skip

    model.Technology_emissions_definition_1stCtr = Constraint(model.TECHNOLOGIES, model.TECH_TYPE, model.SECTOR, model.AREAS,
                                                              model.YEAR, rule=Technology_emissions_definition_1st_rule)

    def Technology_emissions_definition_2nd_rule(model, tech, tech_type,sector, area, year):
        if tech_type in t_tt_combinations[tech]:
            return model.V_emissions_tech_type[tech, tech_type,sector, area, year] == -model.P_conversion_factor[tech, tech_type,sector, "CO2", year] * \
                   model.V_technology_use_coef[tech, tech_type,sector, area, year]
        else:
            return Constraint.Skip #model.V_emissions_tech_type[tech, tech_type,sector, area, year]==0

    model.Technology_emissions_definition_2ndCtr = Constraint(model.TECHNOLOGIES, model.TECH_TYPE,model.SECTOR, model.AREAS,
                                                              model.YEAR,
                                                              rule=Technology_emissions_definition_2nd_rule)

    def Technology_emissions_definition_3rd_rule(model, sector, area, year):
        return sum(sum(model.V_emissions_tech_type[tech, tech_type,sector, area, year] for tech_type in t_tt_combinations[tech]) for tech in model.TECHNOLOGIES)>=0

    model.Technology_emissions_definition_3rdCtr = Constraint(model.SECTOR, model.AREAS,
                                                              model.YEAR,
                                                              rule=Technology_emissions_definition_3rd_rule)

    def Carbon_cost_rule(model,sector,area,year):
        return model.V_carbon_cost[sector, area, year] == model.P_carbon_tax[sector,area,year]*model.V_ctax_emissions_plus[sector, area, year]

    model.Carbon_costCtr=Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=Carbon_cost_rule)

    def Ctax_emissions_rule(model,sector,area,year):
        return model.V_ctax_emissions_plus[sector, area, year]+ model.V_ctax_emissions_minus[sector, area, year] == \
               sum(sum(
                   model.V_emissions_tech_type[tech, tech_type, sector, area, year] for tech_type in
                   t_tt_combinations[tech]) - model.V_captured_emissions[tech, sector, area, year] for tech in
                   model.TECHNOLOGIES) + \
               sum(model.P_emissions_r[resource, sector, area, year] * model.V_resource_imports[
                   resource, sector, area, year] for resource
                   in model.CTAX_RESOURCES)#+model.V_resource_exports["CO",sector,area,year]*1.6 #todo do I include CO emissions in the equation ?
    model.Ctax_emissionsCtr=Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=Ctax_emissions_rule)

    def Emissions_reduction_rule(model,sector,area,year):
        year_ini=min(getattr(model, "YEAR").data())
        if model.P_emissions_reduction_ratio_obj[sector,area,year]!=0 and year > year_ini:
            return model.V_emissions[sector,area,year]<=(1-model.P_emissions_reduction_ratio_obj[sector,area,year])*model.V_emissions[sector,area,year_ini]
        else:
            return Constraint.Skip

    model.Emissions_reductionCtr=Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=Emissions_reduction_rule)


    return model