from os import path, sep
import arcpy


class WastewaterV3(object):
    def __init__(self):
        self.__version__ = '3'
        self.category = 'Sources'
        self.label = 'Wastewater [v{}]'.format(self.__version__)
        self.description = """
        The wastewater discharges (or agglomeration) module calculates the emissions from wastewater treatment plants 
        (WWTPs) and Storm Water Overflows (SWOs, aka combined sewer overflow; CSO) using information reported in the 
        pre-processed dataset where normal operation plant outflow and storm water overflow are in one field, but over
        two separate rows.
        """
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

        # Parameters specific to Wastewater Treatment Plants
        in_agglo = arcpy.Parameter(
            displayName="Agglomerations Discharges Data",
            name="in_agglo",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Wastewater Data Settings")
        in_agglo.value = sep.join([in_gdb, 'UWW_EmissionPointData_2016'])

        in_uww_field = arcpy.Parameter(
            displayName="Field for urban wastewater emission load (include {} where it should be replaced by N or P)",
            name="in_uww_field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
            category="Wastewater Data Settings")
        in_uww_field.value = "T{}2016_Kgyr"

        return [out_gdb,
                project_name, nutrient, region, selection,
                in_agglo, in_uww_field]

    def execute(self, parameters, messages):
        # retrieve parameters
        out_gdb, project_name, nutrient, region, selection, in_agglo, in_uww_field = \
            [p.valueAsText for p in parameters]

        # determine which nutrient to work on
        nutrient = 'N' if nutrient == 'Nitrogen (N)' else 'P'

        # determine which location to work on
        if selection:  # i.e. selection requested
            messages.addMessage("> Selecting requested Location(s) within Region.")
            location = sep.join([out_gdb, project_name + '_SelectedRegion'])
            arcpy.Select_analysis(in_features=region, out_feature_class=location, where_clause=selection)
        else:
            location = region

        # run geoprocessing function
        wastewater_v3_geoprocessing(project_name, nutrient, location, in_agglo, in_uww_field,
                                    out_gdb, messages)

        # garbage collection
        if selection:
            arcpy.Delete_management(location)


def wastewater_v3_geoprocessing(project_name, nutrient, location, in_agglo, in_uww_field,
                                out_gdb, messages,
                                out_agglo=None):
    """
    :param project_name: name of the project that will be used to identify the outputs in the geodatabase [required]
    :type project_name: str
    :param nutrient: nutrient of interest {possible values: 'N' or 'P'} [required]
    :type nutrient: str
    :param location: path of the feature class for the location of interest [required]
    :type location: str
    :param in_agglo: path of the input feature class of the wastewater treatment plants data [required]
    :type in_agglo: str
    :param in_uww_field: name of the field in in_agglo to use for the WWTP outflow [required]
    :type in_uww_field: str
    :param out_gdb: path of the geodatabase where to store the output feature classes [required]
    :type out_gdb: str
    :param messages: object used for communication with the user interface [required]
    :type messages: instance of a class featuring a 'addMessage' method
    :param out_agglo: path of the output feature class for wastewater treatment plants load [optional]
    :type out_agglo: str
    """
    # calculate load for wastewater treatment plants
    messages.addMessage("> Calculating {} load for Wastewater Treatment Plants.".format(nutrient))

    if not out_agglo:
        out_agglo = sep.join([out_gdb, project_name + '_{}_Wastewater'.format(nutrient)])

    arcpy.SpatialJoin_analysis(target_features=in_agglo, join_features=location, out_feature_class=out_agglo,
                               join_operation="JOIN_ONE_TO_ONE", join_type="KEEP_COMMON",
                               match_option='CLOSEST', search_radius='2000 Meters')

    arcpy.AddField_management(in_table=out_agglo, field_name="Wast3calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_agglo, field="Wast3calc",
                                    expression="!{}!".format(in_uww_field).format(nutrient),
                                    expression_type="PYTHON_9.3")

    return out_agglo


class WastewaterV2(object):
    def __init__(self):
        self.__version__ = '2'
        self.category = 'Sources'
        self.label = 'Wastewater [v{}]'.format(self.__version__)
        self.description = """
        The wastewater discharges (or agglomeration) module calculates the emissions from wastewater treatment plants 
        (WWTPs) and Storm Water Overflows (SWOs, aka combined sewer overflow; CSO) using information reported in the 
        pre-processed dataset where normal operation plant outflow and storm water overflow are in two separate fields.
        """
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

        # Parameters specific to Wastewater Treatment Plants
        in_agglo = arcpy.Parameter(
            displayName="Agglomerations Discharges Data",
            name="in_agglo",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Wastewater Data Settings")
        in_agglo.value = sep.join([in_gdb, 'SLAM_Agglom15_March17_IsMain'])

        in_treated_field = arcpy.Parameter(
            displayName="Field for Treated WWTP Outflow (include {} where it should be replaced by N or P)",
            name="in_treated_field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
            category="Wastewater Data Settings")
        in_treated_field.value = "PointT{}"

        in_overflow_field = arcpy.Parameter(
            displayName="Field for WWTP Storm Overflow (include {} where it should be replaced by N or P)",
            name="in_overflow_field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
            category="Wastewater Data Settings")
        in_overflow_field.value = "T{}_SWO"

        return [out_gdb,
                project_name, nutrient, region, selection,
                in_agglo, in_treated_field, in_overflow_field]

    def execute(self, parameters, messages):
        # retrieve parameters
        out_gdb, project_name, nutrient, region, selection, in_agglo, in_treated_field, in_overflow_field = \
            [p.valueAsText for p in parameters]

        # determine which nutrient to work on
        nutrient = 'N' if nutrient == 'Nitrogen (N)' else 'P'

        # determine which location to work on
        if selection:  # i.e. selection requested
            messages.addMessage("> Selecting requested Location(s) within Region.")
            location = sep.join([out_gdb, project_name + '_SelectedRegion'])
            arcpy.Select_analysis(in_features=region, out_feature_class=location, where_clause=selection)
        else:
            location = region

        # run geoprocessing function
        wastewater_v2_geoprocessing(project_name, nutrient, location, in_agglo, in_treated_field, in_overflow_field,
                                    out_gdb, messages)

        # garbage collection
        if selection:
            arcpy.Delete_management(location)


def wastewater_v2_geoprocessing(project_name, nutrient, location, in_agglo, in_treated_field, in_overflow_field,
                                out_gdb, messages,
                                out_agglo=None):
    """
    :param project_name: name of the project that will be used to identify the outputs in the geodatabase [required]
    :type project_name: str
    :param nutrient: nutrient of interest {possible values: 'N' or 'P'} [required]
    :type nutrient: str
    :param location: path of the feature class for the location of interest [required]
    :type location: str
    :param in_agglo: path of the input feature class of the wastewater treatment plants data [required]
    :type in_agglo: str
    :param in_treated_field: name of the field in in_agglo to use for the WWTP treated outflow [required]
    :type in_treated_field: str
    :param in_overflow_field: name of the field in in_agglo to use for the WWTP storm overflow [required]
    :type in_overflow_field: str
    :param out_gdb: path of the geodatabase where to store the output feature classes [required]
    :type out_gdb: str
    :param messages: object used for communication with the user interface [required]
    :type messages: instance of a class featuring a 'addMessage' method
    :param out_agglo: path of the output feature class for wastewater treatment plants load [optional]
    :type out_agglo: str
    """
    # calculate load for wastewater treatment plants
    messages.addMessage("> Calculating {} load for Wastewater Treatment Plants.".format(nutrient))

    if not out_agglo:
        out_agglo = sep.join([out_gdb, project_name + '_{}_Wastewater'.format(nutrient)])

    arcpy.SpatialJoin_analysis(target_features=in_agglo, join_features=location, out_feature_class=out_agglo,
                               join_operation="JOIN_ONE_TO_ONE", join_type="KEEP_COMMON",
                               match_option='CLOSEST', search_radius='2000 Meters')

    arcpy.AddField_management(in_table=out_agglo, field_name="SWOWast2calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_agglo, field="SWOWast2calc",
                                    expression="!{}!".format(in_overflow_field).format(nutrient),
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_agglo, field_name="Wast2calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_agglo, field="Wast2calc",
                                    expression="!{}!".format(in_treated_field).format(nutrient),
                                    expression_type="PYTHON_9.3")

    return out_agglo


class WastewaterV1(object):
    def __init__(self):
        self.__version__ = '1'
        self.category = 'Sources'
        self.label = 'Wastewater [v{}]'.format(self.__version__)
        self.description = """
        The wastewater discharges (or agglomeration) module calculates the emissions from wastewater treatment plants 
        (WWTPs) and Storm Water Overflows (SWOs, aka combined sewer overflow; CSO) using information reported in the 
        annual environmental reports (AERs) where available, and otherwise make estimates using the best available 
        information on the population equivalents (PE), influent concentrations, and flow rates.
        """
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

        # Parameters specific to Wastewater Treatment Plants
        in_wwtp = arcpy.Parameter(
            displayName="Agglomerations Discharges Data",
            name="in_agglo",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Wastewater Data Settings")
        in_wwtp.value = sep.join([in_gdb, 'LAM_Agglom_Nov15'])

        in_factors_wwtp_n = arcpy.Parameter(
            displayName="WWTP Factors for Nitrogen (N)",
            name="in_factors_wwtp_n",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            category="Wastewater Data Settings")
        in_factors_wwtp_n.value = sep.join([in_fld, 'LAM_Factors.xlsx', 'UWWTP_N$'])

        in_factors_wwtp_p = arcpy.Parameter(
            displayName="WWTP Factors for Phosphorus (P)",
            name="in_factors_wwtp_p",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            category="Wastewater Data Settings")
        in_factors_wwtp_p.value = sep.join([in_fld, 'LAM_Factors.xlsx', 'UWWTP_P$'])

        return [out_gdb,
                project_name, nutrient, region, selection,
                in_wwtp, in_factors_wwtp_n, in_factors_wwtp_p]

    def execute(self, parameters, messages):
        # retrieve parameters
        out_gdb, project_name, nutrient, region, selection, in_wwtp, in_factors_wwtp_n, in_factors_wwtp_p = \
            [p.valueAsText for p in parameters]

        # determine which nutrient to work on
        nutrient = 'N' if nutrient == 'Nitrogen (N)' else 'P'

        # determine which location to work on
        if selection:  # i.e. selection requested
            messages.addMessage("> Selecting requested Location(s) within Region.")
            location = sep.join([out_gdb, project_name + '_SelectedRegion'])
            arcpy.Select_analysis(in_features=region, out_feature_class=location, where_clause=selection)
        else:
            location = region

        # determine which factors to use
        in_factors_wwtp = in_factors_wwtp_n if nutrient == 'N' else in_factors_wwtp_p

        # run geoprocessing function
        wastewater_v1_geoprocessing(project_name, nutrient, location, in_wwtp, in_factors_wwtp, out_gdb, messages)

        # garbage collection
        if selection:
            arcpy.Delete_management(location)


def wastewater_v1_geoprocessing(project_name, nutrient, location, in_wwtp, in_factors_wwtp, out_gdb, messages,
                                out_wwtp=None):
    """
    :param project_name: name of the project that will be used to identify the outputs in the geodatabase [required]
    :type project_name: str
    :param nutrient: nutrient of interest {possible values: 'N' or 'P'} [required]
    :type nutrient: str
    :param location: path of the feature class for the location of interest [required]
    :type location: str
    :param in_wwtp: path of the input feature class of the domestic septic tank systems data [required]
    :type in_wwtp: str
    :param in_factors_wwtp: path of the input table of the export factors for WWTP types [required]
    :type in_factors_wwtp: str
    :param out_gdb: path of the geodatabase where to store the output feature classes [required]
    :type out_gdb: str
    :param messages: object used for communication with the user interface [required]
    :type messages: instance of a class featuring a 'addMessage' method
    :param out_wwtp: path of the output feature class for domestic septic tank systems load [optional]
    :type out_wwtp: str
    """
    # calculate load for wastewater treatment plants
    messages.addMessage("> Calculating {} load for wastewater treatment plants.".format(nutrient))

    if not out_wwtp:
        out_wwtp = sep.join([out_gdb, project_name + '_{}_Wastewater'.format(nutrient)])

    arcpy.SpatialJoin_analysis(target_features=in_wwtp, join_features=location, out_feature_class=out_wwtp,
                               join_operation="JOIN_ONE_TO_ONE", join_type="KEEP_COMMON",
                               match_option='CLOSEST', search_radius='2000 Meters')

    arcpy.DeleteIdentical_management(in_dataset=out_wwtp, fields="RegCD", z_tolerance="0")

    arcpy.AddField_management(in_table=out_wwtp, field_name="PE_calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_wwtp, field="PE_calc",
                                    expression="factor(float(!AER14_PE!), float(!LEMA_PE!))",
                                    expression_type="PYTHON_9.3",
                                    code_block=
                                    """def factor(aer14, lema):
                                    if aer14 > 1:
                                        return aer14
                                    else:
                                        return lema
                                    """)

    raw, prelim, primary, second, tertN, tertNP, tertP, POPfactor = None, None, None, None, None, None, None, None
    found = False
    for row in arcpy.SearchCursor(in_factors_wwtp):
        if row.getValue('FactorName') == '{}_factors'.format(nutrient):
            raw = float(row.getValue('raw'))
            prelim = float(row.getValue('prelim'))
            primary = float(row.getValue('primary'))
            second = float(row.getValue('second'))
            tertN = float(row.getValue('tertN'))
            tertNP = float(row.getValue('tertNP'))
            tertP = float(row.getValue('tertP'))
            POPfactor = float(row.getValue('POPfactor'))
            found = True
            break
    if not found:
        raise Exception('Factors for {} are not available in {}'.format(nutrient, in_factors_wwtp))

    arcpy.AddField_management(in_table=out_wwtp, field_name="Treat_Fact", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_wwtp, field="Treat_Fact",
                                    expression="factor(!TreatmentL!)",
                                    expression_type="PYTHON_9.3",
                                    code_block=
                                    """def factor(treatment):
                                    if treatment == '0 - No Treatment':
                                        return {}
                                    elif treatment == '0 - Preliminary Treatment':
                                        return {}
                                    elif treatment == '1 - Primary Treatment':
                                        return {}
                                    elif treatment == '2 - Secondary Treatment':
                                        return {}
                                    elif treatment == '3N - Tertiary N Removal':
                                        return {}
                                    elif treatment == '3NP - Tertiary N&P Removal':
                                        return {}
                                    elif treatment == '3P - Tertiary P Removal':
                                        return {}
                                    elif treatment == 'Secondary':
                                        return {}
                                    else:
                                        return {}
                                    """.format(raw, prelim, primary, second, tertN, tertNP, tertP, second, primary))

    arcpy.AddField_management(in_table=out_wwtp, field_name="PEqWast1calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_wwtp, field="PEqWast1calc",
                                    expression="value(float(!{}_WWTP_AER!), float(!PE_calc!), "
                                               "float(!Treat_Fact!))".format(nutrient),
                                    expression_type="PYTHON_9.3",
                                    code_block=
                                    """def value(wwtp_aer, pe_calc, treat_fact):
                                    if wwtp_aer > 1:
                                        return 0
                                    else:
                                        return pe_calc * treat_fact *({} * 365 / 1000)
                                    """.format(POPfactor))

    arcpy.AddField_management(in_table=out_wwtp, field_name="PEqSWOWast1calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_wwtp, field="PEqSWOWast1calc",
                                    expression="value(float(!{}_SWO_AER!), float(!PE!), "
                                               "float(!LOSS_perce!))".format(nutrient),
                                    expression_type="PYTHON_9.3",
                                    code_block=
                                    """def value(swo_aer, pe, loss_perce):
                                    if swo_aer < 0.1:
                                        return ((pe * ({} * 365 / 1000)) / 1 - loss_perce) * loss_perce
                                    else:
                                        return 0
                                    """.format(POPfactor))

    arcpy.AddField_management(in_table=out_wwtp, field_name="AERWast1calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_wwtp, field="AERWast1calc",
                                    expression="!{}_WWTP_AER!".format(nutrient),
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_wwtp, field_name="AERSWOWast1calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_wwtp, field="AERSWOWast1calc",
                                    expression="!{}_SWO_AER!".format(nutrient),
                                    expression_type="PYTHON_9.3")
