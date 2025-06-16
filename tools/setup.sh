#!/bin/bash

# AutoGen Repository Setup for Codex Analysis
# Ubuntu 24.04 Compatible

set -e

echo "Setting up AutoGen repository for analysis..."

# Update system
sudo apt update

# Install git if not present
sudo apt install -y git

# Clone AutoGen repository
echo "Cloning AutoGen repository..."
git clone https://github.com/microsoft/autogen.git
cd autogen

# Install Python dependencies
echo "Installing Python dependencies..."
sudo apt install -y python3 python3-pip python3-venv

# Create virtual environment
python3 -m venv autogen_env
source autogen_env/bin/activate

# Install AutoGen and dependencies
pip install --upgrade pip
pip install pyautogen

# Install Jupyter for notebook analysis
pip install jupyter notebook jupyterlab

# Install additional analysis tools
pip install pandas numpy matplotlib seaborn

# Extract Python files from notebooks for Codex analysis
echo "Extracting Python code from notebooks..."
mkdir -p extracted_code

# Find all notebooks and extract code
find . -name "*.ipynb" -type f | while read notebook; do
    # Get relative path and create corresponding .py file
    rel_path=$(realpath --relative-to=. "$notebook")
    py_file="extracted_code/${rel_path%.ipynb}.py"
    
    # Create directory structure
    mkdir -p "$(dirname "$py_file")"
    
    # Extract code cells using jupyter
    jupyter nbconvert --to script "$notebook" --output-dir="$(dirname "$py_file")" --output="$(basename "${py_file%.py}")" 2>/dev/null || echo "Skipping $notebook (conversion failed)"
done

# Create analysis summary
echo "Creating repository structure analysis..."
cat > repository_analysis.md << 'EOF'
# AutoGen Repository Analysis

## Structure Overview
```
$(tree -L 3 -I '__pycache__|*.pyc|node_modules|.git')
```

## Python Files Extracted
$(find extracted_code -name "*.py" | wc -l) Python files extracted from notebooks

## Key Directories
- **autogen/**: Core framework code
- **samples/**: Example implementations
- **test/**: Test suites
- **docs/**: Documentation
- **extracted_code/**: Jupyter notebooks converted to Python

## Requirements
$(pip list | grep -E "(autogen|jupyter)")

EOF

# Evaluate tree command availability and update analysis
if command -v tree &> /dev/null; then
    tree -L 3 -I '__pycache__|*.pyc|node_modules|.git' >> temp_tree.txt
    sed -i '/$(tree/r temp_tree.txt' repository_analysis.md
    sed -i '/$(tree/d' repository_analysis.md
    rm temp_tree.txt
else
    echo "Installing tree command..."
    sudo apt install -y tree
    tree -L 3 -I '__pycache__|*.pyc|node_modules|.git' >> temp_tree.txt
    sed -i '/$(tree/r temp_tree.txt' repository_analysis.md
    sed -i '/$(tree/d' repository_analysis.md
    rm temp_tree.txt
fi

# Update requirements section
pip list | grep -E "(autogen|jupyter)" >> temp_reqs.txt
sed -i '/$(pip list/r temp_reqs.txt' repository_analysis.md
sed -i '/$(pip list/d' repository_analysis.md
rm temp_reqs.txt

echo "Setup complete!"
echo "Repository cloned to: $(pwd)"
echo "Virtual environment: autogen_env"
echo "Python files extracted to: extracted_code/"
echo "Analysis summary: repository_analysis.md"

# Provide next steps
cat << 'EOF'

Next Steps:
1. Activate environment: source autogen_env/bin/activate
2. Review repository_analysis.md
3. Examine extracted_code/ for Python implementations
4. Run: jupyter lab (to explore notebooks interactively if needed)

For Codex Analysis:
- Focus on extracted_code/ directory for pure Python code
- Key files likely in autogen/ core directory
- Examples in samples/ directory show usage patterns
EOF
