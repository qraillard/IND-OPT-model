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
                        if sector!="All":
                            tuple_list=[(resource, sector, area, year, parameter),
                                            (resource,sector, area, 0, parameter),
                                            (resource,sector, 0, year, parameter),
                                            (resource,sector, 0, 0, parameter),
                                            (resource, 0, area, year, parameter),
                                            (resource, 0, area, 0, parameter),
                                            (resource, 0, 0, year, parameter),
                                            (resource, 0, 0, 0, parameter),
                                            (0, 0, 0, 0, parameter)]
                        else:
                            tuple_list = [(resource, sector, area, year, parameter),
                                            (resource,sector, area, 0, parameter),
                                            (resource,sector, 0, year, parameter),
                                            (resource,sector, 0, 0, parameter)]
                        for tuple_index in tuple_list:

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
                        if sector!="All" and year<=2050:
                            tuple_list=[(tech, sector,area, year, parameter),
                                            (tech,sector, area, 0, parameter),
                                            (tech, sector,0, year, parameter),
                                            (tech, sector,0, 0, parameter),
                                            (tech, 0, area, year, parameter),
                                            (tech, 0,0, year, parameter),
                                            (tech, 0, area, 0, parameter),
                                            (tech, 0, 0, 0, parameter),
                                            (0,sector,0, year, parameter),
                                            (0, sector,0, 0, parameter),
                                            (0, 0, 0, year, parameter),
                                            (0,0,0,0, parameter)]
                        elif sector!="All" and year>2050:
                            tuple_list=[(tech, sector,area, 2050, parameter),
                                            (0, 0, 0, 2050, parameter),
                                            (tech,sector, area, 0, parameter),
                                            (tech, sector,0, 2050, parameter),
                                            (tech, sector,0, 0, parameter),
                                            (tech, 0, area, 2050, parameter),
                                            (tech, 0,0, 2050, parameter),
                                            (tech, 0, area, 0, parameter),
                                            (tech, 0, 0, 0, parameter),
                                            (0,sector,0, 2050, parameter),
                                            (0, sector,0, 0, parameter),
                                            (0,0,0,0, parameter)]

                        elif sector=="All" and year<=2050:
                            tuple_list = [(tech, sector, area, year, parameter),
                                          (tech, sector, area, 0, parameter),
                                          (tech, sector, 0, year, parameter),
                                          (tech, sector, 0, 0, parameter),
                                          (0, sector, 0, year, parameter),
                                          (0, sector, 0, 0, parameter)]

                        else:
                            tuple_list = [(tech, sector, area, 2050, parameter),
                                          (tech, sector, area, 0, parameter),
                                          (tech, sector, 0, 2050, parameter),
                                          (tech, sector, 0, 0, parameter),
                                          (0, sector, 0, 2050, parameter),
                                          (0, sector, 0, 0, parameter)]
                        for tuple_index in tuple_list:

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
    u=data[data.Parameter.isin(["capacity_associated_resource","max_capacity_t","tech_age","installation_ramp_t"])].set_index(["TECHNOLOGIES", "SECTOR","AREAS", "Parameter", "YEAR"])

    data=data[~data.Parameter.isin(["capacity_associated_resource","max_capacity_t","tech_age","installation_ramp_t"])].set_index(["TECHNOLOGIES", "SECTOR","AREAS", "Parameter", "YEAR"])
    # data.set_index(['Parameter', 'TECHNOLOGIES', 'TECH_TYPE', 'SECTOR', 'YEAR'], inplace=True)
    data = data.reset_index().pivot(index="YEAR", columns=["TECHNOLOGIES", "SECTOR","AREAS", "Parameter"],
                                    values=['Value'])
    data = data.astype("float").interpolate(method="linear", limit_direction="forward")
    # print(data)
    data = data.melt(ignore_index=False).reset_index()[
        ["TECHNOLOGIES", "SECTOR","AREAS", "Parameter", "YEAR", "value"]].rename(
        columns={"value": "Value"}).set_index(
        ["TECHNOLOGIES", "SECTOR","AREAS", "Parameter", "YEAR"])
    # print(data)
    data=pd.concat([data,u.rename(
        columns={"value": "Value"})])
    # print(data.reset_index().pivot(index=["TECHNOLOGIES","SECTOR","AREAS","YEAR"],columns="Parameter",values="Value"))
    # data.set_index(['TECHNOLOGIES','SECTOR', 'AREAS', 'YEAR', 'Parameter'], inplace=True)
    # for tech in tech_list:
    #     for sector in sect_list:
    #         for area in areas_list:
    #             for parameter in parameter_list:
    #                 if parameter not in ["capacity_associated_resource","max_capacity_t","tech_age"]:
    #                     data.loc[(tech, sector,area, slice(None), parameter), "Value"] = data.loc[
    #                         (tech, sector, area, slice(None), parameter), "Value"].astype("float").interpolate(method="linear",
    #                                                                                                    limit_direction="forward")
    # print(data)
    # print(data.reset_index().pivot(index=["TECHNOLOGIES","SECTOR","AREAS","YEAR"],columns="Parameter",values="Value"))
    return data.reset_index().pivot(index=["TECHNOLOGIES","SECTOR","AREAS","YEAR"],columns="Parameter",values="Value")

def technologies_resources_sheet(df,sector_list,year_list,t_tt_combinations,s_t_combinations):
    a=time.time()
    data = []
    df2=df
    df2[["TECHNOLOGIES", "TECH_TYPE","SECTOR", "YEAR"]]=df2[["TECHNOLOGIES", "TECH_TYPE","SECTOR", "YEAR"]].fillna(0)
    df2 = df2.set_index(["TECHNOLOGIES", "TECH_TYPE","SECTOR", "YEAR"]).stack().reset_index().rename(
        columns={"level_4": "Parameter", 0: "Value"}).set_index(["TECHNOLOGIES", "TECH_TYPE","SECTOR", "YEAR", 'Parameter'])
    df3=df2["Value"].squeeze().to_dict()
    sect_list = sector_list
    try:
        sect_list.remove("All")
    except:
        pass
    # if "All" not in sect_list:
    #     sect_list=sect_list+["All"]

    # tech_list=list(df.TECHNOLOGIES.dropna().unique())
    # tech_type_list=list(df.TECH_TYPE.unique())
    # if "All" not in tech_type_list:
    #     tech_type_list=tech_type_list+["All"]

    # print(time.time()-a)
    # a = time.time()
    parameter_list=df.columns[4:]

    for sector in sect_list:
        for tech in s_t_combinations[sector]:
            # t=tech
            # if t in s_t_combinations[sector]:
            for tech_type in t_tt_combinations[tech]:
                tt = tech_type
                # if type(tech_type) != str:
                #     tt = 0
                # if tt in t_tt_combinations[t]:

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
            #         else:
            #             data=data+[list(tup) for tup in itertools.product([tech],[tech_type],sect_list,year_list,parameter_list,[0])]
            # else:
            #     data = data + [list(tup) for tup in itertools.product([tech], tech_type_list, sect_list, year_list, parameter_list, [0])]
    # print(time.time() - a)
    # a = time.time()
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
    # print(time.time() - a)
    # a = time.time()
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

    tech_type_list=[]
    for l in list(t_tt_combinations.values()):
        tech_type_list+=l
    tech_type_list=set(tech_type_list)
    tech_type_list.add("All")


    for tech in tech_list:
        for tech_type in tech_type_list:
            tt = tech_type
            if type(tech_type) != str:
                tt = 0
            for sector in sect_list:
                for area in areas_list:
                    for year in year_list:
                        for parameter in parameter_list:
                            value = None
                            if sector != "All":
                                tuple_list = [(tech, tt, sector,area, year, parameter),
                                                (tech, tt,sector, area, 0, parameter),
                                                (tech, tt, sector,0, year, parameter),
                                                (tech, tt,sector, 0, 0, parameter),
                                                (tech, tt, 0, 0, 0, parameter),
                                                (tech, 0, sector, area, year, parameter),
                                                (tech, 0, sector, area, 0, parameter),
                                                (tech, 0, sector, 0, year, parameter),
                                                (tech, 0, sector, 0, 0, parameter),
                                                (tech, 0, 0, 0, 0, parameter)]
                            else:
                                tuple_list = [(tech, tt, sector,area, year, parameter),
                                                (tech, tt,sector, area, 0, parameter),
                                                (tech, tt, sector,0, year, parameter),
                                                (tech, tt,sector, 0, 0, parameter),
                                                (tech, 0, sector, area, year, parameter),
                                                (tech, 0, sector, area, 0, parameter),
                                                (tech, 0, sector, 0, year, parameter),
                                                (tech, 0, sector, 0, 0, parameter)]
                            for tuple_index in tuple_list:
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
    u = data[data.Parameter.isin(["forced_resource","forced_prod_t","forced_prod_min_t","forced_prod_ratio_min","forced_prod_ratio_max"])].set_index(
        ['TECHNOLOGIES', 'TECH_TYPE','SECTOR', 'AREAS','Parameter', 'YEAR'])

    data = data[~data.Parameter.isin(["forced_resource","forced_prod_t","forced_prod_min_t","forced_prod_ratio_min","forced_prod_ratio_max"])].set_index(
        ['TECHNOLOGIES', 'TECH_TYPE','SECTOR', 'AREAS','Parameter', 'YEAR'])

    data = data.reset_index().pivot(index="YEAR", columns=["TECHNOLOGIES",'TECH_TYPE', "SECTOR", "AREAS", "Parameter"],
                                    values=['Value'])
    data = data.astype("float").interpolate(method="linear", limit_direction="forward")
    # print(data)
    data = data.melt(ignore_index=False).reset_index()[
        ["TECHNOLOGIES",'TECH_TYPE', "SECTOR", "AREAS", "Parameter", "YEAR", "value"]].rename(
        columns={"value": "Value"}).set_index(
        ["TECHNOLOGIES", 'TECH_TYPE',"SECTOR", "AREAS", "Parameter", "YEAR"])
    # print(data)
    data = pd.concat([data, u.rename(
        columns={"value": "Value"})])

    # data.set_index(['TECHNOLOGIES', 'TECH_TYPE','SECTOR', 'AREAS', 'YEAR', 'Parameter'], inplace=True)
    # for tech in tech_list:
    #     for tech_type in t_tt_combinations[tech]:
    #         for sector in sect_list:
    #             for area in areas_list:
    #                 for parameter in parameter_list:
    #                     if parameter not in ["forced_resource","forced_prod_t","forced_prod_min_t","forced_prod_ratio_min","forced_prod_ratio_max"]:
    #                         data.loc[(tech, tech_type,sector, area, slice(None), parameter), "Value"] = data.loc[
    #                             (tech, tech_type, sector,area, slice(None), parameter), "Value"].astype("float").interpolate(
    #                             limit_direction='both')

    return data.reset_index().pivot(index=["TECHNOLOGIES","TECH_TYPE","SECTOR","AREAS","YEAR"],columns="Parameter",values="Value")

def sector_sheet(df,sector_list,year_list,areas_list):
    parameter_list = ["carbon_tax","min_capture_ratio","max_capture_ratio","max_biogas_from_digester_t",
                      "max_biogas_from_gasification_t","emissions_reduction_ratio_obj","co2_transport_and_storage_cost",
                      "methane_leakage_ratio","olefins_carbone_storage_rate","methane_gwp"]
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
                    if sector!="All":
                        tuple_list=[(sector, area, year, parameter),
                                        (sector, area, 0, parameter),
                                        (sector, 0, year, parameter),
                                        (sector, 0, 0, parameter),
                                        (0, area, year, parameter),
                                        (0, 0, year, parameter),
                                        (0, 0, 0, parameter)]
                    else:
                        tuple_list=[(sector, area, year, parameter),
                                        (sector, area, 0, parameter),
                                        (sector, 0, year, parameter),
                                        (sector, 0, 0, parameter)]
                    for tuple_index in tuple_list:
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


def ccs_sheet(df, sector_list, year_list, areas_list, sector_tech_ccs_combinations):
    parameter_list = ["ccs_lifetime", "ccs_ratio", "ccs_capex", "ccs_opex","ccs_discount_rate", "ccs_elec", "ccs_gas","ccs_biomass","ccs_force_install_ratio","ccs_force_capture_ratio"]
    data = []
    # ccr_list = list(ccs_tech_combinations.keys())
    # try:
    #     ccr_list.remove(np.nan)
    # except:
    #     pass

    df2 = df
    df2[['CCS_TYPE', 'TECHNOLOGIES', 'SECTOR', 'AREAS', 'YEAR', 'Parameter']] = df2[['CCS_TYPE', 'TECHNOLOGIES', 'SECTOR', 'AREAS', 'YEAR', 'Parameter']].fillna(0)
    df2 = df2.set_index(['CCS_TYPE', 'TECHNOLOGIES', 'SECTOR', 'AREAS', 'YEAR', 'Parameter'])["Value"].squeeze().to_dict()

    sect_list = sector_list
    try:
        sect_list.remove("All")
    except:
        pass
    # for ccr in ccr_list:
    #     for tech in tech_list:
    #         # print(ccr,tech)
    #         if tech in ccs_tech_combinations[ccr]:
    #             # print("\t",ccs_tech_combinations[ccr])
    #             for sector in sect_list:
    for sector in sector_tech_ccs_combinations.keys():
        for tech in sector_tech_ccs_combinations[sector].keys():
            for ccr in sector_tech_ccs_combinations[sector][tech]:
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
            # else:
            #     # for sector in sect_list:
            #     #     for area in areas_list:
            #     #         for year in year_list:
            #     #             for parameter in parameter_list:
            #     #                 data.append([ccr, tech, sector, area, year, parameter, 0])
            #     data = data + [list(tup) for tup in itertools.product([ccr], [tech], sect_list,areas_list, year_list, parameter_list, [0])]
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

def sector_tech_combinations(df):
    combinations = {}
    sect_list=set(df.SECTOR.unique())
    try:
        sect_list.remove(0)
    except:
        pass
    for sector in sect_list:
        combinations[sector] = list(df[df.SECTOR.isin([0,sector])].TECHNOLOGIES.unique())
    return combinations
def ccs_tech_combinations_fct(df):
    combinations = {}
    for ccs in df.CCS_TYPE.unique():
        combinations[ccs] = list(df[df.CCS_TYPE == ccs].TECHNOLOGIES.unique())
    return combinations

def tech_ccs_combinations_fct(df):
    combinations = {}
    tech_list=set(df.TECHNOLOGIES.unique())
    try:
        tech_list.remove(0)
    except:
        pass
    for tech in tech_list:
        combinations[tech] = list(df[df.TECHNOLOGIES==tech].CCS_TYPE.unique())
    return combinations

def sector_tech_ccs_combinations_fct(df,sector_list):

    # sect_list = set(df.SECTOR.unique())
    sect_list=set(sector_list)
    sect_list.remove("All")
    combinations = {}
    all=None
    for sect in sect_list:
        tech_list=set(df[df.SECTOR.isin([sect,0])].TECHNOLOGIES.unique())
        u={}
        try:
            tech_list.remove(0)
        except:
            pass

        for tech in tech_list:
            u[tech]=list(df[df.TECHNOLOGIES==tech].CCS_TYPE.unique())

        if sect!=0:
            combinations[sect]=u
        else:
            all=u
    for key in combinations.keys():
        try:
            combinations[key].update(all)
        except:
            pass

    return combinations

def max_biogas_readjustment(df,available_potential_ratio):
    df1=df
    df1["max_biogas_from_digester_t"]=df1["max_biogas_from_digester_t"].astype("float")*available_potential_ratio
    df1["max_biogas_from_gasification_t"] = df1["max_biogas_from_gasification_t"].astype("float") * available_potential_ratio
    return df1

def biomass_waste_potential_readjustment(df,available_potential_ratio):
    df1=df
    df1.loc[(["Biomass_low_price","Biomass_med_price","Biomass_high_price","Municipal_wastes","Agriculture_wastes"],"All"),"max_capacity_t"]=\
        df1.loc[(["Biomass_low_price","Biomass_med_price","Biomass_high_price","Municipal_wastes","Agriculture_wastes"],"All"),"max_capacity_t"].astype(float).interpolate(method="linear",limit_direction="forward") * available_potential_ratio
    return df1


