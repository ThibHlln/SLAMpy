import arcpy
import numpy as np
import pandas as pd
from os import sep
from matplotlib.gridspec import GridSpec
import matplotlib.pyplot as plt

from ._load_apportionment import load_apportionment_v3_geoprocessing, load_apportionment_v3_stats_and_summary
from ._post_processing import postprocessing_v3_geoprocessing


_area_header = ['AREAKM2']

_source_headers = ['Arable', 'Pasture', 'Lake_Deposition', 'Forestry', 'Peatlands',
                   'Diffuse_Urban', 'Industry', 'Septic_Tank_Systems', 'Wastewater']

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
        # get the dataframe for the waterbody areas
        df_areas = self._arctable_to_dataframe(feature_, index_field, [area_field],
                                               index_name='waterbody', value_names=['area_km2'])
        # convert km2 to ha
        df_areas /= 100
        # rename column to reflect change of unit
        df_areas.columns = ['area_ha']

        return df_areas

    def _get_loads_dataframe(self, feature_, index_field, source_fields):
        # get the dataframe for the waterbody loads per source
        df_loads = self._arctable_to_dataframe(feature_, index_field, source_fields,
                                               index_name='waterbody')
        # add a second level to the column header for category (i.e. diffuse or point)
        df_loads.columns = pd.MultiIndex.from_arrays([['Diffuse'] * 6 + ['Point'] * 3, df_loads.columns])
        # collapse the multi-level columns into a second and third indices to get a multi-index dataframe
        df_loads = df_loads.stack([0, 1]).to_frame()
        # rename the multi-index indices and column
        df_loads.index.names = ['waterbody', 'category' 'source']
        df_loads.columns = ['load']
        # because the stack sorted the indices, reorder the source level of the multi-index
        df_loads = df_loads.reindex(labels=source_fields, level='source')

        return df_loads

    def plot_as_donut(self, output_name, width=None, colour_palette=None, title_on=True,
                      custom_title=None, name_mapping=None, label_display_threshold_percent=1):

        if self.loads is None:
            raise RuntimeError("The scenario '{}' cannot be plotted because it was not run yet.".format(self.name))

        # set up plot
        fig = plt.figure()
        gs = GridSpec(1, 1)
        ax = fig.add_subplot(gs[:, :])

        # colour palette
        colour_palette = colour_palette if colour_palette else _source_colour_palette

        # fancy renaming
        if name_mapping:
            fancy_names = [name_mapping[name] if name_mapping.get(name) else name
                           for name in _source_headers]
        else:
            fancy_names = [_source_fancy_names[name] for name in _source_headers]

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
            wedgeprops=dict(width=width if width else 0.35, edgecolor='w'),
            labeldistance=2.0, startangle=90,
            colors=[colour_palette[c] for c in _source_headers]
        )

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

        ax.axis('equal')  # to keep donut as a perfect circle, not an oval

        # figure title
        if title_on:
            fig.suptitle(custom_title if custom_title else
                         "Source Load Apportionment for {} ({})".format(self.nutrient, self.name),
                         x=0.5, y=1.1)

        # save plot
        fig.tight_layout(rect=[0, 0, 1, 1])
        fig.savefig(output_name + '.pdf', bbox_inches='tight',
                    facecolor='white', edgecolor='none', format='pdf')

    def to_df_pickle(self, output_name):

        summary = self.loads.join(self.areas.reindex(self.loads.index, level=0))

        summary.to_pickle('{}.{}.df'.format(output_name, self.nutrient))

    def from_df_pickle(self, file_name):

        if file_name.split('.')[-2] != self.nutrient:
            raise RuntimeError("The file you are trying to import from is not "
                               "for nutrient {}.".format(self.nutrient))

        summary = pd.read_pickle(file_name)

        self.loads = summary.drop('area_ha', axis=1)

        areas = summary.loc[:, 'area_ha'].to_frame('area_ha')
        areas = areas.reset_index(('category', 'source'), drop=True)
        areas = areas.loc[~areas.index.duplicated(keep='first')]

        self.areas = areas

    def save_as_csv(self, output_name):

        summary = self.loads.join(self.areas.reindex(self.loads.index, level=0))

        summary.to_csv('{}.csv'.format(output_name), header=['load [kg yr-1]', 'area [ha]'])


class ScenarioV3(Scenario):
    def __init__(self, name, nutrient, sort_field, region, selection=None, overwrite=True):

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
                self.name, self.nutrient, location, in_lc_field,
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

        # collect areas and loads as pandas DataFrames
        self.areas = self._get_areas_dataframe(out_summary, self.sort_field, _area_header)
        self.loads = self._get_loads_dataframe(out_summary, self.sort_field, _source_headers)

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
