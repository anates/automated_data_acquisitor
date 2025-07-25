# Automated Data Acquisitor

This project provides a script for automated acoustic data acquisition.

## Main Script

The main code is located in `automated_data_acquisitor.py`. All necessary documentation is included within the script.

## Setup

This project uses [Poetry](https://python-poetry.org/) for environment and dependency management.

1. **Clone or download** this repository.
2. Ensure you have Poetry installed.
3. Install dependencies and set up the environment:

    ```bash
    poetry install
    ```

## Supported Python Versions

- Python 3.11
- Python 3.12
- Python 3.13

## Usage

Run the script using Poetry, either using the full path:

```bash
poetry run python -m src.automated_data_acquisitor.automated_data_acquisitor --config <path_to_config_file>
```

or after running `poetry install`: 

```bash
poetry run acquire_data --config <path_to_config_file>
```

## Options

- `--config <path>`: Specify the path to the configuration file (optional).

## Example

```bash
poetry run acquire_data --config params.json
```

## Support

If you encounter issues or have questions, please consult the developers at EMPA.