from os import path, sep
import arcpy


class PostProcessingV3(object):
    def __init__(self):
        self.__version__ = '3'
        self.category = 'Add-ons'
        self.label = 'Post-processing [v{}]'.format(self.__version__)
        self.description = "Post-processing tool to calculate various totals and sub-totals."
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

        # Parameters for Post-Processing
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

        return [out_gdb,
                project_name, nutrient]

    def execute(self, parameters, messages):
        # retrieve parameters
        out_gdb, project_name, nutrient = [p.valueAsText for p in parameters]

        # determine which nutrient to work on
        nutrient = 'N' if nutrient == 'Nitrogen (N)' else 'P'

        # run geoprocessing function
        postprocessing_v3_geoprocessing(project_name, nutrient, out_gdb, messages)


def postprocessing_v3_geoprocessing(project_name, nutrient, out_gdb, messages,
                                    out_summary=None):
    """
    :param project_name: name of the project that will be used to identify the outputs in the geodatabase [required]
    :type project_name: str
    :param nutrient: nutrient of interest {possible values: 'N' or 'P'} [required]
    :type nutrient: str
    :param out_gdb: path of the geodatabase where to store the output feature classes [required]
    :type out_gdb: str
    :param messages: object used for communication with the user interface [required]
    :type messages: instance of a class featuring a 'addMessage' method
    :param out_summary: path of the output feature class containing the calculated nutrient loads [optional]
    :type out_summary: str
    """

    if not out_summary:
        out_summary = sep.join([out_gdb, project_name + '_{}_Loads_Summary'.format(nutrient)])

    # calculate load for atmospheric deposition
    messages.addMessage("> Calculating {} loads totals and sub-totals.".format(nutrient))

    # calculate the required totals and sub-totals
    arcpy.AddField_management(in_table=out_summary, field_name="Wastewater", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Wastewater",
                                    expression="!SUM_Wast3calc! if !SUM_Wast3calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Industry", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Industry",
                                    expression="!SUM_IPInd2calc! if !SUM_IPInd2calc! is not None else 0 + "
                                               "!SUM_S4Ind2calc! if !SUM_S4Ind2calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Diffuse_Urban", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Diffuse_Urban",
                                    expression="!SUM_Urb1calc! if !SUM_Urb1calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Septic_Tank_Systems", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Septic_Tank_Systems",
                                    expression="!SUM_Sept2calc! if !SUM_Sept2calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Pasture", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Pasture",
                                    expression="!SUM_GWPast2calc! if !SUM_GWPast2calc! is not None else 0 + "
                                               "!SUM_Past2calc! if !SUM_Past2calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Arable", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Arable",
                                    expression="!SUM_GWArab2calc! if !SUM_GWArab2calc! is not None else 0 + "
                                               "!SUM_Arab2calc! if !SUM_Arab2calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Forestry", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Forestry",
                                    expression="!SUM_For1calc! if !SUM_For1calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Peatlands", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Peatlands",
                                    expression="!SUM_Peat1calc! if !SUM_Peat1calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Lake_Deposition", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Lake_Deposition",
                                    expression="!SUM_Atm2calc! if !SUM_Atm2calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="TotalDiffuse", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="TotalDiffuse",
                                    expression="!Diffuse_Urban! + !Pasture! + !Arable! + "
                                               "!Forestry! + !Peatlands! + !Lake_Deposition!",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="TotalPoint", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="TotalPoint",
                                    expression="!Wastewater! + !Industry! + !Septic_Tank_Systems!",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Total", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Total",
                                    expression="!TotalDiffuse! + !TotalPoint!",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="TotalHa", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="TotalHa",
                                    expression="value(float(!Total!), float(!AREAKM2!))",
                                    expression_type="PYTHON_9.3",
                                    code_block=
                                    """def value(total, area):
                                    if area == 0:
                                        return 0
                                    else:
                                        return total / (area * 100)
                                    """)

    arcpy.AddField_management(in_table=out_summary, field_name="PercentGW", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="PercentGW",
                                    expression="value(float(!Total!), "
                                               "float(!SUM_GWSept2calc! if !SUM_GWSept2calc! is not None else 0), "
                                               "float(!SUM_GWPast2calc! if !SUM_GWPast2calc! is not None else 0), "
                                               "float(!SUM_GWArab2calc! if !SUM_GWArab2calc! is not None else 0))",
                                    expression_type="PYTHON_9.3",
                                    code_block=
                                    """def value(total, gw_septic_tanks, gw_pasture, gw_arable):
                                    if total == 0:
                                        return 0
                                    else:
                                        return (gw_septic_tanks + gw_pasture + gw_arable) / total * 100
                                    """)

    arcpy.AddField_management(in_table=out_summary, field_name="PercentPoint", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="PercentPoint",
                                    expression="value(float(!Total!), float(!TotalPoint!))",
                                    expression_type="PYTHON_9.3",
                                    code_block=
                                    """def value(total, total_point):
                                    if total == 0:
                                        return 0
                                    else:
                                        return total_point / total * 100
                                    """)

    arcpy.AddField_management(in_table=out_summary, field_name="PercentPasture", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="PercentPasture",
                                    expression="value(float(!Total!), float(!Pasture!))",
                                    expression_type="PYTHON_9.3",
                                    code_block=
                                    """def value(total, pasture):
                                    if total == 0:
                                        return 0
                                    else:
                                        return pasture / total * 100
                                    """)


class PostProcessingV2(object):
    def __init__(self):
        self.__version__ = '2'
        self.category = 'Add-ons'
        self.label = 'Post-processing [v{}]'.format(self.__version__)
        self.description = "Post-processing tool to calculate various totals and sub-totals."
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

        # Parameters for Post-Processing
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

        return [out_gdb,
                project_name, nutrient]

    def execute(self, parameters, messages):
        # retrieve parameters
        out_gdb, project_name, nutrient = [p.valueAsText for p in parameters]

        # determine which nutrient to work on
        nutrient = 'N' if nutrient == 'Nitrogen (N)' else 'P'

        # run geoprocessing function
        postprocessing_v2_geoprocessing(project_name, nutrient, out_gdb, messages)


def postprocessing_v2_geoprocessing(project_name, nutrient, out_gdb, messages,
                                    out_summary=None):
    """
    :param project_name: name of the project that will be used to identify the outputs in the geodatabase [required]
    :type project_name: str
    :param nutrient: nutrient of interest {possible values: 'N' or 'P'} [required]
    :type nutrient: str
    :param out_gdb: path of the geodatabase where to store the output feature classes [required]
    :type out_gdb: str
    :param messages: object used for communication with the user interface [required]
    :type messages: instance of a class featuring a 'addMessage' method
    :param out_summary: path of the output feature class containing the calculated nutrient loads [optional]
    :type out_summary: str
    """

    if not out_summary:
        out_summary = sep.join([out_gdb, project_name + '_{}_Loads_Summary'.format(nutrient)])

    # calculate load for atmospheric deposition
    messages.addMessage("> Calculating {} loads totals and sub-totals.".format(nutrient))

    # calculate the required totals and sub-totals
    arcpy.AddField_management(in_table=out_summary, field_name="Wastewater", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Wastewater",
                                    expression="!SUM_SWOWast2calc! if !SUM_SWOWast2calc! is not None else 0 + "
                                               "!SUM_Wast2calc! if !SUM_Wast2calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Industry", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Industry",
                                    expression="!SUM_IPInd2calc! if !SUM_IPInd2calc! is not None else 0 + "
                                               "!SUM_S4Ind2calc! if !SUM_S4Ind2calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Diffuse_Urban", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Diffuse_Urban",
                                    expression="!SUM_Urb1calc! if !SUM_Urb1calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Septic_Tank_Systems", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Septic_Tank_Systems",
                                    expression="!SUM_Sept2calc! if !SUM_Sept2calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Pasture", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Pasture",
                                    expression="!SUM_GWPast2calc! if !SUM_GWPast2calc! is not None else 0 + "
                                               "!SUM_Past2calc! if !SUM_Past2calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Arable", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Arable",
                                    expression="!SUM_GWArab2calc! if !SUM_GWArab2calc! is not None else 0 + "
                                               "!SUM_Arab2calc! if !SUM_Arab2calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Forestry", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Forestry",
                                    expression="!SUM_For1calc! if !SUM_For1calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Peatlands", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Peatlands",
                                    expression="!SUM_Peat1calc! if !SUM_Peat1calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Lake_Deposition", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Lake_Deposition",
                                    expression="!SUM_Atm2calc! if !SUM_Atm2calc! is not None else 0",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="TotalDiffuse", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="TotalDiffuse",
                                    expression="!Diffuse_Urban! + !Pasture! + !Arable! + "
                                               "!Forestry! + !Peatlands! + !Lake_Deposition!",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="TotalPoint", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="TotalPoint",
                                    expression="!Wastewater! + !Industry! + !Septic_Tank_Systems!",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="Total", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="Total",
                                    expression="!TotalDiffuse! + !TotalPoint!",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_summary, field_name="TotalHa", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="TotalHa",
                                    expression="value(float(!Total!), float(!AREAKM2!))",
                                    expression_type="PYTHON_9.3",
                                    code_block=
                                    """def value(total, area):
                                    if area == 0:
                                        return 0
                                    else:
                                        return total / (area * 100)
                                    """)

    arcpy.AddField_management(in_table=out_summary, field_name="PercentGW", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="PercentGW",
                                    expression="value(float(!Total!), "
                                               "float(!SUM_GWSept2calc! if !SUM_GWSept2calc! is not None else 0), "
                                               "float(!SUM_GWPast2calc! if !SUM_GWPast2calc! is not None else 0), "
                                               "float(!SUM_GWArab2calc! if !SUM_GWArab2calc! is not None else 0))",
                                    expression_type="PYTHON_9.3",
                                    code_block=
                                    """def value(total, gw_septic_tanks, gw_pasture, gw_arable):
                                    if total == 0:
                                        return 0
                                    else:
                                        return (gw_septic_tanks + gw_pasture + gw_arable) / total * 100
                                    """)

    arcpy.AddField_management(in_table=out_summary, field_name="PercentPoint", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="PercentPoint",
                                    expression="value(float(!Total!), float(!TotalPoint!))",
                                    expression_type="PYTHON_9.3",
                                    code_block=
                                    """def value(total, total_point):
                                    if total == 0:
                                        return 0
                                    else:
                                        return total_point / total * 100
                                    """)

    arcpy.AddField_management(in_table=out_summary, field_name="PercentPasture", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_summary, field="PercentPasture",
                                    expression="value(float(!Total!), float(!Pasture!))",
                                    expression_type="PYTHON_9.3",
                                    code_block=
                                    """def value(total, pasture):
                                    if total == 0:
                                        return 0
                                    else:
                                        return pasture / total * 100
                                    """)
