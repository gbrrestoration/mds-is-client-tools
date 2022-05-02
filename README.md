# mds-is-client-tools
Suite of client scripts to provide example automated access workflows.

## Purpose 
Provide examples of scripts demonstrating the automated access workflows compatible with the system. For more information see the [documentation](https://gbrrestoration.github.io/rrap-mds-knowledge-hub/information-system/data-store/automated-access.html).

## To run

### Linux

```bash
# Setup environment
python -m venv .venv 
source .venv/bin/activate
# Install requirements
pip install -r requirements.txt 

# (First time only) get offline code
python get_offline_code.py 
# Save the code and export to environment
export RRAP_OFFLINE_TOKEN="above token here"
# Demonstrate getting access token 
python offline_access.py 
# Full end to end example 
python example_usage.py
```
