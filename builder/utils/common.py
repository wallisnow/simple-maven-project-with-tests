#!/usr/bin/python3

import requests, json, subprocess, time, glob, hashlib, os
from requests.auth import HTTPBasicAuth
from datetime import datetime

################################################################################
# Generic global functions
################################################################################
def loadConfig(filepath, root):
    with open(filepath, 'r') as f:
        configs = json.load(f)

    target_path = "{}/{}".format(root, configs["target_build_dir"])

    # Prepare some configs to have nested configs
    tcc = configs["tar_client_config"]
    tcc["artifactory_config"] = configs["artifactory_config"]
    tcc["target_path"] = target_path
    tcc["root"] = root

    configs["helm_client_config"]["target_path"] = target_path
    configs["helm_client_config"]["root"] = root

    configs["make_client_config"]["root"] = root

    ccc = configs["container_client_config"]
    ccc["armdocker_config"] = configs["armdocker_config"]
    ccc["artifactory_config"] = configs["artifactory_config"]

    cbc = configs["component_builder_config"]
    cbc["root"] = root
    cbc["target_path"] = target_path
    cbc["container_client_config"] = configs["container_client_config"]
    cbc["make_client_config"] = configs["make_client_config"]
    cbc["artifactory_config"] = configs["artifactory_config"]

    # update master data file
    configs["master_data_file"]="{}/{}".format(root,configs["master_data_file"])

    return configs


def headerLog(msg, width=80):
    log('-'*width)
    log(msg.center(width, "-"))
    log('-'*width)

def log(msg):
    print("{}: {}".format(datetime.now(),msg))

def parseMasterFile(masterfile):
    with open(masterfile, 'r') as f:
        json_data = json.load(f)

    images = []
    artifacts = []
    helmCharts = []
    components = []

    build_info = json_data["container_build_info"]
    for namespace in build_info:
        for key in build_info[namespace]:
            build_info[namespace][key]["key"] = key
            build_info[namespace][key]["namespace"] = namespace
            if "external_source" in build_info[namespace][key]:
                build_info[namespace][key]["external"] = True
            else:
                build_info[namespace][key]["external"] = False
            images.append(build_info[namespace][key])

    artifact_info = json_data["artifacts"]
    for key in artifact_info:
        artifact_info[key]["key"] = key
        artifacts.append(artifact_info[key])


    helm_info = json_data["helm_charts"]
    for key in helm_info:
        helm_info[key]["key"] = key
        helmCharts.append(helm_info[key])

    component_info = json_data["components"]
    for key in component_info:
        component_info[key]["key"] = key
        components.append(component_info[key])

    return (images, artifacts, helmCharts, components,
            json_data["erikube_version"], json_data["default_registry"])

def createContainerList(masterfile, images, targetfile):
    with open(masterfile, 'r') as f:
        json_data = json.load(f)

    del json_data["container_build_info"]
    del json_data["artifacts"]
    del json_data["components"]

    for key in json_data["helm_charts"]:
        if "source" in json_data["helm_charts"][key]:
            del json_data["helm_charts"][key]["source"]
        if "hash" in json_data["helm_charts"][key]:
            del json_data["helm_charts"][key]["hash"]

    json_data["containers"] = {}
    for image in images:
        if not image["namespace"] in json_data["containers"]:
            json_data["containers"][image["namespace"]] = {}

        image_name = "{}:{}".format(image["name"], image["tag"])
        json_data["containers"][image["namespace"]][image["key"]] = image_name

    with open(targetfile, 'w+') as f:
        f.write(json.dumps(json_data, indent=4))

def runCMDRetry(cmd, nofail=False, cwd=None, output=True, retry_count=3):
    for i in range(0,retry_count):
        try:
            return runCMD(cmd, nofail=nofail, cwd=cwd, output=output)
        except:
            pass

def runCMD(cmd, nofail=False, cwd=None, output=True):
    cmd_filtered = " ".join(filter(None,cmd))
    log("Execute Command: {} in path {}".format(cmd_filtered,cwd))
    popen = subprocess.Popen(cmd_filtered, cwd=cwd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, shell=True,
                              universal_newlines=True)

    stdout = ""
    for stdout_line in iter(popen.stdout.readline, ""):
        stdout += stdout_line
        if output:
            log("[\"{}\"][{}]: {}".format(cwd,
                    cmd_filtered,stdout_line.strip("\n")))

    popen.stdout.close()
    return_code = popen.wait()

    if not nofail and return_code:
        log("stderr:\n{}".format(popen.stderr.read()))
        raise subprocess.CalledProcessError(return_code, cmd_filtered)

    popen.stdout = stdout
    popen.stderr = popen.stderr.read()
    return popen

def getFilename(path):
    return path.split("/")[-1]

def getFileDirectory(path):
    return "/".join(path.split("/")[:-1])
