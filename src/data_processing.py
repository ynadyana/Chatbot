import pandas as pd

# Load your dataset
data_path = "../cleaned_laptops.csv"
laptop_data = pd.read_csv(data_path)

# Replace data at index 5 with animal-related information
# Example animal data: You can adjust the fields as per your requirement
animal_data = {
    'index': 5,  # Index to replace
    'brand': 'Lion',  # Replace 'brand' with animal name, for example
    'Model': 'Panthera leo',
    'Rating': 4.5,  # Example rating
    'processor_brand': 'N/A',  # Not applicable
    'processor_tier': 'N/A',  # Not applicable
    'num_cores': 0,  # Not applicable
    'num_threads': 0,  # Not applicable
    'ram_memory': 0,  # Not applicable
    'primary_storage_type': 'N/A',  # Not applicable
    'primary_storage_capacity': 0,  # Not applicable
    'secondary_storage_type': 'N/A',  # Not applicable
    'secondary_storage_capacity': 0,  # Not applicable
    'gpu_brand': 'N/A',  # Not applicable
    'gpu_type': 'N/A',  # Not applicable
    'is_touch_screen': 'No',  # Not applicable
    'display_size': 0,  # Not applicable
    'resolution_width': 0,  # Not applicable
    'resolution_height': 0,  # Not applicable
    'OS': 'N/A',  # Not applicable
    'year_of_warranty': 'N/A',  # Not applicable
    'Price_MYR': 0,  # Not applicable
}

# Replace the row with animal data
for column, value in animal_data.items():
    laptop_data.at[animal_data['index'], column] = value

# Save the updated dataset to a new CSV file
laptop_data.to_csv('updated_laptop_dataset.csv', index=False)

print("Row 5 has been replaced with animal data!")