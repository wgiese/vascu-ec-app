import os
from pathlib import Path

from polarityjam.utils.io import read_parameters


class Parameter:

    def __init__(self, *args, **kwargs):
        if args == () and kwargs == {}:
            # init with default values from resources
            current_path = Path(os.path.dirname(os.path.realpath(__file__)))
            param_base_file = Path(current_path).joinpath("..", "utils", "resources", "parameters.yml")
            kwargs = read_parameters(param_base_file)

        if args != ():
            for dictionary in args:
                for key in dictionary:
                    self._setattr(key, dictionary[key])

        if kwargs != {}:
            for key in kwargs:
                self._setattr(key, kwargs[key])

    def _setattr(self, key, val):
        if hasattr(self, key):
            setattr(self, key, val)

    @classmethod
    def from_yml(cls, path):
        params = read_parameters(path)

        cls(**params)

    def __str__(self, indent=2):
        s = '\n'
        for attr in self.__dict__:
            for i in range(0, indent):
                s += '\t'
            s += (attr + ':\t' + str(getattr(self, attr))) + '\n'
        return s


class SegmentationParameter(Parameter):

    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        self.manually_annotated_mask = None
        self.store_segmentation = None
        self.use_given_mask = None
        self.cp_model_type = None
        self.cp_model_path = None
        self.estimated_cell_diameter = None
        self.use_gpu = None
        self.clear_border = None
        self.min_cell_size = None
        self.min_nucleus_size = None
        self.min_organelle_size = None

        super().__init__(**attrs)


class InputParameter(Parameter):

    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        self.channel_junction = None
        self.channel_nucleus = None
        self.channel_organelle = None
        self.channel_expression_marker = None
        self.membrane_thickness = None
        self.feature_of_interest = None

        super().__init__(**attrs)


class PlotParameter(Parameter):

    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        self.plot_junctions = None
        self.plot_polarity = None
        self.plot_orientation = None
        self.plot_marker = None
        self.plot_ratio_method = None
        self.plot_cyclic_orientation = None

        self.outline_width = None
        self.show_polarity_angles = None
        self.show_graphics_axis = None

        self.graphics_output_format = None
        self.dpi = None
        self.graphics_width = None
        self.graphics_height = None

        super().__init__(**attrs)