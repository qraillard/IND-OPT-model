from pyomo.environ import *
from pyomo.core import *
from pyomo.opt import SolverFactory
from datetime import timedelta
import pandas as pd
import numpy as np
import re
import sys

def CCS_specific_Ctr(model,t_tt_combinations,s_t_combinations,sector_tech_ccs_combinations):
    def ccs_max_capacity_rule(model,tech,tech_type,sector,area,year):
        if tech_type in t_tt_combinations[tech]:
            return sum(model.V_ccs_tech_type_capacity[ccs, tech, tech_type, sector, area, year] for ccs in sector_tech_ccs_combinations[sector][tech])<= \
                   model.V_technology_tech_type_use_coef_capacity[tech,tech_type,sector, area, year]
        else:
            return Constraint.Skip
    model.ccs_max_capacityCtr=Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR_CCS_SPECIFIC,model.AREAS,model.YEAR,rule=ccs_max_capacity_rule)

    def ccs_max_capacity_2nd_rule(model,tech,sector,area,year):
        return sum(model.V_ccs_capacity[ccs, tech, sector, area, year] for ccs in sector_tech_ccs_combinations[sector][tech])<= \
               model.V_technology_use_coef_capacity[tech,sector, area, year]
    model.ccs_max_capacity_2ndCtr=Constraint(model.TECHNOLOGIES_SECTOR_CCS_SPECIFIC,model.AREAS,model.YEAR,rule=ccs_max_capacity_2nd_rule)

    def ccs_capacity_1st_rule(model,ccs, tech, sector, area, year):
        return sum(model.V_ccs_tech_type_capacity[ccs,tech,tech_type,sector, area, year] for tech_type in t_tt_combinations[tech]) == \
               model.V_ccs_capacity[ccs, tech, sector, area, year]
    model.ccs_capacity_1stCtr = Constraint(model.CCS_TYPE_TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,
                                           rule=ccs_capacity_1st_rule)

    def ccs_capacity_2nd_rule(model,ccs, tech,tech_type, sector, area, year):
        if tech_type in t_tt_combinations[tech]:
            return model.V_ccs_tech_type_capacity[ccs,tech,tech_type,sector, area, year] >= model.V_ccs_tech_type_usage[ccs,tech,tech_type,sector, area, year]
        else:
            return Constraint.Skip
    model.ccs_capacity_2ndCtr = Constraint(model.CCS_TYPE_TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS, model.YEAR, rule=ccs_capacity_2nd_rule)

    def ccs_usage_rule(model,tech,tech_type,sector,area,year):
        if tech_type in t_tt_combinations[tech]:
            return sum(model.V_ccs_tech_type_usage[ccs,tech,tech_type,sector, area, year] for ccs in sector_tech_ccs_combinations[sector][tech])<=\
               model.V_technology_use_coef[tech,tech_type,sector, area, year]
        else:
            return Constraint.Skip
    model.ccs_usageCtr = Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR_CCS_SPECIFIC, model.AREAS, model.YEAR,rule=ccs_usage_rule)

    def ccs_opex_rule(model,sector,area,year):
        return model.V_ccs_opex_cost[sector,area,year]==\
               sum(model.P_ccs_opex[ccs, tech, sector, area, year] * model.V_ccs_capacity[ccs, tech, sector, area, year]
                   for tech in sector_tech_ccs_combinations[sector].keys() for ccs in sector_tech_ccs_combinations[sector][tech]) + \
            model.V_stored_emissions[sector, area, year]* model.P_co2_transport_and_storage_cost[
                sector, area, year]

    model.ccs_opexCtr=Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=ccs_opex_rule)

    def ccs_capex_rule(model,sector,area,year):
        return model.V_ccs_capex_cost[sector,area,year]==\
               sum( model.V_ccs_tech_capex_cost[ccs,tech,sector, area, year] for
            tech in sector_tech_ccs_combinations[sector].keys() for ccs in sector_tech_ccs_combinations[sector][tech])
    model.ccs_capexCtr=Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=ccs_capex_rule)

    def ccs_tech_capex_rule(model,ccs,tech,sector,area,year):
        Tot = 0
        for y in model.YEAR:
            subTot = 0
            if y <= year:
                if model.P_ccs_lifetime[ccs,tech, sector, area, y] != 0:
                    n = model.P_ccs_lifetime[ccs,tech, sector, area, y]
                    i = model.P_ccs_discount_rate[ccs,tech, sector, area, y]
                    CRF = i * (i + 1) ** n / ((1 + i) ** n - 1)
                    # ROI_ratio = 0
                    if y + n - year > 0:
                        # ROI_ratio = CRF * (y + n - year)
                        subTot += model.P_ccs_capex[ccs,tech,sector,area,y] * CRF * model.V_ccs_added_capacity[ccs,
                            tech, sector, area, y]
            Tot += subTot
        return model.V_ccs_tech_capex_cost[ccs,tech,sector, area, year] == Tot
    model.ccs_tech_capexCtr=Constraint(model.CCS_TYPE_TECHNOLOGIES_SECTOR,model.AREAS,model.YEAR,rule=ccs_tech_capex_rule)

    def ccs_added_removed_capacity_rule(model,ccs,tech,sector,area,year):
        return model.V_ccs_capacity[ccs,tech,sector,area,year] == sum(
            model.V_ccs_added_capacity[ccs,tech,sector,area, ys] - \
            sum(model.V_ccs_removed_capacity[ccs,tech, sector, area, ys, y] for y in range(ys, year + 1))
            for ys in range(min(getattr(model, "YEAR").data()), year + 1))
    model.ccs_added_removed_capacityCtr=Constraint(model.CCS_TYPE_TECHNOLOGIES_SECTOR,model.AREAS,model.YEAR,rule=ccs_added_removed_capacity_rule)


    def ccs_added_capacity_rule(model,ccs,tech,sector,area,year):
        if model.P_ccs_ratio[ccs,tech,sector,area,year]==0:
            return model.V_ccs_added_capacity[ccs,tech,sector,area, year]==0
        else:
            return Constraint.Skip
    model.ccs_added_capacityCtr=Constraint(model.CCS_TYPE_TECHNOLOGIES_SECTOR,model.AREAS,model.YEAR,rule=ccs_added_capacity_rule)

    def ccs_removed_capacity_def_rule(model,ccs,tech,sector,area,year_start):#,year):
        lifetime = model.P_ccs_lifetime[ccs,tech, sector, area, year_start]
        # if year_start+int(lifetime)>year and year>year_start:
        #     return model.V_ccs_removed_capacity[ccs,tech, sector, area, year_start,year]<=model.V_ccs_added_capacity[ccs,tech, sector, area, year_start]-\
        #         sum(model.V_ccs_removed_capacity[ccs,tech, sector, area, year_start,y] #for y in range(min(getattr(model, "YEAR").data()), year))
        #             for y in range(year_start, year))
        # elif year_start+int(lifetime)==year:
        #     return model.V_ccs_removed_capacity[ccs,tech, sector, area, year_start, year] == model.V_ccs_added_capacity[ccs,
        #         tech, sector, area, year_start] - sum(model.V_ccs_removed_capacity[ccs,tech, sector, area, year_start, y]
        #             for y in range(year_start, year))
        # else:
        #     return model.V_removed_capacity[tech, sector, area, year_start, year] == 0
        if year_start+int(lifetime)+1<=max(getattr(model, "YEAR").data()) and year_start<max(getattr(model, "YEAR").data()) :
            return model.V_ccs_added_capacity[ccs,tech, sector, area, year_start]-sum(model.V_ccs_removed_capacity[ccs,tech, sector, area, year_start,y]
                                                        for y in range(year_start+1,year_start+int(lifetime)+1))==0
        else:
            return Constraint.Skip


    model.ccs_removed_capacity_defCtr=Constraint(model.CCS_TYPE_TECHNOLOGIES_SECTOR,model.AREAS,model.YEAR,#model.YEAR,
                                                             rule=ccs_removed_capacity_def_rule)

    def ccs_captured_emissions_1st_rule(model,ccs,tech,sector,area,year):
        return model.V_ccs_captured_emissions[ccs,tech,sector,area,year] <= model.P_ccs_ratio[ccs,tech,sector,area,year]* \
               sum(model.V_emissions_tech_type_plus[tech, tech_type, sector, area, year] \
                   for tech_type in t_tt_combinations[tech])

    model.ccs_captured_emissions_1stCtr = Constraint(model.CCS_TYPE_TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,
                                                     rule=ccs_captured_emissions_1st_rule)

    def ccs_captured_emissions_2nd_rule(model,tech,sector,area,year):
        return model.V_captured_emissions[tech,sector,area,year]==sum(model.V_ccs_captured_emissions[ccs,tech,sector,area,year] for ccs in sector_tech_ccs_combinations[sector][tech])
    model.ccs_captured_emissions_2ndCtr=Constraint(model.TECHNOLOGIES_SECTOR_CCS_SPECIFIC,model.AREAS,model.YEAR,rule=ccs_captured_emissions_2nd_rule)

    def ccs_captured_emissions_3rd_rule(model,ccs,tech,sector,area,year):
        return model.V_ccs_captured_emissions[ccs,tech,sector,area,year]==sum(model.V_ccs_tech_type_captured_emissions[ccs,tech,tech_type,sector,area,year]
                                                                              for tech_type in t_tt_combinations[tech])
    model.ccs_captured_emissions_3rdCtr=Constraint(model.CCS_TYPE_TECHNOLOGIES_SECTOR,model.AREAS,model.YEAR,rule=ccs_captured_emissions_3rd_rule)

    def ccs_captured_emissions_4th_rule(model,ccs, tech, tech_type, sector, area, year):
        if tech_type in t_tt_combinations[tech]:
            return model.V_ccs_tech_type_captured_emissions[ccs,tech,tech_type,sector,area,year]==model.P_ccs_ratio[ccs, tech, sector, area, year] * \
        model.V_ccs_tech_type_usage[ccs, tech, tech_type, sector, area, year] * \
               -model.P_conversion_factor[tech, tech_type, sector, "CO2", year]
        else:
            return model.V_ccs_tech_type_captured_emissions[ccs,tech,tech_type,sector,area,year]==0 #Constraint.Skip

    model.ccs_captured_emissions_4thCtr = Constraint(model.CCS_TYPE_TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS, model.YEAR,
                                                     rule=ccs_captured_emissions_4th_rule)

    def ccs_captured_emissions_5th_rule(model,tech,sector,area,year):
        return sum(model.V_ccs_captured_emissions[ccs,tech,sector,area,year] for ccs in sector_tech_ccs_combinations[sector][tech])==\
               model.V_captured_emissions[tech,sector,area,year]

    model.ccs_captured_emissions_5thCtr = Constraint(model.TECHNOLOGIES_SECTOR_CCS_SPECIFIC, model.AREAS, model.YEAR,
                                                     rule=ccs_captured_emissions_5th_rule)

    def ccs_captured_emissions_6th_rule(model,ccs, tech, tech_type, sector, area, year):
        if tech_type in t_tt_combinations[tech]:
            if model.P_conversion_factor[tech, tech_type, sector, "CO2", year]>=0:
                return  model.V_ccs_tech_type_usage[ccs, tech, tech_type, sector, area, year]==0
            else:
                return Constraint.Skip
        else:
            return model.V_ccs_tech_type_usage[ccs, tech, tech_type, sector, area, year]==0

    model.ccs_captured_emissions_6thCtr = Constraint(model.CCS_TYPE_TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS, model.YEAR,
                                                     rule=ccs_captured_emissions_6th_rule)

    def ccs_captured_emissions_7th_rule(model,area,year):
        s_t_combinations_no_biogas=s_t_combinations
        for sector in model.SECTOR:
            try:
                s_t_combinations_no_biogas[sector].remove("Biogas_Digester")
            except:
                pass
            try:
                s_t_combinations_no_biogas[sector].remove("Biomass_low_price")
            except:
                pass
            try:
                s_t_combinations_no_biogas[sector].remove("Biomass_med_price")
            except:
                pass
            try:
                s_t_combinations_no_biogas[sector].remove("Biomass_high_price")
            except:
                pass
            try:
                s_t_combinations_no_biogas[sector].remove("Municipal_wastes")
            except:
                pass
            try:
                s_t_combinations_no_biogas[sector].remove("Agriculture_wastes")
            except:
                pass
        return sum(model.V_captured_emissions[tech,sector,area,year] for sector in model.SECTOR for tech in s_t_combinations_no_biogas[sector]) >=\
                      -1*sum(model.V_emissions_tech_type_minus[tech, tech_type, sector, area, year] \
                    for sector in model.SECTOR
                   for tech in s_t_combinations_no_biogas[sector]
                   for tech_type in t_tt_combinations[tech]
                    )

    model.ccs_captured_emissions_7thCtr=Constraint(model.AREAS,model.YEAR,rule=ccs_captured_emissions_7th_rule)

    def ccs_captured_emissions_8th_rule(model,tech,sector, area, year):
        if tech in sector_tech_ccs_combinations[sector].keys():
            return Constraint.Skip
        else:
            return model.V_captured_emissions[tech,sector,area,year]==0

    model.ccs_captured_emissions_8thCtr = Constraint(model.TECHNOLOGIES_SECTOR,model.AREAS, model.YEAR, rule=ccs_captured_emissions_8th_rule)
    def ccs_consumption_rule(model,tech,tech_type,sector,resource,area,year):
        if tech in sector_tech_ccs_combinations[sector].keys():
            if tech_type in t_tt_combinations[tech]:
                if resource=="Electricity":
                    return model.V_ccs_tech_type_consumption[tech,tech_type,sector,resource,area,year]== \
                            sum(model.V_ccs_tech_type_usage[ccs, tech, tech_type, sector, area, year]*\
                                model.P_ccs_elec[ccs, tech, sector, area, year]\
                                for ccs in sector_tech_ccs_combinations[sector][tech])
                elif resource=="Gas":
                    return model.V_ccs_tech_type_consumption[tech,tech_type,sector,resource,area,year]== \
                            sum(model.V_ccs_tech_type_usage[ccs, tech, tech_type, sector, area, year]*\
                                model.P_ccs_gas[ccs, tech, sector, area, year]\
                                for ccs in sector_tech_ccs_combinations[sector][tech])
                elif resource=="Biomass":
                    return model.V_ccs_tech_type_consumption[tech,tech_type,sector,resource,area,year]== \
                            sum(model.V_ccs_tech_type_usage[ccs, tech, tech_type, sector, area, year]*\
                                model.P_ccs_biomass[ccs, tech, sector, area, year]\
                                for ccs in sector_tech_ccs_combinations[sector][tech])
                else:
                    return model.V_ccs_tech_type_consumption[tech,tech_type,sector,resource,area,year]==0
            else:
                return model.V_ccs_tech_type_consumption[tech,tech_type,sector,resource,area,year]==0
        else:
            return model.V_ccs_tech_type_consumption[tech, tech_type, sector, resource, area, year] == 0
    model.ccs_consumptionCtr=Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR,model.RESOURCES,model.AREAS,model.YEAR,rule=ccs_consumption_rule)

    def ccs_forced_installation_rule(model,ccs,tech,sector,area,year):
        if model.P_ccs_force_install_ratio[ccs,tech,sector,area,year]!=0:

            return model.V_technology_use_coef_capacity[tech,sector, area, year]* \
                   model.P_ccs_force_install_ratio[ccs, tech, sector, area, year]== \
                   model.V_ccs_capacity[ccs, tech, sector, area, year]
        else:
            return Constraint.Skip
    model.ccs_forced_installationCtr=Constraint(model.CCS_TYPE_TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,
                                                rule=ccs_forced_installation_rule)

    def ccs_forced_capture_rule(model,ccs,tech,sector,area,year):
        if model.P_ccs_force_capture_ratio[ccs,tech,sector,area,year]!=0:
            return sum(model.V_technology_use_coef[tech,tech_type,sector,area,year] for tech_type in t_tt_combinations[tech]) * \
                   model.P_ccs_force_capture_ratio[ccs, tech, sector, area, year]== sum(model.V_ccs_tech_type_usage[ccs, tech, tech_type, sector, area, year] for tech_type in t_tt_combinations[tech])
        else:
            return Constraint.Skip
    model.ccs_forced_captureCtr=Constraint(model.CCS_TYPE_TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR, rule=ccs_forced_capture_rule)


    def ccs_overall_min_capture_rule(model,sector,area,year):
        if model.P_min_capture_ratio[sector,area,year]!=0:
            return sum(model.V_captured_emissions[tech,sector,area,year] for tech in s_t_combinations[sector])>=\
                   model.P_min_capture_ratio[sector,area,year]*model.V_emissions_no_ccs[sector,area,year]
        else:
            return Constraint.Skip
    model.ccs_overall_min_captureCtr=Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=ccs_overall_min_capture_rule)

    def ccs_overall_max_capture_rule(model,sector,area,year):
        if model.P_max_capture_ratio[sector,area,year]!=0:
            return sum(model.V_captured_emissions[tech,sector,area,year] for tech in s_t_combinations[sector])<=\
                   model.P_max_capture_ratio[sector,area,year]*model.V_emissions_no_ccs[sector,area,year]
        else:
            return Constraint.Skip
    model.ccs_overall_max_captureCtr=Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=ccs_overall_max_capture_rule)

    def ccs_added_capacity_ramp_rule(model,tech,sector,area,year):
        if year > min(getattr(model, "YEAR").data()) and model.P_installation_ramp_t[tech, sector, area, year] != 0:
            return sum(model.V_ccs_capacity[ccs,tech,sector,area,year]-model.V_ccs_capacity[ccs,tech,sector,area,year-1]  for ccs in
                       sector_tech_ccs_combinations[sector][tech]) <= \
                   model.P_installation_ramp_t[tech, sector, area, year]
        else:
            return Constraint.Skip
    model.ccs_added_capacity_rampCtr=Constraint(model.TECHNOLOGIES_SECTOR_CCS_SPECIFIC,model.AREAS,model.YEAR,rule=ccs_added_capacity_ramp_rule)

    def ccs_added_capacity_ramp_area_rule(model, tech, area, year):
        if year > min(getattr(model, "YEAR").data()) and model.P_installation_ramp_t[tech, "All", area, year] != 0:
            return sum(model.V_ccs_capacity[ccs,tech,sector,area,year]-model.V_ccs_capacity[ccs,tech,sector,area,year-1]  for ccs in
                       sector_tech_ccs_combinations[sector][tech]) <= \
                   model.P_installation_ramp_t[tech, "All", area, year]
        else:
            return Constraint.Skip

    model.ccs_added_capacity_ramp_areaCtr = Constraint(model.TECHNOLOGIES_CCS_SPECIFIC, model.AREAS, model.YEAR,
                                                   rule=ccs_added_capacity_ramp_area_rule)

    def ccs_stored_emissions_rule(model,area,year):
        s_t_combinations_no_biogas = s_t_combinations
        for sector in model.SECTOR:
            try:
                s_t_combinations_no_biogas[sector].remove("Biogas_Digester")
            except:
                pass
            try:
                s_t_combinations_no_biogas[sector].remove("Biomass_low_price")
            except:
                pass
            try:
                s_t_combinations_no_biogas[sector].remove("Biomass_med_price")
            except:
                pass
            try:
                s_t_combinations_no_biogas[sector].remove("Biomass_high_price")
            except:
                pass
            try:
                s_t_combinations_no_biogas[sector].remove("Municipal_wastes")
            except:
                pass
            try:
                s_t_combinations_no_biogas[sector].remove("Agriculture_wastes")
            except:
                pass
        return sum(model.V_stored_emissions[sector,area,year] for sector in model.SECTOR)==sum(model.V_captured_emissions[tech, sector, area, year] for sector in model.SECTOR for tech in
                   s_t_combinations_no_biogas[sector])+sum(model.V_emissions_tech_type_minus[tech, tech_type, sector, area, year] \
                     for sector in model.SECTOR
                     for tech in s_t_combinations_no_biogas[sector]
                     for tech_type in t_tt_combinations[tech]
                     )+sum(model.V_resource_outflow["DAC_CO2",sector,area,year] for sector in model.SECTOR)
    model.ccs_stored_emissionsCtr=Constraint(model.AREAS,model.YEAR,rule=ccs_stored_emissions_rule)

    return model