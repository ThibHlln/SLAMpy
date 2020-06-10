import arcpy
import numpy as np
import pandas as pd
from os import sep
from matplotlib.gridspec import GridSpec
import matplotlib.pyplot as plt

from ._load_apportionment import load_apportionment_v3_geoprocessing, load_apportionment_v3_stats_and_summary, \
    load_apportionment_v4_geoprocessing, load_apportionment_v4_stats_and_summary
from ._post_processing import postprocessing_v3_geoprocessing, postprocessing_v4_geoprocessing


_area_header_arcmap = ['AREAKM2']

_area_header_csv = ['area [ha]']

_source_headers_arcmap = ['Arable', 'Pasture', 'Lake_Deposition', 'Forestry', 'Peatlands',
                          'Diffuse_Urban', 'Industry', 'Septic_Tank_Systems', 'Wastewater']

_source_headers_csv = ['arable [kg yr-1]', 'pasture [kg yr-1]', 'lake deposition [kg yr-1]',
                       'forestry [kg yr-1]', 'peatlands [kg yr-1]', 'diffuse urban [kg yr-1]',
                       'industry [kg yr-1]', 'septic tank systems [kg yr-1]', 'wastewater [kg yr-1]']

_source_fancy_names = {
    'Arable': 'Arable',
    'Pasture': 'Pasture',
    'Lake_Deposition': 'Lake Deposition',
    'Forestry': 'Forestry',
    'Peatlands': 'Peatlands',
    'Diffuse_Urban': 'Diffuse Urban',
    'Industry': 'Industry',
    'Septic_Tank_Systems': 'Septic Tanks',
    'Wastewater': 'Wastewater'
}

_source_colour_palette = {
    'Arable': '#127dc6',
    'Pasture': '#f05b0c',
    'Lake_Deposition': '#129c7c',
    'Forestry': '#dd1f87',
    'Peatlands': '#ffb700',
    'Diffuse_Urban': '#572c8c',
    'Industry': '#8bc722',
    'Septic_Tank_Systems': '#074097',
    'Wastewater': '#932989'
}


class Messages(object):

    def addMessage(self, msg):
        print(msg)


class Scenario(object):

    _current = list()

    def __init__(self, name, nutrient, overwrite=True):

        arcpy.env.overwriteOutput = overwrite

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
                               "please choose another name for this scenario.".format(name))

        self.areas = None
        self.loads = None

        self._msg = Messages()

    @staticmethod
    def _arctable_to_dataframe(feature_, index_field, value_fields, index_name=None, value_names=None):
        if not isinstance(index_field, str):
            raise TypeError("The argument 'index_field' must be a string.")
        if not isinstance(value_fields, list):
            raise TypeError("The argument 'value_fields' must be a list.")

        if not index_name:
            index_name = index_field
        else:
            if not isinstance(index_name, str):
                raise TypeError("The argument 'index_name' must be a string.")
        if not value_names:
            value_names = value_fields
        else:
            if not isinstance(value_names, list):
                raise TypeError("The argument 'value_names' must be a list.")

        return pd.DataFrame([row for row in arcpy.da.SearchCursor(feature_, [index_field] + value_fields)],
                            columns=[index_name] + value_names).set_index(index_name, drop=True)

    def _get_areas_dataframe(self, feature_, index_field, area_field):
        # get the dataframe for the basin areas
        df_areas = self._arctable_to_dataframe(feature_, index_field, area_field,
                                               index_name='basin', value_names=['area_km2'])
        # convert km2 to ha
        df_areas /= 100
        # rename column to remove unit
        df_areas.columns = ['area']

        return df_areas

    def _get_loads_dataframe(self, feature_, index_field, source_fields):
        # get the dataframe for the basin loads per source
        df_loads = self._arctable_to_dataframe(feature_, index_field, source_fields,
                                               index_name='basin')
        # add a second level to the column header for category (i.e. diffuse or point)
        df_loads.columns = pd.MultiIndex.from_arrays([['Diffuse'] * 6 + ['Point'] * 3, df_loads.columns])
        # collapse the multi-level columns into a second and third indices to get a multi-index dataframe
        df_loads = df_loads.stack([0, 1]).to_frame()
        # rename the multi-index indices and column
        df_loads.index.names = ['basin', 'category', 'source']
        df_loads.columns = ['load']
        # because the stack sorted the indices, reorder the source level of the multi-index
        df_loads = df_loads.reindex(labels=source_fields, level='source')

        return df_loads

    def plot_as_donut(self, file_name, output_location=None, file_format='pdf',
                      width=0.35, colour_palette=None, title_on=True,
                      custom_title=None, name_mapping=None, label_display_threshold_percent=1):

        if self.loads is None:
            raise RuntimeError("The scenario '{}' cannot be plotted because it was not run yet.".format(self.name))

        # generate file pth from from file_name and output location if given
        file_path = output_location + sep + file_name + '.' + file_format \
            if output_location else file_name + '.' + file_format

        # set up plot
        fig = plt.figure()
        gs = GridSpec(1, 1)
        ax = fig.add_subplot(gs[:, :])

        # colour palette
        colour_palette = colour_palette if colour_palette else _source_colour_palette

        # fancy renaming
        if name_mapping:
            fancy_names = [name_mapping[name] if name_mapping.get(name) else name
                           for name in _source_headers_arcmap]
        else:
            fancy_names = [_source_fancy_names[name] for name in _source_headers_arcmap]

        # plot
        bbox_props = dict(boxstyle="square,pad=0.3", fc=(1, 1, 1, 0), ec="k", lw=0.)
        kw = dict(arrowprops=dict(arrowstyle="-"),
                  bbox=bbox_props, zorder=0, va="center")

        donut_val = self.loads.groupby(
            ['source']).agg(
            {'load': 'sum'}).apply(
            lambda x: 100 * x / float(x.sum())).values.flatten()

        donut = ax.pie(
            donut_val,
            radius=1.0,
            wedgeprops=dict(width=width, edgecolor='w'),
            labeldistance=2.0, startangle=90,
            colors=[colour_palette[c] for c in _source_headers_arcmap]
        )

        not_tagged = list()
        for i, p in enumerate(donut[0]):
            if donut_val[i] > label_display_threshold_percent:
                ang = (p.theta2 - p.theta1) / 2. + p.theta1
                y = np.sin(np.deg2rad(ang))
                x = np.cos(np.deg2rad(ang))
                horizontal_alignment = {-1: "right", 1: "left"}[int(np.sign(x))]
                connection_style = "angle,angleA=0,angleB={}".format(ang)
                kw["arrowprops"].update({"connectionstyle": connection_style})
                ax.annotate('{} [{:2.1f} %]'.format(fancy_names[i], donut_val[i]),
                            xy=(x, y), xytext=(1.2 * np.sign(x), 1.25 * y),
                            horizontalalignment=horizontal_alignment, **kw)
            else:
                not_tagged.append('{} [{:2.1f} %]'.format(fancy_names[i], donut_val[i]))
        not_tagged = "Not tagged: " + ", ".join(not_tagged)
        ax.annotate(not_tagged, xy=(0.5, 0.01), xycoords='figure fraction',
                    horizontalalignment='center')

        ax.axis('equal')  # to keep donut as a perfect circle, not an oval

        # figure title
        if title_on:
            fig.suptitle(custom_title if custom_title else
                         "Source Load Apportionment for {} ({})".format(self.nutrient, self.name),
                         x=0.5, y=1.1)

        # save plot
        fig.tight_layout(rect=[0, 0, 1, 1])
        fig.savefig(file_path, bbox_inches='tight',
                    facecolor='white', edgecolor='none', format=file_format)

    @classmethod
    def read_from_csv(cls, file_path):
        # infer attributes for Scenario from standardised file name
        file_name = file_path.split(sep)[-1]
        name, nutrient, extension = file_name.split('.')

        # use pandas to read the file
        summary = pd.read_csv(file_path, header=0, index_col=0)

        # split read in dataframe into two separate dataframes for loads and areas
        loads = summary.drop('area [ha]', axis=1)
        areas = summary.loc[:, 'area [ha]'].to_frame('area [ha]')

        # rename areas column to drop unit
        areas.columns = ['area']

        # convert loads column names into how they are found in ArcMap
        loads.columns = _source_headers_arcmap
        # add a second level to the column header for category (i.e. diffuse or point)
        loads.columns = pd.MultiIndex.from_arrays([['Diffuse'] * 6 + ['Point'] * 3, loads.columns])
        # collapse the multi-level columns into a second and third indices to get a multi-index dataframe
        loads = loads.stack([0, 1]).to_frame()
        # give names to the multi-index indices
        loads.index.names = ['basin', 'category', 'source']
        # rename loads column to drop unit
        loads.columns = ['load']
        # because the stack sorted the indices, reorder the source level of the multi-index
        loads = loads.reindex(labels=_source_headers_arcmap, level='source')

        # create an instance of the class from all the information collected and processed
        instance = cls(name, nutrient)
        instance.loads = loads
        instance.areas = areas

        return instance

    def write_to_csv(self, output_location=None):
        # infer file name from scenario's attributes
        file_name = '{}.{}.csv'.format(self.name, self.nutrient)
        # generate file pth from from file_name and output location if given
        file_path = output_location + sep + file_name if output_location else file_name

        # make deep copies of the dataframes
        loads = self.loads.copy(deep=True)
        areas = self.areas.copy(deep=True)

        # remove the 'category' in multi-index
        loads.reset_index(level=1, drop=True, inplace=True)
        # unstack dataframe to get 'sources' as columns
        loads = loads.unstack(level=1)
        # remove the first level of the multi-column (i.e. 'load')
        loads = loads.droplevel(level=0, axis=1)
        # reorder the columns because unstack sorted them
        loads = loads[_source_headers_arcmap]
        # use the formatted version of the headers to include units
        loads.columns = _source_headers_csv

        # merge the two dataframes into one
        summary = loads.join(areas)
        # rename the index
        summary.index.name = 'basins \\ {} loads'.format(self.nutrient)

        # save as CSV file
        summary.to_csv(file_path)

    @classmethod
    def from_subset_in_existing_scenario(cls, existing_scenario, basin_subset_list, new_name):
        # use the list of basin subset on the existing scenario to get the two subset dataframes
        try:
            lo = existing_scenario.loads.loc[basin_subset_list]
            ar = existing_scenario.areas.loc[basin_subset_list]
        except KeyError:  # pandas.DataFrame.loc will raise a KeyError if any item in list is missing in DataFrame index
            # figure out which basin(s) is (are) missing to return a more informative error message
            missing = [m for m in basin_subset_list if m not in
                       existing_scenario.areas.index.values.tolist()]
            raise KeyError("Error when generating a subset Scenario: "
                           "the following basins are not available in "
                           "the Scenario '{}': {}".format(existing_scenario.name, missing))

        # create an instance of the class from all the information collected and processed
        instance = cls(new_name, existing_scenario.nutrient)
        instance.loads = lo
        instance.areas = ar

        return instance


class ScenarioV4(Scenario):
    def __init__(self, name, nutrient, sort_field, region, selection=None, overwrite=True):
        """Initialisation of a ScenarioV4 object.

        Scenario V4 relies on the following versions for each source:
            * diffuse agriculture V2
            * atmospheric deposition V2
            * forestry V1
            * peatlands V1
            * diffuse urban emissions V1
            * industrial discharges V2
            * septic tank systems V2
            * wastewater discharges V3

        :Parameters:

            name: `str`
                The identifier for the scenario. All output feature
                class names will use this identifier as their leading
                part.

                    *Parameter example:*
                        ``name='AvocaCatchment'``
                        ``name='EasternRiverBasinDistrict'``

            nutrient: `str`
                The nutrient for which load apportionment is sought. It
                can either 'N' for Nitrogen or 'P' for Phosphorus.

                    *Parameter example:*
                        ``nutrient='N'``
                        ``nutrient='P'``

            sort_field: `str`
                The name of the field in the *region* feature class that
                will be used to sort the output results into
                sub-regions (e.g. river sub-basins in a given
                catchment).

                    *Parameter example:*
                        ``sort_field='EU_CD'``

            region: `str`
                The location of the feature class (or shapefile) that
                delineates the area for which load apportionment is
                sought.

                    *Parameter example:*
                        ``region='SLAMpy/in/input.gdb/MyRegion'``
                        ``region='SLAMpy/in/MyRegion.shp'``

            selection: `str`, optional
                A valid SQL query to further delineate the area within
                the area delineated in *region*. If not provided, no
                further delineation is carried out.

                    *Parameter example:*
                        ``selection="EU_CD = 'IE_EA_09L010700' OR EU_CD = 'IE_EA_09L010600'"``

            overwrite: `bool`, optional
                A switch to decide whether the overwriting of existing
                files is permitted or not. Set to `True` if permitted,
                set to `False` if forbidden. If not provided, the
                default behaviour is to allow overwriting existing
                files.

                    *Parameter example:*
                        ``overwrite=False``
        """

        super(ScenarioV4, self).__init__(name, nutrient, overwrite)
        self.__version__ = '4'

        self.sort_field = sort_field
        self.region = region
        self.selection = selection

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
            in_land_cover=None, in_lc_field=None, in_factors=None,
            in_ipc=None, in_sect4=None, in_dwts=None, in_agglo=None, in_uww_field=None,
            ex_arable=None, ex_pasture=None, ex_atm_depo=None, ex_forest=None, ex_peat=None, ex_urban=None,
            ex_ipc=None, ex_sect4=None, ex_dwts=None, ex_agglo=None):
        """Run the geo-processing tools to determine the source load
        apportionment for the given nutrient in the given region.

        The following tool versions for each source will be used:
            * diffuse agriculture V2
            * atmospheric deposition V2
            * forestry V1
            * peatlands V1
            * diffuse urban emissions V1
            * industrial discharges V2
            * septic tank systems V2
            * wastewater discharges V3
        Note, for each tool, either the input for a run from scratch, or
        the existing outputs for a run from existing must be provided.

        The post-processing tool used will be:
            * post-processing V4

        :Parameters:

            out_gdb: `str`
                The location of the geodatabase where all output feature
                classes will be written.

                    *Parameter example:*
                        ``out_gdb='SLAMpy/out/output.gdb'``

            *Running from scratch*

            in_arable: `str`
                The location of the feature class (or shapefile)
                containing the N and P export loads to surface waters
                for arable (based on LPIS or Census 2010 data) –
                specially pre-processed for SLAM. Must contain fields:
                'nSwFromGw', 'pSwFromGw', 'nTotaltoSWreceptor',
                'pTotaltoSWreceptor'. Required for diffuse agriculture
                tool V2.

                    *Parameter example:*
                        ``in_arable='SLAMpy/in/input.gdb/PathwaysCCT_IRL_Arable_LPIS'``

            in_pasture: `str`
                The location of the feature class (or shapefile)
                containing the N and P export loads to surface waters
                for pasture (based on LPIS or Census 2010 data) –
                specially pre-processed for SLAM. Must contain fields:
                'nSwFromGw', 'pSwFromGw', 'nTotaltoSWreceptor',
                'pTotaltoSWreceptor'. Required for diffuse agriculture
                tool V2.

                    *Parameter example:*
                        ``in_pasture='SLAMpy/in/input.gdb/PathwaysCCT_IRL_Pasture_LPIS'``

            in_atm_depo: `str`
                The location of the feature class (or shapefile)
                containing the N and P atmospheric deposition on lakes
                – specially pre-processed for SLAM. Must contain fields:
                'N_Dep_tot', 'P_Dep_tot'. Required for atmospheric
                deposition tool V2.

                    *Parameter example:*
                        ``in_atm_depo='SLAMpy/in/input.gdb/AtmosDep_Lakes'``

            in_land_cover: `str`
                The location of the feature class (or shapefile)
                containing the Corine land cover dataset. Must contain
                fields: [for urban:] 'c111', 'c112', 'c121', 'c122',
                'c133', 'c141', 'c142', [for forestry:] 'c311', 'c312',
                'c313', 'c324', [for peatlands:] 'c411', 'c412'.
                Required for diffuse urban emissions tool V1, forestry
                tool V1, and peatlands tool V1.

                    *Parameter example:*
                        ``in_land_cover='SLAMpy/in/input.gdb/CLC18_IE'``
            
            in_lc_field: `str`
                The name of the field in the *in_land_cover* dataset
                that identifies the different Corine land cover types.
                Required for diffuse urban emissions tool V1, forestry
                tool V1, and peatlands tool V1.

                    *Parameter example:*
                        ``in_lc_field='CODE_18'``
            
            in_factors: `str`
                The location of the spreadsheet containing the export
                factors from the different land cover types (for N or
                for P). Required for diffuse urban emissions tool V1,
                forestry tool V1, and peatlands tool V1.

                    *Parameter example:*
                        ``in_factors='SLAMpy\in\LAM_Factors.xlsx\Corine_N$'``
                        ``in_factors='SLAMpy\in\LAM_Factors.xlsx\Corine_P$'``

            in_ipc: `str`
                The location of the feature class (or shapefile)
                containing the data for the IPC (Integrated Pollution
                Control) licensed industries – specially pre-processed
                for SLAM. Must contain fields: 'N_2012_LAM',
                'P_2012_LAM'. Required for industrial discharges
                tool V2.

                    *Parameter example:*
                        ``in_ipc='SLAMpy/in/input.gdb/IPPC_Loads_LAM2'``

            in_sect4: `str`
                The location of the feature class (or shapefile)
                containing the data for the Section licensed industries
                – specially pre-processed for SLAM. Must contain fields:
                'Flow__m3_d', 'Discharge_', 'TON_ELV', 'TN_ELV',
                'NO3_ELV', 'NH3_ELV', 'NH4_ELV', 'NO2_ELV', 'TP_ELV',
                'PO4_ELV'. Required for industrial discharges tool V2.

                    *Parameter example:*
                        ``in_sect4='SLAMpy/in/input.gdb/Section4Discharges_D07_IsMain'``
            
            in_dwts: `str`
                The location of the feature class (or shapefile)
                containing the data generated by the SANICOSE model.
                Must contain fields: 'GW_N_2c', 'GW_P_2c', 'Total_N_2c',
                'Total_P_2c'. Required for septic tank systems tool V2.

                    *Parameter example:*
                        ``in_dwts='SLAMpy/in/input.gdb/SepticTankSystems_LoadModel17'``
            
            in_agglo: `str`
                The location of the feature class (or shapefile)
                containing the WWTP information, including the location
                of the treatment plant discharges as points and the
                total N and P loads, where normal operation outflow
                and storm water overflow are provided in separate
                entries in the attribute table – specially pre-processed
                for SLAM. Must contain field *in_uww_field*. Required
                for wastewater discharges tool V3.

                    *Parameter example:*
                        ``in_agglo='SLAMpy/in/input.gdb/UWW_EmissionPointData_2016'``

            in_uww_field: `str`
                The name of the field in the *in_agglo* dataset that
                provides the total annual load from wastewater
                in kg/year. The string must feature {} where the
                character N or P needs to be inserted (to distinguish
                the N load from the P load contained in the same
                dataset). Required for wastewater discharges tool V3.

                    *Parameter example:*
                        ``in_uww_field='T{}2016_Kgyr'``

            *Running from existing*

            ex_arable: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for arable using
                the diffuse agriculture tool V2 for the given *nutrient*
                and the given *region*. Must contain fields:
                'GWArab2calc', 'Arab2calc'. Must be provided alongside
                *ex_pasture* otherwise run from existing is impossible.

            ex_pasture: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for arable using
                the diffuse agriculture tool V2 for the given *nutrient*
                and the given *region*. Must contain fields:
                'GWPast2calc', 'Past2calc'. Must be provided alongside
                *ex_arable* otherwise run from existing is impossible.
            
            ex_atm_depo: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for atmospheric
                deposition using the atmospheric deposition tool V2
                for the given *nutrient* and the given *region*. Must
                contain fields: 'Atm2calc'.
            
            ex_forest: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for forestry tool
                V1 for the given *nutrient* and the given *region*.
                Must contain fields: 'For1calc'.
            
            ex_peat: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for peatlands using
                the peatlands tool V1 for the given *nutrient* and the
                given *region*. Must contain fields: 'Peat1calc'.
            
            ex_urban: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for diffuse urban
                emissiong using the diffuse urban emissions tool V1 for
                the given *nutrient* and the given *region*. Must
                contain fields: 'Urb1calc'.
            
            ex_ipc: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for IPC licensed
                industries load using the industrial discharges tool V2.
                Must contain fields: 'IPInd2calc'. Must be provided
                alongside *ex_sect4* otherwise run from existing is
                impossible.
            
            ex_sect4: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for section 4
                licensed industries load using the industrial discharges
                tool V2.  Must contain fields: 'S4Ind2calc'. Must be
                provided alongside *ex_ipc* otherwise run from
                existing is impossible.
            
            ex_dwts: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for domestic septic
                tank systems load using the septic tank systems tool V2.
                Must contain fields: 'GWSept2calc', 'Sept2calc'.
            
            ex_agglo: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for the urban
                wastewater treatment plants load using the wastewater
                discharges tool V3. Must contain fields: 'Wast3calc'.
        """

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

        # check whether required fields are provided
        if not in_lc_field:
            raise ValueError("The field 'in_lc_field' required for the forest, peat, and urban tools is not provided.")
        if not in_uww_field:
            raise ValueError("The field 'in_uww_field' required for the agglomeration wastewater tool.")

        # determine which location to work on
        if self.selection:  # i.e. selection requested
            self._msg.addMessage("> Selecting requested Location(s) within Region.")
            location = sep.join([out_gdb, self.name + '_SelectedRegion'])
            arcpy.Select_analysis(in_features=self.region, out_feature_class=location, where_clause=self.selection)
        else:
            location = self.region

        # run geoprocessing functions for each source load
        (out_arable, out_pasture, out_atm_depo, out_forest, out_peat,
            out_urban, out_ipc, out_sect4, out_dwts, out_agglo) = load_apportionment_v4_geoprocessing(
                self.name, self.nutrient, location, in_lc_field,
                in_arable, in_pasture, in_atm_depo, in_land_cover, in_factors,
                in_ipc, in_sect4, in_dwts, in_agglo, in_uww_field,
                ex_arable, ex_pasture, ex_atm_depo, ex_forest, ex_peat, ex_urban,
                ex_ipc, ex_sect4, ex_dwts, ex_agglo,
                out_gdb,
                self._msg)

        # run geoprocessing functions for load apportionment
        out_summary = load_apportionment_v4_stats_and_summary(
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
        postprocessing_v4_geoprocessing(self.name, self.nutrient, out_gdb, self._msg, out_summary=out_summary)

        # collect areas and loads as pandas DataFrames
        self.areas = self._get_areas_dataframe(out_summary, self.sort_field, _area_header_arcmap)
        self.loads = self._get_loads_dataframe(out_summary, self.sort_field, _source_headers_arcmap)

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
            elif isinstance(existing, Scenario):
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


class ScenarioV3(Scenario):
    def __init__(self, name, nutrient, sort_field, region, selection=None, overwrite=True):
        """Initialisation of a ScenarioV3 object.

        Scenario V3 relies on the following versions for each source:
            * diffuse agriculture V2
            * atmospheric deposition V2
            * forestry V1
            * peatlands V1
            * diffuse urban emissions V1
            * industrial discharges V2
            * septic tank systems V2
            * wastewater discharges V2

        :Parameters:

            name: `str`
                The identifier for the scenario. All output feature
                class names will use this identifier as their leading
                part.

                    *Parameter example:*
                        ``name='AvocaCatchment'``
                        ``name='EasternRiverBasinDistrict'``

            nutrient: `str`
                The nutrient for which load apportionment is sought. It
                can either 'N' for Nitrogen or 'P' for Phosphorus.

                    *Parameter example:*
                        ``nutrient='N'``
                        ``nutrient='P'``

            sort_field: `str`
                The name of the field in the *region* feature class that
                will be used to sort the output results into
                sub-regions (e.g. river sub-basins in a given
                catchment).

                    *Parameter example:*
                        ``sort_field='EU_CD'``

            region: `str`
                The location of the feature class (or shapefile) that
                delineates the area for which load apportionment is
                sought.

                    *Parameter example:*
                        ``region='SLAMpy/in/input.gdb/MyRegion'``
                        ``region='SLAMpy/in/MyRegion.shp'``

            selection: `str`, optional
                A valid SQL query to further delineate the area within
                the area delineated in *region*. If not provided, no
                further delineation is carried out.

                    *Parameter example:*
                        ``selection="EU_CD = 'IE_EA_09L010700' OR EU_CD = 'IE_EA_09L010600'"``

            overwrite: `bool`, optional
                A switch to decide whether the overwriting of existing
                files is permitted or not. Set to `True` if permitted,
                set to `False` if forbidden. If not provided, the
                default behaviour is to allow overwriting existing
                files.

                    *Parameter example:*
                        ``overwrite=False``
        """
        super(ScenarioV3, self).__init__(name, nutrient, overwrite)
        self.__version__ = '3'

        self.sort_field = sort_field
        self.region = region
        self.selection = selection

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
            in_land_cover=None, in_lc_field=None, in_factors=None,
            in_ipc=None, in_sect4=None, in_dwts=None, in_agglo=None, in_treated_field=None, in_overflow_field=None,
            ex_arable=None, ex_pasture=None, ex_atm_depo=None, ex_forest=None, ex_peat=None, ex_urban=None,
            ex_ipc=None, ex_sect4=None, ex_dwts=None, ex_agglo=None):
        """Run the geo-processing tools to determine the source load
        apportionment for the given nutrient in the given region.

        The following tool versions for each source will be used:
            * diffuse agriculture V2
            * atmospheric deposition V2
            * forestry V1
            * peatlands V1
            * diffuse urban emissions V1
            * industrial discharges V2
            * septic tank systems V2
            * wastewater discharges V2
        Note, for each tool, either the input for a run from scratch, or
        the existing outputs for a run from existing must be provided.

        The post-processing tool used will be:
            * post-processing V4

        :Parameters:

            out_gdb: `str`
                The location of the geodatabase where all output feature
                classes will be written.

                    *Parameter example:*
                        ``out_gdb='SLAMpy/out/output.gdb'``

            *Running from scratch*

            in_arable: `str`
                The location of the feature class (or shapefile)
                containing the N and P export loads to surface waters
                for arable (based on LPIS or Census 2010 data) –
                specially pre-processed for SLAM. Must contain fields:
                'nSwFromGw', 'pSwFromGw', 'nTotaltoSWreceptor',
                'pTotaltoSWreceptor'. Required for diffuse agriculture
                tool V2.

                    *Parameter example:*
                        ``in_arable='SLAMpy/in/input.gdb/PathwaysCCT_IRL_Arable_LPIS'``

            in_pasture: `str`
                The location of the feature class (or shapefile)
                containing the N and P export loads to surface waters
                for pasture (based on LPIS or Census 2010 data) –
                specially pre-processed for SLAM. Must contain fields:
                'nSwFromGw', 'pSwFromGw', 'nTotaltoSWreceptor',
                'pTotaltoSWreceptor'. Required for diffuse agriculture
                tool V2.

                    *Parameter example:*
                        ``in_pasture='SLAMpy/in/input.gdb/PathwaysCCT_IRL_Pasture_LPIS'``

            in_atm_depo: `str`
                The location of the feature class (or shapefile)
                containing the N and P atmospheric deposition on lakes
                – specially pre-processed for SLAM. Must contain fields:
                'N_Dep_tot', 'P_Dep_tot'. Required for atmospheric
                deposition tool V2.

                    *Parameter example:*
                        ``in_atm_depo='SLAMpy/in/input.gdb/AtmosDep_Lakes'``

            in_land_cover: `str`
                The location of the feature class (or shapefile)
                containing the Corine land cover dataset. Must contain
                fields: [for urban:] 'c111', 'c112', 'c121', 'c122',
                'c133', 'c141', 'c142', [for forestry:] 'c311', 'c312',
                'c313', 'c324', [for peatlands:] 'c411', 'c412'.
                Required for diffuse urban emissions tool V1, forestry
                tool V1, and peatlands tool V1.

                    *Parameter example:*
                        ``in_land_cover='SLAMpy/in/input.gdb/CLC18_IE'``

            in_lc_field: `str`
                The name of the field in the *in_land_cover* dataset
                that identifies the different Corine land cover types.
                Required for diffuse urban emissions tool V1, forestry
                tool V1, and peatlands tool V1.

                    *Parameter example:*
                        ``in_lc_field='CODE_18'``

            in_factors: `str`
                The location of the spreadsheet containing the export
                factors from the different land cover types (for N or
                for P). Required for diffuse urban emissions tool V1,
                forestry tool V1, and peatlands tool V1.

                    *Parameter example:*
                        ``in_factors='SLAMpy\in\LAM_Factors.xlsx\Corine_N$'``
                        ``in_factors='SLAMpy\in\LAM_Factors.xlsx\Corine_P$'``

            in_ipc: `str`
                The location of the feature class (or shapefile)
                containing the data for the IPC (Integrated Pollution
                Control) licensed industries – specially pre-processed
                for SLAM. Must contain fields: 'N_2012_LAM',
                'P_2012_LAM'. Required for industrial discharges
                tool V2.

                    *Parameter example:*
                        ``in_ipc='SLAMpy/in/input.gdb/IPPC_Loads_LAM2'``

            in_sect4: `str`
                The location of the feature class (or shapefile)
                containing the data for the Section licensed industries
                – specially pre-processed for SLAM. Must contain fields:
                'Flow__m3_d', 'Discharge_', 'TON_ELV', 'TN_ELV',
                'NO3_ELV', 'NH3_ELV', 'NH4_ELV', 'NO2_ELV', 'TP_ELV',
                'PO4_ELV'. Required for industrial discharges tool V2.

                    *Parameter example:*
                        ``in_sect4='SLAMpy/in/input.gdb/Section4Discharges_D07_IsMain'``

            in_dwts: `str`
                The location of the feature class (or shapefile)
                containing the data generated by the SANICOSE model.
                Must contain fields: 'GW_N_2c', 'GW_P_2c', 'Total_N_2c',
                'Total_P_2c'. Required for septic tank systems tool V2.

                    *Parameter example:*
                        ``in_dwts='SLAMpy/in/input.gdb/SepticTankSystems_LoadModel17'``

            in_agglo: `str`
                The location of the feature class (or shapefile)
                containing the WWTP information, including the location
                of the treatment plant discharges as points, the
                treatment levels, the population equivalent, and
                possibly AER information – specially pre-processed
                for SLAM. Must contain fields *in_treated_field* and
                *in_overflow_field*. Required for wastewater discharges
                tool V2.

                    *Parameter example:*
                        ``in_agglo='SLAMpy/in/input.gdb/SLAM_Agglom15_March17_IsMain'``

            in_treated_field: `str`
                The name of the field in the *in_agglo* dataset that
                provides the total annual load from normal operation
                treated outflow. The string must feature {} where the
                character N or P needs to be inserted (to distinguish
                the N load from the P load contained in the same
                dataset). Required for wastewater discharges tool V2.

                    *Parameter example:*
                        ``in_treated_field='PointT{}'``

            in_overflow_field: `str`
                The name of the field in the *in_agglo* dataset that
                provides the total annual load from storm water
                overflow. The string must feature {} where the character
                N or P needs to be inserted (to distinguish the N load
                from the P load contained in the same dataset). Required
                for wastewater discharges tool V2.

                    *Parameter example:*
                        ``in_overflow_field='T{}_SWO'``

            *Running from existing*

            ex_arable: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for arable using
                the diffuse agriculture tool V2 for the given *nutrient*
                and the given *region*. Must contain fields:
                'GWArab2calc', 'Arab2calc'. Must be provided alongside
                *ex_pasture* otherwise run from existing is impossible.

            ex_pasture: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for arable using
                the diffuse agriculture tool V2 for the given *nutrient*
                and the given *region*. Must contain fields:
                'GWPast2calc', 'Past2calc'. Must be provided alongside
                *ex_arable* otherwise run from existing is impossible.

            ex_atm_depo: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for atmospheric
                deposition using the atmospheric deposition tool V2
                for the given *nutrient* and the given *region*. Must
                contain fields: 'Atm2calc'.

            ex_forest: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for forestry tool
                V1 for the given *nutrient* and the given *region*.
                Must contain fields: 'For1calc'.

            ex_peat: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for peatlands using
                the peatlands tool V1 for the given *nutrient* and the
                given *region*. Must contain fields: 'Peat1calc'.

            ex_urban: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for diffuse urban
                emissiong using the diffuse urban emissions tool V1 for
                the given *nutrient* and the given *region*. Must
                contain fields: 'Urb1calc'.

            ex_ipc: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for IPC licensed
                industries load using the industrial discharges tool V2.
                Must contain fields: 'IPInd2calc'. Must be provided
                alongside *ex_sect4* otherwise run from existing is
                impossible.

            ex_sect4: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for section 4
                licensed industries load using the industrial discharges
                tool V2.  Must contain fields: 'S4Ind2calc'. Must be
                provided alongside *ex_ipc* otherwise run from
                existing is impossible.

            ex_dwts: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for domestic septic
                tank systems load using the septic tank systems tool V2.
                Must contain fields: 'GWSept2calc', 'Sept2calc'.

            ex_agglo: `str`
                The location of the feature class (or shapefile)
                corresponding to the existing output for the urban
                wastewater treatment plants load using the wastewater
                discharges tool V2. Must contain fields: 'SWOWast2calc',
                'Wast2calc'.
        """
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

        # check whether required fields are provided
        if not in_lc_field:
            raise ValueError("The field 'in_lc_field' required for the forest, peat, and urban tools is not provided.")
        if not in_treated_field:
            raise ValueError("The field 'in_treated_field' required for the agglomeration wastewater tool.")
        if not in_overflow_field:
            raise ValueError("The field 'in_overflow_field' required for the agglomeration wastewater tool.")

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
                self.name, self.nutrient, location, in_lc_field,
                in_arable, in_pasture, in_atm_depo, in_land_cover, in_factors,
                in_ipc, in_sect4, in_dwts, in_agglo, in_treated_field, in_overflow_field,
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

        # collect areas and loads as pandas DataFrames
        self.areas = self._get_areas_dataframe(out_summary, self.sort_field, _area_header_arcmap)
        self.loads = self._get_loads_dataframe(out_summary, self.sort_field, _source_headers_arcmap)

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
            elif isinstance(existing, Scenario):
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
