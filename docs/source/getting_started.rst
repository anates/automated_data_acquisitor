Getting started
=================
Welcome to the Automated Data Acquisitor project! This guide will help you get started with the 
project, including installation, usage, and contributing.

Installation
----------------
To install the Automated Data Acquisitor, you can use Poetry, a dependency management tool for 
Python. Follow these steps:

1. **Install Poetry**: If you haven't already, install Poetry by following the instructions on the 
[Poetry website](https://python-poetry.org/docs/#installation).

2. **Clone the repository**: Clone the Automated Data Acquisitor repository from GitLab:
```bash
git clone https://gitlab.com/intelligent-manufacturing-group/automated_data_aquisitor.git
cd automated_data_aquisitor
```
3. **Install dependencies**: Run the following command to install the project dependencies:
```bash
poetry install
```
4. **Activate the virtual environment**: Poetry automatically creates a virtual environment for the 
project. You can activate it with:
```bash
poetry shell
```

5. **Run the project**: You can now run the Automated Data Acquisitor using Poetry:
```bash
poetry run acquire_data --config path/to/config.json
```

Usage
----------------
Once you have installed the Automated Data Acquisitor, you can start using it to acquire and process 
data. All settings can be set and changed via the config.json-file. For details refer to the 
documentation or contact the authors.
