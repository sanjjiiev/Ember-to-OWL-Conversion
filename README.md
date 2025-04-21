Ember to OWL Conversion is a data transformation pipeline that converts raw JSON data from the Ember Dataset — which includes telemetry for both malware and benign software — into a semantic, machine-readable format using OWL (Web Ontology Language). This process is built on top of a unified ontology derived from existing PE (Portable Executable) ontologies to enable intelligent reasoning and analysis.
📘 Project Overview

This project bridges low-level malware feature data and high-level semantic representation by:

    📦 Parsing raw Ember JSON samples.

    🧠 Mapping features to an integrated OWL ontology.

    🧬 Creating semantically rich individuals and class assertions in OWL.

    🔍 Enabling intelligent querying and inference for malware detection and analysis.

🧠 Ontology Background

    ✅ PE Ontology: Used to describe structures of Windows Portable Executable files.

    🔄 Merged Ontology: Combines concepts from PE ontology and UCO (Unified Cybersecurity Ontology) for better expressiveness.

    📄 Output: An OWL file (.owl) representing the sample semantically.

🔧 Features

    📁 Supports Bulk JSON Conversion from the Ember dataset.

    🗂️ Flexible Mapping Layer between JSON features and OWL properties.

    🛠️ Built using Python + RDFLib / OWLReady2.

    🧩 Ontology output is reasoner-ready (can be loaded in Protégé or used with OWL reasoners).

# PE Malware Ontology

## Technical report

Technical report about ontology is available at:

[https://arxiv.org/abs/2301.00153](https://arxiv.org/abs/2301.00153)

## Data

Datasets are available at:

[https://orbis-security.com/foldershare](https://orbis-security.com/foldershare)
