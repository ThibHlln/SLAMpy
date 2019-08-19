import arcpy
from LoadApportionment import LoadApportionmentV3
from _DiffuseAgriculture import AgriV2, AgriV1
from _DiffuseAtmDepo import AtmosV2
from _DiffuseForestry import ForestryV1
from _DiffusePeat import PeatV1
from _DiffuseUrban import DiffuseUrbanV1
from _DirectIndustry import IndustryV2
from _DirectSepticTanks import SepticV2
from _DirectWastewater import WastewaterV2, WastewaterV1
from _PostProcessing import PostProcessingV3
arcpy.env.overwriteOutput = True


class Toolbox(object):
    def __init__(self):
        self.alias = 'SLAM'
        self.label = 'SLAM'
        self.description = "Source Load Apportionment Model for Irish Catchments."
        self.__version__ = '1'

        self.tools = [LoadApportionmentV3,
                      AgriV2, AgriV1,
                      AtmosV2,
                      ForestryV1,
                      PeatV1,
                      DiffuseUrbanV1,
                      IndustryV2,
                      SepticV2,
                      WastewaterV2, WastewaterV1,
                      PostProcessingV3]
