import arcpy
from _DiffuseAgriculture import CCTv2
arcpy.env.overwriteOutput = True


class Toolbox(object):
    def __init__(self):
        self.alias = 'SLAM'
        self.label = 'SLAM'
        self.description = "Source Load Apportionment Model for Irish Catchments."
        self.__version__ = '1'

        self.tools = [CCTv2]
