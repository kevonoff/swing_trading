#!/bin/bash

# ==============================================================================
# update_deps.sh
#
# This script scans all .py files in the project for imports and automatically
# adds any missing dependencies to the pyproject.toml file using Poetry.
#
# It relies on the 'deptry' tool to accurately identify missing packages.
# ==============================================================================

# --- Helper Functions ---
function print_info {
    echo -e "\033[34mINFO:\033[0m $1"
}

function print_success {
    echo -e "\033[32mSUCCESS:\033[0m $1"
}

function print_error {
    echo -e "\033[31mERROR:\033[0m $1"
}

# --- Main Script ---

# 1. Check if 'poetry' is installed and available
if ! command -v poetry &> /dev/null
then
    print_error "'poetry' command not found. Please install Poetry and ensure it's in your PATH."
    exit 1
fi
print_info "Poetry found."

# 2. Check if the project has 'deptry' installed as a dev dependency
if ! poetry run deptry --version &> /dev/null
then
    print_info "'deptry' not found in the project's environment."
    print_info "Attempting to install it as a development dependency..."
    poetry add deptry --group dev
    if [ $? -ne 0 ]; then
        print_error "Failed to install 'deptry'. Please install it manually with 'poetry add deptry --group dev'"
        exit 1
    fi
fi
print_info "Dependency analyzer 'deptry' is ready."

# 3. Run 'deptry' to find missing dependencies and capture the output
print_info "Scanning project for missing dependencies..."
# The 'awk' command isolates the list of missing packages from deptry's output.
MISSING_DEPS=$(poetry run deptry . | awk '/obsolete dependencies/,0{next} /missing dependencies/{flag=1; next} /^$/{flag=0} flag {print $1}')

# 4. Check if there are any missing dependencies to add
if [ -z "$MISSING_DEPS" ]; then
    print_success "Your pyproject.toml is already up-to-date. No new dependencies found."
    exit 0
fi

print_info "Found missing dependencies to add:"
echo "$MISSING_DEPS"
echo "" # newline for readability

# 5. Loop through the list and add each missing dependency
for DEP in $MISSING_DEPS
do
    print_info "Adding '$DEP' to pyproject.toml..."
    poetry add "$DEP"
    if [ $? -ne 0 ]; then
        print_error "Failed to add '$DEP'. Please add it manually."
    else
        print_success "Successfully added '$DEP'."
    fi
done

print_success "pyproject.toml has been updated."
```

### How to Use It

1.  **Save the file:** Create a file named `update_deps.sh` in the root of your project and paste the code above into it.
2.  **Make it executable:** Open your terminal in the project directory and run this command:
    ```bash
    chmod +x update_deps.sh
    ```
3.  **Run the script:** Whenever you've added new imports to your Python files and want to update `pyproject.toml`, just run:
    ```bash
    ./update_deps.sh
    
