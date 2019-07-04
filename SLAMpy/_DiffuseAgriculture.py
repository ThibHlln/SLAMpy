import arcpy


class CCTv2(object):
    def __init__(self):
        self.__version__ = '2'
        self.category = 'Sources'
        self.label = 'Agriculture [v{}]'.format(self.__version__)
        self.description = "Diffuse nutrient sources from pasture and arable fields (based on CCT model)."
        self.canRunInBackground = False

    def getParameterInfo(self):
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

        in_arable = arcpy.Parameter(
            displayName="CCT Data for Arable",
            name="in_arable",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        in_pasture = arcpy.Parameter(
            displayName="CCT Data for Pasture",
            name="in_pasture",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        out_arable = arcpy.Parameter(
            displayName="Output for Arable",
            name="out_arable",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        out_pasture = arcpy.Parameter(
            displayName="Output for Pasture",
            name="out_pasture",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        return [nutrient, region, selection, in_arable, in_pasture, out_arable, out_pasture]

    def execute(self, parameters, messages):
        """
        :param parameters: list of the 8 parameters in the order as follows:
           [0] nutrient of interest [type: str] {possible values: 'Nitrogen (N)' or 'Nitrogen (P)'}
           [1] path of the feature class for the region of interest [type: str] {required}
           [2] SQL query to select specific location(s) within region [type: str] {optional}
           [3] path of the input feature class of the CCT data for arable [type: str] {required}
           [4] path of the input feature class of the CCT data for pasture [type: str] {required}
           [5] path of the output feature class for arable nutrient load [type: str] {required}
           [6] path of the output feature class for pasture nutrient load [type: str] {required}
        :param messages: Messages object provided by ArcPy when running the tool

        N.B. If the optional parameters are not used, they must be set to None.
        """

        # retrieve parameters
        nutrient, region, selection, in_arable, in_pasture, out_arable, out_pasture = \
            [p.valueAsText for p in parameters]

        # determine which nutrient to work on
        nutrient = 'N' if nutrient == 'Nitrogen (N)' else 'P'

        # determine which location to work on
        arcpy.MakeFeatureLayer_management(region, 'lyrLocation')
        if selection:  # i.e. selection requested
            messages.addMessage("Selecting requested Location(s) within Region")
            arcpy.SelectLayerByAttribute_management('lyrLocation', "NEW_SELECTION", selection)

        # calculate load for arable
        messages.addMessage("Calculating {} load for arable.".format(nutrient))

        arcpy.Intersect_analysis(['lyrLocation', in_arable], out_arable,
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
        messages.addMessage("Calculating {} load for pasture.".format(nutrient))

        arcpy.Intersect_analysis(['lyrLocation', in_pasture], out_pasture,
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
