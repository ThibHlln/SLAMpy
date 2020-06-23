import arcpy
from _load_apportionment import LoadApportionmentV3, LoadApportionmentV2
from _diffuse_agriculture import AgriV2, AgriV1
from _diffuse_atm_depo import AtmosV2
from _diffuse_forestry import ForestryV1
from _diffuse_peat import PeatV1
from _diffuse_urban import DiffuseUrbanV1
from _direct_industry import IndustryV2
from _direct_septic_tanks import SepticV2
from _direct_wastewater import WastewaterV3, WastewaterV2, WastewaterV1
from _post_processing import PostProcessingV3, PostProcessingV2
arcpy.env.overwriteOutput = True


class Toolbox(object):
    def __init__(self):
        self.alias = 'SLAM'
        self.label = 'SLAM'
        self.description = "Source Load Apportionment Model for Irish Catchments."
        self.__version__ = '3.0.0.beta1'

        self.tools = [LoadApportionmentV3, LoadApportionmentV2,
                      AgriV2, AgriV1,
                      AtmosV2,
                      ForestryV1,
                      PeatV1,
                      DiffuseUrbanV1,
                      IndustryV2,
                      SepticV2,
                      WastewaterV3, WastewaterV2, WastewaterV1,
                      PostProcessingV3, PostProcessingV2]
