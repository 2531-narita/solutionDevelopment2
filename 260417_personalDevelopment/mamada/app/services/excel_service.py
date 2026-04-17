import pandas as pd
import os
import uuid

def export_to_excel(extracted_data, export_dir):
    """
    extracted_data: list of dicts [{'tag': 'Date', 'text': '2023-05-13'}, ...]
    """
    # Create dictionary mapping tags to text
    row_data = {}
    for item in extracted_data:
        row_data[item['tag']] = [item['text']]
        
    df = pd.DataFrame(row_data)
    
    file_id = str(uuid.uuid4())
    excel_path = os.path.join(export_dir, f"result_{file_id}.xlsx")
    df.to_excel(excel_path, index=False)
    
    return excel_path
