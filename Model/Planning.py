from pyomo.environ import *
from pyomo.core import *
from pyomo.opt import SolverFactory
from datetime import timedelta
import pandas as pd
import numpy as np
import re
import sys

def Capacity_planning(model,t_tt_combinations,s_t_combinations):
    def Technology_Capacity_rule(model,tech,sector,area,year):
        if model.P_max_capacity_t[tech,sector,area,year]>0:
            resource = model.P_capacity_associated_resource[tech,sector,area,year]
            return sum(model.V_resource_tech_type_capacity[tech,tech_type,sector,resource,area,year] for tech_type in t_tt_combinations[tech])<=model.P_max_capacity_t[tech,sector,area,year]
        else:
            return Constraint.Skip
    model.Technology_CapacityCtr=Constraint(model.TECHNOLOGIES_SECTOR,model.AREAS,model.YEAR,rule=Technology_Capacity_rule)

    def Technology_Capacity_2nd_rule(model,tech,tech_type,sector,resource,area,year):
        if tech_type in t_tt_combinations[tech]:
            if model.P_conversion_factor[tech, tech_type, sector, resource, year]<=0:
                return model.V_resource_tech_type_capacity[tech,tech_type,sector,resource,area,year]>=\
                       model.V_resource_tech_type_outflow[tech,tech_type,sector,resource,area,year]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.Technology_Capacity2ndCtr=Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR,model.RESOURCES,model.AREAS,model.YEAR,rule=Technology_Capacity_2nd_rule)

    def Technology_Capacity_3rd_rule(model,tech,tech_type,sector,resource,area,year):
        if tech_type in t_tt_combinations[tech]:
            return model.V_resource_tech_type_capacity[tech,tech_type,sector,resource,area,year]== \
                   model.V_technology_tech_type_use_coef_capacity[tech, tech_type, sector, area, year] * \
                   -model.P_conversion_factor[tech, tech_type, sector, resource, year]
        else:
            return Constraint.Skip #model.V_resource_tech_type_capacity[tech,tech_type,sector,resource,area,year]==0

    model.Technology_Capacity3rdCtr=Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR,model.RESOURCES,model.AREAS,model.YEAR,rule=Technology_Capacity_3rd_rule)

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
    model.Technology_Capacity_4thCtr=Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR,model.AREAS,model.YEAR,rule=Technology_Capacity_4th_rule)

    def Technology_Capacity_area_rule(model,tech,area,year):
        if model.P_max_capacity_t[tech,"All",area,year]>0:
            resource = model.P_capacity_associated_resource[tech,"All",area,year]
            sect_list=[]
            for sect in model.SECTOR:
                try:
                    s_t_combinations[sect].index(tech)
                    sect_list.append(sect)
                except:
                    return Constraint.Skip

            return sum(model.V_resource_tech_type_capacity[tech,tech_type,sector,resource,area,year] for tech_type in t_tt_combinations[tech] for sector in sect_list)<=model.P_max_capacity_t[tech,"All",area,year]
        else:
            return Constraint.Skip
    model.Technology_Capacity_areaCtr=Constraint(model.TECHNOLOGIES,model.AREAS,model.YEAR,rule=Technology_Capacity_area_rule)




    # model.V_added_bin = Var(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR, initialize=0,
    #                         domain=NonNegativeIntegers)
    # # model.V_removed_bin = Var(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,model.YEAR, initialize=0,
    # #                           domain=NonNegativeIntegers)
    # model.V_removed_bin = Var(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR, initialize=0,
    #                           domain=NonNegativeIntegers)
    # model.V_removed_capacity_overall=Var(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR, initialize=0,
    #                           domain=NonNegativeReals)
    #
    # def Removed_capacity_overall_rule(model, tech, sector, area, year):
    #     return model.V_removed_capacity_overall[tech, sector, area, year]==sum(model.V_removed_capacity[tech, sector, area, ys,year] for ys in model.YEAR)
    #
    # def Added_bin_rule(model, tech, sector, area, year):
    #     return model.V_added_capacity[tech, sector, area, year] <= 1e9 * model.V_added_bin[
    #         tech, sector, area, year]
    #
    # # def Removed_bin_rule(model, tech, sector, area,year_start,year):
    #     # return model.V_removed_capacity[tech, sector, area, year_start,year] <= 1e9 * model.V_removed_bin[
    #     #     tech, sector, area, year_start,year]
    # def Removed_bin_rule(model, tech, sector, area,year):
    #     return model.V_removed_capacity_overall[tech, sector, area, year] <= 1e9 * model.V_removed_bin[
    #         tech, sector, area, year]
    #
    # # def Added_removed_bin_rule(model, tech, sector, area, year_start,year):
    # #     return model.V_added_bin[tech, sector, area, year] + model.V_removed_bin[tech, sector, area, year_start,year] == 1
    # def Added_removed_bin_rule(model, tech, sector, area,year):
    #     return model.V_added_bin[tech, sector, area, year] + model.V_removed_bin[tech, sector, area, year] == 1
    #
    # model.Removed_capacity_overallCtr=Constraint(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR, rule=Removed_capacity_overall_rule)
    #
    # model.Added_binCtr = Constraint(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR, rule=Added_bin_rule)
    # # model.Removed_binCtr = Constraint(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,model.YEAR, rule=Removed_bin_rule)
    # model.Removed_binCtr = Constraint(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,rule=Removed_bin_rule)
    # # model.Added_removed_binCtr = Constraint(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,model.YEAR,
    # #                                         rule=Added_removed_bin_rule)
    # model.Added_removed_binCtr = Constraint(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,
    #                                         rule=Added_removed_bin_rule)
    def Capacity_def_rule(model, tech, sector, area, year):
        # return model.V_technology_use_coef_capacity[tech, sector, area, year] == sum(
        #     model.V_added_capacity[tech, sector, area, ys] - \
        #     sum(model.V_removed_capacity[tech, sector, area, ys, y] + model.V_end_of_life_capacity[
        #         tech, sector, area, ys, y]
        #         for y in range(ys,year + 1))
        #     for ys in range(min(getattr(model, "YEAR").data()), year + 1))
        return model.V_technology_use_coef_capacity[tech, sector, area, year] == sum(
            model.V_added_capacity[tech, sector, area, ys] - \
            sum(model.V_removed_capacity[tech, sector, area, ys, y] #+ \
                #model.V_end_of_life_capacity[tech, sector, area, ys, y]
                for y in range(ys+1, year + 1))
            for ys in range(min(getattr(model, "YEAR").data()), year + 1))
    model.Capacity_defCtr=Constraint(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,rule=Capacity_def_rule)

    # def Removed_capacity_def_rule(model,tech,sector,area,year_start,year):
    #     lifetime = model.P_lifetime[tech, sector, area, year_start] - model.P_tech_age[tech, sector, area, year_start]
    #     if year_start+int(lifetime)>year and year>year_start :# and year>2029: #
    #         return Constraint.Skip
    #         # return model.V_removed_capacity[tech, sector, area, year_start,year]<=model.V_added_capacity[tech, sector, area, year_start]-\
    #         #     sum(model.V_removed_capacity[tech, sector, area, year_start,y] #for y in range(min(getattr(model, "YEAR").data()), year))
    #         #         for y in range(year_start, year))
    #     elif year_start+int(lifetime)==year:
    #         # return model.V_removed_capacity[tech, sector, area, year_start, year] == 0#Constraint.Skip
    #         return model.V_removed_capacity[tech, sector, area, year_start, year] == model.V_added_capacity[
    #             tech, sector, area, year_start] - sum(model.V_removed_capacity[tech, sector, area, year_start, y]
    #                 for y in range(year_start, year))
    #     else:
    #         return model.V_removed_capacity[tech, sector, area, year_start, year] == 0
    def Removed_capacity_def_2nd_rule(model, tech, sector, area, year_start):
        lifetime = model.P_lifetime[tech, sector, area, year_start] - model.P_tech_age[tech, sector, area, year_start]
        if year_start+int(lifetime)+1<=max(getattr(model, "YEAR").data()) and year_start<max(getattr(model, "YEAR").data()) :
            return model.V_added_capacity[
                    tech, sector, area, year_start]-sum(model.V_removed_capacity[tech, sector, area, year_start, y]#+\
                                                        #model.V_end_of_life_capacity[tech, sector, area, year_start, y]
                                                        for y in range(year_start+1,year_start+int(lifetime)+1))==0
        else:
            return Constraint.Skip
    # model.Removed_capacity_defCtr=Constraint(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,model.YEAR,rule=Removed_capacity_def_rule)
    model.Removed_capacity_def_2ndCtr = Constraint(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,rule=Removed_capacity_def_2nd_rule)

    # def End_of_life_def_rule(model,tech,sector,area,year_start,year):
    #     lifetime = model.P_lifetime[tech, sector, area, year_start] - model.P_tech_age[tech, sector, area, year_start]
    #     if year_start+int(lifetime)==year:
    #         return model.V_end_of_life_capacity[tech, sector, area, year_start, year] == \
    #                     model.V_added_capacity[tech, sector, area, year_start]-\
    #             sum(model.V_removed_capacity[tech, sector, area, year_start,y] for y in range(year_start,year))
    #     else:
    #         return model.V_end_of_life_capacity[tech, sector, area, year_start, year] == 0
    # model.End_of_life_defCtr=Constraint(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,model.YEAR,rule=End_of_life_def_rule)



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
    model.Added_capacity_valueCtr=Constraint(model.TECHNOLOGIES_SECTOR,model.AREAS,model.YEAR,rule=Added_capacity_value_rule)

    # def Added_capacity_ramp_rule(model,tech,sector,area,year):
    #     if model.P_installation_ramp_t[tech,sector,area,year]!=0:
    #         return model.V_added_capacity[tech,sector,area,year]<=model.P_installation_ramp_t[tech,sector,area,year]
    #     else:
    #         return Constraint.Skip
    def Added_capacity_ramp_rule(model, tech, sector, area, year):
        if year>min(getattr(model, "YEAR").data()) and model.P_installation_ramp_t[tech,sector,area,year]!=0:
            return model.V_technology_use_coef_capacity[tech,sector,area,year]-model.V_technology_use_coef_capacity[tech,sector,area,year-1]<=model.P_installation_ramp_t[tech,sector,area,year]
        else:
            return Constraint.Skip
    model.Added_capacity_rampCtr = Constraint(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,rule=Added_capacity_ramp_rule)

    # def Added_capacity_ramp_area_rule(model,tech,area,year):
    #     if model.P_installation_ramp_t[tech,"All",area,year]!=0:
    #         sect_list = []
    #         for sect in model.SECTOR:
    #             try:
    #                 s_t_combinations[sect].index(tech)
    #                 sect_list.append(sect)
    #             except:
    #                 return Constraint.Skip
    #         return sum(model.V_added_capacity[tech,sector,area,year] for sector in sect_list)<=model.P_installation_ramp_t[tech,"All",area,year]
    #     else:
    #         return Constraint.Skip

    def Added_capacity_ramp_area_rule(model,tech,area,year):
        if year>min(getattr(model, "YEAR").data()) and model.P_installation_ramp_t[tech,"All",area,year]!=0:
            sect_list = []
            for sect in model.SECTOR:
                try:
                    s_t_combinations[sect].index(tech)
                    sect_list.append(sect)
                except:
                    return Constraint.Skip
            return sum(model.V_technology_use_coef_capacity[tech,sector,area,year]-model.V_technology_use_coef_capacity[tech,sector,area,year-1] for sector in sect_list)<=model.P_installation_ramp_t[tech,"All",area,year]
        else:
            return Constraint.Skip

    model.Added_capacity_ramp_areaCtr=Constraint(model.TECHNOLOGIES,model.AREAS,model.YEAR,rule=Added_capacity_ramp_area_rule)

    def Tech_type_change_ramp_rule(model,tech,tech_type,sector,area,year):
        if year>min(getattr(model, "YEAR").data()):
            return model.V_technology_tech_type_use_coef_capacity[tech,tech_type,sector,area,year]-\
                    model.V_technology_tech_type_use_coef_capacity[tech,tech_type,sector,area,year-1]<=model.P_installation_ramp_t[tech,sector,area,year]+\
                   model.V_added_capacity[tech,sector,area,year]
        else:
            return Constraint.Skip
    model.Tech_type_change_ramp_rule=Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR,model.AREAS,model.YEAR,rule=Tech_type_change_ramp_rule)
    def Tech_use_coef_1st_rule(model,tech,tech_type,sector,area,year):
        if tech_type in t_tt_combinations[tech]:
            return model.V_technology_tech_type_use_coef_capacity[tech, tech_type,sector,area, year]>=model.V_technology_use_coef[tech,tech_type,sector,area,year]
        else:
            return model.V_technology_use_coef[tech, tech_type,sector,area, year]==0
    model.Tech_use_coef_1stCtr=Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR,model.AREAS,model.YEAR,rule=Tech_use_coef_1st_rule)

    def Tech_use_coef_2nd_rule(model,tech,sector,area,year):
        return sum(model.V_technology_tech_type_use_coef_capacity[tech, tech_type,sector,area,year] for tech_type in t_tt_combinations[tech])==model.V_technology_use_coef_capacity[tech,sector,area,year]

    model.Tech_use_coef_2ndCtr = Constraint(model.TECHNOLOGIES_SECTOR, model.AREAS,model.YEAR,
                                            rule=Tech_use_coef_2nd_rule)

    def Tech_use_coef_3rd_rule(model,tech,sector,area,year):
        if model.P_max_capacity_t[tech,sector,area,year]!=0:
            return model.V_technology_use_coef_capacity[tech,sector,area,year]<=model.P_max_capacity_t[tech,sector,area,year]
        else:
            return Constraint.Skip
    model.Tech_use_coef_3rdCtr = Constraint(model.TECHNOLOGIES_SECTOR, model.AREAS,model.YEAR, rule=Tech_use_coef_3rd_rule)
    #
    return model