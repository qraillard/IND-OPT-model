from pyomo.environ import *
from pyomo.core import *
from pyomo.opt import SolverFactory
from datetime import timedelta
import pandas as pd
import numpy as np
import re
import sys

def Cost_Emissions_Obj_Ctr(model,t_tt_combinations,s_t_combinations):
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
                       for tech_type in t_tt_combinations[tech]) for tech in s_t_combinations[sector]) + \
               sum(model.V_technology_cost[tech,sector, area, year] for tech in s_t_combinations[sector]) + \
               sum(model.P_opex_cost[tech,sector, area, year] * model.V_technology_use_coef_capacity[tech,sector, area, year] for tech
                   in s_t_combinations[sector]) + \
               model.V_carbon_cost[sector,area,year] + \
               model.V_ccs_capex_cost[sector,area,year] + model.V_ccs_opex_cost[sector,area,year]


    model.Cost_definitionCtr = Constraint(model.SECTOR,model.AREAS, model.YEAR, rule=Cost_definition_rule)

    def Technology_cost_definition_rule(model, tech,sector, area, year):
        # Tot = 0
        # for y in model.YEAR:
        #     subTot = 0
        #     tech_exists = False
        #     for resource in model.RESOURCES:
        #         for tech_type in t_tt_combinations[tech]:
        #             if model.P_conversion_factor[tech, tech_type, sector, resource, y] != 0:
        #                 tech_exists = True
        #     if tech_exists:
        #         if y <= year:
        #             if model.P_lifetime[tech,sector, area, y] != 0 or model.P_construction_time[tech,sector, area, y] != 0:
        #                 n =  model.P_lifetime[tech,sector, area, y] #+model.P_construction_time[tech,sector, area, y]
        #                 i = model.P_discount_rate[tech,sector, area, y]
        #                 CRF = i * (i + 1) ** n / ((1 + i) ** n - 1)
        #                 # ROI_ratio = 0
        #                 if y + n - year - model.P_tech_age[tech,sector, area, y] > 0:
        #                     # ROI_ratio = CRF * (y + n - year)
        #                     subTot += model.P_capex[tech,sector, area, y] * CRF *(model.V_added_capacity[tech,sector, area, y])
        #     Tot += subTot
        #
        #
        # return model.V_technology_cost[tech,sector, area, year] == Tot
        return model.V_technology_cost[tech,sector, area, year]==sum(model.P_capex[tech,sector, area, y]* \
            model.P_discount_rate[tech, sector, area, y] *(1+model.P_discount_rate[tech,sector, area, y])**(model.P_lifetime[tech,sector, area, y])/\
                                                                     ((1+model.P_discount_rate[tech,sector, area, y])**(model.P_lifetime[tech,sector, area, y])-1)* \
                                                                     model.V_counted_added_capacity[tech, sector, area, y, year]
                                                                     for y in range(min(getattr(model, "YEAR").data()), year + 1))

    model.Technology_cost_definitionCtr = Constraint(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,
                                                     rule=Technology_cost_definition_rule)

    def Capacity_for_capex_rule(model,tech,sector,area,year_start,year):
        lifetime = model.P_lifetime[tech, sector, area, year_start] - model.P_tech_age[tech, sector, area, year_start]
        if year_start+lifetime>year:
            return model.V_counted_added_capacity[tech,sector,area,year_start,year]==model.V_added_capacity[tech,sector, area, year_start]
        else:
            return model.V_counted_added_capacity[tech, sector, area, year_start, year]==0
    model.Capacity_for_capexCtr=Constraint(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,model.YEAR,rule=Capacity_for_capex_rule)

    def Emissions_definition_rule(model,sector, area, year):
        if sector!="E-Fuels":
            return model.V_emissions[sector,area, year] == sum(sum(
                model.V_emissions_tech_type_plus[tech, tech_type,sector, area, year] for tech_type in
                t_tt_combinations[tech])-model.V_captured_emissions[tech,sector,area,year] for tech in s_t_combinations[sector]) + \
                   sum(model.P_emissions_r[resource,sector, area, year] * model.V_resource_imports[resource,sector, area, year] for resource
                       in model.RESOURCES)+sum(sum(model.V_emissions_tech_type_minus[tech, tech_type,sector, area, year] for tech_type in
                t_tt_combinations[tech]) for tech in ["Biogas_Digester","Biomass_low_price","Biomass_med_price","Biomass_high_price","Municipal_wastes","Agriculture_wastes"])-\
                model.V_resource_outflow["DAC_CO2",sector,area,year]+\
                model.P_methane_leakage_ratio[sector,area,year]*model.V_resource_inflow["Gas",sector,area,year]*model.P_methane_gwp[sector,area,year]+ \
                model.V_olefins_end_of_life_emissions[sector, area, year]
        else:
            return model.V_emissions[sector,area, year] == sum(sum(
                model.V_emissions_tech_type_plus[tech, tech_type,sector, area, year] for tech_type in
                t_tt_combinations[tech])-model.V_captured_emissions[tech,sector,area,year] for tech in s_t_combinations[sector]) + \
                   sum(model.P_emissions_r[resource,sector, area, year] * model.V_resource_imports[resource,sector, area, year] for resource
                       in model.RESOURCES)+sum(sum(model.V_emissions_tech_type_minus[tech, tech_type,sector, area, year] for tech_type in
                t_tt_combinations[tech]) for tech in ["Biogas_Digester","Biomass_low_price","Biomass_med_price","Biomass_high_price","Municipal_wastes","Agriculture_wastes"])-\
                model.V_resource_outflow["DAC_CO2",sector,area,year]+\
                model.P_methane_leakage_ratio[sector,area,year]*model.V_resource_inflow["Gas",sector,area,year]*model.P_methane_gwp[sector,area,year]+ \
                model.V_olefins_end_of_life_emissions[sector, area, year]+\
                model.V_resource_exports["MeOH",sector,area,year]*1.37+model.V_resource_exports["E-Kerosene",sector,area,year]*3.056 #combustion emissions from e-fuels
    model.Emissions_definitionCtr = Constraint(model.SECTOR,model.AREAS, model.YEAR, rule=Emissions_definition_rule)



    def Technology_emissions_definition_1st_rule(model, tech, tech_type,sector, area, year):
        if tech_type in t_tt_combinations[tech]:
            return model.V_emissions_tech_type[tech, tech_type,sector, area, year] == model.V_emissions_tech_type_plus[
                tech, tech_type,sector, area, year] + model.V_emissions_tech_type_minus[tech, tech_type, sector, area, year]
        else:
            return Constraint.Skip

    model.Technology_emissions_definition_1stCtr = Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS,
                                                              model.YEAR, rule=Technology_emissions_definition_1st_rule)

    def Technology_emissions_definition_2nd_rule(model, tech, tech_type,sector, area, year):
        if tech_type in t_tt_combinations[tech]:
            return model.V_emissions_tech_type[tech, tech_type,sector, area, year] == -model.P_conversion_factor[tech, tech_type,sector, "CO2", year] * \
                   model.V_technology_use_coef[tech, tech_type,sector, area, year]
        else:
            return Constraint.Skip #model.V_emissions_tech_type[tech, tech_type,sector, area, year]==0

    model.Technology_emissions_definition_2ndCtr = Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS,
                                                              model.YEAR,
                                                              rule=Technology_emissions_definition_2nd_rule)
    def Technology_emissions_definition_3rd_rule(model, tech, tech_type,sector, area, year):
        if model.P_conversion_factor[tech, tech_type,sector, "CO2", year]>=0:
            return model.V_emissions_tech_type_plus[tech, tech_type,sector, area, year] == 0
        else:
            return model.V_emissions_tech_type_minus[tech, tech_type,sector, area, year] == 0

    model.Technology_emissions_definition_3rdCtr = Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS,
                                                              model.YEAR,
                                                              rule=Technology_emissions_definition_3rd_rule)

    # def Technology_emissions_definition_3rd_rule(model, sector, area, year):
    #     return sum(sum(model.V_emissions_tech_type[tech, tech_type,sector, area, year] for tech_type in t_tt_combinations[tech]) for tech in model.TECHNOLOGIES)>=0

    # model.Technology_emissions_definition_3rdCtr = Constraint(model.SECTOR, model.AREAS,
    #                                                           model.YEAR,
    #                                                           rule=Technology_emissions_definition_3rd_rule)




    def Carbon_cost_rule(model,sector,area,year):
        # return model.V_carbon_cost[sector, area, year] == model.P_carbon_tax[sector,area,year]*(model.V_ctax_emissions_plus[sector, area, year]+model.V_efuels_taxed_co2_consumption[sector, area, year])
        return model.V_carbon_cost[sector, area, year] == model.P_carbon_tax[sector, area, year] *model.V_ctax_emissions[sector, area, year]

    model.Carbon_costCtr=Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=Carbon_cost_rule)

    # def Ctax_emissions_rule(model,sector,area,year):
    #     if model.P_CCU_negative_emissions:
    #         return model.V_ctax_emissions_plus[sector, area, year]+ model.V_ctax_emissions_minus[sector, area, year] == \
    #                sum(sum(
    #                    model.V_emissions_tech_type[tech, tech_type, sector, area, year] for tech_type in
    #                    t_tt_combinations[tech]) - model.V_captured_emissions[tech, sector, area, year] for tech in
    #                    s_t_combinations[sector]) + \
    #                sum(model.P_emissions_r[resource, sector, area, year] * model.V_resource_imports[
    #                    resource, sector, area, year] for resource
    #                    in model.CTAX_RESOURCES)-model.V_resource_outflow["DAC_CO2",sector,area,year]+\
    #         model.P_methane_leakage_ratio[sector,area,year]*model.V_resource_inflow["Gas",sector,area,year]*model.P_methane_gwp[sector,area,year]+ \
    #             model.V_olefins_end_of_life_emissions[sector, area, year]
    #     else:
    #         # if sector!="E-Fuels":
    #         return model.V_ctax_emissions_plus[sector, area, year] + model.V_ctax_emissions_minus[sector, area, year] == \
    #                 sum(sum(
    #                     model.V_emissions_tech_type_plus[tech, tech_type, sector, area, year] for tech_type in
    #                     t_tt_combinations[tech]) - model.V_captured_emissions[tech, sector, area, year] for tech in
    #                     s_t_combinations[sector]) + \
    #                 sum(model.P_emissions_r[resource, sector, area, year] * model.V_resource_imports[
    #                     resource, sector, area, year] for resource
    #                     in model.CTAX_RESOURCES)+sum(sum(model.V_emissions_tech_type_minus[tech, tech_type,sector, area, year] for tech_type in
    #             t_tt_combinations[tech]) for tech in ["Biogas_Digester","Biomass_low_price","Biomass_med_price","Biomass_high_price","Municipal_wastes","Agriculture_wastes"])-\
    #                 model.V_resource_outflow["DAC_CO2",sector,area,year]+\
    #             model.P_methane_leakage_ratio[sector,area,year]*model.V_resource_inflow["Gas",sector,area,year]*model.P_methane_gwp[sector,area,year]+ \
    #             model.V_olefins_end_of_life_emissions[sector,area,year]
    def Ctax_emissions_rule(model,sector,area,year):
        if sector !="E-Fuels":
            return model.V_ctax_emissions[sector, area, year] == \
                                sum(sum(
                                model.V_emissions_tech_type_plus[tech, tech_type, sector, area, year] for tech_type in
                                t_tt_combinations[tech]) - model.V_captured_emissions[tech, sector, area, year] for tech in
                                s_t_combinations[sector]) + \
                            sum(model.P_emissions_r[resource, sector, area, year] * model.V_resource_imports[
                                resource, sector, area, year] for resource
                                in model.CTAX_RESOURCES)+sum(sum(model.V_emissions_tech_type_minus[tech, tech_type,sector, area, year] for tech_type in
                        t_tt_combinations[tech]) for tech in ["Biogas_Digester","Biomass_low_price","Biomass_med_price","Biomass_high_price","Municipal_wastes","Agriculture_wastes"])-\
                            model.V_resource_outflow["DAC_CO2",sector,area,year]+\
                        model.P_methane_leakage_ratio[sector,area,year]*model.V_resource_inflow["Gas",sector,area,year]*model.P_methane_gwp[sector,area,year]+ \
                        model.V_olefins_end_of_life_emissions[sector,area,year]
        else:
            return model.V_ctax_emissions[sector, area, year] == \
                                sum(sum(
                                model.V_emissions_tech_type_plus[tech, tech_type, sector, area, year] for tech_type in
                                t_tt_combinations[tech]) - model.V_captured_emissions[tech, sector, area, year] for tech in
                                s_t_combinations[sector]) + \
                            sum(model.P_emissions_r[resource, sector, area, year] * model.V_resource_imports[
                                resource, sector, area, year] for resource
                                in model.CTAX_RESOURCES)+sum(sum(model.V_emissions_tech_type_minus[tech, tech_type,sector, area, year] for tech_type in
                        t_tt_combinations[tech]) for tech in ["Biogas_Digester","Biomass_low_price","Biomass_med_price","Biomass_high_price","Municipal_wastes","Agriculture_wastes"])-\
                            model.V_resource_outflow["DAC_CO2",sector,area,year]+\
                        model.P_methane_leakage_ratio[sector,area,year]*model.V_resource_inflow["Gas",sector,area,year]*model.P_methane_gwp[sector,area,year]+ \
                        model.V_olefins_end_of_life_emissions[sector,area,year] +\
                        model.V_resource_exports["MeOH", sector, area, year] * 1.37 +\
                        model.V_resource_exports["E-Kerosene", sector, area, year] * 3.056  # combustion emissions from e-fuels


    model.Ctax_emissionsCtr=Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=Ctax_emissions_rule)

    def Ctax_emissions_2nd_rule(model,area,year):
        return sum(model.V_ctax_emissions[sector,area, year] for sector in model.SECTOR) >= 0
    model.Ctax_emissions_2ndCtr = Constraint( model.AREAS, model.YEAR, rule=Ctax_emissions_2nd_rule)
    def Emissions_reduction_rule(model,sector,area,year):
        year_ini=min(getattr(model, "YEAR").data())
        if model.P_emissions_reduction_ratio_obj[sector,area,year]!=0 and year > year_ini:
            return model.V_emissions[sector,area,year]<=(1-model.P_emissions_reduction_ratio_obj[sector,area,year])*model.V_emissions[sector,area,year_ini]
        else:
            return Constraint.Skip

    model.Emissions_reductionCtr=Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=Emissions_reduction_rule)

    def Emissions_reduction_overall_rule(model,area,year):
        year_ini=min(getattr(model, "YEAR").data())
        if model.P_emissions_reduction_ratio_obj["All",area,year]!=0 and year > year_ini:
            return sum(model.V_emissions[sector,area,year] for sector in model.SECTOR)<=(1-model.P_emissions_reduction_ratio_obj["All",area,year])*sum(model.V_emissions[sector,area,year_ini] for sector in model.SECTOR)
        else:
            return Constraint.Skip

    model.Emissions_reduction_overallCtr=Constraint(model.AREAS,model.YEAR,rule=Emissions_reduction_overall_rule)

    # def Efuels_ctax_CO2(model):
    #
    #
    #     def Efuels_ctax_CO2_1st_rule(model,sector,area,year):
    #         # if sector!="E-Fuels":
    #         return model.V_resource_inflow["CO2",sector,area,year]==model.V_efuels_taxed_co2_consumption[sector,area,year]+model.V_efuels_untaxed_co2_consumption[sector,area,year]
    #         # else:
    #         #     return model.V_resource_inflow["CO2", sector, area, year] == model.V_efuels_taxed_co2_consumption[
    #         #         sector, area, year] + model.V_efuels_untaxed_co2_consumption[sector, area, year]-1.37*model.V_resource_outflow["MeOH",sector,area,year]
    #     def Efuels_ctax_CO2_2nd_rule(model,sector,area,year):
    #         if sector!="E-Fuels":
    #             return model.V_efuels_taxed_co2_consumption[sector,area,year]==0
    #         else:
    #             return model.V_efuels_untaxed_co2_consumption[sector,area,year]<=model.V_resource_outflow["DAC_CO2",sector,area,year]+ \
    #                 sum(model.V_captured_emissions["Gasification", s, area, year] for s in model.SECTOR)
    #     # def Efuels_ctax_CO2_3rd_rule(model,sector,area,year):
    #     #     if sector!="E-Fuels":
    #     #         return Constraint.Skip
    #     #     else:
    #     #         return model.V_efuels_taxed_co2_consumption[sector,area,year]>=1.37*model.V_resource_outflow["MeOH",sector,area,year] #1.37kgCO2 per kgMeOH burnt
    #
    #     model.Efuels_ctax_CO2_1stCtr = Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=Efuels_ctax_CO2_1st_rule)
    #     model.Efuels_ctax_CO2_2ndCtr = Constraint(model.SECTOR, model.AREAS, model.YEAR, rule=Efuels_ctax_CO2_2nd_rule)
    #     # model.Efuels_ctax_CO2_3rCtr = Constraint(model.SECTOR, model.AREAS, model.YEAR, rule=Efuels_ctax_CO2_3rd_rule)
    #
    #     return model
    # model=Efuels_ctax_CO2(model)

    def Olefins_end_of_life_rule(model,sector,area,year):
            return model.V_olefins_end_of_life_emissions[sector,area,year]==\
                model.V_resource_outflow["Olefins",sector,area,year]*(1-model.P_olefins_carbone_storage_rate[sector,area,year])*1.5*3
    model.Olefins_end_of_lifeCtr=Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=Olefins_end_of_life_rule)
    return model