import numpy as np
import pandas as pd
from collections import MutableSequence
from matplotlib.gridspec import GridSpec
import matplotlib.pyplot as plt

from scenario import Scenario, _source_headers_arcmap, _source_colour_palette, _source_fancy_names


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
        if not isinstance(value, Scenario):
            raise TypeError("A {} can only contain instances of "
                            "{}.".format(self.__class__.__name__,
                                         Scenario.__name__))

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
                           for name in _source_headers_arcmap]
        else:
            fancy_names = [_source_fancy_names[name] for name in _source_headers_arcmap]

        # concatenate the scenarios into one dataframe
        all_loads = [scenario.loads for scenario in self.scenarios]
        all_names = [scenario.name for scenario in self.scenarios]

        df_loads = pd.concat(all_loads, axis=1)
        df_loads.columns = all_names

        # reindex the created dataframe to make sure that the order of the sources is standard
        # (because if the waterbodies are not ordered in the same way, it could have changed the
        # order of the sources during the concatenation)
        df_loads = df_loads.reindex(labels=_source_headers_arcmap, level='source')

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
        for i, source in enumerate(_source_headers_arcmap):
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
