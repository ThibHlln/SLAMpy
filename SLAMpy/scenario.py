import arcpy
import numpy as np
import pandas as pd
from os import sep
from collections import MutableSequence
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


class _Scenario(object):

    _current = list()

    def __init__(self, name, nutrient, sort_field, region, selection=None, overwrite=True):

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
                               "please choose another name for this scenario.".format(self.name))
        self.sort_field = sort_field
        self.region = region
        self.selection = selection

        self.areas = None
        self.loads = None

        self._msg = Messages()

    def __sub__(self, other):
        if not self.sort_field == other.sort_field:
            raise RuntimeError("The two scenarios being subtracted do not share the same 'field' attribute.")
        if (self.loads is None) or (other.loads is None):
            raise RuntimeError("At least one of the scenarios being subtracted was not run yet.")

        return self.loads - other.loads

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

    def save_as_csv(self, output_name):

        summary = self.loads.join(self.areas.reindex(self.loads.index, level=0))

        summary.to_csv('{}.csv'.format(output_name), header=['load [kg yr-1]', 'area [ha]'])


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


class ScenarioList(MutableSequence):

    def __init__(self, *args, **kwargs):

        self.scenarios = list()
        self.nutrient = None
        self.extend(list(*args, **kwargs))

    def __getitem__(self, index): return self.scenarios[index]

    def __setitem__(self, index, value):

        self._check_scenario(value)
        self.scenarios[index] = value

    def __delitem__(self, index): del self.scenarios[index]

    def __len__(self): return len(self.scenarios)

    def insert(self, index, value):

        self._check_scenario(value)
        self.scenarios.insert(index, value)

    def _check_scenario(self, value):
        # check that the object given is an instance of Scenario or a subclass of Scenario
        if not isinstance(value, _Scenario):
            raise TypeError("A {} can only contain instances of "
                            "{}.".format(self.__class__.__name__,
                                         _Scenario.__name__))

        # check that the name of the scenario doesn't already exist
        if value.name in [s.name for s in self.scenarios]:
            raise RuntimeError("A scenario named '{}' already exists in the {}, "
                               "please choose another name for this scenario.".format(value.name,
                                                                                      self.__class__.__name__))

        # check that the scenario was already run
        if value.loads is None:
            raise RuntimeError("The scenario '{}' cannot be added to the {} because it "
                               "was not run yet.".format(value.name, self.__class__.__name__))

        if len(self.scenarios) > 0:  # if there is at least one Scenario already in the list
            # check that nutrient is the same
            if not self.scenarios[0].nutrient == value.nutrient:
                raise ValueError("The scenario '{}' cannot be added to the {} because its "
                                 "nutrient does not match the nutrient of the existing scenarios.")
            # check that the multi-index of the 'loads' dataframes are equal
            if not self.scenarios[0].loads.sort_index().index.equals(value.loads.sort_index().index):
                raise ValueError("The scenario '{}' cannot be added to the {} because its "
                                 "index does not match the indices of the existing scenarios: "
                                 "it is likely that they contain different waterbodies.")
        else:
            self.nutrient = value.nutrient

    def plot_as_stacked_bars(self, output_name, colour_palette=None, name_mapping=None,
                             title_on=True, custom_title=None, scenario_label_rotation=90,
                             width=0.05):

        # fancy renaming
        if name_mapping:
            fancy_names = [name_mapping[name] if name_mapping.get(name) else name
                           for name in _source_headers]
        else:
            fancy_names = [_source_fancy_names[name] for name in _source_headers]

        # concatenate the scenarios into one dataframe
        all_loads = [scenario.loads for scenario in self.scenarios]
        all_names = [scenario.name for scenario in self.scenarios]

        df_loads = pd.concat(all_loads, axis=1)
        df_loads.columns = all_names

        # reindex the created dataframe to make sure that the order of the sources is standard
        # (because if the waterbodies are not ordered in the same way, it could have changed the
        # order of the sources during the concatenation)
        df_loads = df_loads.reindex(labels=_source_headers, level='source')

        # group by the sources in each scenario
        # (i.e. collapse values to selection level, i.e. lose the information per waterbody)
        df_loads = df_loads.groupby(
            ['source']).agg(
            {name: 'sum' for name in all_names})

        # make sure than the column ordering has not been changed
        # because the agg method uses a dict which is not ordered
        df_loads = df_loads[all_names]

        # convert dataframe to array
        stack_vals = df_loads.values

        # determine sizing parameters
        length = stack_vals.shape[1]

        standard_aspect_ratio = 1.0
        max_length = (1.0 / standard_aspect_ratio - 2 * width) / (2 * width) + 1

        if length <= max_length:
            aspect_ratio = 1.0
        else:
            aspect_ratio = 1 / (2 * width * length)

        # determine the intrinsic range to use for x-axis depending on oddness/evenness
        odd = True if length == 0 else False
        range_ = np.arange(-length + 1, length - 1, 2, dtype=float) if odd \
            else np.arange(-length + 1, length, 2, dtype=float)

        # set up plot
        w, h = plt.figaspect(aspect_ratio)
        fig = plt.figure(figsize=(w, h))
        gs = GridSpec(1, 1)
        ax = fig.add_subplot(gs[:, :])

        # colour palette
        colour_palette = colour_palette if colour_palette else _source_colour_palette

        # plot
        bars = list()
        bottom = np.zeros(stack_vals.shape[1])
        for i, source in enumerate(_source_headers):
            bars.append(
                ax.bar(
                    x=range_ * width + (1.0 / aspect_ratio / 2),
                    height=stack_vals[i, :],
                    width=width,
                    bottom=bottom,
                    color=colour_palette[source],
                    tick_label=all_names
                )
            )
            bottom += stack_vals[i, :]

        ax.set_xlim(0, 1.0 / aspect_ratio)

        # axes
        ax.set_ylabel("Total {} ".format(self.nutrient) + r"$[\mathregular{kg.yr^{-1}}]$")
        ax.ticklabel_format(axis='y', style='sci', scilimits=(0, 0), useMathText=True)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=scenario_label_rotation)

        # legend
        fig.legend(
            [bar[0] for bar in bars],
            fancy_names,
            loc='lower center',
            bbox_to_anchor=(0.5 + 0.04 * aspect_ratio, -0.01),
            ncol=3,
            frameon=False
        )

        # figure title
        if title_on:
            fig.suptitle(custom_title if custom_title else
                         "Source Load Apportionment Comparison between Scenarios",
                         x=0.5, y=1.03)

        # save plot
        fig.tight_layout(rect=[0, 0.13, 1, 1])
        fig.savefig(output_name + '.pdf', bbox_inches='tight',
                    facecolor='white', edgecolor='none', format='pdf')
