from __future__ import print_function, absolute_import, division
import yamlreader
import boto3
import logging
import yaml
from monocyte import Monocyte


def read_config(path):
    return {} if path is None else yamlreader.yaml_load(path)



def convert_arguments_to_config(arguments):
    dry_run = (arguments["--dry-run"] != "False")
    config_path = arguments["--config-path"]
    whitelist_path = arguments.get('--whitelist', None)

    config = {
        "dry_run": dry_run,
    }

    return config_path, config, whitelist_path


def apply_default_config(config):
    if config.get("cloudwatchlogs"):
        cloudwatchlogs_default_config = {
            'region': 'eu-central-1',
            'log_level': 'INFO',
            'groupname': 'monocyte_logs'
        }
        yamlreader.data_merge(cloudwatchlogs_default_config, config['cloudwatchlogs'])

        log_level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARN': logging.WARN,
            'ERROR': logging.ERROR
        }
        cloudwatchlogs_default_config['log_level'] = log_level_map[cloudwatchlogs_default_config['log_level'].upper()]

        config['cloudwatchlogs'] = cloudwatchlogs_default_config

    default_config = {
        "handler_names": [
            "cloudformation.Stack",
            "ec2.Instance",
            "ec2.Volume",
            "rds2.Instance",
            "rds2.Snapshot",
            "dynamodb.Table",
            "s3.Bucket"],
        "ignored_resources": {"cloudformation": ["cloudtrail-logging"]},
        "ignored_regions": ["cn-north-1", "us-gov-west-1"],
        "allowed_regions_prefixes": ["eu"]
    }
    for key in default_config.keys():
        config[key] = config.get(key, default_config[key])


def main(arguments):
    path, cli_config, whitelist_uri = convert_arguments_to_config(arguments)
    file_config = read_config(path)
    whitelist = load_whitelist(whitelist_uri)
    config = yamlreader.data_merge(file_config, cli_config)
    apply_default_config(config)

    monocyte = Monocyte(**config)

    try:
        return monocyte.search_and_destroy_unwanted_resources()
    except Exception:
        monocyte.logger.exception("Error while running monocyte:")
        return 1


def load_whitelist(whitelist_uri):
    if(whitelist_uri != None):
        bucket_name = whitelist_uri.split('/', 4)[2]
        key = whitelist_uri.split('/', 3)[3]
        s3 = boto3.resource('s3')
        whitelist_string = s3.Object(bucket_name, key).get()['Body'].read()

        return yaml.load(whitelist_string)
    return {}