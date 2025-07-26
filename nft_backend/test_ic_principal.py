import sys
try:
    from ic.principal import Principal
    print(f"Successfully imported Principal from {Principal.__module__}")
    if hasattr(Principal, 'from_text'):
        print("Principal class has 'from_text' attribute.")
        test_principal_id = "aaaaa-aa"  # A common, valid principal ID for testing
        try:
            p = Principal.from_text(test_principal_id)
            print(f"Successfully created Principal object: {p}")
        except Exception as e:
            print(f"Error when calling Principal.from_text: {e}")
    else:
        print("ERROR: Principal class does NOT have 'from_text' attribute.")
    
    print(f"Type of the imported Principal object: {type(Principal)}")
    print("Directory listing of Principal object (contains its attributes/methods):")
    for attr in dir(Principal):
        print(f"  - {attr}")

except ImportError as e:
    print(f"Failed to import ic.principal: {e}")
    print("Please ensure 'ic-py' is installed: pip install ic-py")
except Exception as e:
    print(f"An unexpected error occurred: {e}")

print("\n--- Environment Info ---")
print(f"Python executable used: {sys.executable}")
print("Python path (sys.path):")
for p in sys.path:
    print(f"  - {p}")
