import arcpy
from LoadApportionment import SLAMv3
from _DiffuseAgriculture import CCTv2
from _DiffuseAtmDepo import AtmosV2
from _DiffuseForestry import ForestryV1
from _DiffusePeat import PeatV1
from _DiffuseUrban import UrbanV1
from _DirectIndustry import IndustryV2
from _DirectSepticTanks import DWTSv2
from _DirectWastewater import WasteWater2015
arcpy.env.overwriteOutput = True


class Toolbox(object):
    def __init__(self):
        self.alias = 'SLAM'
        self.label = 'SLAM'
        self.description = "Source Load Apportionment Model for Irish Catchments."
        self.__version__ = '1'

        self.tools = [SLAMv3, CCTv2, AtmosV2, ForestryV1, PeatV1, UrbanV1, IndustryV2, DWTSv2, WasteWater2015]
