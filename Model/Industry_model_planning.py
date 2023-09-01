from pyomo.environ import *
from pyomo.opt import SolverFactory
from pyomo.core import *
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from Model.Model_initialization import *
from Model.Economic import *
from Model.Planning import *
from Model.Flow_management import *
from Model.CCS_specific import *


def GetIndustryModel(Parameters,t_tt_combinations,s_t_combinations,tech_ccs_combinations,sector_tech_ccs_combinations,CCU_negative_emissions=False):
    # model = ConcreteModel()

    model=Create_Sets_Parameters_Variables(Parameters,t_tt_combinations,s_t_combinations,tech_ccs_combinations,sector_tech_ccs_combinations)
    model.P_CCU_negative_emissions=CCU_negative_emissions
    model=Cost_Emissions_Obj_Ctr(model,t_tt_combinations,s_t_combinations)
    model=Capacity_planning(model,t_tt_combinations,s_t_combinations)
    model=Flow_management_Ctr(model,t_tt_combinations,s_t_combinations)
    model=CCS_specific_Ctr(model,t_tt_combinations,s_t_combinations,sector_tech_ccs_combinations)

    return model