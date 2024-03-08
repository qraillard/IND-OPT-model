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
        if COLNAME in ["carbon_tax","co2_transport_and_storage_cost","methane_leakage_ratio"]:
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
    # model.V_emissions_no_ccs = Var(model.SECTOR, model.AREAS, model.YEAR, domain=Reals, initialize=0)
    # model.V_ctax_emissions_plus=Var(model.SECTOR,model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0) #only this one is kept for carbon tax
    # model.V_ctax_emissions_minus = Var(model.SECTOR, model.AREAS, model.YEAR, domain=NonPositiveReals,initialize=0)
    model.V_ctax_emissions = Var(model.SECTOR, model.AREAS, model.YEAR, domain=Reals,initialize=0)  # only this one is kept for carbon tax

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
    # model.V_end_of_life_capacity = Var(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,model.YEAR, initialize=0,
    #                              domain=NonNegativeReals)
    model.V_added_capacity = Var(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR, initialize=0,
                                 domain=NonNegativeReals)
    model.V_counted_added_capacity = Var(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR, model.YEAR, initialize=0,
                                 domain=NonNegativeReals)

    model.V_removed_capacity = Var(model.TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR,model.YEAR, initialize=0,
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
    model.V_ccs_removed_capacity = Var(model.CCS_TYPE_TECHNOLOGIES_SECTOR, model.AREAS, model.YEAR, model.YEAR,
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

    # model.V_efuels_untaxed_co2_consumption = Var(model.SECTOR, model.AREAS, model.YEAR,
    #                                              initialize=0, domain=NonNegativeReals)
    # model.V_efuels_taxed_co2_consumption = Var(model.SECTOR, model.AREAS, model.YEAR,
    #                                            initialize=0, domain=NonNegativeReals)

    model.V_olefins_end_of_life_emissions=Var(model.SECTOR, model.AREAS, model.YEAR,
                                              initialize=0, domain=NonNegativeReals)

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
    for r in ["Electricity","Electricity_25%_LF","Electricity_50%_LF","Biomass"]:
        for s in model.SECTOR_ALL:
            for a in model.AREAS:
                for y in model.YEAR:
                    model.P_flow_cost_r[r,s,a,y]=Parameters["RESOURCES_parameters"].flow_cost_r.squeeze().to_dict()[(r,s,a,y)]
    for t in ["Biogas_Digester","Biomass_low_price", "Biomass_med_price", "Biomass_high_price",
            "Municipal_wastes", "Agriculture_wastes"]:
        for s in model.SECTOR_ALL:
            for a in model.AREAS:
                for y in model.YEAR:
                    model.P_flow_cost_t[t,s,a,y]=Parameters["TECHNOLOGIES_parameters"].flow_cost_t.squeeze().to_dict()[(t,s,a,y)]

    for s in model.SECTOR_ALL:
        for a in model.AREAS:
            for y in model.YEAR:
                model.P_carbon_tax[s, a, y] = Parameters["SECTOR_parameters"].carbon_tax.squeeze().to_dict()[(s, a, y)]
                model.P_co2_transport_and_storage_cost[s, a, y] = Parameters["SECTOR_parameters"].co2_transport_and_storage_cost.squeeze().to_dict()[(s, a, y)]
                model.P_methane_leakage_ratio[s,a,y] = Parameters["SECTOR_parameters"].methane_leakage_ratio.squeeze().to_dict()[(s,a,y)]
    return model


def get_var_value_map(model):
    var_value_map = ComponentMap()

    for v in model.component_data_objects(ctype=Var, descend_into=True):
        var_value_map[v] = value(v)

    return var_value_map


def set_var_value_from_map(model, var_value_map):
    for v in var_value_map:
        v.set_value(var_value_map[v])