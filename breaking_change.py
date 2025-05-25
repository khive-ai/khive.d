"""
Breaking change implementation for API v2.
"""

def new_api_function(data: dict, version: str = "v2") -> dict:
    """
    New API function that breaks backward compatibility.
    
    Args:
        data: Input data in new format
        version: API version (required parameter in v2)
    
    Returns:
        Processed data in new format
    """
    if version != "v2":
        raise ValueError("Only v2 API is supported")
    
    # New processing logic that's incompatible with v1
    return {"version": version, "processed": data, "timestamp": "2025-01-01"}