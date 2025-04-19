import json
import urllib
import random

from owlready2 import *
from timeit import default_timer as timer

section_names = []
api_actions = {}

ember_malware = []
ember_benign = []

rng = random.SystemRandom()

training_subset = 0.8
entropy_threshold = 7.0
imports_threshold = 10
# fold = 5
def generate_folds(examples_path, output_path, dataset_name, folds = 1):
    print("[*] Generating ", folds, " folds")

    examples = {}

    try:
        with open(examples_path, "r") as file:
            examples = json.load(file)
        print("JSON file loaded successfully!")
    except OSError:
        print("[*] Failed to open file: ", examples_path)
        
    # Check if the 'positive' and 'negative' keys exist in the examples dictionary
    if "positive" not in examples or "negative" not in examples:
        print("[*] Error: 'positive' or 'negative' key missing in examples data.")
        return  # Early return if the required keys are missing
    
    positive_size = len(examples["positive"])
    negative_size = len(examples["negative"])
    chunk_size = max(1, int(((positive_size + negative_size) / folds) / 2))

    #chunk_size = int(((positive_size + negative_size) / folds) / 2)

    positive_chunks = []
    negative_chunks = []

    for i in range(0, positive_size, chunk_size):
        #positive_chunks.append(examples["positive"][i:i+100])
        positive_chunks.append(examples["positive"][i:i+chunk_size])

    for i in range(0, negative_size, chunk_size):
        #negative_chunks.append(examples["negative"][i:i+100])
        negative_chunks.append(examples["negative"][i:i+chunk_size])

    for i in range(0, folds):
        print("[*] Generating fold: ", str(i + 1))

        positive_testing = positive_chunks[i]
        negative_testing = negative_chunks[i]

        positive_training = positive_chunks.copy()
        del positive_training[i]
        positive_training = sum(positive_training, [])

        negative_training = negative_chunks.copy()
        del negative_training[i]
        negative_training = sum(negative_training, [])

        config_file = open(output_path + "/" + dataset_name + "_fold_" + str(i + 1) + ".conf", "w")

        # positive training
        config_file.write("lp.positiveExamples = {\n")
        for i in range(0, len(positive_training)):
            if i != len(positive_training) - 1:
                config_file.write("\"" + positive_training[i] + "\",\n")
            else:
                config_file.write("\"" + positive_training[i] + "\"}\n\n")

        # positive testing
        config_file.write("lp.testPositiveExamples = {\n")
        for i in range(0, len(positive_testing)):
            if i != len(positive_testing) - 1:
                config_file.write("\"" + positive_testing[i] + "\",\n")
            else:
                config_file.write("\"" + positive_testing[i] + "\"}\n\n")

        # negative training
        config_file.write("lp.negativeExamples = {\n")
        for i in range(0, len(negative_training)):
            if i != len(negative_training) - 1:
                config_file.write("\"" + negative_training[i] + "\",\n")
            else:
                config_file.write("\"" + negative_training[i] + "\"}\n\n")

        # negative testing
        config_file.write("lp.testNegativeExamples = {\n")
        for i in range(0, len(negative_testing)):
            if i != len(negative_testing) - 1:
                config_file.write("\"" + negative_testing[i] + "\",\n")
            else:
                config_file.write("\"" + negative_testing[i] + "\"}\n\n")
        
        config_file.close()

def load_actions(path):
    global api_actions 

    try:
        with open(path) as file:
            api_actions = json.loads(file.read())
    except OSError:
        print("[*] Failed to open file: ", path)

def has_api_action(imports, action):
    for dll in imports:
        for func in imports[dll]:
            for adtf in api_actions[action]:
                f = func.lower()
                if f.find(adtf) != -1:
                    return True
    return False

def count_imports(imports):
    count = 0

    for dll in imports:
        for func in imports[dll]:
            count += 1
    
    return count

def load_section_names(path):
    try:
        with open(path) as file:
            data = json.loads(file.read())

            for section_name in data["names"]:
                section_names.append(section_name)
    except OSError:
        print("[*] Failed to open file: ", path)

def generate_training_sets(path, malware_p, benign_p, train_total):
    file = open(path)
    entries = file.readlines()

    malware_total = train_total * malware_p
    benign_total = train_total * benign_p
    malware_count = 0
    benign_count = 0
    train = []

    for i in range(0, len(entries)):
        sample = json.loads(entries[i])

        if (malware_count + benign_count) < (malware_total + benign_total):
            if sample["label"] == 1 and malware_count < malware_total:
                train.append(entries[i])
                malware_count += 1
            if sample["label"] == 0 and benign_count < benign_total:
                train.append(entries[i])
                benign_count += 1

        if len(train) == train_total:
            break
    
    file = open("train.json", "w")
    for sample in train:
        file.write(sample)
    file.close()

def generate_datasets(malware_p, benign_p, total, dataset_count, ember_benign, ember_malware):
    malware_total = int(total * malware_p)
    benign_total = int(total * benign_p)
    
    #Initialize random number generator
    rng = random.Random()

    datasets = {}

    for i in range(1, dataset_count + 1):
        print("[*] Generating ", str(i), "th dataset of size ", str(total))
        print(f"Size of ember_benign: {len(ember_benign)}")
        print(f"Requested sample size (benign_total): {benign_total}")
        print(f"Size of ember_malware: {len(ember_malware)}")
        print(f"Requested sample size (malware_total): {malware_total}")
        
        # Ensure that the sample size does not exceed the population size
        benign_total = min(benign_total, len(ember_benign))
        malware_total = min(malware_total, len(ember_malware))
        
        # Check if the total requested samples are valid (non-negative and non-zero)
        if benign_total <= 0 or malware_total <= 0:
            raise ValueError("Sample size must be greater than 0 for benign or malware samples")

        # Sample from the benign and malware datasets
        benign_samples = rng.sample(ember_benign, benign_total)
        malware_samples = rng.sample(ember_malware, malware_total)
        
        # Combine the benign and malware samples and shuffle them
        final_dataset = benign_samples + malware_samples
        rng.shuffle(final_dataset)
        
        # Store the generated dataset
        datasets[i] = final_dataset
    
    return datasets

def load_dataset(path):
    datasets = {}

    print("[*] Loading dataset: ", path)

    with open(path) as file:
        print("[*] Loading file ", path)
        entries = file.readlines()
        datasets[0] = entries
    
    print("[*] Loading finished")

    return datasets
    
def check_individual(individual, section_name = False):
    individual = individual.replace("<", "")
    individual = individual.replace(">", "")
    individual = individual.lower()

    if section_name:
        individual = individual.replace(".", "")

    return urllib.parse.quote(individual)

def write_pos_neg_examples(malware, benign, save_path, dataset_name):
    data = {}
    positive = []
    negative = []

    # positive samples
    for sample in malware:
        positive.append("ex:" + sample)

    for sample in benign:
        negative.append("ex:" + sample)

    data["positive"] = positive
    data["negative"] = negative

    json_data = json.dumps(data, indent=4)
    output_file = open(save_path + "/" + dataset_name + "_examples.json", "w")
    output_file.write(json_data)
    output_file.close()

def check_section_entropy(section):
    if section["entropy"] >= entropy_threshold:
        return True
    else:
        return False

def check_section_name(section):
    section_name = section["name"].lower()

    for sn in section_names:
        if section_name.find(sn) != -1:
            return True
    
    return False

def check_section_wx(section):
    write = False
    execute = False

    for prop in section["props"]:
        if prop == "MEM_WRITE":
            write = True
        if prop == "MEM_EXECUTE":
            execute = True
    
    if write and execute:
        return True
    else:
        return False

def check_section_property(section, p):
    for prop in section["props"]:
       if prop == p:
           return True
    
    return False

def check_entry_point(entry, sections):
    for section in sections:
        if section["name"] == entry:
            for prop in section["props"]:
                if prop == "MEM_EXECUTE":
                    return True
    
    return False

def executable_sections(sections):
    count = 0

    for section in sections:
        for prop in section["props"]:
            if prop == "MEM_EXECUTE":
                count += 1
    
    return count

def check_characteristic(characteristics, char):
    for c in characteristics:
        if c == char:
            return True
    
    return False

def load_ember(paths):
    print("[*] Loading EMBER dataset")
    for path in paths:
        with open(path) as file:
            print("[*] Loading file ", path)
            entries = file.readlines()

            for i in range(0, len(entries)):
                sample = json.loads(entries[i])
                label = sample["label"]

                if label == 0:
                    ember_benign.append(entries[i])
                if label == 1:
                    ember_malware.append(entries[i])
    
    print("[*] Loading finished")
    print("[*] Benign samples: ", str(len(ember_benign)), " Malware samples: ", str(len(ember_malware)))
    print("[*] Shuffling...")

    rng.shuffle(ember_benign)
    rng.shuffle(ember_malware)

def map_to_ontology(dataset, ot, save_path, dataset_name):
    start = timer()

    malware = []
    benign = []

    raw_file = open(save_path + "/" + dataset_name + "_raw.json", "w")
    for sample in dataset:
        raw_file.write(sample)
    raw_file.close()

    print("[*] Ontology mapping: ", dataset_name)

    '''for i in range(0, len(dataset)):
        sample = json.loads(dataset[i])'''
    for i in range(0, len(dataset)):
        data = dataset[i]
        print(f"Loading dataset entry {i}: {data}")  # Log data to check
        
        # Check if the data is empty or contains only whitespace
        if not data.strip():  
            print(f"Warning: Skipping empty dataset entry at index {i}")
            continue

        try:
            # Attempt to parse the JSON data
            sample = json.loads(data)
        except json.decoder.JSONDecodeError as e:
            # Handle JSON parsing error and skip this entry
            print(f"Error parsing JSON at index {i}: {e}")
            continue

        
        label = sample["label"]
        pe_hash = sample["md5"]

        # PE_FILE
        is_dll = False
        if check_characteristic(sample["header"]["coff"]["characteristics"], "DLL"):
            is_dll = True

        if label == 0:
            benign.append(pe_hash)
            
            if is_dll:
                pe_file = ot.DynamicLinkLibrary(pe_hash)
            else:
                pe_file = ot.ExecutableFile(pe_hash)
        elif label == 1:
            malware.append(pe_hash)
            
            if is_dll:
                pe_file = ot.DynamicLinkLibrary(pe_hash)
            else:
                pe_file = ot.ExecutableFile(pe_hash)
        else:
            continue

        features = []

        # STRINGS
        if sample["strings"]["MZ"] > 1:
            features.append(ot.NonstandardMZ("nonstandard_mz"))
        if sample["strings"]["paths"] > 0:
            features.append(ot.PathStrings("path_strings"))
        if sample["strings"]["urls"] > 0:
            features.append(ot.URLStrings("url_strings"))
        if sample["strings"]["registry"] > 0:
            features.append(ot.RegistryStrings("registry_strings"))
        
        # STRING DATA PROPERTIES
        pe_file.mz_count = [int(sample["strings"]["MZ"])]
        pe_file.path_strings_count = [int(sample["strings"]["paths"])]
        pe_file.url_strings_count = [int(sample["strings"]["urls"])]
        pe_file.registry_strings_count = [int(sample["strings"]["registry"])]

        # GENERAL
        if sample["general"]["has_signature"] == 1:
            features.append(ot.Signature("signature"))
        if sample["general"]["has_debug"] == 1:
            features.append(ot.Debug("debug") )
        if sample["general"]["has_tls"] == 1:
            features.append(ot.TLS("tls"))
        if sample["general"]["symbols"] > 0:
            features.append(ot.Symbols("symbols"))
        if sample["general"]["has_relocations"] == 1:
            features.append(ot.Relocations("relocations"))
        if sample["general"]["has_resources"] == 1:
            features.append(ot.Resources("resources"))
        if sample["general"]["exports"] > 0:
            features.append(ot.Exports("exports"))

        # GENERAL DATA PROPERTIES
        pe_file.exports_count = [int(sample["general"]["exports"])]
        pe_file.imports_count = [int(sample["general"]["imports"])]
        pe_file.symbols_count = [int(sample["general"]["symbols"])]

        # SECTIONS
        sections = []
        
        if check_entry_point(sample["section"]["entry"], sample["section"]["sections"]) == False:
            features.append(ot.NonexecutableEntryPoint("nonexecutable_entry_point"))

        if executable_sections(sample["section"]["sections"]) > 1:
            features.append(ot.MultipleExecutableSections("multiple_executable_sections"))

        for s in sample["section"]["sections"]:
            section_features = []
            section_flags = []
            s_name = check_individual(s["name"], True)
            s_entropy = float(s["entropy"])

            if check_section_property(s, "CNT_CODE"):
                new_section = ot.CodeSection(s_name + "_" + pe_hash)
            elif check_section_property(s, "CNT_INITIALIZED_DATA"):
                new_section = ot.InitializedDataSection(s_name + "_" + pe_hash)
            elif check_section_property(s, "CNT_UNINITIALIZED_DATA"):
                new_section = ot.UninitializedDataSection(s_name + "_" + pe_hash)
            else:
                # special cases

                # resource section with no content flag -> assume initialized data
                if s_name == '.rsrc':
                    new_section = ot.InitializedDataSection(s_name + "_" + pe_hash)

            if check_section_property(s, "MEM_EXECUTE"):
                section_flags.append(ot.Executable("executable"))
            if check_section_property(s, "MEM_WRITE"):
                section_flags.append(ot.Writable("writable"))
            if check_section_property(s, "MEM_READ"):
                section_flags.append(ot.Readable("readable"))
            if check_section_property(s, "MEM_SHARED"):
                section_flags.append(ot.Shareable("shareable"))

            new_section.section_entropy = [s_entropy]
            new_section.section_name = [s_name]

            if check_section_entropy(s):
                section_features.append(ot.HighEntropy("high_entropy"))
            if check_section_name(s) == False:
                section_features.append(ot.NonstandardSectionName("nonstandard_section_name"))
            if check_section_wx(s):
                section_features.append(ot.WriteExecuteSection("write_execute_section"))
            
            new_section.has_section_feature = section_features
            new_section.has_section_flag = section_flags

            sections.append(new_section)
        
        pe_file.has_section = sections

        # IMPORTS
        actions = []

        if sample["general"]["imports"] < imports_threshold:
            features.append(ot.LowImportsCount("low_imports_count"))

        # ACCESS MANAGEMENT
        if has_api_action(sample["imports"], "add-user"):
            actions.append(ot.AddUser("add-user"))
        if has_api_action(sample["imports"], "change-password"):
            actions.append(ot.ChangePassword("change-password"))
        if has_api_action(sample["imports"], "delete-user"):
            actions.append(ot.DeleteUser("delete-user"))
        if has_api_action(sample["imports"], "enumerate-users"):
            actions.append(ot.EnumerateUsers("enumerate-users"))
        if has_api_action(sample["imports"], "get-username"):
            actions.append(ot.GetUsername("get-username"))
        if has_api_action(sample["imports"], "logon-as-user"):
            actions.append(ot.LogonAsUser("logon-as-user"))
        if has_api_action(sample["imports"], "remove-user-from-group"):
            actions.append(ot.RemoveUserFromGroup("remove-user-from-group"))

        # ANTI DEBUGGING
        if has_api_action(sample["imports"], "check-for-kernel-debugger"):
            actions.append(ot.CheckForKernelDebugger("check-for-kernel-debugger"))
        if has_api_action(sample["imports"], "check-for-remote-debugger"):
            actions.append(ot.CheckForRemoteDebugger("check-for-remote-debugger"))
        if has_api_action(sample["imports"], "output-debug-string"):
            actions.append(ot.OutputDebugString("output-debug-string"))

        # CRYPTOGRAPHY
        if has_api_action(sample["imports"], "encrypt"):
            actions.append(ot.Encrypt("encrypt"))
        if has_api_action(sample["imports"], "decrypt"):
            actions.append(ot.Decrypt("decrypt"))
        if has_api_action(sample["imports"], "generate-key"):
            actions.append(ot.GenerateKey("generate-key"))

        # DIRECTORY HANDLING
        if has_api_action(sample["imports"], "delete-directory"):
            actions.append(ot.DeleteDirectory("delete-directory"))
        if has_api_action(sample["imports"], "monitor-directory"):
            actions.append(ot.MonitorDirectory("monitor-directory"))
        if has_api_action(sample["imports"], "open-directory"):
            actions.append(ot.OpenDirectory("open-directory"))
        if has_api_action(sample["imports"], "create-directory"):
            actions.append(ot.CreateDirectory("create-directory"))

        # DISK MANAGEMENT
        if has_api_action(sample["imports"], "enumerate-disks"):
            actions.append(ot.EnumerateDisks("enumerate-disks"))
        if has_api_action(sample["imports"], "get-disk-attributes"):
            actions.append(ot.GetDiskAttributes("get-disk-attributes"))
        if has_api_action(sample["imports"], "get-disk-type"):
            actions.append(ot.GetDiskType("get-disk-type"))
        if has_api_action(sample["imports"], "mount-disk"):
            actions.append(ot.MountDisk("mount-disk"))
        if has_api_action(sample["imports"], "unmount-disk"):
            actions.append(ot.UnmountDisk("unmount-disk"))

        # FILE HANDLING
        if has_api_action(sample["imports"], "close-file"):
            actions.append(ot.CloseFile("close-file"))
        if has_api_action(sample["imports"], "copy-file"):
            actions.append(ot.CopyFile("copy-file"))
        if has_api_action(sample["imports"], "create-file"):
            actions.append(ot.CreateFile("create-file"))
        if has_api_action(sample["imports"], "create-file-mapping"):
            actions.append(ot.CreateFileMapping("create-file-mapping"))
        if has_api_action(sample["imports"], "create-file-symbolic-link"):
            actions.append(ot.CreateFileSymbolicLink("create-file-symbolic-link"))
        if has_api_action(sample["imports"], "delete-file"):
            actions.append(ot.DeleteFile("delete-file"))
        if has_api_action(sample["imports"], "download-file"):
            actions.append(ot.DownloadFile("download-file"))
        if has_api_action(sample["imports"], "execute-file"):
            actions.append(ot.ExecuteFile("execute-file"))
        if has_api_action(sample["imports"], "find-file"):
            actions.append(ot.FindFile("find-file"))
        if has_api_action(sample["imports"], "get-file-or-directory-attributes"):
            actions.append(ot.GetFileOrDirectoryAttributes("get-file-or-directory-attributes"))
        if has_api_action(sample["imports"], "get-temporary-files-directory"):
            actions.append(ot.GetTemporaryFilesDirectory("get-temporary-files-directory"))
        if has_api_action(sample["imports"], "lock-file"):
            actions.append(ot.LockFile("lock-file"))
        if has_api_action(sample["imports"], "map-file-into-process"):
            actions.append(ot.MapFileIntoProcess("map-file-into-process"))
        if has_api_action(sample["imports"], "move-file"):
            actions.append(ot.MoveFile("move-file"))
        if has_api_action(sample["imports"], "open-file-mapping"):
            actions.append(ot.OpenFileMapping("open-file-mapping"))
        if has_api_action(sample["imports"], "read-from-file"):
            actions.append(ot.ReadFromFile("read-from-file"))
        if has_api_action(sample["imports"], "set-file-or-directory-attributes"):
            actions.append(ot.SetFileOrDirectoryAttributes("set-file-or-directory-attributes"))
        if has_api_action(sample["imports"], "unlock-file"):
            actions.append(ot.UnlockFile("unlock-file"))
        if has_api_action(sample["imports"], "unmap-file-from-process"):
            actions.append(ot.UnmapFileFromProcess("unmap-file-from-process"))
        if has_api_action(sample["imports"], "write-to-file"):
            actions.append(ot.WriteToFile("write-to-file"))

        # INTER PROCESS COMMUNICATION
        if has_api_action(sample["imports"], "connect-to-named-pipe"):
            actions.append(ot.ConnectToNamedPipe("connect-to-named-pipe"))
        if has_api_action(sample["imports"], "create-mailslot"):
            actions.append(ot.CreateMailslot("create-mailslot"))
        if has_api_action(sample["imports"], "create-named-pipe"):
            actions.append(ot.CreateNamedPipe("create-named-pipe"))
        
        # LIBRARY HANDLING
        if has_api_action(sample["imports"], "enumerate-libraries"):
            actions.append(ot.EnumerateLibraries("enumerate-libraries"))
        if has_api_action(sample["imports"], "free-library"):
            actions.append(ot.FreeLibrary("free-library"))
        if has_api_action(sample["imports"], "get-function-address"):
            actions.append(ot.GetFunctionAddress("get-function-address"))
        if has_api_action(sample["imports"], "load-library"):
            actions.append(ot.LoadLibrary("load-library"))

        # NETWORKING
        if has_api_action(sample["imports"], "accept-socket-connection"):
            actions.append(ot.AcceptSocketConnection("accept-socket-connection"))
        if has_api_action(sample["imports"], "bind-address-to-socket"):
            actions.append(ot.BindAddressToSocket("bind-address-to-socket"))
        if has_api_action(sample["imports"], "close-socket"):
            actions.append(ot.CloseSocket("close-socket"))
        if has_api_action(sample["imports"], "connect-to-ftp-server"):
            actions.append(ot.ConnectToFtpServer("connect-to-ftp-server"))
        if has_api_action(sample["imports"], "connect-to-socket"):
            actions.append(ot.ConnectToSocket("connect-to-socket"))
        if has_api_action(sample["imports"], "connect-to-url"):
            actions.append(ot.ConnectToUrl("connect-to-url"))
        if has_api_action(sample["imports"], "create-socket"):
            actions.append(ot.CreateSocket("create-socket"))
        if has_api_action(sample["imports"], "get-host-by-address"):
            actions.append(ot.GetHostByAddress("get-host-by-address"))
        if has_api_action(sample["imports"], "get-host-by-name"):
            actions.append(ot.GetHostByName("get-get-host-by-name"))
        if has_api_action(sample["imports"], "listen-on-socket"):
            actions.append(ot.ListenOnSocket("listen-on-socket"))
        if has_api_action(sample["imports"], "send-data-on-socket"):
            actions.append(ot.SendDataOnSocket("send-data-on-socket"))
        if has_api_action(sample["imports"], "send-dns-query"):
            actions.append(ot.SendDnsQuery("send-dns-query"))
        if has_api_action(sample["imports"], "send-http-connect-request"):
            actions.append(ot.SendHttpConnectRequest("send-http-connect-request"))
        if has_api_action(sample["imports"], "send-icmp-request"):
            actions.append(ot.SendIcmpRequest("send-icmp-request"))
        if has_api_action(sample["imports"], "receive-data-on-socket"):
            actions.append(ot.ReceiveDataOnSocket("receive-data-on-socket"))
        if has_api_action(sample["imports"], "send-http-request"):
            actions.append(ot.SendHttpRequest("send-http-request"))
        if has_api_action(sample["imports"], "send-ftp-command"):
            actions.append(ot.SendFtpCommand("send-ftp-command"))

        # PROCESS HANDLING
        if has_api_action(sample["imports"], "allocate-process-virtual-memory"):
            actions.append(ot.AllocateProcessVirtualMemory("allocate-process-virtual-memory"))
        if has_api_action(sample["imports"], "create-process"):
            actions.append(ot.CreateProcess("create-process"))
        if has_api_action(sample["imports"], "impersonate-process"):
            actions.append(ot.ImpersonateProcess("impersonate-process"))
        if has_api_action(sample["imports"], "create-process-as-user"):
            actions.append(ot.CreateProcessAsUser("create-process-as-user"))
        if has_api_action(sample["imports"], "enumerate-processes"):
            actions.append(ot.EnumerateProcesses("enumerate-processes"))
        if has_api_action(sample["imports"], "flush-process-instruction-cache"):
            actions.append(ot.FlushProcessInstructionCache("flush-process-instruction-cache"))
        if has_api_action(sample["imports"], "free-process-virtual-memory"):
            actions.append(ot.FreeProcessVirtualMemory("free-process-virtual-memory"))
        if has_api_action(sample["imports"], "get-process-current-directory"):
            actions.append(ot.GetProcessCurrentDirectory("get-process-current-directory"))
        if has_api_action(sample["imports"], "get-process-environment-variable"):
            actions.append(ot.GetProcessEnvironmentVariable("get-process-environment-variable"))
        if has_api_action(sample["imports"], "get-process-startupinfo"):
            actions.append(ot.GetProcessStartupinfo("get-process-startupinfo"))
        if has_api_action(sample["imports"], "kill-process"):
            actions.append(ot.KillProcess("kill-process"))
        if has_api_action(sample["imports"], "modify-process-virtual-memory-protection"):
            actions.append(ot.ModifyProcessVirtualMemoryProtection("modify-process-virtual-memory-protection"))
        if has_api_action(sample["imports"], "open-process"):
            actions.append(ot.OpenProcess("open-process"))
        if has_api_action(sample["imports"], "read-from-process-memory"):
            actions.append(ot.ReadFromProcessMemory("read-from-process-memory"))
        if has_api_action(sample["imports"], "set-process-current-directory"):
            actions.append(ot.SetProcessCurrentDirectory("set-process-current-directory"))
        if has_api_action(sample["imports"], "set-process-environment-variable"):
            actions.append(ot.SetProcessEnvironmentVariable("set-process-environment-variable"))
        if has_api_action(sample["imports"], "sleep-process"):
            actions.append(ot.SleepProcess("sleep-process"))
        if has_api_action(sample["imports"], "write-to-process-memory"):
            actions.append(ot.WriteToProcessMemory("write-to-process-memory"))

        # REGISTRY HANDLING
        if has_api_action(sample["imports"], "close-registry-key"):
            actions.append(ot.CloseRegistryKey("close-registry-key"))
        if has_api_action(sample["imports"], "create-registry-key"):
            actions.append(ot.CreateRegistryKey("create-registry-key"))
        if has_api_action(sample["imports"], "create-registry-key-value"):
            actions.append(ot.CreateRegistryKeyValue("create-registry-key-value"))
        if has_api_action(sample["imports"], "delete-registry-key-value"):
            actions.append(ot.DeleteRegistryKeyValue("delete-registry-key-value"))
        if has_api_action(sample["imports"], "delete-registry-key"):
            actions.append(ot.DeleteRegistryKey("delete-registry-key"))
        if has_api_action(sample["imports"], "enumerate-registry-key-subkeys"):
            actions.append(ot.EnumerateRegistryKeySubkeys("enumerate-registry-key-subkeys"))
        if has_api_action(sample["imports"], "enumerate-registry-key-values"):
            actions.append(ot.EnumerateRegistryKeyValues("enumerate-registry-key-values"))
        if has_api_action(sample["imports"], "modify-registry-key"):
            actions.append(ot.ModifyRegistryKey("modify-registry-key"))
        if has_api_action(sample["imports"], "monitor-registry-key"):
            actions.append(ot.MonitorRegistryKey("monitor-registry-key"))
        if has_api_action(sample["imports"], "open-registry-key"):
            actions.append(ot.OpenRegistryKey("open-registry-key"))
        if has_api_action(sample["imports"], "read-registry-key-value"):
            actions.append(ot.ReadRegistryKeyValue("read-registry-key-value"))

        # RESOURCE SHARING
        if has_api_action(sample["imports"], "add-network-share"):
            actions.append(ot.AddNetworkShare("add-network-share"))
        if has_api_action(sample["imports"], "delete-network-share"):
            actions.append(ot.DeleteNetworkShare("delete-network-share"))
        if has_api_action(sample["imports"], "enumerate-network-shares"):
            actions.append(ot.EnumerateNetworkShares("enumerate-network-shares"))

        # SERVICE HANDLING
        if has_api_action(sample["imports"], "create-service"):
            actions.append(ot.CreateService("create-service"))
        if has_api_action(sample["imports"], "delete-service"):
            actions.append(ot.DeleteService("delete-service"))
        if has_api_action(sample["imports"], "enumerate-services"):
            actions.append(ot.EnumerateServices("enumerate-services"))
        if has_api_action(sample["imports"], "modify-service-configuration"):
            actions.append(ot.ModifyServiceConfiguration("modify-service-configuration"))
        if has_api_action(sample["imports"], "open-service"):
            actions.append(ot.OpenService("open-service"))
        if has_api_action(sample["imports"], "start-service"):
            actions.append(ot.StartService("start-service"))
        if has_api_action(sample["imports"], "stop-service"):
            actions.append(ot.StopService("stop-service"))

        # SYNCHRONIZATION PRIMITIVES HANDLING
        if has_api_action(sample["imports"], "create-critical-section"):
            actions.append(ot.CreateCriticalSection("create-critical-section"))
        if has_api_action(sample["imports"], "create-event"):
            actions.append(ot.CreateEvent("create-event"))
        if has_api_action(sample["imports"], "create-mutex"):
            actions.append(ot.CreateMutex("create-mutex"))
        if has_api_action(sample["imports"], "create-semaphore"):
            actions.append(ot.CreateSemaphore("create-semaphore"))
        if has_api_action(sample["imports"], "delete-critical-section"):
            actions.append(ot.DeleteCriticalSection("delete-critical-section"))
        if has_api_action(sample["imports"], "open-critical-section"):
            actions.append(ot.OpenCriticalSection("open-critical-section"))
        if has_api_action(sample["imports"], "open-event"):
            actions.append(ot.OpenEvent("open-event"))
        if has_api_action(sample["imports"], "open-mutex"):
            actions.append(ot.OpenMutex("open-mutex"))
        if has_api_action(sample["imports"], "open-semaphore"):
            actions.append(ot.OpenSemaphore("open-semaphore"))
        if has_api_action(sample["imports"], "release-critical-section"):
            actions.append(ot.ReleaseCriticalSection("release-critical-section"))
        if has_api_action(sample["imports"], "release-mutex"):
            actions.append(ot.ReleaseMutex("release-mutex"))
        if has_api_action(sample["imports"], "release-semaphore"):
            actions.append(ot.ReleaseSemaphore("release-semaphore"))
        if has_api_action(sample["imports"], "reset-event"):
            actions.append(ot.ResetEvent("reset-event"))

        # SYSTEM MANIPULATION
        if has_api_action(sample["imports"], "add-scheduled-task"):
            actions.append(ot.AddScheduledTask("add-scheduled-task"))
        if has_api_action(sample["imports"], "get-elapsed-system-up-time"):
            actions.append(ot.GetElapsedSystemUpTime("get-elapsed-system-up-time"))
        if has_api_action(sample["imports"], "get-netbios-name"):
            actions.append(ot.GetNetbiosName("get-netbios-name"))
        if has_api_action(sample["imports"], "get-system-global-flags"):
            actions.append(ot.GetSystemGlobalFlags("get-system-global-flags"))
        if has_api_action(sample["imports"], "get-system-time"):
            actions.append(ot.GetSystemTime("get-system-time"))
        if has_api_action(sample["imports"], "get-windows-directory"):
            actions.append(ot.GetWindowsDirectory("get-windows-directory"))
        if has_api_action(sample["imports"], "get-windows-system-directory"):
            actions.append(ot.GetWindowsSystemDirectory("get-windows-system-directory"))
        if has_api_action(sample["imports"], "set-netbios-name"):
            actions.append(ot.SetNetbiosName("set-netbios-name"))
        if has_api_action(sample["imports"], "set-system-time"):
            actions.append(ot.SetSystemTime("set-system-time"))
        if has_api_action(sample["imports"], "shutdown-system"):
            actions.append(ot.ShutdownSystem("shutdown-system"))
        if has_api_action(sample["imports"], "unload-driver"):
            actions.append(ot.UnloadDriver("unload-driver"))
        if has_api_action(sample["imports"], "get-system-local-time"):
            actions.append(ot.GetSystemLocalTime("get-system-local-time"))

        # THREAD HANDLING
        if has_api_action(sample["imports"], "create-remote-thread-in-process"):
            actions.append(ot.CreateRemoteThreadInProcess("create-remote-thread-in-process"))
        if has_api_action(sample["imports"], "create-thread"):
            actions.append(ot.CreateThread("create-thread"))
        if has_api_action(sample["imports"], "enumerate-threads"):
            actions.append(ot.EnumerateThreads("enumerate-threads"))
        if has_api_action(sample["imports"], "get-thread-context"):
            actions.append(ot.GetThreadContext("get-thread-context"))
        if has_api_action(sample["imports"], "kill-thread"):
            actions.append(ot.KillThread("kill-thread"))
        if has_api_action(sample["imports"], "queue-apc-in-thread"):
            actions.append(ot.QueueApcInThread("queue-apc-in-thread"))
        if has_api_action(sample["imports"], "revert-thread-to-self"):
            actions.append(ot.RevertThreadToSelf("revert-thread-to-self"))
        if has_api_action(sample["imports"], "set-thread-context"):
            actions.append(ot.SetThreadContext("set-thread-context"))

        # WINDOW HANDLING
        if has_api_action(sample["imports"], "add-windows-hook"):
            actions.append(ot.AddWindowsHook("add-windows-hook"))
        if has_api_action(sample["imports"], "create-dialog-box"):
            actions.append(ot.CreateDialogBox("create-dialog-box"))
        if has_api_action(sample["imports"], "create-window"):
            actions.append(ot.CreateWindow("create-window"))
        if has_api_action(sample["imports"], "enumerate-windows"):
            actions.append(ot.EnumerateWindows("enumerate-windows"))
        if has_api_action(sample["imports"], "find-window"):
            actions.append(ot.FindWindow("find-window"))
        if has_api_action(sample["imports"], "kill-window"):
            actions.append(ot.KillWindow("kill-window"))
        if has_api_action(sample["imports"], "show-window"):
            actions.append(ot.ShowWindow("show-window"))
        
        #DATA DIRECTORIES
        for directory in sample["datadirectories"]:
            if directory["name"] == "CLR_RUNTIME_HEADER" and directory["size"] > 0:
                clr = ot.CLR("clr")
                features.append(clr)

        pe_file.has_file_feature = features
        pe_file.has_action = actions

    end = timer()
    print("[*] Ontology mapping finished")
    print("[*] Total time: ")
    print(end - start)

    write_pos_neg_examples(malware, benign, save_path, dataset_name)

def map_ontology(ontology_path, ontology_name, dataset, save_path, dataset_name):
    onto_path.append(ontology_path)
    ot = owlready2.get_ontology(ontology_name)
    ot.load()
    map_to_ontology(dataset, ot, save_path, dataset_name)
    path = save_path + "/" + dataset_name + ".owl"
    ot.save(file = path)

    for individual in owlready2.default_world.individuals():
        owlready2.destroy_entity(individual)

def clear_ontology(ontology_path, ontology_name):
    print("[*] Clearing ontology")
    f = open(ontology_path + "/" + ontology_name, "r")
    data = f.read()
    f.close()

    data = data.replace(u'\x02', '')
    data = data.replace(u'\x16', '')

    f = open(ontology_path + "/" + ontology_name, "w")
    f.write(data)
    f.close()

def create_ontology_dataset(path, name, dataset, dataset_name, save_path):
    map_ontology(path, name, dataset, save_path, dataset_name)
    clear_ontology(save_path, dataset_name + ".owl")

set_datatype_iri(float, "http://www.w3.org/2001/XMLSchema#double")

ontology_path = r"/home/user007/Downloads/ml_files/pe-malware-ontology-main/pe_malware_ontology.owl"
ontology_name = "pe_malware_ontology.owl"
output_path = r"/home/user007/Downloads/ml_files/pe-malware-ontology-main/ontologies1"

load_actions("actions.json")
load_section_names("section_names.json")

'''
# loading EMBER dataset

ember_paths = []

ember_paths.append("./ember2018/train_features_0.jsonl")
ember_paths.append("./ember2018/train_features_1.jsonl")
ember_paths.append("./ember2018/train_features_2.jsonl")
ember_paths.append("./ember2018/train_features_3.jsonl")
ember_paths.append("./ember2018/train_features_4.jsonl")
ember_paths.append("./ember2018/train_features_5.jsonl")
ember_paths.append("./ember2018/test_features.jsonl")

load_ember(ember_paths)
'''

'''
# generate fractional datasets

dataset = generate_datasets(0.5, 0.5, 1000, 10)
for num, d in dataset.items():
    create_ontology_dataset(ontology_path, ontology_name, d, "dataset_" + str(num) + "_1000", output_path)
'''

'''
# regenerate ontology from specific samples

dataset = load_dataset("./example/dataset_8_1000_raw.json")

for num, d in dataset.items():
    create_ontology_dataset(ontology_path, ontology_name, d, "test", output_path)
'''

'''
# generate folds from examples file
generate_folds("/path/to/examples.json", "output_path", "dataset_name")
'''
#define path to your dataset
dataset_path = r"/home/user007/Downloads/ml_files/pe-malware-ontology-main/example1/sample_examples.json"


# Load the dataset.json file
try:
    with open(dataset_path, 'r') as f:
        data = json.load(f)
        print("Dataset loaded successfully")
        print("Dataset contents:", data)
except FileNotFoundError:
    print(f"Error: The file at {dataset_path} was not found.")
    exit(1)  # Exit the script if the file is not found
except json.JSONDecodeError:
    print(f"Error: Failed to decode JSON from the file at {dataset_path}.")
    exit(1)  # Exit if there are issues with the JSON structure
    

# Extract benign (positive) and malware (negative) data
ember_benign = data.get('positive', [])  # Default to empty list if not found
ember_malware = data.get('negative', [])  # Default to empty list if not found

# Check if benign or malware data is missing
if not ember_benign or not ember_malware:
    print("Warning: Benign or Malware data is missing in the dataset.")
    print("Benign data:", ember_benign)
    print("Malware data:", ember_malware)

# Ensure ember_benign and ember_malware are loaded before calling generate_datasets
if not ember_benign or not ember_malware:
    raise ValueError("Benign or Malware data is missing in the dataset")

# Now call the generate_datasets function with the correct arguments
dataset = generate_datasets(0.5, 0.5, 1000, 10, ember_benign, ember_malware)

# Iterate over the datasets and call create_ontology_dataset for each one
for num, d in dataset.items():
    create_ontology_dataset(ontology_path, ontology_name, d, "dataset_" + str(num) + "_1000", output_path)
    
# regenerate ontology from specific samples

dataset = load_dataset(r"/home/user007/Downloads/ml_files/pe-malware-ontology-main/example1/sample_raw.json")

for num, d in dataset.items():
    create_ontology_dataset(ontology_path, ontology_name, d, "sample", output_path)



# generate folds from examples file
generate_folds(r"/home/user007/Downloads/ml_files/pe-malware-ontology-main/example1/sample_examples.json", output_path,"test_1")

