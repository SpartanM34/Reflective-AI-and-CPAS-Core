import json
import sys
from jsonschema import validate, ValidationError

# Load schema
def load_schema(schema_path):
    with open(schema_path, 'r') as f:
        return json.load(f)

# Load instance JSON to validate
def load_instance(instance_path):
    with open(instance_path, 'r') as f:
        return json.load(f)

# Perform validation
def validate_instance(instance_path, schema_path):
    schema = load_schema(schema_path)
    instance = load_instance(instance_path)
    try:
        validate(instance=instance, schema=schema)
        print(f"✅ Validation passed for {instance_path}")
    except ValidationError as ve:
        print(f"❌ Validation failed for {instance_path}")
        print("Reason:", ve.message)
        print("At:", list(ve.absolute_path))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python validate_idp.py <instance.json> <schema.json>")
        sys.exit(1)

    instance_file = sys.argv[1]
    schema_file = sys.argv[2]
    validate_instance(instance_file, schema_file)
