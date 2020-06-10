"""The Python `SLAMpy` is the implementation of SLAM in Python. SLAMpy
can both be used as an ArcMap Toolbox and as a Python package with its
Application Programming Interface (API).

The Source Load Apportionment Model (SLAM), developed by Ireland's
Environmental Protection Agency (EPA), estimates the phosphorus (P) and
nitrogen (N) loads that reach a river from all major sources in a
sub-catchment e.g. agriculture, forestry and industry.

This package was developed with the financial support of Ireland's
Environmental Protection Agency.

**References**

Mockler, E.M., Deakin, J., Archbold, M., Daly, D., Bruen, M.: Nutrient
Load Apportionment to Support the Identification of Appropriate Water
Framework Directive Measures, Biology and Environment, 116B(3), 245-263.
doi:10.3318/bioe.2016.22, 2016.
"""

from .scenario import Scenario, ScenarioV3, ScenarioV4
from .scenariolist import ScenarioList
