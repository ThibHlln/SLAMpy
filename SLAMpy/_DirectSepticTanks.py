from os import path, sep
import arcpy


class SepticV2(object):
    def __init__(self):
        self.__version__ = '2'
        self.category = 'Sources'
        self.label = 'Septic Tanks [v{}]'.format(self.__version__)
        self.description = "Direct nutrient discharges from septic tank systems (based on SANICOSE model)."
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

        # Parameters specific to Septic Tanks
        in_dwts = arcpy.Parameter(
            displayName="Domestic Septic Tanks Data",
            name="in_dwts",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Septic Tanks Data Settings")
        in_dwts.value = sep.join([in_gdb, 'SepticTankSystems_LoadModel17'])

        return [out_gdb,
                project_name, nutrient, region, selection,
                in_dwts]

    def execute(self, parameters, messages):
        # retrieve parameters
        out_gdb, project_name, nutrient, region, selection, in_dwts = \
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
        septic_v2_geoprocessing(project_name, nutrient, location, in_dwts, out_gdb, messages)

        # garbage collection
        if selection:
            arcpy.Delete_management(location)


def septic_v2_geoprocessing(project_name, nutrient, location, in_dwts, out_gdb, messages,
                            out_dwts=None):
    """
    :param project_name: name of the project that will be used to identify the outputs in the geodatabase [required]
    :type project_name: str
    :param nutrient: nutrient of interest {possible values: 'N' or 'P'} [required]
    :type nutrient: str
    :param location: path of the feature class for the location of interest [required]
    :type location: str
    :param in_dwts: path of the input feature class of the domestic septic tank systems data [required]
    :type in_dwts: str
    :param out_gdb: path of the geodatabase where to store the output feature classes [required]
    :type out_gdb: str
    :param messages: object used for communication with the user interface [required]
    :type messages: instance of a class featuring a 'addMessage' method
    :param out_dwts: path of the output feature class for domestic septic tank systems load [optional]
    :type out_dwts: str
    """
    # calculate load for septic tank systems
    messages.addMessage("> Calculating {} load for Septic Tank Systems.".format(nutrient))

    if not out_dwts:
        out_dwts = sep.join([out_gdb, project_name + '_{}_SepticTanks'.format(nutrient)])

    arcpy.Intersect_analysis([location, in_dwts], out_dwts,
                             join_attributes="ALL", output_type="INPUT")

    arcpy.AddField_management(out_dwts, "GWSept2calc", "DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(out_dwts, "GWSept2calc",
                                    "!GW_{}_2c!".format(nutrient),
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(out_dwts, "Sept2calc", "DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(out_dwts, "Sept2calc",
                                    "!Total_{}_2c!".format(nutrient),
                                    expression_type="PYTHON_9.3")

    return out_dwts
