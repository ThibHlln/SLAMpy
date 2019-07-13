from os import path, sep
import arcpy
from _DiffuseAgriculture import cct_v2_geoprocessing
from _DiffuseAtmDepo import atmos_v2_geoprocessing
from _DiffuseForestry import forestry_v1_geoprocessing
from _DiffusePeat import peat_v1_geoprocessing
from _DiffuseUrban import urban_v1_geoprocessing
from _DirectIndustry import industry_v2_geoprocessing
from _DirectSepticTanks import dwts_v2_geoprocessing
from _DirectWastewater import ww_2015_geoprocessing


class SLAMv3(object):
    def __init__(self):
        self.__version__ = '3'
        self.label = 'SLAM [v{}]'.format(self.__version__)
        self.description = "Calculates the nutrient (N or P) loads from all sources."
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Define Workspace
        root = path.dirname(path.dirname(path.realpath(__file__)))
        arcpy.env.workspace = root

        # Parameters for Folders Options
        in_gdb = sep.join([root, 'in', 'input.gdb'])

        in_fld = sep.join([root, 'in'])

        out_gdb = arcpy.Parameter(
            displayName="Output Geodatabase",
            name="out_gdb",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input",
            category='# Folders Settings')
        out_gdb.value = sep.join([root, 'out', 'output.gdb'])

        out_fld = arcpy.Parameter(
            displayName="Output Folder",
            name="out_fld",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input",
            category='# Folders Settings')
        out_fld.value = sep.join([root, 'out'])

        # Parameters Common to All Sources
        project_name = arcpy.Parameter(
            displayName="Name of the Project",
            name="project_name",
            datatype="GPString",
            parameterType="Required",
            direction="Input")

        nutrient = arcpy.Parameter(
            displayName="Nutrient of Interest",
            name="nutrient",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        nutrient.filter.type = "ValueList"
        nutrient.filter.list = ['Nitrogen (N)', 'Phosphorus (P)']

        region = arcpy.Parameter(
            displayName="Region of Interest",
            name="region",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        selection = arcpy.Parameter(
            displayName="Selection within Region",
            name="selection",
            datatype="GPSQLExpression",
            parameterType="Optional",
            direction="Input")
        selection.parameterDependencies = [region.name]

        field = arcpy.Parameter(
            displayName="Field for Summary Spatial Scale",
            name="field",
            datatype="Field",
            parameterType="Required",
            direction="Input")
        field.parameterDependencies = [region.name]

        # Parameters specific to Diffuse Agriculture
        in_arable = arcpy.Parameter(
            displayName="CCT Data for Arable",
            name="in_arable",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Diffuse Agriculture Data Settings")
        in_arable.value = sep.join([in_gdb, 'PathwaysCCT_IRL_Arable_LPIS'])

        in_pasture = arcpy.Parameter(
            displayName="CCT Data for Pasture",
            name="in_pasture",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Diffuse Agriculture Data Settings")
        in_pasture.value = sep.join([in_gdb, 'PathwaysCCT_IRL_Pasture_LPIS'])

        # Parameters specific to Atmospheric Deposition
        in_atm_depo = arcpy.Parameter(
            displayName="Data for Atmospheric Deposition",
            name="in_atm_depo",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Atmospheric Deposition Data Settings")
        in_atm_depo.value = sep.join([in_gdb, 'AtmosDep_Lakes'])

        # Parameters specific to Forestry, Peat, and Urban
        in_land_cover = arcpy.Parameter(
            displayName="Corine Land Cover Data",
            name="in_land_cover",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Forestry, Peat, and Urban Data Settings")
        in_land_cover.value = sep.join([in_gdb, 'clc12_IE'])

        in_factors_n = arcpy.Parameter(
            displayName="Land Cover Factors for Nitrogen (N)",
            name="in_factors_n",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            category="Forestry, Peat, and Urban Data Settings")
        in_factors_n.value = sep.join([in_fld, 'LAM_Factors.xlsx', 'Corine_N$'])

        in_factors_p = arcpy.Parameter(
            displayName="Land Cover Factors for Phosphorus (P)",
            name="in_factors_p",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            category="Forestry, Peat, and Urban Data Settings")
        in_factors_p.value = sep.join([in_fld, 'LAM_Factors.xlsx', 'Corine_P$'])

        # Parameters specific to Industry
        in_ipc = arcpy.Parameter(
            displayName="IPC Licences Data",
            name="in_ipc",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Industry Data Settings")
        in_ipc.value = sep.join([in_gdb, 'IPPC_Loads_LAM2'])

        in_sect4 = arcpy.Parameter(
            displayName="Section 4 Licences Data",
            name="in_sect4",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Industry Data Settings")
        in_sect4.value = sep.join([in_gdb, 'Section4Discharges_D07_IsMain'])

        # Parameters specific to Septic Tanks
        in_dwts = arcpy.Parameter(
            displayName="Domestic Septic Tanks Data",
            name="in_dwts",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Septic Tanks Data Settings")
        in_dwts.value = sep.join([in_gdb, 'SepticTankSystems_LoadModel17'])

        # Parameters specific to Wastewater Treatment Plants
        in_agglo = arcpy.Parameter(
            displayName="Agglomerations Discharges Data",
            name="in_agglo",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Wastewater Data Settings")
        in_agglo.value = sep.join([in_gdb, 'SLAM_Agglom15_March17_IsMain'])

        return [out_gdb, out_fld,
                project_name, nutrient, region, selection, field,
                in_arable, in_pasture,
                in_atm_depo,
                in_land_cover, in_factors_n, in_factors_p,
                in_ipc, in_sect4,
                in_dwts,
                in_agglo]

    def execute(self, parameters, messages):
        # retrieve parameters
        out_gdb, out_fld, project_name, nutrient, region, selection, field, in_arable, in_pasture, in_atm_depo, \
            in_land_cover, in_factors_n, in_factors_p, in_ipc, in_sect4, in_dwts, in_agglo = \
            [p.valueAsText for p in parameters]

        # determine which nutrient to work on
        nutrient = 'N' if nutrient == 'Nitrogen (N)' else 'P'

        # determine which location to work on
        if selection:  # i.e. selection requested
            messages.addMessage("> Selecting requested Location(s) within Region.")
            location = sep.join([out_gdb, project_name + '_SelectedRegion'])
            arcpy.Select_analysis(region, location, selection)
        else:
            location = region

        # determine which factors to use
        in_factors = in_factors_n if nutrient == 'N' else in_factors_p

        # run geoprocessing functions for each source load
        out_arable, out_pasture = \
            cct_v2_geoprocessing(project_name, nutrient, location, in_arable, in_pasture, out_gdb, messages)
        out_atm_depo = \
            atmos_v2_geoprocessing(project_name, nutrient, location, in_atm_depo, out_gdb, messages)
        out_forest = \
            forestry_v1_geoprocessing(project_name, nutrient, location, in_land_cover, in_factors, out_gdb, messages)
        out_peat = \
            peat_v1_geoprocessing(project_name, nutrient, location, in_land_cover, in_factors, out_gdb, messages)
        out_urban = \
            urban_v1_geoprocessing(project_name, nutrient, location, in_land_cover, in_factors, out_gdb, messages)
        out_ipc, out_sect4 = \
            industry_v2_geoprocessing(project_name, nutrient, location, in_ipc, in_sect4, out_gdb, messages)
        out_dwts = \
            dwts_v2_geoprocessing(project_name, nutrient, location, in_dwts, out_gdb, messages)
        out_agglo = \
            ww_2015_geoprocessing(project_name, nutrient, location, in_agglo, out_gdb, messages)

        # run geoprocessing function for load apportionment
        load_summary_v3_geoprocessing(project_name, nutrient, location, field, out_gdb,
                                      out_arable, out_pasture, out_atm_depo, out_forest, out_peat, out_urban,
                                      out_ipc, out_sect4, out_dwts, out_agglo,
                                      messages)

        # garbage collection
        if selection:
            arcpy.Delete_management(location)


def load_summary_v3_geoprocessing(project_name, nutrient, location, field, out_gdb,
                                  out_arable, out_pasture, out_atm_depo, out_forest, out_peat, out_urban,
                                  out_ipc, out_sect4, out_dwts, out_agglo,
                                  messages,
                                  out_summary=None):

    # calculate the summary statistics using the sorting field provided for each source load
    messages.addMessage("> Calculating summary loads for all sources of {}.".format(nutrient))

    arcpy.Statistics_analysis(in_table=out_arable, out_table=out_arable + '_stats',
                              statistics_fields=[["GWCrop2CCT", "SUM"], ["Crop2CCT", "SUM"]], case_field=field)
    arcpy.Statistics_analysis(in_table=out_pasture, out_table=out_pasture + '_stats',
                              statistics_fields=[["GWPast2CCT", "SUM"], ["Past2CCT", "SUM"]], case_field=field)

    arcpy.Statistics_analysis(in_table=out_atm_depo, out_table=out_atm_depo + '_stats',
                              statistics_fields=[["Atmos2calc", "SUM"]], case_field=field)

    arcpy.Statistics_analysis(in_table=out_forest, out_table=out_forest + '_stats',
                              statistics_fields=[["For1calc", "SUM"]], case_field=field)

    arcpy.Statistics_analysis(in_table=out_peat, out_table=out_peat + '_stats',
                              statistics_fields=[["Peat1calc", "SUM"]], case_field=field)

    arcpy.Statistics_analysis(in_table=out_urban, out_table=out_urban + '_stats',
                              statistics_fields=[["Urb0calc", "SUM"]], case_field=field)

    arcpy.Statistics_analysis(in_table=out_ipc, out_table=out_ipc + '_stats',
                              statistics_fields=[["IPPC_calc", "SUM"]], case_field=field)
    arcpy.Statistics_analysis(in_table=out_sect4, out_table=out_sect4 + '_stats',
                              statistics_fields=[["Sect4_Load", "SUM"]], case_field=field)

    arcpy.Statistics_analysis(in_table=out_dwts, out_table=out_dwts + '_stats',
                              statistics_fields=[["GW_DWTS", "SUM"], ["DWTS", "SUM"]], case_field=field)

    arcpy.Statistics_analysis(in_table=out_agglo, out_table=out_agglo + '_stats',
                              statistics_fields=[["CSO15", "SUM"], ["Agglom2015", "SUM"]], case_field=field)

    # copy the input region or sub-region into the output gdb to store the results in
    messages.addMessage("> Creating output feature class to store load apportionment for {}.".format(nutrient))

    if not out_summary:
        out_summary = sep.join([out_gdb, project_name + '_{}_Loads_Summary'.format(nutrient)])

    arcpy.CopyFeatures_management(in_features=location, out_feature_class=out_summary)

    # combine the source loads into output summary
    messages.addMessage("> Gathering all sources of {} in output feature class.".format(nutrient))

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_arable + '_stats', join_field=field,
                               fields=["SUM_GWCrop2CCT", "SUM_Crop2CCT"])
    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_pasture + '_stats', join_field=field,
                               fields=["SUM_GWPast2CCT", "SUM_Past2CCT"])

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_atm_depo + '_stats', join_field=field,
                               fields=["SUM_Atmos2calc"])

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_forest + '_stats', join_field=field,
                               fields=["SUM_For1calc"])

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_peat + '_stats', join_field=field,
                               fields=["SUM_Peat1calc"])

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_urban + '_stats', join_field=field,
                               fields=["SUM_Urb0calc"])

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_ipc + '_stats', join_field=field,
                               fields=["SUM_IPPC_calc"])
    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_sect4 + '_stats', join_field=field,
                               fields=["SUM_Sect4_Load"])

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_dwts + '_stats', join_field=field,
                               fields=["SUM_GW_DWTS", "SUM_DWTS"])

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_agglo + '_stats', join_field=field,
                               fields=["SUM_CSO15", "SUM_Agglom2015"])

    # garbage collection of the summary stats feature classes created for each individual source load
    for source in [out_arable, out_pasture, out_atm_depo, out_forest, out_peat,
                   out_urban, out_ipc, out_sect4, out_dwts, out_agglo]:
        arcpy.Delete_management(source + '_stats')