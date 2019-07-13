from os import path, sep
import arcpy


class WasteWater2015(object):
    def __init__(self):
        self.__version__ = '2015'
        self.category = 'Sources'
        self.label = 'WasteWater [{}]'.format(self.__version__)
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
                project_name, nutrient, region, selection,
                in_agglo]

    def execute(self, parameters, messages):
        # retrieve parameters
        out_gdb, out_fld, project_name, nutrient, region, selection, in_agglo = \
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
        ww_2015_geoprocessing(project_name, nutrient, location, in_agglo, out_gdb, messages)

        # garbage collection
        if selection:
            arcpy.Delete_management(location)


def ww_2015_geoprocessing(project_name, nutrient, location, in_agglo, out_gdb, messages,
                          out_agglo=None):
    """
        :param project_name: name of the project that will be used to identify the outputs in the geodatabase [required]
        :type project_name: str
        :param nutrient: nutrient of interest {possible values: 'N' or 'P'} [required]
        :type nutrient: str
        :param location: path of the feature class for the location of interest [required]
        :type location: str
        :param in_agglo: path of the input feature class of the domestic septic tank systems data [required]
        :type in_agglo: str
        :param out_gdb: path of the geodatabase where to store the output feature classes [required]
        :type out_gdb: str
        :param messages: object used for communication with the user interface [required]
        :type messages: instance of a class featuring a 'addMessage' method
        :param out_agglo: path of the output feature class for domestic septic tank systems load [optional]
        :type out_agglo: str
        """
    # calculate load for wastewater treatment plants
    messages.addMessage("> Calculating {} load for wastewater treatment plants.".format(nutrient))

    if not out_agglo:
        out_agglo = sep.join([out_gdb, project_name + '_{}_WasteWater'.format(nutrient)])

    arcpy.SpatialJoin_analysis(location, in_agglo, out_agglo,
                               join_operation="JOIN_ONE_TO_ONE", join_type="KEEP_COMMON",
                               match_option='CLOSEST', search_radius='2000 Meters')

    arcpy.AddField_management(out_agglo, "CSO15", "DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(out_agglo, "CSO15",
                                    "!T{}_SWO!".format(nutrient),
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(out_agglo, "Agglom2015", "DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(out_agglo, "Agglom2015",
                                    "!PointT{}!".format(nutrient),
                                    expression_type="PYTHON_9.3")

    return out_agglo
