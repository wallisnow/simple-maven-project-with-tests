#!/usr/bin/python3

import json, re, shutil, tarfile, glob

from utils.common import log, runCMD, getFileDirectory

from utils.artifactory import ArtifactoryClient

from pathlib import Path

################################################################################
# TarballBuilder
################################################################################

class TarballBuilder:

    def __init__(self, config):
        self.tar_path = config["tar_path"]
        self.artifactoryclient = ArtifactoryClient(config["artifactory_config"])
        self.tar_postfix = config["tar_postfix"]
        self.tar_prefix = config["tar_prefix"]
        self.root = config["root"]
        self.version = config["version"]
        self.build_number = config["build_number"]
        self.target_path = config["target_path"]
        self.tar_target_location = config["tar_target_location"]
        self.helm_search_pattern = config["helm_search_pattern"]
        self.helm_charts_source =  config["helm_charts_source"]
        self.helm_charts_target =  config["helm_charts_target"]

    def clean(self):
        try:
            shutil.rmtree(self.target_path)
        except:
            pass
        try:
            Path(self.__tarPath()).unlink()
        except:
            pass

    def build(self):
        '''
        Copy direcories and files from git repo
        '''
        self.__appendWithFilesAndDirectories()

        # Copy helm-charts
        self.__copyHelmCharts()

        tar_path = self.__tarPath()
        base_dir_name = self.__genTarName().replace(".tgz", '')
        cmd = ["tar", "-zcvf", tar_path, "-C", self.target_path, '.',
               "--transform", "s/./{}/".format(base_dir_name)]
        cmd[1:1] = self.__getExcludes()
        runCMD(cmd)

    def publish(self):
        tar_path = self.__tarPath()
        target_path = "{}/{}".format(self.__artifactoryPath(),
                                     self.__genTarName())
        log("Save tar to artifactory. ({})".format(target_path))
        if not self.artifactoryclient.putFile(tar_path, target_path):
            raise Exception("Failed to publish tar at {}".format(target_path))

    def findBuild(self, all_builds=True):
        tar_name = self.__genTarName(wild_card=all_builds)
        path = self.__artifactoryPath()
        files = self.artifactoryclient.searchFiles("{}/{}".format(
                                                    path,tar_name))
        return len(files) > 0

    def getLatestTarName(self):
        tar_name = self.__genTarName(wild_card=True)
        path = self.__artifactoryPath()
        files = self.artifactoryclient.searchFiles("{}/{}".format(
                                                    path,tar_name))
        files.sort(reverse = True)
        if len(files) > 0:
            return files[0].split('/')[-1]
        else:
            return None

    # Private functions
    def __getExcludes(self):
        excludes = []
        search_path = "{}/components/**/exclude_from_tar".format(
                        self.target_path)
        for filename in sorted(glob.glob(search_path, recursive=True)):
            dir = getFileDirectory(filename)
            local_dir=dir.replace(self.target_path+"/", '')
            excludes.append("--exclude='./{}'".format(local_dir))
        return excludes

    def __artifactoryPath(self):
        return "{}/{}/tars".format(self.tar_path, self.version)

    def __tarPath(self):
        tarname = self.__genTarName()
        return "{}/{}/{}".format(self.root, self.tar_target_location, tarname)

    # version can be x.x.x or x.x.x-nightly or  x.x.x-whatever
    def __genTarName(self, wild_card=False):
        cmd =[ "git", "log", "--pretty=tformat:\"%h\"", "-n", "1"]
        hash = runCMD(cmd).stdout.strip()
        if wild_card:
            build_number = '*'
        else:
            build_number = self.build_number
        return "{}-{}-{}-{}-{}".format(self.tar_prefix, self.version,
                                          build_number, hash,
                                          self.tar_postfix)

    def __copyHelmCharts(self):
        target_path = "{}/{}".format(self.target_path, self.helm_charts_target)
        try:
            Path(target_path).mkdir()
        except:
            pass
        for file in glob.glob("{}/{}/{}".format(self.root,
                    self.helm_charts_source, self.helm_search_pattern)):
            shutil.copy(file, "{}/{}".format(target_path, file.split('/')[-1]))

    def __appendWithFilesAndDirectories(self):
        '''
        Copy direcories and files from git repo
        '''
        # Create Ansible direcory
        shutil.copytree("{}/erikube-deployment/ansible/erikube".format(
                        self.root), "{}/ansible/erikube/".format(
                                    self.target_path), symlinks=True)
        Path("{}/ansible/common".format(self.target_path)).mkdir()
        shutil.copy("{}/container-list.json".format(self.target_path),
                    "{}/ansible/common/container-list.json".format(
                    self.target_path))

        # Copy scripts
        shutil.copytree("{}/erikube-deployment/scripts".format(self.root),
                        "{}/scripts".format(self.target_path), symlinks=True)

        # Copy terraform
        shutil.copytree("{}/erikube-deployment/terraform".format(self.root),
                        "{}/terraform".format(self.target_path), symlinks=True)

        # Copy CHANGELOG
        shutil.copy("{}/CHANGELOG.md".format(self.root),
                    "{}/CHANGELOG.md".format(self.target_path))

        # Copy README
        shutil.copy("{}/docs/release/README.md".format(self.root),
                    "{}/README.md".format(self.target_path))

        git_hash = ""

        cmd =[ "git", "log", "--pretty=tformat:\"%H\"", "-n", "1"]
        output = runCMD(cmd)
        git_hash = output.stdout

        # Create extra_info (git hash)
        with open("{}/extra_info".format(self.target_path), "w") as f:
            f.write("RELEASE_GIT_HASH={}".format(git_hash))
