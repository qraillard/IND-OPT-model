from pyomo.environ import *
from pyomo.opt import SolverFactory
from pyomo.core import *
import pandas as pd
import numpy as np

def Create_Sets_Parameters_Variables(Parameters,t_tt_combinations,s_t_combinations,tech_ccs_combinations,sector_tech_ccs_combinations):
    model = ConcreteModel()

    #####################
    # Data preparation ##
    #####################

    TECHNOLOGIES = set(Parameters["TECHNOLOGIES_RESOURCES_parameters"].index.get_level_values('TECHNOLOGIES').unique())
    TECH_TYPE = set(Parameters["TECHNOLOGIES_RESOURCES_parameters"].index.get_level_values('TECH_TYPE').unique())
    # TECH_TYPE.remove("All")
    TECH_TYPE_ALL = set(Parameters["TECHNOLOGIES_RESOURCES_parameters"].index.get_level_values('TECH_TYPE').unique())
    TECH_TYPE_ALL.add("All")

    SECTOR = set(Parameters["RESOURCES_parameters"].index.get_level_values('SECTOR').unique())
    SECTOR.remove("All")
    SECTOR_ALL = set(Parameters["RESOURCES_parameters"].index.get_level_values('SECTOR').unique())

    resources_list=Parameters["TECHNOLOGIES_RESOURCES_parameters"].index.get_level_values('RESOURCES').unique()
    RESOURCES = set(resources_list)
    CTAX_RESOURCES = set(resources_list[resources_list.isin(["Biomass","Waste"])])
    # CTAX_RESOURCES = set(Parameters["TECHNOLOGIES_RESOURCES_parameters"].index.get_level_values('RESOURCES').unique())
    # CTAX_RESOURCES.remove("Electricity")

    YEAR = set(Parameters["RESOURCES_parameters"].index.get_level_values('YEAR').unique())
    AREAS = set(Parameters["RESOURCES_parameters"].index.get_level_values('AREAS').unique())
    CCS_TYPE = set(Parameters["CCS_parameters"].index.get_level_values('CCS_TYPE').unique())

    ########
    # SETS #
    ########
    model.TECHNOLOGIES = Set(initialize=TECHNOLOGIES, ordered=False)
    model.TECH_TYPE = Set(initialize=TECH_TYPE, ordered=False)
    model.TECH_TYPE_ALL = Set(initialize=TECH_TYPE_ALL, ordered=False)
    model.TECHNOLOGIES_TECH_TYPE=Set(within=model.TECHNOLOGIES*model.TECH_TYPE, initialize={(t,tt) for t in model.TECHNOLOGIES for tt in t_tt_combinations.get(t)})
    model.SECTOR = Set(initialize=SECTOR,ordered=False)
    model.SECTOR_ALL = Set(initialize=SECTOR_ALL, ordered=False)
    model.TECHNOLOGIES_SECTOR = Set(within=model.TECHNOLOGIES*model.SECTOR,
                                       initialize={(t,s) for s in model.SECTOR for t in
                                                   s_t_combinations.get(s)})

    model.TECHNOLOGIES_TECH_TYPE_SECTOR = Set(within=model.TECHNOLOGIES * model.TECH_TYPE * model.SECTOR,
                                       initialize={(t, tt,s) for s in model.SECTOR for t in
                                                   s_t_combinations.get(s) for tt in t_tt_combinations.get(t)})

    model.RESOURCES = Set(initialize=RESOURCES, ordered=False)
    model.CTAX_RESOURCES = Set(initialize=CTAX_RESOURCES, ordered=False) ##SUBSET OF RESOURCES
    model.YEAR = Set(initialize=YEAR, ordered=False)
    model.AREAS = Set(initialize=AREAS, ordered=False)
    model.CCS_TYPE = Set(initialize=CCS_TYPE,ordered=False)
    model.CCS_TYPE_TECHNOLOGIES_SECTOR=Set(within=model.CCS_TYPE*model.TECHNOLOGIES*model.SECTOR,
                                           initialize={(ccr, t,s) for s in model.SECTOR for t in
                                                   sector_tech_ccs_combinations[s].keys() for ccr in sector_tech_ccs_combinations[s].get(t)})
    model.CCS_TYPE_TECHNOLOGIES_TECH_TYPE_SECTOR = Set(within=model.CCS_TYPE*model.TECHNOLOGIES * model.TECH_TYPE * model.SECTOR,
                                              initialize={(ccr,t, tt, s) for s in model.SECTOR for t in
                                                   sector_tech_ccs_combinations[s].keys() for tt in t_tt_combinations.get(t)
                                                          for ccr in sector_tech_ccs_combinations[s].get(t) })

    model.TECHNOLOGIES_CCS_SPECIFIC = Set(within=model.TECHNOLOGIES,
                                                 initialize={(t) for t in tech_ccs_combinations.keys()},ordered=False)

    model.TECHNOLOGIES_SECTOR_CCS_SPECIFIC = Set(within=model.TECHNOLOGIES * model.SECTOR,
                                    initialize={(t, s) for s in model.SECTOR for t in
                                                sector_tech_ccs_combinations[s].keys()})

    model.TECHNOLOGIES_TECH_TYPE_SECTOR_CCS_SPECIFIC = Set(within=model.TECHNOLOGIES * model.TECH_TYPE * model.SECTOR,
                                              initialize={(t, tt, s) for s in model.SECTOR for t in
                                                          sector_tech_ccs_combinations[s].keys() for tt in t_tt_combinations.get(t)})


    ###############
    # Parameters ##
    ###############
    for COLNAME in Parameters["TECHNOLOGIES_RESOURCES_parameters"]:
        exec(
            "model.P_" + COLNAME + " =  Param(model.TECHNOLOGIES_TECH_TYPE_SECTOR,model.RESOURCES,model.YEAR, mutable=False, domain=Any,default=0," +
            "initialize=Parameters[\"TECHNOLOGIES_RESOURCES_parameters\"]." + COLNAME + ".squeeze().to_dict())")

    for COLNAME in Parameters["TECHNOLOGIES_TECH_TYPE_parameters"]:
        exec(
            "model.P_" + COLNAME + " =  Param(model.TECHNOLOGIES,model.TECH_TYPE_ALL,model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=False, domain=Any,default=0," +
            "initialize=Parameters[\"TECHNOLOGIES_TECH_TYPE_parameters\"]." + COLNAME + ".squeeze().to_dict())")

    for COLNAME in Parameters["RESOURCES_parameters"]:
        if COLNAME=="flow_cost_r":
            exec(
                "model.P_" + COLNAME + " =  Param(model.RESOURCES,model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=True, domain=Any,default=0," +
                "initialize=Parameters[\"RESOURCES_parameters\"]." + COLNAME + ".squeeze().to_dict())")
        else:
            exec(
                "model.P_" + COLNAME + " =  Param(model.RESOURCES,model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=False, domain=Any,default=0," +
                "initialize=Parameters[\"RESOURCES_parameters\"]." + COLNAME + ".squeeze().to_dict())")


    for COLNAME in Parameters["SECTOR_parameters"]:
        if COLNAME in ["carbon_tax","co2_transport_and_storage_cost"]:
            exec(
                "model.P_" + COLNAME + " =  Param(model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=True, domain=Any,default=0," +
                "initialize=Parameters[\"SECTOR_parameters\"]." + COLNAME + ".squeeze().to_dict())")
        else:
            exec(
                "model.P_" + COLNAME + " =  Param(model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=False, domain=Any,default=0," +
                "initialize=Parameters[\"SECTOR_parameters\"]." + COLNAME + ".squeeze().to_dict())")



    for COLNAME in Parameters["TECHNOLOGIES_parameters"]:
        if COLNAME=="flow_cost_t":
            exec(
                "model.P_" + COLNAME + " =  Param(model.TECHNOLOGIES,model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=True, domain=Any,default=0," +
                "initialize=Parameters[\"TECHNOLOGIES_parameters\"]." + COLNAME + ".squeeze().to_dict())")
        else:
            exec(
            "model.P_" + COLNAME + " =  Param(model.TECHNOLOGIES,model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=False, domain=Any,default=0," +
            "initialize=Parameters[\"TECHNOLOGIES_parameters\"]." + COLNAME + ".squeeze().to_dict())")

    for COLNAME in Parameters["CCS_parameters"]:
        exec(
            "model.P_" + COLNAME + " =  Param(model.CCS_TYPE_TECHNOLOGIES_SECTOR,model.AREAS,model.YEAR, mutable=False, domain=Any,default=0," +
            "initialize=Parameters[\"CCS_parameters\"]." + COLNAME + ".squeeze().to_dict())")



    ################
    # Variables    #
    ################
    model.V_cost_total = Var(domain=NonNegativeReals,initialize=0)
    model.V_emissions_total = Var(domain=Reals,initialize=0)
    model.V_cost = Var(model.SECTOR,model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0)
    model.V_carbon_cost=Var(model.SECTOR,model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0)
    model.V_technology_cost = Var(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0)
    model.V_emissions = Var(model.SECTOR,model.AREAS, model.YEAR, domain=Reals,initialize=0)
    model.V_emissions_no_ccs = Var(model.SECTOR, model.AREAS, model.YEAR, domain=Reals, initialize=0)
    model.V_ctax_emissions_plus=Var(model.SECTOR,model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0) #only this one is kept for carbon tax
    model.V_ctax_emissions_minus = Var(model.SECTOR, model.AREAS, model.YEAR, domain=NonPositiveReals,initialize=0)



    model.V_emissions_tech_type = Var(model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS, model.YEAR, domain=Reals,
                                      initialize=0)
    model.V_emissions_tech_type_plus = Var(model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS, model.YEAR,
                                           domain=NonNegativeReals, initialize=0)
    model.V_emissions_tech_type_minus = Var(model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS, model.YEAR,
                                            domain=NonPositiveReals, initialize=0)



    model.V_resource_flow = Var(model.RESOURCES,model.SECTOR, model.AREAS, model.YEAR, domain=Reals,initialize=0)
    model.V_resource_inflow = Var(model.RESOURCES, model.SECTOR,model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0)
    model.V_resource_outflow = Var(model.RESOURCES,model.SECTOR, model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0)
    model.V_resource_imports = Var(model.RESOURCES,model.SECTOR, model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0)
    model.V_resource_exports = Var(model.RESOURCES,model.SECTOR, model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0)

    model.V_resource_tech_type_inflow = Var(model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.RESOURCES, model.AREAS,
                                            model.YEAR, initialize=0,
                                            domain=NonNegativeReals)
    model.V_resource_tech_type_outflow = Var(model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.RESOURCES, model.AREAS,
                                             model.YEAR, initialize=0,
                                             domain=NonNegativeReals)
    model.V_resource_tech_type_capacity = Var(model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.RESOURCES,
                                              model.AREAS, model.YEAR, initialize=0,
                                              domain=Reals)

    model.V_technology_use_coef = Var(model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS, model.YEAR, initialize=0,
                                      domain=NonNegativeReals)

    model.V_technology_use_coef_capacity = Var(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,
                                               domain=NonNegativeReals, initialize=0)
    model.V_technology_tech_type_use_coef_capacity = Var(model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS,
                                                         model.YEAR, initialize=0,
                                                         domain=NonNegativeReals)
    model.V_added_capacity = Var(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR, initialize=0,
                                 domain=NonNegativeReals)

    model.V_removed_capacity = Var(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR, initialize=0,
                                   domain=NonNegativeReals)


    model.V_ccs_capex_cost = Var( model.SECTOR, model.AREAS, model.YEAR,
                               initialize=0, domain=NonNegativeReals)
    model.V_ccs_tech_capex_cost = Var(model.CCS_TYPE_TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,
                                 initialize=0, domain=NonNegativeReals)
    model.V_ccs_opex_cost = Var(model.SECTOR, model.AREAS, model.YEAR,
                                 initialize=0, domain=NonNegativeReals)
    model.V_ccs_capacity = Var(model.CCS_TYPE_TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,
                                               initialize=0, domain=NonNegativeReals)
    model.V_ccs_tech_type_capacity = Var(model.CCS_TYPE, model.TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS, model.YEAR,
                               initialize=0, domain=NonNegativeReals)
    model.V_ccs_tech_type_usage = Var(model.CCS_TYPE_TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS,
                                         model.YEAR,
                                         initialize=0, domain=NonNegativeReals)
    model.V_ccs_added_capacity = Var(model.CCS_TYPE_TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,
                                 initialize=0, domain=NonNegativeReals)
    model.V_ccs_removed_capacity = Var(model.CCS_TYPE_TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,
                                   initialize=0, domain=NonNegativeReals)
    model.V_captured_emissions = Var(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,
                                   initialize=0, domain=NonNegativeReals)
    model.V_stored_emissions = Var(model.SECTOR, model.AREAS, model.YEAR,
                                     initialize=0, domain=NonNegativeReals)
    model.V_ccs_captured_emissions = Var(model.CCS_TYPE_TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,
                                     initialize=0, domain=NonNegativeReals)
    model.V_ccs_tech_type_captured_emissions = Var(model.CCS_TYPE_TECHNOLOGIES_TECH_TYPE_SECTOR, model.AREAS, model.YEAR,
                                         initialize=0, domain=NonNegativeReals)

    model.V_ccs_tech_type_consumption=Var(model.TECHNOLOGIES_TECH_TYPE_SECTOR,model.RESOURCES, model.AREAS, model.YEAR, initialize=0,
                                   domain=NonNegativeReals)

    return model

def Update_Model(model,Parameters,prev_output_ratio,ouput_change_ratio,t_tt_combinations,s_t_combinations,sector_tech_ccs_combinations):

    model.del_component("P_flow_cost_r")
    model.del_component("P_flow_cost_r_index")
    model.del_component("P_flow_cost_t")
    model.del_component("P_flow_cost_t_index")
    model.del_component("P_carbon_tax")
    model.del_component("P_carbon_tax_index")
    model.del_component("P_co2_transport_and_storage_cost")
    model.del_component("P_co2_transport_and_storage_cost_index")

    model.P_flow_cost_r=Param(model.RESOURCES,model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=False, domain=Any,default=0,initialize=Parameters["RESOURCES_parameters"].flow_cost_r.squeeze().to_dict())
    model.P_flow_cost_t =  Param(model.TECHNOLOGIES,model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=False, domain=Any,default=0,initialize=Parameters["TECHNOLOGIES_parameters"].flow_cost_t.squeeze().to_dict())
    model.P_carbon_tax= Param(model.SECTOR_ALL, model.AREAS, model.YEAR, mutable=False, domain=Any, default=0,initialize=Parameters["SECTOR_parameters"].carbon_tax.squeeze().to_dict())
    model.P_co2_transport_and_storage_cost= Param(model.SECTOR_ALL, model.AREAS, model.YEAR, mutable=False, domain=Any, default=0,initialize=Parameters["SECTOR_parameters"].co2_transport_and_storage_cost.squeeze().to_dict())
    # model.P_flow_cost_r.reconstruct(Parameters["RESOURCES_parameters"].flow_cost_r.squeeze().to_dict())
    # model.P_flow_cost_t.reconstruct(Parameters["TECHNOLOGIES_parameters"].flow_cost_t.squeeze().to_dict())
    # model.P_carbon_tax.reconstruct(Parameters["SECTOR_parameters"].carbon_tax.squeeze().to_dict())
    # model.P_co2_transport_and_storage_cost.reconstruct(Parameters["SECTOR_parameters"].co2_transport_and_storage_cost.squeeze().to_dict())

    model.del_component("Cost_definitionCtr")
    model.del_component("Cost_definitionCtr_index")
    model.del_component("Carbon_costCtr")
    model.del_component("Carbon_costCtr_index")
    model.del_component("ccs_opexCtr")
    model.del_component("ccs_opexCtr_index")
    def Cost_definition_rule(model, sector, area, year):
        return model.V_cost[sector, area, year] == sum(
            model.P_flow_cost_r[resource, sector, area, year] * model.V_resource_imports[resource, sector, area, year]
            for resource in model.RESOURCES) + \
            sum(sum(model.P_flow_cost_t[tech, sector, area, year] * model.V_technology_use_coef[
                tech, tech_type, sector, area, year] \
                    for tech_type in t_tt_combinations[tech]) for tech in s_t_combinations[sector]) + \
            sum(model.V_technology_cost[tech, sector, area, year] for tech in s_t_combinations[sector]) + \
            sum(model.P_opex_cost[tech, sector, area, year] * model.V_technology_use_coef_capacity[
                tech, sector, area, year] for tech
                in s_t_combinations[sector]) + \
            model.V_carbon_cost[sector, area, year] + \
            model.V_ccs_capex_cost[sector, area, year] + model.V_ccs_opex_cost[sector, area, year]
    def Carbon_cost_rule(model, sector, area, year):
        return model.V_carbon_cost[sector, area, year] == model.P_carbon_tax[sector, area, year] * \
            model.V_ctax_emissions_plus[sector, area, year]
    def ccs_opex_rule(model, sector, area, year):
        return model.V_ccs_opex_cost[sector, area, year] == \
            sum(model.P_ccs_opex[ccs, tech, sector, area, year] * model.V_ccs_capacity[ccs, tech, sector, area, year]
                for tech in sector_tech_ccs_combinations[sector].keys() for ccs in
                sector_tech_ccs_combinations[sector][tech]) + \
            model.V_stored_emissions[sector, area, year] * model.P_co2_transport_and_storage_cost[
                sector, area, year]

    model.Cost_definitionCtr = Constraint(model.SECTOR, model.AREAS, model.YEAR, rule=Cost_definition_rule)
    model.ccs_opexCtr = Constraint(model.SECTOR, model.AREAS, model.YEAR, rule=ccs_opex_rule)
    model.Carbon_costCtr = Constraint(model.SECTOR, model.AREAS, model.YEAR, rule=Carbon_cost_rule)



    if ouput_change_ratio!=prev_output_ratio:
        model.del_component("Resource_min_outflowCtr")
        model.del_component("Resource_min_outflowCtr_index")
        model.del_component("Production_moinsCtr")
        model.del_component("Production_moinsCtr_index")
        model.del_component("Production_plusCtr")
        model.del_component("Production_plusCtr_index")

        model.del_component("P_output")
        model.del_component("P_output_index")
        model.del_component("P_min_output")
        model.del_component("P_min_output_index")

        model.P_output =  Param(model.RESOURCES,model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=False, domain=Any,default=0,initialize=Parameters["RESOURCES_parameters"].output.squeeze().to_dict())
        model.P_min_output = Param(model.RESOURCES,model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=False, domain=Any,default=0,initialize=Parameters["RESOURCES_parameters"].min_output.squeeze().to_dict())

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

        def Resource_min_outflow_rule(model, resource, sector, area, year):
            if model.P_min_output[resource, sector, area, year] != 0:
                return model.P_min_output[resource, sector, area, year] <= model.V_resource_outflow[
                    resource, sector, area, year]
            else:
                return Constraint.Skip

        model.Resource_min_outflowCtr = Constraint(model.RESOURCES, model.SECTOR, model.AREAS, model.YEAR,rule=Resource_min_outflow_rule)
        model.Production_moinsCtr = Constraint(model.RESOURCES, model.SECTOR,model.AREAS, model.YEAR, rule=Production_moins_rule)
        model.Production_plusCtr = Constraint(model.RESOURCES,model.SECTOR, model.AREAS, model.YEAR, rule=Production_plus_rule)
    else:
        pass





    return model


def Update_Modelv2(model,Parameters):
    # model.P_flow_cost_r.clear()
    # model.P_flow_cost_r._constructed = False
    # model.P_flow_cost_r.construct(Parameters["RESOURCES_parameters"].flow_cost_r.squeeze().to_dict())
    # model.P_flow_cost_t.clear()
    # model.P_flow_cost_t._constructed = False
    # model.P_flow_cost_t.construct(Parameters["TECHNOLOGIES_parameters"].flow_cost_t.squeeze().to_dict())
    # model.P_carbon_tax.clear()
    # model.P_carbon_tax._constructed = False
    # model.P_carbon_tax.construct(Parameters["SECTOR_parameters"].carbon_tax.squeeze().to_dict())
    # model.P_co2_transport_and_storage_cost.clear()
    # model.P_co2_transport_and_storage_cost._constructed = False
    # model.P_co2_transport_and_storage_cost.construct(Parameters["SECTOR_parameters"].co2_transport_and_storage_cost.squeeze().to_dict())
    # model.P_flow_cost_r.pprint()
    for r in ["Electricity","Electricity_25%_LF","Electricity_50%_LF"]:
        for s in model.SECTOR_ALL:
            for a in model.AREAS:
                for y in model.YEAR:
                    model.P_flow_cost_r[r,s,a,y]=Parameters["RESOURCES_parameters"].flow_cost_r.squeeze().to_dict()[(r,s,a,y)]
    for t in ["Biogas_Digester"]:
        for s in model.SECTOR_ALL:
            for a in model.AREAS:
                for y in model.YEAR:
                    model.P_flow_cost_t[t,s,a,y]=Parameters["TECHNOLOGIES_parameters"].flow_cost_t.squeeze().to_dict()[(t,s,a,y)]

    for s in model.SECTOR_ALL:
        for a in model.AREAS:
            for y in model.YEAR:
                model.P_carbon_tax[s, a, y] = Parameters["SECTOR_parameters"].carbon_tax.squeeze().to_dict()[(s, a, y)]
                model.P_co2_transport_and_storage_cost[s, a, y] = Parameters["SECTOR_parameters"].co2_transport_and_storage_cost.squeeze().to_dict()[(s, a, y)]
    return model


def get_var_value_map(model):
    var_value_map = ComponentMap()

    for v in model.component_data_objects(ctype=Var, descend_into=True):
        var_value_map[v] = value(v)

    return var_value_map


def set_var_value_from_map(model, var_value_map):
    for v in var_value_map:
        v.set_value(var_value_map[v])