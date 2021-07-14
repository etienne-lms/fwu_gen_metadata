#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
#
# Copyright (c) 2021, STMicroelectronics
#
# -*-encoding:utf-8*-

"""
    CLI tool to interact with the 'fwu_metadata' data structure
    Contains files for:
        - gen_metadata.py:  CLI management
        - src/metadata.py:  Python dict fwu_metadata
        - src/structs.py:   C-style struct fwu_metadata
        - src/utils.py:     Usefull functions for all project
        - src/uuid_t.py:    Class & functions to deal with UUID
        - src/shell.py:     Interactive or scripted shell to automate things
"""

import json
import argparse

from src.uuid_t import test_uuids
from src.utils import test_utils
from src.metadata import create_dummy_metadata, validate_metadata
from src.structs import fwupd_from_dict, fwupd_to_dict
from src.shell import start_shell

# COMMAND LINE


def cli_dummy(dummy_args):
    """
        Routine for the command "dummy" passed in CLI
    """
    try:
        dummy_metadata = create_dummy_metadata(
            dummy_args.nb_fw_imgs, dummy_args.nb_banks)
        assert validate_metadata(dummy_metadata)
        fwupd = fwupd_from_dict(dummy_metadata)
        if dummy_args.display:
            fwupd.display()
        json.dump(dummy_metadata, dummy_args.jsonfile, indent=4)
        dummy_args.binfile.write(fwupd)
    finally:
        dummy_args.jsonfile.close()
        dummy_args.binfile.close()


def cli_jsonparse(jsonparse_args):
    """
        Routine for the command "jsonparse" passed in CLI
    """
    try:
        data = json.load(jsonparse_args.jsonfile)
        if not validate_metadata(data):
            raise Exception("Metadata contained in file are not correct")
        fwupd = fwupd_from_dict(data)
        if jsonparse_args.display:
            fwupd.display()
        jsonparse_args.binfile.write(fwupd)
    finally:
        jsonparse_args.jsonfile.close()
        jsonparse_args.binfile.close()


def cli_binparse(binparse_args):
    """
        Routine for the command "binparse" passed in CLI
    """
    try:
        if binparse_args.template:
            template_data = json.load(binparse_args.template)
            configs = template_data["configs"]
            dummy_metadata = create_dummy_metadata(
                configs["nb_fw_img"], configs["nb_fw_banks"])
        else:
            template_data = {"uuids": {"locations": {}, "entries": {}}}
            dummy_metadata = create_dummy_metadata(
                binparse_args.nb_fw_imgs, binparse_args.nb_banks)
        assert validate_metadata(dummy_metadata)
        fwupd = fwupd_from_dict(dummy_metadata)
        binparse_args.binfile.readinto(fwupd)
        if binparse_args.display:
            fwupd.display()
        data = fwupd_to_dict(fwupd, binparse_args.nb_fw_imgs,
                             binparse_args.nb_banks,
                             list(template_data["uuids"]["entries"].keys()),
                             template_data["uuids"]["locations"])
        json.dump(data, binparse_args.jsonfile, indent=4)
    finally:
        if binparse_args.template:
            binparse_args.template.close()
        binparse_args.binfile.close()
        binparse_args.jsonfile.close()


def cli_dump(dump_args):
    """
        Routine for the "Dump" command passed in CLI
    """
    try:
        dummy_metadata = create_dummy_metadata(
            dump_args.nb_fw_imgs, dump_args.nb_banks)
        fwupd = fwupd_from_dict(dummy_metadata)
        dump_args.binfile.readinto(fwupd)
        fwupd.display()
    finally:
        dump_args.binfile.close()


def cli_test(test_args):
    """ Routine for the "Test" command passed in CLI """
    all_tests = [("Utils", test_utils), ("UUIDs", test_uuids)]
    if test_args.number == -1:
        for (key, test) in all_tests:
            print("Test " + key)
            test(test_args)
            print("")
    elif test_args.number < len(all_tests):
        print("Test " + all_tests[test_args.number][0])
        all_tests[test_args.number][1](test_args)
    else:
        print("Tests available:")
        for nbtest, (test, _) in enumerate(all_tests):
            print("\t{} - Test {}".format(nbtest, test))


def cli_shell(shell_args):
    """
        Routine for the "Shell" command passed in CLI
    """
    try:
        # Gather all the commands from CLI and script
        cmdlist_raw = list()
        if shell_args.script:
            cmdlist_raw = shell_args.script.read().split("\n")
        cmdlist_raw.extend(" ".join(shell_args.commands))

        # Create clean commands + args from the lines
        cmdlist = list()
        for cmd in cmdlist_raw:
            # Cut the comments
            cmd = cmd.split("#")[0].lstrip()

            # Remove empty lines
            if cmd == "":
                continue

            # Split comma-separated commands, strip whitespaces
            cmdlist.extend([el.rstrip().lstrip() for el in cmd.split(",")])

        kwargs = {}
        if shell_args.jsonfile:
            kwargs["jsonfile"] = shell_args.jsonfile
        if shell_args.binfile:
            kwargs["binfile_load"] = shell_args.binfile + " " + \
                str(shell_args.nb_fw_imgs) + " " + str(shell_args.nb_banks)

        start_shell(cmdlist, shell_args.keep, shell_args.verbose, **kwargs)

    finally:
        if shell_args.script:
            shell_args.script.close()


def cli():
    """ Function parsing args, dispatching commands """
    parser = argparse.ArgumentParser()
    subp = parser.add_subparsers(dest="cmd")

    # GENERAL ARGS
    parser.add_argument("--nb-fw-imgs", "-ni", default=1, type=int,
                        help="Number of firmware images in entries")
    parser.add_argument("--nb-banks", "-nb", default=2, type=int,
                        help="Number of firmware banks for each image")

    # DUMMY
    dummy = subp.add_parser("dummy",
                            help="Create a dummy JSON metadata file and a " +
                            "dummy binary metadata file")
    dummy.add_argument("--display", "-v", action="store_true",
                       help="Display the content of the binary metadata" +
                       " after creation")
    dummy.add_argument("--jsonfile", "-j", type=argparse.FileType("w"),
                       default="dummy.json",
                       help="The JSON file where to write the dummy metadata")
    dummy.add_argument("--binfile", "-b", type=argparse.FileType("wb"),
                       default="dummy.bin",
                       help="The binary file where to write the dummy metadata"
                       )

    # JSON PARSE
    jsparse = subp.add_parser("jsonparse",
                              help="Parse json and creates a binary " +
                              "metadata file")
    jsparse.add_argument("jsonfile", type=argparse.FileType("r"),
                         help="The JSON file where to read the metadata from")
    jsparse.add_argument("--display", "-v", action="store_true",
                         help="Display the content of the binary metadata " +
                         "after creation")
    jsparse.add_argument("--binfile", "-b", type=argparse.FileType("wb"),
                         default="fwupd.bin",
                         help="The binary file where to write the binary " +
                         "metadata")

    # BINPARSE
    binparse = subp.add_parser("binparse",
                               help="Parse binary data and generates a JSON " +
                               "metadata file")
    binparse.add_argument("binfile", type=argparse.FileType("rb"),
                          help="The binary file where to read the metadata " +
                          "from")
    binparse.add_argument("--display", "-v", action="store_true",
                          help="Display the content of the binary metadata " +
                          "after creation")
    binparse.add_argument("--jsonfile", "-j", type=argparse.FileType("w"),
                          default="fwupd.json",
                          help="The JSON file where to write the generated " +
                          "JSON metadata")
    binparse.add_argument("--template", "-t", type=argparse.FileType("r"),
                          help="The JSON file to read the config from & use " +
                          "as a template")

    # DUMP
    dump = subp.add_parser("dump",
                           help="Read a binary metadata file and prints " +
                           "its data")
    dump.add_argument("binfile", type=argparse.FileType("rb"),
                      help="The binary file where to reda the metadata from")

    # SHELL
    shell = subp.add_parser("shell",
                            help="Creates a shell to interact dynamically " +
                            "with the metadata")
    shell.add_argument("--jsonfile", "-j", type=str,
                       help="The JSON file to interact with")
    shell.add_argument("--binfile", "-b", type=str,
                       help="The binary file to interact with")
    shell.add_argument("--script", "-s", type=argparse.FileType("r"),
                       help="A file containing the list of commands to pass " +
                       "to the shell directly")
    shell.add_argument("--keep", "-k", action="store_true",
                       help="Keep the shell open for interactive commands " +
                       "after the end")
    shell.add_argument("--verbose", "-v", action="store_true",
                       help="Display the commands passed from script / " +
                       "stdinput")
    shell.add_argument("commands", type=str, default="", nargs="*",
                       help="A list of comma-separated commands to pass to " +
                       "the shell directly. " +
                       "If a script is already specified, commands " +
                       "are passed after the script"
                       )

    # TEST
    test = subp.add_parser("test",
                           help="Perform validation tests on the tool")
    test.add_argument("--number", "-n", type=int, default=-1,
                      help="The test nb to perform (default: all)")

    args = parser.parse_args()

    # Dispatch commands
    if args.cmd == "dummy":
        cli_dummy(args)
    elif args.cmd == "jsonparse":
        cli_jsonparse(args)
    elif args.cmd == "binparse":
        cli_binparse(args)
    elif args.cmd == "dump":
        cli_dump(args)
    elif args.cmd == "test":
        cli_test(args)
    elif args.cmd == "shell":
        cli_shell(args)
    else:
        # If no command passed, considered as faulty, print help
        parser.print_help()


if __name__ == "__main__":
    cli()
