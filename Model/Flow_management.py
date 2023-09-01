from pyomo.environ import *
from pyomo.core import *
from pyomo.opt import SolverFactory
from datetime import timedelta
import pandas as pd
import numpy as np
import re
import sys

def Flow_management_Ctr(model,t_tt_combinations,s_t_combinations):
    # decomposition (+/-) of resource flow
    def resource_flow_definition_1st_rule(model, resource,sector, area, year):
        return model.V_resource_flow[resource,sector, area, year] == model.V_resource_inflow[resource,sector, area, year] - \
               model.V_resource_outflow[resource,sector, area, year]

    model.resource_flow_definition_1stCtr = Constraint(model.RESOURCES, model.SECTOR,model.AREAS, model.YEAR,
                                                       rule=resource_flow_definition_1st_rule)

    # decomposition (+/-) of tech flow
    def resource_flow_definition_2nd_rule(model, tech, tech_type,sector, resource, area, year):
        if tech_type in t_tt_combinations[tech]:
            return model.V_resource_tech_type_inflow[tech, tech_type, sector,resource, area, year] - model.V_resource_tech_type_outflow[
                tech, tech_type,sector, resource, area, year] == model.V_technology_use_coef[tech, tech_type,sector, area, year] * \
                   model.P_conversion_factor[tech, tech_type,sector, resource, year]+\
            model.V_ccs_tech_type_consumption[tech, tech_type,sector, resource, area, year]
        else:
            return model.V_resource_tech_type_outflow[tech, tech_type,sector, resource, area, year]==0


    model.resource_flow_definition_2ndCtr = Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR,model.RESOURCES,
                                                       model.AREAS, model.YEAR, rule=resource_flow_definition_2nd_rule)


    def resource_flow_tech_rule(model, tech, tech_type, sector, resource, area, year):
        if tech_type in t_tt_combinations[tech]:
            if model.P_conversion_factor[tech, tech_type,sector, resource, year] > 0:
                return model.V_resource_tech_type_outflow[tech, tech_type,sector, resource, area, year] == 0
            else:
                return model.V_resource_tech_type_inflow[tech, tech_type,sector, resource, area, year] ==model.V_ccs_tech_type_consumption[tech, tech_type,sector, resource, area, year]
        else:
            return model.V_resource_tech_type_inflow[tech, tech_type,sector, resource, area, year]==0
    model.resource_flow_techCtr = Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR,model.RESOURCES, model.AREAS,
                                             model.YEAR, rule=resource_flow_tech_rule)

    def resource_flow_definition_3rd_rule(model, resource,sector, area, year):
        # return model.V_resource_inflow[resource, sector, area, year] == sum(
        #     model.V_resource_tech_type_inflow[tech, tech_type,sector, resource, area, year] for tech in model.TECHNOLOGIES for
        #     tech_type in model.TECH_TYPE)
        return model.V_resource_inflow[resource, sector, area, year] == sum(sum(
            model.V_resource_tech_type_inflow[tech, tech_type,sector, resource, area, year] for
            tech_type in t_tt_combinations[tech]) for tech in s_t_combinations[sector] )

    model.resource_flow_definition_3rdCtr = Constraint(model.RESOURCES,model.SECTOR, model.AREAS, model.YEAR,
                                                       rule=resource_flow_definition_3rd_rule)

    def resource_flow_definition_4th_rule(model, resource, sector, area, year):
        # tot=0
        # for tech in model.TECHNOLOGIES:
        #     for tech_type in model.TECH_TYPE:
        #         if tech_type in t_tt_combinations[tech]:
        #             tot+=model.V_resource_tech_type_outflow[tech, tech_type,sector, resource, area, year]
        # return model.V_resource_outflow[resource,sector, area, year] == tot
        # return model.V_resource_outflow[resource,sector, area, year] == sum(
        #     model.V_resource_tech_type_outflow[tech, tech_type,sector, resource, area, year] for tech in model.TECHNOLOGIES for
        #     tech_type in model.TECH_TYPE)
        return model.V_resource_outflow[resource,sector, area, year] == sum(sum(
            model.V_resource_tech_type_outflow[tech, tech_type,sector, resource, area, year]  for
            tech_type in t_tt_combinations[tech]) for tech in s_t_combinations[sector])

    model.resource_flow_definition_4thCtr = Constraint(model.RESOURCES,model.SECTOR, model.AREAS, model.YEAR,
                                                       rule=resource_flow_definition_4th_rule)

    def resource_flow_definition_5th_rule(model, resource, sector,area, year):
        return model.V_resource_flow[resource,sector, area, year] ==model.V_resource_imports[resource,sector,area,year]-model.V_resource_exports[resource,sector,area,year]

    model.resource_flow_definition_5thCtr = Constraint(model.RESOURCES, model.SECTOR, model.AREAS, model.YEAR, rule=resource_flow_definition_5th_rule)



    ###Production Constraints###
    def Production_moins_rule(model,resource, sector,area, year):
        if model.P_output[resource,sector, area, year] != 0:
            return model.P_output[resource,sector, area, year] * (1 + model.P_production_error_margin[resource, sector, area, year]) >= \
                   model.V_resource_outflow[resource,sector, area, year]
        else:
            return Constraint.Skip

    def Production_plus_rule(model, resource,sector, area, year):
        if model.P_output[resource,sector, area, year] != 0:
            return model.P_output[resource,sector, area, year] * (1 - model.P_production_error_margin[resource,sector, area, year]) <= \
                   model.V_resource_outflow[resource,sector, area, year]
        else:
            return Constraint.Skip

    model.Production_moinsCtr = Constraint(model.RESOURCES, model.SECTOR,model.AREAS, model.YEAR, rule=Production_moins_rule)
    model.Production_plusCtr = Constraint(model.RESOURCES,model.SECTOR, model.AREAS, model.YEAR, rule=Production_plus_rule)

    def Resource_flow_rule(model, resource, sector, area, year):
        if model.P_is_product[resource,sector, area, year] == 0 and resource not in ["CO2"]: #CO2 emissions can be captured and thus we can have negative emissions
            return model.V_resource_flow[resource,sector, area, year] >= 0
        else:
            return Constraint.Skip

    model.Resource_flowCtr = Constraint(model.RESOURCES, model.SECTOR, model.AREAS, model.YEAR, rule=Resource_flow_rule)


    def Technology_Production_Min_rule(model, tech, tech_type, sector, area, year):
        if tech_type in t_tt_combinations[tech]:
            if model.P_forced_prod_ratio_min[tech, "All",sector, area, year] != 0:
                resource = model.P_forced_resource[tech, "All", sector, area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    return Constraint.Skip
                else:
                    return model.P_forced_prod_ratio_min[tech, "All",sector, area, year] * model.V_resource_outflow[
                        resource,sector, area, year] <= -sum(model.V_technology_use_coef[tech, tt,sector, area, year] * \
                           model.P_conversion_factor[tech, tt,sector, resource, year] for tt in t_tt_combinations[tech])

            elif model.P_forced_prod_ratio_min[tech, tech_type,sector, area, year] != 0:
                resource = model.P_forced_resource[tech, tech_type,sector, area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    return Constraint.Skip
                else:
                    return model.P_forced_prod_ratio_min[tech, tech_type, sector, area, year] * model.V_resource_outflow[
                        resource,sector, area, year] <= -model.V_technology_use_coef[tech, tech_type,sector, area, year] * \
                           model.P_conversion_factor[tech, tech_type,sector, resource, year]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.Technology_Production_MinCtr = Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS, model.YEAR,
                                                    rule=Technology_Production_Min_rule)

    def Technology_Production_Max_rule(model, tech, tech_type,sector, area, year):
        if tech_type in t_tt_combinations[tech]:
            if model.P_forced_prod_ratio_max[tech, "All",sector, area, year] != 0:
                resource = model.P_forced_resource[tech, "All", sector, area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    return Constraint.Skip
                else:
                    return model.P_forced_prod_ratio_max[tech, "All",sector, area, year] * model.V_resource_outflow[
                        resource,sector, area, year] >= -sum(model.V_technology_use_coef[tech, tt,sector, area, year] * \
                           model.P_conversion_factor[tech, tt,sector, resource, year] for tt in t_tt_combinations[tech])

            elif model.P_forced_prod_ratio_max[tech, tech_type,sector, area, year] != 0:
                resource = model.P_forced_resource[tech, tech_type,sector, area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    return Constraint.Skip
                else:
                    return model.P_forced_prod_ratio_max[tech, tech_type,sector, area, year] * model.V_resource_outflow[
                        resource,sector, area, year] >= -model.V_technology_use_coef[tech, tech_type,sector, area, year] * \
                           model.P_conversion_factor[tech, tech_type,sector, resource, year]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.Technology_Production_MaxCtr = Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS, model.YEAR,
                                                    rule=Technology_Production_Max_rule)

    def Technology_Production_forced_rule(model, tech, tech_type,sector, area, year):
        if tech_type in t_tt_combinations[tech]:
            if model.P_forced_prod_t[tech, "All",sector, area, year] != 0:
                resource = model.P_forced_resource[tech, "All",sector, area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    return Constraint.Skip
                else:
                    return model.P_forced_prod_t[tech, "All",sector, area, year] == -sum(model.V_technology_use_coef[
                        tech, tt,sector, area, year] * model.P_conversion_factor[tech, tt,sector, resource, year] for tt in t_tt_combinations[tech])

            elif model.P_forced_prod_t[tech, tech_type,sector, area, year] != 0:
                resource = model.P_forced_resource[tech, tech_type,sector, area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    return Constraint.Skip
                else:
                    return model.P_forced_prod_t[tech, tech_type,sector, area, year] == -model.V_technology_use_coef[
                        tech, tech_type,sector, area, year] * model.P_conversion_factor[tech, tech_type,sector, resource, year]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.Technology_Production_forced_Ctr = Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS, model.YEAR,
                                                        rule=Technology_Production_forced_rule)

    def Technology_Production_forced_min_rule(model, tech, tech_type,sector, area, year):
        if tech_type in t_tt_combinations[tech]:
            if model.P_forced_prod_min_t[tech, "All",sector, area, year] != 0:
                resource = model.P_forced_resource[tech, "All",sector, area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    return Constraint.Skip
                else:
                    return model.P_forced_prod_min_t[tech, "All",sector, area, year] <= -sum(model.V_technology_use_coef[
                        tech, tt,sector, area, year] * model.P_conversion_factor[tech, tt,sector, resource, year] for tt in t_tt_combinations[tech])

            elif model.P_forced_prod_min_t[tech, tech_type,sector, area, year] != 0:
                resource = model.P_forced_resource[tech, tech_type,sector, area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    return Constraint.Skip
                else:
                    return model.P_forced_prod_min_t[tech, tech_type,sector, area, year] <= -model.V_technology_use_coef[
                        tech, tech_type,sector, area, year] * model.P_conversion_factor[tech, tech_type,sector, resource, year]
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.Technology_Production_forced_min_Ctr = Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS, model.YEAR,
                                                        rule=Technology_Production_forced_min_rule)

    def Resource_max_outflow_rule(model,resource,sector,area,year):
        if model.P_max_output[resource,sector,area,year]!=0:
            return model.P_max_output[resource,sector,area,year]>=model.V_resource_outflow[
                    resource,sector, area, year]
        else:
            return Constraint.Skip
    model.Resource_max_outflowCtr=Constraint(model.RESOURCES,model.SECTOR,model.AREAS,model.YEAR,rule=Resource_max_outflow_rule)

    def Resource_min_outflow_rule(model,resource,sector,area,year):
        if model.P_min_output[resource,sector,area,year]!=0:
            return model.P_min_output[resource,sector,area,year]<=model.V_resource_outflow[
                    resource,sector, area, year]
        else:
            return Constraint.Skip
    model.Resource_min_outflowCtr=Constraint(model.RESOURCES,model.SECTOR,model.AREAS,model.YEAR,rule=Resource_min_outflow_rule)

    def Resource_min_export_rule(model,resource,sector,area,year):
        if model.P_min_export[resource,sector,area,year]!=0:
            return model.P_min_export[resource,sector,area,year]<=model.V_resource_exports[
                    resource,sector, area, year]
        else:
            return Constraint.Skip

    model.Resource_min_exportCtr = Constraint(model.RESOURCES, model.SECTOR, model.AREAS, model.YEAR,
                                              rule=Resource_min_export_rule)

    def Resource_exports_and_outflow_rule(model,resource,sector,area,year):
        return model.V_resource_outflow[resource,sector, area, year]>=model.V_resource_exports[resource,sector, area, year]

    model.Resource_exports_and_outflowCtr = Constraint(model.RESOURCES, model.SECTOR, model.AREAS, model.YEAR, rule=Resource_exports_and_outflow_rule)

    def Resource_imports_and_inflow_rule(model,resource,sector,area,year):
        return model.V_resource_inflow[resource,sector, area, year]>=model.V_resource_imports[resource,sector, area, year]

    model.Resource_imports_and_inflowCtr = Constraint(model.RESOURCES, model.SECTOR, model.AREAS, model.YEAR,
                                              rule=Resource_imports_and_inflow_rule)

    def Resource_export_1st_rule(model,resource, sector,area, year):
        if model.P_export[resource,sector, area, year] != 0:
            return model.P_export[resource,sector, area, year] == model.V_resource_exports[resource,sector, area, year]
        else:
            return Constraint.Skip

    model.Resource_export_1stCtr = Constraint(model.RESOURCES, model.SECTOR, model.AREAS, model.YEAR,
                                              rule=Resource_export_1st_rule)

    def Resource_max_import_rule(model,resource,sector,area,year):
        if model.P_no_import[resource,sector,area,year]==1:
            return model.V_resource_imports[resource,sector,area,year]==0
        elif model.P_max_import[resource,sector,area,year]!=0:
            return model.P_max_import[resource,sector,area,year]>=model.V_resource_imports[resource,sector,area,year]
        else:
            return Constraint.Skip
    model.Resource_max_importCtr=Constraint(model.RESOURCES,model.SECTOR,model.AREAS,model.YEAR,rule=Resource_max_import_rule)

    def Resource_min_import_rule(model,resource,sector,area,year):
        if model.P_min_import[resource,sector,area,year]!=0:
            return model.P_min_import[resource,sector,area,year]<=model.V_resource_imports[resource,sector,area,year]
        else:
            return Constraint.Skip
    model.Resource_min_importCtr=Constraint(model.RESOURCES,model.SECTOR,model.AREAS,model.YEAR,rule=Resource_min_import_rule)


    def Resource_max_import_ratio_rule(model,resource,sector,area,year):
        if model.P_max_import_ratio[resource,sector,area,year]!=0:
            return model.P_max_import_ratio[resource,sector,area,year]*model.V_resource_inflow[
                    resource,sector, area, year]>=model.V_resource_imports[resource,sector,area,year]
        else:
            return Constraint.Skip
    model.Resource_max_import_ratioCtr=Constraint(model.RESOURCES,model.SECTOR,model.AREAS,model.YEAR,rule=Resource_max_import_ratio_rule)

    def Resource_max_import_ratio_from_start_rule(model,resource,sector,area,year):
        year_ini = min(getattr(model, "YEAR").data())
        if model.P_max_import_ratio_from_start[resource,sector,area,year]!=0 and year>year_ini:
            return model.P_max_import_ratio_from_start[resource,sector,area,year]*model.V_resource_imports[resource,sector,area,year_ini]>= model.V_resource_imports[resource,sector,area,year]
        else:
            return Constraint.Skip
    model.Resource_max_import_ratio_from_startCtr=Constraint(model.RESOURCES,model.SECTOR,model.AREAS,model.YEAR,rule=Resource_max_import_ratio_from_start_rule)

    def Resource_min_import_ratio_rule(model,resource,sector,area,year):
        if model.P_min_import_ratio[resource,sector,area,year]!=0:
            return model.P_min_import_ratio[resource,sector,area,year]*model.V_resource_inflow[
                    resource,sector, area, year]<=model.V_resource_imports[resource,sector,area,year]
        else:
            return Constraint.Skip
    model.Resource_min_import_ratioCtr=Constraint(model.RESOURCES,model.SECTOR,model.AREAS,model.YEAR,rule=Resource_min_import_ratio_rule)


    #############################
    # Area specific constraints #
    #############################

    def Technology_Production_Min_area_rule(model, tech, tech_type, area, year):
        if tech_type in t_tt_combinations[tech]:
            if model.P_forced_prod_ratio_min[tech, "All","All", area, year] != 0:
                resource = model.P_forced_resource[tech, "All","All", area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    pass
                else:
                    return model.P_forced_prod_ratio_min[tech, "All","All", area, year] * sum(model.V_resource_outflow[
                        resource,sector, area, year] for sector in model.SECTOR) <= sum(-model.V_technology_use_coef[tech, tt,sector, area, year] * \
                           model.P_conversion_factor[tech, tt,sector, resource, year] for sector in model.SECTOR for tt in t_tt_combinations[tech])

            elif model.P_forced_prod_ratio_min[tech, tech_type,"All", area, year] != 0:
                resource = model.P_forced_resource[tech, tech_type,"All", area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    pass
                else:
                    return model.P_forced_prod_ratio_min[tech, tech_type,"All", area, year] * sum(model.V_resource_outflow[
                        resource,sector, area, year] for sector in model.SECTOR) <= sum(-model.V_technology_use_coef[tech, tech_type,sector, area, year] * \
                           model.P_conversion_factor[tech, tech_type,sector, resource, year] for sector in model.SECTOR)
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.Technology_Production_Min_areaCtr = Constraint(model.TECHNOLOGIES_TECH_TYPE, model.AREAS, model.YEAR,
                                                    rule=Technology_Production_Min_area_rule)

    def Technology_Production_Max_area_rule(model, tech, tech_type, area, year):
        if tech_type in t_tt_combinations[tech]:
            if model.P_forced_prod_ratio_max[tech, "All","All", area, year] != 0:
                resource = model.P_forced_resource[tech, "All","All", area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    return Constraint.Skip
                else:
                    return model.P_forced_prod_ratio_max[tech, "All","All", area, year] * sum(model.V_resource_outflow[
                        resource,sector, area, year] for sector in model.SECTOR)>= sum(-model.V_technology_use_coef[tech, tt,sector, area, year] * \
                           model.P_conversion_factor[tech, tt,sector, resource, year] for sector in model.SECTOR for tt in t_tt_combinations[tech])

            elif model.P_forced_prod_ratio_max[tech, tech_type,"All", area, year] != 0:
                resource = model.P_forced_resource[tech, tech_type,"All", area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    return Constraint.Skip
                else:
                    return model.P_forced_prod_ratio_max[tech, tech_type,"All", area, year] * sum(model.V_resource_outflow[
                        resource,sector, area, year] for sector in model.SECTOR)>= sum(-model.V_technology_use_coef[tech, tech_type,sector, area, year] * \
                           model.P_conversion_factor[tech, tech_type,sector, resource, year] for sector in model.SECTOR)
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip

    model.Technology_Production_Max_areaCtr = Constraint(model.TECHNOLOGIES_TECH_TYPE, model.AREAS, model.YEAR,
                                                    rule=Technology_Production_Max_area_rule)

    def Technology_Production_forced_area_rule(model, tech, tech_type, area, year):
        if tech_type in t_tt_combinations[tech]:
            if model.P_forced_prod_t[tech, "All","All", area, year] != 0:
                resource = model.P_forced_resource[tech, "All","All", area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    return Constraint.Skip
                else:
                    return model.P_forced_prod_t[tech, "All","All", area, year] == sum(-model.V_technology_use_coef[
                        tech, tt,sector, area, year] * model.P_conversion_factor[tech, tt,sector, resource, year] for sector in model.SECTOR for tt in t_tt_combinations[tech])

            elif model.P_forced_prod_t[tech, tech_type,"All", area, year] != 0:
                resource = model.P_forced_resource[tech, tech_type,"All", area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    return Constraint.Skip
                else:
                    return model.P_forced_prod_t[tech, tech_type,"All", area, year] == sum(-model.V_technology_use_coef[
                        tech, tech_type,sector, area, year] * model.P_conversion_factor[tech, tech_type,sector, resource, year] for sector in model.SECTOR)
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    model.Technology_Production_forced_areaCtr = Constraint(model.TECHNOLOGIES_TECH_TYPE,  model.AREAS, model.YEAR,
                                                        rule=Technology_Production_forced_area_rule)

    def Technology_Production_forced_min_area_rule(model, tech, tech_type, area, year):
        if tech_type in t_tt_combinations[tech]:
            if model.P_forced_prod_min_t[tech, "All","All", area, year] != 0:
                resource = model.P_forced_resource[tech, "All","All", area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    return Constraint.Skip
                else:
                    return model.P_forced_prod_min_t[tech, "All","All", area, year] <= sum(-model.V_technology_use_coef[
                        tech, tt,sector, area, year] * model.P_conversion_factor[tech, tt,sector, resource, year] for sector in model.SECTOR for tt in t_tt_combinations[tech])

            elif model.P_forced_prod_min_t[tech, tech_type,"All", area, year] != 0:
                resource = model.P_forced_resource[tech, tech_type,"All", area, year]
                if resource == 0:  # if no resources specified, the constraint cannot be applied
                    return Constraint.Skip
                else:
                    return model.P_forced_prod_min_t[tech, tech_type,"All", area, year] <= sum(-model.V_technology_use_coef[
                        tech, tech_type,sector, area, year] * model.P_conversion_factor[tech, tech_type,sector, resource, year] for sector in model.SECTOR)
            else:
                return Constraint.Skip
        else:
            return Constraint.Skip
    model.Technology_Production_forced_min_areaCtr = Constraint(model.TECHNOLOGIES_TECH_TYPE,  model.AREAS, model.YEAR,
                                                        rule=Technology_Production_forced_min_area_rule)

    def Resource_max_outflow_area_rule(model,resource,area,year):
        if model.P_max_output[resource,"All",area,year]!=0:
            return model.P_max_output[resource,"All",area,year]>=sum(model.V_resource_outflow[
                    resource,sector, area, year] for sector in model.SECTOR)
        else:
            return Constraint.Skip
    model.Resource_max_outflow_areaCtr=Constraint(model.RESOURCES,model.AREAS,model.YEAR,rule=Resource_max_outflow_area_rule)

    def Resource_max_import_area_rule(model,resource,area,year):
        if model.P_max_import[resource, "All", area, year] != 0:
            return model.P_max_import[resource, "All", area, year] >= sum(model.V_resource_imports[resource,sector,area,year]
                                                                          for sector in model.SECTOR)
        else:
            return Constraint.Skip

    model.Resource_max_import_areaCtr = Constraint(model.RESOURCES, model.AREAS, model.YEAR,
                                              rule=Resource_max_import_area_rule)

    def Resource_min_import_area_rule(model,resource,area,year):
        if model.P_min_import[resource, "All", area, year] != 0:
            return model.P_min_import[resource, "All", area, year] <= sum(model.V_resource_imports[resource,sector,area,year]
                                                                          for sector in model.SECTOR)
        else:
            return Constraint.Skip

    model.Resource_min_import_areaCtr = Constraint(model.RESOURCES, model.AREAS, model.YEAR,
                                              rule=Resource_min_import_area_rule)

    def Resource_max_import_ratio_area_rule(model,resource,area,year):
        if model.P_no_import[resource,"All",area,year]==1:
            return sum(model.V_resource_imports[resource,sector, area, year] for sector in model.SECTOR)==0
        elif model.P_max_import_ratio[resource,"All",area,year]!=0:
            return model.P_max_import_ratio[resource,"All",area,year]*sum(model.V_resource_inflow[
                    resource,sector, area, year] for sector in model.SECTOR)>=sum(model.V_resource_imports[resource,sector,area,year]
                                                                                  for sector in model.SECTOR)
        else:
            return Constraint.Skip
    model.Resource_max_import_ratio_areaCtr=Constraint(model.RESOURCES,model.AREAS,model.YEAR,rule=Resource_max_import_ratio_area_rule)

    def Resource_max_import_ratio_from_start_area_rule(model,resource,area,year):
        year_ini = min(getattr(model, "YEAR").data())
        if model.P_max_import_ratio_from_start[resource,"All",area,year]!=0 and year>year_ini:
            return model.P_max_import_ratio_from_start[resource,"All",area,year]*sum(model.V_resource_imports[resource,sector,area,year_ini] for sector in model.SECTOR)>= sum(model.V_resource_imports[resource,sector,area,year] for sector in model.SECTOR)
        else:
            return Constraint.Skip
    model.Resource_max_import_ratio_from_start_areaCtr=Constraint(model.RESOURCES,model.AREAS,model.YEAR,rule=Resource_max_import_ratio_from_start_area_rule)



    def Resource_min_import_ratio_area_rule(model,resource,area,year):
        if model.P_min_import_ratio[resource,"All",area,year]!=0:
            return model.P_min_import_ratio[resource,"All",area,year]*sum(model.V_resource_inflow[
                    resource,sector, area, year] for sector in model.SECTOR)<=sum(model.V_resource_imports[resource,sector,area,year]
                                                                                  for sector in model.SECTOR)
        else:
            return Constraint.Skip
    model.Resource_min_import_ratio_areaCtr=Constraint(model.RESOURCES,model.AREAS,model.YEAR,rule=Resource_min_import_ratio_area_rule)



    def Max_biogas_rule(model,sector,area,year):
        tech_list=["Biogas_Digester","Gasification"]
        if model.P_max_biogas_t["All",area,year]!=0:
            return sum(sum(model.V_resource_tech_type_outflow[tech,tech_type,s,"Gas",area,year]
                       for tech_type in t_tt_combinations[tech]) for tech in tech_list  \
                       for s in model.SECTOR)<= \
                   model.P_max_biogas_t["All", area, year]
        elif model.P_max_biogas_t[sector,area,year]!=0:
            return sum(sum(model.V_resource_tech_type_outflow[tech, tech_type, sector,"Gas", area, year]
                        for tech_type in t_tt_combinations[tech]) for tech in tech_list) <= \
                   model.P_max_biogas_t[sector, area, year]
        else:
            return Constraint.Skip

    model.Max_biogasCtr=Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=Max_biogas_rule)

    def Min_capacity_factor_rule(model,tech,sector,area,year):
        if model.P_min_capacity_factor[tech,sector,area,year]>0:
            return model.V_technology_use_coef_capacity[tech,sector,area,year]*model.P_min_capacity_factor[tech,sector,area,year]<=sum(model.V_technology_use_coef[tech,tech_type,sector,area,year] for tech_type in t_tt_combinations[tech])
        else:
            return Constraint.Skip
    model.Min_capacity_factorCtr=Constraint(model.TECHNOLOGIES_SECTOR,model.AREAS,model.YEAR,rule=Min_capacity_factor_rule)

    def Electricity_load_factor_rule(model,tech,tech_type,sector,area,year):
        if tech_type=="50%_LF":
            return model.V_technology_tech_type_use_coef_capacity[tech,tech_type,sector,area,year]*0.5>=model.V_technology_use_coef[tech,tech_type,sector,area,year]
        elif tech_type=="25%_LF":
            return model.V_technology_tech_type_use_coef_capacity[tech,tech_type,sector,area,year]*0.25>=model.V_technology_use_coef[tech,tech_type,sector,area,year]
        else:
            return Constraint.Skip

    model.Electricity_load_factorCtr=Constraint(model.TECHNOLOGIES_TECH_TYPE_SECTOR,model.AREAS,model.YEAR,rule=Electricity_load_factor_rule)


    def Hydrogen_specific_prod_rules(model):

        model.V_h2_prod_required = Var(model.SECTOR, model.AREAS, model.YEAR, initialize=0,
                                          domain=NonNegativeReals)
        model.V_h2_no_prod_required = Var(model.SECTOR, model.AREAS, model.YEAR, initialize=0,
                                       domain=NonNegativeReals)
        model.V_hpr_non_zero = Var(model.SECTOR, model.AREAS, model.YEAR, initialize=0,
                                       domain=Binary)
        model.V_hnpr_non_zero = Var(model.SECTOR, model.AREAS, model.YEAR, initialize=0,
                                          domain=Binary)

        def Hydrogen_specific_prod_1st_rule(model,sector,area,year):
            if model.P_is_product["Hydrogen", sector, area, year] == 1:
                not_dedicated_tech_list = []
                for tech in s_t_combinations[sector]:
                    if model.P_capacity_associated_resource[tech, sector, area, year] != "Hydrogen":
                        not_dedicated_tech_list.append(tech)

                return model.V_h2_prod_required[sector,area,year]-model.V_h2_no_prod_required[sector,area,year]==\
            model.V_resource_inflow["Hydrogen",sector,area,year]-model.V_resource_imports["Hydrogen",sector,area,year]-sum(model.V_resource_tech_type_outflow[
                        tech, tech_type,sector, "Hydrogen", area, year] for tech in not_dedicated_tech_list for tech_type in t_tt_combinations[tech])
            else:
                return Constraint.Skip
        model.Hydrogen_specific_prod_1stCtr=Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=Hydrogen_specific_prod_1st_rule)
        def Hydrogen_specific_prod_2nd_rule(model,sector,area,year): #Hydrogen by-product surplus is authorized but surplus from dedicated to hydrogen production technologies is forbidden
            tech_list=[]
            if model.P_is_product["Hydrogen",sector, area, year]==1:
                for tech in s_t_combinations[sector]:
                    if model.P_capacity_associated_resource[tech,sector,area,year]=="Hydrogen":
                        tech_list.append(tech)

                return model.V_h2_prod_required[sector,area,year]>=sum(model.V_resource_tech_type_outflow[
                    tech, tech_type,sector, "Hydrogen", area, year] for tech in tech_list for tech_type in t_tt_combinations[tech])
            else:
                return Constraint.Skip
        model.Hydrogen_specific_prod_2ndCtr=Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=Hydrogen_specific_prod_2nd_rule)
        def h2_prod_non_zero_rule(model,sector,area,year):
            return model.V_h2_prod_required[sector,area,year]<=model.V_hpr_non_zero[sector,area,year]*1e12
        def h2_no_prod_non_zero_rule(model, sector, area, year):
            return model.V_h2_no_prod_required[sector, area, year] <= model.V_hnpr_non_zero[sector, area, year] * 1e12
        def h2_prod_no_prod_non_zero_rule(model,sector,area,year):
            return model.V_hpr_non_zero[sector,area,year]+model.V_hnpr_non_zero[sector,area,year]<=1
        model.h2_prod_non_zeroCtr=Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=h2_prod_non_zero_rule)
        model.h2_no_prod_non_zeroCtr =Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=h2_no_prod_non_zero_rule)
        model.h2_prod_no_prod_non_zeroCtr =Constraint(model.SECTOR,model.AREAS,model.YEAR,rule=h2_prod_no_prod_non_zero_rule)


        return model
    # model=Hydrogen_specific_prod_rules(model)


    return model