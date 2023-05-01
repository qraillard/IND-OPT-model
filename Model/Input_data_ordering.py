import time

from pyomo.environ import *
from pyomo.core import *
from pyomo.opt import SolverFactory
from datetime import timedelta
import pandas as pd
import numpy as np
import re
import sys
import itertools

def resource_sheet(df,sector_list,year_list,areas_list,resource_list):
    parameter_list = ["emissions_r", "flow_cost_r", "is_product","output", "production_error_margin","max_output","min_output","min_export","export","max_import","max_import_ratio","min_import","min_import_ratio","no_import","max_import_ratio_from_start"]
    data = []
    df2 = df
    df2[['RESOURCES','SECTOR', 'AREAS', 'YEAR']] = df2[['RESOURCES','SECTOR', 'AREAS', 'YEAR']].fillna(0)
    df2 = df2.set_index(['RESOURCES','SECTOR', 'AREAS', 'YEAR', 'Parameter'])
    df2=df2['Value'].squeeze()
    # print(df2)
    # print(df2.get(key=("Electricity","nan","France",2015,"flow_cost_r")))
    # print(df2.to_dict())
    # print(df2.to_dict()[("Electricity",np.nan,"France",2015,"flow_cost_r")])
    # # print(df2.loc[("Electricity",np.nan,"France",2015,"flow_cost_r"),"Value"])
    # return 0
    df2=df2.to_dict()
    sect_list=sector_list
    if "All" not in sect_list:
        sect_list=sect_list+["All"]
    for resource in resource_list:
        # print(resource)
        for sector in sect_list:
            # print("\t",sector)
            for area in areas_list:
                # print("\t\t",area)
                for year in year_list:
                    for parameter in parameter_list:
                        value=None
                        for tuple_index in [(resource, sector, area, year, parameter),
                                            (resource,sector, area, 0, parameter),
                                            (resource,sector, 0, year, parameter),
                                            (resource,sector, 0, 0, parameter),
                                            (resource, 0, area, year, parameter),
                                            (resource, 0, area, 0, parameter),
                                            (resource, 0, 0, year, parameter),
                                            (resource, 0, 0, 0, parameter),
                                            (0, 0, 0, 0, parameter)]:

                            if value==None:
                                try:
                                    value=df2[tuple_index]#df2.get(key=tuple_index).values[0]#df2.loc[tuple_index,"Value"] #
                                except:
                                    pass
                            elif value!=None:
                                break

                        data.append([resource, sector, area, year, parameter, value])
    data = pd.DataFrame(data, columns=df.columns)
    data.set_index(['Parameter','RESOURCES','SECTOR', 'AREAS', 'YEAR'], inplace=True)
    data = data.reset_index().pivot(index="YEAR",
                                    columns=['Parameter','RESOURCES','SECTOR', 'AREAS' ],
                                    values=['Value'])

    data = data.astype("float").interpolate(method="linear", limit_direction="forward")
    #
    data = data.melt(ignore_index=False).reset_index()[
        ['RESOURCES','SECTOR', 'AREAS', 'YEAR','Parameter', "value"]].rename(
        columns={"value": "Value"})
    # print(data)
    return data.pivot(index=["RESOURCES","SECTOR","AREAS","YEAR"],columns="Parameter",values="Value")

def technologies_sheet(df,tech_list,sector_list,year_list,areas_list):
    parameter_list = ["discount_rate", "capex", "flow_cost_t","opex_cost", "construction_time", "lifetime","tech_age",
                      "max_capacity_t", "capacity_associated_resource","installation_ramp_t","min_unit_size_t","min_capacity_factor"]
    data = []
    df2 = df
    df2[['TECHNOLOGIES','SECTOR', 'AREAS', 'YEAR']] = df2[['TECHNOLOGIES','SECTOR', 'AREAS', 'YEAR']].fillna(0)
    df2 = df2.set_index(['TECHNOLOGIES','SECTOR', 'AREAS', 'YEAR', 'Parameter'])["Value"].squeeze().to_dict()
    # print(df2[("Biogas_Digester","All",0,2018,"max_capacity_t")])
    sect_list = sector_list
    if "All" not in sect_list:
        sect_list=sect_list+["All"]
    for tech in tech_list:
        for sector in sect_list:
            for area in areas_list:
                for year in year_list:
                    for parameter in parameter_list:
                        value = None
                        for tuple_index in [(tech, sector,area, year, parameter),
                                            (tech,sector, area, 0, parameter),
                                            (tech, sector,0, year, parameter),
                                            (tech, sector,0, 0, parameter),
                                            (tech, 0,0, year, parameter),
                                            (tech, 0, 0, 0, parameter),
                                            (0,sector,0, year, parameter),
                                            (0, sector,0, 0, parameter),
                                            (0,0,0,0, parameter)]:

                            if value == None:
                                try:
                                    value =df2[tuple_index]
                                    # print(tuple_index,df2[tuple_index])# df2.loc[tuple_index, "Value"]#.values[1] #df2.get(key=tuple_index)#
                                    # print(value)
                                except:
                                    pass
                            elif value != None:
                                break
                        data.append([tech, sector,area, year, parameter, value])
    data = pd.DataFrame(data, columns=df.columns)
    data.set_index(['TECHNOLOGIES','SECTOR', 'AREAS', 'YEAR', 'Parameter'], inplace=True)
    for tech in tech_list:
        for sector in sect_list:
            for area in areas_list:
                for parameter in parameter_list:
                    if parameter not in ["capacity_associated_resource","max_capacity_t","tech_age"]:
                        data.loc[(tech, sector,area, slice(None), parameter), "Value"] = data.loc[
                            (tech, sector, area, slice(None), parameter), "Value"].astype("float").interpolate(method="linear",
                                                                                                       limit_direction="forward")
    # print(data)
    # print(data.reset_index().pivot(index=["TECHNOLOGIES","SECTOR","AREAS","YEAR"],columns="Parameter",values="Value"))
    return data.reset_index().pivot(index=["TECHNOLOGIES","SECTOR","AREAS","YEAR"],columns="Parameter",values="Value")

def technologies_resources_sheet(df,sector_list,year_list,t_tt_combinations):
    data = []
    df2=df
    df2[["TECHNOLOGIES", "TECH_TYPE","SECTOR", "YEAR"]]=df2[["TECHNOLOGIES", "TECH_TYPE","SECTOR", "YEAR"]].fillna(0)
    df2 = df2.set_index(["TECHNOLOGIES", "TECH_TYPE","SECTOR", "YEAR"]).stack().reset_index().rename(
        columns={"level_4": "Parameter", 0: "Value"}).set_index(["TECHNOLOGIES", "TECH_TYPE","SECTOR", "YEAR", 'Parameter'])
    df3=df2["Value"].squeeze().to_dict()
    sect_list = sector_list
    if "All" not in sect_list:
        sect_list=sect_list+["All"]

    tech_list=list(df.TECHNOLOGIES.dropna().unique())
    tech_type_list=list(df.TECH_TYPE.unique())
    if "All" not in tech_type_list:
        tech_type_list=tech_type_list+["All"]


    parameter_list=df.columns[4:]
    for tech in tech_list:
        for tech_type in tech_type_list:
            tt = tech_type
            if type(tech_type) != str:
                tt = 0
            if tt in t_tt_combinations[tech]:
                for sector in sect_list:
                    for year in year_list:
                        for parameter in parameter_list:
                            value = None
                            for tuple_index in [(tech, tt,sector, year, parameter),
                                                (tech, tt,sector, 0, parameter),
                                                (tech, tt, 0, year, parameter),
                                                (tech, tt, 0,0, parameter)]:
                                if value == None:
                                    try:
                                        value = df3[tuple_index]#df2.get(key=tuple_index)  # df2.loc[tuple_index, "Value"]
                                    except:
                                        pass
                                elif value != None:
                                    break

                            data.append([tech, tech_type, sector, year, parameter, value])
            else:
                # for sector in sect_list:
                #     for year in year_list:
                #         for parameter in df.columns[4:]:
                #             data.append([tech, tech_type, sector, year, parameter, None])
                data=data+[list(tup) for tup in itertools.product([tech],[tech_type],sect_list,year_list,parameter_list,[0])]
    # print("\t\t Input data cleaned within "+str(time.time()-p)+"s")
    data = pd.DataFrame(data, columns=df2.reset_index().columns)
    data.set_index(['Parameter','TECHNOLOGIES', 'TECH_TYPE','SECTOR', 'YEAR'], inplace=True)
    data=data.reset_index().pivot(index="YEAR", columns=["TECHNOLOGIES","TECH_TYPE","SECTOR","Parameter"], values=['Value'])
    # return data
    # for tech in tech_list:
    #     for tech_type in tech_type_list:
    #         for sector in sect_list:
    #             for parameter in parameter_list:
    #                 if parameter not in ["capacity_associated_resource","max_capacity_t"]:
    #                     data.loc[(tech, tech_type, sector,slice(None), parameter), "Value"] = data.loc[
    #                         (tech, tech_type,sector, slice(None), parameter), "Value"].astype("float").interpolate(method="linear",limit_direction="forward")
    # print("\t\t Interpolation within " + str(time.time() - p) + "s")
    data=data.interpolate(method="linear",limit_direction="forward")
    # print(data)
    data=data.melt(ignore_index=False).reset_index()[["TECHNOLOGIES","TECH_TYPE","SECTOR","Parameter","YEAR","value"]].rename(columns={"value":"Value"}).set_index(
["TECHNOLOGIES","TECH_TYPE","SECTOR","Parameter","YEAR"])

    return data.reset_index().pivot(index=["TECHNOLOGIES","TECH_TYPE","SECTOR","YEAR"],columns="Parameter",values="Value")

def technologies_tech_type_sheet(df,tech_list,sector_list,year_list,areas_list,t_tt_combinations):
    parameter_list = ["forced_prod_ratio_min", "forced_prod_ratio_max", "forced_prod_t","forced_prod_min_t",
                      "forced_resource"]
    data = []
    df2 = df
    df2[['TECHNOLOGIES', 'TECH_TYPE', 'SECTOR','AREAS', 'YEAR']] = df2[['TECHNOLOGIES', 'TECH_TYPE', 'SECTOR','AREAS', 'YEAR']].fillna(0)
    df2 = df2.set_index(['TECHNOLOGIES', 'TECH_TYPE', 'SECTOR','AREAS', 'YEAR', 'Parameter'])["Value"].squeeze().to_dict()
    sect_list = sector_list
    if "All" not in sect_list:
        sect_list=sect_list+["All"]



    for tech in tech_list:
        for tech_type in t_tt_combinations[tech]+["All"]:
            tt = tech_type
            if type(tech_type) != str:
                tt = 0
            for sector in sect_list:
                for area in areas_list:
                    for year in year_list:
                        for parameter in parameter_list:
                            value = None
                            for tuple_index in [(tech, tt, sector,area, year, parameter),
                                                (tech, tt,sector, area, 0, parameter),
                                                (tech, tt, sector,0, year, parameter),
                                                (tech, tt,sector, 0, 0, parameter),
                                                (tech, tt, 0, 0, 0, parameter),
                                                (tech, 0, sector, area, year, parameter),
                                                (tech, 0, sector, area, 0, parameter),
                                                (tech, 0, sector, 0, year, parameter),
                                                (tech, 0, sector, 0, 0, parameter),
                                                (tech, 0, 0, 0, 0, parameter)]:

                                if value == None:
                                    try:
                                        value =df2[tuple_index]#df2.loc[tuple_index, "Value"] #df2.get(key=tuple_index)#
                                        # if parameter=='forced_prod_t':
                                        #     print([tech, tech_type,sector, area, year, parameter, value])
                                    except:
                                        pass
                                elif value != None:
                                    break
                            data.append([tech, tech_type,sector, area, year, parameter, value])
    data = pd.DataFrame(data, columns=df.columns)
    data.set_index(['TECHNOLOGIES', 'TECH_TYPE','SECTOR', 'AREAS', 'YEAR', 'Parameter'], inplace=True)
    for tech in tech_list:
        for tech_type in t_tt_combinations[tech]:
            for sector in sect_list:
                for area in areas_list:
                    for parameter in parameter_list:
                        if parameter not in ["forced_resource","forced_prod_t","forced_prod_min_t","forced_prod_ratio_min","forced_prod_ratio_max"]:
                            data.loc[(tech, tech_type,sector, area, slice(None), parameter), "Value"] = data.loc[
                                (tech, tech_type, sector,area, slice(None), parameter), "Value"].astype("float").interpolate(
                                limit_direction='both')

    return data.reset_index().pivot(index=["TECHNOLOGIES","TECH_TYPE","SECTOR","AREAS","YEAR"],columns="Parameter",values="Value")

def sector_sheet(df,sector_list,year_list,areas_list):
    parameter_list = ["carbon_tax","min_capture_ratio","max_capture_ratio","max_biogas_t","emissions_reduction_ratio_obj"]
    data = []
    df2 = df
    df2[['SECTOR', 'AREAS', 'YEAR']] = df2[['SECTOR', 'AREAS', 'YEAR']].fillna(0)
    df2 = df2.set_index(['SECTOR', 'AREAS', 'YEAR', 'Parameter'])
    sect_list = sector_list
    if "All" not in sect_list:
        sect_list = sect_list + ["All"]
    for sector in sect_list:
        for area in areas_list:
            for year in year_list:
                for parameter in parameter_list:
                    value = None
                    for tuple_index in [(sector, area, year, parameter),
                                        (sector, area, 0, parameter),
                                        (sector, 0, year, parameter),
                                        (sector, 0, 0, parameter),
                                        (0, area, year, parameter),
                                        (0, 0, year, parameter),
                                        (0, 0, 0, parameter)]:

                        if value == None:
                            try:
                                value = df2.loc[tuple_index, "Value"] #df2.get(key=tuple_index)  #
                                # if parameter=='forced_prod_t':
                                #     print([tech, tech_type,sector, area, year, parameter, value])
                            except:
                                pass
                        elif value != None:
                            break

                    data.append([sector, area, year, parameter, value])
    data = pd.DataFrame(data, columns=df.columns)

    data.set_index(['SECTOR', 'AREAS', 'YEAR', 'Parameter'], inplace=True)
    for sector in sect_list:
        for area in areas_list:
            for parameter in parameter_list:
                data.loc[(sector, area, slice(None), parameter), "Value"] = data.loc[
                    (sector, area, slice(None), parameter), "Value"].interpolate(limit_direction='forward')
    return data.reset_index().pivot(index=["SECTOR","AREAS","YEAR"],columns="Parameter",values="Value")


def ccs_sheet(df, sector_list, year_list, areas_list, tech_list,ccs_tech_combinations):
    parameter_list = ["ccs_lifetime", "ccs_ratio", "ccs_capex", "ccs_opex","ccs_discount_rate", "ccs_elec", "ccs_gas","ccs_force_install_ratio","ccs_force_capture_ratio"]
    data = []
    ccr_list = list(df.CCS_TYPE.unique())
    ccr_list.remove(np.nan)

    df2 = df
    df2[['CCS_TYPE', 'TECHNOLOGIES', 'SECTOR', 'AREAS', 'YEAR', 'Parameter']] = df2[['CCS_TYPE', 'TECHNOLOGIES', 'SECTOR', 'AREAS', 'YEAR', 'Parameter']].fillna(0)
    df2 = df2.set_index(['CCS_TYPE', 'TECHNOLOGIES', 'SECTOR', 'AREAS', 'YEAR', 'Parameter'])["Value"].squeeze().to_dict()
    sect_list = sector_list
    if "All" not in sect_list:
        sect_list = sect_list + ["All"]
    for ccr in ccr_list:
        for tech in tech_list:
            # print(ccr,tech)
            if tech in ccs_tech_combinations[ccr]:
                # print("\t",ccs_tech_combinations[ccr])
                for sector in sect_list:
                    for area in areas_list:
                        for year in year_list:
                            for parameter in parameter_list:
                                value = None
                                for tuple_index in [(ccr, tech, sector, area, year, parameter),
                                                    (ccr, tech, sector, area, 0, parameter),
                                                    (ccr, tech, 0, area, year, parameter),
                                                    (ccr, tech, sector, 0, year, parameter),
                                                    (ccr, tech, sector, 0, 0, parameter),
                                                    (ccr, tech, 0, 0, year, parameter),
                                                    (ccr, tech, 0, 0, 0, parameter),
                                                    (0, 0, 0, 0, 0, parameter)]:

                                    if value == None:
                                        try:
                                            value = df2[tuple_index]#df2.loc[tuple_index, "Value"] # df2.get(key=tuple_index)  #
                                            # print(tuple_index,df2[tuple_index])
                                            # if parameter=='forced_prod_t':
                                            #     print([tech, tech_type,sector, area, year, parameter, value])
                                        except:
                                            pass
                                    elif value != None:
                                        break

                                data.append([ccr, tech, sector, area, year, parameter, value])
            else:
                # for sector in sect_list:
                #     for area in areas_list:
                #         for year in year_list:
                #             for parameter in parameter_list:
                #                 data.append([ccr, tech, sector, area, year, parameter, 0])
                data = data + [list(tup) for tup in itertools.product([ccr], [tech], sect_list,areas_list, year_list, parameter_list, [0])]
    data = pd.DataFrame(data, columns=df.columns)
    # return data
    # print(data)
    data.set_index(['Parameter','CCS_TYPE', 'TECHNOLOGIES', 'SECTOR', 'AREAS', 'YEAR'], inplace=True)
    data = data.reset_index().pivot(index="YEAR", columns=['Parameter','CCS_TYPE', 'TECHNOLOGIES', 'SECTOR', 'AREAS'],
                                    values=['Value'])

    data = data.astype("float").interpolate(method="linear", limit_direction="forward")
    #
    data = data.melt(ignore_index=False).reset_index()[
        ['CCS_TYPE', 'TECHNOLOGIES', 'SECTOR', 'AREAS', 'YEAR','Parameter', "value"]].rename(columns={"value": "Value"})

    return data.pivot(index=['CCS_TYPE', 'TECHNOLOGIES', 'SECTOR', 'AREAS', 'YEAR'],
                                    columns="Parameter", values="Value")

def tech_and_tech_type_combinations(df):
    combinations = {}
    for tech in df.TECHNOLOGIES.unique():
        combinations[tech] = list(df[df.TECHNOLOGIES == tech].TECH_TYPE.fillna(0).unique())
    return combinations

def ccs_tech_combinations_fct(df):
    combinations = {}
    for ccs in df.CCS_TYPE.unique():
        combinations[ccs] = list(df[df.CCS_TYPE == ccs].TECHNOLOGIES.unique())
    return combinations


def max_biogas_readjustment(df,available_potential_ratio):
    df1=df
    df1["max_biogas_t"]=df1["max_biogas_t"].astype("float")*available_potential_ratio
    return df1
