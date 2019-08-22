from os import path, sep
import arcpy


class AgriV2(object):
    def __init__(self):
        self.__version__ = '2'
        self.category = 'Sources'
        self.label = 'Agriculture [v{}]'.format(self.__version__)
        self.description = "Diffuse nutrient sources from pasture and arable fields (based on PIP maps)."
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

        # Parameters specific to Diffuse Agriculture
        in_arable = arcpy.Parameter(
            displayName="PIP Maps Data for Arable",
            name="in_arable",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Diffuse Agriculture Data Settings")
        in_arable.value = sep.join([in_gdb, 'PathwaysCCT_IRL_Arable_LPIS'])

        in_pasture = arcpy.Parameter(
            displayName="PIP Maps Data for Pasture",
            name="in_pasture",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Diffuse Agriculture Data Settings")
        in_pasture.value = sep.join([in_gdb, 'PathwaysCCT_IRL_Pasture_LPIS'])

        return [out_gdb,
                project_name, nutrient, region, selection,
                in_arable, in_pasture]

    def execute(self, parameters, messages):
        # retrieve parameters
        out_gdb, project_name, nutrient, region, selection, in_arable, in_pasture = \
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
        agri_v2_geoprocessing(project_name, nutrient, location, in_arable, in_pasture, out_gdb, messages)

        # garbage collection
        if selection:
            arcpy.Delete_management(location)


def agri_v2_geoprocessing(project_name, nutrient, location, in_arable, in_pasture, out_gdb, messages,
                          out_arable=None, out_pasture=None):
    """
    :param project_name: name of the project that will be used to identify the outputs in the geodatabase [required]
    :type project_name: str
    :param nutrient: nutrient of interest {possible values: 'N' or 'P'} [required]
    :type nutrient: str
    :param location: path of the feature class for the location of interest [required]
    :type location: str
    :param in_arable: path of the input feature class of the CCT data for arable [required]
    :type in_arable: str
    :param in_pasture: path of the input feature class of the CCT data for pasture [required]
    :type in_pasture: str
    :param out_gdb: path of the geodatabase where to store the output feature classes [required]
    :type out_gdb: str
    :param messages: object used for communication with the user interface [required]
    :type messages: instance of a class featuring a 'addMessage' method
    :param out_arable: path of the output feature class for arable nutrient load [optional]
    :type out_arable: str
    :param out_pasture: path of the output feature class for pasture nutrient load [optional]
    :type out_pasture: str
    """
    # calculate load for arable
    messages.addMessage("> Calculating {} load for Arable.".format(nutrient))

    if not out_arable:
        out_arable = sep.join([out_gdb, project_name + '_{}_Arable'.format(nutrient)])

    arcpy.Intersect_analysis(in_features=[location, in_arable], out_feature_class=out_arable,
                             join_attributes="ALL", output_type="INPUT")

    arcpy.AddField_management(in_table=out_arable, field_name="Area_ha", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_arable, field="Area_ha",
                                    expression="!shape.area@hectares!",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_arable, field_name="GWArab2calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_arable, field="GWArab2calc",
                                    expression="!{}SwFromGw! * !Area_ha!".format(nutrient.lower()),
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_arable, field_name="Arab2calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_arable, field="Arab2calc",
                                    expression="!{}TotaltoSWreceptor! * !Area_ha!".format(nutrient.lower()),
                                    expression_type="PYTHON_9.3")

    # calculate load for pasture
    messages.addMessage("> Calculating {} load for Pasture.".format(nutrient))

    if not out_pasture:
        out_pasture = sep.join([out_gdb, project_name + '_{}_Pasture'.format(nutrient)])

    arcpy.Intersect_analysis(in_features=[location, in_pasture], out_feature_class=out_pasture,
                             join_attributes="ALL", output_type="INPUT")

    arcpy.AddField_management(in_table=out_pasture, field_name="Area_ha", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_pasture, field="Area_ha",
                                    expression="!shape.area@hectares!",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_pasture, field_name="GWPast2calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_pasture, field="GWPast2calc",
                                    expression="!{}SwFromGw! * !Area_ha!".format(nutrient.lower()),
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_pasture, field_name="Past2calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_pasture, field="Past2calc",
                                    expression="!{}TotaltoSWreceptor! * !Area_ha!".format(nutrient.lower()),
                                    expression_type="PYTHON_9.3")

    return out_arable, out_pasture


class AgriV1(object):
    def __init__(self):
        self.__version__ = '1'
        self.category = 'Sources'
        self.label = 'Agriculture [v{}]'.format(self.__version__)
        self.description = "Diffuse nutrient sources from pasture and arable fields (based on CSO Agriculture Census)."
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

        # Parameters specific to Peat
        in_agri = arcpy.Parameter(
            displayName="CSO Census Electoral Divisions Data",
            name="in_agri",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Diffuse Agriculture Data Settings")
        in_agri.value = sep.join([in_gdb, 'T2010_ED_Agri4'])

        in_factors_crop_n = arcpy.Parameter(
            displayName="Crop Factors for Nitrogen (N)",
            name="in_factors_crop_n",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            category="Diffuse Agriculture Data Settings")
        in_factors_crop_n.value = sep.join([in_fld, 'LAM_Factors.xlsx', 'Crop_N$'])

        in_factors_crop_p = arcpy.Parameter(
            displayName="Crop Factors for Phosphorus (P)",
            name="in_factors_crop_p",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            category="Diffuse Agriculture Data Settings")
        in_factors_crop_p.value = sep.join([in_fld, 'LAM_Factors.xlsx', 'Crop_P$'])

        in_factors_livestock_n = arcpy.Parameter(
            displayName="Livetock Factors for Nitrogen (N)",
            name="in_factors_livestock_n",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            category="Diffuse Agriculture Data Settings")
        in_factors_livestock_n.value = sep.join([in_fld, 'LAM_Factors.xlsx', 'Livestock_N$'])

        in_factors_livestock_p = arcpy.Parameter(
            displayName="Livestock Factors for Phosphorus (P)",
            name="in_factors_livestock_p",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            category="Diffuse Agriculture Data Settings")
        in_factors_livestock_p.value = sep.join([in_fld, 'LAM_Factors.xlsx', 'Livestock_P$'])

        return [out_gdb,
                project_name, nutrient, region, selection,
                in_agri, in_factors_crop_n, in_factors_crop_p, in_factors_livestock_n, in_factors_livestock_p]

    def execute(self, parameters, messages):
        # retrieve parameters
        out_gdb, project_name, nutrient, region, selection, in_agri, in_factors_crop_n, in_factors_crop_p, \
            in_factors_livestock_n, in_factors_livestock_p = [p.valueAsText for p in parameters]

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
        in_factors_crop = in_factors_crop_n if nutrient == 'N' else in_factors_crop_p
        in_factors_livestock = in_factors_livestock_n if nutrient == 'N' else in_factors_livestock_p

        # run geoprocessing function
        agri_v1_geoprocessing(project_name, nutrient, location, in_agri,
                              in_factors_crop, in_factors_livestock, out_gdb, messages)

        # garbage collection
        if selection:
            arcpy.Delete_management(location)


def agri_v1_geoprocessing(project_name, nutrient, location, in_agri, in_factors_crop, in_factors_livestock, out_gdb,
                          messages, out_arable=None, out_pasture=None):
    """
    :param project_name: name of the project that will be used to identify the outputs in the geodatabase [required]
    :type project_name: str
    :param nutrient: nutrient of interest {possible values: 'N' or 'P'} [required]
    :type nutrient: str
    :param location: path of the feature class for the location of interest [required]
    :type location: str
    :param in_agri: path of the input feature class of the land cover data [required]
    :type in_agri: str
    :param in_factors_crop: path of the input table of the export factors for crop types [required]
    :type in_factors_crop: str
    :param in_factors_livestock: path of the input table of the export factors for livestock types [required]
    :type in_factors_livestock: str
    :param out_gdb: path of the geodatabase where to store the output feature classes [required]
    :type out_gdb: str
    :param messages: object used for communication with the user interface [required]
    :type messages: instance of a class featuring a 'addMessage' method
    :param out_arable: path of the output feature class for arable load [optional]
    :type out_arable: str
    :param out_pasture: path of the output feature class for pasture load [optional]
    :type out_pasture: str
    """

    # calculate load for arable
    messages.addMessage("> Calculating {} load for Arable.".format(nutrient))

    arcpy.MakeFeatureLayer_management(in_features=in_agri, out_layer='lyrArable')

    arcpy.AddField_management(in_table='lyrArable', field_name="Area_ha", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table='lyrArable', field="Area_ha",
                                    expression="!shape.area@hectares!",
                                    expression_type="PYTHON_9.3")

    winter_wheat, spring_wheat, winter_barley, spring_barley, winter_oats, spring_oats, potatoes, \
        sugar_beet, other_crops, other_cereals, pasture, export_factor = \
        None, None, None, None, None, None, None, None, None, None, None, None
    found = False
    for row in arcpy.SearchCursor(in_factors_crop):
        if row.getValue('FactorName') == '{}_factors'.format(nutrient):
            winter_wheat = float(row.getValue('WinterWheat'))
            spring_wheat = float(row.getValue('SpringWheat'))
            winter_barley = float(row.getValue('WinterBarley'))
            spring_barley = float(row.getValue('SpringBarley'))
            winter_oats = float(row.getValue('WinterOats'))
            spring_oats = float(row.getValue('SpringOats'))
            potatoes = float(row.getValue('Potatoes'))
            sugar_beet = float(row.getValue('SugarBeet'))
            other_crops = float(row.getValue('OtherCrops'))
            other_cereals = float(row.getValue('CerealOther'))
            pasture = float(row.getValue('Pasture'))
            export_factor = float(row.getValue('ExportFactor'))
            found = True
            break
    if not found:
        raise Exception('Factors for {} are not available in {}'.format(nutrient, in_factors_crop))

    arcpy.AddField_management(in_table='lyrArable', field_name="Arab_calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table='lyrArable', field="Arab_calc",
                                    expression="(!total_cere! * {} + !other_crop! * {} + !potatoes! * {}) * {} / "
                                               "!Area_ha!".format(other_cereals, other_crops, potatoes, export_factor),
                                    expression_type="PYTHON_9.3")

    if not out_arable:
        out_arable = sep.join([out_gdb, project_name + '_{}_Arable'.format(nutrient)])

    arcpy.Intersect_analysis(in_features=[location, 'lyrArable'], out_feature_class=out_arable,
                             join_attributes="ALL", output_type="INPUT")

    arcpy.AddField_management(in_table=out_arable, field_name="Area_ha2", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_arable, field="Area_ha2",
                                    expression="!shape.area@hectares!", expression_type="PYTHON_9.3")
    arcpy.AddField_management(in_table=out_arable, field_name="Arab1calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_arable, field="Arab1calc",
                                    expression="!Arab_calc! * !Area_ha2!",
                                    expression_type="PYTHON_9.3")

    # calculate load for pasture
    messages.addMessage("> Calculating {} load for Pasture.".format(nutrient))

    arcpy.MakeFeatureLayer_management(in_features=in_agri, out_layer='lyrPasture')

    arcpy.AddField_management(in_table='lyrPasture', field_name="Area_ha", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table='lyrPasture', field="Area_ha",
                                    expression="!shape.area@hectares!",
                                    expression_type="PYTHON_9.3")

    dairy_cows, bulls, other_cattle, cattle_m_1, cattle_m_2, cattle_m_3, cattle_m_4, total_sheep, export_factor, \
        horses = None, None, None, None, None, None, None, None, None, None
    found = False
    for row in arcpy.SearchCursor(in_factors_livestock):
        if row.getValue('FactorName') == '{}_factors'.format(nutrient):
            dairy_cows = float(row.getValue('dairy_cows'))
            bulls = float(row.getValue('bulls'))
            other_cattle = float(row.getValue('other_cattle'))
            cattle_m_1 = float(row.getValue('cattle_m_1'))
            cattle_m_2 = float(row.getValue('cattle_m_2'))
            cattle_m_3 = float(row.getValue('cattle_m_3'))
            cattle_m_4 = float(row.getValue('cattle_m_4'))
            total_sheep = float(row.getValue('total_sheep'))
            horses = float(row.getValue('horses'))
            export_factor = float(row.getValue('ExportFactor'))
            found = True
            break
    if not found:
        raise Exception('Factors for {} are not available in {}'.format(nutrient, in_factors_livestock))

    arcpy.AddField_management(in_table='lyrPasture', field_name="Past_calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table='lyrPasture', field="Past_calc",
                                    expression="{} * (!bulls! * {} + !dairy_cows! * {} + "
                                               "!suckler_co! * {} + (!cattle_m_1! + !cattle_f_1!) * {} + "
                                               "(!cattle_m_2! + !cattle_f_2!) * {} + "
                                               "(!cattle_m_3! + !cattle_f_3! + !cattle_m_4! + "
                                               "!cattle_f_4! + !dairyheife! + !otherheife!) * {} + "
                                               "!total_shee! * {} + !horses! * {} + "
                                               "(!Hay! + !Pasture! + !Silage!)* {}) / !Area_ha!".format(export_factor,
                                                                                                        bulls,
                                                                                                        dairy_cows,
                                                                                                        other_cattle,
                                                                                                        cattle_m_1,
                                                                                                        cattle_m_2,
                                                                                                        cattle_m_3,
                                                                                                        total_sheep,
                                                                                                        horses,
                                                                                                        pasture),
                                    expression_type="PYTHON_9.3")

    if not out_pasture:
        out_pasture = sep.join([out_gdb, project_name + '_{}_Pasture'.format(nutrient)])

    arcpy.Intersect_analysis(in_features=[location, 'lyrPasture'], out_feature_class=out_pasture,
                             join_attributes="ALL", output_type="INPUT")

    arcpy.AddField_management(in_table=out_pasture, field_name="Area_ha2", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_pasture, field="Area_ha2",
                                    expression="!shape.area@hectares!",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(in_table=out_pasture, field_name="Past1calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_pasture, field="Past1calc",
                                    expression="!Past_calc! * !Area_ha2!",
                                    expression_type="PYTHON_9.3")

    return out_arable, out_pasture
