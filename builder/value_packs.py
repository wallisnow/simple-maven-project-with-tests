#!/usr/bin/env python3

import os
from typing import Pattern
import git
import sys
import json
import shutil
import hashlib
import tarfile
import logging
import requests
import subprocess
import argparse
from pathlib import Path
import re

# value packs handler
# This script can build value packs, and return a list
# of value packs from an specified CCD software
# package

g_armdocker_url = "armdocker.rnd.ericsson.se"
g_value_pack_artifactory_path = "https://arm.rnd.ki.sw.ericsson.se/artifactory/proj-erikube-generic-local/erikube/baremetal/valuepacks/"

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(lineno)d: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def getArgs():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd", help='sub-command help')
    subparsers.required = True

    # build
    build_sub = subparsers.add_parser(
        'build', help="Build value packs based on container-list.json")
    build_sub.add_argument('--container-list', '-c',
                           type=argparse.FileType('r'),
                           help="container-list.json for this sw package.",
                           default="./container-list.json")
    build_sub.set_defaults(func=build_value_pack)

    # list
    list_sub = subparsers.add_parser(
        'list',
        help="List value packs associated with an specified CCD sw package"
    )
    list_sub.add_argument('--software-package', '-s',
                          help="Software package tarball to examine",
                          required=True)
    list_sub.set_defaults(func=list_value_pack)

    return parser.parse_args()


def generate_value_pack_tarball(value_pack_filename):
    source_dir = value_pack_filename.split(".tar.gz")[0]
    try:
        with tarfile.open("{}".format(value_pack_filename), "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))
    except Exception as e:
        logger.error("Failed to compress directory: %s into file: %s, due to %s",
                     source_dir, value_pack_filename, e.message)


def create_target_folder(folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    else:
        try:
            shutil.rmtree(folder_name)
        except OSError as e:
            logger.error(
                "Failed to remove existing folder: %s due to %s", folder_name, e.strerror)
            exit("Failed to remove existing folder: %s due to %s" %
                 (folder_name, e.strerror))


def get_credential():
    user, passwd = None, None
    sdnrad_file = Path.home().as_posix() + '/sdnrad.creds'
    with open(sdnrad_file) as f:
        content = f.readlines()
        for line in content:
            if g_armdocker_url in line.strip():
                user = line.strip().split(" ")[3]
                passwd = line.strip().split(" ")[5]
    return user, passwd


def pull_and_save_container(docker_image_url, image_tarball_file, folder_name):
    user, passwd = get_credential()
    copy_commnad = ["skopeo", "copy"]
    if not (user == None or passwd == None):
        copy_commnad.append("--src-creds={}:{}".format(user, passwd))
    copy_commnad.extend(["docker://{}".format(docker_image_url),
                         "docker-archive:{}/{}".format(folder_name, image_tarball_file)])
    result = subprocess.run(copy_commnad)
    if result.returncode != 0:
        logger.error("Failed to pull container image: %s with return code %s",
                     docker_image_url, result.returncode)


def fill_metadata(container_tag, image_tarball_file, metadata):
    image_metadata = dict()
    image_metadata['name'] = container_tag
    image_metadata['path'] = image_tarball_file.split(":")[0]
    metadata['images'].append(image_metadata)


def dump_metadata_into_file(file_path, metadata):
    with open(file_path, 'w') as fp:
        json.dump(metadata, fp)
    logger.info("Dump metadata into file: %s", file_path)


def init_metadata(data):
    metadata = dict()
    metadata['version'] = data.get('erikube_version')
    metadata['hash'] = git.Repo(
        search_parent_directories=True).head.object.hexsha
    metadata['images'] = []
    metadata['yamls'] = []
    return metadata


def get_container(path, containers):
    '''Recursively search the container matching the path
    '''
    parts = path.split(".")
    if len(parts) == 1:
        if parts[0] in containers.keys():
            return containers[parts[0]]
        else:
            logger.error("container: %s not find", parts[0])
            exit("container: %s not find" % (parts[0]))
    else:
        if parts[0]:
            new_path = ".".join(parts[1:])
            sub_containers = containers[parts[0]]
        else:
            new_path = ".".join(parts[2:])
            sub_containers = containers[parts[1]]
        return get_container(new_path, sub_containers)


def do_build_value_pack(folder_name, value_pack, data):
    metadata = init_metadata(data)
    create_target_folder(folder_name)
    for container_path in value_pack.get('containers'):
        container_tag = get_container(container_path, data)
        docker_image_url = "%s/%s" % (data.get('default_registry'),
                                      container_tag)
        image_tarball_file = container_tag+'.tar'
        pull_and_save_container(
            docker_image_url, image_tarball_file.split(":")[0], folder_name)
        fill_metadata(container_tag, image_tarball_file, metadata)
    dump_metadata_into_file(folder_name+'/metadata.json', metadata)


def generate_value_pack_filename(value_pack, data):
    container_names_with_tag = []
    value_pack_name = value_pack.get('name')
    for container_path in value_pack.get('containers'):
        container_tag = get_container(container_path, data)
        container_names_with_tag.append(container_tag)
    value_pack_hash = hashlib.md5(
        "".join(container_names_with_tag).encode('utf-8')).hexdigest()
    value_pack_filename = "{}-{}-{}.tar.gz".format(value_pack.get('package_name_prefix'),
                        data.get('erikube_version'), value_pack_hash)
    return value_pack_name, value_pack_filename


def build_value_pack(args: argparse.Namespace):
    data = None
    logger.debug(f"Loading {args.container_list}...")
    data = json.load(args.container_list)

    valuepacks = list()
    release = data.get('erikube_version')

    value_pack_artifactory_path = "{}/{}/".format(
        g_value_pack_artifactory_path, release)
    for value_pack in data.get('value_packages').get('baremetal'):
        value_pack_name, value_pack_filename = generate_value_pack_filename(
            value_pack, data)
        valuepacks.append(value_pack_filename)
        try:
            request = requests.get(
                value_pack_artifactory_path + value_pack_filename)
            if request.status_code == 200:
                logger.info(
                    "Value Package: %s already exist, skip re-build", value_pack_name)
            else:
                logger.info(
                    "Value Package: %s not exist, need to build it", value_pack_name)
                do_build_value_pack(value_pack_filename.split(".tar.gz")[
                                    0], value_pack, data)
                generate_value_pack_tarball(value_pack_filename)
        except ConnectionError:
            logger.error(
                "Failed to connect to artifactory, failed value package building for %s", value_pack_name)
            exit("Failed to connect to artifactory, failed value package building for %s" % (
                value_pack_name))

    # print the list to stdout
    logger.info("Value pack list JSON: %s", json.dumps(valuepacks))
    print(json.dumps(valuepacks))


def get_file_from_tar(tarf: tarfile.TarFile, p: Pattern[str]):
    '''Returns a file object for a file that matches the regex'''

    while True:
        info = tarf.next()
        if info is None:
            return None
        logging.debug(f"Checking inside tarball {info.name}")
        if p.match(info.name):
            return tarf.extractfile(info)


def parse_container_list_from_tar(tarball_path: str):
    logging.info(f"Openning tarball {tarball_path}...", )
    p = re.compile('^.*\/container-list.json$')
    with tarfile.open(tarball_path, "r:*") as tarf:
        container_list_f = get_file_from_tar(tarf, p)
        return json.load(container_list_f)


def parse_container_list(json_path: str):
    with open(json_path, "r") as f:
        return json.load(f)


def list_value_pack(args: argparse.Namespace):
    data = None
    try:
        data = parse_container_list_from_tar(args.software_package)
    except Exception:
        logging.warning(
            f"{args.software_package} is not a software package tarball!")
        logging.warning("Trying as a directory")
        data = parse_container_list(os.path.join(
            args.software_package, "container-list.json"))
    valuepacks = list()

    for value_pack in data.get('value_packages').get('baremetal'):
        value_pack_name, value_pack_filename = generate_value_pack_filename(
            value_pack, data)
        logging.debug(f"Found value pack {value_pack_name}")
        valuepacks.append(value_pack_filename)

    print(json.dumps(valuepacks))


if __name__ == '__main__':
    args = getArgs()
    exit(args.func(args))
