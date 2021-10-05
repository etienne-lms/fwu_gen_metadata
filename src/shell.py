#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-2-Clause
#
# Copyright (c) 2021, STMicroelectronics
#

"""
    shell.py
        Interact with the fwu_metadata from an interactive / scripted shell
        To implement a command:
            - Create function do_<name>(self, inp)
                Where the actual code is situated
                o Pass "inp" into "expect_args" function

            - Create function help_<name>(self)
                Prints help message to screen

            - If this command is available for scripting (non interactive),
                add the command name into accepted_script_cmds list
"""
import os
import uuid
import json
import traceback
from cmd import Cmd

from src.uuid_t import validate_uuid
from src.structs import fwupd_from_dict, fwupd_to_dict, validate_fwupd_and_dict
from src.metadata import validate_metadata, create_dummy_metadata


def clean_exit_kb_interrupt(f):
    """ Function decorator, to provoke clean exit in CTRL + C"""
    def fct(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except KeyboardInterrupt:
            print("")
            print("Stopped")
            print("")
            return
    return fct


def ask_userinput(msg, default=None):
    """ Ask user to enter a value, mimic "default" arg type if passed"""
    if default is not None:
        usr = input(msg + " [default {}]: ".format(default))
        if usr == "":
            usr = default
        if type(default) == bool:
            return (usr == "True") or (usr == "true")
        return type(default)(usr)
    else:
        return input(msg)


def expect_args(args, nbargs, types):
    """
        Convert @args into verified, converted, minimal, arg list

        If @args is str, split into spaces
        Check if have enough args as expected by @nbargs
        Check if each arg of @args can be converted into the type passed in
            @types list
        Return list of converted values, ready to use
    """
    if isinstance(args, str):
        args = args.split()
    if len(args) < nbargs:
        raise Exception(
            "Expected at least {} arguments, got {}".format(nbargs, len(args)))
    for n, t in enumerate(types):

        if t == "fname":
            if not os.path.isfile(args[n]):
                raise Exception("File {} does not exist".format(args[n]))
        if t == "int":
            args[n] = int(args[n])
        if t == "float":
            args[n] = float(args[n])
    return args


class FwupdShell(Cmd):
    """
        Class containing all the functions and data for the shell
    """
    prompt = "fwupd> "
    intro = "Welcome ! Type ? to list the commands"

    exit_aliases = ["quit", "q", "Q", "bye"]
    accepted_script_cmds = [
        "exit", "test", "echo",
        "load", "load_binary", "load_json",
        "save", "save_binary", "save_json",
        "autodummy",
        "dump",
        "set_bank_policy", "set_active_index",
        "print_choices_uuids", "print_all_uuids",
    ]

    def __init__(self):
        Cmd.__init__(self)
        self.metadata = None    # Python dict containing human-friendly data
        self.fwupd = None       # Python class created from C struct

    def default(self, inp):
        if inp in self.exit_aliases:
            return self.do_exit(inp)

    def check_file_init(self, check_metadata=True, check_fwupd=True):
        """
            Check if internal data (self.metadata & self.fwupd) are init or not

            They can be initialized using command "load"
            Or passed through CLI via arg --binfile or --jsonfile
        """
        res = True
        if check_metadata:
            res = res and (self.metadata is not None)
        if check_fwupd:
            res = res and (self.fwupd is not None)
        return res

    def update_fwupd_struct(self):
        self.fwupd = fwupd_from_dict(self.metadata)

    # COMMANDS AVAILABLE FOR SCRIPTING
    # ECHO
    def help_echo(self):
        print('Prints a message in the shell')

    def do_echo(self, inp):
        print(inp)

    # EXIT
    def help_exit(self):
        print('Exit the shell. Shorthand: {} Ctrl-D.'.format(
            " ".join(self.exit_aliases))
        )

    def do_exit(self, inp):
        print("")
        return True

    # TEST
    def help_test(self):
        print("Test command for the shell, prints hello world and echo " +
              "the args")

    def do_test(self, inp):
        print("Hello world!")
        print(inp)

    # GET_SCRIPT_CMDS
    def help_get_script_cmds(self):
        print("Get the shell commands allowed inside a script")

    def do_get_script_cmds(self, inp):
        print("\n".join(self.accepted_script_cmds))

    # LOAD_BINARY
    def help_load_binary(self):
        print(
            "Loads a binary metadata file\n\tUsage: load <filename> " +
            "<nb_fw_imgs> <nb_banks>")

    def do_load_binary(self, inp):
        inp = expect_args(inp, 3, ["fname", "int", "int"])
        if not self.metadata:
            self.do_autodummy(inp[1:])
        self.update_fwupd_struct()
        with open(inp[0], "rb") as f:
            f.readinto(self.fwupd)
        self.metadata = fwupd_to_dict(
            self.fwupd, inp[1], inp[2], list(), dict())

    # LOAD_JSON
    def help_load_json(self):
        print("Loads a JSON metadata file\n\tUsage: load <filename>")

    def do_load_json(self, inp):
        inp = expect_args(inp, 1, ["fname"])
        with open(inp[0], "r") as f:
            self.metadata = json.load(f)
        if not validate_metadata(self.metadata):
            raise Exception("Metadata contained in file are not correct")

    # LOAD
    def help_load(self):
        print("Loads a file in memory, allows to manipulate the fields.")
        print("\tUsage: load <json/binary/pair> <args...>")
        print("\tIf the file is JSON, expect arg: <filename>")
        print("\tIf the file is binary, requires additionnal arguments: " +
              "<nb_fw_imgs> <nb_banks>")
        print("\tIf both a JSON and binary file is loaded, expect arguments:" +
              " <jsonfile> <binfile>")

    def do_load(self, inp):
        inp = expect_args(inp, 1, ["str"])
        if inp[0] == "json":
            self.do_load_json(inp[1:])
        elif inp[0] == "binary":
            self.do_load_binary(inp[1:])
        elif inp[0] == "pair":
            expect_args(inp[1:], 2, ["fname", "fname"])
            self.do_load_json(inp[1])
            self.do_load_binary(
                "{} {} {}".format(inp[2],
                                  self.metadata["configs"]["nb_fw_img"],
                                  self.metadata["configs"]["nb_fw_banks"]))
            if not validate_fwupd_and_dict(self.metadata, self.fwupd):
                raise Exception(
                    "Json metadata and binary metadata does not contain " +
                    "the same information")
        else:
            self.help_load()
            raise Exception("Wrong argument '{}'".format(inp[0]))

    # SAVE_JSON
    def help_save_json(self):
        print("Save the metadata as a JSON file\n\tUsage: save <jsonfile>")

    def do_save_json(self, inp):
        inp = expect_args(inp, 1, ["str"])
        self.check_file_init(check_fwupd=False)
        with open(inp[0], "w") as f:
            json.dump(self.metadata, f, indent=4)

    # SAVE_BINARY
    def help_save_binary(self):
        print("Save the metadata as a binary file\n\tUsage: save <binaryfile>")

    def do_save_binary(self, inp):
        inp = expect_args(inp, 1, ["str"])
        self.check_file_init(check_metadata=False)
        with open(inp[0], "wb") as f:
            f.write(self.fwupd)

    # SAVE
    def help_save(self):
        print("Save a file on the disk.\n\tUsage: save <json/binary/pair>" +
              " <filename(s)>")

    def do_save(self, inp):
        inp = expect_args(inp, 1, ["str"])
        if inp[0] == "json":
            self.do_save_json(inp[1])
        elif inp[0] == "binary":
            self.do_save_binary(inp[1])
        elif inp[0] == "pair":
            inp = expect_args(inp[1:], 2, ["str"])
            self.do_save_json(inp[0])
            self.do_save_binary(inp[1])
        else:
            raise Exception("Usage: save <json/binary> <filename>")

    # AUTODUMMY
    def help_autodummy(self):
        print("Auto-generate a dummy metadata to memory.")
        print("\tUsage: autodummy <nb_fw_imgs> <nb_banks>")

    def do_autodummy(self, inp):
        inp = expect_args(inp, 2, ["int", "int"])
        self.metadata = create_dummy_metadata(inp[0], inp[1])
        self.update_fwupd_struct()

    # DUMP
    def help_dump(self):
        print("Dump the metadata contained in memory")

    def do_dump(self, inp):
        print("--- BINARY ---")
        self.fwupd.display()
        print("--- JSON ---")
        js = json.dumps(self.metadata, indent=2)
        print(js)

    # SET_BANK_POLICY
    def help_set_bank_policy(self):
        print("Set the policy (accept / refuse) of a bank")
        print(
            "Usage: <image name / uuid> <bank number> <accept, 1," +
            " true / refuse, 0, false>")

    def do_set_bank_policy(self, inp):
        inp = expect_args(inp, 3, ["str", "str", "str"])

        if inp[0] not in self.metadata["metadata"]["img_entry"].keys():
            if inp[0] not in self.metadata["uuids"]["entries"].values():
                print("UUIDs found: {}".format(
                    ", ".join([
                        "{}={}".format(key, val)
                        for key, val in self.metadata["metadata"
                                                      ]["img_entry"].items()
                        if "_bank_" not in key
                    ])
                ))
                print("Images found: {}".format(
                    ", ".join(self.metadata["metadata"]["img_entry"].keys())))
                raise Exception(
                    "Image '{}' not found in metadata".format(inp[0]))
            else:
                inp[0] = [key for key, val in self.metadata["metadata"]
                          ["img_entry"].items() if val == inp[0]][0]

        if not inp[1].isdigit():
            raise Exception(
                "Bank has to be set by number (got '{}' which is not a number)"
                .format(inp[1]))

        if inp[0] + "_bank_" + inp[1] not in \
            self.metadata["metadata"]["img_entry"][inp[0]]["img_bank_info"
                                                           ].keys():
            print(inp[0] + "_bank_" + inp[1])
            raise Exception(
                "Bank nb°{} not found in entry {}".format(inp[1], inp[0]))

        if inp[2] in ["accept", "1", "true"]:
            self.metadata["metadata"
                          ]["img_entry"
                            ][inp[0]
                              ]["img_bank_info"
                                ][inp[0] + "_bank_" + inp[1]
                                  ]["accepted"] = True
        elif inp[2] in ["refuse", "0", "false"]:
            self.metadata["metadata"
                          ]["img_entry"
                            ][inp[0]
                              ]["img_bank_info"
                                ][inp[0] + "_bank_" + inp[1]
                                  ]["accepted"] = False
        else:
            raise Exception("Policy '{}' not recognized".format(inp[2]))
        self.update_fwupd_struct()

    # PRINT_CHOICES_UUIDS
    def help_print_choices_uuids(self):
        print("Prints the UUID of the images selected from the banks")

    def do_print_choices_uuids(self, inp):
        print("Banks {} selected".format(
            self.metadata["metadata"]["active_index"]))
        willboot = True
        for imgname, img in self.metadata["metadata"]["img_entry"].items():
            bankname = imgname + "_bank_" + \
                str(self.metadata["metadata"]["active_index"])
            accepted = img["img_bank_info"][bankname]["accepted"]
            willboot = willboot and accepted
            print("{}: {} ({})".format(imgname,
                                       self.metadata["uuids"]["entries"
                                                              ][bankname],
                                       "accepted"*(accepted) +
                                       "refused"*(not accepted))
                  )
        if not willboot:
            print("\n/!\\ This setup will not be booted")
            print("    Verify that all the banks are accepted\n")

    # PRINT_ALL_UUIDS
    def help_print_all_uuids(self):
        print("Prints the UUIDS for all the images, image types and locations")

    def do_print_all_uuids(self, inp):
        print("--- Locations ---")
        for key, uuid in self.metadata["uuids"]["locations"].items():
            print("{}: {}".format(key, uuid))

        types = list()
        print("\n--- Image types ---")
        for key, uuid in [(key, val) for key, val in
                          self.metadata["uuids"]["entries"].items()
                          if "_bank_" not in key]:
            print("{}: {}".format(key, uuid))
            types.append(key)

        print("\n--- Image banks ---")
        for t in types:
            print(" - {} banks".format(t))
            for key, uuid in [(key, val) for key, val in
                              self.metadata["uuids"]["entries"].items()
                              if t + "_bank_" in key]:
                print("\t{}: {}".format(key, uuid))
            print("")

    # SET_ACTIVE_INDEX
    def help_set_active_index(self):
        print("Changes the active_index in the metadata")

    def do_set_active_index(self, inp):
        inp = expect_args(inp, 1, ["int"])
        self.metadata["metadata"]["active_index"] = inp[0]
        self.update_fwupd_struct()


    # SET_PREVIOUS_ACTIVE_INDEX
    def help_set_previous_active_index(self):
        print("Changes the previous_active_index in the metadata")

    def do_set_previous_active_index(self, inp):
        inp = expect_args(inp, 1, ["int"])
        self.metadata["metadata"]["previous_active_index"] = inp[0]
        self.update_fwupd_struct()


    # COMMANDS AVAILABLE ONLY ON INTERACTIVE MODE
    # CREATE_METADATA
    def help_create_metadata(self):
        print("Interactive human-friendly tool to create metadata from " +
              "scratch")

    @clean_exit_kb_interrupt
    def do_create_metadata(self, inp):
        nb_fw_img = ask_userinput("The number of images entries", default=1)
        nb_banks = ask_userinput("The number of banks per image", default=2)

        print("\nFirst, enter the human-friendly names and identifiants")
        version = ask_userinput("Metadata version", default=0)
        active_index = ask_userinput("Active index", default=0)
        previous_active_index = ask_userinput(
            "Previous active index", default=0)
        images = dict()
        uuids = {"entries": {}, "locations": {}}
        for n in range(nb_fw_img):
            img_name = ask_userinput(
                "Image {} name".format(n), default="img_" + str(n))
            uuids["entries"][img_name] = None
            loc = ask_userinput("Location of image", default="sda")
            uuids["locations"][loc] = None
            images[img_name] = {"location": loc, "img_bank_info": {}}
            for b in range(nb_banks):
                accepted = ask_userinput(
                    "{} bank {} accepted".format(img_name, b), default=True)
                reserved = ask_userinput("Reserved field data", default=0)
                images[img_name]["img_bank_info"
                                 ]["{}_bank_{}".format(img_name, b)] = {
                    "accepted": accepted, "reserved": reserved}
                uuids["entries"]["{}_bank_{}".format(img_name, b)] = None

        print("\nThen, enter any known UUID for the given keys")
        print("\tType 'q' to finish")

        known = list()
        not_known = [key for key, val in uuids["entries"].items()
                     if val is None] + \
            [key for key, val in uuids["locations"].items() if val is None]

        while True:
            print("")
            print("Known: {}".format(", ".join(known)))
            print("Not known: {}".format(", ".join(not_known)))
            uuid_id = input("ID: ")
            if uuid_id == "q":
                break
            if uuid_id not in not_known + known:
                print("ID not recognized")
                continue
            uuid_str = input("UUID: ")
            if uuid_str == "q":
                break
            if not validate_uuid(uuid_str):
                print(
                    "Wrong UUID, must be of format: xxxxxxxx-xxxx-xxxx-" +
                    "xxxx-xxxxxxxxxxxx")
                continue

            if uuid_id in uuids["locations"].keys():
                uuids["locations"][uuid_id] = uuid_str
            elif uuid_id in uuids["entries"].keys():
                uuids["entries"][uuid_id] = uuid_str
            else:
                raise Exception("Unreachable")

            if uuid_id in not_known:
                index = not_known.index(uuid_id)
                known.append(not_known.pop(index))

        print("\nGenerating missing UUIDs")
        uuids["locations"].update(
            {k: str(uuid.uuid4()) for k, val in uuids["locations"].items()
                if val is None})
        uuids["entries"].update(
            {k: str(uuid.uuid4()) for k, val in uuids["entries"].items()
                if val is None})

        self.metadata = {"metadata": {
            "version": version, "active_index": active_index,
            "previous_active_index": previous_active_index,
            "img_entry": images
        },
            "uuids": uuids,
            "configs": {"nb_fw_img": nb_fw_img, "nb_fw_banks": nb_banks},
        }
        self.update_fwupd_struct()

        print("Call command 'save' to write changes to filesystem")

    do_EOF = do_exit
    help_EOF = help_exit


def start_shell(cmdlist, keep, verbose, jsonfile=None, binfile_load=None):
    shell = FwupdShell()

    # binfile_load & jsonfile arg passed as strings
    #   the same way they would have been typed as a command
    if jsonfile is not None:
        shell.do_load_json(jsonfile)
        if binfile_load is not None:
            shell.do_load_binary(binfile_load)
            validate_fwupd_and_dict(shell.metadata, shell.fwupd)
        else:
            shell.update_fwupd_struct()
    elif binfile_load is not None:
        shell.do_load_binary(binfile_load)

    # Pass each commands from script into shell
    for nbcmd, cmd in enumerate(cmdlist):
        try:
            if verbose:
                print("\n+ ", cmd.split()[0], "\t", cmd.split()[1:])
            if cmd.split()[0] not in shell.accepted_script_cmds:
                raise Exception(
                    "Command '{}' not known/allowed for scripting".format(
                        cmd.split()[0]))
            shell.onecmd(cmd)
        except Exception as err:
            traceback.print_exc()
            print(
                "\n/!\\ Exception occured, stopping script at cmd n°{}/{}"
                .format(nbcmd+1, len(cmdlist)))
            return

    # If used in interactive mode, or keep alive after script
    if keep or len(cmdlist) == 0:
        shell.cmdloop()

    # Save to files
    if jsonfile is not None:
        shell.do_save_json(jsonfile)
    if binfile_load is not None:
        shell.do_save_binary(binfile_load.split(" ")[0])
