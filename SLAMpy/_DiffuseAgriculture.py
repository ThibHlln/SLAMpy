from os import path, sep
import arcpy


class CCTv2(object):
    def __init__(self):
        self.__version__ = '2'
        self.category = 'Sources'
        self.label = 'Agriculture [v{}]'.format(self.__version__)
        self.description = "Diffuse nutrient sources from pasture and arable fields (based on CCT model)."
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

        # Parameters specific to Diffuse Agriculture
        in_arable = arcpy.Parameter(
            displayName="CCT Data for Arable",
            name="in_arable",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Diffuse Agriculture Data Settings")
        in_arable.value = sep.join([in_gdb, 'CCT_Arable'])

        in_pasture = arcpy.Parameter(
            displayName="CCT Data for Pasture",
            name="in_pasture",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Diffuse Agriculture Data Settings")
        in_pasture.value = sep.join([in_gdb, 'CCT_Pasture'])

        return [out_gdb, out_fld,
                project_name, nutrient, region, selection,
                in_arable, in_pasture]

    def execute(self, parameters, messages):
        # retrieve parameters
        out_gdb, out_fld, project_name, nutrient, region, selection, in_arable, in_pasture = \
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

        # run geoprocessing function
        cct_v2_geoprocessing(project_name, nutrient, location, in_arable, in_pasture, out_gdb, messages)

        # garbage collection
        if selection:
            arcpy.Delete_management(location)


def cct_v2_geoprocessing(project_name, nutrient, location, in_arable, in_pasture, out_gdb, messages,
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
    messages.addMessage("> Calculating {} load for arable.".format(nutrient))

    if not out_arable:
        out_arable = sep.join([out_gdb, project_name + '_{}_Arable'.format(nutrient)])

    arcpy.Intersect_analysis([location, in_arable], out_arable,
                             join_attributes="ALL", output_type="INPUT")

    arcpy.AddField_management(out_arable, "Area_ha", "DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(out_arable, "Area_ha", "!shape.area@hectares!",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(out_arable, "GWCrop2CCT", "DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(out_arable, "GWCrop2CCT",
                                    "!{}SwFromGw! * !Area_ha!".format(nutrient.lower()),
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(out_arable, "Crop2CCT", "DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(out_arable, "Crop2CCT",
                                    "!{}TotaltoSWreceptor! * !Area_ha!".format(nutrient.lower()),
                                    expression_type="PYTHON_9.3")

    # calculate load for pasture
    messages.addMessage("> Calculating {} load for pasture.".format(nutrient))

    if not out_pasture:
        out_pasture = sep.join([out_gdb, project_name + '_{}_Pasture'.format(nutrient)])

    arcpy.Intersect_analysis([location, in_pasture], out_pasture,
                             join_attributes="ALL", output_type="INPUT")

    arcpy.AddField_management(out_pasture, "Area_ha", "DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(out_pasture, "Area_ha", "!shape.area@hectares!",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(out_pasture, "GWPast2CCT", "DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(out_pasture, "GWPast2CCT",
                                    "!{}SwFromGw! * !Area_ha!".format(nutrient.lower()),
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(out_pasture, "Past2CCT", "DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(out_pasture, "Past2CCT",
                                    "!{}TotaltoSWreceptor! * !Area_ha!".format(nutrient.lower()),
                                    expression_type="PYTHON_9.3")

    return out_arable, out_pasture
