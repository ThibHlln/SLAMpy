from os import path, sep
import arcpy


class DiffuseUrbanV1(object):
    def __init__(self):
        self.__version__ = '1'
        self.category = 'Sources'
        self.label = 'Diffuse Urban [v{}]'.format(self.__version__)
        self.description = "Diffuse nutrient sources from urban areas."
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

        # Parameters specific to Urban
        in_urban = arcpy.Parameter(
            displayName="Corine Land Cover Data",
            name="in_urban",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Urban Data Settings")
        in_urban.value = sep.join([in_gdb, 'clc12_IE'])

        in_field = arcpy.Parameter(
            displayName="Field for Land Cover Code",
            name="in_field",
            datatype="Field",
            parameterType="Required",
            direction="Input",
            category="Urban Data Settings")
        in_field.parameterDependencies = [in_urban.name]
        in_field.value = "CODE_12"

        in_factors_n = arcpy.Parameter(
            displayName="Land Cover Factors for Nitrogen (N)",
            name="in_factors_n",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            category="Urban Data Settings")
        in_factors_n.value = sep.join([in_fld, 'LAM_Factors.xlsx', 'Corine_N$'])

        in_factors_p = arcpy.Parameter(
            displayName="Land Cover Factors for Phosphorus (P)",
            name="in_factors_p",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            category="Urban Data Settings")
        in_factors_p.value = sep.join([in_fld, 'LAM_Factors.xlsx', 'Corine_P$'])

        return [out_gdb,
                project_name, nutrient, region, selection,
                in_urban, in_field, in_factors_n, in_factors_p]

    def execute(self, parameters, messages):
        # retrieve parameters
        out_gdb, project_name, nutrient, region, selection, in_urban, in_field, in_factors_n, in_factors_p = \
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
        in_factors = in_factors_n if nutrient == 'N' else in_factors_p

        # run geoprocessing function
        urban_v1_geoprocessing(project_name, nutrient, location, in_urban, in_field, in_factors, out_gdb, messages)

        # garbage collection
        if selection:
            arcpy.Delete_management(location)


def urban_v1_geoprocessing(project_name, nutrient, location, in_urban, in_field, in_factors, out_gdb, messages,
                           out_urban=None):
    """
    :param project_name: name of the project that will be used to identify the outputs in the geodatabase [required]
    :type project_name: str
    :param nutrient: nutrient of interest {possible values: 'N' or 'P'} [required]
    :type nutrient: str
    :param location: path of the feature class for the location of interest [required]
    :type location: str
    :param in_urban: path of the input feature class of the land cover data [required]
    :type in_urban: str
    :param in_field: name of the field in in_urban to use for the land cover type [required]
    :type in_field: str
    :param in_factors: path of the input table of the export factors for land cover types [required]
    :type in_factors: str
    :param out_gdb: path of the geodatabase where to store the output feature classes [required]
    :type out_gdb: str
    :param messages: object used for communication with the user interface [required]
    :type messages: instance of a class featuring a 'addMessage' method
    :param out_urban: path of the output feature class for diffuse urban load [optional]
    :type out_urban: str
    """
    # calculate load for urban fabric
    messages.addMessage("> Calculating {} load for Urban.".format(nutrient))

    arcpy.MakeFeatureLayer_management(in_features=in_urban, out_layer='lyrUrban')
    arcpy.SelectLayerByAttribute_management(in_layer_or_view='lyrUrban',
                                            selection_type="NEW_SELECTION",
                                            where_clause="{} LIKE '1%'".format(in_field))

    if not out_urban:
        out_urban = sep.join([out_gdb, project_name + '_{}_Urban'.format(nutrient)])

    arcpy.Intersect_analysis(in_features=[location, 'lyrUrban'], out_feature_class=out_urban,
                             join_attributes="ALL", output_type="INPUT")

    arcpy.AddField_management(in_table=out_urban, field_name="Area_ha", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_urban, field="Area_ha",
                                    expression="!shape.area@hectares!",
                                    expression_type="PYTHON_9.3")

    c111, c112, c121, c122, c133, c141, c142 = None, None, None, None, None, None, None
    found = False
    for row in arcpy.SearchCursor(in_factors):
        if row.getValue('FactorName') == '{}_factors'.format(nutrient):
            c111 = float(row.getValue('c111'))
            c112 = float(row.getValue('c112'))
            c121 = float(row.getValue('c121'))
            c122 = float(row.getValue('c122'))
            c133 = float(row.getValue('c133'))
            c141 = float(row.getValue('c141'))
            c142 = float(row.getValue('c142'))
            found = True
            break
    if not found:
        raise Exception('Factors for {} are not available in {}'.format(nutrient, in_factors))

    arcpy.AddField_management(in_table=out_urban, field_name="Urb1calc", field_type="DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(in_table=out_urban, field="Urb1calc",
                                    expression="factor(!{}!, float(!Area_ha!))".format(in_field),
                                    expression_type="PYTHON_9.3",
                                    code_block=
                                    """def factor(code, area):
                                        if code == '111':
                                            return {} * area
                                        elif code == '112':
                                            return {} * area
                                        elif code == '121':
                                            return {} * area
                                        elif code == '122':
                                            return {} * area
                                        elif code == '133':
                                            return {} * area
                                        elif code == '141':
                                            return {} * area
                                        elif code == '142':
                                            return {} * area
                                        else:
                                            return 0.0
                                    """.format(c111, c112, c121, c122, c133, c141, c142))

    return out_urban
