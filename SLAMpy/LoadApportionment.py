from os import path, sep
import arcpy
from _DiffuseAgriculture import agri_v2_geoprocessing
from _DiffuseAtmDepo import atmos_v2_geoprocessing
from _DiffuseForestry import forestry_v1_geoprocessing
from _DiffusePeat import peat_v1_geoprocessing
from _DiffuseUrban import urban_v1_geoprocessing
from _DirectIndustry import industry_v2_geoprocessing
from _DirectSepticTanks import septic_v2_geoprocessing
from _DirectWastewater import wastewater_v2_geoprocessing


class LoadApportionmentV3(object):
    def __init__(self):
        self.__version__ = '3'
        self.label = 'Source Load Apportionment [v{}]'.format(self.__version__)
        self.description = "Calculates the nutrient (N or P) loads from all diffuse and point sources."
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
            displayName="Field for Spatial Discretisation of Loads Summary",
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

        ex_arable = arcpy.Parameter(
            displayName="Existing output for arable to use as a substitute to the tool",
            name="ex_arable",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input",
            category="Diffuse Agriculture Data Settings")

        ex_pasture = arcpy.Parameter(
            displayName="Existing output for pasture to use as a substitute to the tool",
            name="ex_pasture",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input",
            category="Diffuse Agriculture Data Settings")

        # Parameters specific to Atmospheric Deposition
        in_atm_depo = arcpy.Parameter(
            displayName="Data for Atmospheric Deposition",
            name="in_atm_depo",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Atmospheric Deposition Data Settings")
        in_atm_depo.value = sep.join([in_gdb, 'AtmosDep_Lakes'])

        ex_atm_depo = arcpy.Parameter(
            displayName="Existing output for atmospheric deposition to use as a substitute to the tool",
            name="ex_atm_depo",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input",
            category="Atmospheric Deposition Data Settings")

        # Parameters specific to Forestry, Peat, and Urban
        in_land_cover = arcpy.Parameter(
            displayName="Corine Land Cover Data",
            name="in_land_cover",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Forestry, Peat, and Diffuse Urban Data Settings")
        in_land_cover.value = sep.join([in_gdb, 'clc12_IE'])

        in_field = arcpy.Parameter(
            displayName="Field for Land Cover Code",
            name="in_field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
            category="Forestry, Peat, and Diffuse Urban Data Settings")
        in_field.parameterDependencies = [in_land_cover.name]
        in_field.value = "CODE_12"

        in_factors_n = arcpy.Parameter(
            displayName="Land Cover Factors for Nitrogen (N)",
            name="in_factors_n",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            category="Forestry, Peat, and Diffuse Urban Data Settings")
        in_factors_n.value = sep.join([in_fld, 'LAM_Factors.xlsx', 'Corine_N$'])

        in_factors_p = arcpy.Parameter(
            displayName="Land Cover Factors for Phosphorus (P)",
            name="in_factors_p",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            category="Forestry, Peat, and Diffuse Urban Data Settings")
        in_factors_p.value = sep.join([in_fld, 'LAM_Factors.xlsx', 'Corine_P$'])

        ex_forest = arcpy.Parameter(
            displayName="Existing output for forestry to use as a substitute to the tool",
            name="ex_forest",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input",
            category="Forestry, Peat, and Diffuse Urban Data Settings")

        ex_peat = arcpy.Parameter(
            displayName="Existing output for peatlands to use as a substitute to the tool",
            name="ex_peat",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input",
            category="Forestry, Peat, and Diffuse Urban Data Settings")

        ex_urban = arcpy.Parameter(
            displayName="Existing output for diffuse urban to use as a substitute to the tool",
            name="ex_urban",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input",
            category="Forestry, Peat, and Diffuse Urban Data Settings")

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

        ex_ipc = arcpy.Parameter(
            displayName="Existing output for IPC industries to use as a substitute to the tool",
            name="ex_ipc",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input",
            category="Industry Data Settings")

        ex_sect4 = arcpy.Parameter(
            displayName="Existing output for Section 4 industries to use as a substitute to the tool",
            name="ex_sect4",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input",
            category="Industry Data Settings")

        # Parameters specific to Septic Tanks
        in_dwts = arcpy.Parameter(
            displayName="Domestic Septic Tanks Data",
            name="in_dwts",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Septic Tanks Data Settings")
        in_dwts.value = sep.join([in_gdb, 'SepticTankSystems_LoadModel17'])

        ex_dwts = arcpy.Parameter(
            displayName="Existing output for septic tanks to use as a substitute to the tool",
            name="ex_dwts",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input",
            category="Septic Tanks Data Settings")

        # Parameters specific to Wastewater Treatment Plants
        in_agglo = arcpy.Parameter(
            displayName="Agglomerations Discharges Data",
            name="in_agglo",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Wastewater Data Settings")
        in_agglo.value = sep.join([in_gdb, 'SLAM_Agglom15_March17_IsMain'])

        ex_agglo = arcpy.Parameter(
            displayName="Existing output for WWTPs to use as a substitute to the tool",
            name="ex_agglo",
            datatype="DEFeatureClass",
            parameterType="Optional",
            direction="Input",
            category="Wastewater Data Settings")

        return [out_gdb,
                project_name, nutrient, region, selection, field,
                in_arable, in_pasture, ex_arable, ex_pasture,
                in_atm_depo, ex_atm_depo,
                in_land_cover, in_field, in_factors_n, in_factors_p, ex_forest, ex_peat, ex_urban,
                in_ipc, in_sect4, ex_ipc, ex_sect4,
                in_dwts, ex_dwts,
                in_agglo, ex_agglo]

    def execute(self, parameters, messages):
        # retrieve parameters
        out_gdb, \
            project_name, nutrient, region, selection, field, \
            in_arable, in_pasture, ex_arable, ex_pasture, \
            in_atm_depo, ex_atm_depo, \
            in_land_cover, in_field, in_factors_n, in_factors_p, ex_forest, ex_peat, ex_urban, \
            in_ipc, in_sect4, ex_ipc, ex_sect4, \
            in_dwts, ex_dwts, \
            in_agglo, ex_agglo = \
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
        if ex_arable and ex_pasture:
            messages.addMessage("> Reusing existing data for arable and pasture.")
            out_arable, out_pasture = ex_arable, ex_pasture
        else:
            out_arable, out_pasture = \
                agri_v2_geoprocessing(project_name, nutrient, location, in_arable, in_pasture, out_gdb, messages)
        if ex_atm_depo:
            messages.addMessage("> Reusing existing data for atmospheric deposition.")
            out_atm_depo = ex_atm_depo
        else:
            out_atm_depo = \
                atmos_v2_geoprocessing(project_name, nutrient, location, in_atm_depo, out_gdb, messages)
        if ex_forest:
            messages.addMessage("> Reusing existing data for forestry.")
            out_forest = ex_forest
        else:
            out_forest = \
                forestry_v1_geoprocessing(project_name, nutrient, location, in_land_cover, in_field, in_factors,
                                          out_gdb, messages)
        if ex_peat:
            messages.addMessage("> Reusing existing data for peatlands.")
            out_peat = ex_peat
        else:
            out_peat = \
                peat_v1_geoprocessing(project_name, nutrient, location, in_land_cover, in_field, in_factors,
                                      out_gdb, messages)
        if ex_urban:
            messages.addMessage("> Reusing existing data for diffuse urban.")
            out_urban = ex_urban
        else:
            out_urban = \
                urban_v1_geoprocessing(project_name, nutrient, location, in_land_cover, in_field, in_factors,
                                       out_gdb, messages)
        if ex_ipc and ex_sect4:
            messages.addMessage("> Reusing existing data for IPC and Section 4 industries.")
            out_ipc, out_sect4 = ex_ipc, ex_sect4
        else:
            out_ipc, out_sect4 = \
                industry_v2_geoprocessing(project_name, nutrient, location, in_ipc, in_sect4, out_gdb, messages)
        if ex_dwts:
            messages.addMessage("> Reusing existing data for septic tanks.")
            out_dwts = ex_dwts
        else:
            out_dwts = \
                septic_v2_geoprocessing(project_name, nutrient, location, in_dwts, out_gdb, messages)
        if ex_agglo:
            messages.addMessage("> Reusing existing data for WWTPs.")
            out_agglo = ex_agglo
        else:
            out_agglo = \
                wastewater_v2_geoprocessing(project_name, nutrient, location, in_agglo, out_gdb, messages)

        # run geoprocessing function for load apportionment
        load_apportionment_v3_geoprocessing(project_name, nutrient, location, field, out_gdb,
                                            out_arable, out_pasture, out_atm_depo, out_forest, out_peat, out_urban,
                                            out_ipc, out_sect4, out_dwts, out_agglo,
                                            messages)

        # garbage collection
        if selection:
            arcpy.Delete_management(location)


def load_apportionment_v3_geoprocessing(project_name, nutrient, location, field, out_gdb,
                                        out_arable, out_pasture, out_atm_depo, out_forest, out_peat, out_urban,
                                        out_ipc, out_sect4, out_dwts, out_agglo,
                                        messages,
                                        out_summary=None):

    # calculate the summary statistics using the sorting field provided for each source load
    messages.addMessage("> Calculating summary loads for all sources of {}.".format(nutrient))

    arcpy.Statistics_analysis(in_table=out_arable, out_table=out_arable + '_stats',
                              statistics_fields=[["GWArab2calc", "SUM"], ["Arab2calc", "SUM"]], case_field=field)
    arcpy.Statistics_analysis(in_table=out_pasture, out_table=out_pasture + '_stats',
                              statistics_fields=[["GWPast2calc", "SUM"], ["Past2calc", "SUM"]], case_field=field)

    arcpy.Statistics_analysis(in_table=out_atm_depo, out_table=out_atm_depo + '_stats',
                              statistics_fields=[["Atm2calc", "SUM"]], case_field=field)

    arcpy.Statistics_analysis(in_table=out_forest, out_table=out_forest + '_stats',
                              statistics_fields=[["For1calc", "SUM"]], case_field=field)

    arcpy.Statistics_analysis(in_table=out_peat, out_table=out_peat + '_stats',
                              statistics_fields=[["Peat1calc", "SUM"]], case_field=field)

    arcpy.Statistics_analysis(in_table=out_urban, out_table=out_urban + '_stats',
                              statistics_fields=[["Urb1calc", "SUM"]], case_field=field)

    arcpy.Statistics_analysis(in_table=out_ipc, out_table=out_ipc + '_stats',
                              statistics_fields=[["IPInd2calc", "SUM"]], case_field=field)
    arcpy.Statistics_analysis(in_table=out_sect4, out_table=out_sect4 + '_stats',
                              statistics_fields=[["S4Ind2calc", "SUM"]], case_field=field)

    arcpy.Statistics_analysis(in_table=out_dwts, out_table=out_dwts + '_stats',
                              statistics_fields=[["GWSept2calc", "SUM"], ["Sept2calc", "SUM"]], case_field=field)

    arcpy.Statistics_analysis(in_table=out_agglo, out_table=out_agglo + '_stats',
                              statistics_fields=[["CSOWast2calc", "SUM"], ["AggWast2calc", "SUM"]], case_field=field)

    # copy the input region or sub-region into the output gdb to store the results in
    messages.addMessage("> Creating output feature class to store load apportionment for {}.".format(nutrient))

    if not out_summary:
        out_summary = sep.join([out_gdb, project_name + '_{}_Loads_Summary'.format(nutrient)])

    arcpy.CopyFeatures_management(in_features=location, out_feature_class=out_summary)

    # combine the source loads into output summary
    messages.addMessage("> Gathering all sources of {} in output feature class.".format(nutrient))

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_arable + '_stats', join_field=field,
                               fields=["SUM_GWArab2calc", "SUM_Arab2calc"])
    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_pasture + '_stats', join_field=field,
                               fields=["SUM_GWPast2calc", "SUM_Past2calc"])

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_atm_depo + '_stats', join_field=field,
                               fields=["SUM_Atm2calc"])

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_forest + '_stats', join_field=field,
                               fields=["SUM_For1calc"])

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_peat + '_stats', join_field=field,
                               fields=["SUM_Peat1calc"])

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_urban + '_stats', join_field=field,
                               fields=["SUM_Urb1calc"])

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_ipc + '_stats', join_field=field,
                               fields=["SUM_IPInd2calc"])
    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_sect4 + '_stats', join_field=field,
                               fields=["SUM_S4Ind2calc"])

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_dwts + '_stats', join_field=field,
                               fields=["SUM_GWSept2calc", "SUM_Sept2calc"])

    arcpy.JoinField_management(in_data=out_summary, in_field=field,
                               join_table=out_agglo + '_stats', join_field=field,
                               fields=["SUM_CSOWast2calc", "SUM_AggWast2calc"])

    # garbage collection of the summary stats feature classes created for each individual source load
    for source in [out_arable, out_pasture, out_atm_depo, out_forest, out_peat,
                   out_urban, out_ipc, out_sect4, out_dwts, out_agglo]:
        arcpy.Delete_management(source + '_stats')
