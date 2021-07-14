# fwumd\_tool
Tool to create FWU Metadata struct in Python

## Getting started
As metadata struct composition and length changes depending on how many images and how many banks you want to put in them,
the options `--nb-img-in-banks` (or `-ni` for short) and `--nb-banks` (or `-nb` for short) may be required to format the binary data properly.
The default values are **1 image** and **2 banks**

### From Json to binary
`fwumd_tool.py dummy` will generate a file `dummy.json` and `dummy.bin`, containing
dummy metadata for testing purpose.

Modify the json file with the correct metadata you want to set, then call
`fwumd_tool.py jsonparse <json file>` to generate the binary metadata from the given json file
In both of these commands, passing option `-v` will dump the content of the metadata for visual
inspection.

**The name format `<image>_bank_<nb>` needs to be respected for images in banks**

### From binary to json
You can dump a binary metadata file using the command `fwumd_tool.py dump <binary file>` to
visualize the metadata in human-readable format from the binary.

You can also generate a json config file from binary data using the command `fwumd_tool.py binparse <binary file>`.
It will generate json data in which names are automatically generated.

Passing the option `--template <jsonfile>` to binparse allows the tool to get the config from the given json file,
and will mimic the number of images, the number of banks, and the names given to images, banks, location.

### Test reproducible binary metadata
Passing these commands should end up with matching checksum.
```bash
./fwumd_tool.py dummy
./fwumd_tool.py binparse dummy.bin -j dummy2.json
./fwumd_tool.py jsonparse dummy2.json -b dummy2.bin
shasum dummy.bin dummy2.bin
```

## Shell
Using `./fwumd_tool.py shell` allows to pass commands interactively, in standard input or using a script.
The shell is under construction for now, but a command `create_metadata` already allows to interactively create the metadata
from scratch with an assistant.

Scripts will not be allowed to use any interactive commands (expecting user input), but will have a restricted set of commands
allowed, given by the command `get_script_cmds`.

The shell has a json AND a binary version of the metadata, each of them are modified step by step with the commands, 
and saved when needed. Only when a Json file is loaded, the image names and location names are properly loaded, if not,
generic & auto-generated names will be used instead. **ALWAYS LOAD THE JSON FILE BEFORE THE BINARY FILE**

Json and binary files are validated when loaded.

### Exemples
#### Load a pair (JSON + binary) of files
```bash
./fwumd_tool.py shell -v -b dummy.bin -j dummy.json -- dump
```
This command will load the json and binary file, validate their content (will raise an error if they don't match)
and execute the command `dump` of the script, priting to screen the content of both the binary and JSON metadata.

#### Set policy (accept / refuse) on a bank
```bash
./fwumd_tool.py shell -v -b dummy.bin -- set_bank_policy 0 1 refuse
```
The option `-v` will output each line of the script before executing it.

The option `-b` is used to load a binary file before executing the script, then save the changes made to it after

`set_bank_policy 0 1 refuse` will refuse the bank n°1 of the image n°0.
If you work with image names, you can pass the image name instead.

#### Execute script
In the file "testscript":
```
# Generate the dummy data
autodummy 1 2	# 1 image, 2 banks
dump			# Display the generated data

# Set the Image img_0 (default name) bank 1 policy to "refuse"
set_bank_policy img_0 1 refuse, dump	# Double command using a comma

# Save our work into json and binary file
save pair testscript.json testscript.bin
```
Call the command `./fuwmd_tool.py shell -v -s testscript` to automatically
perform all these tasks.

Note that comments (using "#") and blank lines can be added in the script.
Severall commands can be passed in one line using comas ","


## Propositions, precepts, thoughts
- Endianness of the data contained in the struct has to either be fixed, or defined in the "configs" section of the metadata and embedded into the binary metadata
- Discussions has been made to embed configs into the binary metadata directly, allowing for much easier validation of the data and less prone to errors
- A list of wanted features to ease scripting with the tool should be made.
- PEP8 rules have been applied as much as possible on the code, as well as comments & docstrings.

## TODO
- Compute real CRC32
- Verify CRC32 of binary metadata file

## Json examples
### Dummy JSON metadata
```json
{
    "metadata": {
        "version": 0,
        "active_index": 1,
        "previous_active_index": 0,
        "img_entry": {
            "img_0": {
                "location": "sda",
                "img_bank_info": {
                    "img_0_bank_0": {
                        "accepted": true,
                        "reserved": 101
                    },
                    "img_0_bank_1": {
                        "accepted": false,
                        "reserved": 102
                    }
                }
            }
        }
    },
    "uuids": {
        "locations": {
            "sda": "7e93078a-2dc2-4657-b496-eaf638247c5b"
        },
        "entries": {
            "img_0_bank_0": "c31fe18a-9408-49b5-a647-03113b85dc58",
            "img_0_bank_1": "d4ccc9b2-58a0-46ed-beeb-1f37059db676",
            "img_0": "50833315-fe46-4eb1-8c4a-b38d03684f7f"
        }
    },
    "configs": {
        "nb_fw_img": 1,
        "nb_fw_banks": 2
    }
}
```
