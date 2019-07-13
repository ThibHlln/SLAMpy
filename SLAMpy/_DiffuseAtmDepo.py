from os import path, sep
import arcpy


class AtmosV2(object):
    def __init__(self):
        self.__version__ = '2'
        self.category = 'Sources'
        self.label = 'Atmospheric Deposition [v{}]'.format(self.__version__)
        self.description = "Diffuse nutrient sources from atmospheric deposition."
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

        # Parameters specific to Atmospheric Deposition
        in_atm_depo = arcpy.Parameter(
            displayName="Data for Atmospheric Deposition",
            name="in_atm_depo",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input",
            category="Atmospheric Deposition Data Settings")
        in_atm_depo.value = sep.join([in_gdb, 'AtmosDep_Lakes'])

        return [out_gdb, out_fld,
                project_name, nutrient, region, selection,
                in_atm_depo]

    def execute(self, parameters, messages):
        # retrieve parameters
        out_gdb, out_fld, project_name, nutrient, region, selection, in_atm_depo = \
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
        atmos_v2_geoprocessing(project_name, nutrient, location, in_atm_depo, out_gdb, messages)

        # garbage collection
        if selection:
            arcpy.Delete_management(location)


def atmos_v2_geoprocessing(project_name, nutrient, location, in_atm_depo, out_gdb, messages,
                           out_atm_depo=None):
    """
    :param project_name: name of the project that will be used to identify the outputs in the geodatabase [required]
    :type project_name: str
    :param nutrient: nutrient of interest {possible values: 'N' or 'P'} [required]
    :type nutrient: str
    :param location: path of the feature class for the location of interest [required]
    :type location: str
    :param in_atm_depo: path of the input feature class of the atmospheric deposition data [required]
    :type in_atm_depo: str
    :param out_gdb: path of the geodatabase where to store the output feature classes [required]
    :type out_gdb: str
    :param messages: object used for communication with the user interface [required]
    :type messages: instance of a class featuring a 'addMessage' method
    :param out_atm_depo: path of the output feature class for atmospheric deposition load [optional]
    :type out_atm_depo: str
    """
    # calculate load for atmospheric deposition
    messages.addMessage("> Calculating {} load for Atmospheric Deposition.".format(nutrient))

    if not out_atm_depo:
        out_atm_depo = sep.join([out_gdb, project_name + '_{}_AtmDepo'.format(nutrient)])

    arcpy.Intersect_analysis([location, in_atm_depo], out_atm_depo,
                             join_attributes="ALL", output_type="INPUT")

    arcpy.AddField_management(out_atm_depo, "Area_ha", "DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(out_atm_depo, "Area_ha", "!shape.area@hectares!",
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(out_atm_depo, "AtmosRate", "DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(out_atm_depo, "AtmosRate",
                                    "!{}_Dep_tot!".format(nutrient),
                                    expression_type="PYTHON_9.3")

    arcpy.AddField_management(out_atm_depo, "Atmos2calc", "DOUBLE",
                              field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED")
    arcpy.CalculateField_management(out_atm_depo, "Atmos2calc",
                                    "!AtmosRate! * !Area_ha!".format(nutrient),
                                    expression_type="PYTHON_9.3")

    return out_atm_depo
