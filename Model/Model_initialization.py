from pyomo.environ import *
from pyomo.opt import SolverFactory
from pyomo.core import *
import pandas as pd
import numpy as np

def Create_Sets_Parameters_Variables(Parameters):
    model = ConcreteModel()

    #####################
    # Data preparation ##
    #####################

    TECHNOLOGIES = set(Parameters["TECHNOLOGIES_RESOURCES_parameters"].index.get_level_values('TECHNOLOGIES').unique())
    TECH_TYPE = set(Parameters["TECHNOLOGIES_RESOURCES_parameters"].index.get_level_values('TECH_TYPE').unique())
    TECH_TYPE.remove("All")
    TECH_TYPE_ALL = set(Parameters["TECHNOLOGIES_RESOURCES_parameters"].index.get_level_values('TECH_TYPE').unique())

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
    model.SECTOR = Set(initialize=SECTOR,ordered=False)
    model.SECTOR_ALL = Set(initialize=SECTOR_ALL, ordered=False)
    model.RESOURCES = Set(initialize=RESOURCES, ordered=False)
    model.CTAX_RESOURCES = Set(initialize=CTAX_RESOURCES, ordered=False) ##SUBSET OF RESOURCES
    model.YEAR = Set(initialize=YEAR, ordered=False)
    model.AREAS = Set(initialize=AREAS, ordered=False)
    model.CCS_TYPE = Set(initialize=CCS_TYPE,ordered=False)

    ###############
    # Parameters ##
    ###############

    for COLNAME in Parameters["TECHNOLOGIES_TECH_TYPE_parameters"]:
        exec(
            "model.P_" + COLNAME + " =  Param(model.TECHNOLOGIES,model.TECH_TYPE_ALL,model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=False, domain=Any,default=0," +
            "initialize=Parameters[\"TECHNOLOGIES_TECH_TYPE_parameters\"]." + COLNAME + ".squeeze().to_dict())")

    for COLNAME in Parameters["RESOURCES_parameters"]:
        exec(
            "model.P_" + COLNAME + " =  Param(model.RESOURCES,model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=False, domain=Any,default=0," +
            "initialize=Parameters[\"RESOURCES_parameters\"]." + COLNAME + ".squeeze().to_dict())")

    for COLNAME in Parameters["SECTOR_parameters"]:
        exec(
            "model.P_" + COLNAME + " =  Param(model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=False, domain=Any,default=0," +
            "initialize=Parameters[\"SECTOR_parameters\"]." + COLNAME + ".squeeze().to_dict())")

    for COLNAME in Parameters["TECHNOLOGIES_RESOURCES_parameters"]:
        exec(
            "model.P_" + COLNAME + " =  Param(model.TECHNOLOGIES,model.TECH_TYPE_ALL,model.SECTOR_ALL,model.RESOURCES,model.YEAR, mutable=False, domain=Any,default=0," +
            "initialize=Parameters[\"TECHNOLOGIES_RESOURCES_parameters\"]." + COLNAME + ".squeeze().to_dict())")

    for COLNAME in Parameters["TECHNOLOGIES_parameters"]:
        exec(
            "model.P_" + COLNAME + " =  Param(model.TECHNOLOGIES,model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=False, domain=Any,default=0," +
            "initialize=Parameters[\"TECHNOLOGIES_parameters\"]." + COLNAME + ".squeeze().to_dict())")

    for COLNAME in Parameters["CCS_parameters"]:
        exec(
            "model.P_" + COLNAME + " =  Param(model.CCS_TYPE,model.TECHNOLOGIES,model.SECTOR_ALL,model.AREAS,model.YEAR, mutable=False, domain=Any,default=0," +
            "initialize=Parameters[\"CCS_parameters\"]." + COLNAME + ".squeeze().to_dict())")

    # print("Hey",model.P_forced_prod_ratio_min['Electrolyser', 0, 'Steel','France', 2030])
    # print("Hey2",model.P_output["Biomass",'Steel', "France", 2030])
    # print("Hey3", model.P_forced_prod_t['DRI-EAF', "H2", 'Steel', 'France', 2030])
    ################
    # Variables    #
    ################
    model.V_cost_total = Var(domain=NonNegativeReals,initialize=0)
    model.V_emissions_total = Var(domain=Reals,initialize=0)
    model.V_cost = Var(model.SECTOR,model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0)
    model.V_carbon_cost=Var(model.SECTOR,model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0)
    model.V_technology_cost = Var(model.TECHNOLOGIES,model.SECTOR, model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0)
    model.V_emissions = Var(model.SECTOR,model.AREAS, model.YEAR, domain=Reals,initialize=0)
    model.V_emissions_no_ccs = Var(model.SECTOR, model.AREAS, model.YEAR, domain=Reals, initialize=0)
    model.V_ctax_emissions_plus=Var(model.SECTOR,model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0) #only this one is kept for carbon tax
    model.V_ctax_emissions_minus = Var(model.SECTOR, model.AREAS, model.YEAR, domain=NonPositiveReals,initialize=0)


    model.V_emissions_tech_type = Var(model.TECHNOLOGIES, model.TECH_TYPE,model.SECTOR, model.AREAS, model.YEAR, domain=Reals,initialize=0)
    model.V_emissions_tech_type_plus = Var(model.TECHNOLOGIES, model.TECH_TYPE,model.SECTOR, model.AREAS, model.YEAR,
                                      domain=NonNegativeReals,initialize=0)
    model.V_emissions_tech_type_minus = Var(model.TECHNOLOGIES, model.TECH_TYPE,model.SECTOR, model.AREAS, model.YEAR,
                                       domain=NonPositiveReals,initialize=0)



    model.V_resource_flow = Var(model.RESOURCES,model.SECTOR, model.AREAS, model.YEAR, domain=Reals,initialize=0)
    model.V_resource_inflow = Var(model.RESOURCES, model.SECTOR,model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0)
    model.V_resource_outflow = Var(model.RESOURCES,model.SECTOR, model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0)
    model.V_resource_imports = Var(model.RESOURCES,model.SECTOR, model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0)
    model.V_resource_exports = Var(model.RESOURCES,model.SECTOR, model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0)
    model.V_resource_tech_type_inflow = Var(model.TECHNOLOGIES, model.TECH_TYPE, model.SECTOR, model.RESOURCES, model.AREAS, model.YEAR,initialize=0,
                                       domain=NonNegativeReals)
    model.V_resource_tech_type_outflow = Var(model.TECHNOLOGIES, model.TECH_TYPE,model.SECTOR, model.RESOURCES, model.AREAS, model.YEAR,initialize=0,
                                        domain=NonNegativeReals)
    model.V_resource_tech_type_capacity = Var(model.TECHNOLOGIES, model.TECH_TYPE, model.SECTOR, model.RESOURCES,
                                             model.AREAS, model.YEAR,initialize=0,
                                             domain=Reals)

    model.V_technology_use_coef = Var(model.TECHNOLOGIES, model.TECH_TYPE,model.SECTOR, model.AREAS, model.YEAR,initialize=0,
                                      domain=NonNegativeReals)

    model.V_technology_use_coef_capacity = Var(model.TECHNOLOGIES,model.SECTOR, model.AREAS, model.YEAR, domain=NonNegativeReals,initialize=0)
    model.V_technology_tech_type_use_coef_capacity = Var(model.TECHNOLOGIES, model.TECH_TYPE,model.SECTOR, model.AREAS, model.YEAR,initialize=0,
                                                         domain=NonNegativeReals)
    model.V_added_capacity = Var(model.TECHNOLOGIES,model.SECTOR, model.AREAS, model.YEAR, initialize=0, domain=NonNegativeReals)


    model.V_removed_capacity = Var(model.TECHNOLOGIES,model.SECTOR, model.AREAS, model.YEAR, initialize=0, domain=NonNegativeReals)


    model.V_ccs_capex_cost = Var( model.SECTOR, model.AREAS, model.YEAR,
                               initialize=0, domain=NonNegativeReals)
    model.V_ccs_tech_capex_cost = Var(model.CCS_TYPE,model.TECHNOLOGIES,model.SECTOR, model.AREAS, model.YEAR,
                                 initialize=0, domain=NonNegativeReals)
    model.V_ccs_opex_cost = Var(model.SECTOR, model.AREAS, model.YEAR,
                                 initialize=0, domain=NonNegativeReals)
    model.V_ccs_capacity = Var(model.CCS_TYPE,model.TECHNOLOGIES, model.SECTOR, model.AREAS, model.YEAR,
                                               initialize=0, domain=NonNegativeReals)
    model.V_ccs_tech_type_capacity = Var(model.CCS_TYPE, model.TECHNOLOGIES,model.TECH_TYPE, model.SECTOR, model.AREAS, model.YEAR,
                               initialize=0, domain=NonNegativeReals)
    model.V_ccs_tech_type_usage = Var(model.CCS_TYPE, model.TECHNOLOGIES, model.TECH_TYPE, model.SECTOR, model.AREAS,
                                         model.YEAR,
                                         initialize=0, domain=NonNegativeReals)
    model.V_ccs_added_capacity = Var(model.CCS_TYPE,model.TECHNOLOGIES, model.SECTOR, model.AREAS, model.YEAR,
                                 initialize=0, domain=NonNegativeReals)
    model.V_ccs_removed_capacity = Var(model.CCS_TYPE,model.TECHNOLOGIES, model.SECTOR, model.AREAS, model.YEAR,
                                   initialize=0, domain=NonNegativeReals)
    model.V_captured_emissions = Var(model.TECHNOLOGIES, model.SECTOR, model.AREAS, model.YEAR,
                                   initialize=0, domain=NonNegativeReals)
    model.V_ccs_captured_emissions = Var(model.CCS_TYPE,model.TECHNOLOGIES, model.SECTOR, model.AREAS, model.YEAR,
                                     initialize=0, domain=NonNegativeReals)
    model.V_ccs_tech_type_captured_emissions = Var(model.CCS_TYPE, model.TECHNOLOGIES,model.TECH_TYPE, model.SECTOR, model.AREAS, model.YEAR,
                                         initialize=0, domain=NonNegativeReals)

    model.V_ccs_tech_type_consumption=Var(model.TECHNOLOGIES, model.TECH_TYPE, model.SECTOR,model.RESOURCES, model.AREAS, model.YEAR, initialize=0,
                                   domain=NonNegativeReals)

    return model