import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from polarityjam.feature_extraction import get_features_from_cellpose_seg_multi_channel, Extractor
from polarityjam.polarityjam_logging import get_logger
from polarityjam.utils import parameters
from polarityjam.utils.io import read_parameters, read_image, get_tif_list, read_key_file, \
    get_doc_file_prefix, write_dict_to_yml, create_path_recursively
from polarityjam.utils.plot import plot_seg_channels, plot_cellpose_masks, set_figure_dpi
from polarityjam.utils.seg import load_or_get_cellpose_segmentation, get_image_for_segmentation


def run(args):
    set_figure_dpi()

    # read args
    param_file = args.param
    filepath = args.in_file
    filename = args.filename_prefix
    output_path = args.out_path

    # print info
    get_logger().info(
        "Arguments provided: %s" % json.dumps(
            {"param": param_file, "in_file": filepath, "out_path": output_path, "filename": filename},
            sort_keys=True, indent=4
        )
    )

    # process args
    if not filename:
        filename, _ = os.path.splitext(os.path.basename(filepath))

    parameters = read_parameters(param_file)
    get_logger().info("Parameters: %s" % json.dumps(parameters, sort_keys=True, indent=4))

    # start routine
    _run_oo(filepath, parameters, output_path, filename)
    _finish(parameters, output_path)


def _finish(parameters, output_path):
    # write parameters to disk
    out_param = Path(output_path).joinpath("%s_param%s" % (get_doc_file_prefix(), ".yml"))
    get_logger().info("Writing parameter to disk: %s" % out_param)
    write_dict_to_yml(out_param, parameters)


def _run(infile, parameters, output_path, fileout_name):
    create_path_recursively(output_path)

    # read input
    img = read_image(infile)
    img_seg = get_image_for_segmentation(parameters, img)

    # plot input
    plot_seg_channels(img_seg, output_path, fileout_name, parameters)

    # basic segmentation
    cellpose_mask = load_or_get_cellpose_segmentation(parameters, img_seg, infile)

    # plot cellpose mask
    plot_cellpose_masks(img_seg, cellpose_mask, output_path, fileout_name, parameters)

    # feature extraction
    properties_df = get_features_from_cellpose_seg_multi_channel(
        parameters, img, cellpose_mask, fileout_name, output_path
    )

    get_logger().info("Head of created dataset: \n %s" % properties_df.head())

    # write output
    fileout_base, _ = os.path.splitext(fileout_name)
    fileout_path = Path(output_path).joinpath(fileout_base + ".csv")
    get_logger().info("Writing features to disk: %s" % fileout_path)
    properties_df.to_csv(str(fileout_path), index=False)

    return properties_df, cellpose_mask


def _set_params(param):
    # set parameters
    for key in param.keys():
        try:
            setattr(parameters, str(key), param[key])
        except KeyError as e:
            get_logger().info("Key \"%s\"in parameters file specified that is unknown!" % str(key))
            raise KeyError from e


def _run_oo(infile, param, output_path, fileout_name):
    create_path_recursively(output_path)

    # set the parameters
    _set_params(param)

    # read input
    img = read_image(infile)
    img_seg = get_image_for_segmentation(param, img)

    # plot input
    plot_seg_channels(img_seg, output_path, fileout_name, param)

    # basic segmentation
    cellpose_mask = load_or_get_cellpose_segmentation(param, img_seg, infile)

    # plot cellpose mask
    plot_cellpose_masks(img_seg, cellpose_mask, output_path, fileout_name, param)

    # feature extraction
    e = Extractor(img, cellpose_mask, fileout_name, output_path)
    properties_df = e.extract(param)

    get_logger().info("Head of created dataset: \n %s" % properties_df.head())

    # write output
    fileout_base, _ = os.path.splitext(fileout_name)
    fileout_path = Path(output_path).joinpath(fileout_base + ".csv")
    get_logger().info("Writing features to disk: %s" % fileout_path)
    properties_df.to_csv(str(fileout_path), index=False)

    return properties_df, cellpose_mask


def run_stack(args):
    set_figure_dpi()

    # read args
    param_file = args.param
    inpath = args.in_path
    output_path = args.out_path

    # print info
    get_logger().info(
        "Arguments provided: %s" % json.dumps(
            {"param": param_file, "in_path": inpath, "out_path": output_path},
            sort_keys=True, indent=4
        )
    )

    # process
    parameters = read_parameters(param_file)
    get_logger().info("Parameters: %s" % json.dumps(parameters, sort_keys=True, indent=4))

    file_list = get_tif_list(inpath)

    for filepath in file_list:
        filepath = Path(filepath)
        filename = filepath.stem + filepath.suffix

        if not ((filepath.suffix != ".tif") or (filepath.suffix != ".tiff")):
            continue

        get_logger().info(
            "Processing file with: file stem  \"%s\" and file extension: \"%s\"" % (filepath.stem, filepath.suffix)
        )

        # start routine
        _run(filepath, parameters, output_path, filename)

    _finish(parameters, output_path)


def run_key(args):
    set_figure_dpi()

    # read args
    param_file = args.param
    in_path = args.in_path
    inkey = args.in_key
    output_path_base = args.out_path

    # print info
    get_logger().info(
        "Arguments provided: %s" % json.dumps(
            {"param": param_file, "in_key": inkey, "out_path": output_path_base},
            sort_keys=True, indent=4
        )
    )

    # convert
    output_path_base = Path(output_path_base)
    create_path_recursively(output_path_base)
    in_path = Path(in_path)

    # process
    parameters = read_parameters(param_file)
    get_logger().info("Parameters: %s" % json.dumps(parameters, sort_keys=True, indent=4))
    key_file = read_key_file(inkey)

    # empty DF summarizing overall results
    summary_df = pd.DataFrame()

    offset = 0
    for k, row in key_file.iterrows():
        # current stack input sub folder
        cur_sub_path = str(row['folder_name'])
        if cur_sub_path.startswith(os.path.sep):
            cur_sub_path = cur_sub_path[1:-1]
        input_path = in_path.joinpath(cur_sub_path)

        # current stack output sub-folder
        cur_sub_out_path = str(row["short_name"])
        output_path = output_path_base.joinpath(cur_sub_out_path)

        # empty results dataset for each condition
        merged_properties_df = pd.DataFrame()

        file_list = get_tif_list(input_path)
        for file_index, filepath in enumerate(file_list):
            filepath = Path(filepath)
            filename = filepath.stem + filepath.suffix

            if not ((filepath.suffix != ".tif") or (filepath.suffix != ".tiff")):
                continue

            get_logger().info(
                "Processing file with: file stem  %s and file extension: %s" % (filepath.stem, filepath.suffix)
            )

            # single run
            properties_df, cellpose_mask = _run(filepath, parameters, output_path, filename)

            # append condition
            properties_df["condition"] = row["short_name"]

            if merged_properties_df.empty:
                merged_properties_df = properties_df.copy()
            else:
                merged_properties_df = pd.concat([merged_properties_df, properties_df], ignore_index=True)

            summary_df.at[offset + file_index, "folder_name"] = row["folder_name"]
            summary_df.at[offset + file_index, "short_name"] = row["short_name"]
            summary_df.at[offset + file_index, "filepath"] = filepath
            summary_df.at[offset + file_index, "cell_number"] = len(np.unique(cellpose_mask))

        offset = offset + len(file_list)
        merged_file = str(output_path.joinpath("merged_table_%s" % row["short_name"] + ".csv"))
        get_logger().info("Writing merged features to disk: %s" % merged_file)
        merged_properties_df.to_csv(merged_file, index=False)

    summary_df_path = output_path_base.joinpath("summary_table" + ".csv")
    get_logger().info("Writing summary table to disk: %s" % summary_df_path)
    summary_df.to_csv(str(summary_df_path), index=False)

    keyfile_path = output_path_base.joinpath("key_file" + ".csv")
    get_logger().info("Writing key file to disk: %s" % keyfile_path)
    key_file.to_csv(str(keyfile_path), index=False)

    _finish(parameters, output_path_base)
