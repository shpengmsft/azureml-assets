"""This file contains the core logic for feature attribution drift component."""
import pandas as pd
from datetime import datetime
from shared_utilities.io_utils import init_spark, save_spark_df_as_mltable
from azureml.metrics import constants


def log_time_and_message(message):
    """Print the time in addition to message for logging purposes.

    :param message: The message to be printed after the time
    : type message: string
    """
    print(f"[{datetime.now()}] {message}")


def convert_pandas_to_spark(pandas_data):
    """Convert pandas.Dataframe to pySpark.Dataframe.

    :param pandas_data: the input pandas data to convert
    :type pandas_data: pandas.Dataframe
    :return: the input data in spark format
    :rtype: pySpark.Dataframe
    """
    spark = init_spark()
    return spark.createDataFrame(pandas_data)


def write_to_mltable(metrics_artifacts, output_data_file_name):
    """

    Args:
        metrics_artifacts:
        output_data_file_name:

    Returns:

    """
    log_time_and_message("Begin writing metric to mltable")
    # ToDo: We might need to support this for vector metrices as well
    metrics_data = pd.DataFrame([metrics_artifacts[constants.Metric.Metrics]])
    spark_data = convert_pandas_to_spark(metrics_data)
    save_spark_df_as_mltable(spark_data, output_data_file_name)