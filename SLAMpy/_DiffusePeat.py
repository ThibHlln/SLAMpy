from os import path, sep
import arcpy


class PeatV1(object):
    def __init__(self):
        self.__version__ = '1'
        self.category = 'Sources'
        self.label = 'Peat [v{}]'.format(self.__version__)
        self.description = "Diffuse nutrient sources from peatlands."
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

        # Parameters specific to Peat
        in_peat = arcpy.Parameter(
            displayName="Corine Land Cover Data",
            name="in_peat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Peat Data Settings")
        in_peat.value = sep.join([in_gdb, 'clc12_IE'])

        in_factors_n = arcpy.Parameter(
            displayName="Land Cover Factors for Nitrogen (N)",
            name="in_factors_n",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            category="Peat Data Settings")
        in_factors_n.value = sep.join([in_fld, 'LAM_Factors.xlsx', 'Corine_N$'])

        in_factors_p = arcpy.Parameter(
            displayName="Land Cover Factors for Phosphorus (P)",
            name="in_factors_p",
            datatype="DETable",
            parameterType="Required",
            direction="Input",
            category="Peat Data Settings")
        in_factors_p.value = sep.join([in_fld, 'LAM_Factors.xlsx', 'Corine_P$'])

        return [out_gdb, out_fld,
                project_name, nutrient, region, selection,
                in_peat, in_factors_n, in_factors_p]

    def execute(self, parameters, messages):
        # retrieve parameters
        out_gdb, out_fld, project_name, nutrient, region, selection, in_peat, in_factors_n, in_factors_p = \
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

        # run geoprocessing function
        peat_v1_geoprocessing(project_name, nutrient, location, in_peat, in_factors, out_gdb, messages)

        # garbage collection
        if selection:
            arcpy.Delete_management(location)


def peat_v1_geoprocessing(project_name, nutrient, location, in_peat, in_factors, out_gdb, messages,
                          out_peat=None):
    """
    :param project_name: name of the project that will be used to identify the outputs in the geodatabase [required]
    :type project_name: str
    :param nutrient: nutrient of interest {possible values: 'N' or 'P'} [required]
    :type nutrient: str
    :param location: path of the feature class for the location of interest [required]
    :type location: str
    :param in_peat: path of the input feature class of the land cover data [required]
    :type in_peat: str
    :param in_factors: path of the input table of the export factors for land cover types [required]
    :type in_factors: str
    :param out_gdb: path of the geodatabase where to store the output feature classes [required]
    :type out_gdb: str
    :param messages: object used for communication with the user interface [required]
    :type messages: instance of a class featuring a 'addMessage' method
    :param out_peat: path of the output feature class for peatlands load [optional]
    :type out_peat: str
    """

    # calculate load for peat
    messages.addMessage("> Calculating {} load for Peat.".format(nutrient))

    arcpy.MakeFeatureLayer_management(in_peat, 'lyrPeat')
    arcpy.SelectLayerByAttribute_management('lyrPeat', "NEW_SELECTION", "CODE_12 LIKE '41%'")

    if not out_peat:
        out_peat = sep.join([out_gdb, project_name + '_{}_Peat'.format(nutrient)])

    arcpy.Intersect_analysis([location, 'lyrPeat'], out_peat,
                             join_attributes="ALL", output_type="INPUT")

    arcpy.AddField_management(out_peat, "Area_ha", "DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(out_peat, "Area_ha", "!shape.area@hectares!",
                                    expression_type="PYTHON_9.3")

    c411, c412 = None, None
    found = False
    for row in arcpy.SearchCursor(in_factors):
        if row.getValue('FactorName') == '{}_factors'.format(nutrient):
            c411 = float(row.getValue('c411'))
            c412 = float(row.getValue('c412'))
            found = True
            break
    if not found:
        raise Exception('Factors for {} are not available in {}'.format(nutrient, in_factors))

    arcpy.AddField_management(out_peat, "Peat1calc", "DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(out_peat, "Peat1calc",
                                    expression="factor(!CODE_12!, float(!Area_ha!))",
                                    expression_type="PYTHON_9.3",
                                    code_block=
                                    """def factor(code, area):
                                        if code == '411':
                                            return {} * area
                                        elif code == '412':
                                            return {} * area
                                        else:
                                            return 0.0
                                    """.format(c411, c412))

    return out_peat
