from pyomo.environ import *
from pyomo.core import *
from pyomo.opt import SolverFactory
from datetime import timedelta
import pandas as pd
import numpy as np
import re
import sys

def Capacity_planning(model,t_tt_combinations):
    def Technology_Capacity_rule(model,tech,sector,area,year):
        if model.P_max_capacity_t[tech,sector,area,year]>0:
            resource = model.P_capacity_associated_resource[tech,sector,area,year]
            return sum(model.V_resource_tech_type_capacity[tech,tech_type,sector,resource,area,year] for tech_type in model.TECH_TYPE)<=model.P_max_capacity_t[tech,sector,area,year]
        else:
            return Constraint.Skip
    model.Technology_CapacityCtr=Constraint(model.TECHNOLOGIES,model.SECTOR,model.AREAS,model.YEAR,rule=Technology_Capacity_rule)

    def Technology_Capacity_2nd_rule(model,tech,tech_type,sector,resource,area,year):
        if tech_type in t_tt_combinations[tech]:
            if model.P_conversion_factor[tech, tech_type, sector, resource, year]<=0:
                return model.V_resource_tech_type_capacity[tech,tech_type,sector,resource,area,year]>=\
                       model.V_resource_tech_type_outflow[tech,tech_type,sector,resource,area,year]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.Technology_Capacity2ndCtr=Constraint(model.TECHNOLOGIES,model.TECH_TYPE,model.SECTOR,model.RESOURCES,model.AREAS,model.YEAR,rule=Technology_Capacity_2nd_rule)

    def Technology_Capacity_3rd_rule(model,tech,tech_type,sector,resource,area,year):
        if tech_type in t_tt_combinations[tech]:
            return model.V_resource_tech_type_capacity[tech,tech_type,sector,resource,area,year]== \
                   model.V_technology_tech_type_use_coef_capacity[tech, tech_type, sector, area, year] * \
                   -model.P_conversion_factor[tech, tech_type, sector, resource, year]
        else:
            return Constraint.Skip #model.V_resource_tech_type_capacity[tech,tech_type,sector,resource,area,year]==0

    model.Technology_Capacity3rdCtr=Constraint(model.TECHNOLOGIES,model.TECH_TYPE,model.SECTOR,model.RESOURCES,model.AREAS,model.YEAR,rule=Technology_Capacity_3rd_rule)

    def Technology_Capacity_4th_rule(model,tech,tech_type,sector,area,year):
        if tech_type in t_tt_combinations[tech]:
            tech_exists = False
            resource = model.P_capacity_associated_resource[tech, sector, area, year]
            if resource!=0:
                if model.P_conversion_factor[tech, tech_type, sector, resource, year] != 0:
                    tech_exists = True

            if tech_exists:
                return Constraint.Skip
            else:
                return model.V_technology_tech_type_use_coef_capacity[tech, tech_type, sector, area, year]==0
        else:
            return Constraint.Skip #model.V_technology_tech_type_use_coef_capacity[tech, tech_type, sector, area, year]==0
    model.Technology_Capacity_4thCtr=Constraint(model.TECHNOLOGIES,model.TECH_TYPE,model.SECTOR,model.AREAS,model.YEAR,rule=Technology_Capacity_4th_rule)

    def Technology_Capacity_area_rule(model,tech,area,year):
        if model.P_max_capacity_t[tech,"All",area,year]>0:
            resource = model.P_capacity_associated_resource[tech,"All",area,year]
            return sum(model.V_resource_tech_type_capacity[tech,tech_type,sector,resource,area,year] for tech_type in model.TECH_TYPE for sector in model.SECTOR)<=model.P_max_capacity_t[tech,"All",area,year]
        else:
            return Constraint.Skip
    model.Technology_Capacity_areaCtr=Constraint(model.TECHNOLOGIES,model.AREAS,model.YEAR,rule=Technology_Capacity_area_rule)


    def Added_removed_capacity_rule(model,tech,sector,area,year):
        Tot=0
        # lifetime=model.P_lifetime[tech,area,year]

        for y in model.YEAR:
            tech_exists=False
            resource = model.P_capacity_associated_resource[tech, sector, area, year]
            if resource != 0:
                for tech_type in model.TECH_TYPE:
                    if model.P_conversion_factor[tech, tech_type, sector, resource, year] != 0:
                        tech_exists = True
            if tech_exists:
                lifetime = model.P_lifetime[tech,sector, area, y]-model.P_tech_age[tech,sector,area,y]

                if y<=year:
                    # past_year=y
                    # if year-past_year<=lifetime-1:
                    if y+lifetime-year>0:
                        Tot+=model.V_added_capacity[tech,sector,area,y]-model.V_removed_capacity[tech,sector,area,y]

        return model.V_technology_use_coef_capacity[tech,sector,area,year]==Tot

    model.Added_removed_capacity_Ctr=Constraint(model.TECHNOLOGIES, model.SECTOR,model.AREAS,model.YEAR,rule=Added_removed_capacity_rule)

    def Added_capacity_value_rule(model,tech,sector,area,year):
        tech_exists = False
        resource=model.P_capacity_associated_resource[tech,sector,area,year]
        if resource!=0:
            for tech_type in t_tt_combinations[tech]:
                if model.P_conversion_factor[tech, tech_type, sector, resource, year] != 0:
                    tech_exists = True
        if tech_exists:
            return Constraint.Skip
        else:
            return model.V_added_capacity[tech,sector,area,year]==0
    model.Added_capacity_valueCtr=Constraint(model.TECHNOLOGIES, model.SECTOR,model.AREAS,model.YEAR,rule=Added_capacity_value_rule)

    def Added_capacity_ramp_rule(model,tech,sector,area,year):
        if model.P_installation_ramp_t[tech,sector,area,year]!=0:
            return model.V_added_capacity[tech,sector,area,year]<=model.P_installation_ramp_t[tech,sector,area,year]
        else:
            return Constraint.Skip
    model.Added_capacity_rampCtr=Constraint(model.TECHNOLOGIES,model.SECTOR,model.AREAS,model.YEAR,rule=Added_capacity_ramp_rule)

    def Added_capacity_ramp_area_rule(model,tech,area,year):
        if model.P_installation_ramp_t[tech,"All",area,year]!=0:
            return sum(model.V_added_capacity[tech,sector,area,year] for sector in model.SECTOR)<=model.P_installation_ramp_t[tech,"All",area,year]
        else:
            return Constraint.Skip
    model.Added_capacity_ramp_areaCtr=Constraint(model.TECHNOLOGIES,model.AREAS,model.YEAR,rule=Added_capacity_ramp_area_rule)


    def Tech_use_coef_1st_rule(model,tech,tech_type,sector,area,year):
        if tech_type in t_tt_combinations[tech]:
            return model.V_technology_tech_type_use_coef_capacity[tech, tech_type,sector,area, year]>=model.V_technology_use_coef[tech,tech_type,sector,area,year]
        else:
            return model.V_technology_use_coef[tech, tech_type,sector,area, year]==0
    model.Tech_use_coef_1stCtr=Constraint(model.TECHNOLOGIES,model.TECH_TYPE,model.SECTOR,model.AREAS,model.YEAR,rule=Tech_use_coef_1st_rule)

    def Tech_use_coef_2nd_rule(model,tech,sector,area,year):
        return sum(model.V_technology_tech_type_use_coef_capacity[tech, tech_type,sector,area,year] for tech_type in t_tt_combinations[tech])==model.V_technology_use_coef_capacity[tech,sector,area,year]

    model.Tech_use_coef_2ndCtr = Constraint(model.TECHNOLOGIES, model.SECTOR, model.AREAS,model.YEAR,
                                            rule=Tech_use_coef_2nd_rule)

    def Tech_use_coef_3rd_rule(model,tech,sector,area,year):
        if model.P_max_capacity_t[tech,sector,area,year]!=0:
            return model.V_technology_use_coef_capacity[tech,sector,area,year]<=model.P_max_capacity_t[tech,sector,area,year]
        else:
            return Constraint.Skip
    model.Tech_use_coef_3rdCtr = Constraint(model.TECHNOLOGIES, model.SECTOR, model.AREAS,model.YEAR, rule=Tech_use_coef_3rd_rule)
    #
    return model