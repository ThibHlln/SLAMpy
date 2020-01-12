import arcpy
import pandas as pd
from os import sep

from ._load_apportionment import load_apportionment_v3_geoprocessing, load_apportionment_v3_stats_and_summary
from ._post_processing import postprocessing_v3_geoprocessing


class Messages(object):

    def addMessage(self, msg):
        print(msg)


class _Scenario(object):
    _current = list()

    def __init__(self, name, nutrient, sort_field, region, selection=None):

        self.__version__ = None
        if nutrient in ['N', 'P']:
            self.nutrient = nutrient
        else:
            raise ValueError("The nutrient for this scenario can only be 'N' for Nitrogen or 'P' for Phosphorus.")
        if name not in self._current:
            self.name = name
            self._current.append(name)
        else:
            raise RuntimeError("A scenario named '{}' already exists, "
                               "please choose another name for this scenario.".format(self.name))
        self.sort_field = sort_field
        self.region = region
        self.selection = selection

        self.headers = ['Arable', 'Pasture', 'Lake_Deposition', 'Forestry', 'Peatlands',
                        'Diffuse_Urban', 'Industry', 'Septic_Tank_Systems', 'Wastewater',
                        'TotalDiffuse', 'TotalPoint', 'Total', 'TotalHa']
        self.summary = None
        self._msg = Messages()

    def __sub__(self, other):
        if not self.sort_field == other.sort_field:
            raise RuntimeError("The two scenarios being subtracted do not share the same 'field' attribute.")
        if not (self.summary and other.summary):
            raise RuntimeError("At least one of the scenarios being subtracted was not run yet.")

        return self.summary - other.summary

    @staticmethod
    def _table_to_dataframe(feature_, index_field, value_fields):
        if not isinstance(index_field, str):
            raise TypeError("The argument 'index_field' must be a string.")
        if not isinstance(value_fields, list):
            raise TypeError("The argument 'value_fields' must be a list.")

        return pd.DataFrame([row for row in arcpy.da.SearchCursor(feature_, [index_field] + value_fields)],
                            columns=[index_field] + value_fields).set_index(index_field, drop=True)


class ScenarioV3(_Scenario):
    def __init__(self, name, nutrient, sort_field, region, selection=None):

        super(ScenarioV3, self).__init__(name, nutrient, sort_field, region, selection)
        self.__version__ = '3'

        self._outputs = {
            'arable': None,
            'pasture': None,
            'atm_depo': None,
            'forest': None,
            'peat': None,
            'urban': None,
            'ipc': None,
            'sect4': None,
            'dwts': None,
            'agglo': None
        }

    def run(self, out_gdb, in_arable=None, in_pasture=None, in_atm_depo=None,
            in_land_cover=None, in_field=None, in_factors=None,
            in_ipc=None, in_sect4=None, in_dwts=None, in_agglo=None,
            ex_arable=None, ex_pasture=None, ex_atm_depo=None, ex_forest=None, ex_peat=None, ex_urban=None,
            ex_ipc=None, ex_sect4=None, ex_dwts=None, ex_agglo=None):

        # check whether the output geodatabase provided as a string is actually one
        if not arcpy.Describe(out_gdb).dataType == "Workspace":
            raise TypeError("The output geodatabase is not a valid ArcGIS workspace.")

        # check if there is sufficient information to proceed (i.e. existing outputs [checked first], or inputs)
        self._check_ex_or_in('arable', ex_arable, [in_arable])
        self._check_ex_or_in('pasture', ex_pasture, [in_pasture])
        self._check_ex_or_in('atm_depo', ex_atm_depo, [in_atm_depo])
        self._check_ex_or_in('forest', ex_forest, [in_land_cover, in_factors])
        self._check_ex_or_in('peat', ex_peat, [in_land_cover, in_factors])
        self._check_ex_or_in('urban', ex_urban, [in_land_cover, in_factors])
        self._check_ex_or_in('ipc', ex_ipc, [in_ipc])
        self._check_ex_or_in('sect4', ex_sect4, [in_sect4])
        self._check_ex_or_in('dwts', ex_dwts, [in_dwts])
        self._check_ex_or_in('agglo', ex_agglo, [in_agglo])

        # determine which location to work on
        if self.selection:  # i.e. selection requested
            self._msg.addMessage("> Selecting requested Location(s) within Region.")
            location = sep.join([out_gdb, self.name + '_SelectedRegion'])
            arcpy.Select_analysis(in_features=self.region, out_feature_class=location, where_clause=self.selection)
        else:
            location = self.region

        # run geoprocessing functions for each source load
        (out_arable, out_pasture, out_atm_depo, out_forest, out_peat,
            out_urban, out_ipc, out_sect4, out_dwts, out_agglo) = load_apportionment_v3_geoprocessing(
                self.name, self.nutrient, location, in_field,
                in_arable, in_pasture, in_atm_depo, in_land_cover, in_factors,
                in_ipc, in_sect4, in_dwts, in_agglo,
                ex_arable, ex_pasture, ex_atm_depo, ex_forest, ex_peat, ex_urban,
                ex_ipc, ex_sect4, ex_dwts, ex_agglo,
                out_gdb,
                self._msg)

        # run geoprocessing functions for load apportionment
        out_summary = load_apportionment_v3_stats_and_summary(
            self.name, self.nutrient, location, self.sort_field, out_gdb,
            out_arable, out_pasture, out_atm_depo, out_forest, out_peat,
            out_urban, out_ipc, out_sect4, out_dwts, out_agglo,
            self._msg)

        # garbage collection
        if self.selection:
            arcpy.Delete_management(location)

        # assign the outputs to the class instance attributes
        self._outputs['arable'] = out_arable
        self._outputs['pasture'] = out_pasture
        self._outputs['atm_depo'] = out_atm_depo
        self._outputs['forest'] = out_forest
        self._outputs['peat'] = out_peat
        self._outputs['urban'] = out_urban
        self._outputs['ipc'] = out_ipc
        self._outputs['sect4'] = out_sect4
        self._outputs['dwts'] = out_dwts
        self._outputs['agglo'] = out_agglo

        # run postprocessing
        postprocessing_v3_geoprocessing(self.name, self.nutrient, out_gdb, self._msg, out_summary=out_summary)

        # collect summary as a pandas DataFrame
        self.summary = self._table_to_dataframe(out_summary, self.sort_field, self.headers)

    @staticmethod
    def _check_ex_or_in(category, existing, inputs):

        # check if existing outputs or corresponding inputs were provided for the given load category
        if not existing:  # if not reusing existing, must provide corresponding inputs
            for input_ in inputs:
                if not input_:  # no input path provided
                    raise RuntimeError("Inputs or existing output for {} must be provided.".format(category))
                else:  # input path provided
                    if not arcpy.Exists(input_):  # but the data at this location does not exists
                        raise ValueError("The input '{}' does not exist for {}.".format(input_, category))
        else:
            # check if existing is provided by reusing a Scenario instance with a compatible version, if so, proceed
            if isinstance(existing, ScenarioV3):
                existing = existing._outputs[category]
                if not arcpy.Exists(existing):
                    raise ValueError(
                        "The existing output '{}' does not exist.".format(existing))
            # check if existing is provided by reusing a Scenario instance with an incompatible version, if so, stop
            elif isinstance(existing, _Scenario):
                raise TypeError("The existing output given for {} is an instance of an incompatible version of "
                                "Scenario (i.e. v{} instead of v3).".format(category, existing.__version__))
            # check if existing is provided as a string (i.e. providing the direct path to data)
            elif isinstance(existing, str):
                # check if existing data exists, if so, proceed, if not, stop
                if not arcpy.Exists(existing):
                    raise ValueError(
                        "The existing output '{}' does not exist.".format(existing))
            # i.e. existing is neither provided as a Scenario instance nor a path as a string (only valid options), stop
            else:
                raise TypeError("Valid types for reusing existing outputs are path to data as a string or "
                                "an instance of a Scenario: neither of these was provided for {}.".format(category))
