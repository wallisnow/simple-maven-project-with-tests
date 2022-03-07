#!/usr/bin/python3

import json, subprocess, argparse, copy

from utils.common import log, createContainerList, parseMasterFile, loadConfig, headerLog

from utils.componentbuilder import ComponentBuilder
from utils.helmbuilder import Helmbuilder
from utils.tarballbuilder import TarballBuilder

################################################################################
#  Util to create containers artifacts and tarball
#  This tool is also made to publish them and push them to
#  Armdocker and artifactory
################################################################################

def getArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default="config.json",
                        help="Configuration file path")
    parser.add_argument('--root', type=str, required=True,
                        help="where git root is located")
    parser.add_argument('--buildall', action='store_true',
                        help="This ignores what it stored in external sources")
    parser.add_argument('--masterdata', type=str, default="",
                        help="Location of master data. If not used the config is used.")
    parser.add_argument('--publish', action='store_true',
                        help="Will upload content to armdocker and artifactory")
    parser.add_argument('--noclean', action='store_true',
                        help="Do not execute cleanup step")
    parser.add_argument('--force', action='store_true',
                        help="Ignore existing local resources and build anycase.")
    parser.add_argument('--cleanonly', action='store_true',
                        help="Execute only cleanup.")
    parser.add_argument('--buildnumber', type=int, default=1,
                        help="Build number")
    return parser.parse_args()

def main():
    args  = getArgs()

    # Load config file
    configs=loadConfig(args.config, args.root)
    masterdata_file = args.masterdata
    if masterdata_file == "":
        masterdata_file = configs["master_data_file"]

    # Get all items from master record
    (all_images, all_artifacts, all_helmcharts, all_components,
        version, default_registry) = parseMasterFile(masterdata_file)

    ############################################################################

    # Create all clients
    headerLog("Create Builders")

    hcc = configs["helm_client_config"]
    hcc["make_client_config"] = configs["make_client_config"]
    helmbuilder = Helmbuilder(hcc)

    configs["component_builder_config"]["version"] = version
    configs["component_builder_config"]["default_registry"] = default_registry
    componentBuilder = ComponentBuilder(configs["component_builder_config"])

    configs["tar_client_config"]["version"] = version
    configs["tar_client_config"]["build_number"] = args.buildnumber
    tarballbuilder = TarballBuilder(configs["tar_client_config"])

    ############################################################################

    if args.cleanonly:
        headerLog("Clean only")
        all_images.extend(helmbuilder.getImages(all_helmcharts))
        componentBuilder.set(all_components, all_images, all_artifacts,
                             all_helmcharts,cleanonly=True)
        componentBuilder.clean()
        tarballbuilder.clean()
        helmbuilder.clean()
        headerLog("Exit")
        return

    log("Try to find latest build")
    latest_build = tarballbuilder.getLatestTarName()

    if not args.force and latest_build != None:
        log("Build found!")
        log("Latest build is {}".format(latest_build))
        headerLog("End")
        return
    else:
        log("No build found!")

    ############################################################################

    headerLog("Build Helm")
    helmbuilder.build()

    headerLog("Update images from Helm")
    images, helm_component = helmbuilder.getImages(all_helmcharts)
    all_images.extend(images)
    all_components.append(helm_component)

    ############################################################################

    headerLog("Setup componentBuilder")
    componentBuilder.set(all_components, all_images, all_artifacts,
                         all_helmcharts)

    headerLog("Build components")
    componentBuilder.build(args.force)

    ############################################################################

    headerLog("Build Tarball")
    tarballbuilder.build()

    ############################################################################

    if args.publish:
        headerLog("Publish All")
        componentBuilder.publish()
        # TODO: helm publish will not override what ever helmcharts there is.
        # So that patchset can override master charts without any checks!
        # enable when actually needed or overriding is fixed
        #helmbuilder.publish()
        tarballbuilder.publish()

    ############################################################################

    if not args.noclean:
        headerLog("Cleanup")
        helmbuilder.clean()
        componentBuilder.clean()
        tarballbuilder.clean()

    headerLog("End")

main()
